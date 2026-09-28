"""bin/pstack-model turns a pstack role or tier slug into a model and effort for one runtime."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PstackModel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / 'pstack-models.md'
        self.addCleanup(self.tmp.cleanup)

    def resolve(self, *args, expected=0):
        env = dict(os.environ, DEV_PLATFORM_PSTACK_MODELS=str(self.file))
        result = subprocess.run([str(ROOT / 'bin/pstack-model'), 'resolve', *args],
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return [tuple(line.split('\t')) for line in result.stdout.splitlines()]

    def test_without_a_file_a_role_takes_its_default_tier(self):
        self.assertEqual(self.resolve('judgment and prose'), [('fable', 'max')])
        self.assertEqual(self.resolve('swarm workers'), [('sonnet', 'xhigh')])
        self.assertEqual(self.resolve('mechanical'), [('haiku', '')])

    def test_a_panel_spreads_across_families(self):
        self.assertEqual(self.resolve('arena runners', '--all'),
                         [('fable', 'max'), ('codex:gpt-5.6-sol', 'max'), ('sonnet', 'xhigh')])
        # Claude cannot run the Codex family, so the second judgment slot moves to the next family.
        self.assertEqual(self.resolve('arena runners', '--all', '--runtime', 'claude'),
                         [('fable', 'max'), ('opus', 'max'), ('sonnet', 'xhigh')])

    def test_codex_takes_its_own_families_and_caps_effort(self):
        self.assertEqual(self.resolve('reflect tooling', '--runtime', 'codex'), [('gpt-5.6-sol', 'xhigh')])

    def test_the_owners_tiers_and_roles_win(self):
        self.file.write_text('# budget: small (medium)\ntier judgment: opus\n'
                             'judgment and prose: judgment-medium\nhow explorer: sonnet-low\n')
        self.assertEqual(self.resolve('judgment and prose'), [('opus', 'medium')])
        self.assertEqual(self.resolve('how explorer'), [('sonnet', 'low')])
        self.assertEqual(self.resolve('hardest tasks'), [('opus', 'max')])

    def test_aliases_inherit_unless_refused(self):
        self.file.write_text('judgment and prose: inherit-parent\n')
        self.assertEqual(self.resolve('judgment and prose'), [('inherit', '')])
        # With nothing runnable on the owner's line, the default line decides.
        self.assertEqual(self.resolve('judgment and prose', '--no-inherit', '--runtime', 'claude'), [('fable', 'max')])

    def test_nothing_runnable_exits_one(self):
        self.assertEqual(self.resolve('codex:gpt-5.6-sol-high', '--runtime', 'claude', expected=1), [])


if __name__ == '__main__':
    unittest.main()
