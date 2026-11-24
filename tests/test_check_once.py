"""hooks/check-once.sh runs the check of a repository from bin/check, package.json or scripts/check."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'hooks/check-once.sh'


class CheckSources(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='check-once-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / 'repo'
        self.repo.mkdir()
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'TMPDIR')}
        self.env.update(HOME=str(self.tmp), GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
                        DEV_PLATFORM_ENV_DIR=str(self.tmp / 'env.d'))
        self.run_cmd('git', 'init', '-q', '-b', 'main')
        (self.repo / 'source').write_text('initial\n')

    def run_cmd(self, *args, expected=0):
        result = subprocess.run([str(a) for a in args], cwd=self.repo, env=self.env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def script(self, relative, marker):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'#!/usr/bin/env bash\necho {marker} >> "$(git rev-parse --path-format=absolute --git-path ran)"\n')
        path.chmod(0o755)

    def ran(self):
        path = Path(self.run_cmd('git', 'rev-parse', '--path-format=absolute', '--git-path', 'ran').stdout.strip())
        return path.read_text().split() if path.exists() else []

    def commit(self):
        self.run_cmd('git', 'add', '.')
        self.run_cmd('git', 'commit', '-qm', 'test: fixture')

    def check(self, expected=0):
        return self.run_cmd('bash', HOOK, expected=expected)

    def test_scripts_check_runs_when_it_is_the_only_source(self):
        self.script('scripts/check', 'scripts')
        self.commit()
        self.check()
        self.assertEqual(self.ran(), ['scripts'])
        self.check()                                   # the second run is cached
        self.assertEqual(self.ran(), ['scripts'])

    def test_bin_check_wins_over_scripts_check(self):
        self.script('bin/check', 'bin')
        self.script('scripts/check', 'scripts')
        self.commit()
        self.check()
        self.assertEqual(self.ran(), ['bin'])

    def test_package_json_check_wins_over_scripts_check(self):
        bun = self.tmp / 'bun'
        bun.write_text('#!/bin/sh\necho package >> "$(git rev-parse --path-format=absolute --git-path ran)"\n')
        bun.chmod(0o755)
        self.env['BUN_PATH'] = str(bun)
        (self.repo / 'package.json').write_text('{"scripts": {"check": "true"}}')
        self.script('scripts/check', 'scripts')
        self.commit()
        self.check()
        self.assertEqual(self.ran(), ['package'])

    def test_a_linked_worktree_of_a_second_session_does_not_change_the_result(self):
        self.script('scripts/check', 'scripts')
        self.run_cmd('git', 'add', '-A')
        self.run_cmd('git', 'commit', '-q', '-m', 'first')
        self.run_cmd('git', 'worktree', 'add', '-q', '-b', 'other', '.claude/worktrees/other')
        (self.repo / '.claude/worktrees/other/source').write_text('the uncommitted work of a second session\n')
        self.run_cmd('bash', HOOK)   # a dirty linked worktree was "dirty submodule cannot be cached"
        self.assertEqual(self.ran(), ['scripts'])
        (self.repo / '.claude/worktrees/other/source').write_text('more work\n')
        self.run_cmd('bash', HOOK)   # and it does not make this tree a new tree: the pass is kept
        self.assertEqual(self.ran(), ['scripts'])
        (self.repo / 'source').write_text('a change of this tree\n')
        self.run_cmd('bash', HOOK)
        self.assertEqual(self.ran(), ['scripts', 'scripts'])

    def test_no_source_refuses_to_record_a_pass(self):
        (self.repo / 'package.json').write_text('{"description": "check"}')
        self.commit()
        result = self.check(expected=2)
        self.assertIn('scripts/check', result.stdout)

    def test_source_names_the_check_and_hash_gives_the_pass_record_and_neither_runs_it(self):
        self.run_cmd('bash', HOOK, '--source', expected=2)
        self.script('scripts/check', 'scripts')
        self.commit()
        self.assertEqual(self.run_cmd('bash', HOOK, '--source').stdout, 'scripts/check\n')
        self.script('bin/check', 'bin')
        self.assertEqual(self.run_cmd('bash', HOOK, '--source').stdout, 'bin/check\n')
        (self.tmp / 'env.d').mkdir()
        (self.tmp / 'env.d/repo.sh').write_text("export DEV_PLATFORM_CHECK='make all-checks'\n")
        self.assertEqual(self.run_cmd('bash', HOOK, '--source').stdout, 'make all-checks\n')
        (self.tmp / 'env.d/repo.sh').unlink()
        digest = self.run_cmd('bash', HOOK, '--hash').stdout
        self.assertEqual(self.ran(), [])
        self.check()
        record = Path(self.run_cmd('git', 'rev-parse', '--path-format=absolute', '--git-path', 'dev-platform/check-pass').stdout.strip())
        self.assertEqual(record.read_text(), digest)

    def test_failing_scripts_check_is_not_cached(self):
        path = self.repo / 'scripts/check'
        path.parent.mkdir()
        path.write_text('#!/usr/bin/env bash\nexit 5\n')
        path.chmod(0o755)
        self.commit()
        self.check(expected=1)
        self.run_cmd('bash', HOOK, '--status', expected=1)


if __name__ == '__main__':
    unittest.main()
