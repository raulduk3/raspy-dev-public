"""ai-guardrails equips a home without touching what the owner put there, and the formatter hook."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import guardrails  # noqa: E402


class Guardrails(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / 'home'
        self.home.mkdir()
        # A release that looks like /opt/dev-platform/current: the real skills and rules.
        self.release = self.tmp / 'opt/dev-platform/current'
        self.release.mkdir(parents=True)
        for part in ('skills', 'hooks', 'agents', 'integrations'):
            (self.release / part).symlink_to(ROOT / part)

    def install(self, role=None):
        return guardrails.install(self.home, self.release, role)

    def test_every_global_prompt_gets_the_naming_rule(self):
        (self.home / '.claude-accounts/acme').mkdir(parents=True)
        (self.home / '.claude-accounts/acme/settings.json').write_text('{}')
        (self.home / '.pi/agent').mkdir(parents=True)
        self.install()
        for rel in ('.claude/CLAUDE.md', '.claude-accounts/acme/CLAUDE.md', '.codex/AGENTS.md',
                    '.pi/agent/APPEND_SYSTEM.md'):
            self.assertIn('purpose(area): Description #ref', (self.home / rel).read_text(), rel)
        self.assertEqual(guardrails.status(self.home, self.release), [])
        (self.home / '.pi/agent/APPEND_SYSTEM.md').write_text('mine\n')
        self.assertIn('no session-entry block', ' '.join(guardrails.status(self.home, self.release)))

    def test_a_fresh_home_is_fully_equipped(self):
        self.assertEqual(self.install(), [])
        self.assertEqual(guardrails.status(self.home, self.release), [])
        develop = self.home / '.claude/skills/develop'
        self.assertEqual(os.readlink(develop), str(self.release / 'skills/develop'))
        self.assertTrue((self.home / '.agents/skills/develop/SKILL.md').is_file())
        self.assertEqual(len(list((self.home / '.codex/skills').iterdir())),
                         len(guardrails.wanted_skills(self.release)))
        self.assertIn(f'@{self.release}/skills/develop/SKILL.md', (self.home / '.claude/CLAUDE.md').read_text())
        self.assertIn('hygiene.py', (self.home / '.codex/AGENTS.md').read_text())
        self.assertTrue((self.home / '.codex/config.toml').read_text().startswith('sandbox_mode = "workspace-write"'))

    def test_running_twice_changes_nothing(self):
        self.install()
        before = {p: (p.is_symlink() and os.readlink(p)) or p.read_bytes()
                  for p in self.home.rglob('*') if p.is_symlink() or p.is_file()}
        self.install()
        after = {p: (p.is_symlink() and os.readlink(p)) or p.read_bytes()
                 for p in self.home.rglob('*') if p.is_symlink() or p.is_file()}
        self.assertEqual(before, after)

    def test_the_owners_own_things_are_kept(self):
        (self.home / '.claude/skills/develop').mkdir(parents=True)            # a folder of its own
        (self.home / '.claude/skills/mine').mkdir()
        (self.home / '.codex').mkdir()
        (self.home / '.codex/config.toml').write_text('model = "x"\n[profiles.a]\nsandbox_mode = "read-only"\n')
        (self.home / '.claude/CLAUDE.md').write_text('My own line.\n')
        notes = self.install()
        self.assertTrue(any('develop: a folder of its own' in n for n in notes))
        self.assertFalse((self.home / '.claude/skills/develop').is_symlink())
        self.assertTrue((self.home / '.claude/skills/mine').is_dir())
        config = (self.home / '.codex/config.toml').read_text()
        self.assertTrue(config.startswith('sandbox_mode = "workspace-write"\nmodel = "x"\n[profiles.a]'))
        claude = (self.home / '.claude/CLAUDE.md').read_text()
        self.assertTrue(claude.startswith('My own line.\n'))
        self.install()
        self.assertEqual((self.home / '.claude/CLAUDE.md').read_text().count(guardrails.BEGIN), 1)

    def test_a_config_that_names_a_sandbox_is_left_as_it_is(self):
        (self.home / '.codex').mkdir()
        (self.home / '.codex/config.toml').write_text('sandbox_mode = "read-only"\n')
        self.install()
        self.assertEqual((self.home / '.codex/config.toml').read_text(), 'sandbox_mode = "read-only"\n')

    def test_only_engineer_gets_its_engineering_skill(self):
        self.install('engineer')
        self.assertTrue((self.home / '.claude/skills/engineering/SKILL.md').is_file())
        self.install('assistant')
        self.assertFalse((self.home / '.claude/skills/engineering').exists())
        self.assertTrue((self.home / '.claude/skills/develop').is_symlink())

    def test_a_role_home_holds_its_table_row_and_the_session_entry(self):
        table = json.loads((ROOT / 'agents/skills.json').read_text())
        self.assertEqual(set(table), {'assistant', 'ops', 'engineer'})
        for role, rows in table.items():
            self.assertEqual(self.install(role), [])
            self.assertEqual(guardrails.status(self.home, self.release, role), [])
            for rel in ('.claude/skills', '.codex/skills', '.agents/skills'):
                self.assertEqual(sorted(p.name for p in (self.home / rel).iterdir()),
                                 sorted({'develop', *(Path(r).name for r in rows)}), (role, rel))
        # The owner's home, installed after a role's, has every platform skill again.
        self.install()
        self.assertEqual(len(list((self.home / '.claude/skills').iterdir())),
                         len(list((ROOT / 'skills').glob('*/SKILL.md'))) + len(list((ROOT / 'agents').glob('*/skills/*/SKILL.md'))))

    def test_stale_platform_links_go_and_foreign_links_stay(self):
        base = self.home / '.claude/skills'
        base.mkdir(parents=True)
        (base / 'gone').symlink_to('/Users/x/Dev/dev-platform/skills/gone')        # old Mac layout
        (base / 'other').symlink_to('/somewhere/else/skill')
        self.install()
        self.assertFalse((base / 'gone').is_symlink())
        self.assertTrue((base / 'other').is_symlink())

    def test_the_owner_home_links_each_role_file_as_an_agent(self):
        self.assertTrue(any('.claude/agents/engineer.md' in line for line in guardrails.status(self.home, self.release)))
        self.assertEqual(self.install(), [])
        agents = self.home / '.claude/agents'
        roles = sorted(p.parent.name for p in (ROOT / 'agents').glob('*/role.md'))
        self.assertIn('engineer', roles)
        self.assertEqual(sorted(p.name for p in agents.iterdir()), [f'{role}.md' for role in roles])
        for role in roles:
            self.assertEqual(os.readlink(agents / f'{role}.md'), str(self.release / f'agents/{role}/role.md'))
        self.assertFalse((agents / 'assistant.md').exists())          # assistant has no role file
        self.assertEqual(guardrails.status(self.home, self.release), [])

    def test_agent_links_of_its_own_stay_and_gone_roles_go(self):
        agents = self.home / '.claude/agents'
        agents.mkdir(parents=True)
        (agents / 'engineer.md').write_text('mine\n')                              # a file of its own
        (agents / 'ops.md').symlink_to('/somewhere/else/ops.md')                 # a link of its own
        (agents / 'gone.md').symlink_to('/opt/dev-platform/releases/old/agents/gone/role.md')
        (agents / 'other.md').symlink_to('/opt/dev-platform/current/docs/other.md')
        notes = self.install()
        self.assertTrue(any('engineer.md: a file of its own' in n for n in notes))
        self.assertTrue(any('ops.md: a link of its own' in n for n in notes))
        self.assertEqual((agents / 'engineer.md').read_text(), 'mine\n')
        self.assertEqual(os.readlink(agents / 'ops.md'), '/somewhere/else/ops.md')
        self.assertFalse((agents / 'gone.md').is_symlink())
        self.assertTrue((agents / 'other.md').is_symlink())                     # not a role file: stays
        problems = ' '.join(guardrails.status(self.home, self.release))
        self.assertIn('engineer.md: not linked', problems)
        self.assertIn('ops.md: not linked', problems)

    def test_a_role_home_gets_no_agent_links(self):
        self.assertEqual(self.install('engineer'), [])
        self.assertFalse((self.home / '.claude/agents').exists())
        self.assertEqual(guardrails.status(self.home, self.release, 'engineer'), [])

    def test_session_naming_is_installed_and_kept_beside_other_hooks(self):
        (self.home / '.codex').mkdir()
        existing = {'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': 'bash other.sh'}]}]}}
        (self.home / '.codex/hooks.json').write_text(json.dumps(existing))
        self.assertEqual(self.install(), [])
        link = self.home / '.codex/hooks/codex-session-title.py'
        self.assertEqual(os.readlink(link), str(self.release / 'hooks/codex-session-title.py'))
        hooks = json.loads((self.home / '.codex/hooks.json').read_text())['hooks']
        self.assertEqual(set(hooks), {'SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop'})
        self.assertEqual(hooks['SessionStart'][0]['hooks'][0]['command'], 'bash other.sh')
        self.assertEqual(len(hooks['SessionStart']), 2)
        self.install()
        self.assertEqual(json.loads((self.home / '.codex/hooks.json').read_text())['hooks'], hooks)
        self.assertIn('purpose(area): Description #ref', (self.home / '.codex/AGENTS.md').read_text())
        self.assertIn('purpose(area)', (self.home / '.claude/CLAUDE.md').read_text())
        (self.home / '.pi/agent').mkdir(parents=True)
        self.install()
        extension = self.home / '.pi/agent/extensions/session-title.ts'
        self.assertEqual(extension.read_text(), (ROOT / 'integrations/pi/session-title.mjs').read_text())

    def test_pi_guard_joins_the_extensions_and_other_keys_stay(self):
        agent = self.home / '.pi/agent'
        agent.mkdir(parents=True)
        (agent / 'settings.json').write_text(json.dumps({'theme': 'dark', 'extensions': ['/x/mine.mjs']}))
        self.install()
        self.install()
        data = json.loads((agent / 'settings.json').read_text())
        guard = str(self.release / 'integrations/pi/seat-guard.mjs')
        self.assertEqual(data['theme'], 'dark')
        self.assertEqual(data['extensions'], ['/x/mine.mjs', guard])
        self.assertEqual(guardrails.status(self.home, self.release), [])

    def test_pi_guard_is_reported_when_missing_and_skipped_without_pi(self):
        self.install()
        self.assertFalse((self.home / '.pi').exists())
        (self.home / '.pi/agent').mkdir(parents=True)
        self.assertTrue(any('seat-guard.mjs' in line for line in guardrails.status(self.home, self.release)))
        self.install()
        self.assertEqual(guardrails.status(self.home, self.release), [])

    def hooks_path(self):
        done = subprocess.run(['git', 'config', '--file', str(self.home / '.gitconfig'), '--get', 'core.hooksPath'],
                              capture_output=True, text=True)
        return done.stdout.strip()

    def test_global_hooks_path_is_set_when_unset(self):
        self.assertTrue(any('core.hooksPath' in line for line in guardrails.status(self.home, self.release)))
        self.assertEqual(self.install(), [])
        self.assertEqual(self.hooks_path(), str(self.release / 'hooks/git'))
        self.assertEqual(guardrails.status(self.home, self.release), [])

    def test_global_hooks_path_of_an_older_release_is_moved(self):
        old = '/opt/dev-platform/releases/abc/hooks/git'
        subprocess.run(['git', 'config', '--file', str(self.home / '.gitconfig'), 'core.hooksPath', old], check=True)
        self.install()
        self.assertEqual(self.hooks_path(), str(self.release / 'hooks/git'))

    def test_foreign_hooks_path_is_left_alone_and_reported(self):
        subprocess.run(['git', 'config', '--file', str(self.home / '.gitconfig'), 'core.hooksPath', '/my/hooks'], check=True)
        notes = self.install()
        self.assertEqual(self.hooks_path(), '/my/hooks')
        self.assertTrue(any('/my/hooks' in note for note in notes))
        self.assertTrue(any('/my/hooks' in line for line in guardrails.status(self.home, self.release)))

    def test_command_reports_a_missing_release(self):
        result = subprocess.run([sys.executable, str(ROOT / 'bin/ai-guardrails'), 'status',
                                 '--home', str(self.home), '--release', str(self.tmp / 'none')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('no platform release', result.stderr)


class Formatter(unittest.TestCase):
    """The PostToolUse hook formats with the repository's own prettier and never fails the tool."""
    def run_hook(self, file_path):
        return subprocess.run(['bash', str(ROOT / 'hooks/post-tool-use-format.sh')],
                              input=json.dumps({'tool_input': {'file_path': str(file_path)}}),
                              capture_output=True, text=True)

    def repo(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        subprocess.run(['git', 'init', '-q', str(tmp)], check=True)
        return tmp

    def test_formats_with_the_repositorys_prettier(self):
        repo = self.repo()
        bin_dir = repo / 'node_modules/.bin'
        bin_dir.mkdir(parents=True)
        fake = bin_dir / 'prettier'
        fake.write_text('#!/bin/sh\nfor a; do f=$a; done\nprintf "formatted\\n" > "$f"\n')
        fake.chmod(0o755)
        doc = repo / 'a.md'
        doc.write_text('x\n')
        self.assertEqual(self.run_hook(doc).returncode, 0)
        self.assertEqual(doc.read_text(), 'formatted\n')

    def test_without_prettier_or_for_other_files_nothing_happens(self):
        repo = self.repo()
        doc, code = repo / 'a.md', repo / 'a.py'
        doc.write_text('x\n')
        code.write_text('x\n')
        self.assertEqual(self.run_hook(doc).returncode, 0)
        self.assertEqual(self.run_hook(code).returncode, 0)
        self.assertEqual(self.run_hook(repo / 'missing.md').returncode, 0)
        self.assertEqual(doc.read_text(), 'x\n')


class OwnerWords(unittest.TestCase):
    """One source file: Claude includes it, Codex and Pi get its text, and an edit shows as out of date."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / 'home'
        (self.home / '.pi/agent').mkdir(parents=True)
        self.release = self.tmp / 'release'
        shutil.copytree(ROOT / 'skills/develop', self.release / 'skills/develop')

    def test_each_agent_gets_the_words_once(self):
        source = self.release / guardrails.OWNER_WORDS
        words = source.read_text().strip()
        for path, kind in guardrails.prompt_files(self.home):
            guardrails.write_block(path, guardrails.block(kind, self.release))
            guardrails.write_block(path, guardrails.block(kind, self.release))
        claude = (self.home / '.claude/CLAUDE.md').read_text()
        self.assertIn(f'@{source}', claude)
        self.assertNotIn('## Ask first', claude)
        for rel in ('.codex/AGENTS.md', '.pi/agent/APPEND_SYSTEM.md'):
            text = (self.home / rel).read_text()
            self.assertEqual(text.count(words), 1, rel)
        source.write_text(source.read_text() + '\n| new | PROPOSED | x |\n')
        stale = [kind for path, kind in guardrails.prompt_files(self.home)
                 if guardrails.block(kind, self.release) not in path.read_text()]
        self.assertEqual(sorted(stale), ['codex', 'pi'])

    def test_a_release_without_the_file_gives_the_old_block(self):
        (self.release / guardrails.OWNER_WORDS).unlink()
        self.assertNotIn('owner-words', guardrails.block('claude', self.release))
        self.assertTrue(guardrails.block('codex', self.release).endswith(guardrails.NAMING_RULE + '\n' + guardrails.END))


if __name__ == '__main__':
    unittest.main()
