"""Real Git/check fixtures, no user config, network, AI workers, or external writes."""
import json
import os
from pathlib import Path
import pty
import signal
import subprocess
import sys
import tempfile
import time
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CHECK = PLATFORM / 'hooks/check-once.sh'
LOOP = PLATFORM / 'skills/loop/scripts/loop.sh'
RIG = 'feat/work'
GUARD = PLATFORM / 'hooks/pre-tool-use-guard.sh'
GHX = PLATFORM / 'skills/loop/scripts/ghx'


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='platform-test-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.config = self.base / 'config'
        self.config.mkdir()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.fakebin = self.base / 'fakebin'
        self.fakebin.mkdir()
        # OpenRig is never reached from a test: rig records what it was asked to send.
        rig = self.fakebin / 'rig'
        rig.write_text(f'#!/bin/sh\necho "$*" >> {self.base / "rig.calls"}\n')
        rig.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'TMPDIR')}
        self.env.update(HOME=str(self.home), GIT_CONFIG_NOSYSTEM='1',
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0',
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
                        DEV_PLATFORM_REPOS=str(self.config / 'repos.conf'),
                        DEV_PLATFORM_BRIEF=str(self.config / 'absent.conf'),
                        DEV_PLATFORM_PERSONAL=str(self.config / 'personal.conf'),
                        DEV_PLATFORM_ENV_DIR=str(self.config / 'env.d'),
                        LOOP_STATE_DIR=str(self.base / 'state'),
                        GH_CALLS=str(self.base / 'gh.calls'))
        (self.config / 'personal.conf').write_text('')
        self.env['PATH'] = str(self.fakebin) + os.pathsep + self.env['PATH']
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.run_cmd('git', 'init', '-q', '-b', 'main', cwd=self.repo)
        (self.repo / 'source').write_text('initial\n')
        (self.repo / 'bin').mkdir()
        self.write_check('echo checked >> "$(git rev-parse --path-format=absolute --git-path calls)"\n')
        self.commit()
        self.configure()

    def run_cmd(self, *args, cwd=None, expected=0, input=None, env=None):
        result = subprocess.run([str(a) for a in args], cwd=cwd or self.repo,
                                env=env or self.env, input=input, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=25)
        if expected is not None:
            self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def commit(self):
        self.run_cmd('git', 'add', '.')
        self.run_cmd('git', 'commit', '-qm', 'test: fixture')

    def write_check(self, body):
        check = self.repo / 'bin/check'
        check.write_text('#!/usr/bin/env bash\nset -eu\n' + body)
        check.chmod(0o755)

    def configure(self, base='main', personal=False, identity='owner', path=None):
        (self.config / 'repos.conf').write_text(f'test/repo\t{path or self.repo}\t{identity}\t{base}\n')
        (self.config / 'personal.conf').write_text(str(self.repo) + '\n' if personal else '')

    def calls(self, cwd=None):
        gitdir = self.run_cmd('git', 'rev-parse', '--path-format=absolute', '--git-path', 'calls', cwd=cwd).stdout.strip()
        p = Path(gitdir)
        return len(p.read_text().splitlines()) if p.exists() else 0

    def check(self, *args, **kwargs):
        return self.run_cmd('bash', CHECK, *args, **kwargs)

    def setup_remote(self):
        remote = self.base / 'remote.git'
        self.run_cmd('git', 'clone', '--bare', '-q', self.repo, remote)
        self.run_cmd('git', 'remote', 'add', 'origin', remote)
        self.run_cmd('git', 'fetch', '-q', 'origin')
        self.run_cmd('git', 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
        gh = self.fakebin / 'gh'
        gh.write_text('''#!/usr/bin/env python3
import os,sys
with open(os.environ['GH_CALLS'], 'a') as f: f.write(' '.join(sys.argv[1:])+'\\n')
if sys.argv[1:3] in (['issue','list'], ['pr','list']): print('[]')
else: sys.exit('external operation refused by fixture')
''')
        gh.chmod(0o755)
        claude = self.fakebin / 'claude'
        claude.write_text('#!/bin/sh\necho UNEXPECTED_WORKER >&2\nexit 99\n')
        claude.chmod(0o755)

    def loop(self, *args, **kwargs):
        return self.run_cmd('bash', LOOP, args[0], 'test/repo', *args[1:], **kwargs)

    def ctl(self):
        return self.base / 'state/test__repo'


class CheckTests(Fixture):
    def test_artifacts_ignored_source_and_untracked_invalidated(self):
        self.check('--status', expected=1)
        self.assertEqual(self.calls(), 0)
        self.check()
        (self.repo / '.worker-pr.md').write_text('after check')
        (self.repo / 'notes').mkdir()
        (self.repo / 'notes/.worker-report.md').write_text('nested artifact')
        self.check('--status')
        self.check()
        self.assertEqual(self.calls(), 1)
        (self.repo / 'source').write_text('edited\n')
        self.check('--status', expected=1)
        self.check()
        self.assertEqual(self.calls(), 2)
        (self.repo / 'new file\nwith newline').write_text('untracked source')
        self.check('--status', expected=1)
        self.check()
        self.assertEqual(self.calls(), 3)
        (self.repo / 'new file\nwith newline').write_text('changed again')
        self.check('--status', expected=1)

    def test_index_changes_even_when_worktree_reverted(self):
        self.check()
        (self.repo / 'source').write_text('staged\n')
        self.run_cmd('git', 'add', 'source')
        (self.repo / 'source').write_text('initial\n')
        self.check('--status', expected=1)
        self.check()
        self.assertEqual(self.calls(), 2)

    def test_tracked_artifacts_not_ignored(self):
        (self.repo / '.worker-source').write_text('tracked')
        self.commit()
        self.check()
        (self.repo / '.worker-source').write_text('changed')
        self.check('--status', expected=1)

    def test_failure_never_caches(self):
        self.write_check('exit 7\n')
        self.check(expected=1)
        self.check('--status', expected=1)
        self.write_check('echo passing\n')
        self.check()
        self.check('--status')

    def test_changed_during_check_is_not_blessed(self):
        self.write_check("printf 'changed during check\\n' >> source\n")
        result = self.check(expected=1)
        self.assertIn('changed during check', result.stdout)
        self.check('--status', expected=1)

    def test_missing_check_fails_closed(self):
        (self.repo / 'bin/check').unlink()
        (self.repo / 'package.json').write_text('{"description":"check"}')
        self.check(expected=2)
        self.check('--status', expected=2)

    def test_env_key_main_and_linked_worktree(self):
        envdir = self.config / 'env.d'
        envdir.mkdir()
        (envdir / 'repo.sh').write_text('export EXPECTED_VALUE=shared\n')
        self.write_check('[ "${EXPECTED_VALUE:-}" = shared ]\necho checked >> "$(git rev-parse --path-format=absolute --git-path calls)"\n')
        self.commit()
        self.check()
        linked = self.base / 'linked'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'test/linked', linked)
        self.check('--status', cwd=linked, expected=1)
        self.check(cwd=linked)
        self.assertEqual(self.calls(linked), 1)
        self.assertEqual(self.calls(), 1)
        (envdir / 'repo.sh').write_text('export EXPECTED_VALUE=changed\n')
        self.check('--status', expected=1)
        self.check('--status', cwd=linked, expected=1)
        self.check(cwd=linked, expected=1)

    def test_dirty_submodule_fails_closed(self):
        sub = self.base / 'sub-source'
        self.run_cmd('git', 'clone', '-q', '--local', self.repo, sub)
        self.run_cmd('git', '-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', str(sub), 'module')
        self.commit()
        self.check()
        (self.repo / 'module/source').write_text('dirty module')
        result = self.check('--status', expected=1)
        self.assertIn('dirty submodule cannot be cached', result.stdout)
        self.check(expected=1)

    def test_pinned_bun_selected_after_env(self):
        (self.repo / 'bin/check').unlink()
        (self.repo / 'package.json').write_text('{"scripts":{"check":"fixture"}}')
        bun = self.base / 'pinned-bun'
        bun.write_text('#!/bin/sh\n[ "$1 $2" = "run check" ]\n')
        bun.chmod(0o755)
        envdir = self.config / 'env.d'; envdir.mkdir()
        (envdir / 'repo.sh').write_text(f'BUN_PATH="{bun}"\n')
        self.check()

    def test_existing_lock_does_not_run_check(self):
        lock = self.repo / '.git/dev-platform/check-lock'
        lock.mkdir(parents=True)
        self.check(expected=3)
        self.assertEqual(self.calls(), 0)


