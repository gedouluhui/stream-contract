import json
import unittest
try:
    from streamcontract.chat import collect_chat
except ModuleNotFoundError:
    collect_chat = None


def chunk(choices, usage=None):
    return ('data: '+json.dumps({'object':'chat.completion.chunk','choices':choices,'usage':usage},ensure_ascii=False)+'\n\n').encode()


def choice(i=0, text=None, finish=None):
    return {'index':i,'delta':{'content':text},'finish_reason':finish}


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(collect_chat, 'text collector is not implemented')

    def test_text_unicode_and_empty_usage_choices(self):
        wire=chunk([choice(text='雪')])+chunk([choice(text='!',finish='stop')])+chunk([],{'total_tokens':5})+b'data: [DONE]\n\n'
        expected={'status':'complete','choices':[{'index':0,'text':'雪!','finish_reason':'stop'}], 'usage':{'total_tokens':5},'diagnostic':None}
        for cut in range(len(wire)+1):
            self.assertEqual(collect_chat([wire[:cut],wire[cut:]]),expected)

    def test_multiple_choices_sorted_and_role_only_supported(self):
        wire=chunk([{'index':1,'delta':{'role':'assistant'}},choice(0,'A')])+chunk([choice(1,'B','stop'),choice(0,None,'length')])+b'data: [DONE]\n\n'
        result=collect_chat([wire])
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['choices'],[{'index':0,'text':'A','finish_reason':'length'},{'index':1,'text':'B','finish_reason':'stop'}])

    def test_missing_done_and_unfinished_event_are_incomplete(self):
        wire=chunk([choice(text='ok',finish='stop')])
        self.assertEqual(collect_chat([wire])['status'],'incomplete')
        self.assertEqual(collect_chat([wire+b'data: [DONE]'])['status'],'incomplete')

    def test_tools_are_explicitly_unsupported(self):
        wire=chunk([{'index':0,'delta':{'tool_calls':[]}}])+b'data: [DONE]\n\n'
        self.assertEqual(collect_chat([wire])['status'],'unsupported')

    def test_malformed_json_and_wrong_types_are_not_complete(self):
        for wire in [b'data: bad\n\n', b'data: []\n\n', chunk([choice(True,'x','stop')]),
                     chunk([choice(text=123,finish='stop')]), b'data: {"object":"chat.completion.chunk","choices":null}\n\n']:
            with self.subTest(wire=wire):
                self.assertEqual(collect_chat([wire])['status'],'profile_error')

    def test_done_only_and_data_after_done_rejected(self):
        self.assertEqual(collect_chat([b'data: [DONE]\n\n'])['status'],'profile_error')
        wire=chunk([choice(text='a',finish='stop')])+b'data: [DONE]\n\n'+chunk([choice(text='b')])
        self.assertEqual(collect_chat([wire])['status'],'profile_error')

    def test_no_finish_is_not_completed(self):
        self.assertEqual(collect_chat([chunk([choice(text='a')])+b'data: [DONE]\n\n'])['status'],'incomplete')

    def test_content_after_finish_rejected(self):
        wire=chunk([choice(text='a',finish='stop')])+chunk([choice(text='b')])+b'data: [DONE]\n\n'
        self.assertEqual(collect_chat([wire])['status'],'profile_error')

if __name__ == '__main__':
    unittest.main()
