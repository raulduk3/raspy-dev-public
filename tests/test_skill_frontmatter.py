"""Every tracked SKILL.md frontmatter parses under a strict YAML parser.

Some agent runtimes reject a plain scalar containing ': ' that others tolerate; quote such values.
The description is the only text a client reads when deciding to load a skill, so it must be whole.
"""
import subprocess
import unittest

import yaml

from test_stability import PLATFORM


def tracked_skills():
    out = subprocess.run(['git', 'ls-files', '*SKILL.md'], cwd=PLATFORM, check=True,
                         text=True, stdout=subprocess.PIPE).stdout
    # vendor/ holds upstream copies as published; bin/pstack-port builds the installed skills from them.
    return [PLATFORM / line for line in out.splitlines() if line and not line.startswith('vendor/')]


class SkillFrontmatterTests(unittest.TestCase):
    def test_skills_are_tracked(self):
        self.assertTrue(tracked_skills())

    def test_frontmatter_parses_strictly(self):
        for path in tracked_skills():
            rel = path.relative_to(PLATFORM)
            with self.subTest(skill=str(rel)):
                lines = path.read_text().split('\n')
                self.assertEqual(lines[0], '---', f'{rel}: frontmatter must open on line 1')
                self.assertIn('---', lines[1:], f'{rel}: frontmatter is not closed')
                block = '\n'.join(lines[1:lines.index('---', 1)])
                try:
                    data = yaml.safe_load(block)
                except yaml.YAMLError as error:
                    self.fail(f'{rel}: frontmatter is not strict YAML: {error}')
                self.assertIsInstance(data, dict, rel)
                self.assertEqual(data.get('name'), path.parent.name, rel)
                self.assertIsInstance(data.get('description'), str, rel)
                self.assertTrue(data['description'].strip(), rel)
                self.assertFalse(data['description'].rstrip().endswith(('…', '...')),
                                 f'{rel}: description is truncated')


if __name__ == '__main__':
    unittest.main()
