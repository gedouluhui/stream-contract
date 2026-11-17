import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def run(args,cwd):
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')
    return subprocess.run([sys.executable,'-m','streamcontract',*args],cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)


class CliTests(unittest.TestCase):
    def test_demo_has_reference_and_actual_broken_control(self):
        with tempfile.TemporaryDirectory() as d:
            r=run(['demo','--json','result.json'],d)
            self.assertEqual(r.returncode,0,r.stderr)
            result=json.loads(Path(d,'result.json').read_text(encoding='utf-8'))
            self.assertEqual(result['reference']['status'],'pass')
            self.assertEqual(result['broken_control']['status'],'fail')
            self.assertIsNotNone(result['broken_control']['first_failure'])
            self.assertIn('intentionally broken',result['note'])
            before=Path(d,'result.json').read_bytes()
            self.assertEqual(run(['demo','--json','result.json'],d).returncode,2)
            self.assertEqual(Path(d,'result.json').read_bytes(),before)
            self.assertEqual(run(['demo','--json','result.json','--force'],d).returncode,0)

    def test_check_success_incomplete_and_invalid(self):
        complete=b'data: {"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
        with tempfile.TemporaryDirectory() as d:
            for wire,want in [(complete,0),(complete.split(b'data: [DONE]')[0],1),(b'data: bad\n\n',1)]:
                Path(d,'input.sse').write_bytes(wire)
                r=run(['check','input.sse'],d)
                self.assertEqual(r.returncode,want,r.stderr)
                self.assertIn('status',json.loads(r.stdout))
            self.assertEqual(run(['check','absent.sse'],d).returncode,2)

    def test_check_cannot_replace_input_with_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'input.sse');p.write_bytes(b'data: x\n\n')
            r=run(['check','input.sse','--json','input.sse','--force'],d)
            self.assertEqual(r.returncode,2)
            self.assertEqual(p.read_bytes(),b'data: x\n\n')

if __name__=='__main__':
    unittest.main()
