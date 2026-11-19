import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TitleBundle(unittest.TestCase):
    def test_installer_adds_hooks_and_rule_and_keeps_owner_settings(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        home = tmp / 'home'
        (home / '.claude').mkdir(parents=True)
        (home / '.claude-accounts/work').mkdir(parents=True)
        (home / '.claude/settings.json').write_text('{"model": "opus", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}]}}')
        script = tmp / 'naming-install.py'
        script.write_text(subprocess.run([str(ROOT / 'bin/ai-title-bundle')], capture_output=True, text=True, check=True).stdout)
        env = dict(os.environ, HOME=str(home))
        env.pop('CLAUDE_CONFIG_DIR', None)
        for _ in range(2):
            run = subprocess.run(['python3', '-I', str(script), 'install'], env=env, capture_output=True, text=True, cwd=tmp)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        settings = json.loads((home / '.claude/settings.json').read_text())
        self.assertEqual(settings['model'], 'opus')
        self.assertEqual(settings['hooks']['Stop'][0]['hooks'][0]['command'], 'echo keep')
        self.assertEqual(len(settings['hooks']['UserPromptSubmit']), 1)
        self.assertIn('purpose(area)', (home / '.claude-accounts/work/CLAUDE.md').read_text())
        words = (ROOT / 'skills/develop/owner-words.md').read_text().strip()
        self.assertIn(words, (home / '.claude/CLAUDE.md').read_text())
        self.assertEqual((home / '.claude/CLAUDE.md').read_text().count('## Ask first'), 1)
        hook = home / '.local/share/dev-platform-naming/hooks/session-title.py'
        out = subprocess.run(['python3', str(hook)], input=json.dumps({'session_id': 'x', 'hook_event_name': 'UserPromptSubmit',
                             'prompt': 'Fix the login redirect bug', 'cwd': str(tmp)}), env=env, capture_output=True, text=True)
        title = json.loads(out.stdout)['hookSpecificOutput']['sessionTitle']
        self.assertIn('] fix(login): Fix the login redirect bug · ', title)

    def test_status_accepts_the_platform_block_that_imports_the_owner_words(self):
        # 2026-11-17, dev-server: ai-guardrails writes the naming rule and an import of the word list.
        # status looked for the word list as text and said "no naming rule".
        sys.path.insert(0, str(ROOT / 'lib'))
        from ai_ecosystem.guardrails import NAMING_RULE
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        home = tmp / 'home'
        (home / '.claude').mkdir(parents=True)
        block = ('<!-- dev-platform guardrails: begin (managed by ai-guardrails; edit outside this block) -->\n'
                 f'{NAMING_RULE}\n\n@/opt/dev-platform/current/skills/develop/owner-words.md\n'
                 '<!-- dev-platform guardrails: end -->\n')
        (home / '.claude/CLAUDE.md').write_text(block)
        script = tmp / 'naming-install.py'
        script.write_text(subprocess.run([str(ROOT / 'bin/ai-title-bundle')], capture_output=True, text=True, check=True).stdout)
        env = dict(os.environ, HOME=str(home))
        env.pop('CLAUDE_CONFIG_DIR', None)
        run = subprocess.run(['python3', '-I', str(script), 'install'], env=env, capture_output=True, text=True, cwd=tmp)
        self.assertNotIn('no naming rule', run.stdout + run.stderr)
        self.assertEqual((home / '.claude/CLAUDE.md').read_text(), block)
        (home / '.claude/CLAUDE.md').write_text(block.replace(NAMING_RULE, 'no rule here'))
        run = subprocess.run(['python3', '-I', str(script), 'status'], env=env, capture_output=True, text=True, cwd=tmp)
        self.assertIn('no naming rule', run.stdout + run.stderr)


class ClientBundle(unittest.TestCase):
    """--client: the portable rules for local agents on a machine without the platform (the laptop)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / 'home'
        (self.home / '.claude').mkdir(parents=True)
        (self.home / '.codex').mkdir(parents=True)
        self.script = self.tmp / 'client-install.py'
        self.script.write_text(subprocess.run([str(ROOT / 'bin/ai-title-bundle'), '--client'],
                                              capture_output=True, text=True, check=True).stdout)
        self.env = dict(os.environ, HOME=str(self.home))
        for name in ('CLAUDE_CONFIG_DIR', 'GIT_CONFIG_GLOBAL', 'XDG_CONFIG_HOME', 'GIT_CONFIG_SYSTEM'):
            self.env.pop(name, None)
        self.env['GIT_CONFIG_NOSYSTEM'] = '1'
        self.ste = (ROOT / 'skills/develop/ste100.md').read_text().strip('\n')
        self.body = self.ste.split('\n', 1)[1].rsplit('\n', 1)[0]
        self.prefix = self.home / '.local/share/dev-platform-naming'

    def run_installer(self, command='install'):
        return subprocess.run(['python3', '-I', str(self.script), command], env=self.env,
                              capture_output=True, text=True, cwd=self.tmp)

    def git_global(self, *args):
        return subprocess.run(['git', 'config', '--global', *args], env=self.env, capture_output=True, text=True)

    def test_client_install_carries_the_portable_rules_once(self):
        old_title = ('<!-- dev-platform session title: begin (managed by naming-install.py) -->\nold rule\n'
                     '<!-- dev-platform session title: end -->')
        (self.home / '.claude/CLAUDE.md').write_text(f'mine\n\n{self.ste}\n\n{old_title}\n')
        # Codex has the STE text with no markers, as on the Mac.
        (self.home / '.codex/AGENTS.md').write_text(f'{self.body}\n\n{old_title}\n')
        (self.home / '.codex/config.toml').write_text('sandbox_mode = "danger-full-access"\napproval_policy = "never"\n')
        for _ in range(2):
            run = self.run_installer()
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        for path in (self.home / '.claude/CLAUDE.md', self.home / '.codex/AGENTS.md'):
            text = path.read_text()
            self.assertEqual(text.count('# Writing standard: ASD-STE100'), 1, path)
            self.assertIn(self.ste, text)
            self.assertNotIn('session title: begin', text)
            self.assertNotIn('old rule', text)
            self.assertEqual(text.count('client rules: begin'), 1)
            self.assertIn('runs on dev-server over SSH', text)
            self.assertIn('no Co-Authored-By trailer', text)
            self.assertIn('purpose(area)', text)
            self.assertEqual(text.count('## Ask first'), 1)
            self.assertNotIn('/opt/dev-platform', text)
        self.assertTrue((self.home / '.claude/CLAUDE.md').read_text().startswith('mine\n'))
        # The Codex sandbox and approval settings are the owner's.
        self.assertIn('danger-full-access', (self.home / '.codex/config.toml').read_text())
        settings = json.loads((self.home / '.claude/settings.json').read_text())
        guards = settings['hooks']['PreToolUse']
        self.assertEqual(len(guards), 1)
        self.assertEqual(guards[0]['matcher'], 'Bash')
        self.assertIn('dev-platform-naming/hooks/pre-tool-use-guard.sh', guards[0]['hooks'][0]['command'])
        self.assertEqual(len(settings['hooks']['UserPromptSubmit']), 1)
        self.assertEqual(self.git_global('--get', 'core.hooksPath').stdout.strip(), str(self.prefix / 'hooks/git'))
        self.assertEqual(self.run_installer('status').returncode, 0)

    def test_installed_guard_and_git_hooks_run_without_the_platform(self):
        run = self.run_installer()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        guard = self.prefix / 'hooks/pre-tool-use-guard.sh'
        env = dict(self.env, DEV_PLATFORM_JEV_GUARD='0', DEV_PLATFORM_REPOS=str(self.tmp / 'none.conf'))

        def decide(command):
            return subprocess.run([str(guard)], input=json.dumps({'tool_input': {'command': command}, 'cwd': str(self.tmp)}),
                                  env=env, capture_output=True, text=True)

        refused = decide('git push --force origin feature')
        self.assertEqual(refused.returncode, 2)
        self.assertNotIn('could not run', refused.stderr)
        self.assertEqual(decide('git status').returncode, 0)
        repo = self.tmp / 'repo'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True, env=env)
        commit = ['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-q',
                  '--allow-empty', '-m']
        # A repository that repos.conf does not name is tier 3: the commit-msg hook refuses attribution.
        refused = subprocess.run(commit + ['feat: x\n\nCo-Authored-By: Claude <noreply@anthropic.com>'], env=env,
                                 capture_output=True, text=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('dev-platform commit-msg', refused.stderr)
        self.assertEqual(subprocess.run(commit + ['feat: x'], env=env).returncode, 0)

    def test_owner_hooks_path_and_different_ste_text_are_left_alone(self):
        self.git_global('core.hooksPath', '/owner/hooks')
        (self.home / '.codex/AGENTS.md').write_text('# Writing standard: ASD-STE100 with an expanded vocabulary\nolder text\n')
        run = self.run_installer()
        self.assertIn('core.hooksPath is /owner/hooks; left alone', run.stderr)
        self.assertIn('no ste100 markers', run.stderr)
        self.assertEqual(self.git_global('--get', 'core.hooksPath').stdout.strip(), '/owner/hooks')
        self.assertEqual((self.home / '.codex/AGENTS.md').read_text().count('# Writing standard'), 1)
        self.assertEqual(self.run_installer('status').returncode, 1)

    def test_plain_bundle_has_no_client_parts(self):
        text = subprocess.run([str(ROOT / 'bin/ai-title-bundle')], capture_output=True, text=True, check=True).stdout
        self.assertIn('CLIENT = False', text)
        self.assertNotIn('pre-tool-use-guard.sh"', text)
        self.assertEqual(subprocess.run([str(ROOT / 'bin/ai-title-bundle'), '--other'], capture_output=True).returncode, 2)


if __name__ == '__main__':
    unittest.main()
