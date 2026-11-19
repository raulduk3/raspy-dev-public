"""Behavior retained from older PRs, exercised through the actual hooks/templates."""
import importlib.util
import json
import subprocess
import sys
import unittest

from test_stability import Fixture, PLATFORM


class StopHookTests(Fixture):
    def stop(self, expected=0, input=''):
        return self.run_cmd('bash', PLATFORM / 'hooks/stop-check.sh', expected=expected, input=input)

    def test_a_stop_after_the_hooks_own_block_is_let_through(self):
        self.write_check('echo deliberate-failure\nexit 7\n')
        self.stop(expected=2, input='{"session_id": "s", "stop_hook_active": false}')
        self.stop(expected=0, input='{"session_id": "s", "stop_hook_active": true}')
        self.stop(expected=0, input='{"stop_hook_active":true}')    # compact JSON too

    def test_bin_check_without_package_json_and_cached_second_stop(self):
        (self.repo / 'source').write_text('modified\n')
        self.stop()
        self.stop()
        self.assertEqual(self.calls(), 1)

    def test_a_running_check_on_the_tree_lets_the_stop_through(self):
        (self.repo / 'source').write_text('modified\n')
        lock = self.repo / '.git/dev-platform/check-lock'
        lock.mkdir(parents=True)
        holder = subprocess.Popen(['sleep', '30'])
        self.addCleanup(lambda: (holder.kill(), holder.wait()))
        (lock / 'pid').write_text(f'{holder.pid}\n')
        self.assertIn('another check holds', self.stop().stdout)
        self.assertEqual(self.calls(), 0)

    def test_the_session_cwd_in_the_hook_input_selects_its_worktree(self):
        # The hook can start in the project folder while the session works in a linked worktree:
        # the worktree with the change is checked, and the clean project folder is left alone.
        worktree = self.base / 'wt'
        self.run_cmd('git', 'worktree', 'add', '-q', '-b', 'wt', worktree)
        (worktree / 'source').write_text('worktree change\n')
        self.stop(input=json.dumps({'session_id': 's', 'cwd': str(worktree), 'stop_hook_active': False}))
        self.assertEqual(self.calls(cwd=worktree), 1)
        self.assertEqual(self.calls(), 0)
        self.assertTrue((worktree / '.git').is_file())
        self.run_cmd('git', '-C', worktree, 'rev-parse', '--git-path', 'dev-platform')

    def test_an_orchestrated_tree_runs_no_check_at_a_stop(self):
        (self.repo / 'source').write_text('modified\n')
        marker = self.repo / '.git/dev-platform/orchestrated'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        self.assertIn('orchestrated tree', self.stop().stdout)
        self.assertEqual(self.calls(), 0)
        # A linked worktree of the same repository shares the marker.
        worktree = self.base / 'wt'
        self.run_cmd('git', 'worktree', 'add', '-q', '-b', 'wt', worktree)
        (worktree / 'source').write_text('worktree change\n')
        self.stop(input=json.dumps({'session_id': 's', 'cwd': str(worktree), 'stop_hook_active': False}))
        self.assertEqual(self.calls(cwd=worktree), 0)
        # The agent can still run the check directly.
        self.check()
        self.assertEqual(self.calls(), 1)

    def test_bin_check_failure_blocks_stop(self):
        self.write_check('echo deliberate-failure\nexit 7\n')
        self.assertIn('deliberate-failure', self.stop(expected=2).stdout)
        self.check('--status', expected=1)

    def test_clean_tree_with_unpublished_commits_is_checked(self):
        self.setup_remote()
        self.run_cmd('git', 'branch', '--set-upstream-to=origin/main')
        (self.repo / 'source').write_text('committed\n')
        self.commit()
        self.stop()
        self.assertEqual(self.calls(), 1)

    def test_clean_tree_at_upstream_does_not_run_check(self):
        self.setup_remote()
        self.run_cmd('git', 'branch', '--set-upstream-to=origin/main')
        self.stop()
        self.assertEqual(self.calls(), 0)


class HygieneTemplateTests(Fixture):
    def hygiene(self, base):
        module = PLATFORM / 'templates/scripts/checks/hygiene.py'
        spec = importlib.util.spec_from_file_location('template_hygiene', module)
        hygiene = importlib.util.module_from_spec(spec)
        sys.modules['template_hygiene'] = hygiene
        spec.loader.exec_module(hygiene)
        return hygiene.check_hygiene(self.repo, base)

    def commit_message(self, message):
        self.run_cmd('git', 'add', '.')
        self.run_cmd('git', 'commit', '--allow-empty', '-qm', message)

    def test_actual_history_flags_tool_trailer_and_generated_with(self):
        base = self.run_cmd('git', 'rev-parse', 'HEAD').stdout.strip()
        self.commit_message('fix: update behavior\n\nCo-authored-by: Claude <noreply@anthropic.com>')
        self.commit_message('fix: update another behavior\n\nGenerated with a tool')
        result = self.hygiene(base)
        self.assertEqual(result['commitsChecked'], 2)
        self.assertEqual([f['code'] for f in result['findings']],
                         ['trailer-attribution', 'trailer-attribution'])

    def test_plain_history_and_nonphrase_are_clean_but_source_tokens_are_not(self):
        base = self.run_cmd('git', 'rev-parse', 'HEAD').stdout.strip()
        self.commit_message('fix: regenerate data\n\nData regenerated with a new seed')
        self.assertEqual(self.hygiene(base)['findings'], [])
        (self.repo / 'src').mkdir()
        (self.repo / 'src/example.ts').write_text('// Generated by codex\n')
        self.commit_message('fix: add example')
        findings = self.hygiene(base)['findings']
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['code'], 'forbidden-token')
        self.assertEqual(findings[0]['where'], 'src/example.ts:1')
