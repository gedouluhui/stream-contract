"""Review regressions: complete must mean supported terminal semantics."""
import json
import unittest
from unittest.mock import patch

from streamcontract import audit, collect_chat


def wire(reason='stop', usage=None):
    obj = {'object': 'chat.completion.chunk',
           'choices': [{'index': 0, 'delta': {'content': 'x'}, 'finish_reason': reason}]}
    text = json.dumps(obj)
    if usage is not None:
        text = text[:-1] + ',"usage":' + usage + '}'
    return ('data: ' + text + '\n\ndata: [DONE]\n\n').encode()


class QualityR3(unittest.TestCase):
    def test_exponent_overflow_cannot_complete(self):
        for number in ('1e309', '-1e309', '1e99999'):
            r = collect_chat([wire(usage='{"total_tokens":'+number+'}')])
            self.assertEqual(r['status'], 'profile_error')
            self.assertIsNone(r['usage'])
            json.dumps(r, allow_nan=False)

    def test_terminal_reason_is_not_arbitrary_string(self):
        for reason, status in [('', 'profile_error'), ('bogus', 'unsupported'),
                               ('tool_calls', 'unsupported'), ('function_call', 'unsupported')]:
            self.assertEqual(collect_chat([wire(reason)])['status'], status)

    def test_supported_terminal_and_finite_numbers_still_complete(self):
        for reason in ('stop', 'length', 'content_filter'):
            r = collect_chat([wire(reason, '{"total_tokens":5,"ratio":1e-300}')])
            self.assertEqual(r['status'], 'complete')
            self.assertEqual(r['usage']['total_tokens'], 5)

    def test_large_oracle_integer_rejected_before_encoder(self):
        # Wrong fix to expose: check size only after JSONEncoder serialized the int.
        with patch('streamcontract.audit.json.JSONEncoder.iterencode', side_effect=AssertionError('encoder reached')):
            with self.assertRaisesRegex(ValueError, 'integer'):
                audit(b'x', lambda _: 0, 1 << 5000)

    def test_large_client_integer_fails_with_value_error(self):
        r = audit(b'x', lambda _: 1 << 5000, None)
        self.assertEqual(r['status'], 'fail')
        self.assertEqual(r['first_failure'].get('exception'), 'ValueError')
        self.assertNotIn('actual', r['first_failure'])

    def test_normal_and_negative_integers_preserved(self):
        for n in [0, -1, 2**63, -(2**63), 1 << 4095]:
            self.assertEqual(audit(b'x', lambda _, n=n: n, n)['status'], 'pass')

    def test_huge_incoming_integer_is_profile_error(self):
        r = collect_chat([wire(usage='{"total_tokens":' + str(1 << 5000) + '}')])
        self.assertEqual(r['status'], 'profile_error')
        self.assertIsNone(r['usage'])


if __name__ == '__main__':
    unittest.main()
