"""Project grouping against real Git worktrees; delegation against the actual loop."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/ai-work'
sys.path.insert(0, str(PLATFORM / 'lib'))
from ai_ecosystem.store import Store, session_id
from ai_ecosystem.workspace import project_id


class Workspace(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='ai-work-')
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.dev = self.base / 'Dev'
        self.dev.mkdir()
        self.repo = self.dev / 'project'
        self.env = dict(os.environ, HOME=str(self.home), GIT_CONFIG_GLOBAL='/dev/null',
                        GIT_CONFIG_NOSYSTEM='1', DEV_PLATFORM_BRIEF=str(self.base / 'no-brief'),
                        DEV_PLATFORM_PERSONAL=str(self.base / 'no-personal'),
                        LOOP_STATE_DIR=str(self.base / 'loop'),
                        PYTHONDONTWRITEBYTECODE='1')
        for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'LOOP_MODEL', 'LOOP_CAP'):
            self.env.pop(key, None)
        self.init_repo(self.repo)
        self.config = self.base / 'repos.conf'
        self.config.write_text(f'owner/project\t{self.repo}\towner\tmain\n')
        self.state = self.base / 'sessions'
        self.workspace = self.base / 'openrig'

    def run_command(self, args, check=True):
        proc = subprocess.run([str(a) for a in args], env=self.env, text=True, capture_output=True)
        if check and proc.returncode:
            self.fail(f'{args}: {proc.returncode}\n{proc.stderr}\n{proc.stdout}')
        return proc

    def init_repo(self, path):
        path.mkdir(parents=True)
        self.run_command(['git', 'init', '-q', '-b', 'main', path])
        self.run_command(['git', '-C', path, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                          '-c', 'core.hooksPath=/dev/null', 'commit', '-q', '--allow-empty', '-m', 'initial'])

    def cli(self, *args, check=True):
        return self.run_command([CLI, '--config', self.config, '--state-root', self.state, *args], check)

    def projects(self, *args):
        return json.loads(self.cli(*args, 'projects').stdout)['projects']

    def add_session(self, cwd, name, title=None):
        store = Store(self.state)
        sid = session_id('claude', '/native', name)
        with store.lock(sid):
            store.put(dict(id=sid, cwd=str(cwd), title=title or name, native_id=name,
                           runtime='claude', owner='user', status='unknown', updated_at=name))
        return sid

    def test_a_local_repository_is_a_loop_project_with_its_mode(self):
        self.config.write_text(f'owner/project\t{self.repo}\tlocal\tdevelop\n')
        project = next(p for p in self.projects() if p['repo'] == 'owner/project')
        self.assertTrue(project['loop_enabled'])
        self.assertEqual(project['mode'], 'local')
        self.config.write_text(f'owner/project\t{self.repo}\tgithub\n')
        self.assertIn('local|owner|bot', self.cli('projects', check=False).stderr)

    def test_group_real_linked_worktrees_and_preserve_distinct_repositories(self):
        worktree = self.base / 'different-name'
        self.run_command(['git', '-C', self.repo, 'worktree', 'add', '-q', '-b', 'feature', worktree])
        other = self.dev / 'group' / 'project'
        self.init_repo(other)
        native = self.base / 'native.jsonl'
        native.write_text('do not read or copy this transcript')
        first = self.add_session(self.repo, '1')
        second = self.add_session(worktree, '2')
        third = self.add_session(other, '3')
        before = native.read_bytes()
        projects = self.projects('--dev-root', self.dev)
        self.assertEqual(len(projects), 2)
        self.assertEqual({p['group'] for p in projects}, {'local', 'group'})
        result = json.loads(self.cli('--dev-root', self.dev, 'sessions', '--project', 'owner/project').stdout)
        self.assertEqual({s['id'] for s in result['sessions']}, {first, second})
        self.assertNotIn(third, str(result))
        self.assertEqual(native.read_bytes(), before)
        self.assertFalse(next(p for p in projects if p['repo'] is None)['loop_enabled'])

    def test_native_project_id_length_and_configured_group_follow_dev_folder(self):
        first = project_id('owner/' + 'a' * 200)
        second = project_id('owner/' + 'a' * 199 + 'b')
        self.assertLessEqual(len(first), 64)
        self.assertNotEqual(first, second)
        grouped = self.dev / 'acme-corp' / 'server'
        self.init_repo(grouped)
        self.config.write_text(self.config.read_text() + f'Example-Systems/server\t{grouped}\towner\n')
        projects = self.projects('--dev-root', self.dev)
        server = next(p for p in projects if p['repo'] == 'Example-Systems/server')
        self.assertEqual(server['group'], 'acme-corp')
        self.cli('--dev-root', self.dev, 'sync-openrig', '--workspace', self.workspace)
        manifest = json.loads((self.workspace / 'projects' / server['id'] / 'project.yaml').read_text())
        self.assertEqual(manifest['metadata']['name'], 'acme-corp / server')

    def test_session_listing_bounded_missing_paths_unassigned_no_index_creation(self):
        self.assertEqual(json.loads(self.cli('sessions').stdout)['total'], 0)
        self.assertFalse(self.state.exists())
        self.add_session(self.repo, '1')
        self.add_session(self.repo, '2')
        missing = self.add_session(self.base / 'old-project', '3')
        listed = json.loads(self.cli('sessions', '--limit', '1').stdout)
        self.assertEqual(listed['total'], 3)
        self.assertTrue(listed['has_more'])
        self.assertEqual(len(listed['sessions']), 1)
        self.assertEqual(json.loads(self.cli('sessions', '--project', 'unassigned').stdout)['sessions'][0]['id'], missing)
        self.assertEqual(self.cli('sessions', '--limit', '0', check=False).returncode, 2)

    def test_symlink_and_worktree_discovery_deduplicate_using_git_identity(self):
        alias = self.dev / 'alias'
        alias.symlink_to(self.repo, target_is_directory=True)
        self.run_command(['git', '-C', self.repo, 'worktree', 'add', '-q', '-b', 'feature', self.dev / 'worktree'])
        self.assertEqual(len(self.projects('--dev-root', self.dev)), 1)
        self.config.write_text(self.config.read_text() + f'owner/alias\t{alias}\towner\n')
        result = self.cli('projects', check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn('ambiguous', result.stderr)

    def test_discovery_does_not_recurse_into_session_or_worktree_stores(self):
        self.init_repo(self.repo / '.claude/worktrees/hidden')
        self.assertEqual(len(self.projects('--dev-root', self.dev)), 1)
        result = self.cli('loop', 'unregistered/project', 'pause', check=False)
        self.assertEqual(result.returncode, 2)

    def test_real_loop_status_pause_and_dispatch_lock_shared_across_entrypoints(self):
        before = self.run_command(['git', '-C', self.repo, 'status', '--porcelain']).stdout
        result = self.cli('loop', 'owner/project', 'status')
        self.assertIn('owner/project', result.stdout)
        self.assertIn('pause (no steer file)', result.stdout)
        self.cli('loop', self.projects()[0]['id'], 'pause')
        ledger = self.base / 'loop/owner__project'
        self.assertEqual((ledger / 'steer').read_text(), 'pause\n')
        direct = self.run_command([PLATFORM / 'skills/loop/scripts/loop.sh', 'status', 'owner/project'], check=False)
        # The same existing loop also needs the same repository configuration, not a parallel catalog.
        self.assertNotEqual(direct.returncode, 0)
        self.env['DEV_PLATFORM_REPOS'] = str(self.config)
        direct = self.run_command([PLATFORM / 'skills/loop/scripts/loop.sh', 'status', 'owner/project'])
        self.assertIn('steer: pause', direct.stdout)
        (ledger / 'dispatch-lock').mkdir()
        self.assertNotEqual(self.cli('loop', 'owner/project', 'start', check=False).returncode, 0)
        self.assertNotEqual(self.cli('loop', 'owner/project', 'start', 'loop/2026-09-24', check=False).returncode, 0)
        locked = self.cli('loop', 'owner/project', 'go', 'only', '12', check=False)
        self.assertEqual(locked.returncode, 3)
        self.assertIn('another dispatch', locked.stderr)
        self.assertEqual((ledger / 'steer').read_text(), 'pause\n')
        self.assertEqual(self.run_command(['git', '-C', self.repo, 'status', '--porcelain']).stdout, before)

    def test_loop_arguments_are_exact_and_cannot_inject_shell_or_release_actions(self):
        plan = json.loads(self.cli('loop', 'owner/project', 'go', 'only', '2', '7', '--dry-run').stdout)
        self.assertEqual(plan['argv'], [str(PLATFORM / 'skills/loop/scripts/loop.sh'), 'go', 'owner/project', 'only', '2', '7'])
        self.assertEqual(plan['config'], str(self.config))
        self.assertFalse((self.base / 'loop').exists())
        for args in [('go', 'only', '2;touch injected'), ('pause', 'only', '2'), ('go', 'only'), ('fold',)]:
            self.assertNotEqual(self.cli('loop', 'owner/project', *args, check=False).returncode, 0)
        self.assertFalse((self.repo / 'injected').exists())

    def test_native_catalog_sync_idempotent_external_and_preserves_unowned_files(self):
        self.workspace.mkdir()
        unrelated = self.workspace / 'notes.md'
        unrelated.write_text('user notes')
        self.cli('sync-openrig', '--workspace', self.workspace)
        before = {str(p): p.read_bytes() for p in self.workspace.rglob('*') if p.is_file()}
        self.cli('sync-openrig', '--workspace', self.workspace)
        after = {str(p): p.read_bytes() for p in self.workspace.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        catalog = json.loads((self.workspace / 'workspace.yaml').read_text())
        self.assertEqual(catalog['schema'], 'openrig.workspace/v0alpha1')
        project = catalog['projects'][0]
        root = self.workspace / project['root']
        self.assertTrue((root / 'missions').is_dir())
        manifest = json.loads((root / 'project.yaml').read_text())
        self.assertEqual(manifest['schema'], 'openrig.project/v0alpha1')
        self.assertEqual(manifest['metadata'], {'id': project['id'], 'name': 'owner / project'})
        self.assertIn(str(self.repo), (root / 'SPEC.md').read_text())
        self.assertEqual(unrelated.read_text(), 'user notes')
        self.assertFalse((self.repo / '.openrig').exists())

    def test_sync_refuses_unowned_modified_and_symlink_collisions_without_overwrite(self):
        self.workspace.mkdir()
        file = self.workspace / 'workspace.yaml'
        file.write_text('projects: []\n')
        result = self.cli('sync-openrig', '--workspace', self.workspace, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(file.read_text(), 'projects: []\n')
        self.assertFalse((self.workspace / 'projects').exists())
        file.unlink()
        self.cli('sync-openrig', '--workspace', self.workspace)
        file.write_text('edited by owner')
        self.assertEqual(self.cli('sync-openrig', '--workspace', self.workspace, check=False).returncode, 2)
        self.assertEqual(file.read_text(), 'edited by owner')
        alternative = self.base / 'symlink-workspace'
        alternative.mkdir()
        (alternative / 'projects').symlink_to(self.repo, target_is_directory=True)
        self.assertEqual(self.cli('sync-openrig', '--workspace', alternative, check=False).returncode, 2)
        self.assertEqual(self.cli('sync-openrig', '--workspace', self.repo / 'generated', check=False).returncode, 2)
        self.assertFalse((self.repo / 'generated').exists())

    def test_removed_catalog_entries_leave_owned_project_artifacts_intact(self):
        self.cli('sync-openrig', '--workspace', self.workspace)
        project = json.loads((self.workspace / 'workspace.yaml').read_text())['projects'][0]
        spec = self.workspace / project['root'] / 'SPEC.md'
        before = spec.read_bytes()
        self.config.write_text('')
        self.cli('sync-openrig', '--workspace', self.workspace)
        self.assertEqual(json.loads((self.workspace / 'workspace.yaml').read_text())['projects'], [])
        self.assertEqual(spec.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
