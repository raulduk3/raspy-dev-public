"""Per-seat OpenRig account binding: host_plan's openrig branch, and the
dev-workspace --account launcher path. Offline: no daemon, no docker, no
native login, no real rig binary.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem.environment_service import host_plan

LAUNCHER = ROOT / 'bin/dev-workspace'


def binding(home, email, native_default=False):
    return {'home': str(home), 'expected_email': email, 'native_default': native_default}


def row(account, runtime, state, remaining_percent=None, quota=None):
    return dict(account=account, runtime=runtime, state=state, observed_at=1,
               remaining_percent=remaining_percent, quota=quota,
               capabilities={runtime: 'authenticated' if state != 'unverified' else 'unverified'})


class OpenRigPlan(unittest.TestCase):
    def setUp(self):
        # The service refuses inherited provider overrides; strip them the
        # same way tests/test_host_environment.py does in its own setUp.
        clean = {k: v for k, v in os.environ.items() if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))}
        patcher = mock.patch.dict(os.environ, clean, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_native_default_binding_emits_no_config_home(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder).resolve() / '.claude'
            data = {'bindings': {'anthropic-gmail': binding(home, 'user@example.com', native_default=True)}}
            rows = [row('anthropic-gmail', 'claude', 'ready', 50)]
            plan = host_plan(rows, data, 'openrig', 'anthropic', Path(folder).resolve(),
                             preferred='anthropic-gmail', allow_unknown=True)
            self.assertTrue(plan['launch_allowed'], plan)
            self.assertEqual(plan['selected'], 'anthropic-gmail')
            self.assertNotIn('config_home', plan)
            self.assertNotIn('config_home', plan['member'])
            self.assertEqual(plan['member']['runtime'], 'claude-code')
            self.assertTrue(plan['profile']['native_default'])
            self.assertEqual(plan['profile']['environment'], {})

    def test_isolated_binding_emits_absolute_profile_home(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            home = root / 'accounts' / 'anthropic-apple'
            data = {'bindings': {'anthropic-apple': binding(home, 'other@example.com')}}
            rows = [row('anthropic-apple', 'claude', 'ready', 80)]
            plan = host_plan(rows, data, 'openrig', 'anthropic', root,
                             preferred='anthropic-apple', allow_unknown=True)
            self.assertTrue(plan['launch_allowed'], plan)
            self.assertEqual(plan['config_home'], str(home))
            self.assertTrue(Path(plan['config_home']).is_absolute())
            self.assertEqual(plan['member'], {'runtime': 'claude-code', 'cwd': str(root),
                                              'config_home': str(home)})
            self.assertFalse(plan['profile']['native_default'])

    def test_openai_isolated_binding_maps_codex_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            home = root / 'accounts' / 'openai-apple'
            data = {'bindings': {'openai-apple': binding(home, 'codex@example.com')}}
            rows = [row('openai-apple', 'codex', 'ready', 10)]
            plan = host_plan(rows, data, 'openrig', 'openai', root,
                             preferred='openai-apple', allow_unknown=True)
            self.assertTrue(plan['launch_allowed'], plan)
            self.assertEqual(plan['member']['runtime'], 'codex')
            self.assertEqual(plan['member']['config_home'], str(home))

    def test_unverified_account_refuses_openrig_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            data = {'bindings': {'anthropic-apple': binding(root / 'home', 'user@example.com')}}
            rows = [row('anthropic-apple', 'claude', 'unverified')]
            plan = host_plan(rows, data, 'openrig', 'anthropic', root, preferred='anthropic-apple')
            self.assertFalse(plan['launch_allowed'])
            self.assertIsNone(plan['selected'])
            self.assertNotIn('member', plan)

    def test_exhausted_account_refuses_openrig_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            data = {'bindings': {'openai-apple': binding(root / 'home', 'user@example.com')}}
            rows = [row('openai-apple', 'codex', 'exhausted', 0)]
            plan = host_plan(rows, data, 'openrig', 'openai', root, preferred='openai-apple')
            self.assertFalse(plan['launch_allowed'])
            self.assertIsNone(plan['selected'])

    def test_unenrolled_binding_refuses_even_when_ready(self):
        # A "ready" row whose registry binding never recorded an expected
        # identity cannot be fingerprinted for resume/fork revalidation, so
        # it is not "verified and eligible" for an OpenRig seat, even though
        # the same row is enough for a direct codex/claude launch.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            data = {'bindings': {'openai-apple': {'home': str(root / 'home')}}}
            rows = [row('openai-apple', 'codex', 'ready', 50)]
            direct = host_plan(rows, data, 'codex', 'openai', root, preferred='openai-apple')
            self.assertTrue(direct['launch_allowed'])
            openrig = host_plan(rows, data, 'openrig', 'openai', root, preferred='openai-apple')
            self.assertFalse(openrig['launch_allowed'])
            self.assertNotIn('member', openrig)


class WorkspaceAccountLauncher(unittest.TestCase):
    """Hermetic dev-workspace --account tests using a harmless CLI fixture for
    both `rig` and the account service, following tests/test_openrig_launcher.py's
    subprocess-with-fixture pattern. The real rig binary and real ai-environment
    probing are never invoked.
    """
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log = self.root / 'calls.jsonl'
        rig = self.root / 'app/node_modules/.bin/rig'
        rig.parent.mkdir(parents=True)
        node = self.root / 'node-v24.14.0-darwin-arm64/bin/node'
        node.parent.mkdir(parents=True)
        node.touch()
        rig.write_text('''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as f:
    f.write(json.dumps({'args':a})+'\\n')
if a == ['--version']: print('0.5.14 (cc75efdd)')
elif a == ['daemon', 'status']: print(os.environ.get('DAEMON_STATE', 'Daemon running on port 4400 (pid 1)'))
elif a == ['ps', '--json', '--include-archived']: print(os.environ.get('RIGS', '[]'))
elif a[0] == 'up' and '--plan' in a: pass
''')
        rig.chmod(0o755)
        self.service = self.root / 'ai-environment-fixture'
        self.service.write_text('''#!/usr/bin/env python3
import json, os, sys
print(os.environ.get('ACCOUNT_PLAN', json.dumps({'launch_allowed': False, 'reason': 'fixture default refusal'})))
''')
        self.service.chmod(0o755)
        self.env = dict(os.environ, DEV_WORKSPACE_RUNTIME=str(self.root), CALLS=str(self.log),
                        DEV_WORKSPACE_ACCOUNT_SERVICE=str(self.service),
                        DEV_WORKSPACE_STATE_DIR=str(self.root / 'state'),
                        DEV_PLATFORM_PERSONAL=str(self.root / 'personal.conf'))

    def call(self, *args):
        return subprocess.run([str(LAUNCHER), *args], env=self.env, text=True, capture_output=True)

    def records(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_account_path_refuses_on_disallowed_plan_before_touching_rig_inventory(self):
        self.env['ACCOUNT_PLAN'] = json.dumps({'launch_allowed': False, 'reason': 'no eligible environment'})
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-apple')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no eligible environment', result.stderr)
        # Refused before the rig 'ps' inventory lookup and before any 'up'.
        commands = [r['args'][0] for r in self.records()]
        self.assertNotIn('ps', commands)
        self.assertFalse((self.root / 'state').exists())

    def test_account_mismatched_runtime_is_rejected_by_argument_parsing(self):
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'anthropic-apple')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('does not match runtime', result.stderr)
        self.assertEqual(self.records(), [])

    def test_account_path_writes_distinct_named_spec_with_config_home(self):
        member = {'runtime': 'codex', 'cwd': str(self.root), 'config_home': str(self.root / 'accounts/openai-apple')}
        self.env['ACCOUNT_PLAN'] = json.dumps({'launch_allowed': True, 'selected': 'openai-apple', 'member': member})
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-apple')
        self.assertEqual(result.returncode, 0, result.stderr)
        spec_path = self.root / 'state' / 'development-codex-openai-apple.yaml'
        self.assertTrue(spec_path.is_file())
        text = spec_path.read_text()
        self.assertIn('name: development-codex-openai-apple', text)
        self.assertIn('runtime: codex', text)
        self.assertIn(json.dumps(str(self.root / 'accounts/openai-apple')), text)
        self.assertEqual(spec_path.stat().st_mode & 0o777, 0o600)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][1], str(spec_path))

    def test_account_path_native_default_spec_has_no_config_home(self):
        member = {'runtime': 'claude-code', 'cwd': str(self.root)}
        self.env['ACCOUNT_PLAN'] = json.dumps({'launch_allowed': True, 'selected': 'anthropic-gmail', 'member': member})
        result = self.call('start', 'claude', '--cwd', str(self.root), '--account', 'anthropic-gmail')
        self.assertEqual(result.returncode, 0, result.stderr)
        spec_path = self.root / 'state' / 'development-claude-anthropic-gmail.yaml'
        text = spec_path.read_text()
        self.assertNotIn('config_home', text)

    def test_existing_per_account_rig_is_reused_without_regenerating_spec(self):
        self.env['RIGS'] = json.dumps([{'name': 'development-codex-openai-apple'}])
        member = {'runtime': 'codex', 'cwd': str(self.root), 'config_home': str(self.root / 'accounts/openai-apple')}
        self.env['ACCOUNT_PLAN'] = json.dumps({'launch_allowed': True, 'selected': 'openai-apple', 'member': member})
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-apple')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'state').exists())
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(commands, [['up', 'development-codex-openai-apple', '--existing', '--plan'],
                                    ['up', 'development-codex-openai-apple', '--existing']])

    def test_plan_without_account_is_unaffected(self):
        result = self.call('plan', 'codex', '--cwd', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'state').exists())
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertTrue(commands[0][1].endswith('integrations/openrig/codex.yaml'))


class AiEnvironmentRunRefusesOpenrig(unittest.TestCase):
    """ai-environment run must not exec the bare native client for an
    'openrig' client even once host_plan allows an openrig plan: OpenRig
    seats are launched through dev-workspace --account, never a bare exec.
    """
    def test_run_refuses_openrig_client(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            result = subprocess.run([str(ROOT / 'bin/ai-environment'), '--registry', str(root / 'registry.json'),
                                     'run', '--client', 'openrig', '--provider', 'openai', '--cwd', str(root), '--'],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertIn('dev-workspace --account', result.stderr)


if __name__ == '__main__':
    unittest.main()