class LoopTests(Fixture):
    def test_main_base_start_and_pinning(self):
        self.setup_remote()
        self.loop('start', RIG)
        ctl = self.ctl()
        self.assertEqual((ctl / 'rig-base').read_text().strip(), 'main')
        day = (ctl / 'rig-branch').read_text().strip()
        self.assertEqual(self.run_cmd('git', 'rev-parse', day).stdout,
                         self.run_cmd('git', 'rev-parse', 'origin/main').stdout)
        self.configure(base='develop')
        self.assertIn('origin/main', self.loop('status').stdout)
        self.loop('start', RIG, expected=3)

    def test_explicit_stacked_base(self):
        self.run_cmd('git', 'branch', 'fix/bootstrap')
        self.setup_remote()
        self.configure(base='fix/bootstrap', personal=True)
        self.loop('start', RIG)
        self.assertEqual((self.ctl() / 'rig-base').read_text().strip(), 'fix/bootstrap')

    def test_personal_remote_default_main(self):
        self.setup_remote()
        self.configure(base='', personal=True)
        self.loop('start', RIG)
        self.assertEqual((self.ctl() / 'rig-base').read_text().strip(), 'main')

    def test_personal_symlink_default_main(self):
        self.setup_remote()
        alias = self.base / 'repo-alias'
        alias.symlink_to(self.repo, target_is_directory=True)
        self.configure(base='', path=alias)
        (self.config / 'personal.conf').write_text(str(alias) + '\n')
        self.loop('start', RIG)
        self.assertEqual((self.ctl() / 'rig-base').read_text().strip(), 'main')

    def test_personal_linked_alias_default_main(self):
        self.setup_remote()
        linked = self.base / 'linked'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'test/linked', linked)
        alias = self.base / 'linked-alias'
        alias.symlink_to(linked, target_is_directory=True)
        self.configure(base='', path=alias)
        (self.config / 'personal.conf').write_text(str(alias) + '\n')
        self.loop('start', RIG)
        self.assertEqual((self.ctl() / 'rig-base').read_text().strip(), 'main')

    def test_professional_stays_develop_even_if_default_main(self):
        self.run_cmd('git', 'branch', 'develop')
        self.setup_remote()
        self.configure(base='', personal=False)
        self.loop('start', RIG)
        self.assertEqual((self.ctl() / 'rig-base').read_text().strip(), 'develop')

    def test_mapping_accepts_linked_worktree(self):
        self.setup_remote()
        linked = self.base / 'linked'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'test/linked', linked)
        self.configure(path=linked)
        self.loop('status')

    def test_tidy_reads_remote_branches_past_origin_head(self):
        self.setup_remote()
        self.run_cmd('git', 'push', '-q', 'origin', 'HEAD:refs/heads/fix/done')
        self.run_cmd('git', 'fetch', '-q', 'origin')
        out = self.loop('tidy').stdout
        self.assertNotIn('origin/origin', out)
        self.assertIn('remote branches merged into origin/main:\n  fix/done', out)

    def test_owner_gates_no_bypass_or_network(self):
        self.setup_remote()
        env = dict(self.env, LOOP_AGENT_ACTS='1')
        for personal in (False, True):
            self.configure(personal=personal)
            for args in [('finish', '1'), ('tidy', '--apply')]:
                with self.subTest(personal=personal, args=args):
                    self.loop(*args, env=env, expected=4)
        self.assertFalse(Path(self.env['GH_CALLS']).exists())

    def test_close_ready_and_professional_push_gated(self):
        self.setup_remote(); self.loop('start', RIG)
        self.loop('close', '--push', expected=4)
        self.configure(personal=True)
        self.loop('close', '--ready', expected=4)
        self.loop('close', '--push', '--ready', expected=4)

    def test_only_does_not_override_plan(self):
        self.setup_remote(); self.loop('start', RIG)
        result = self.loop('go', 'only', '999')
        self.assertIn('nothing to dispatch', result.stdout)
        self.assertEqual(list(self.repo.glob('.claude/worktrees/loop-*')), [])

    def test_invalid_limits_and_base_refused(self):
        for limit in ('0', '-1', 'bogus'):
            self.loop('status', env=dict(self.env, LOOP_CAP=limit), expected=2)
        self.configure(base='--bad')
        self.loop('status', expected=2)

    def test_resume_respects_cap_without_launch(self):
        self.setup_remote(); self.loop('start', RIG)
        day = (self.ctl() / 'rig-branch').read_text().strip().replace('/', '__')
        result_path = self.ctl() / day / 'workers/1.exit'
        process = subprocess.Popen([sys.executable, str(PLATFORM / 'skills/loop/scripts/worker-run.py'),
                                    '5', str(result_path), '--', sys.executable, '-c',
                                    'import time; time.sleep(3)'], cwd=self.repo, env=self.env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            result_path.with_suffix('.pid').write_text(str(process.pid))
            deadline = time.monotonic() + 2
            while not result_path.with_suffix('.identity.json').exists() and time.monotonic() < deadline:
                time.sleep(.02)
            result = self.loop('resume', '2', env=dict(self.env, LOOP_CAP='1'))
            self.assertIn('cap reached', result.stdout)
        finally:
            process.wait(timeout=7)

    def test_close_uses_base_and_accurate_verification(self):
        self.setup_remote(); self.loop('start', RIG)
        ctl = self.ctl(); day = (ctl / 'rig-branch').read_text().strip().replace('/', '__')
        out = ctl / day
        (out / 'folded.tsv').write_text('1\tfix/example\t123\tnow\n')
        (out / 'folded-1.md').write_text('## What changed and why\n\nFixture.\n\n## Verification\n\nFixture check.\n\n## Deploy and provider impact\n\nNone.\n\n## Review notes\n\nReview locally.\n')
        result = self.loop('close')
        self.assertIn('--base "main"', result.stdout)
        body = (out / 'pr.md').read_text()
        self.assertIn('integrated head passed', body)
        self.assertNotIn('bun run check', body)
        self.assertNotIn('every merge', body)
        self.loop('close', '--as', 'main', expected=2)
        (out / 'folded-1.md').write_text('## What changed and why\n\nGenerated with Codex\n')
        self.loop('close', expected=1)


    def in_owner_terminal(self, *args):
        """Run a loop verb with a pseudo-terminal on stdin and stdout, as the owner's own shell."""
        master, slave = pty.openpty()
        process = subprocess.Popen(['bash', LOOP, *args], cwd=self.repo, env=self.env,
                                   stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        output = b''
        while True:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            output += chunk
        process.wait(timeout=25)
        os.close(master)
        return output.decode()

    def test_fold_refuses_an_attached_seat_and_committed_managed_context(self):
        self.setup_remote(); self.loop('start', RIG)
        day = (self.ctl() / 'rig-branch').read_text().strip()
        wt = self.repo / '.claude/worktrees/loop-1-example'
        self.run_cmd('git', 'worktree', 'add', '-q', '-b', 'fix/example-1', wt, day)
        (wt / 'source').write_text('changed\n')
        (wt / 'CLAUDE.md').write_text('<!-- BEGIN OpenRig MANAGED BLOCK: role -->\nx\n<!-- END OpenRig MANAGED BLOCK: role -->\n')
        self.run_cmd('git', 'commit', '-qam', 'fix: example', cwd=wt)
        fold = lambda: self.in_owner_terminal('fold', 'test/repo', '1')
        self.assertIn('seat is still attached', fold())
        (wt / 'CLAUDE.md').unlink()
        (wt / '.openrig').mkdir()
        (wt / '.openrig/context-collector.cjs').write_text('collector\n')
        self.run_cmd('git', 'add', '-f', '.openrig', cwd=wt)
        self.run_cmd('git', 'commit', '-qm', 'fix: stray', cwd=wt)
        self.assertIn("commits OpenRig's managed context", fold())
        self.assertTrue(wt.exists())


    def test_seat_rig_gives_a_resumed_issue_a_seat_instead_of_a_headless_worker(self):
        self.setup_remote(); self.loop('start', RIG)
        day = (self.ctl() / 'rig-branch').read_text().strip().replace('/', '__')
        wt = self.repo / '.claude/worktrees/loop-1-example'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'fix/example-1', wt)
        (wt / '.worker-brief.md').write_text('Scope (only these path prefixes may change): source\n')
        (self.fakebin / 'gh').write_text('#!/bin/sh\necho \'{"title":"Example","labels":[],"body":"Scope: source"}\'\n')
        calls = self.base / 'dev-workspace.calls'
        workspace = self.fakebin / 'dev-workspace'
        workspace.write_text(f'#!/bin/sh\necho "$*" >> {calls}\n')
        for path in (self.fakebin / 'gh', workspace):
            path.chmod(0o755)
        env = dict(self.env, DEV_WORKSPACE=str(workspace), LOOP_SEAT_RIG='development-helm')
        self.loop('resume', '1', env=env)
        self.loop('resume', '1', env=dict(env, LOOP_SEAT_RUNTIME='codex'))
        self.loop('resume', '1', env=dict(env, LOOP_SEAT_RUNTIME='codex', LOOP_SEAT_ACCOUNT='openai-gmail'))
        recorded = calls.read_text().splitlines()
        self.assertEqual(recorded[0], f'add-worker claude --rig development-helm --cwd {wt}')
        self.assertEqual(recorded[-2], f'add-worker codex --rig development-helm --cwd {wt}')
        self.assertEqual(recorded[-1], f'add-worker codex --rig development-helm --cwd {wt} --account openai-gmail')
        self.assertFalse((self.ctl() / day / 'workers/1.pid').exists())


class LocalLoopTests(Fixture):
    """A local repository: tasks are files, the rig branch merges back locally, GitHub is never called."""

    def setUp(self):
        super().setUp()
        self.run_cmd('git', 'checkout', '-qb', 'develop')
        tasks = self.repo / 'docs/tasks'
        tasks.mkdir(parents=True)
        (tasks / 'README.md').write_text('# Tasks\n')
        (tasks / '1-game-rules.md').write_text(
            '# Game rules\n\nStatus: ready\nLabels: enhancement\nScope: source\nDepends on: none\n\nBuild it.\n')
        (tasks / '2-polish.md').write_text('# Polish\n\nStatus: ready\nScope: extra\nDepends on: #1\n\nLater.\n')
        (tasks / '3-draft.md').write_text('# Draft\n\nStatus: draft\nScope: other\nDepends on: none\n')
        self.commit()
        self.configure(base='develop', personal=True, identity='local')
        gh = self.fakebin / 'gh'
        gh.write_text('#!/bin/sh\necho "$*" >> "$GH_CALLS"\nexit 99\n')
        gh.chmod(0o755)
        self.workspace = self.fakebin / 'dev-workspace'
        self.workspace.write_text(f'#!/bin/sh\necho "$*" >> {self.base / "dev-workspace.calls"}\n')
        self.workspace.chmod(0o755)
        self.addCleanup(lambda: self.assertFalse((self.base / 'gh.calls').exists(), 'a local repository called gh'))

    def in_owner_terminal(self, *args):
        return LoopTests.in_owner_terminal(self, *args)

    def test_a_rig_branch_runs_from_task_files_to_a_local_merge(self):
        start = self.loop('start', RIG).stdout
        self.assertIn('cut from develop', start)
        self.assertIn('#1 lane=', start)
        self.assertIn('#2 waits on #1', start)
        self.assertNotIn('#3 lane=', start)
        env = dict(self.env, DEV_WORKSPACE=str(self.workspace), LOOP_SEAT_RIG='helm-repo')
        self.assertIn('(seat in helm-repo, told to start)', self.loop('go', env=env).stdout)
        self.assertIn('send workers-issue-1@helm-repo Start task #1 now: read .worker-brief.md',
                      (self.base / 'rig.calls').read_text())
        wt = next((self.repo / '.claude/worktrees').glob('loop-1-*'))
        brief = (wt / '.worker-brief.md').read_text()
        self.assertIn('Read the task file `docs/tasks/1-game-rules.md`', brief)
        self.assertNotIn('gh issue view', brief)
        self.assertIn('feat/', self.run_cmd('git', 'branch', '--show-current', cwd=wt).stdout)
        (wt / 'source').write_text('changed\n')
        self.run_cmd('git', 'commit', '-qam', 'feat(game): rules', cwd=wt)
        (wt / '.worker-pr.md').write_text('## What changed and why\n\nRules.\n\nCloses #1\n')
        # A control seat folds a finished child into the rig branch; no owner terminal needed.
        self.assertIn('folded', self.loop('fold', '1').stdout)
        self.assertIn('close test/repo --merge', self.loop('close').stdout)
        self.loop('close', '--push', expected=2)
        self.loop('close', '--merge', expected=4)  # landing on the base stays the owner's
        self.assertIn('merged feat/work into develop', self.in_owner_terminal('close', 'test/repo', '--merge'))
        self.assertEqual((self.repo / 'source').read_text(), 'changed\n')
        self.assertTrue((self.repo / 'docs/tasks/done/1-game-rules.md').exists())
        self.assertFalse((self.repo / 'docs/tasks/1-game-rules.md').exists())
        self.assertFalse((self.ctl() / 'rig-branch').exists())
        self.assertEqual(self.run_cmd('git', 'log', '--merges', '-1', '--format=%s').stdout.strip(), 'feat: work (#1)')
        self.assertEqual((self.ctl() / 'steer').read_text().strip(), 'pause')
        self.assertIn('#2 lane=', self.loop('plan').stdout)
        self.assertIn('merged locally into develop', self.loop('status').stdout)
        self.assertIn('CYCLE', self.loop('collect').stdout)
        self.assertIn('read-only', self.loop('tidy').stdout)

    def test_tasks_are_written_numbered_and_checked_where_the_command_runs(self):
        self.assertEqual(self.loop('tasks').stdout.splitlines(),
                         ['#1 ready Game rules', '#2 ready Polish', '#3 draft Draft'])
        self.assertEqual(self.loop('tasks', 'check').stdout.strip(), 'ok: 3 open task(s)')
        # A task moved to done keeps its number: numbers are never reused.
        (self.repo / 'docs/tasks/done').mkdir()
        self.run_cmd('git', 'mv', 'docs/tasks/3-draft.md', 'docs/tasks/done/3-draft.md')
        self.assertEqual(self.loop('tasks', 'next').stdout.strip(), '4')
        self.run_cmd('git', 'commit', '-qm', 'chore(tasks): done')
        # Written in the worktree the command runs in (an intake branch), not the mapped checkout.
        wt = self.base / 'intake'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'docs/plan', wt)
        path = self.loop('tasks', 'new', 'Score: keep it', '--scope', 'src/score/', '--depends', '#1',
                         '--labels', 'enhancement', '--ready', cwd=wt).stdout.strip()
        self.assertEqual(path, 'docs/tasks/4-score-keep-it.md')
        self.assertFalse((self.repo / path).exists())
        self.assertEqual((wt / path).read_text().splitlines()[:6],
                         ['# Score: keep it', '', 'Status: ready', 'Labels: enhancement',
                          'Scope: src/score/', 'Depends on: #1'])
        self.run_cmd('git', 'add', '.', cwd=wt)
        self.run_cmd('git', 'commit', '-qm', 'docs(tasks): score', cwd=wt)
        # A second branch that has not seen the first takes the same number; the merge shows it.
        self.assertEqual(self.loop('tasks', 'new', 'Sound', '--scope', 'src/sound/').stdout.strip(),
                         'docs/tasks/4-sound.md')
        self.run_cmd('git', 'add', '.')
        self.run_cmd('git', 'commit', '-qm', 'docs(tasks): sound')
        self.run_cmd('git', 'merge', '-q', '--no-ff', '-m', 'merge', 'docs/plan')
        self.assertIn('more than one task file for #4', self.loop('tasks', 'check', expected=1).stdout)
        self.loop('tasks', expected=1)
        self.run_cmd('git', 'mv', 'docs/tasks/4-sound.md', 'docs/tasks/5-sound.md')
        self.run_cmd('git', 'commit', '-qm', 'fix(tasks): renumber')
        listed = self.loop('tasks').stdout
        self.assertIn('#4 ready Score: keep it', listed)
        self.assertIn('#5 draft Sound', listed)
        self.assertIn('#4 waits on #1', self.loop('plan').stdout)
        (self.repo / 'docs/tasks/6-bad.md').write_text('Status: soon\nDepends on: #6, #9, 7\n')
        problems = self.loop('tasks', 'check', expected=1).stdout
        for expected in ("no `# ` title heading", "Status must be ready or draft, not 'soon'",
                         'no Scope: line', 'depends on itself', 'depends on #9, which has no task file',
                         "Depends on: '7' is not #N"):
            self.assertIn(expected, problems)
        self.loop('tasks', 'new', 'No scope', expected=2)

    def test_state_reports_the_rig_branch_and_each_worker_as_json(self):
        self.assertIsNone(json.loads(self.loop('state').stdout)['rig'])
        self.loop('start', RIG)
        env = dict(self.env, DEV_WORKSPACE=str(self.workspace), LOOP_SEAT_RIG='helm-repo')
        self.loop('go', 'only', '1', env=env)
        wt = next((self.repo / '.claude/worktrees').glob('loop-1-*'))
        (wt / 'CLAUDE.md').write_text('<!-- BEGIN OpenRig MANAGED BLOCK: role -->\n')
        (wt / 'source').write_text('changed\n')
        self.run_cmd('git', 'commit', '-qam', 'feat(game): rules', cwd=wt)
        state = json.loads(self.loop('state').stdout)
        self.assertEqual((state['rig'], state['base'], state['mode']), (RIG, 'develop', 'local'))
        self.assertEqual(state['workers'], [{'issue': 1, 'branch': 'feat/game-rules-1', 'worktree': str(wt),
                                             'ahead': '1', 'state': 'working', 'seat': 'helm-repo'}])
        self.assertIn('#1 feat/game-rules-1 ahead 1: working, seat in helm-repo', self.loop('status').stdout)

    def test_only_a_spec_task_may_change_the_specification(self):
        spec = self.repo / 'docs/spec'
        spec.mkdir(parents=True)
        (spec / 'SDD.md').write_text('**GR-01.** The snake must grow when it eats.\n'
                                     '<!-- id: SDD-GR-01 | tdd: TDD-1.1.1 | status: pending:#1 -->\n'
                                     '\n**GR-02.** The game must end at a wall.\n')
        (self.repo / 'docs/tasks/4-amend.md').write_text(
            '# Amend growth\n\nStatus: ready\nLabels: spec\nScope: docs/spec\nDepends on: none\n')
        self.commit()
        self.loop('start', RIG)
        env = dict(self.env, DEV_WORKSPACE=str(self.workspace), LOOP_SEAT_RIG='helm-repo')
        self.loop('go', 'only', '1', '4', env=env)
        build = next((self.repo / '.claude/worktrees').glob('loop-1-*'))
        (build / 'source').write_text('changed\n')
        (build / 'docs/spec/SDD.md').write_text('**GR-01.** The snake must grow by two when it eats.\n'
                                              '<!-- id: SDD-GR-01 | tdd: TDD-1.1.1 | status: implemented -->\n'
                                              '\n**GR-02.** The game must end at a wall.\n')
        self.run_cmd('git', 'commit', '-qam', 'feat(game): rules', cwd=build)
        refused = self.loop('fold', '1').stdout
        self.assertIn('changes the specification; only a spec task may', refused)
        self.assertIn('-**GR-01.** The snake must grow when it eats.', refused)
        (build / 'docs/spec/SDD.md').write_text('**GR-01.** The snake must grow when it eats.\n'
                                              '<!-- id: SDD-GR-01 | tdd: TDD-1.1.1 | status: implemented -->\n'
                                              '\n**GR-02.** The game must end at a wall.\n')
        self.run_cmd('git', 'commit', '-qam', 'docs(spec): mark GR-01 implemented', cwd=build)
        self.assertIn('folded', self.loop('fold', '1').stdout)
        amend = next((self.repo / '.claude/worktrees').glob('loop-4-*'))
        (amend / 'docs/spec/SDD.md').write_text('**GR-01.** The snake must grow when it eats.\n'
                                              '<!-- id: SDD-GR-01 | tdd: TDD-1.1.1 | status: pending:#1 -->\n'
                                              '\n**GR-02.** The game must end at a wall or at itself.\n')
        self.run_cmd('git', 'commit', '-qam', 'docs(spec): grow by two', cwd=amend)
        self.assertIn('folded', self.loop('fold', '4').stdout)

    def test_fold_releases_the_seat_and_requires_a_passing_check(self):
        self.loop('start', RIG)
        env = dict(self.env, DEV_WORKSPACE=str(self.workspace), LOOP_SEAT_RIG='helm-repo')
        self.loop('go', 'only', '1', env=env)
        wt = next((self.repo / '.claude/worktrees').glob('loop-1-*'))
        (wt / 'CLAUDE.md').write_text('<!-- BEGIN OpenRig MANAGED BLOCK: role -->\nx\n<!-- END OpenRig MANAGED BLOCK: role -->\n')
        (wt / 'source').write_text('changed\n')
        (wt / 'bin/check').write_text('#!/usr/bin/env bash\necho lint failed\nexit 1\n')
        self.run_cmd('git', 'commit', '-qam', 'feat(game): rules', cwd=wt)
        refused = self.loop('fold', '1', env=env).stdout
        self.assertIn('released its seat in helm-repo', refused)
        self.assertIn(f'remove-worker --rig helm-repo --cwd {wt}', (self.base / 'dev-workspace.calls').read_text())
        self.assertIn('the check fails', refused)
        self.assertIn('lint failed', refused)
        self.assertTrue(wt.exists())
        (wt / 'CLAUDE.md').unlink()
        (wt / 'bin/check').write_text('#!/usr/bin/env bash\necho checked\n')
        self.run_cmd('git', 'commit', '-qam', 'fix(check): pass', cwd=wt)
        self.assertIn('folded', self.loop('fold', '1', env=env).stdout)
        self.assertFalse(wt.exists())

    def test_workers_take_model_and_effort_from_the_setup_pstack_file(self):
        (self.repo / 'docs/tasks/4-spec.md').write_text(
            '# Spec\n\nStatus: ready\nLabels: spec\nScope: docs/spec\nDepends on: none\n')
        self.commit()
        (self.config / 'pstack-models.md').write_text(
            '# budget: medium (high)\nfeature, refactoring: sonnet-high\n'
            'judgment and prose: fable-max, codex:gpt-5.6-sol-max\n')
        calls = self.base / 'claude.calls'
        claude = self.fakebin / 'claude'
        claude.write_text('#!/usr/bin/env python3\nimport json, sys\n'
                          f'open({str(calls)!r}, "a").write(json.dumps(sys.argv[1:]) + "\\n")\n')
        claude.chmod(0o755)
        env = dict(self.env, DEV_PLATFORM_PSTACK_MODELS=str(self.config / 'pstack-models.md'))
        self.loop('start', RIG)
        self.loop('go', env=env)
        for _ in range(250):
            if calls.exists() and len(calls.read_text().splitlines()) == 2:
                break
            time.sleep(0.02)
        launched = {}
        for line in calls.read_text().splitlines():
            argv = json.loads(line)
            launched[argv[argv.index('--name') + 1].rsplit(' ', 1)[1]] = argv
        for issue, model, effort in (('#1', 'sonnet', 'high'), ('#4', 'fable', 'max')):
            argv = launched[issue]
            self.assertEqual(argv[argv.index('--model') + 1], model)
            self.assertEqual(argv[argv.index('--effort') + 1], effort)
        # A codex: entry is skipped for a Claude worker; the first Claude model on the line wins.
        (self.config / 'pstack-models.md').write_text('judgment and prose: codex:gpt-5.6-sol-max\n')
        self.assertIn('(opus)', self.loop('resume', '4', env=env).stdout)

    def test_tasks_refuse_a_github_backed_repository(self):
        self.configure(base='develop', personal=True, identity='owner')
        self.assertIn('GitHub issues', self.loop('tasks', expected=2).stdout)


