"""Optional real-SDK comparison; offline, no key/client/model call.

Uses an internal SDK decoder API, so report the exact installed version.
Differences from WHATWG SSE are observations, not claims about live APIs.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from streamcontract import audit, parse_sse


def main():
    try:
        import openai
        from openai._streaming import SSEDecoder
    except ImportError:
        print('Optional check requires an already installed openai SDK.', file=sys.stderr)
        return 2

    def sdk(chunks):
        return [{'event': e.event or 'message', 'data': e.data, 'id': e.id or ''}
                for e in SSEDecoder().iter_bytes(iter(chunks))]

    expected = [{'event': 'message', 'data': 'snow: 雪', 'id': ''}]
    normal = 'data: snow: 雪\r\n\r\n'.encode('utf-8')
    results = []
    for name, wire in [('unicode_crlf', normal), ('leading_utf8_bom', b'\xef\xbb\xbf' + normal)]:
        results.append({'case': name, 'wire_hex': wire.hex(),
                        'reference': audit(wire, parse_sse, expected),
                        'sdk': audit(wire, sdk, expected)})
    print(json.dumps({'sdk': 'openai', 'version': openai.__version__,
                      'interface': 'openai._streaming.SSEDecoder.iter_bytes (internal)',
                      'normalization': 'missing event->message; missing id->empty string',
                      'note': 'Offline decoder comparison, not a live API or general SDK compliance claim.',
                      'cases': results}, ensure_ascii=True, indent=2))
    # A difference is a recorded finding, not a failed execution of this probe.
    # Baseline/reference failures make the probe itself inconclusive.
    return 0 if all(r['reference']['status'] == 'pass' for r in results) and results[0]['sdk']['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
