import json
import random
import unittest

from streamcontract.chat import collect_chat
from streamcontract.jsonutil import loads


class DuplicateKeyTests(unittest.TestCase):
    def test_duplicate_keys_are_rejected_at_every_object_depth(self):
        documents = [
            '{"same":1,"same":2}',
            '{"outer":{"same":1,"same":2}}',
            '{"outer":[{"inner":{"same":1,"same":2}}]}',
            '{"same":1,"\\u0073ame":2}',
        ]
        for document in documents:
            with self.subTest(document=document):
                with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
                    loads(document)

    def test_repeated_keys_in_distinct_objects_are_not_duplicates(self):
        self.assertEqual(loads('{"left":{"a":1},"right":{"a":2}}'),
                         {'left': {'a': 1}, 'right': {'a': 2}})

    def test_strict_loader_preserves_json_and_numeric_parser_options(self):
        value = loads('[1,1.5,"x"]', parse_int=lambda value: ('int', value),
                      parse_float=lambda value: ('float', value))
        self.assertEqual(value, [('int', '1'), ('float', '1.5'), 'x'])
        def reject_constant(value):
            raise ValueError('non-finite')
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            loads('NaN', parse_constant=reject_constant)

    def test_chat_rejects_duplicate_keys_in_all_parsed_sections(self):
        documents = [
            '{"object":"chat.completion.chunk","object":"chat.completion.chunk","choices":[]}',
            '{"object":"chat.completion.chunk","choices":[{"index":0,"index":0,"delta":{},"finish_reason":"stop"}]}',
            '{"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"a","content":"b"},"finish_reason":"stop"}]}',
            '{"object":"chat.completion.chunk","choices":[],"usage":{"total_tokens":1,"total_tokens":2}}',
            '{"object":"chat.completion.chunk","choices":[],"usage":{"nested":{"a":1,"a":2}}}',
            '{"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"metadata":{"a":1,"a":2}}}]}',
        ]
        for document in documents:
            with self.subTest(document=document):
                wire = ('data: ' + document + '\n\ndata: [DONE]\n\n').encode('utf-8')
                report = collect_chat([wire])
                self.assertEqual(report['status'], 'profile_error')
                self.assertEqual(report['diagnostic'], 'invalid_json')

    def test_random_nested_duplicate_keys_are_always_rejected(self):
        rng = random.Random(61489)
        for case in range(60):
            document = '{"dup":1,"dup":2}'
            for depth in range(rng.randint(0, 8)):
                if rng.choice([False, True]):
                    document = '[' + document + ']'
                else:
                    document = '{"level' + str(depth) + '":' + document + '}'
            with self.subTest(case=case, document=document):
                with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
                    loads(document)
                wire = ('data: {"object":"chat.completion.chunk","choices":[],"usage":'
                        + document + '}\n\ndata: [DONE]\n\n').encode('utf-8')
                report = collect_chat([wire])
                self.assertEqual(report['status'], 'profile_error')
                self.assertEqual(report['diagnostic'], 'invalid_json')


if __name__ == '__main__':
    unittest.main()