class GuardTests(Fixture):
    def guard(self, command, expected):
        return self.run_cmd('bash', GUARD, input=json.dumps({'cwd': str(self.repo),
                            'tool_input': {'command': command}}), expected=expected)

    def test_hard_refusals_everywhere(self):
        for personal in (False, True):
            self.configure(personal=personal)
            for command in ('git push origin main', 'git push origin develop',
                            'git push --force origin fix/example', 'git push',
                            'git -C /tmp push origin main', 'git -c foo=bar rebase main',
                            'git commit --amend', 'git reset --hard',
                            'git checkout develop && git merge fix/example',
                            'gh pr merge 1', 'gh pr ready 1', 'gh pr review 1 --approve',
                            'docker compose restart', 'ssh root@host uptime'):
                with self.subTest(personal=personal, command=command):
                    self.guard(command, 2)
            self.guard('git status', 0)
            self.guard('git push -u origin fix/example', 0)

    def test_ghost_attribution_professional_only(self):
        command = 'git commit -m "Generated with Codex"'
        self.guard(command, 2)
        self.configure(personal=True)
        self.guard(command, 0)

    def test_desktop_script_workspace_refusal(self):
        desktop = self.home / 'Desktop' / 'probe.sh'
        for command in (f'cat > {desktop} <<EOF\necho bad\nEOF',
                        f'chmod +x {desktop}',
                        f'bash {desktop}',
                        'bash ~/Desktop/probe.sh'):
            with self.subTest(command=command):
                self.guard(command, 2)
        self.guard(f'ls {desktop}', 0)

    def test_ghx_owner_actions_refused_for_both_identities(self):
        self.setup_remote()
        for identity in ('owner', 'bot'):
            self.configure(identity=identity)
            for args in [('pr', 'merge', '1'), ('pr', 'ready', '1'),
                         ('pr', 'review', '1', '--approve'), ('api', 'repos/test/repo'),
                         ('pr', 'list', '--repo', 'other/repo')]:
                self.run_cmd('bash', GHX, 'test/repo', *args, expected=3)
        self.assertFalse(Path(self.env['GH_CALLS']).exists())

    def test_ghx_professional_bot_refused_before_credentials(self):
        self.configure(identity='bot')
        self.run_cmd('bash', GHX, 'test/repo', 'pr', 'list', expected=3)


