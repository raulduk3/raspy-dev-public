"""new-repo is installed as a link in ~/.local/bin and must still find the release's templates."""
from pathlib import Path
import subprocess
import sys
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
        # No language package manager on PATH keeps the run offline; the skeleton still commits.
        self.env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'GIT_CONFIG_GLOBAL': str(home / '.gitconfig'),
                    'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com',
                    'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.com',
                    'DEV_PLATFORM_REPOS': str(self.config / 'repos.conf')}

    def new_repo(self, *args):
        return subprocess.run([str(self.tmp / 'bin/new-repo'), str(self.tmp / 'game'), '--owner', 'someone', *args],
                              capture_output=True, text=True, env=self.env)

    def test_runs_through_a_link_like_the_installed_command(self):
        result = self.new_repo()
        self.assertNotIn('No such file or directory', result.stderr)
        self.assertTrue((self.tmp / 'game/AGENTS.md').is_file(), result.stderr)
        self.assertTrue((self.tmp / 'game/docs/spec').is_dir())

    def branches(self, game):
        out = subprocess.run(['git', '-C', str(game), 'branch', '--format=%(refname:short)'],
                             capture_output=True, text=True)
        return sorted(out.stdout.split())

    def test_a_personal_repository_is_tier_2_on_main_with_no_develop_branch(self):
        result = self.new_repo('--register', '--personal')
        game = (self.tmp / 'game').resolve()
        branch = subprocess.run(['git', '-C', str(game), 'branch', '--show-current'], capture_output=True, text=True)
        self.assertEqual(branch.stdout.strip(), 'main')
        self.assertEqual(self.branches(game), ['main'])
        self.assertTrue((game / 'docs/tasks/README.md').is_file())
        self.assertEqual((self.config / 'repos.conf').read_text(),
                         f'someone/game {game} local main tier=2 tracker=files tasks=json\n')
        self.assertIn('Source control tier: 2 (see repos.conf)', (game / 'AGENTS.md').read_text())
        self.assertNotIn('develop', (game / 'CONTRIBUTING.md').read_text())
        self.assertNotIn('develop', (game / '.github/workflows/checks.yml').read_text())
        self.assertIn('registered', result.stdout)

    def test_tier_1_is_main_only_and_the_tier_is_written(self):
        self.new_repo('--register', '--personal', '--tier', '1')
        game = (self.tmp / 'game').resolve()
        self.assertEqual(self.branches(game), ['main'])
        self.assertIn(' tier=1 tracker=files tasks=json', (self.config / 'repos.conf').read_text())
        self.assertIn('Source control tier: 1 (see repos.conf)', (game / 'AGENTS.md').read_text())

    def test_a_company_repository_is_tier_3_and_keeps_develop(self):
        self.new_repo('--register')
        game = (self.tmp / 'game').resolve()
        branch = subprocess.run(['git', '-C', str(game), 'branch', '--show-current'], capture_output=True, text=True)
        self.assertEqual(branch.stdout.strip(), 'develop')
        self.assertEqual(self.branches(game), ['develop', 'main'])
        self.assertEqual((self.config / 'repos.conf').read_text(),
                         f'someone/game {game} local develop tier=3 tracker=files tasks=md\n')
        self.assertIn('Source control tier: 3 (see repos.conf)', (game / 'AGENTS.md').read_text())

    def test_a_personal_repository_gets_the_task_schema_and_its_check(self):
        import json
        import shutil
        self.new_repo('--register', '--personal')
        game = (self.tmp / 'game').resolve()
        schema = game / 'docs/tasks/task.schema.json'
        self.assertEqual(schema.read_bytes(), (ROOT / 'schemas/task/v1.schema.json').read_bytes())
        self.assertIn('scripts/checks/tasks.py', (game / 'scripts/check').read_text())
        if not (shutil.which('uvx') or __import__('importlib').util.find_spec('jsonschema')):
            self.skipTest('no JSON Schema validator')
        check = [sys.executable, str(game / 'scripts/checks/tasks.py'), '--cwd', str(game)]
        env = dict(self.env, PATH=self.env['PATH'] + ':' + str(Path.home() / '.local/bin'), HOME=str(Path.home()))
        self.assertEqual(subprocess.run(check, capture_output=True, text=True, env=env).returncode, 0)
        (game / 'docs/tasks/1.json').write_text(json.dumps({'schema': 'dev-platform/task@1', 'id': 1, 'title': 'x'}))
        self.assertEqual(subprocess.run(check, capture_output=True, text=True, env=env).returncode, 1)

    def test_an_unregistered_repository_keeps_markdown_tasks(self):
        out = subprocess.run([sys.executable, '-I', str(ROOT / 'lib/ai_ecosystem/tiers.py'), '--conf', str(self.tmp / 'none.conf'),
                              str(self.tmp)], capture_output=True, text=True)
        self.assertIn('tasks=md', out.stdout.splitlines(), out.stderr)

    def test_a_tier_outside_1_to_4_is_refused(self):
        result = self.new_repo('--tier', '7')
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.tmp / 'game').exists())

    def test_skeleton_is_language_neutral_and_versioned(self):
        result = self.new_repo()
        game = self.tmp / 'game'
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((game / 'scripts/check').is_file())
        self.assertTrue((game / 'scripts/version.py').is_file())
        self.assertTrue((game / 'scripts/checks/hygiene.py').is_file())
        self.assertTrue((game / 'docs/VERSIONING.md').is_file())
        self.assertFalse((game / 'package.json').exists())
        self.assertFalse((game / 'tsconfig.json').exists())
        version = subprocess.run(['python3', 'scripts/version.py'], cwd=game, capture_output=True, text=True)
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertEqual(version.stdout.strip(), '0.1.0')
        subprocess.run(['git', 'checkout', '-q', '-b', 'feat/branch-version'], cwd=game, check=True)
        (game / 'README.md').write_text((game / 'README.md').read_text() + '\nBranch work.\n')
        subprocess.run(['git', 'add', 'README.md'], cwd=game, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'docs(repo): describe branch work'], cwd=game, check=True,
                       env=self.env)
        sha = subprocess.run(['git', 'rev-parse', '--short=8', 'HEAD'], cwd=game, capture_output=True, text=True)
        version = subprocess.run(['python3', 'scripts/version.py'], cwd=game, capture_output=True, text=True)
        self.assertEqual(version.stdout.strip(), f'0.1.1-feat-branch-version.1+{sha.stdout.strip()}')

    def test_an_already_listed_repository_is_not_told_to_add_itself(self):
        self.config.mkdir()
        game = self.tmp / 'game'
        game.mkdir()
        (self.config / 'repos.conf').write_text(f'someone/game {game.resolve()} local main tier=2\n')
        result = self.new_repo()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('already listed', result.stdout)
        self.assertNotIn('add this line', result.stdout)


if __name__ == '__main__':
    unittest.main()
