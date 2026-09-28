"""new-repo is installed as a link in ~/.local/bin and must still find the release's templates."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NewRepo(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        (self.tmp / 'bin').mkdir()
        (self.tmp / 'bin/new-repo').symlink_to(ROOT / 'bin/new-repo')
        home = self.tmp / 'home'
        home.mkdir()
        self.config = self.tmp / 'config'
        # No bun on PATH keeps the run offline; new-repo warns and still commits.
        self.env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'GIT_CONFIG_GLOBAL': str(home / '.gitconfig'),
                    'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com',
                    'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.com',
                    'DEV_PLATFORM_REPOS': str(self.config / 'repos.conf'),
                    'DEV_PLATFORM_PERSONAL': str(self.config / 'personal.conf')}

    def new_repo(self, *args):
        return subprocess.run([str(self.tmp / 'bin/new-repo'), str(self.tmp / 'game'), '--owner', 'someone', *args],
                              capture_output=True, text=True, env=self.env)

    def test_runs_through_a_link_like_the_installed_command(self):
        result = self.new_repo()
        self.assertNotIn('No such file or directory', result.stderr)
        self.assertTrue((self.tmp / 'game/AGENTS.md').is_file(), result.stderr)
        self.assertTrue((self.tmp / 'game/docs/spec').is_dir())

    def test_a_new_repository_is_local_on_develop_with_a_tasks_folder(self):
        result = self.new_repo('--register', '--personal')
        game = (self.tmp / 'game').resolve()
        branch = subprocess.run(['git', '-C', str(game), 'branch', '--show-current'], capture_output=True, text=True)
        self.assertEqual(branch.stdout.strip(), 'develop')
        self.assertTrue((game / 'docs/tasks/README.md').is_file())
        self.assertEqual((self.config / 'repos.conf').read_text(), f'someone/game {game} local develop\n')
        self.assertEqual((self.config / 'personal.conf').read_text(), f'{game}\n')
        self.assertIn('registered', result.stdout)

    def test_lint_and_format_skip_what_openrig_and_the_loop_place_in_a_worktree(self):
        result = self.new_repo()
        game = self.tmp / 'game'
        eslint = (game / 'eslint.config.js').read_text()
        self.assertIn('ignores: ["node_modules/", "dist/", ".openrig/", ".claude/"]', eslint, result.stderr)
        ignored = (game / '.prettierignore').read_text().splitlines()
        for pattern in ('docs/incoming.html', '.openrig/', '.claude/', '.worker-*', 'CLAUDE.md', 'AGENTS.md'):
            self.assertEqual(ignored.count(pattern), 1, pattern)

    def test_an_already_listed_repository_is_not_told_to_add_itself(self):
        self.config.mkdir()
        game = self.tmp / 'game'
        game.mkdir()
        (self.config / 'repos.conf').write_text(f'someone/game {game.resolve()} local develop\n')
        result = self.new_repo()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('already listed', result.stdout)
        self.assertNotIn('add this line', result.stdout)


if __name__ == '__main__':
    unittest.main()
