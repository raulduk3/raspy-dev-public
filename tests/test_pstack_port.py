"""The pstack skills in skills/ are what bin/pstack-port builds from the unmodified vendor copy."""
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
