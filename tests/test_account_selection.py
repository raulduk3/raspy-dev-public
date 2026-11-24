"""ai-account select: the owner names an account per provider; the resolver uses it or
refuses, and never substitutes another. ai-account run: a folder whose client settings
override authentication or the provider starts nothing. Fake store only."""
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import accounts  # noqa: E402
from test_registry import Fake  # noqa: E402


class SelectionTest(Fake):
    def setUp(self):
        super().setUp()
        self.selection = self.tmp / 'selection.json'
        self.sel_env = mock.patch.dict(os.environ, {'DEV_PLATFORM_ACCOUNT_SELECTION': str(self.selection)})
        self.sel_env.start()
        self.addCleanup(self.sel_env.stop)

    def cli(self, *argv):
        with mock.patch('sys.stdout', new=io.StringIO()) as out, mock.patch('sys.stderr', new=io.StringIO()) as err:
            code = accounts.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_selecting_an_unverified_account_is_refused(self):
        code, _, err = self.cli('select', 'anthropic-alpha')
        self.assertEqual(code, 2)
        self.assertIn('not signed in and verified', err)
        self.assertFalse(self.selection.exists())

    def test_a_selected_account_is_used_over_more_quota_elsewhere(self):
        self.signed('anthropic-bravo', 'claude')
        self.signed('anthropic-alpha', 'claude')
        self.used('anthropic-bravo', 10)
        self.used('anthropic-alpha', 80)
        self.assertEqual(self.cli('select', 'anthropic-alpha')[0], 0)
        self.assertEqual(json.loads(self.selection.read_text()), {'anthropic': 'anthropic-alpha'})
        code, out, _ = self.cli('selected')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['selected'], 'anthropic-alpha')
        self.assertIn('selected by the owner', json.loads(out)['reason'])

    def test_a_selected_account_that_runs_out_fails_and_is_never_substituted(self):
        self.signed('anthropic-bravo', 'claude')
        self.signed('anthropic-alpha', 'claude')
        self.cli('select', 'anthropic-alpha')
        self.used('anthropic-alpha', 100)
        code, _, err = self.cli('resolve', '--client', 'claude')
        self.assertEqual(code, 2)
        self.assertIn('never substituted', err)

    def test_an_account_named_for_one_launch_wins_over_the_selection(self):
        self.signed('anthropic-bravo', 'claude')
        self.signed('anthropic-alpha', 'claude')
        self.cli('select', 'anthropic-alpha')
        code, out, _ = self.cli('resolve', '--client', 'claude', '--account', 'anthropic-bravo')
        self.assertEqual((code, out.strip()), (0, 'anthropic-bravo'))

    def test_selection_is_per_provider_and_clears(self):
        self.signed('anthropic-alpha', 'claude')
        self.signed('openai-bravo', 'codex')
        self.cli('select', 'anthropic-alpha')
        self.cli('select', 'openai-bravo')
        self.assertEqual(json.loads(self.selection.read_text()),
                         {'anthropic': 'anthropic-alpha', 'openai': 'openai-bravo'})
        self.cli('select', '--clear', '--provider', 'openai')
        self.assertEqual(json.loads(self.selection.read_text()), {'anthropic': 'anthropic-alpha'})
        self.cli('select', '--clear')
        self.assertEqual(json.loads(self.selection.read_text()), {})

    def test_an_unreadable_selection_refuses_instead_of_launching_unnamed(self):
        self.signed('anthropic-bravo', 'claude')
        self.selection.write_text('not json')
        code, _, _ = self.cli('resolve', '--client', 'claude')
        self.assertEqual(code, 2)


class ConfigurationCheckTest(Fake):
    """accounts.configuration_check, through ai-account run: the launcher is a stand-in."""
    def start(self, folder):
        clean = {k: v for k, v in os.environ.items() if not accounts.conflicts({k: v})}
        with mock.patch.dict(os.environ, clean, clear=True), \
                mock.patch.object(accounts, 'default_model', return_value='model-x'), \
                mock.patch.object(accounts.os, 'execvpe') as started, \
                mock.patch('sys.stderr', new=io.StringIO()) as err:
            code = accounts.main(['run', '--client', 'claude', '--cwd', str(folder), '--', 'hello'])
        return code, err.getvalue(), started

    def test_a_folder_with_plain_settings_starts_through_the_launcher_with_names_only(self):
        project = self.tmp / 'project'
        (project / '.claude').mkdir(parents=True)
        (project / '.claude/settings.json').write_text('{"permissions": {"allow": []}}')
        code, err, started = self.start(project)
        self.assertEqual((code, err), (0, ''))
        program, argv, env = started.call_args[0]
        self.assertEqual((program, argv), ('agent', ['agent', 'owner', str(project.resolve()), '--', 'hello']))
        self.assertEqual((env['OL_MODEL'], env['DEV_SESSION_PROVIDER']), ('model-x', 'anthropic'))
        self.assertNotIn('OL_ACCOUNT', env)                      # none named: the launcher resolves

    def test_settings_that_override_the_provider_refuse_the_run_and_name_only_the_file(self):
        project = self.tmp / 'project'
        (project / '.claude').mkdir(parents=True)
        (project / 'deep/er').mkdir(parents=True)
        settings = project / '.claude/settings.json'
        settings.write_text('{"env": {"ANTHROPIC_BASE_URL": "https://proxy.invalid"}}')
        for folder in (project, project / 'deep/er'):            # the check reads each folder above too
            code, err, started = self.start(folder)
            self.assertEqual(code, 2)
            self.assertIn(f'{settings} overrides authentication or the provider', err)
            self.assertNotIn('proxy.invalid', err)               # the file is named, never its values
            started.assert_not_called()
        settings.unlink()
        (project / '.codex').mkdir()
        (project / '.codex/config.toml').write_text('model_provider = "other"\n')
        code, err, started = self.start(project)
        self.assertEqual(code, 2)
        self.assertIn('.codex/config.toml overrides authentication or the provider', err)
        started.assert_not_called()


if __name__ == '__main__':
    unittest.main()
