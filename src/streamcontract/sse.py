"""Bounded SSE framing following WHATWG event-stream interpretation.

This is an offline parser, not EventSource: it never reconnects or does I/O.
"""
import codecs
from collections.abc import Iterable


def parse_sse(chunks: Iterable[bytes], *, max_bytes: int = 1048576,
              max_event_chars: int = 65536) -> list[dict]:
    for name, limit in [('max_bytes', max_bytes), ('max_event_chars', max_event_chars)]:
        if type(limit) is not int or limit < 1:
            raise ValueError(f'{name} must be a positive integer')
    decoder = codecs.getincrementaldecoder('utf-8-sig')(errors='replace')
    events, line, data = [], [], []
    event_type, last_id = '', ''
    consumed = data_chars = 0
    previous_cr = False

    def process_line():
        nonlocal event_type, last_id, data_chars
        text = ''.join(line)
        line.clear()
        if not text:
            if data:
                events.append({'event': event_type or 'message',
                               'data': '\n'.join(data), 'id': last_id})
            data.clear()
            data_chars = 0
            event_type = ''
        elif not text.startswith(':'):
            field, sep, value = text.partition(':')
            if sep and value.startswith(' '):
                value = value[1:]
            if field == 'data':
                data_chars += len(value) + 1
                if data_chars > max_event_chars:
                    raise ValueError('max_event_chars exceeded')
                data.append(value)
            elif field == 'event':
                event_type = value
            elif field == 'id' and '\x00' not in value:
                last_id = value
            # retry and unknown fields have no offline transport side effects.

    def feed(text):
        nonlocal previous_cr
        for char in text:
            if char == '\r':
                process_line()
                previous_cr = True
            elif char == '\n':
                if not previous_cr:
                    process_line()
                previous_cr = False
            else:
                previous_cr = False
                line.append(char)
                if len(line) > max_event_chars:
                    raise ValueError('max_event_chars exceeded by a line')

    for chunk in chunks:
        if type(chunk) is not bytes:
            raise TypeError('chunks must contain bytes')
        consumed += len(chunk)
        if consumed > max_bytes:
            raise ValueError('max_bytes exceeded')
        feed(decoder.decode(chunk))
    feed(decoder.decode(b'', final=True))
    # Deliberately do not dispatch a pending line/event at EOF.
    return events