class PersonalIdentityTests(Fixture):
    def setUp(self):
        super().setUp()
        self.linked = self.base / 'linked'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'test/linked', self.linked)
        self.alias = self.base / 'repo-alias'
        self.alias.symlink_to(self.repo, target_is_directory=True)
        self.linked_alias = self.base / 'linked-alias'
        self.linked_alias.symlink_to(self.linked, target_is_directory=True)
        # Credential access always stops at a local fixture; no secret is read.
        self.op_calls = self.base / 'op.calls'
        self.env['OP_CALLS'] = str(self.op_calls)
        op = self.fakebin / 'op'
        op.write_text('#!/bin/sh\necho called >> "$OP_CALLS"\nexit 1\n')
        op.chmod(0o755)

    def assert_identity(self, checkout, entry, personal):
        self.configure(base='', identity='bot', path=checkout)
        (self.config / 'personal.conf').write_text(str(entry) + '\n')
        command = 'git commit -m "Generated with Codex"'
        self.run_cmd('bash', GUARD, input=json.dumps({'cwd': str(checkout),
                     'tool_input': {'command': command}}), expected=0 if personal else 2)
        self.run_cmd('bash', GHX, 'test/repo', 'pr', 'list', expected=4 if personal else 3)
        self.assertEqual(self.op_calls.exists(), personal)
        if self.op_calls.exists():
            self.op_calls.unlink()

    def test_main_linked_and_symlink_entries_share_exact_identity(self):
        paths = (self.repo.resolve(), self.alias, self.linked.resolve(), self.linked_alias)
        for checkout in paths:
            for entry in paths:
                with self.subTest(checkout=checkout, entry=entry):
                    self.assert_identity(checkout, entry, True)

    def test_siblings_nested_repos_and_nonrepos_stay_professional(self):
        sibling = self.base / 'repo-other'
        nested = self.repo / 'nested-professional'
        for checkout in (sibling, nested):
            self.run_cmd('git', 'init', '-q', '-b', 'main', checkout)
            with self.subTest(checkout=checkout):
                self.assert_identity(checkout, self.alias, False)
                self.assert_identity(checkout, self.repo.resolve(), False)
        for entry in (self.base, self.base / 'missing'):
            with self.subTest(entry=entry):
                self.assert_identity(self.repo, entry, False)


