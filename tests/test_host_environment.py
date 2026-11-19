"""ai-environment's host plans come from the one resolver; no per-account homes, no Docker fallback."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
sys.path.insert(0, str(ROOT / 'tests'))
from ai_ecosystem.environment_service import host_plan  # noqa: E402
from test_registry import Fake  # noqa: E402


class HostEnvironment(Fake):
    def test_plan_takes_the_resolvers_choice_and_carries_no_credential_or_home(self):
        self.signed('openai-bravo', 'codex')
        self.signed('openai-alpha', 'codex')
        self.used('openai-bravo', 100)
        plan = host_plan([], None, 'codex', 'openai', self.tmp)
        self.assertTrue(plan['launch_allowed'])
        self.assertEqual(plan['selected'], 'openai-alpha')
        self.assertEqual(plan['rotated_from'], None)
        self.assertNotIn('profile', plan)
        self.assertNotIn('container', plan)
        self.assertIn('launcher', plan['credential'])
        self.assertFalse(host_plan([], None, 'claude', 'openai', self.tmp)['launch_allowed'])
        refused = host_plan([], None, 'codex', 'openai', self.tmp, 'openai-bravo')
        self.assertFalse(refused['launch_allowed'])
        self.assertIn('never substituted', refused['reason'])

    def test_project_override_of_the_provider_is_refused(self):
        self.signed('anthropic-bravo', 'claude')
        (self.tmp / '.claude').mkdir()
        (self.tmp / '.claude/settings.json').write_text('{"env": {"ANTHROPIC_BASE_URL": "x"}}')
        plan = host_plan([], None, 'claude', 'anthropic', self.tmp)
        self.assertFalse(plan['launch_allowed'])
        self.assertIn('overrides authentication', plan['reason'])

    def test_cli_has_no_per_account_profile_and_no_docker_fallback(self):
        def run(*args):
            return subprocess.run([str(ROOT / 'bin/ai-environment'), *args], capture_output=True, text=True)
        refused = run('profile', '--client', 'codex', '--account', 'openai-alpha', '--prepare')
        self.assertEqual(refused.returncode, 2)
        self.assertIn('ol-login openai-alpha codex', refused.stderr)
        self.assertEqual(run('--root', str(self.tmp), 'status').returncode, 2)
        plan = run('plan', '--client', 'codex', '--provider', 'openai', '--cwd', str(self.tmp))
        self.assertEqual(plan.returncode, 2)
        self.assertIn('no openai account left', json.loads(plan.stdout)['reason'])


if __name__ == '__main__':
    unittest.main()
