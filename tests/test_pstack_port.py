"""The pstack skills in skills/ are what bin/pstack-port builds from the unmodified vendor copy."""
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True  # The port has no file ending; loading it must leave no cache in bin/.
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

    def test_the_setup_overlay_writes_the_one_file_every_user_reads(self):
        text = (ROOT / 'skills/setup-pstack/SKILL.md').read_text()
        self.assertIn('~/dev/dev-server/etc/pstack-models.md', text)
        self.assertIn('/etc/dev-platform/pstack-models.md', text)
        self.assertIn('~/.config/dev-platform/pstack-models.md', text)  # the personal override
        self.assertNotIn('Write `~/.cursor', text)
        self.assertIn('integrations/pstack/overlays/setup-pstack', text)
        # The loop resolves through pstack-model, so it sees the system file and any override.
        loop = (ROOT / 'skills/loop/scripts/loop.sh').read_text()
        self.assertIn('"$PSTACK_MODEL" resolve', loop)
        self.assertNotIn('DEV_PLATFORM_PSTACK_MODELS=', loop)

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

    def test_a_left_out_path_stays_in_the_vendor_copy_and_no_ported_skill_holds_or_names_it(self):
        loader = SourceFileLoader('pstack_port', str(ROOT / 'bin/pstack-port'))
        port = module_from_spec(spec_from_loader(loader.name, loader))
        loader.exec_module(port)
        self.assertIn('scripts/watch-pr', port.LEFT_OUT['poteto-mode'])
        for skill, paths in port.LEFT_OUT.items():
            ported = ROOT / 'skills' / port.RENAMED.get(skill, skill)
            for rel in paths:
                with self.subTest(path=f'{skill}/{rel}'):
                    self.assertTrue((ROOT / 'vendor/pstack/skills' / skill / rel).exists())
                    self.assertFalse((ported / rel).exists())
                    for path in ported.rglob('*'):
                        if path.suffix in ('.md', '.json', '.ts', '.mjs', '.sh'):
                            self.assertNotIn(Path(rel).name, path.read_text(), path.relative_to(ROOT))

    def test_the_setup_skill_shows_the_resolver_defaults(self):
        defaults = subprocess.run([str(ROOT / 'bin/pstack-model'), 'defaults'], capture_output=True,
                                  text=True, check=True).stdout
        self.assertIn('```\n' + defaults + '```', (ROOT / 'skills/setup-pstack/SKILL.md').read_text())


if __name__ == '__main__':
    unittest.main()
