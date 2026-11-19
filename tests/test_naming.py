import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import naming  # noqa: E402


class NamingTest(unittest.TestCase):
    def test_format_round_trips(self):
        title = naming.format_title('feat(platform): Unify session naming', client='claude-desktop', who='owner',
                                    host='dev-server', project='dev-platform', date='2026-11-06',
                                    provider='anthropic', model='claude-opus-5-5', kind='interactive')
        self.assertEqual(title, '[dev-server/dev-platform] feat(platform): Unify session naming · owner · claude-desktop · anthropic/opus-5-5 · interactive · 2026-11-06')
        fields = naming.parse(title)
        self.assertEqual((fields['project'], fields['purpose'], fields['area']), ('dev-platform', 'feat', 'platform'))
        self.assertEqual(naming.problems(title), [])

    def test_retitle_keeps_what_and_is_idempotent(self):
        first = naming.format_title('Plan  October travel', client='chatgpt', who='owner', host='web', project='none', date='2026-10-01')
        again = naming.format_title(first, client='chatgpt', who='owner', host='web', project='none', date='2026-10-01')
        self.assertEqual(first, again)
        self.assertEqual(naming.parse(first)['what'], 'plan(october): Plan October travel')
        self.assertEqual(naming.parse(first)['model'], 'unknown')

    def test_account_and_hostile_text(self):
        title = naming.format_title('App · Acme sk-abcdefghijklmnopqrstu ' + 'x' * 200, client='claude-cli',
                                    account='acme', who='loop#12', host='dev-server', project='acme', date=1762387200000,
                                    model='openrouter/moonshotai/kimi-k2.6', kind='loop')
        parsed = naming.parse(title)
        self.assertEqual(parsed['client'], 'claude-cli:acme')
        self.assertEqual(parsed['who'], 'loop#12')
        self.assertEqual((parsed['model'], parsed['type']), ('openrouter/kimi-k2.6', 'loop'))
        self.assertNotIn('sk-abc', title)
        self.assertLessEqual(len(parsed['what']), naming.WHAT_MAX)

    def test_check_rejects_legacy_titles(self):
        self.assertTrue(naming.problems('Polish Acme UI/UX'))
        run = subprocess.run([str(ROOT / 'bin/ai-title'), 'check', 'writing'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)

    def test_guess_uses_branch_and_words(self):
        self.assertEqual(naming.infer_purpose('Server prompt fix', 'claude/fix-server-prompt-545b19'), ('fix', 'server'))
        self.assertEqual(naming.infer_purpose('Guardian review'), ('review', 'guardian'))
        self.assertEqual(naming.infer_purpose('anything', 'feat/crm-links'), ('feat', 'crm'))
        self.assertEqual(naming.infer_purpose('Smart links for CRM file uploads')[0], 'feat')

    def test_short_title_is_the_tmux_window_name(self):
        self.assertEqual(naming.short_title('fix(accounts): Thing #3', 'dev-platform'), 'dev-platform:fix(accounts)')
        self.assertEqual(naming.short_title('plain words', 'x'), 'x:chat(plain)')

    def test_seat_environment_goes_to_the_claude_settings_of_the_seat_folder(self):
        import importlib.machinery, importlib.util, json, tempfile
        from pathlib import Path
        loader = importlib.machinery.SourceFileLoader('dev_workspace', str(ROOT / 'bin/dev-workspace'))
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader('dev_workspace', loader))
        loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / '.claude').mkdir()
            (cwd / '.claude/settings.local.json').write_text(json.dumps({'env': {'KEEP': '1', 'DEV_SESSION_WHO': 'old'}}))
            module.seat_session_env(cwd, 'claude', 'workers-issue-12@dev', 'anthropic-alpha')
            saved = json.loads((cwd / '.claude/settings.local.json').read_text())['env']
            self.assertEqual(saved, {'KEEP': '1', 'DEV_SESSION_WHO': 'workers-issue-12@dev', 'DEV_SESSION_TYPE': 'seat',
                                     'DEV_SESSION_PROVIDER': 'anthropic', 'DEV_SESSION_ACCOUNT': 'anthropic-alpha'})
            self.assertIsNone(module.seat_session_env(cwd, 'codex', 'x@y'))

    def test_project_from_vanished_worktree(self):
        self.assertEqual(naming.project_of('/nope/dev-platform/.claude/worktrees/x', home='/home/owner'), 'dev-platform')
        self.assertEqual(naming.project_of('/home/owner', home='/home/owner'), 'home')


if __name__ == '__main__':
    unittest.main()