class WorkerBoundTests(Fixture):
    def wait_for_file(self, path, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return
            time.sleep(0.02)
        self.fail(f'timed out waiting for {path}')

    def detached_supervisor(self, timed_out, title='Fix "quoted" $(touch leaked)\n parser.',
                            expected_name='fix(repo): Fix "quoted" $(touch leaked) parser #1', account=False):
        self.setup_remote()
        self.loop('start', RIG)
        day = (self.ctl() / 'rig-branch').read_text().strip().replace('/', '__')
        workers = self.ctl() / day / 'workers'
        wt = self.repo / '.claude/worktrees/loop-1-fixture'
        self.run_cmd('git', 'worktree', 'add', '-qb', 'fix/fixture', wt)
        (wt / '.worker-brief.md').write_text('Harmless lifecycle fixture only.\n')
        gh = self.fakebin / 'gh'
        issue = {'title': title, 'labels': [], 'body': 'Scope: source'}
        gh.write_text('#!/usr/bin/env python3\nprint(' + repr(json.dumps(issue)) + ')\n')
        claude = self.fakebin / 'claude'
        claude.write_text('''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
if sys.argv[1:]==['auth','status','--json']:
 print(json.dumps({'loggedIn':True,'authMethod':'claude.ai','apiProvider':'firstParty','email':'fixture@example.invalid','subscriptionType':'max'}))
 sys.exit(0)
assert sys.stdin.read() == ''
assert 'DO_NOT_INHERIT' not in os.environ
assert os.environ['SAFE_FIXTURE'] == 'yes'
Path('child.started').write_text(json.dumps({'pid': os.getpid(), 'parent': os.getppid(), 'argv': sys.argv[1:], 'native_home':os.getenv('CLAUDE_CONFIG_DIR')}))
print('fixture stdout', flush=True)
print('fixture stderr', file=sys.stderr, flush=True)
while not Path('child.release').exists(): time.sleep(0.02)
sys.exit(7)
''')
        env = dict(self.env, LOOP_WORKER_MAX_SECONDS='3' if timed_out else '10',
                   DO_NOT_INHERIT='fixture', SAFE_FIXTURE='yes', DEV_PLATFORM_ENV_PASS='SAFE_FIXTURE')
        if account:
            native_home = self.home / 'native-profile'
            native_home.mkdir()
            registry = self.home / '.config/dev-platform/accounts.json'
            registry.parent.mkdir(parents=True)
            registry.write_text(json.dumps({'version':1,'selected':'anthropic-apple' if account == 'default' else None,'bindings':{'anthropic-apple':{
                'home':str(native_home),'expected_email':'fixture@example.invalid'}}}))
            if account != 'default':
                env['LOOP_ACCOUNT_ID'] = 'anthropic-apple'
        ready = self.base / 'launcher.ready'
        # Keep a short-lived outer shell in its own group, then emulate tool cleanup.
        launcher = subprocess.Popen(
            ['bash', '-c', 'bash "$1" resume test/repo 1 && touch "$2"; exec sleep 20',
             'fixture-launcher', str(LOOP), str(ready)], cwd=self.repo, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        supervisor = child = None
        worker_finished = False
        try:
            self.wait_for_file(ready)
            self.wait_for_file(wt / 'child.started')
            metadata = json.loads((wt / 'child.started').read_text())
            child = metadata['pid']
            argv = metadata['argv']
            self.assertEqual(argv.count('--name'), 1)
            self.assertEqual(argv[argv.index('--name') + 1], expected_name)
            self.assertNotIn('--resume', argv, 'loop resume starts a new attempt, not a native resume')
            if account:
                self.assertEqual(metadata['native_home'], str(native_home.resolve()))
                receipt = json.loads((workers / '1.account.jsonl').read_text())
                self.assertEqual(receipt['account_id'], 'anthropic-apple')
            self.assertFalse((wt / 'leaked').exists(), 'issue titles must remain literal arguments')
            supervisor = int((workers / '1.pid').read_text())
            self.assertEqual(supervisor, metadata['parent'], 'PID must name the actual supervisor')
            os.killpg(launcher.pid, signal.SIGTERM)
            launcher.wait(timeout=3)
            time.sleep(0.1)
            os.kill(supervisor, 0)
            os.kill(child, 0)
            self.assertFalse((workers / '1.exit').exists(), 'supervisor must wait for its child')
            self.assertEqual(os.getpgid(supervisor), supervisor, 'supervisor must detach from launcher')
            if not timed_out:
                (wt / 'child.release').touch()
            self.wait_for_file(workers / '1.exit')
            worker_finished = True
            result = json.loads((workers / '1.exit').read_text())
            self.assertEqual(result['exit_code'], 124 if timed_out else 7)
            self.assertEqual(result['reason'], 'wall_time_limit' if timed_out else 'exited')
            if timed_out:
                self.assertLess(result['elapsed_seconds'], 8)
            log = (workers / '1.log').read_text()
            self.assertIn('fixture stdout', log)
            self.assertIn('fixture stderr', log)
            with self.assertRaises(ProcessLookupError):
                os.kill(child, 0)
        finally:
            # Only fixture process groups. Never touch real loop state or workers.
            # A completed fixture's numeric PID may already be gone or reused.
            # Do not signal stale groups after the supervisor recorded completion.
            remaining = [] if worker_finished else [supervisor, child]
            if launcher.poll() is None:
                remaining.append(launcher.pid)
            for pid in remaining:
                if pid is not None:
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            launcher.wait(timeout=3)

    def test_supervisor_survives_launcher_group_cleanup_and_reports_exit(self):
        self.detached_supervisor(timed_out=False)

    def test_supervisor_survives_launcher_group_cleanup_and_bounds_worker(self):
        self.detached_supervisor(timed_out=True)

    def test_worker_display_name_is_bounded(self):
        self.detached_supervisor(False, 'A' * 100, 'fix(repo): ' + 'A' * 60 + ' #1')

    def test_worker_display_name_handles_missing_title(self):
        self.detached_supervisor(False, None, 'fix(repo): Implement issue #1')

    def test_explicit_account_pins_new_worker_attempt_without_changing_supervisor(self):
        self.detached_supervisor(False, account=True)

    def test_shared_selection_pins_future_loop_workers(self):
        self.detached_supervisor(False, account='default')

    def test_account_preflight_fails_before_steer_change_or_worker_allocation(self):
        self.setup_remote()
        self.loop('start', RIG)
        before = (self.ctl() / 'steer').read_text()
        for account in ('openai-gmail', 'zai', 'anthropic-apple'):
            self.loop('go', env=dict(self.env, LOOP_ACCOUNT_ID=account), expected=2)
            self.assertEqual((self.ctl() / 'steer').read_text(), before)
            self.assertEqual(list(self.repo.glob('.claude/worktrees/loop-*')), [])
        registry = self.home / '.config/dev-platform/accounts.json'
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps({'version':1,'selected':'openai-gmail','bindings':{}}))
        self.loop('go', expected=2)
        self.assertEqual((self.ctl() / 'steer').read_text(), before)

    def test_unreadable_account_registry_never_falls_back_to_legacy_dispatch(self):
        self.setup_remote()
        self.loop('start', RIG)
        before = (self.ctl() / 'steer').read_bytes()
        registry = self.home / '.config/dev-platform/accounts.json'
        registry.parent.mkdir(parents=True, exist_ok=True)
        for contents in ('not json', '{"version":2,"bindings":{}}'):
            registry.write_text(contents)
            self.loop('go', expected=2)
            self.assertEqual((self.ctl() / 'steer').read_bytes(), before)
            self.assertEqual(list(self.repo.glob('.claude/worktrees/loop-*')), [])

    def test_supervisor_sanitizes_environment_and_reports_exit(self):
        result = self.base / 'worker.exit'
        env = dict(self.env, DO_NOT_INHERIT='fixture', SAFE_FIXTURE='yes', DEV_PLATFORM_ENV_PASS='SAFE_FIXTURE')
        command = "import os; assert 'DO_NOT_INHERIT' not in os.environ; assert os.environ['SAFE_FIXTURE']=='yes'"
        self.run_cmd(sys.executable, PLATFORM / 'skills/loop/scripts/worker-run.py',
                     '5', result, '--', sys.executable, '-c', command, env=env)
        self.assertEqual(json.loads(result.read_text())['exit_code'], 0)

    def test_supervisor_times_out_harmless_process(self):
        result = self.base / 'worker.exit'
        self.run_cmd(sys.executable, PLATFORM / 'skills/loop/scripts/worker-run.py',
                     '1', result, '--', sys.executable, '-c', 'import time; time.sleep(20)', expected=124)
        self.assertEqual(json.loads(result.read_text())['reason'], 'wall_time_limit')
