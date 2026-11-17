"""Synthetic positive fixture and an intentionally broken negative control."""
import json
from .audit import audit
from .chat import collect_chat


def demo_wire() -> bytes:
    objects = [
        {'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': 'Hello '}, 'finish_reason': None}]},
        {'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {'content': '雪'}, 'finish_reason': 'stop'}]},
        {'object': 'chat.completion.chunk', 'choices': [], 'usage': {'total_tokens': 5}},
    ]
    return ''.join('data: '+json.dumps(x, ensure_ascii=False)+'\r\n\r\n' for x in objects).encode() + b'data: [DONE]\r\n\r\n'


def demo_report() -> dict:
    wire = demo_wire()
    expected = {'status': 'complete', 'choices': [{'index': 0, 'text': 'Hello 雪', 'finish_reason': 'stop'}],
                'usage': {'total_tokens': 5}, 'diagnostic': None}

    def broken(chunks):
        # Intentionally wrong: decoding every network chunk independently
        # corrupts multibyte UTF-8 that crosses a byte boundary.
        text = ''.join(chunk.decode('utf-8', errors='replace') for chunk in chunks)
        return collect_chat([text.encode('utf-8')])

    return {'schema': 'streamcontract.demo.v1',
            'note': 'Synthetic fixture; the negative control is intentionally broken, not a third-party SDK bug.',
            'reference': audit(wire, collect_chat, expected),
            'broken_control': audit(wire, broken, expected)}
