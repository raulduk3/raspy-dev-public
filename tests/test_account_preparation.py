import json
from pathlib import Path
import subprocess
import tempfile
import unittest

CLI=Path(__file__).resolve().parents[1]/'bin/ai-account'

class Preparation(unittest.TestCase):
    def test_independent_profiles_and_existing_config_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            registry=root/'accounts.json'
            registry.write_text('{"version":1,"selected":"openai-apple","bindings":{}}')
            original=registry.read_bytes()
            def run(name):
                return subprocess.run([str(CLI),'--registry',str(registry),'prepare-login',name,'--profiles-root',str(root/'profiles')],capture_output=True,text=True)
            paths=[]
            for name in ('openai-apple','openai-gmail','anthropic-apple','anthropic-gmail'):
                result=run(name);self.assertEqual(result.returncode,0,result.stderr)
                home=Path(json.loads(result.stdout)['native_home']);paths.append(home)
                self.assertEqual(home.stat().st_mode & 0o777,0o700)
                self.assertFalse((home/'auth.json').exists())
                self.assertFalse((home/'.credentials.json').exists())
                self.assertEqual(run(name).returncode,0)
            self.assertEqual(len(set(paths)),4)
            config=paths[0]/'config.toml'
            self.assertEqual(config.read_text(),'cli_auth_credentials_store = "file"\n')
            config.write_text('preserve this custom configuration\n')
            self.assertNotEqual(run('openai-apple').returncode,0)
            self.assertEqual(config.read_text(),'preserve this custom configuration\n')
            self.assertEqual(registry.read_bytes(),original)
