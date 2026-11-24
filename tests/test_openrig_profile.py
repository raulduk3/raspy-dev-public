"""Per-seat OpenRig account binding: the dev-workspace --account launcher path,
which asks the one resolver and checks the folder's configuration files.
Offline: no daemon, no native login, no real rig binary.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem.paths import node_platform  # noqa: E402
NODE_PLATFORM = node_platform()

LAUNCHER = ROOT / 'bin/dev-workspace'


class WorkspaceAccountLauncher(unittest.TestCase):
    """Hermetic dev-workspace --account tests using a harmless CLI fixture for `rig`,
    following tests/test_openrig_launcher.py's subprocess-with-fixture pattern, and a
    fake account state (sign-in records and usage readings) for the one resolver.
    The real rig binary, the machine's registry and its credential store are never used.
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
        self.accounts = self.root / 'accounts'
        self.accounts.mkdir()
        (self.root / 'usage').mkdir()
        self.env = dict(os.environ, DEV_WORKSPACE_RUNTIME=str(self.root), CALLS=str(self.log),
                        OL_ACCOUNTS_STATE=str(self.accounts), OL_USAGE_DIR=str(self.root / 'usage'),
                        OL_CHAT=str(self.root / 'chat'),
                        DEV_PLATFORM_ACCOUNTS_TEMPLATE=str(ROOT / 'tests/support/accounts.json'),
                        DEV_WORKSPACE_STATE_DIR=str(self.root / 'state'))

    def signed(self, account, client, verified=True):
        (self.accounts / f'{account}.{client}.json').write_text(
            json.dumps({'identity': 'owner@example.invalid', 'verified': verified, 'checked_at': int(time.time())}))

    def used(self, account, percent):
        (self.root / 'usage' / f'{account}.json').write_text(json.dumps(
            {'account': account, 'captured': int(time.time()),
             'five_hour': {'used_percentage': percent, 'resets_at': int(time.time()) + 3600}}))

    def call(self, *args):
        return subprocess.run([str(LAUNCHER), *args], env=self.env, text=True, capture_output=True)

    def records(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_account_path_refuses_on_disallowed_plan_before_touching_rig_inventory(self):
        # Not signed in: the resolver refuses the named account and substitutes no other.
        self.signed('openai-bravo', 'codex')
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-alpha')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('account plan refused: openai-alpha is not signed in', result.stderr)
        self.assertIn('never substituted', result.stderr)
        # Refused before the rig 'ps' inventory lookup and before any 'up'.
        commands = [r['args'][0] for r in self.records()]
        self.assertNotIn('ps', commands)
        self.assertFalse((self.root / 'state').exists())

    def test_an_exhausted_or_unverified_named_account_refuses(self):
        self.signed('openai-alpha', 'codex', verified=False)
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-alpha')
        self.assertEqual(result.returncode, 2)
        self.assertIn('not signed in', result.stderr)
        self.signed('openai-alpha', 'codex')
        self.used('openai-alpha', 100)
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-alpha')
        self.assertEqual(result.returncode, 2)
        self.assertIn('openai-alpha is exhausted', result.stderr)
        self.assertFalse((self.root / 'state').exists())

    def test_a_folder_whose_settings_override_the_provider_refuses_the_seat(self):
        # The check of configuration files runs for a seat too, and names the file, never its values.
        self.signed('anthropic-bravo', 'claude')
        (self.root / '.claude').mkdir()
        (self.root / '.claude/settings.json').write_text('{"env": {"ANTHROPIC_BASE_URL": "https://proxy.invalid"}}')
        result = self.call('start', 'claude', '--cwd', str(self.root), '--account', 'anthropic-bravo')
        self.assertEqual(result.returncode, 2)
        self.assertIn('overrides authentication or the provider', result.stderr)
        self.assertIn('.claude/settings.json', result.stderr)
        self.assertNotIn('proxy.invalid', result.stderr)
        self.assertNotIn('ps', [r['args'][0] for r in self.records()])

    def test_account_mismatched_runtime_is_rejected_by_argument_parsing(self):
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'anthropic-alpha')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('does not match runtime', result.stderr)
        self.assertEqual(self.records(), [])

    def test_account_path_writes_distinct_named_spec_without_config_home(self):
        self.signed('openai-alpha', 'codex')
        result = self.call('start', 'codex', '--cwd', str(self.root), '--account', 'openai-alpha')
        self.assertEqual(result.returncode, 0, result.stderr)
        spec_path = self.root / 'state' / 'development-codex-openai-alpha.yaml'
        self.assertTrue(spec_path.is_file())
        text = spec_path.read_text()
        self.assertIn('name: development-codex-openai-alpha', text)
        self.assertIn('runtime: codex', text)
        self.assertIn(f'cwd: {json.dumps(str(self.root.resolve()))}', text)
        self.assertNotIn('config_home', text)   # stock OpenRig refuses it; the seat launcher brings the account
        self.assertEqual(spec_path.stat().st_mode & 0o777, 0o600)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][1], str(spec_path))

    def test_account_path_native_default_spec_has_no_config_home(self):
        self.signed('anthropic-bravo', 'claude')
        result = self.call('start', 'claude', '--cwd', str(self.root), '--account', 'anthropic-bravo')
        self.assertEqual(result.returncode, 0, result.stderr)
        spec_path = self.root / 'state' / 'development-claude-anthropic-bravo.yaml'
        text = spec_path.read_text()
        self.assertIn('runtime: claude-code', text)   # OpenRig's own name for the Claude Code runtime
        self.assertNotIn('config_home', text)

    def test_existing_per_account_rig_is_reused_without_regenerating_spec(self):
        self.env['RIGS'] = json.dumps([{'name': 'development-codex-openai-alpha'}])
        self.signed('openai-alpha', 'codex')
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


if __name__ == '__main__':
    unittest.main()
