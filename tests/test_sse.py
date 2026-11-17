import unittest
try:
    from streamcontract.sse import parse_sse
except ModuleNotFoundError:
    parse_sse = None


def event(data, event='message', id=''):
    return {'event': event, 'data': data, 'id': id}


class SseTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(parse_sse, 'SSE parser is not implemented')

    def test_known_events_at_every_single_cut_and_one_byte(self):
        fixtures = [
            (b'data: ok\n\n', [event('ok')]),
            ('data: 雪λ\r\ndata: two\r\n\r\n'.encode(), [event('雪λ\ntwo')]),
            (b'data: x\r\r', [event('x')]),
            (b'\xef\xbb\xbfdata: x\n\n', [event('x')]),
            (b':comment\ndata:  spaced\n\n', [event(' spaced')]),
            (b'data\n\n', [event('')]),
            (b'data:\ndata:\n\n', [event('\n')]),
            (b'Data: ignored\n\n', []),
            (b'id: 1\nevent: custom\ndata: first\n\ndata: next\n\n',
             [event('first', 'custom', '1'), event('next', id='1')]),
            (b'id: 1\n\nid: no\x00\ndata: yes\n\n', [event('yes', id='1')]),
            (b'id: 1\ndata: a\n\nid\ndata: b\n\n', [event('a', id='1'), event('b')]),
            (b'event: unused\n\ndata: normal\n\n', [event('normal')]),
            (b'data: \xff\n\n', [event('\ufffd')]),
            (b'data: missing blank\n', []),
            (b'data: no terminator', []),
            (b'data: a\n\ndata: lost', [event('a')]),
        ]
        for wire, want in fixtures:
            with self.subTest(wire=wire):
                for cut in range(len(wire) + 1):
                    self.assertEqual(parse_sse([wire[:cut], wire[cut:]]), want)
                self.assertEqual(parse_sse([wire[i:i+1] for i in range(len(wire))]), want)

    def test_bom_is_only_stripped_once(self):
        self.assertEqual(parse_sse(['data: \ufeffinside\n\n'.encode()]), [event('\ufeffinside')])

    def test_byte_and_line_event_budgets(self):
        with self.assertRaises(ValueError):
            parse_sse([b'data: x\n\n'], max_bytes=3)
        with self.assertRaises(ValueError):
            parse_sse([b'data: '+b'x'*12], max_event_chars=8)
        with self.assertRaises(ValueError):
            parse_sse([b'data: abc\n'*10], max_event_chars=10)

    def test_invalid_input_and_limits_rejected(self):
        for chunks in [['text'], [bytearray(b'data: x')], [None]]:
            with self.assertRaises((TypeError, ValueError)):
                parse_sse(chunks)
        for value in [True, 0, -1, 1.2]:
            with self.assertRaises((TypeError, ValueError)):
                parse_sse([], max_bytes=value)

if __name__ == '__main__':
    unittest.main()
