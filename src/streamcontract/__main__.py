"""Offline CLI. Custom client adapters belong in trusted Python code, not JSON."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .chat import collect_chat
from .demo import demo_report


def _write(path, text, overwrite):
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError('output exists; use --force to replace it')
    fd, tmp = tempfile.mkstemp(prefix='.streamcontract-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if overwrite:
            os.replace(tmp, path)
        else:
            os.link(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv=None):
    p = argparse.ArgumentParser(description='Offline SSE and LLM text-client boundary checks. No network calls.')
    sub = p.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo', help='run a synthetic reference and intentionally broken control')
    check = sub.add_parser('check', help='check recorded SSE with the narrow Chat text profile')
    check.add_argument('input')
    for item in (demo, check):
        item.add_argument('--json', dest='output')
        item.add_argument('--force', action='store_true')
    args = p.parse_args(argv)
    try:
        if args.output and Path(args.output).exists() and not args.force:
            raise FileExistsError('output exists; use --force to replace it')
        if args.command == 'check':
            if args.output and Path(args.input).resolve() == Path(args.output).resolve():
                raise ValueError('input and output paths must differ')
            with open(args.input, 'rb') as f:
                wire = f.read(1048577)
            if len(wire) > 1048576:
                raise ValueError('input exceeds 1 MiB')
            report = collect_chat([wire])
            code = 0 if report['status'] == 'complete' else 1
        else:
            report = demo_report()
            code = 0 if report['reference']['status'] == 'pass' and report['broken_control']['status'] == 'fail' else 1
        text = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + '\n'
        if args.output:
            _write(args.output, text, args.force)
        print(text, end='')
        return code
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        detail = str(exc).encode('ascii', 'backslashreplace').decode('ascii')
        print(f'streamcontract: {detail}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
