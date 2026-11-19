"""The Claude Code guard (hooks/pre-tool-use-guard.sh) against real repositories.

A main checkout and two linked worktrees; the tier comes from a temporary repos.conf.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'hooks/pre-tool-use-guard.sh'


class GuardFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='guard-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / 'home'
        self.home.mkdir()
        self.config = self.tmp / 'config'
        self.config.mkdir()
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'TMPDIR')}
        self.env.update(HOME=str(self.home), GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
                        DEV_PLATFORM_REPOS=str(self.config / 'repos.conf'),
                        DEV_PLATFORM_PERSONAL=str(self.config / 'personal.conf'))
        (self.config / 'personal.conf').write_text('')
        self.repo = self.tmp / 'repo'
        self.mine = self.tmp / 'mine'
        self.other = self.tmp / 'other'
        self.git(self.tmp, 'init', '-q', '-b', 'main', str(self.repo))
        (self.repo / 'file').write_text('x\n')
        self.git(self.repo, 'add', '.')
        self.git(self.repo, 'commit', '-qm', 'test: first')
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'feat/mine', str(self.mine))
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'feat/other', str(self.other))
        self.git(self.repo, 'branch', 'stale')
        self.set_tier(2)

    def git(self, cwd, *args):
        done = subprocess.run(['git', *args], cwd=cwd, env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def set_tier(self, tier):
        (self.config / 'repos.conf').write_text(f'test/repo\t{self.repo}\towner\tmain\ttier={tier}\n')

    def guard(self, command, cwd=None):
        payload = json.dumps({'cwd': str(cwd or self.mine), 'tool_input': {'command': command}})
        return subprocess.run(['bash', str(GUARD)], input=payload, env=self.env, capture_output=True,
                              text=True, timeout=60).returncode

    def refused(self, commands, cwd=None):
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(self.guard(command, cwd), 2)

    def allowed(self, commands, cwd=None):
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(self.guard(command, cwd), 0)


class GuardPush(GuardFixture):
    def test_protected_refs_in_every_spelling_at_tiers_2_to_4(self):
        for tier in (2, 3, 4):
            self.set_tier(tier)
            with self.subTest(tier=tier):
                self.refused(['git push origin main', 'git push -u origin main', 'git push origin master',
                              'git push origin develop', 'git push origin HEAD:refs/heads/main',
                              'git push origin feat/x:main', 'git push origin "main"',
                              f'git -C {self.repo} push origin main', 'git push origin +main',
                              'git push origin :main', 'git push origin refs/heads/x:refs/heads/develop',
                              'cd .. && git push origin main'])

    def test_tier_1_allows_a_plain_push_of_main_only(self):
        self.set_tier(1)
        self.allowed(['git push origin main', 'git push -u origin main', 'git push origin HEAD:refs/heads/main',
                      'git push origin master', 'git push'])
        self.refused(['git push origin +main', 'git push --force origin main', 'git push -f origin main',
                      'git push --force-with-lease origin main', 'git push origin develop',
                      'git push --mirror origin', 'git push --all origin'])

    def test_force_pushes_are_refused_at_every_tier(self):
        for tier in (1, 2, 3, 4):
            self.set_tier(tier)
            with self.subTest(tier=tier):
                self.refused(['git push --force origin fix/x', 'git push -f origin fix/x',
                              'git push origin +fix/x', 'git push origin +HEAD:fix/x'])

    def test_a_wip_ref_is_never_pushed(self):
        for tier in (1, 2, 3, 4):
            self.set_tier(tier)
            with self.subTest(tier=tier):
                self.refused(['git push -u origin wip/desktop-1', 'git push origin HEAD:refs/heads/wip/x',
                              'git push origin fix/y:wip/y'])

    def test_head_means_the_current_branch(self):
        self.refused(['git push -u origin HEAD'], cwd=self.repo)
        self.allowed(['git push -u origin HEAD'], cwd=self.mine)

    def test_ordinary_branches_pass(self):
        self.allowed(['git push -u origin fix/example', 'git push origin HEAD:refs/heads/fix/example',
                      'git status', 'git push origin fix/x 2>&1'])
        self.refused(['git push', 'git push origin'])

    def test_tool_named_branches_are_refused_at_tier_3_only(self):
        commands = ['git push -u origin claude/x', 'git push origin codex/x', 'git push origin HEAD:copilot/x']
        self.set_tier(3)
        self.refused(commands)
        for tier in (1, 2, 4):
            self.set_tier(tier)
            self.allowed(commands)

    def test_an_unregistered_repository_is_tier_3(self):
        (self.config / 'repos.conf').write_text('')
        self.refused(['git push -u origin claude/x',
                      'git commit -m "Co-authored-by: Claude <noreply@anthropic.com>"'])

    def test_a_line_without_tier_follows_personal_conf(self):
        (self.config / 'repos.conf').write_text(f'test/repo\t{self.repo}\towner\tmain\n')
        self.refused(['git commit -m "Generated with Claude"'])
        (self.config / 'personal.conf').write_text(f'{self.repo}\n')
        self.allowed(['git commit -m "Generated with Claude"'])

    def test_an_agent_does_not_set_the_land_variable(self):
        for tier in (1, 2):
            self.set_tier(tier)
            with self.subTest(tier=tier):
                self.refused(['DEV_LOOP_LAND=1 git push origin main', 'export DEV_LOOP_LAND=1',
                              'env DEV_LOOP_LAND=1 git push origin develop',
                              "bash -c 'DEV_LOOP_LAND=1 git push origin main'"])
                self.allowed(['echo DEV_LOOP_LAND=1', 'grep DEV_LOOP_LAND notes'])


class GuardMerge(GuardFixture):
    def test_merge_while_a_protected_branch_is_current(self):
        self.refused(['git merge feat/other', 'git merge --no-ff feat/other',
                      'git checkout main && git merge feat/other', f'git -C {self.repo} merge feat/other',
                      'cd ../repo && git merge feat/other', 'git switch develop; git merge x'], cwd=self.repo)
        self.refused([f'git -C {self.repo} merge feat/other'], cwd=self.mine)
        self.allowed(['git merge feat/other', 'git merge --abort', f'git -C {self.other} merge feat/mine',
                      'git checkout feat/other && git merge feat/mine'], cwd=self.mine)

    def test_a_fast_forward_of_main_is_allowed_at_tier_1_only(self):
        self.set_tier(1)
        self.allowed(['git merge --ff-only feat/other'], cwd=self.repo)
        self.refused(['git merge feat/other'], cwd=self.repo)
        self.set_tier(2)
        self.refused(['git merge --ff-only feat/other'], cwd=self.repo)

    def test_gh_merges(self):
        self.refused(['gh pr merge 1', 'gh pr ready 1', 'gh pr review 1 --approve', 'gh -R o/r pr merge 1',
                      'gh api repos/o/r/merges -f base=main -f head=x',
                      'gh api -X PUT repos/o/r/pulls/5/merge', 'gh api --method PUT /repos/o/r/pulls/5/merge?x=1',
                      'gh api graphql -f query="mutation { mergePullRequest(input: {}) { clientMutationId } }"'])
        self.allowed(['gh api repos/o/r/pulls/5', 'gh pr list', 'gh pr view 1', 'gh pr create --draft --title x'])


class GuardOthers(GuardFixture):
    def test_no_verify(self):
        self.refused(['git commit --no-verify -m x', 'git commit -nm x', 'git commit -n -m x',
                      'git push --no-verify -u origin fix/x', 'git -c core.hooksPath=/dev/null commit -m x',
                      'git config core.hooksPath /dev/null'])
        self.allowed(['git commit -m "use --no-verify never"', 'git commit -am x',
                      'git config --get core.hooksPath'])

    def test_branch_delete_of_a_branch_that_another_worktree_has(self):
        self.refused(['git branch -D feat/other', 'git branch -d --force feat/other',
                      'git branch --delete --force feat/other', 'git branch -df feat/other',
                      f'git -C {self.repo} branch -D main'])
        self.allowed(['git branch -D stale', 'git branch -d stale', 'git branch -D feat/mine', 'git branch --list'])

    def test_worktree_remove_and_clean_of_another_worktree(self):
        self.refused([f'git worktree remove {self.other}', f'git worktree remove --force {self.other}',
                      'git worktree remove ../other', f'git -C {self.other} clean -fd',
                      f'cd {self.other} && git clean -fdx', f'git clean -fd {self.other}',
                      f'git -C {self.repo} clean -fd'])
        self.allowed(['git worktree list', 'git clean -fd', 'git clean -n', f'git -C {self.other} clean -n',
                      'git worktree add ../third -b feat/third'])

    def test_quoted_text_and_search_patterns_are_not_commands(self):
        self.allowed(["grep 'gh pr merge' file", 'rg "git push" .', 'echo "git push origin main"',
                      "echo 'git merge x; git branch -D feat/other'", 'git log --grep="git push"',
                      'cat <<EOF\ngit push origin main\ngh pr merge 1\nEOF',
                      "sed -n '/git rebase/p' notes"], cwd=self.repo)

    def test_shell_wrappers_are_read(self):
        self.refused(["bash -c 'git push origin main'", 'sh -c "gh pr merge 1"', 'eval git push origin main',
                      'sudo git push origin main', 'echo $(git push origin main)', 'FOO=1 git push origin main',
                      'true && (git push origin develop)', '/usr/bin/git push origin main'])

    def test_existing_refusals_stay(self):
        self.refused(['git rebase main', 'git reset --hard', 'git commit --amend', 'git filter-branch',
                      'docker compose up', 'ssh root@host uptime', 'git worktree add /tmp/x -b y'])



class GuardSharedWorktree(GuardFixture):
    """2026-11-06: four sessions shared one worktree. One ran checkout and merge, and the check
    of another failed with "tree or environment changed during check"."""

    def agent(self, name, cwd):
        """A live process named NAME (claude or codex) with its working directory in CWD."""
        exe = self.tmp / 'bin' / name
        exe.parent.mkdir(exist_ok=True)
        if not exe.exists():
            shutil.copy(shutil.which('sleep'), exe)
        Path(cwd).mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen([str(exe), '60'], cwd=cwd)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        return process

    def guard_reason(self, command, cwd):
        payload = json.dumps({'cwd': str(cwd), 'tool_input': {'command': command}})
        return subprocess.run(['bash', str(GUARD)], input=payload, env=self.env, capture_output=True,
                              text=True, timeout=60).stderr

    MOVERS = ['git checkout main', 'git switch -c feat/x', 'git merge stale', 'git reset --soft HEAD~1',
              'git reset', 'git pull', 'git stash pop', 'git stash apply', 'git cherry-pick stale',
              'git revert HEAD']

    def test_head_moves_are_refused_where_another_agent_works(self):
        self.agent('claude', self.other / 'docs')
        self.refused(self.MOVERS, cwd=self.other)
        self.refused([f'git -C {self.other} checkout main', f'cd {self.other} && git merge stale'], cwd=self.mine)
        reason = self.guard_reason('git checkout main', self.other)
        self.assertIn('another live agent', reason)
        self.assertIn('Commit on the bench', reason)
        self.assertIn('git show', reason)

    def test_reads_commits_and_other_worktrees_pass(self):
        self.agent('codex', self.other)
        self.allowed(['git status', 'git diff', 'git show stale:file', 'git log', 'git stash list',
                      'git merge --abort', 'git cherry-pick --abort', 'git commit -m "fix(x): y"'],
                     cwd=self.other)
        self.allowed(self.MOVERS[:3], cwd=self.mine)

    def test_a_nested_worktree_is_not_its_parent(self):
        nested = self.repo / '.claude/worktrees/slot-1'
        self.git(self.repo, 'worktree', 'add', '-q', '--detach', str(nested))
        self.agent('claude', nested)
        self.allowed(['git checkout -q stale'], cwd=self.repo)
        self.refused(['git checkout -q stale'], cwd=nested)

    def test_the_agent_that_runs_the_guard_is_not_another_agent(self):
        bash = self.tmp / 'bin' / 'claude'
        bash.parent.mkdir(exist_ok=True)
        shutil.copy(shutil.which('bash'), bash)
        payload = json.dumps({'cwd': str(self.other), 'tool_input': {'command': 'git checkout main'}})
        done = subprocess.run([str(bash), str(GUARD)], input=payload, cwd=self.other, env=self.env,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == '__main__':
    unittest.main()
