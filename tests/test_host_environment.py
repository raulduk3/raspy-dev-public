"""Native service decisions and real CLI behavior without credentials or inference."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem.environment_service import host_plan


class HostEnvironment(unittest.TestCase):
    def setUp(self):
        # The service refuses inherited provider overrides; the desktop apps set some.
        clean = {k: v for k, v in os.environ.items() if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))}
        patcher = mock.patch.dict(os.environ, clean, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_selection_preserves_profile_and_refuses_unimplemented_rig(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder).resolve()
            data = {'bindings': {a: {'home':str(home/a)} for a in ('openai-apple','openai-gmail')}}
            rows = [dict(account=a,runtime='codex',state=state,remaining_percent=left,
                         capabilities={'codex':'authenticated'},quota=[],observed_at=100)
                    for a,state,left in [('openai-apple','ready',27),('openai-gmail','exhausted',0)]]
            plan = host_plan(rows,data,'codex','openai',home)
            self.assertTrue(plan['launch_allowed'])
            self.assertEqual(plan['selected'],'openai-apple')
            self.assertEqual(plan['cwd'],str(home))
            self.assertEqual(plan['profile']['environment'],{'CODEX_HOME':str(home/'openai-apple')})
            self.assertNotIn('container',plan)
            self.assertFalse(host_plan(rows,data,'openrig','openai',home)['launch_allowed'])
            self.assertFalse(host_plan(rows,data,'pi','openai',home)['launch_allowed'])
            self.assertFalse(host_plan(rows,data,'claude','openai',home)['launch_allowed'])
            self.assertFalse(host_plan(rows,data,'codex','openai',home,'openai-gmail')['launch_allowed'])
            rows[0].update(state='quota_unknown',remaining_percent=None)
            self.assertFalse(host_plan(rows,data,'codex','openai',home,allow_unknown=True)['launch_allowed'])
            self.assertTrue(host_plan(rows,data,'codex','openai',home,'openai-apple',True)['launch_allowed'])

    def test_cli_host_default_profile_preparation_and_no_docker_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            registry = root/'registry.json'
            def run(*args):
                return subprocess.run([str(ROOT/'bin/ai-environment'),'--registry',str(registry),*args],
                                      cwd=root,capture_output=True,text=True,timeout=15)
            status = run('status')
            self.assertEqual(status.returncode,0,status.stderr)
            self.assertEqual(len(json.loads(status.stdout)),4)
            self.assertFalse(registry.exists())
            refused = run('run','--client','codex','--provider','openai','--cwd',str(root),'--','--version')
            self.assertEqual(refused.returncode,2)
            self.assertEqual(json.loads(refused.stdout)['execution_kind'],'host')
            self.assertFalse(json.loads(refused.stdout)['launch_allowed'])
            for client, account in [('pi','openai-apple'),('pi','openai-gmail'),('codex','openai-apple'),('claude','anthropic-apple')]:
                command = ('profile','--client',client,'--account',account,'--profiles-root',str(root/'profiles'))
                planned = run(*command)
                self.assertEqual(planned.returncode,0,planned.stderr)
                profile = Path(json.loads(planned.stdout)['profile_home'])
                self.assertFalse(profile.exists())
                prepared = run(*command,'--prepare')
                self.assertEqual(prepared.returncode,0,prepared.stderr)
                value = json.loads(prepared.stdout)
                self.assertFalse(value['launch_allowed'])
                self.assertEqual(profile.stat().st_mode & 0o777,0o700)
                self.assertNotIn('HOME',value['environment'])
                self.assertFalse((profile/'auth.json').exists())
                self.assertEqual(run(*command,'--prepare').returncode,0)
                if client == 'pi':
                    observed = run(*command,'--check')
                    self.assertEqual(observed.returncode,0,observed.stderr)
                    result = json.loads(observed.stdout)
                    self.assertEqual(result['observation']['state'],'not_ready')
                    self.assertEqual(result['observation']['capability'],'unverified')
                    self.assertFalse((profile/'auth.json').exists())
                    # Pi's actual native checker accepts an OAuth type marker
                    # with expired synthetic tokens. The service must not call it verified.
                    auth = profile/'auth.json'
                    auth.write_text(json.dumps({"openai-codex":{"type":"oauth","access":"synthetic-never-sent","refresh":"synthetic-never-sent","expires":1}}))
                    before = auth.read_bytes()
                    configured = json.loads(run(*command,'--check').stdout)
                    self.assertEqual(configured['observation']['state'],'configured')
                    self.assertEqual(configured['observation']['capability'],'unverified')
                    self.assertFalse(configured['launch_allowed'])
                    self.assertEqual(auth.read_bytes(),before)
            self.assertFalse(registry.exists())
            bad = run('profile','--client','codex','--account','anthropic-apple')
            self.assertEqual(bad.returncode,2)
            resume = run('run','--client','codex','--provider','openai','--','resume','fixture')
            self.assertEqual(resume.returncode,2)


if __name__ == '__main__':
    unittest.main()
