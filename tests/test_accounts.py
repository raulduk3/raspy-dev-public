"""Exercise native process boundaries with hermetic protocol peers, never paid inference."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/ai-account'


class Accounts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='account-boundary-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.native = self.root / 'native home'
        self.native.mkdir()
        self.home = self.root / 'home'
        self.home.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.registry = self.root / 'accounts.json'
        self.log = self.root / 'calls.jsonl'
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        ACCOUNT_TEST_LOG=str(self.log), TEST_EMAIL='owner@example.invalid')
        for key in list(self.env):
            if key.startswith(('ANTHROPIC_', 'CLAUDE_CODE_')) or key in ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN', 'OPENAI_IDENTITY_TOKEN_FILE', 'OPENAI_FEDERATION_RULE_ID'):
                del self.env[key]
        for runtime in ('claude', 'codex'):
            tool = self.bin / runtime
            tool.write_text('''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['ACCOUNT_TEST_LOG'],'a') as f:
 f.write(json.dumps({'argv':sys.argv,'claude':os.getenv('CLAUDE_CONFIG_DIR'),'codex':os.getenv('CODEX_HOME')})+'\\n')
if 'app-server' in sys.argv:
 for line in sys.stdin:
  r=json.loads(line)
  if 'id' not in r: continue
  method=r['method']
  if method=='account/read':
   assert r['params']['refreshToken'] is False
   result={'account':{'type':'chatgpt','email':os.environ['TEST_EMAIL'],'planType':'pro','secret':'NEVER_SHOW'}}
  elif method=='account/rateLimits/read':
   result={'rateLimits':{'primary':{'usedPercent':25,'windowDurationMins':300,'resetsAt':123,'secret':'NEVER_SHOW'}}}
   if os.getenv('TEST_MULTI_POOLS'):
    result={'rateLimitsByLimitId':{'codex':result['rateLimits'],'review':{'primary':{'usedPercent':3,'windowDurationMins':10080,'resetsAt':456}},'bad\\nlabel':{'secondary':{'usedPercent':7}}}}
  else: result={}
  print(json.dumps({'id':r['id'],'result':result}),flush=True)
elif sys.argv[1:]==['auth','status','--json']:
 print(json.dumps({'loggedIn':True,'authMethod':'claude.ai','apiProvider':os.getenv('TEST_PROVIDER','firstParty'),'email':os.environ['TEST_EMAIL'],'subscriptionType':'max','secret':'NEVER_SHOW'}))
else:
 print('launched')
''')
            tool.chmod(0o700)

    def cli(self, *arguments, ok=True):
        p = subprocess.run([str(CLI), '--registry', str(self.registry), *map(str, arguments)],
                           cwd=self.root, env=self.env, text=True, capture_output=True, timeout=25)
        self.assertNotIn('NEVER_SHOW', p.stdout + p.stderr)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def bind(self, account='anthropic-gmail'):
        return self.cli('bind', account, '--home', self.native, '--expected-email', 'owner@example.invalid')

    def test_monitor_is_ordered_unknown_not_zero_and_does_not_create_state(self):
        d = json.loads(self.cli('monitor').stdout)
        self.assertEqual([a['id'] for a in d['accounts']], ['anthropic-gmail', 'anthropic-apple', 'openai-gmail', 'openai-apple', 'zai'])
        self.assertTrue(all(a['quota'] is None and a['identity'] == 'unverified' for a in d['accounts']))
        self.assertFalse(self.registry.exists())
        self.assertFalse(self.log.exists())

    def test_native_terminal_table_preserves_unknown_and_reports_observation(self):
        output = self.cli('monitor', '--table').stdout
        self.assertLess(output.index('anthropic-gmail'), output.index('openai-gmail'))
        self.assertIn('Billing/renewal: unknown', output)
        self.assertIn('Observed:', output)
        self.assertNotIn('0%', output)
        self.bind('openai-gmail')
        output = self.cli('status', 'openai-gmail', '--table').stdout
        self.assertIn('25%', output)
        self.assertIn('300m', output)
        self.assertIn('verified', output)
        self.cli('select', 'openai-gmail')
        self.assertIn('* openai-gmail', self.cli('monitor', '--table').stdout)

    def test_cached_claude_identity_cannot_verify_alternate_provider(self):
        self.env['TEST_PROVIDER'] = 'thirdParty'
        self.assertNotEqual(self.cli('bind', 'anthropic-gmail', '--home', self.native,
                                   '--expected-email', 'owner@example.invalid', ok=False).returncode, 0)
        self.assertFalse(self.registry.exists())

    def test_real_exec_preserves_literal_arguments_and_home_boundary(self):
        sentinel = self.native / 'auth.json'
        sentinel.write_text('unchanged credential sentinel')
        self.bind()
        self.cli('select', 'anthropic-gmail')
        hostile = 'literal $(touch unwanted) ; `id`'
        result = self.cli('run', '--', '--name', hostile, '-p', 'hello')
        self.assertEqual(result.stdout.strip(), 'launched')
        last = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(last['argv'][1:], ['--name', hostile, '-p', 'hello'])
        self.assertEqual(last['claude'], str(self.native.resolve()))
        self.assertIsNone(last['codex'])
        self.assertFalse((self.root / 'unwanted').exists())
        self.assertEqual(sentinel.read_text(), 'unchanged credential sentinel')
        self.assertEqual(self.registry.stat().st_mode & 0o777, 0o600)

    def test_wrong_identity_never_changes_binding_or_selection(self):
        self.bind()
        before = self.registry.read_bytes()
        self.env['TEST_EMAIL'] = 'other@example.invalid'
        self.assertNotEqual(self.cli('select', 'anthropic-gmail', ok=False).returncode, 0)
        self.assertNotEqual(self.cli('run', '--account', 'anthropic-gmail', '--', '-p', 'hello', ok=False).returncode, 0)
        self.assertEqual(self.registry.read_bytes(), before)

    def test_shared_home_cannot_be_two_identities(self):
        self.bind()
        self.assertNotEqual(self.cli('bind', 'anthropic-apple', '--home', self.native,
                                   '--expected-email', 'owner@example.invalid', ok=False).returncode, 0)

    def test_native_default_is_explicit_and_does_not_set_profile_environment(self):
        self.assertNotEqual(self.cli('bind', 'anthropic-gmail', '--home', self.native, '--native-default',
                                   '--expected-email', 'owner@example.invalid', ok=False).returncode, 0)
        default = self.home / '.claude'
        default.mkdir()
        self.cli('bind', 'anthropic-gmail', '--home', default, '--native-default',
                 '--expected-email', 'owner@example.invalid')
        self.cli('run', '--account', 'anthropic-gmail', '--', '-p', 'hello')
        last = json.loads(self.log.read_text().splitlines()[-1])
        self.assertIsNone(last['claude'])
        self.assertIsNone(last['codex'])

    def test_inherited_auth_and_project_overrides_fail_without_leaking(self):
        self.bind()
        self.env['ANTHROPIC_API_KEY'] = 'NEVER_SHOW'
        self.assertNotEqual(self.cli('run', '--account', 'anthropic-gmail', ok=False).returncode, 0)
        del self.env['ANTHROPIC_API_KEY']
        project = self.root / '.claude'
        project.mkdir()
        (project / 'settings.json').write_text('{"env":{"ANTHROPIC_BASE_URL":"NEVER_SHOW"}}')
        self.assertNotEqual(self.cli('run', '--account', 'anthropic-gmail', ok=False).returncode, 0)

    def test_codex_native_read_protocol_whitelists_usage_without_creating_turn(self):
        self.bind('openai-gmail')
        data = json.loads(self.cli('status', 'openai-gmail').stdout)
        self.assertEqual(data['identity'], 'verified')
        self.assertEqual(data['quota'], [{'limit_id': 'codex', 'primary': {'usedPercent': 25, 'windowDurationMins': 300, 'resetsAt': 123}}])
        calls = [json.loads(s) for s in self.log.read_text().splitlines()]
        self.assertTrue(all(c['argv'][1:] == ['app-server'] for c in calls))
        self.assertTrue(all(c['codex'] == str(self.native.resolve()) and c['claude'] is None for c in calls))

    def test_inherited_codex_tokens_and_workload_identity_cannot_override_profile(self):
        self.bind('openai-gmail')
        before = self.log.read_bytes()
        for key in ('CODEX_ACCESS_TOKEN', 'OPENAI_IDENTITY_TOKEN_FILE', 'OPENAI_FEDERATION_RULE_ID'):
            self.env[key] = 'NEVER_SHOW'
            result = self.cli('run', '--account', 'openai-gmail', '--', 'exec', 'hello', ok=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.log.read_bytes(), before, 'no native probe or turn may start')
            del self.env[key]

    def test_monitor_keeps_independent_quota_pool_and_window_labels(self):
        self.bind('openai-gmail')
        self.env['TEST_MULTI_POOLS'] = '1'
        data = json.loads(self.cli('status', 'openai-gmail').stdout)
        self.assertEqual([item['limit_id'] for item in data['quota']], ['codex', 'review', 'pool-3'])
        output = self.cli('status', 'openai-gmail', '--table').stdout
        self.assertIn('codex/primary: 25% / 300m', output)
        self.assertIn('review/primary: 3% / week', output)
        self.assertIn('pool-3/secondary: 7% / unknown window', output)
        self.assertNotIn('bad', output)

    def test_login_plan_does_not_launch_or_create_native_home(self):
        data = json.loads(self.cli('login-plan', 'anthropic-apple').stdout)
        self.assertEqual(data['native_command'], ['claude', 'auth', 'login'])
        self.assertFalse(Path(data['native_home']).exists())
        self.assertFalse(self.log.exists())
        self.assertIsNone(json.loads(self.cli('login-plan', 'zai').stdout)['native_command'])

    def test_run_cannot_reconfigure_account_or_fall_back(self):
        self.bind()
        self.assertNotEqual(self.cli('run', '--', '-p', 'hello', ok=False).returncode, 0)
        for args in [('--config', 'model_provider="other"'), ('--settings=x',), ('--oss',), ('auth', 'logout')]:
            self.assertNotEqual(self.cli('run', '--account', 'anthropic-gmail', '--', *args, ok=False).returncode, 0)

    def test_codex_cannot_change_validated_directory_or_use_attached_profile(self):
        self.bind('openai-gmail')
        before = self.log.read_text()
        for args in [('-C', '/elsewhere'), ('--cd=/elsewhere',), ('-C/elsewhere',), ('-pOTHER',)]:
            self.assertNotEqual(self.cli('run', '--account', 'openai-gmail', '--', *args, ok=False).returncode, 0)
        self.assertEqual(self.log.read_text(), before)


if __name__ == '__main__':
    unittest.main()
