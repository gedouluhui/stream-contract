"""Deterministic partition audits against an explicit, independent JSON oracle."""
from collections.abc import Callable, Iterable
import json
import math


def _canonical(value):
    visited = 0
    def check(x, depth=0):
        nonlocal visited
        visited += 1
        if visited > 20000 or depth > 64:
            raise ValueError('result exceeds node or nesting budget')
        if type(x) is str:
            if len(x) > 1048576:
                raise ValueError('result string exceeds 1 MiB character budget')
            return
        if x is None or type(x) in (bool, int):
            return
        if type(x) is float and math.isfinite(x):
            return
        if type(x) is list:
            for child in x:
                check(child, depth + 1)
            return
        if type(x) is dict:
            for key, child in x.items():
                if type(key) is not str:
                    raise ValueError('result object keys must be strings')
                check(key, depth + 1)
                check(child, depth + 1)
            return
        raise ValueError('expected/client result must be finite JSON with string object keys')
    check(value)
    encoder = json.JSONEncoder(ensure_ascii=True, sort_keys=True, allow_nan=False, separators=(',', ':'))
    parts, size = [], 0
    for part in encoder.iterencode(value):
        size += len(part)  # ensure_ascii means characters and UTF-8 bytes agree.
        if size > 1048576:
            raise ValueError('normalized result exceeds 1 MiB')
        parts.append(part)
    return ''.join(parts)


def replay_chunks(data: bytes, sizes: Iterable[int]) -> list[bytes]:
    if type(data) is not bytes:
        raise ValueError('data must be bytes')
    sizes = list(sizes)
    if any(type(n) is not int or n <= 0 for n in sizes) or sum(sizes) != len(data):
        raise ValueError('chunk sizes must be positive integers covering the input exactly')
    chunks, start = [], 0
    for n in sizes:
        chunks.append(data[start:start+n])
        start += n
    return chunks


def _plans(n):
    if not n:
        yield ()
        return
    yield (n,)
    yield (1,) * n
    for cut in range(1, n):
        yield (cut, n-cut)
    for widths in ((2, 3, 5), (7, 1, 11), (13, 17)):
        sizes, remaining, i = [], n, 0
        while remaining:
            take = min(widths[i % len(widths)], remaining)
            sizes.append(take)
            remaining -= take
            i += 1
        yield tuple(sizes)


def audit(data: bytes, client: Callable, expected, *, max_cases: int = 512) -> dict:
    """Audit finite partitions, not all possible partitions or a whole vendor API.

    The local client is trusted executable code, NOT sandboxed. The caller must
    supply an independent expected result; it is never inferred from the client.
    """
    if type(data) is not bytes or len(data) > 65536:
        raise ValueError('audit needs bytes of length at most 65536')
    if not callable(client):
        raise TypeError('client must be callable')
    if type(max_cases) is not int or not 2 <= max_cases <= 2048:
        raise ValueError('max_cases must be an integer in 2..2048')
    want = _canonical(expected)
    report = {'status': 'pass', 'checked': 0, 'available_single_cuts': max(0, len(data)-1),
              'exhaustive_single_cuts': False, 'max_cases': max_cases, 'first_failure': None}
    seen, cuts = set(), set()
    for plan in _plans(len(data)):
        if plan in seen:
            continue
        if report['checked'] >= max_cases:
            break
        seen.add(plan)
        report['checked'] += 1
        if len(plan) == 2:
            cuts.add(plan[0])
        failure = {'chunk_sizes': list(plan), 'expected': json.loads(want)}
        try:
            actual = _canonical(client(iter(replay_chunks(data, plan))))
        except Exception as exc:
            failure['exception'] = type(exc).__name__
        else:
            if actual == want:
                continue
            failure['actual'] = json.loads(actual)
        report['status'] = 'fail'
        report['first_failure'] = failure
        break
    report['exhaustive_single_cuts'] = len(cuts) == report['available_single_cuts']
    return report
