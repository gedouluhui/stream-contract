import unittest
try:
    from streamcontract.audit import audit, replay_chunks
    from streamcontract.sse import parse_sse
except ModuleNotFoundError:
    audit = replay_chunks = parse_sse = None


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(audit, 'boundary audit is not implemented')
        self.data=b'data: ok\n\n'
        self.expected=[{'event':'message','data':'ok','id':''}]

    def test_reference_agrees_with_independent_expected_events(self):
        result=audit(self.data,parse_sse,self.expected)
        self.assertEqual(result['status'],'pass')
        self.assertTrue(result['exhaustive_single_cuts'])
        self.assertIsNone(result['first_failure'])

    def test_always_empty_client_cannot_self_certify(self):
        r=audit(self.data,lambda chunks:[],self.expected)
        self.assertEqual(r['status'],'fail')
        self.assertEqual(r['checked'],1)

    def test_broken_per_chunk_client_produces_replayable_counterexample(self):
        def broken(chunks):
            return [e for c in chunks for e in parse_sse([c])]
        r=audit(self.data,broken,self.expected)
        self.assertEqual(r['status'],'fail')
        f=r['first_failure']
        self.assertEqual(broken(replay_chunks(self.data,f['chunk_sizes'])),f['actual'])
        self.assertEqual(f['expected'],self.expected)

    def test_budget_reports_unchecked_single_cuts(self):
        r=audit(self.data,parse_sse,self.expected,max_cases=2)
        self.assertEqual(r['checked'],2)
        self.assertFalse(r['exhaustive_single_cuts'])

    def test_bool_does_not_equal_int_and_nan_cannot_pass(self):
        self.assertEqual(audit(b'x',lambda _:True,1)['status'],'fail')
        self.assertEqual(audit(b'x',lambda _:float('nan'),None)['status'],'fail')
        with self.assertRaises(ValueError):
            audit(b'x',lambda _:0,float('nan'))

    def test_client_exception_is_named_not_traceback(self):
        def broken(_):
            raise RuntimeError('private message')
        r=audit(b'x',broken,None)
        self.assertEqual(r['status'],'fail')
        self.assertEqual(r['first_failure']['exception'],'RuntimeError')
        self.assertNotIn('private message',str(r))

    def test_replay_and_input_limits(self):
        for sizes in [[0,10],[-1,11],[True,9],[2]]:
            with self.assertRaises(ValueError):
                replay_chunks(self.data,sizes)
        with self.assertRaises(ValueError):
            audit(b'x'*65537,parse_sse,[])
        for value in [True,1,2049]:
            with self.assertRaises(ValueError):
                audit(self.data,parse_sse,self.expected,max_cases=value)

    def test_shared_oracle_graph_has_a_finite_normalization_budget(self):
        nested = []
        for _ in range(20):
            nested = [nested, nested]
        with self.assertRaises(ValueError):
            audit(b'x', lambda _: [], nested)

    def test_oversized_client_string_fails_with_named_error(self):
        result = audit(b'x', lambda _: 'x' * 1048577, None)
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['first_failure'].get('exception'), 'ValueError')

    def test_empty_stream_has_one_finite_case(self):
        r=audit(b'',parse_sse,[])
        self.assertEqual(r['status'],'pass')
        self.assertEqual(r['checked'],1)
        self.assertTrue(r['exhaustive_single_cuts'])

if __name__ == '__main__':
    unittest.main()
