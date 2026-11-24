"""The ai menu: scripted answers in, the exact hand-off command out. Nothing is launched."""
from contextlib import redirect_stdout
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import pty
import shutil
import tty
import tempfile
import unittest
from unittest import mock

MENU = Path(__file__).resolve().parents[1] / 'bin/ai'


def load_menu():
    loader = importlib.machinery.SourceFileLoader('ai_menu', str(MENU))
    spec = importlib.util.spec_from_loader('ai_menu', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class Menu(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.menu = load_menu()
        self.menu.DRY = True
        self.menu.TEAMS = self.root / 'engagements'
        self.project = {'id': 'owner-repo-1', 'root': str(self.root / 'Research Agent'), 'repo': 'owner/repo',
                        'group': 'owner', 'source': 'repos.conf', 'loop_enabled': True, 'available': True,
                        'common_dir': None}
        Path(self.project['root']).mkdir()
        # The machine layer's commands come from a fake folder, empty unless a test fills it.
        self.machine_bin = self.root / 'machine-bin'
        self.machine_bin.mkdir()
        self.real_machine = self.menu.machine
        lookup = mock.patch.object(self.menu, 'machine',
                                   lambda command: shutil.which(command, path=str(self.machine_bin)))
        lookup.start()
        self.addCleanup(lookup.stop)

    def on_path(self, *commands):
        """Put empty, never-run stand-ins for machine commands on the fake path."""
        for command in commands:
            (self.machine_bin / command).write_text('')
            (self.machine_bin / command).chmod(0o755)

    def drive(self, function, *answers, **kwargs):
        """Run one menu function with scripted answers; return what it printed."""
        replies = iter(answers)

        def answer(prompt=''):
            try:
                return next(replies)
            except StopIteration:
                raise EOFError from None
        out = io.StringIO()
        with mock.patch('builtins.input', answer), redirect_stdout(out):
            try:
                function(**kwargs)
            except self.menu.Quit:
                pass
        return out.getvalue()

    def runs(self, output):
        return [line[4:] for line in output.splitlines() if line.startswith('RUN ')]

    def test_claude_opens_in_the_project_on_the_account_with_most_room(self):
        rows = [{'account': 'anthropic-alpha', 'client': 'Claude Code', 'state': 'cached', 'freshness': 'live',
                 'windows': [{'window': 'seven_day', 'used_percent': 56}]},
                {'account': 'anthropic-bravo', 'client': 'Claude Code', 'state': 'cached', 'freshness': 'live',
                 'windows': [{'window': 'seven_day', 'used_percent': 4}]}]
        with mock.patch.object(self.menu, 'usage_rows', return_value=rows):
            output = self.drive(self.menu.project_menu, '1', '1', project=self.project)
        self.assertIn('anthropic-bravo  cached        7d 4% used  · most room', output)
        run = self.runs(output)[0]
        self.assertIn('bin/ai-account run --client claude --account anthropic-bravo', run)
        self.assertTrue(run.endswith(f"--cwd {self.project['root']}"))

    def test_account_picker_accepts_unknown_windows(self):
        rows = [{'account': 'anthropic-alpha', 'client': 'Claude Code', 'state': 'unknown', 'freshness': 'unknown: no reading yet',
                 'windows': None},
                {'account': 'anthropic-bravo', 'client': 'Claude Code', 'state': 'cached', 'freshness': 'live',
                 'windows': [{'window': 'seven_day', 'used_percent': 4}]}]
        with mock.patch.object(self.menu, 'usage_rows', return_value=rows):
            output = self.drive(self.menu.project_menu, '1', '1', project=self.project)
        self.assertIn('anthropic-alpha  unknown       usage unknown · unknown: no reading yet', output)
        self.assertEqual(len(self.runs(output)), 1)

    def test_a_session_resumes_by_picking_it(self):
        rows = {'sessions': [{'id': 'claude-abc', 'runtime': 'claude', 'owner': 'user', 'title': None,
                              'cwd': '/x/research-agent/.claude/worktrees/loop-4-fix', 'project': 'owner-repo-1',
                              'updated_at': '2026-09-24T00:00:00Z'},
                             {'id': 'pi-x', 'runtime': 'pi', 'owner': 'user', 'title': None,
                              'cwd': '/x', 'project': None, 'updated_at': None}]}
        with mock.patch.object(self.menu, 'catalog', return_value=[self.project]), \
                mock.patch.object(self.menu.workspace, 'session_rows', return_value=rows):
            output = self.drive(self.menu.sessions_menu, '1', project=None)
        self.assertIn('[claude] · Research Agent · loop-4-fix', output)
        self.assertNotIn('[pi]', output)
        self.assertTrue(self.runs(output)[0].endswith('bin/ai-session resume claude-abc --execute'))

    def test_a_role_starts_through_the_launcher_of_the_server(self):
        # ai-role starts nothing without the Pi login folder that the launcher hands in, so the
        # menu gives the role and, for Engineer, the project to `agent`, which asks the rest.
        self.assertEqual(self.runs(self.drive(self.menu.start_role, agent='assistant')), ['agent assistant'])
        self.assertEqual(self.runs(self.drive(self.menu.start_role, agent='engineer', project=self.project)),
                         [f"agent engineer {self.project['root']}"])

    def test_the_role_entries_leave_the_menu_on_a_machine_with_no_launcher(self):
        with mock.patch.object(self.menu, 'upgrade_if_released'), \
                mock.patch.object(self.menu, 'project_for', return_value=None):
            with mock.patch.object(self.menu, 'role_launcher', return_value=None):
                absent = self.drive(self.menu.home)
            with mock.patch.object(self.menu, 'role_launcher', return_value='/usr/local/bin/agent'):
                present = self.drive(self.menu.home)
                ops = self.drive(self.menu.home, '5')
        for entry in ('Assistant, personal', 'Ops, this machine', 'Engineer, on a project'):
            self.assertNotIn(entry, absent)
            self.assertIn(entry, present)
        self.assertEqual(self.runs(ops)[0], 'agent ops')
        with mock.patch.object(self.menu, 'usage_rows', return_value=[]):
            with mock.patch.object(self.menu, 'role_launcher', return_value=None):
                self.assertNotIn('Engineer on this project', self.drive(self.menu.project_menu, project=self.project))
            with mock.patch.object(self.menu, 'role_launcher', return_value='/usr/local/bin/agent'):
                started = self.drive(self.menu.project_menu, '3', project=self.project)
        self.assertEqual(self.runs(started)[0], f"agent engineer {self.project['root']}")

    def test_a_project_team_starts_outside_the_repository_under_its_own_name(self):
        with mock.patch.object(self.menu, 'rigs', return_value=[]), \
                mock.patch.object(self.menu, 'seats', return_value=[]):
            output = self.drive(self.menu.project_team, '1', '1', 'y', '', project=self.project)
        folder = self.root / 'engagements/research-agent'
        self.assertTrue(folder.is_dir())
        self.assertIn('Which shape?', output)
        runs = self.runs(output)
        self.assertTrue(runs[0].endswith('bin/rig-shape write owner/repo build'))
        self.assertTrue(runs[1].endswith(f'bin/dev-workspace start engineer --cwd {folder} --rig engineer-research-agent'))
        with mock.patch.object(self.menu, 'rigs', return_value=[]):
            declined = self.drive(self.menu.project_team, '1', '1', 'n', project=self.project)
            self.assertEqual(self.runs(declined), [])
            self.assertEqual(self.runs(self.drive(self.menu.project_team, project=self.project)), [])

    def test_a_team_follows_its_repository_when_the_checkout_is_renamed(self):
        with mock.patch.object(self.menu, 'rigs', return_value=[]), \
                mock.patch.object(self.menu, 'seats', return_value=[]):
            self.drive(self.menu.project_team, '1', '1', 'y', '', project=self.project)
        self.assertEqual((self.root / 'engagements/research-agent/project').read_text(), 'owner/repo\n')
        renamed = dict(self.project, root=str(self.root / 'renamed-checkout'))
        with mock.patch.object(self.menu, 'catalog', return_value=[renamed]):
            self.assertEqual(self.menu.team_for(renamed), 'engineer-research-agent')
            self.assertEqual(self.menu.team_project('engineer-research-agent'), renamed)
        other = dict(self.project, repo='owner/other', root=str(self.root / 'other'))
        self.assertEqual(self.menu.team_for(other), 'engineer-other')

    def test_a_team_defined_in_its_engagement_folder_is_started_from_that_folder(self):
        folder = self.root / 'engagements/research-agent'
        folder.mkdir(parents=True)
        (folder / 'project').write_text('owner/repo\n')
        (folder / 'rig.yaml').write_text('name: engineer-research-agent\n')
        # The checkout was renamed; the team still starts from its own team folder.
        renamed = dict(self.project, root=str(self.root / 'renamed-checkout'))
        with mock.patch.object(self.menu, 'rigs', return_value=[]), \
                mock.patch.object(self.menu, 'seats', return_value=[]):
            output = self.drive(self.menu.project_team, 'y', '', project=renamed)
        self.assertIn(f"opens the team defined in {folder / 'rig.yaml'}", output)
        self.assertNotIn('Codex overseer', output)
        self.assertTrue(self.runs(output)[0].endswith(
            f'bin/dev-workspace start engineer --cwd {folder} --rig engineer-research-agent'))

    def test_a_project_team_is_reshaped_and_its_history_read_from_its_menu(self):
        with mock.patch.object(self.menu, 'seats', return_value=[]):
            reshaped = self.runs(self.drive(self.menu.team_menu, '4', '3', '2', team='t', project=self.project))
            history = self.runs(self.drive(self.menu.team_menu, '5', team='t', project=self.project))
        self.assertTrue(reshaped[0].endswith('bin/rig-shape write owner/repo solo --all claude-code'))
        self.assertTrue(history[0].endswith('bin/rig-shape history owner/repo'))

    def test_team_seats_attach_relaunch_and_stop(self):
        seats = [{'rigId': 'R1', 'logicalId': 'control.lead', 'runtime': 'claude-code', 'sessionStatus': 'running',
                  'lifecycleState': 'attention_required',
                  'agentActivity': {'state': 'needs_input', 'reason': 'selection_prompt'},
                  'canonicalSessionName': 'control-lead@t'},
                 {'rigId': 'R1', 'logicalId': 'review.overseer', 'runtime': 'codex', 'sessionStatus': 'exited',
                  'lifecycleState': 'attention_required', 'agentActivity': {}, 'canonicalSessionName': 'review-overseer@t'}]
        with mock.patch.object(self.menu, 'seats', return_value=seats), mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(self.menu, 'herdr', return_value=None):
            os.environ.pop('TMUX', None)
            output = self.drive(self.menu.team_menu, '2', '3', 'y', '4', 'y', team='t')
        self.assertIn('control.lead · claude-code · waiting on you\n', output)
        flagged = {'sessionStatus': 'running', 'lifecycleState': 'attention_required', 'agentActivity': {'state': 'running'}}
        self.assertEqual(self.menu.seat_state(flagged), 'working · OpenRig asks you to look')
        self.assertIn('review.overseer · codex · stopped\n', output)
        runs = self.runs(output)
        self.assertEqual(runs[0], 'tmux attach -t control-lead@t')
        self.assertTrue(runs[1].endswith('bin/rig snapshot R1'))
        self.assertTrue(runs[2].endswith('bin/rig launch R1 review.overseer'))
        self.assertTrue(runs[3].endswith('bin/rig down R1'))

    class FakeHerdr:
        """Answers herdr socket requests from a small in-memory state and records them."""
        def __init__(self, workspaces=(), tabs=(), panes=()):
            self.workspaces, self.tabs, self.panes, self.calls = list(workspaces), list(tabs), list(panes), []

        def __call__(self, method, **params):
            self.calls.append((method, params))
            ws = params.get('workspace_id')
            if method == 'workspace.list':
                return {'workspaces': self.workspaces}
            if method == 'workspace.create':
                space = {'workspace_id': 'wNEW', 'label': params['label']}
                self.workspaces.append(space)
                self.tabs.append({'tab_id': 'wNEW:t1', 'workspace_id': 'wNEW', 'label': '1'})
                return {'workspace': space}
            if method == 'tab.list':
                return {'tabs': [t for t in self.tabs if t['workspace_id'] == ws]}
            if method == 'pane.list':
                return {'panes': [p for p in self.panes if p['workspace_id'] == ws]}
            if method == 'layout.apply':
                tab = f"{ws}:{params['tab_label']}"
                self.tabs.append({'tab_id': tab, 'workspace_id': ws, 'label': params['tab_label']})
                def leaves(node):
                    return [node] if node['type'] == 'pane' else leaves(node['first']) + leaves(node['second'])
                for leaf in leaves(params['root']):
                    self.panes.append({'pane_id': f"{tab}:{leaf['label']}", 'tab_id': tab, 'workspace_id': ws,
                                       'label': leaf['label']})
            return {}

        def methods(self):
            return [m for m, _ in self.calls if m not in ('workspace.list', 'tab.list', 'pane.list')]

    def seat(self, logical, status='running'):
        return {'logicalId': logical, 'sessionStatus': status, 'agentActivity': {},
                'canonicalSessionName': logical.replace('.', '-') + '@t'}

    def show(self, fake, agent=None, here='wHERE'):
        seats = [self.seat('control.lead'), self.seat('review.overseer'), self.seat('workers.issue-4'),
                 self.seat('workers.issue-5', 'exited')]
        with mock.patch.object(self.menu, 'herdr', fake), \
                mock.patch.dict(os.environ, {'HERDR_ENV': '1', 'HERDR_WORKSPACE_ID': here}):
            with redirect_stdout(io.StringIO()):
                return self.menu.show_in_herdr('t', seats, Path('/p/project'), agent)

    def test_a_new_team_space_holds_rig_tui_and_every_running_agent_in_one_tab(self):
        fake = self.FakeHerdr(workspaces=[{'workspace_id': 'wOLD', 'label': 'openrig:pod:t/control#l2'}])
        self.assertTrue(self.show(fake, agent='review-overseer@t'))
        self.assertEqual(fake.methods(), ['workspace.close', 'workspace.create', 'layout.apply', 'tab.close',
                                          'tab.focus', 'pane.zoom', 'workspace.focus'])
        created = next(p for m, p in fake.calls if m == 'workspace.create')
        self.assertEqual(created, {'label': 't', 'cwd': '/p/project', 'focus': False})
        applied = next(p for m, p in fake.calls if m == 'layout.apply')
        self.assertEqual(applied['tab_label'], 'team')
        tui, agents = applied['root']['first'], applied['root']['second']
        self.assertEqual((tui['label'], tui['cwd'], tui['env']), ('rig tui', '/p/project', {'OPENRIG_REDUCED_MOTION': '1'}))
        self.assertEqual(tui['command'][:2], ['sh', '-c'])
        self.assertIn('bin/rig tui; printf', tui['command'][2])  # quitting it leaves the pane, offering it again

        def leaves(node):
            return [node] if node['type'] == 'pane' else leaves(node['first']) + leaves(node['second'])
        self.assertEqual([(l['label'], l['command']) for l in leaves(agents)], [
            ('control-lead@t', ['tmux', 'attach', '-t', 'control-lead@t']),
            ('review-overseer@t', ['tmux', 'attach', '-t', 'review-overseer@t']),
            ('workers-issue-4@t', ['tmux', 'attach', '-t', 'workers-issue-4@t'])])  # the stopped issue-5 has no tile
        self.assertIn(('tab.close', {'tab_id': 'wNEW:t1'}), fake.calls)
        self.assertIn(('pane.zoom', {'pane_id': 'wNEW:team:review-overseer@t', 'mode': 'on'}), fake.calls)

    def complete_space(self, labels):
        return self.FakeHerdr(
            workspaces=[{'workspace_id': 'w1', 'label': 't'}, {'workspace_id': 'wHERE', 'label': 'openrig:rig:t#l1'}],
            tabs=[{'tab_id': 'w1:team', 'workspace_id': 'w1', 'label': 'team'}],
            panes=[{'pane_id': f'w1:{l}', 'tab_id': 'w1:team', 'workspace_id': 'w1', 'label': l} for l in labels])

    def test_a_complete_space_is_reused_untouched(self):
        fake = self.complete_space(['rig tui', 'control-lead@t', 'review-overseer@t', 'workers-issue-4@t'])
        self.assertTrue(self.show(fake))
        self.assertEqual(fake.methods(), ['tab.focus', 'pane.zoom', 'workspace.focus'])  # the menu's own view stays

    def test_a_space_missing_an_agent_or_from_an_older_layout_is_rebuilt(self):
        for fake in (self.complete_space(['rig tui', 'control-lead@t', 'review-overseer@t']),
                     self.FakeHerdr(workspaces=[{'workspace_id': 'w1', 'label': 't'}],
                                    tabs=[{'tab_id': 'w1:s', 'workspace_id': 'w1', 'label': 'shell'}])):
            self.assertTrue(self.show(fake))
            self.assertEqual(fake.methods()[:3], ['workspace.close', 'workspace.create', 'layout.apply'])
            self.assertIn(('workspace.close', {'workspace_id': 'w1'}), fake.calls)

    def test_an_agent_ended_inside_its_tile_is_stopped_and_relaunched_cleanly(self):
        self.menu.DRY = False
        seat = dict(self.seat('review.overseer'), rigId='R1')
        def answer(argv, **kwargs):
            if argv[:2] == ['tmux', 'display']:
                return mock.Mock(returncode=0, stdout='3272 /dev/ttys012\n')
            if argv[0] == 'ps':  # only the pane's own shell is in the foreground
                return mock.Mock(returncode=0, stdout=' 3272 Ss+\n 3300 S\n')
            return mock.Mock(returncode=0, stdout='')
        with mock.patch.object(self.menu.subprocess, 'run', side_effect=answer) as ran, \
                mock.patch.object(self.menu.shutil, 'which', return_value='/bin/tmux'), \
                mock.patch.object(self.menu, 'run') as handed:
            self.assertEqual(self.menu.seat_state(seat), 'stopped, left at a shell')
            self.menu.relaunch('R1', seat)
        self.assertIn(mock.call(['tmux', 'kill-session', '-t', 'review-overseer@t'], capture_output=True), ran.call_args_list)
        self.assertEqual([c.args[0][-3:] for c in handed.call_args_list],
                         [[str(self.menu.ROOT / 'bin/rig'), 'snapshot', 'R1'], ['launch', 'R1', 'review.overseer']])

    def test_an_agent_under_a_wrapper_script_is_not_mistaken_for_a_bare_shell(self):
        self.menu.DRY = False
        seat = self.seat('review.overseer')

        def answer(argv, **kwargs):
            if argv[:2] == ['tmux', 'display']:
                return mock.Mock(returncode=0, stdout='3272 /dev/ttys012\n')
            return mock.Mock(returncode=0, stdout=' 3272 Ss\n 3301 S+\n 3302 S+\n')  # the agent holds the terminal
        with mock.patch.object(self.menu.subprocess, 'run', side_effect=answer), \
                mock.patch.object(self.menu.shutil, 'which', return_value='/bin/tmux'):
            self.assertFalse(self.menu.exited_to_shell(seat))
            self.assertEqual(self.menu.seat_state(seat), 'running')

    def test_without_herdr_an_agent_opens_directly_in_tmux(self):
        seats = [self.seat('control.lead')]
        with mock.patch.object(self.menu, 'herdr', return_value=None), \
                mock.patch.object(self.menu, 'seats', return_value=[dict(seats[0], rigId='R1')]):
            os.environ.pop('TMUX', None)
            output = self.drive(self.menu.team_menu, '2', team='t')
        self.assertIn('RUN tmux attach -t control-lead@t', output)

    def open_goal(self, mode='local', **worker):
        folder = Path(self.project['root']) / '.claude/worktrees/loop-1-rules'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / '.worker-pr.md').write_text('## What changed and why\n')
        worker = {'issue': 1, 'branch': 'feat/rules-1', 'worktree': str(folder), 'ahead': '1',
                  'state': 'ready for review', 'seat': 'engineer-research-agent', **worker}
        state = {'repo': 'owner/repo', 'mode': mode, 'rig': 'feat/snake-game', 'base': 'develop',
                 'base_tip': 'develop', 'ahead': '2', 'workers': [worker], 'folded': []}
        self.project['mode'] = mode
        return mock.patch.object(self.menu, 'loop_state', return_value=state)

    def loop_runs(self, *answers):
        return self.runs(self.drive(self.menu.loop_menu, *answers, project=self.project))

    def test_with_no_goal_open_the_first_lever_starts_one(self):
        self.project['mode'] = 'local'
        with mock.patch.object(self.menu, 'loop_state', return_value={'last_rig': 'feat/old'}):
            output = self.drive(self.menu.loop_menu, '1', 'feat/snake-game', project=self.project)
            self.assertEqual(self.loop_runs('1', ''), [])
        self.assertIn('no goal branch open', output)
        self.assertIn('Last landed: feat/old.', output)
        self.assertTrue(self.runs(output)[0].endswith('bin/ai-work loop owner-repo-1 start feat/snake-game'))

    def test_the_goal_panel_lists_each_worker_and_every_lever(self):
        with self.open_goal():
            output = self.drive(self.menu.loop_menu, project=self.project)
        for label in ('owner/repo · feat/snake-game · 2 ahead of develop',
                      '#1 feat/rules-1 · ready for review · seat in engineer-research-agent',
                      'Dispatch ready tasks in the background', 'Dispatch ready tasks as seats in engineer-research-agent',
                      'Pause dispatch', 'Show everything on feat/snake-game', 'Land feat/snake-game: merge it into develop',
                      'Status', 'Plan', 'Cycle report', 'Tasks', 'Tidy merged branches and worktrees'):
            self.assertIn(label, output)

    def test_seats_are_dispatched_only_into_a_running_team(self):
        with self.open_goal(), mock.patch.object(self.menu, 'rigs', return_value=[]):
            refused = self.drive(self.menu.loop_menu, '3', project=self.project)
        self.assertIn('Start engineer-research-agent first', refused)
        self.assertEqual(self.runs(refused), [])
        with self.open_goal(), mock.patch.object(self.menu, 'rigs', return_value=[{'name': 'engineer-research-agent'}]):
            runs = self.loop_runs('3', '')
            four = self.loop_runs('3', '4')
            self.assertEqual(self.loop_runs('3', 'many'), [])
        self.assertTrue(runs[0].endswith('go LOOP_SEAT_RIG=engineer-research-agent LOOP_CAP=3'))
        self.assertTrue(four[0].endswith('go LOOP_SEAT_RIG=engineer-research-agent LOOP_CAP=4'))

    def test_landing_asks_first_and_runs_the_owner_verb_directly(self):
        loop = str(self.menu.LOOP)
        with self.open_goal():
            self.assertEqual(self.loop_runs('7', 'n'), [])
            self.assertEqual(self.loop_runs('7', 'y'), [f'{loop} close owner/repo --merge'])
        with self.open_goal(mode='owner'):
            self.assertEqual(self.loop_runs('7', 'y'), [f'{loop} close owner/repo --push'])
            self.assertEqual(self.loop_runs('8', '12'), [f'{loop} finish owner/repo 12'])

    def test_the_goal_and_its_workers_open_together_in_vs_code(self):
        with self.open_goal():
            runs = self.loop_runs('6')
        self.assertEqual(runs, [f'code -n {self.project["root"]}/.claude/worktrees/loop-1-rules'])

    def test_a_new_project_can_open_in_vs_code_first_and_be_specced_later(self):
        self.menu.DEV_ROOT = str(self.root)
        folder = self.root / 'tetris'
        project = dict(self.project, root=str(folder), repo='owner/tetris', id='owner-tetris')
        with mock.patch.object(self.menu, 'catalog', return_value=[project]), \
                mock.patch.object(self.menu, 'project_menu'):
            runs = self.runs(self.drive(self.menu.new_project, 'Tetris', 'a falling-blocks game', '3'))
        self.assertEqual(runs[1], f'code {folder}')
        with mock.patch.object(self.menu, 'pick_account', return_value='anthropic-bravo'):
            later = self.runs(self.drive(self.menu.spec_session, 'add a hold piece', '1', project=project))
        self.assertIn('Use the intake skill to spec out this project. The goal: add a hold piece.', later[0])
        self.assertIn('Scope paths do not overlap', later[0])

    def test_a_claude_only_team_is_shaped_when_it_first_starts(self):
        with mock.patch.object(self.menu, 'rigs', return_value=[]), \
                mock.patch.object(self.menu, 'seats', return_value=[]):
            output = self.drive(self.menu.project_team, '1', '2', 'y', '', project=self.project)
        self.assertTrue(self.runs(output)[0].endswith('bin/rig-shape write owner/repo build --all claude-code'))

    def test_a_new_project_starts_from_a_goal_and_opens_a_client_to_spec_it(self):
        self.menu.DEV_ROOT = str(self.root)
        folder = self.root / 'tetris'
        project = dict(self.project, root=str(folder), repo='owner/tetris', id='owner-tetris')
        with mock.patch.object(self.menu, 'catalog', return_value=[project]), \
                mock.patch.object(self.menu, 'pick_account', return_value='anthropic-bravo'), \
                mock.patch.object(self.menu, 'project_menu') as opened:
            output = self.drive(self.menu.new_project, 'Tetris', 'a falling-blocks game', '1')
        runs = self.runs(output)
        self.assertTrue(runs[0].endswith(f'bin/new-repo {folder} --register --personal'))
        self.assertIn(f'--cwd {folder} -- Use the intake skill to spec out this project. '
                      'The goal: a falling-blocks game.', runs[1])
        opened.assert_called_once_with(project)
        self.assertEqual(self.runs(self.drive(self.menu.new_project, '')), [])

    def test_a_worker_is_merged_up_released_or_resumed_from_its_own_menu(self):
        loop = str(self.menu.LOOP)
        with self.open_goal():
            self.assertEqual(self.loop_runs('1', '5'), [f'{loop} fold owner/repo 1'])
            released = self.loop_runs('1', '4')
            self.assertTrue(released[0].endswith('bin/dev-workspace remove-worker --rig engineer-research-agent '
                                                 f'--cwd {self.project["root"]}/.claude/worktrees/loop-1-rules'))
            self.assertIn('diff feat/snake-game...feat/rules-1', self.loop_runs('1', '1')[0])
        with self.open_goal(seat=None, state='working'):
            self.assertEqual(self.loop_runs('1', '4'), [f'{loop} resume owner/repo 1'])

    def test_tasks_are_listed_checked_and_written_from_the_menu(self):
        loop = str(self.menu.LOOP)
        with mock.patch.object(self.menu, 'loop_state', return_value={}):
            self.project['mode'] = 'local'
            runs = self.loop_runs('5', '3', 'Score', 'src/score/', '#1', 'y')
        self.assertEqual(runs[0], f'{loop} tasks owner/repo new Score --scope src/score/ --depends #1 --ready'
                                  f'  in {self.project["root"]}')

    def test_engineer_is_on_the_home_screen_and_asks_for_a_project_first(self):
        other = dict(self.project, id='elsewhere', source='discovered', root='/x/other')
        with mock.patch.object(self.menu, 'catalog', return_value=[self.project, other]), \
                mock.patch.object(self.menu, 'start_role') as role:
            output = self.drive(self.menu.engineer_menu, '1')
        self.assertNotIn('other', output)
        role.assert_called_once_with('engineer', self.project)

    def test_a_menu_left_open_across_an_update_restarts_into_the_new_release(self):
        self.menu.DRY = False
        release = self.root / 'releases/new'
        (release / 'bin').mkdir(parents=True)
        (release / 'bin/ai').write_text('')
        (self.root / 'current').symlink_to(release)
        with mock.patch.object(self.menu, 'CURRENT', self.root / 'current'), \
                mock.patch.object(self.menu.os, 'execv') as execv:
            self.menu.upgrade_if_released()
        execv.assert_called_once_with(self.menu.sys.executable, [self.menu.sys.executable, str(release.resolve() / 'bin/ai')])
        with mock.patch.object(self.menu, 'CURRENT', self.root / 'current'), \
                mock.patch.object(self.menu, 'ROOT', release.resolve()), mock.patch.object(self.menu.os, 'execv') as execv:
            self.menu.upgrade_if_released()
        execv.assert_not_called()

    def test_choosing_filters_and_refuses_numbers_that_are_not_shown(self):
        items = [('alpha', 'a'), ('beta', 'b'), ('alphabet', 'c')]
        picked = {}
        output = self.drive(lambda: picked.setdefault('value', self.menu.choose('T', items)), 'alph', '3', '2')
        self.assertIn('There is no 3 here.', output)
        self.assertEqual(picked['value'], 'c')

    def test_only_the_default_anthropic_url_is_dropped(self):
        with mock.patch.dict(os.environ, {'ANTHROPIC_BASE_URL': 'https://api.anthropic.com', 'CLAUDECODE': '1'}):
            self.menu.clean_environment()
            self.assertNotIn('ANTHROPIC_BASE_URL', os.environ)
            self.assertNotIn('CLAUDECODE', os.environ)
        with mock.patch.dict(os.environ, {'ANTHROPIC_BASE_URL': 'http://127.0.0.1:1'}):
            self.menu.clean_environment()
            self.assertEqual(os.environ['ANTHROPIC_BASE_URL'], 'http://127.0.0.1:1')


    def test_fast_arrow_presses_are_read_one_at_a_time(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        tty.setcbreak(slave)  # key-at-a-time input, as while the menu is waiting for a key
        os.write(master, b'\x1b[B\x1b[B\x1bOAx\x7f\r')
        with mock.patch.object(self.menu.sys, 'stdin', mock.Mock(fileno=lambda: slave)):
            keys = [self.menu.read_key() for _ in range(6)]
        self.assertEqual(keys, ['down', 'down', 'up', 'x', 'backspace', 'enter'])
        os.write(master, b'\x1b')
        with mock.patch.object(self.menu.sys, 'stdin', mock.Mock(fileno=lambda: slave)):
            self.assertEqual(self.menu.read_key(), 'esc')

    def home_labels(self, *answers, launcher=None):
        with mock.patch.object(self.menu, 'upgrade_if_released'), \
                mock.patch.object(self.menu, 'project_for', return_value=None), \
                mock.patch.object(self.menu, 'role_launcher', return_value=launcher):
            output = self.drive(self.menu.home, *answers)
        # With no answers the home screen is shown once, so each numbered line is one of its entries.
        return [line.split(None, 1)[1] for line in output.splitlines() if line[:4].strip().isdigit()], output

    MACHINE = ('note', 'tasks', 'task', 'say', 'recall', 'dash', 'ol-hold')

    def test_a_machine_command_is_found_on_the_command_path(self):
        with mock.patch.dict(os.environ, {'PATH': str(self.machine_bin)}):
            self.assertIsNone(self.real_machine('note'))
            self.on_path('note')
            self.assertEqual(self.real_machine('note'), str(self.machine_bin / 'note'))

    def test_without_the_machine_layer_the_home_screen_is_as_before(self):
        labels, _ = self.home_labels()
        self.assertEqual(labels, ['Projects', 'Start a new project', 'Recent sessions', 'Teams', 'Accounts and setup'])

    def test_the_home_screen_shows_the_daily_things_first_and_the_machine_last(self):
        self.on_path(*self.MACHINE)
        labels, _ = self.home_labels(launcher='/usr/local/bin/agent')
        self.assertEqual(labels, ['Write', 'Tasks', 'Inbox', 'Chat', 'Search everything',
                                  'Projects', 'Start a new project', 'Recent sessions',
                                  'Assistant, personal', 'Ops, this machine', 'Engineer, on a project', 'Role conversations in Pi',
                                  'Teams', 'Dashboard', 'This machine', 'Accounts and setup'])

    def test_each_machine_entry_needs_its_own_command(self):
        for command, entry in (('note', 'Write'), ('tasks', 'Tasks'), ('task', 'Inbox'), ('say', 'Chat'),
                               ('recall', 'Search everything'), ('dash', 'Dashboard'), ('ol-hold', 'This machine')):
            for leftover in self.machine_bin.iterdir():
                leftover.unlink()
            self.on_path(command)
            labels, _ = self.home_labels()
            self.assertIn(entry, labels)
            self.assertEqual(len(labels), 6, (command, labels))

    def test_home_hands_write_chat_search_and_the_dashboard_to_their_commands(self):
        self.on_path(*self.MACHINE)
        self.assertEqual(self.runs(self.home_labels('1', '1')[1]), ['note'])
        self.assertEqual(self.runs(self.home_labels('1', '2')[1]), ['note yesterday'])
        self.assertEqual(self.runs(self.home_labels('1', '3', 'paid the rent')[1]), ['note paid the rent'])
        self.assertEqual(self.runs(self.home_labels('4', '1', 'hello @ops')[1]), ['say hello @ops'])
        self.assertEqual(self.runs(self.home_labels('5', 'bank')[1]), ['sh -c "$@" 2>&1 | less -RFX sh recall bank'])
        self.assertEqual(self.runs(self.home_labels('10')[1]), ['dash'])

    def test_a_journal_task_is_finished_or_added_through_task_and_tasks(self):
        tasks = [{'n': 1, 'text': 'Call the bank', 'file': '1.txt', 'due': '2026-01-01', 'tags': ['home']}]
        with mock.patch.object(self.menu, 'journal_tasks', return_value=tasks), \
                mock.patch.object(self.menu, 'tasks_summary', return_value='1 open, 1 overdue'):
            done = self.drive(self.menu.journal_tasks_menu, '1', '1')
            added = self.runs(self.drive(self.menu.journal_tasks_menu, '2', 'Pay rent', 'friday', '3', 'home bills'))
        self.assertIn('1 open, 1 overdue', done)
        self.assertIn('Call the bank  · overdue 2026-01-01, #home', done)
        self.assertEqual(self.runs(done), ['tasks done 1'])
        self.assertEqual(added, ['task Pay rent --due friday --priority high --tag home --tag bills'])

    def test_a_proposal_in_the_inbox_is_taken_as_a_task_and_filed_away(self):
        self.menu.INBOX = self.root / 'inbox'
        self.menu.INBOX.mkdir()
        item = self.menu.INBOX / '2026-11-23-0900-assistant-task-ab12.txt'
        item.write_text('Call the bank\ndue: friday\ntags: #home\n')
        output = self.drive(self.menu.inbox_menu, '1', '2')
        self.assertIn('Inbox · 1 waiting', output)
        self.assertEqual(self.runs(output), ['task Call the bank --due friday --tag home'])
        self.assertFalse(item.exists())
        self.assertTrue((self.root / 'archive/inbox' / item.name).is_file())

    def test_this_machine_shows_only_the_parts_whose_commands_are_present(self):
        self.menu.HOLD = self.root / 'hold'
        self.on_path('ol-hold', 'brief')
        output = self.drive(self.menu.machine_menu, '2', '1', '1')
        self.assertIn('Rounds on · local model on', output)
        for absent in ('Terminals', 'Screen on', 'Services', 'Send a test alert'):
            self.assertNotIn(absent, output)
        self.assertEqual(self.runs(output), ['brief', 'sudo -n /usr/local/bin/ol-hold stream off'])

    def test_a_terminal_is_opened_through_tmux(self):
        rows = [{'name': 'work', 'viewers': 0, 'created': 0, 'command': 'zsh', 'path': '~', 'here': False}]
        with mock.patch.object(self.menu, 'terminals', return_value=rows), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('TMUX', None)
            output = self.drive(self.menu.terminals_menu, '1', '1')
        self.assertIn('work · no viewer · zsh in ~', output)
        self.assertEqual(self.runs(output), ['tmux attach -t work:'])

    def test_a_worker_is_dropped_only_after_a_yes(self):
        loop = str(self.menu.LOOP)
        with self.open_goal():
            self.assertEqual(self.loop_runs('1', '6', 'n'), [])
            self.assertEqual(self.loop_runs('1', '6', 'y'), [f'{loop} drop owner/repo 1'])

    def test_the_roles_earlier_pi_conversations_resume_through_ai_session(self):
        rows = {'sessions': [{'id': 'pi-x', 'runtime': 'pi', 'owner': 'assistant', 'title': 'groceries', 'cwd': '/home/assistant',
                              'project': None, 'updated_at': None},
                             {'id': 'claude-abc', 'runtime': 'claude', 'owner': 'user', 'title': None, 'cwd': '/x',
                              'project': None, 'updated_at': None}]}
        with mock.patch.object(self.menu, 'catalog', return_value=[]), \
                mock.patch.object(self.menu.workspace, 'session_rows', return_value=rows):
            output = self.drive(self.menu.sessions_menu, '1', project=None, pi=True)
        self.assertIn('[assistant] · assistant · groceries', output)
        self.assertNotIn('[claude]', output)
        self.assertTrue(self.runs(output)[0].endswith('bin/ai-session resume pi-x --execute'))

    def test_keyboard_picking_moves_filters_and_backs_out(self):
        items = [('alpha', 'a'), ('beta', 'b'), ('alphabet', 'c')]

        def pick(*keys):
            presses = iter(keys)
            with mock.patch.object(self.menu, 'keyboard', return_value=True), \
                    mock.patch.object(self.menu, 'read_key', lambda: next(presses)), redirect_stdout(io.StringIO()):
                return self.menu.choose('T', items)
        self.assertEqual(pick('down', 'down', 'enter'), 'c')
        self.assertEqual(pick('up', 'enter'), 'c')  # up from the top wraps to the bottom
        self.assertEqual(pick('b', 'enter'), 'b')
        self.assertEqual(pick('a', 'l', 'p', 'h', 'down', 'enter'), 'c')
        self.assertEqual(pick('z', 'esc', 'enter'), 'a')  # Esc clears the filter first
        self.assertIsNone(pick('esc'))
        self.assertIsNone(pick('left'))


if __name__ == '__main__':
    unittest.main()
