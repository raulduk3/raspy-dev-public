"""dev-forge: one goal as a forge (docs/forge.md; docs/spec/SDD.md, items SC-08 and SC-22 to SC-27)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_stability as loop_fixture  # noqa: E402  (a module import: its test classes do not run a second time here)

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/dev-forge'
sys.path.insert(0, str(PLATFORM / 'lib'))
from ai_ecosystem import forge  # noqa: E402


class KitFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='forge-test-')
        self.addCleanup(self.tmp.cleanup)
        self.rig = Path(self.tmp.name) / 'rig'
        self.rig.mkdir()
        self.env = {'PATH': __import__('os').environ['PATH'], 'HOME': self.tmp.name, 'DEV_FORGE_RIG': str(self.rig),
                    'DEV_FORGE_STATE': str(Path(self.tmp.name) / 'state')}
        self.profile()

    def profile(self, **over):
        self.rig.joinpath('forge.json').write_text(json.dumps({'schema': forge.SCHEMA, 'places': {'light': 2, 'heavy': 1, 'mem_min_mb': 0}, **over}))

    def forge(self, *args, expected=0, input=None):
        done = subprocess.run([sys.executable, str(CLI), *args], env=self.env, capture_output=True, text=True, input=input, timeout=60)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        return done


class ChannelTests(KitFixture):
    def test_a_post_is_read_one_time_and_kept_as_the_record(self):
        self.forge('post', 'orchestrator', 'w-1', 'READY #1 abc')
        self.forge('post', 'orchestrator', 'w-2', input='READY #2\nsecond line\n')
        out = self.forge('wait', 'orchestrator', '--seconds', '1', '--poll', '0.1').stdout
        self.assertIn('From: w-1', out)
        self.assertIn('second line', out)
        self.assertEqual(len(list((self.rig / 'inbox/orchestrator/read').glob('*.md'))), 2)
        self.assertIn('wait: none', self.forge('wait', 'orchestrator', '--seconds', '0.2', '--poll', '0.1').stdout)

    def test_a_bad_name_and_an_empty_message_are_refused(self):
        self.assertIn('lowercase', self.forge('post', '../x', 'w-1', 'text', expected=2).stderr)
        self.assertIn('empty', self.forge('post', 'orchestrator', 'w-1', input='', expected=2).stderr)

    def test_stale_lists_a_message_that_nobody_read(self):
        self.forge('post', 'orchestrator', 'w-1', 'READY')
        self.assertIn('orchestrator', self.forge('stale', '0').stdout)
        self.assertEqual(self.forge('stale', '5').stdout, '')


class PlaceTests(KitFixture):
    def test_one_heavy_place_runs_one_command_at_a_time(self):
        log = Path(self.tmp.name) / 'order'
        step = f'echo start >> {log}; sleep 0.4; echo end >> {log}'
        threads = [threading.Thread(target=self.forge, args=('run', 'heavy', '--', 'sh', '-c', step)) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(log.read_text().split(), ['start', 'end'] * 3)

    def test_the_exit_code_of_the_command_comes_back(self):
        self.forge('run', 'light', '--', 'sh', '-c', 'exit 7', expected=7)

    def test_an_unknown_field_of_the_profile_is_refused(self):
        self.profile(speed=3)
        self.assertIn('unknown field speed', self.forge('profile', expected=2).stderr)


class RigProfileTests(KitFixture):
    """forge.json is the one profile of a rig: it names the project record and states its kind (SDD-PJ-01, SDD-SC-23)."""

    def setUp(self):
        super().setUp()
        home = Path(self.tmp.name)
        self.checkout = home / 'product'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.checkout)], check=True)
        (self.checkout / 'bin').mkdir()
        (self.checkout / 'bin/check').write_text('#!/bin/sh\n')
        (self.checkout / 'bin/check').chmod(0o755)
        self.records = home / '.config/dev-platform/projects'
        self.records.mkdir(parents=True)
        self.record(check='make all-checks')

    def record(self, **work):
        (self.records / 'product.json').write_text(json.dumps({
            'schema': 'dev-platform.spec-tree@1', 'name': 'product', 'top': None, 'repositories': [
                {'name': 'server', 'path': str(self.checkout), 'layout': 'none', 'remote': 'acme/product',
                 'git': {'tier': 3, 'mode': 'local', 'slots': 7}, 'work': work}]}))

    def shown(self):
        return json.loads(self.forge('profile').stdout)

    def test_a_profile_takes_the_repository_the_slots_and_the_check_from_the_project_record(self):
        self.profile(project='product')
        shown = self.shown()
        self.assertEqual((shown['repo'], shown['workers']['limit'], shown['commands']['full']), ('acme/product', 7, 'make all-checks'))
        self.profile(project='product', workers={'limit': 2}, commands={'full': 'bin/check'})   # a stated value wins
        shown = self.shown()
        self.assertEqual((shown['workers']['limit'], shown['commands']['full']), (2, 'bin/check'))
        self.profile(project='product', repo='acme/other')
        self.assertIn('state one of the two', self.forge('profile', expected=2).stderr)
        self.profile(project='absent')
        self.assertIn('no project record has the name absent', self.forge('profile', expected=2).stderr)
        self.profile()   # a profile with no project and no repository: the default of the loop
        self.assertEqual(self.shown()['workers']['limit'], 2)

    def test_the_kind_of_a_rig_gives_the_worker_runtime(self):
        self.assertEqual((self.shown()['kind'], self.shown()['workers']['runtime']), ('forge', 'claude'))
        for kind, runtime in (('openrig', 'seat'), ('harness', 'hand'), ('api', 'pi')):
            self.profile(kind=kind)
            self.assertEqual(self.shown()['workers']['runtime'], runtime)
        self.profile(workers={'runtime': 'hand'})   # the older profile with a runtime only
        self.assertEqual(self.shown()['kind'], 'harness')
        self.profile(kind='harness', workers={'runtime': 'seat'})
        self.assertIn('a rig of the kind harness has the worker runtime hand, not seat', self.forge('profile', expected=2).stderr)
        self.profile(kind='swarm')
        self.assertIn('kind is one of forge, openrig, harness, api', self.forge('profile', expected=2).stderr)

    def test_init_names_the_project_and_repeats_no_value_of_its_record(self):
        done = self.forge('init', str(self.checkout))
        proposed = json.loads(done.stdout)
        self.assertEqual((proposed['kind'], proposed['project'], proposed['repo']), ('forge', 'product', ''))
        self.assertEqual((proposed['workers']['limit'], proposed['commands']['full']), (None, None))
        self.assertIn('the full check is the check command of the project record', done.stderr)
        self.record()   # the record states no check: the check script of the repository is the full check
        proposed = json.loads(self.forge('init', str(self.checkout)).stdout)
        self.assertEqual(proposed['commands']['full'], 'bin/check')
        (self.records / 'product.json').unlink()
        done = self.forge('init', str(self.checkout))
        self.assertEqual(json.loads(done.stdout)['project'], None)
        self.assertIn('no project record holds this checkout', done.stderr)


class DetectTests(unittest.TestCase):
    def detect(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                path = Path(tmp) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                if name.startswith(('bin/', 'scripts/')):
                    path.chmod(0o755)
            return forge.detect(tmp)

    def test_each_project_type_gets_its_commands(self):
        bun, _ = self.detect({'package.json': json.dumps({'scripts': {'check': 'x', 'test': 'y', 'typecheck': 'z'}}), 'bun.lock': ''})
        self.assertEqual((bun['install'], bun['cheap'], bun['proof'], bun['full']),
                         ('bun install --frozen-lockfile', 'bun run typecheck', 'bun run test', 'bun run check'))
        python, _ = self.detect({'pyproject.toml': ''})
        self.assertEqual(python['full'], 'python3 -m pytest -q')
        rust, _ = self.detect({'Cargo.toml': ''})
        self.assertEqual((rust['cheap'], rust['full']), ('cargo check', 'cargo test'))

    def test_a_check_script_is_the_full_check_and_a_static_project_has_none(self):
        commands, _ = self.detect({'pyproject.toml': '', 'bin/check': '#!/bin/sh\n'})
        self.assertEqual(commands['full'], 'bin/check')
        commands, notes = self.detect({'index.html': ''})
        self.assertIsNone(commands['full'])
        self.assertTrue(any('folds nothing' in note for note in notes))


class GoalFixture(loop_fixture.Fixture):
    """A local repository with an open goal branch and three tasks whose scopes do not overlap."""

    def setUp(self):
        super().setUp()
        self.run_cmd('git', 'checkout', '-qb', 'develop')
        tasks = self.repo / 'docs/tasks'
        tasks.mkdir(parents=True)
        (tasks / 'README.md').write_text('# Tasks\n')
        (tasks / '1-game-rules.md').write_text('# Game rules\n\nStatus: ready\nLabels: enhancement\nScope: source\nDepends on: none\n\nBuild it.\n')
        (tasks / '3-draft.md').write_text('# Draft\n\nStatus: draft\nScope: other\nDepends on: none\n')
        self.configure(base='develop', personal=True, identity='local', extra='\tslots=4')
        self.workspace = self.fakebin / 'dev-workspace'
        self.workspace.write_text(f'#!/bin/sh\necho "$*" >> {self.base / "dev-workspace.calls"}\n')
        self.workspace.chmod(0o755)
        for number, scope in ((5, 'five'), (6, 'six')):
            (tasks / f'{number}-part.md').write_text(f'# Part {number}\n\nStatus: ready\nScope: {scope}\nDepends on: none\n')
        (tasks / '7-inner.md').write_text('# Inner\n\nStatus: ready\nScope: five/inner\nDepends on: none\n')
        (tasks / '8-wide.md').write_text('# No scope\n\nStatus: ready\nDepends on: none\n')
        # The full check fails while the file five/broken is in the tree.
        self.write_check('[ ! -e five/broken ] || { echo "broken is here"; exit 1; }\n')
        self.commit()
        self.rig = self.base / 'rig'
        self.rig.mkdir()
        self.env.update(DEV_FORGE_RIG=str(self.rig), DEV_FORGE_STATE=str(self.base / 'forge-state'),
                        DEV_WORKSPACE=str(self.workspace), LOOP_SEAT_RIG='engineer-repo')
        self.profile(full='bin/check')
        self.loop('start', loop_fixture.RIG)

    def profile(self, full, **over):
        (self.rig / 'forge.json').write_text(json.dumps({
            'schema': forge.SCHEMA, 'repo': 'test/repo', 'commands': {'full': full, 'proof': 'sh -c "true" {tests}'},
            'places': {'light': 1, 'heavy': 1, 'mem_min_mb': 0}, **over}))

    def forge(self, *args, expected=0):
        return self.run_cmd(sys.executable, CLI, *args, expected=expected)

    def work(self, number, name, text='x\n'):
        slot = loop_fixture.LocalLoopTests.slot_of(self, number)
        (slot / name).parent.mkdir(parents=True, exist_ok=True)
        (slot / name).write_text(text)
        self.run_cmd('git', 'add', name, cwd=slot)
        self.run_cmd('git', 'commit', '-qm', f'feat: task {number}', cwd=slot)

    def folded(self):
        return self.run_cmd('git', 'log', '--format=%s', f'develop..{loop_fixture.RIG}').stdout


class ReadyTests(GoalFixture):
    def test_a_task_is_held_while_a_running_task_shares_its_scope(self):
        out = self.forge('ready').stdout
        self.assertIn('#5\tFREE', out)
        self.assertIn('#7\tFREE', out)
        self.assertNotIn('#3', out)   # a draft
        self.forge('loop', '--', 'go', 'only', '5')
        out = self.forge('ready').stdout
        self.assertIn('#5\tIN WORK', out)
        self.assertIn('#7\theld by #5: five/inner', out)
        self.assertIn('#6\tFREE', out)
        self.assertIn('#8\tALONE', out)

    def test_a_wide_path_of_the_profile_holds_no_task(self):
        self.profile(full='bin/check', wide=['five/inner'])
        self.forge('loop', '--', 'go', 'only', '7')
        self.assertIn('#5\tFREE', self.forge('ready').stdout)


class LoopDoorTests(GoalFixture):
    def test_the_brief_names_the_short_proof_and_the_stop_hook_marker_is_set(self):
        self.forge('loop', '--', 'go', 'only', '5')
        brief = (loop_fixture.LocalLoopTests.slot_of(self, 5) / '.worker-brief.md').read_text()
        self.assertIn('Do NOT run the full check', brief)
        self.assertIn('dev-forge run light -- sh -c "true" {tests}', brief)
        marker = self.repo / '.git/dev-platform/orchestrated'
        self.assertTrue(marker.exists())
        self.forge('end')
        self.assertFalse(marker.exists())

    def test_a_hand_worker_gets_a_slot_and_a_brief_and_no_process(self):
        self.profile(full='bin/check', workers={'runtime': 'hand'})
        del self.env['LOOP_SEAT_RIG']
        out = self.forge('loop', '--', 'go', 'only', '5').stdout
        self.assertIn('hand: start one worker in that folder', out)
        self.assertTrue((loop_fixture.LocalLoopTests.slot_of(self, 5) / '.worker-brief.md').exists())
        self.assertFalse((self.base / 'dev-workspace.calls').exists())

    def test_a_worker_of_a_plain_loop_still_runs_the_full_check(self):
        self.loop('go', 'only', '5')
        brief = (loop_fixture.LocalLoopTests.slot_of(self, 5) / '.worker-brief.md').read_text()
        self.assertIn('check-once.sh', brief)
        self.assertNotIn('Do NOT run the full check', brief)

    def test_the_brief_of_a_task_holds_the_rules_of_the_profile(self):
        out = self.forge('brief', '5').stdout
        self.assertIn('Write no comment inside a function', out)
        self.assertIn('Scope: five', out)
        self.assertIn('post orchestrator w-5', out)


class BatchTests(GoalFixture):
    def test_one_full_check_folds_each_task_of_a_good_batch(self):
        self.forge('loop', '--', 'go', 'only', '1', '5', '6')
        self.work(1, 'source', 'changed\n')
        self.work(5, 'five/a')
        self.work(6, 'six/a')
        out = self.forge('batch', '1', '5', '6').stdout
        self.assertIn('batch: 3 stacked, 3 folded, 1 full check(s), pass', out)
        self.assertEqual(self.folded().count('(#'), 3)
        row = (self.rig / 'batches.tsv').read_text().splitlines()[1].split('\t')
        self.assertEqual(row[1:5], ['3', '3', '1', 'pass'])
        self.assertIn('checks_per_fold\t0.33', self.forge('measure').stdout)

    def test_a_failed_batch_folds_the_tasks_before_the_bad_task_and_reports_it(self):
        self.forge('loop', '--', 'go', 'only', '1', '5', '6')
        self.work(1, 'source', 'changed\n')
        self.work(5, 'five/broken')
        self.work(6, 'six/a')
        out = self.forge('batch', '1', '5', '6', expected=1).stdout
        self.assertIn('#5: the full check fails', out)
        self.assertIn('#6: left for the next batch', out)
        self.assertIn('1 folded', out)
        self.assertIn('Game rules (#1)', self.folded())
        self.assertNotIn('(#5)', self.folded())
        failed = self.forge('wait', 'orchestrator', '--seconds', '1', '--poll', '0.1').stdout
        self.assertIn('FAILED #5', failed)
        self.assertIn('broken is here', failed)
        # The bad task and the task after it keep their slots for the next batch.
        self.assertEqual(loop_fixture.LocalLoopTests.slot_of(self, 6).name[:5], 'slot-')

    def test_a_profile_with_no_full_check_folds_nothing(self):
        self.profile(full=None)
        self.forge('loop', '--', 'go', 'only', '5')
        self.work(5, 'five/a')
        out = self.forge('batch', '5', expected=3).stdout
        self.assertIn('nothing is folded', out)
        self.assertEqual(self.folded(), '')

    def test_a_goal_that_ends_removes_the_check_folder(self):
        self.forge('loop', '--', 'go', 'only', '5')
        self.work(5, 'five/a')
        self.forge('batch', '5')
        self.assertTrue((self.repo / forge.TRIAL).is_dir())
        self.assertNotIn('forge-check', self.loop('tidy').stdout)



class GhostTasksTests(loop_fixture.Fixture):
    """A ghost project: the task files are in the side folder, and the repository holds no task file (SDD-PJ-10)."""
    profile, forge, work, folded = GoalFixture.profile, GoalFixture.forge, GoalFixture.work, GoalFixture.folded

    def setUp(self):
        super().setUp()
        self.run_cmd('git', 'checkout', '-qb', 'develop')
        self.write_check('true\n')
        self.commit()
        self.side = self.base / 'side'
        tasks = self.side / 'docs/tasks'
        tasks.mkdir(parents=True)
        (tasks / 'README.md').write_text('# Tasks\n')
        (tasks / '1-game-rules.md').write_text('# Game rules\n\nStatus: ready\nLabels: enhancement\nScope: source\nDepends on: none\n\nBuild it.\n')
        (tasks / '5-part.md').write_text('# Part 5\n\nStatus: ready\nScope: five\nDepends on: none\n')
        self.run_cmd('git', 'init', '-q', '-b', 'main', self.side)
        self.run_cmd('git', 'add', '-A', cwd=self.side)
        self.run_cmd('git', 'commit', '-qm', 'the tasks of a foreign repository', cwd=self.side)
        self.configure(base='develop', personal=True, identity='local', extra=f'\ttracker=side\tside={self.side}\tslots=4')
        self.workspace = self.fakebin / 'dev-workspace'
        self.workspace.write_text(f'#!/bin/sh\necho "$*" >> {self.base / "dev-workspace.calls"}\n')
        self.workspace.chmod(0o755)
        self.rig = self.base / 'rig'
        self.rig.mkdir()
        self.env.update(DEV_FORGE_RIG=str(self.rig), DEV_FORGE_STATE=str(self.base / 'forge-state'),
                        DEV_WORKSPACE=str(self.workspace), LOOP_SEAT_RIG='engineer-repo')
        self.profile(full='bin/check')
        self.loop('start', loop_fixture.RIG)

    def side_log(self):
        return self.run_cmd('git', 'log', '--format=%s', cwd=self.side).stdout

    def test_the_loop_reads_the_tasks_of_the_side_folder(self):
        listed = self.loop('tasks', 'list').stdout
        self.assertIn('#1 ready', listed)
        self.assertIn('#5 ready', listed)
        self.assertFalse((self.repo / 'docs/tasks').exists())
        out = self.forge('ready').stdout
        self.assertIn('#1\tFREE', out)
        self.assertIn('#5\tFREE', out)
        self.assertIn(f'`{self.side}/docs/tasks/` (outside your slot; do not change it)', self.forge('brief', '5').stdout)

    def test_a_fold_marks_the_task_done_in_the_side_folder_and_adds_no_task_file_to_the_repository(self):
        self.forge('loop', '--', 'go', 'only', '5')
        slot = loop_fixture.LocalLoopTests.slot_of(self, 5)
        self.assertIn(f'{self.side}/docs/tasks/5-part.md', (slot / '.worker-brief.md').read_text())
        self.work(5, 'five/a')
        self.assertIn('1 folded', self.forge('batch', '5').stdout)
        self.assertIn('(#5)', self.folded())
        self.assertIn('chore(tasks): mark #5 done', self.side_log())
        self.assertTrue((self.side / 'docs/tasks/done/5-part.md').is_file())
        self.assertEqual(self.run_cmd('git', 'status', '--porcelain', cwd=self.side).stdout, '')
        tracked = self.run_cmd('git', 'ls-tree', '-r', '--name-only', loop_fixture.RIG).stdout
        self.assertNotIn('docs/tasks', tracked)   # the repository holds no task file
        self.assertNotIn('#5', self.forge('ready').stdout)
        self.assertNotIn('#5 ', self.loop('tasks', 'list').stdout)

    def test_a_side_tracker_with_no_side_folder_is_refused(self):
        self.configure(base='develop', personal=True, identity='local', extra='\ttracker=side')
        done = self.loop('tasks', 'list', expected=2)
        self.assertIn('tracker=side needs the registry field side=', done.stdout)


if __name__ == '__main__':
    unittest.main()
