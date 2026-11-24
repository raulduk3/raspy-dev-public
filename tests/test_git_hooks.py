"""The global git hooks (hooks/git) with real commits and real pushes to a local bare remote.

No agent tool is involved: this is what a plain terminal, Zed or Codex gets from core.hooksPath.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / 'hooks/git'


class GitHookFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='git-hooks-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / 'home'
        self.home.mkdir()
        self.config = self.tmp / 'config'
        self.config.mkdir()
        (self.home / '.gitconfig').write_text(f'[core]\n\thooksPath = {HOOKS}\n')
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'TMPDIR')}
        self.env.update(HOME=str(self.home), GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=str(self.home / '.gitconfig'),
                        GIT_TERMINAL_PROMPT='0',
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
                        DEV_PLATFORM_REPOS=str(self.config / 'repos.conf'))
        self.remote = self.tmp / 'remote.git'
        self.repo = self.tmp / 'repo'
        self.git(self.tmp, 'init', '-q', '--bare', '-b', 'main', str(self.remote))
        self.git(self.tmp, 'init', '-q', '-b', 'main', str(self.repo))
        self.git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        self.set_tier(2)
        self.commit('first')
        self.git(self.repo, 'push', '-q', 'origin', 'main', env={'DEV_LOOP_LAND': '1'})

    def set_tier(self, tier):
        (self.config / 'repos.conf').write_text(f'test/repo\t{self.repo}\towner\tmain\ttier={tier}\n')

    def run_git(self, *args, env=None):
        return subprocess.run(['git', *args], cwd=self.repo, env={**self.env, **(env or {})}, text=True,
                              capture_output=True, timeout=60)

    def git(self, cwd, *args, env=None):
        done = subprocess.run(['git', *args], cwd=cwd, env={**self.env, **(env or {})}, text=True,
                              capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def commit(self, name, message=None):
        (self.repo / name).write_text(name + '\n')
        self.git(self.repo, 'add', name)
        self.git(self.repo, 'commit', '-q', '-m', message or f'test: {name}')

    def push(self, *args, env=None):
        return self.run_git('push', '-q', *args, env=env)

    def accepted(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def refused(self, result, text=None):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        if text:
            self.assertIn(text, result.stderr)

    def remote_has(self, ref):
        done = subprocess.run(['git', '--git-dir', str(self.remote), 'rev-parse', '--verify', '-q', ref],
                              capture_output=True, text=True)
        return done.returncode == 0

    def rewrite_branch(self, branch):
        """Push BRANCH, then replace its last commit, so the next push is a force update."""
        self.git(self.repo, 'switch', '-q', '-c', branch)
        self.commit('one')
        self.accepted(self.push('-u', 'origin', branch))
        self.git(self.repo, 'reset', '-q', '--hard', 'HEAD~1')
        self.commit('two')


class PrePush(GitHookFixture):
    def test_tier_2_refuses_protected_refs_and_allows_a_feature_branch(self):
        self.commit('a')
        for ref in ('main', 'main:develop', 'main:master', 'HEAD:refs/heads/main', 'HEAD:develop'):
            with self.subTest(ref=ref):
                self.refused(self.push('origin', ref), 'tier 2')
        self.git(self.repo, 'switch', '-q', '-c', 'feat/x')
        self.accepted(self.push('-u', 'origin', 'feat/x'))
        self.assertTrue(self.remote_has('refs/heads/feat/x'))
        self.assertFalse(self.remote_has('refs/heads/develop'))

    def test_tier_2_refuses_a_delete_of_main(self):
        self.refused(self.push('origin', '--delete', 'main'), 'deleting main')
        self.assertTrue(self.remote_has('refs/heads/main'))

    def test_a_force_update_is_refused_at_every_tier(self):
        self.rewrite_branch('feat/x')
        for tier in (1, 2, 3, 4):
            self.set_tier(tier)
            with self.subTest(tier=tier):
                self.refused(self.push('--force', 'origin', 'feat/x'), 'force update')
                self.refused(self.push('origin', '+feat/x'), 'force update')

    def test_a_wip_ref_is_refused_at_every_tier(self):
        self.git(self.repo, 'switch', '-q', '-c', 'wip/desktop')
        self.commit('a')
        for tier in (1, 2, 3, 4):
            self.set_tier(tier)
            with self.subTest(tier=tier):
                self.refused(self.push('-u', 'origin', 'wip/desktop'), 'wip/')
        self.assertFalse(self.remote_has('refs/heads/wip/desktop'))

    def test_tier_1_allows_a_fast_forward_of_main_only(self):
        self.set_tier(1)
        self.commit('a')
        self.accepted(self.push('origin', 'main'))
        self.refused(self.push('origin', 'main:develop'), 'develop')
        self.git(self.repo, 'reset', '-q', '--hard', 'HEAD~1')
        self.commit('b')
        self.refused(self.push('--force', 'origin', 'main'), 'force update')

    def test_tier_3_refuses_tool_named_branches(self):
        self.set_tier(3)
        for name in ('claude/x', 'codex/x', 'copilot/x'):
            self.git(self.repo, 'switch', '-q', '-c', name)
            self.commit(name.replace('/', '-'))
            with self.subTest(name=name):
                self.refused(self.push('-u', 'origin', name), 'tool-named')
        self.git(self.repo, 'switch', '-q', '-c', 'feat/ok')
        self.accepted(self.push('-u', 'origin', 'feat/ok'))
        self.git(self.repo, 'switch', '-q', 'main')
        self.commit('m')
        self.refused(self.push('origin', 'main'), 'tier 3')

    def test_tool_named_branches_pass_at_tiers_1_and_2(self):
        self.git(self.repo, 'switch', '-q', '-c', 'claude/x')
        self.commit('a')
        self.accepted(self.push('-u', 'origin', 'claude/x'))

    def test_land_variable_permits_a_fast_forward_of_the_base_at_tiers_1_and_2(self):
        land = {'DEV_LOOP_LAND': '1'}
        for tier in (1, 2):
            self.set_tier(tier)
            with self.subTest(tier=tier):
                self.commit(f'land{tier}')
                if tier == 2:
                    self.refused(self.push('origin', 'main'), 'tier 2')
                self.accepted(self.push('origin', 'main', env=land))
                self.accepted(self.push('origin', 'main:develop', env=land))

    def test_land_variable_never_permits_a_force_update_or_tier_3(self):
        land = {'DEV_LOOP_LAND': '1'}
        self.commit('a')
        self.accepted(self.push('origin', 'main', env=land))
        self.git(self.repo, 'reset', '-q', '--hard', 'HEAD~1')
        self.commit('b')
        self.refused(self.push('--force', 'origin', 'main', env=land), 'force update')
        self.set_tier(3)
        self.git(self.repo, 'reset', '-q', '--hard', 'origin/main')
        self.commit('c')
        self.refused(self.push('origin', 'main', env=land), 'tier 3')

    def test_the_repository_own_hook_still_runs_with_its_input(self):
        marker = self.tmp / 'ran'
        hook = self.repo / '.git/hooks/pre-push'
        hook.write_text(f'#!/bin/sh\necho "$1" > {marker}\ncat >> {marker}\nexit 0\n')
        hook.chmod(0o755)
        self.git(self.repo, 'switch', '-q', '-c', 'feat/x')
        self.accepted(self.push('-u', 'origin', 'feat/x'))
        text = marker.read_text()
        self.assertIn('origin', text)
        self.assertIn('refs/heads/feat/x', text)

    def test_the_repository_own_hook_can_still_refuse(self):
        hook = self.repo / '.git/hooks/pre-push'
        hook.write_text('#!/bin/sh\necho no >&2\nexit 1\n')
        hook.chmod(0o755)
        self.git(self.repo, 'switch', '-q', '-c', 'feat/x')
        self.refused(self.push('-u', 'origin', 'feat/x'), 'no')
        self.assertFalse(self.remote_has('refs/heads/feat/x'))

    def test_the_hook_works_in_a_linked_worktree(self):
        work = self.tmp / 'linked'
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'feat/w', str(work))
        (work / 'w').write_text('w\n')
        self.git(work, 'add', 'w')
        self.git(work, 'commit', '-q', '-m', 'test: w')
        done = subprocess.run(['git', 'push', '-q', 'origin', 'feat/w:main'], cwd=work, env=self.env,
                              text=True, capture_output=True, timeout=60)
        self.refused(done, 'tier 2')


class CommitMsg(GitHookFixture):
    TRAILERS = ('Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>',
                'Co-authored-by: Codex <codex@openai.com>',
                'co-authored-by: Copilot <copilot@github.com>',
                'Co-authored-by: Someone <noreply@example.com>',
                '\U0001F916 Generated with Claude Code',
                'Generated with [Claude Code](https://claude.com/claude-code)')

    def attempt(self, message):
        (self.repo / 'f').write_text(message)
        self.git(self.repo, 'add', 'f')
        return self.run_git('commit', '-q', '-m', message)

    def test_tier_3_refuses_attribution(self):
        self.set_tier(3)
        for trailer in self.TRAILERS:
            with self.subTest(trailer=trailer):
                self.refused(self.attempt(f'fix: x\n\n{trailer}'), 'attribution')

    def test_tier_3_allows_a_plain_message_and_a_human_trailer(self):
        self.set_tier(3)
        self.accepted(self.attempt('fix: x\n\nCo-authored-by: Ana <ana@example.org>'))

    def test_other_tiers_allow_attribution(self):
        for tier in (1, 2, 4):
            self.set_tier(tier)
            with self.subTest(tier=tier):
                self.accepted(self.attempt(f'fix: x{tier}\n\n{self.TRAILERS[0]}'))

    def test_an_unregistered_repository_is_tier_3(self):
        (self.config / 'repos.conf').write_text('')
        self.refused(self.attempt(f'fix: x\n\n{self.TRAILERS[0]}'), 'attribution')

    def test_the_repository_own_hook_still_runs(self):
        hook = self.repo / '.git/hooks/commit-msg'
        hook.write_text('#!/bin/sh\ngrep -q ticket "$1" || { echo needs-ticket >&2; exit 1; }\n')
        hook.chmod(0o755)
        self.refused(self.attempt('fix: x'), 'needs-ticket')
        self.accepted(self.attempt('fix: x ticket'))



class PreCommitHookTests(GitHookFixture):
    """decisions=none (the default) and decisions=frozen: no commit touches docs/decisions/ or adds a SPEC-AMENDMENTS.md."""

    def setUp(self):
        super().setUp()
        self.freeze('decisions=open')   # the history of the repository is older than the mode
        (self.repo / 'docs/decisions').mkdir(parents=True)
        (self.repo / 'docs/decisions/0001-old.md').write_text('old\n')
        self.git(self.repo, 'add', 'docs')
        self.git(self.repo, 'commit', '-q', '-m', 'docs: history')

    def freeze(self, extra='spec=domains\tdecisions=frozen'):
        (self.config / 'repos.conf').write_text(f'test/repo\t{self.repo}\towner\tmain\ttier=3\t{extra}\n')

    def stage(self, path, text='x\n'):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        self.git(self.repo, 'add', path)
        return self.run_git('commit', '-q', '-m', f'docs: {path}')

    def test_frozen_refuses_a_new_changed_or_deleted_decision(self):
        self.freeze()
        self.refused(self.stage('docs/decisions/0002-new.md'), 'decisions=frozen')
        self.git(self.repo, 'reset', '-q')
        self.refused(self.stage('docs/decisions/0001-old.md', 'changed\n'), 'docs/decisions/0001-old.md')
        self.git(self.repo, 'reset', '-q')
        self.git(self.repo, 'checkout', '-q', '--', '.')
        self.git(self.repo, 'rm', '-q', 'docs/decisions/0001-old.md')
        self.refused(self.run_git('commit', '-q', '-m', 'docs: drop'), 'decisions=frozen')

    def test_frozen_refuses_a_new_amendment_ledger_anywhere(self):
        self.freeze()
        self.refused(self.stage('docs/spec/SPEC-AMENDMENTS.md'), 'SPEC-AMENDMENTS.md')

    def test_frozen_allows_a_direct_spec_edit(self):
        self.freeze()
        self.accepted(self.stage('docs/spec/game/sdd.md'))

    def test_none_is_the_default_and_refuses_a_decision_and_a_new_ledger(self):
        for extra in ('tier=3', 'decisions=none'):   # a line with no field, and the field itself
            with self.subTest(extra=extra):
                self.freeze(extra)
                self.refused(self.stage('docs/decisions/0002-new.md'), 'decisions=none')
                self.git(self.repo, 'reset', '-q')
                self.refused(self.stage('docs/decisions/0001-old.md', 'changed\n'), 'docs/decisions/0001-old.md')
                self.git(self.repo, 'reset', '-q')
                self.git(self.repo, 'checkout', '-q', '--', '.')
                self.refused(self.stage('docs/spec/SPEC-AMENDMENTS.md'), 'SPEC-AMENDMENTS.md')
                self.git(self.repo, 'reset', '-q')
        self.accepted(self.stage('docs/spec/SDD.md'))   # the specification itself changes

    def test_none_allows_the_deletion_of_an_old_decision_and_frozen_does_not(self):
        self.freeze('decisions=frozen')
        self.git(self.repo, 'rm', '-q', 'docs/decisions/0001-old.md')
        self.refused(self.run_git('commit', '-q', '-m', 'docs: drop'), 'decisions=frozen')
        self.freeze('decisions=none')
        self.accepted(self.run_git('commit', '-q', '-m', 'docs: drop the old record'))
        self.assertFalse((self.repo / 'docs/decisions/0001-old.md').exists())

    def test_none_leaves_a_ledger_that_exists_open_to_a_change(self):
        self.stage('docs/spec/SPEC-AMENDMENTS.md')
        self.freeze('decisions=none')
        self.accepted(self.stage('docs/spec/SPEC-AMENDMENTS.md', 'a row of the old history\n'))

    def test_open_and_unregistered_repositories_allow_decisions(self):
        self.freeze('decisions=open')
        self.accepted(self.stage('docs/decisions/0002-new.md'))
        (self.config / 'repos.conf').write_text('')
        self.accepted(self.stage('docs/decisions/0003-new.md'))

    def test_the_repository_own_pre_commit_hook_still_runs(self):
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\necho own-hook >&2\nexit 1\n')
        hook.chmod(0o755)
        self.freeze()
        self.refused(self.stage('docs/spec/game/sdd.md'), 'own-hook')

    def test_the_tier_record_has_the_mode_and_its_defaults(self):
        tiers = ROOT / 'lib/ai_ecosystem/tiers.py'
        run = lambda: subprocess.run(['python3', '-I', str(tiers), '--json', str(self.repo)], env=self.env,
                                     capture_output=True, text=True, check=True).stdout
        self.freeze()
        self.assertIn('"decisions": "frozen"', run())
        self.assertIn('"spec": "domains"', run())
        self.freeze('tier=3')
        self.assertIn('"decisions": "none"', run())   # the default of a registered line: no decision record
        self.assertIn('"spec": "single"', run())
        self.freeze('decisions=open')
        self.assertIn('"decisions": "open"', run())
        (self.config / 'repos.conf').write_text('')
        self.assertIn('"decisions": "open"', run())   # a repository that no line names: the platform sets no rule
        self.freeze('decisions=closed')
        bad = subprocess.run(['python3', '-I', str(tiers), str(self.repo)], env=self.env, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)

    def test_the_tier_record_gives_the_place_of_the_incoming_file(self):
        tiers = ROOT / 'lib/ai_ecosystem/tiers.py'
        record = lambda: json.loads(subprocess.run(['python3', '-I', str(tiers), '--json', str(self.repo)], env=self.env,
                                                   capture_output=True, text=True, check=True).stdout)
        self.freeze('tier=3')
        out = record()
        self.assertEqual(out['incoming'], 'state')
        self.assertEqual(out['incoming_file'],
                         str(Path(self.env['HOME']) / '.local/state/dev-platform/incoming' / f'{out["repo"].rpartition("/")[2]}.html'))
        self.freeze('incoming=project')
        out = record()
        self.assertEqual(out['incoming'], 'project')
        self.assertEqual(out['incoming_file'], str(Path(out['path']) / 'docs/incoming.html'))
        self.freeze('incoming=repo')
        bad = subprocess.run(['python3', '-I', str(tiers), str(self.repo)], env=self.env, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)


if __name__ == '__main__':
    unittest.main()
