import json
import random
import unittest

from streamcontract.chat import collect_chat


def event_bytes(value):
    return ('data: ' + json.dumps(value, ensure_ascii=False) + '\n\n').encode('utf-8')


def chunk(content=None, *, index=0, finish=None, role=None):
    delta = {}
    if role is not None:
        delta['role'] = role
    if content is not None:
        delta['content'] = content
    return {'object': 'chat.completion.chunk',
            'choices': [{'index': index, 'delta': delta, 'finish_reason': finish}]}


def complete(events):
    return b''.join(event_bytes(event) for event in events) + b'data: [DONE]\n\n'


def partitions(data, rng):
    cuts = sorted(rng.sample(range(1, len(data)), min(len(data) - 1, rng.randint(1, 20))))
    points = [0, *cuts, len(data)]
    return [data[a:b] for a, b in zip(points, points[1:])]


class MicroDeltaTests(unittest.TestCase):
    def test_many_small_deltas_are_aggregated_without_losing_order(self):
        count = 8000
        first = event_bytes(chunk('x'))
        wire = first * count + event_bytes(chunk(finish='stop')) + b'data: [DONE]\n\n'
        self.assertLess(len(wire), 1048576, 'fixture must remain inside the SSE byte budget')
        report = collect_chat([wire])
        self.assertEqual(report, {
            'status': 'complete',
            'choices': [{'index': 0, 'text': 'x' * count, 'finish_reason': 'stop'}],
            'usage': None,
            'diagnostic': None,
        })

    def test_random_text_is_invariant_under_byte_chunk_boundaries(self):
        rng = random.Random(73021)
        alphabet = ['a', 'Z', '0', ' ', '\n', '\r', '\t', '雪', 'é', 'e\u0301', '🙂', '\x00']
        for case in range(40):
            text = ''.join(rng.choice(alphabet) for _ in range(rng.randint(0, 80)))
            cut = rng.randint(0, len(text))
            wire = complete([chunk(text[:cut]), chunk(text[cut:], finish='stop')])
            expected = {
                'status': 'complete',
                'choices': [{'index': 0, 'text': text, 'finish_reason': 'stop'}],
                'usage': None,
                'diagnostic': None,
            }
            with self.subTest(case=case, text=repr(text)):
                self.assertEqual(collect_chat([wire]), expected)
                self.assertEqual(collect_chat(partitions(wire, rng)), expected)

    def test_every_single_byte_cut_preserves_utf8_and_line_state(self):
        texts = ['雪🙂é', 'e\u0301\n雪', '\x00🙂']
        line_endings = ['\n', '\r', '\r\n']
        for text in texts:
            for ending in line_endings:
                values = [chunk(text[:1]), chunk(text[1:], finish='stop')]
                wire = b''.join(
                    ('data: ' + json.dumps(value, ensure_ascii=False) + ending + ending).encode('utf-8')
                    for value in values
                ) + b'data: [DONE]' + ending.encode() + ending.encode()
                expected = collect_chat([wire])
                self.assertEqual(expected['choices'][0]['text'], text)
                for cut in range(len(wire) + 1):
                    with self.subTest(text=repr(text), ending=repr(ending), cut=cut):
                        self.assertEqual(collect_chat([wire[:cut], wire[cut:]]), expected)

    def test_random_choice_interleavings_preserve_per_choice_order(self):
        rng = random.Random(99173)
        alphabet = ['a', '雪', '🙂', '\n', 'é']
        for case in range(40):
            parts = {index: [''.join(rng.choice(alphabet) for _ in range(rng.randint(1, 8)))
                             for _ in range(rng.randint(1, 6))]
                     for index in range(rng.randint(1, 4))}
            events = [chunk(parts[index][0], index=index, role='assistant' if index == 0 else None)
                      for index in parts]
            positions = {index: 1 for index in parts}
            while any(positions[index] < len(parts[index]) for index in parts):
                available = [index for index in parts if positions[index] < len(parts[index])]
                index = rng.choice(available)
                events.append(chunk(parts[index][positions[index]], index=index))
                positions[index] += 1
            events.extend(chunk(finish='stop', index=index) for index in parts)
            wire = complete(events)
            expected_choices = [
                {'index': index, 'text': ''.join(parts[index]), 'finish_reason': 'stop'}
                for index in sorted(parts)
            ]
            with self.subTest(case=case):
                baseline = collect_chat([wire])
                self.assertEqual(baseline['status'], 'complete')
                self.assertEqual(baseline['choices'], expected_choices)
                for _ in range(4):
                    self.assertEqual(collect_chat(partitions(wire, rng)), baseline)

    def test_escaped_unicode_and_finish_checks_match_across_boundaries(self):
        value = chunk('雪🙂', finish='length')
        raw_json = json.dumps(value, ensure_ascii=True)
        wire = ('data: ' + raw_json + '\n\n').encode('ascii') + b'data: [DONE]\n\n'
        expected = {
            'status': 'complete',
            'choices': [{'index': 0, 'text': '雪🙂', 'finish_reason': 'length'}],
            'usage': None,
            'diagnostic': None,
        }
        for cut in range(len(wire) + 1):
            with self.subTest(cut=cut):
                self.assertEqual(collect_chat([wire[:cut], wire[cut:]]), expected)
        late = (event_bytes(chunk('before')) + event_bytes(chunk('finished', finish='stop'))
                + event_bytes(chunk('after')) + b'data: [DONE]\n\n')
        self.assertEqual(collect_chat([late])['diagnostic'], 'choice_after_finish')


if __name__ == '__main__':
    unittest.main()
