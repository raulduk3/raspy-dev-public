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
from ai_ecosystem.paths import node_platform  # noqa: E402
from ai_ecosystem.environment_service import host_plan  # noqa: E402
NODE_PLATFORM = node_platform()
sys.path.insert(0, str(ROOT / 'tests'))
from test_registry import Fake  # noqa: E402

LAUNCHER = ROOT / 'bin/dev-workspace'


class OpenRigPlan(Fake):
    """An OpenRig plan is the resolver's choice plus a member fragment; the seat gets its
    credential from the launcher, so no config_home is ever emitted."""

    def test_signed_in_account_emits_member_without_config_home(self):
        self.signed('anthropic-bravo', 'claude')
        plan = host_plan([], None, 'openrig', 'anthropic', self.tmp)
        self.assertTrue(plan['launch_allowed'])
        self.assertEqual(plan['selected'], 'anthropic-bravo')
        self.assertEqual(plan['member'], {'runtime': 'claude-code', 'cwd': str(self.tmp)})
        self.assertNotIn('config_home', plan)

    def test_openai_maps_codex_runtime(self):
        self.signed('openai-alpha', 'codex')
        plan = host_plan([], None, 'openrig', 'openai', self.tmp, 'openai-alpha')
        self.assertEqual(plan['member']['runtime'], 'codex')

    def test_unverified_or_exhausted_account_refuses(self):
        self.signed('anthropic-bravo', 'claude', verified=False)
        self.assertFalse(host_plan([], None, 'openrig', 'anthropic', self.tmp)['launch_allowed'])
        self.signed('anthropic-bravo', 'claude')
        self.used('anthropic-bravo', 100)
        self.assertFalse(host_plan([], None, 'openrig', 'anthropic', self.tmp, 'anthropic-bravo')['launch_allowed'])


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
        node = self.root / f'node-v24.14.0-{NODE_PLATFORM}/bin/node'
        node.parent.mkdir(parents=True)
        node.touch()
        rig.write_text('''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as f:
    f.write(json.dumps({'args':a})+'\\n')
if a == ['--version']: print('0.6.10 (3001cc43)')
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
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-alpha')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no eligible environment', result.stderr)
        # Refused before the rig 'ps' inventory lookup and before any 'up'.
        commands = [r['args'][0] for r in self.records()]
        self.assertNotIn('ps', commands)
        self.assertFalse((self.root / 'state').exists())

    def test_account_mismatched_runtime_is_rejected_by_argument_parsing(self):
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'anthropic-alpha')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('does not match runtime', result.stderr)
        self.assertEqual(self.records(), [])

    def test_account_path_writes_distinct_named_spec_without_config_home(self):
        member = {'runtime': 'codex', 'cwd': str(self.root), 'config_home': str(self.root / 'accounts/openai-alpha')}
        self.env['ACCOUNT_PLAN'] = json.dumps({'launch_allowed': True, 'selected': 'openai-alpha', 'member': member})
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-alpha')
        self.assertEqual(result.returncode, 0, result.stderr)
        spec_path = self.root / 'state' / 'development-codex-openai-alpha.yaml'
        self.assertTrue(spec_path.is_file())
        text = spec_path.read_text()
        self.assertIn('name: development-codex-openai-alpha', text)
        self.assertIn('runtime: codex', text)
        self.assertNotIn('config_home', text)   # stock OpenRig refuses it; the seat launcher brings the account
        self.assertEqual(spec_path.stat().st_mode & 0o777, 0o600)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][1], str(spec_path))

    def test_account_path_native_default_spec_has_no_config_home(self):
        member = {'runtime': 'claude-code', 'cwd': str(self.root)}
        self.env['ACCOUNT_PLAN'] = json.dumps({'launch_allowed': True, 'selected': 'anthropic-bravo', 'member': member})
        result = self.call('start', 'claude', '--cwd', str(self.root), '--account', 'anthropic-bravo')
        self.assertEqual(result.returncode, 0, result.stderr)
        spec_path = self.root / 'state' / 'development-claude-anthropic-bravo.yaml'
        text = spec_path.read_text()
        self.assertNotIn('config_home', text)

    def test_existing_per_account_rig_is_reused_without_regenerating_spec(self):
        self.env['RIGS'] = json.dumps([{'name': 'development-codex-openai-alpha'}])
        member = {'runtime': 'codex', 'cwd': str(self.root), 'config_home': str(self.root / 'accounts/openai-alpha')}
        self.env['ACCOUNT_PLAN'] = json.dumps({'launch_allowed': True, 'selected': 'openai-alpha', 'member': member})
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-alpha')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'state').exists())
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(commands, [['up', 'development-codex-openai-alpha', '--existing', '--plan'],
                                    ['up', 'development-codex-openai-alpha', '--existing']])

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
