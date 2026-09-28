"""Launcher boundaries: native calls without real agents or host configuration."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


LAUNCHER = Path(__file__).resolve().parents[1] / 'bin/dev-workspace'


class WorkspaceLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log = self.root / 'calls.jsonl'
        rig = self.root / 'app/node_modules/.bin/rig'
        rig.parent.mkdir(parents=True)
        node = self.root / 'node-v24.14.0-darwin-arm64/bin/node'
        node.parent.mkdir(parents=True)
        node.touch()
        rig.write_text('''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as f:
    f.write(json.dumps({'args':a, 'codex_home':os.environ.get('CODEX_HOME')})+'\\n')
if a == ['--version']: print('0.5.14 (cc75efdd)')
elif a == ['daemon', 'status']: print(os.environ.get('DAEMON_STATE', 'Daemon running on port 4400 (pid 1)'))
elif a == ['ps', '--json', '--include-archived']: print(os.environ.get('RIGS', '[]'))
elif a[:2] == ['ps', '--nodes']:
    seats = os.environ['SEATS']
    print(json.dumps([json.loads(l) for l in open(seats)] if os.path.exists(seats) else []))
elif a[0] == 'ps': sys.exit(2)
elif a[0] == 'add':
    member = open(a[3]).read().split('\\n')[0].split(': ')[1]
    if not os.environ.get('ADD_LOST'):
        with open(os.environ['SEATS'], 'a') as f:
            f.write(json.dumps({'logicalId': a[2] + '.' + member,
                                'canonicalSessionName': a[2] + '-' + member + '@' + a[1]}) + '\\n')
    sys.exit(int(os.environ.get('ADD_EXIT', '0')))
elif a[0] == 'up' and '--plan' in a and os.environ.get('PLAN_FAIL'): sys.exit(7)
''')
        rig.chmod(0o755)
        self.env = dict(os.environ, DEV_WORKSPACE_RUNTIME=str(self.root), CALLS=str(self.log),
                        CODEX_HOME='/not-the-personal-store',
                        DEV_PLATFORM_PERSONAL=str(self.root / 'personal.conf'),
                        SEATS=str(self.root / 'seats.jsonl'),
                        DEV_WORKSPACE_STATE_DIR=str(self.root / 'state'),
                        DEV_WORKSPACE_ADD_WAIT='0')

    def call(self, *args):
        return subprocess.run([str(LAUNCHER), *args], env=self.env, text=True, capture_output=True)

    def records(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_open_starts_only_missing_daemon_and_tui(self):
        self.env['DAEMON_STATE'] = 'Daemon stopped'
        self.assertEqual(self.call().returncode, 0)
        records = self.records()
        self.assertEqual([r['args'] for r in records], [
            ['--version'], ['daemon', 'status'], ['daemon', 'start', '--no-kernel'], ['tui']])
        self.assertTrue(all(r['codex_home'] is None for r in records))

    def test_open_reuses_running_daemon_and_shared_is_explicit(self):
        self.assertEqual(self.call('open', '--shared').returncode, 0)
        self.assertEqual([r['args'] for r in self.records()],
                         [['--version'], ['daemon', 'status'], ['tui', '--shared']])

    def test_existing_seat_uses_native_restore_without_cwd_rebinding(self):
        self.env['RIGS'] = json.dumps([{'name':'development-codex'}])
        result = self.call('start', 'codex', '--cwd', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(commands, [['up', 'development-codex', '--existing', '--plan'],
                                    ['up', 'development-codex', '--existing']])

    def test_failed_new_plan_cannot_launch_a_seat(self):
        self.env['PLAN_FAIL'] = '1'
        self.assertNotEqual(self.call('start', 'claude', '--cwd', str(self.root)).returncode, 0)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(len(commands), 1)
        self.assertIn('--plan', commands[0])
        self.assertTrue(commands[0][1].endswith('integrations/openrig/claude.yaml'))

    def test_unverified_or_unhealthy_daemon_does_not_restart(self):
        for state in ['Daemon state UNVERIFIED', 'Daemon running on port 4400 — process present but UNHEALTHY']:
            with self.subTest(state=state):
                self.log.unlink(missing_ok=True)
                self.env['DAEMON_STATE'] = state
                self.assertNotEqual(self.call().returncode, 0)
                self.assertEqual(len(self.records()), 2)

    def test_plan_does_not_start_stopped_daemon(self):
        self.env['DAEMON_STATE'] = 'Daemon stopped'
        self.assertNotEqual(self.call('plan', 'codex', '--cwd', str(self.root)).returncode, 0)
        self.assertEqual(len(self.records()), 2)

    def test_archived_seat_is_not_recreated(self):
        self.env['RIGS'] = json.dumps([{'name':'development-codex', 'isArchived':True}])
        self.assertNotEqual(self.call('start', 'codex', '--cwd', str(self.root)).returncode, 0)
        self.assertFalse(any(r['args'][0] == 'up' for r in self.records()))

    def test_new_seat_blocks_professional_checkout_but_allows_plan(self):
        repo = self.root / 'professional'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        result = self.call('start', 'codex', '--cwd', str(repo))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('managed context', result.stderr)
        self.assertFalse(any(r['args'][0] == 'up' for r in self.records()))
        self.assertEqual(self.call('plan', 'codex', '--cwd', str(repo)).returncode, 0)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertEqual(len(commands), 1)
        self.assertIn('--plan', commands[0])

    def test_new_seat_accepts_personal_repo_symlink_identity(self):
        repo = self.root / 'personal'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        alias = self.root / 'alias'
        alias.symlink_to(repo, target_is_directory=True)
        (self.root / 'personal.conf').write_text(str(alias) + '\n')
        result = self.call('start', 'codex', '--cwd', str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([r for r in self.records() if r['args'][0] == 'up']), 2)


    def test_helm_control_rig_uses_its_template_and_stays_outside_checkouts(self):
        folder = self.root / 'engagement'
        folder.mkdir()
        result = self.call('start', 'helm', '--cwd', str(folder))
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [r['args'] for r in self.records() if r['args'][0] == 'up']
        self.assertTrue(commands[-1][1].endswith('integrations/openrig/helm.yaml'))
        repo = self.root / 'personal'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        (self.root / 'personal.conf').write_text(str(repo) + '\n')
        result = self.call('start', 'helm', '--cwd', str(repo))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('engagement folder', result.stderr)
        self.assertNotEqual(self.call('start', 'helm', '--cwd', str(folder), '--account', 'openai-apple').returncode, 0)


    def test_helm_rig_takes_a_project_name(self):
        folder = self.root / 'engagement'
        folder.mkdir()
        result = self.call('start', 'helm', '--cwd', str(folder), '--rig', 'helm-research-agent')
        self.assertEqual(result.returncode, 0, result.stderr)
        up = [r['args'] for r in self.records() if r['args'][0] == 'up'][-1]
        spec = Path(up[1]).read_text()
        self.assertIn('name: helm-research-agent\n', spec)
        self.assertNotIn('local:', spec)
        self.assertIn('integrations/openrig/agents/overseer', spec)
        self.env['RIGS'] = json.dumps([{'name': 'helm-research-agent'}])
        self.call('start', 'helm', '--cwd', str(folder), '--rig', 'helm-research-agent')
        self.assertEqual([r['args'] for r in self.records() if r['args'][0] == 'up'][-1],
                         ['up', 'helm-research-agent', '--existing'])
        for bad in (['start', 'codex', '--cwd', str(folder), '--rig', 'x'],
                    ['start', 'helm', '--cwd', str(folder), '--rig', 'Bad Name']):
            self.assertEqual(self.call(*bad).returncode, 2)

    def test_an_engagement_with_its_own_spec_starts_that_team_where_its_members_say(self):
        folder = self.root / 'engagement'
        folder.mkdir()
        spec = folder / 'rig.yaml'
        spec.write_text('version: "0.2"\nname: helm-research-agent\npods: []\n')
        result = self.call('start', 'helm', '--cwd', str(folder), '--rig', 'helm-research-agent')
        self.assertEqual(result.returncode, 0, result.stderr)
        ups = [r['args'] for r in self.records() if r['args'][0] == 'up']
        # No --cwd: it would override every member's own folder.
        self.assertEqual(ups, [['up', str(spec.resolve()), '--plan'], ['up', str(spec.resolve())]])
        spec.write_text('version: "0.2"\nname: another-team\npods: []\n')
        result = self.call('start', 'helm', '--cwd', str(folder), '--rig', 'helm-research-agent')
        self.assertEqual(result.returncode, 2)
        self.assertIn('does not declare name: helm-research-agent', result.stderr)


class WorkerSeats(unittest.TestCase):
    """add-worker and remove-worker against a real Git worktree and the fake rig."""
    call = WorkspaceLauncherTests.call
    records = WorkspaceLauncherTests.records

    def setUp(self):
        WorkspaceLauncherTests.setUp(self)
        self.repo = self.root / 'personal'
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), *a], check=True, capture_output=True)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'CLAUDE.md').write_text('# Repository rules\n')
        git('add', '.')
        git('-c', 'user.name=t', '-c', 'user.email=t@t.invalid', 'commit', '-qm', 'init')
        self.wt = self.repo / '.claude/worktrees/loop-12-fix-parser'
        git('worktree', 'add', '-q', '-b', 'fix/fix-parser-12', str(self.wt))
        (self.root / 'personal.conf').write_text(str(self.repo) + '\n')
        self.env['RIGS'] = json.dumps([{'rigId': 'R1', 'name': 'development-helm'}])

    def add(self, *extra):
        return self.call('add-worker', 'claude', '--rig', 'development-helm', '--cwd', str(self.wt), *extra)

    def test_add_worker_joins_the_workers_pod_from_its_worktree(self):
        result = self.add()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('tmux attach -t workers-issue-12@R1', result.stdout)
        add = [r['args'] for r in self.records() if r['args'][0] == 'add']
        self.assertEqual(add[0][:3], ['add', 'R1', 'workers'])
        fragment = Path(add[0][3]).read_text()
        self.assertIn('id: issue-12\n', fragment)
        self.assertIn('runtime: claude-code\n', fragment)
        self.assertIn(f'cwd: "{self.wt.resolve()}"', fragment)
        self.assertIn('integrations/openrig/agents/worker', fragment)
        self.assertNotIn('config_home', fragment)
        exclude = (self.repo / '.git/info/exclude').read_text().splitlines()
        self.assertIn('.openrig/', exclude)
        self.assertEqual(self.add().returncode, 2)  # one seat per worktree

    def test_client_timeout_is_verified_not_retried(self):
        self.env['ADD_EXIT'] = '1'
        self.assertEqual(self.add().returncode, 0)
        self.env['ADD_LOST'] = '1'
        self.wt = self.repo / '.claude/worktrees/loop-13-other'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '-b', 'fix/other-13', str(self.wt)], check=True)
        result = self.add()
        self.assertEqual(result.returncode, 1)
        self.assertIn('before trying again', result.stderr)
        self.assertEqual(len([r for r in self.records() if r['args'][0] == 'add']), 2)

    def test_refuses_the_checkout_itself_a_professional_repo_and_a_stopped_rig(self):
        checkout = self.call('add-worker', 'claude', '--rig', 'development-helm', '--cwd', str(self.repo))
        self.assertIn('linked worktree', checkout.stderr)
        self.env['RIGS'] = '[]'
        self.assertIn('not one running rig', self.add().stderr)
        (self.root / 'personal.conf').write_text('')
        self.assertIn('professional', self.add().stderr)
        self.assertFalse(any(r['args'][0] == 'add' for r in self.records()))

    def test_remove_worker_restores_tracked_guidance(self):
        self.assertEqual(self.add().returncode, 0)
        claude = self.wt / 'CLAUDE.md'
        claude.write_text('# Repository rules\n\n\n<!-- BEGIN OpenRig MANAGED BLOCK: role -->\nrole\n'
                          '<!-- END OpenRig MANAGED BLOCK: role -->\n\n<!-- BEGIN OpenRig MANAGED BLOCK: '
                          'CULTURE-default.md -->\nculture\n<!-- END OpenRig MANAGED BLOCK: CULTURE-default.md -->\n')
        (self.wt / 'AGENTS.md').write_text('<!-- BEGIN OpenRig MANAGED BLOCK: role -->\nx\n<!-- END OpenRig MANAGED BLOCK: role -->\n')
        result = self.call('remove-worker', '--rig', 'development-helm', '--cwd', str(self.wt))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(['remove', 'R1', 'workers.issue-12'], [r['args'] for r in self.records()])
        self.assertEqual(claude.read_text(), '# Repository rules\n')
        self.assertFalse((self.wt / 'AGENTS.md').exists())
        status = subprocess.run(['git', '-C', str(self.wt), 'status', '--porcelain', '--untracked-files=no'],
                                capture_output=True, text=True).stdout
        self.assertEqual(status, '')


class TmuxEnvironmentScrub(unittest.TestCase):
    """A seat inherits the tmux server's global environment. `start` must unset provider
    overrides there first. A fake tmux on PATH records what the launcher asks it to do.
    Reuses the launcher fixture without inheriting its tests."""
    call = WorkspaceLauncherTests.call
    records = WorkspaceLauncherTests.records

    def setUp(self):
        WorkspaceLauncherTests.setUp(self)
        fake_bin = self.root / 'fakebin'
        fake_bin.mkdir()
        tmux = fake_bin / 'tmux'
        tmux.write_text('''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as f:
    f.write(json.dumps({'tmux': a}) + '\\n')
if a == ['show-environment', '-g']:
    print('ANTHROPIC_BASE_URL=http://127.0.0.1:1')
    print('OPENCLAW_SERVICE_KIND=gateway')
    print('PATH=/usr/bin')
    print('-CODEX_HOME')
''')
        tmux.chmod(0o755)
        self.env['PATH'] = os.pathsep.join([str(fake_bin), self.env.get('PATH', '')])

    def test_start_removes_provider_overrides_from_the_tmux_server_before_launching(self):
        cwd = self.root / 'plain-folder'
        cwd.mkdir()
        result = self.call('start', 'codex', '--cwd', str(cwd))
        self.assertEqual(result.returncode, 0, result.stderr)
        tmux_calls = [r['tmux'] for r in self.records() if 'tmux' in r]
        self.assertIn(['set-environment', '-g', '-u', 'ANTHROPIC_BASE_URL'], tmux_calls)
        self.assertIn(['set-environment', '-g', '-u', 'OPENCLAW_SERVICE_KIND'], tmux_calls)
        self.assertNotIn(['set-environment', '-g', '-u', 'PATH'], tmux_calls)
        self.assertNotIn(['set-environment', '-g', '-u', 'CODEX_HOME'], tmux_calls)
        self.assertIn('Removed inherited provider overrides', result.stdout)
        rig_calls = [r['args'] for r in self.records() if 'args' in r]
        # The scrub happens after the plan and before the real launch.
        self.assertEqual(rig_calls[-1][0], 'up')
        self.assertNotIn('--plan', rig_calls[-1])

    def test_plan_never_touches_the_tmux_server(self):
        cwd = self.root / 'plain-folder'
        cwd.mkdir()
        self.assertEqual(self.call('plan', 'codex', '--cwd', str(cwd)).returncode, 0)
        self.assertEqual([r for r in self.records() if 'tmux' in r], [])
