"""The pstack skills in skills/ are what bin/pstack-port builds from the unmodified vendor copy."""
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PORTED = (ROOT / 'integrations/pstack/ported.txt').read_text().split()


class PstackPort(unittest.TestCase):
    def test_skills_match_a_fresh_port(self):
        result = subprocess.run([str(ROOT / 'bin/pstack-port'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_vendor_copy_carries_its_license_and_source(self):
        self.assertIn('Lauren Tan', (ROOT / 'vendor/pstack/LICENSE').read_text())
        self.assertRegex((ROOT / 'vendor/pstack/UPSTREAM').read_text(), r'commit: [0-9a-f]{40}')

    def test_every_ported_skill_points_at_the_platform_map(self):
        self.assertIn('dev-plat', PORTED)
        self.assertNotIn('poteto-mode', PORTED)
        self.assertNotIn('make-bot-ui', PORTED)
        self.assertTrue((ROOT / 'docs/pstack-platform.md').is_file())
        for name in PORTED:
            with self.subTest(skill=name):
                self.assertIn('(../../docs/pstack-platform.md)', (ROOT / 'skills' / name / 'SKILL.md').read_text())

    def test_the_setup_overlay_writes_the_file_the_loop_reads(self):
        text = (ROOT / 'skills/setup-pstack/SKILL.md').read_text()
        self.assertIn('~/.config/dev-platform/pstack-models.md', text)
        self.assertNotIn('Write `~/.cursor', text)
        self.assertIn('integrations/pstack/overlays/setup-pstack', text)
        self.assertIn('pstack-models.md', (ROOT / 'skills/loop/scripts/loop.sh').read_text())

    def test_no_ported_skill_names_a_model(self):
        product = re.compile(r'claude-opus|gpt-5|grok|\b(fable|opus|sonnet|haiku)\b|codex:')
        for name in PORTED:
            if name == 'setup-pstack':  # It sorts detected families into tiers, so it names examples.
                continue
            for path in (ROOT / 'skills' / name).rglob('*.md'):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    self.assertIsNone(product.search(path.read_text()))

    def test_every_tier_slug_a_skill_names_resolves(self):
        env = dict(os.environ, DEV_PLATFORM_PSTACK_MODELS=os.devnull)
        slugs = set()
        for name in PORTED:
            for path in (ROOT / 'skills' / name).rglob('*.md'):
                slugs |= set(re.findall(r'`((?:judgment|implementation|mechanical)(?:\.\d+)?(?:-[a-z]+)?)`', path.read_text()))
        self.assertIn('judgment.2-max', slugs)
        for slug in sorted(slugs):
            with self.subTest(slug=slug):
                subprocess.run([str(ROOT / 'bin/pstack-model'), 'resolve', slug], check=True,
                               capture_output=True, env=env)

    def test_the_setup_skill_shows_the_resolver_defaults(self):
        defaults = subprocess.run([str(ROOT / 'bin/pstack-model'), 'defaults'], capture_output=True,
                                  text=True, check=True).stdout
        self.assertIn('```\n' + defaults + '```', (ROOT / 'skills/setup-pstack/SKILL.md').read_text())


if __name__ == '__main__':
    unittest.main()
