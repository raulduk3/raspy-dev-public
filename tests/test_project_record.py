"""dev-project: the project record is the source of the registry and of the check environment (docs/spec/SDD.md, area PJ)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'bin/dev-project'
SPEC = ROOT / 'bin/dev-spec'
TIERS = ROOT / 'lib/ai_ecosystem/tiers.py'
HOOK = ROOT / 'hooks/check-once.sh'


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='project-record-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects, self.conf = self.tmp / 'projects', self.tmp / 'repos.conf'
        self.env = dict(os.environ, DEV_PLATFORM_PROJECTS=str(self.projects), DEV_PLATFORM_REPOS=str(self.conf),
                        DEV_PLATFORM_PERSONAL=str(self.tmp / 'personal.conf'), DEV_PLATFORM_ENV_DIR=str(self.tmp / 'env.d'),
                        DEV_PLATFORM_STATE=str(self.tmp / 'state'), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        self.env.pop('DEV_PLATFORM_CHECK', None)
        for name in ('own', 'company', 'domains'):
            repo = self.tmp / name
            sh(self.tmp, 'git', 'init', '-q', '-b', 'main', str(repo))
            (repo / 'a.txt').write_text('a\n')
            sh(repo, 'git', 'add', '-A')
            sh(repo, 'git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '-m', 'first')
        (self.tmp / 'personal.conf').write_text(f'{self.tmp}/own\n')
        self.conf.write_text('# a note of the owner\n'
                             f'me/own {self.tmp}/own local main\n'
                             f'Org/company {self.tmp}/company owner develop keep=main,release slots=4\n'
                             f'me/domains {self.tmp}/domains local main tier=1 spec=domains decisions=frozen tasks=json\n')
        (self.tmp / 'env.d').mkdir()
        (self.tmp / 'env.d/company.sh').write_text('# pinned tools\nexport PATH="$HOME/.bun/bin:$PATH"\nexport BUN_PATH="$HOME/.bun/bin/bun"\n')

    def run_cli(self, *args, expected=0):
        done = subprocess.run([sys.executable, '-I', str(CLI), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        return done

    def tier(self, name):
        done = subprocess.run([sys.executable, '-I', str(TIERS), '--json', str(self.tmp / name)], env=self.env, capture_output=True, text=True)
        return json.loads(done.stdout)

    def record(self, name):
        return json.loads((self.projects / f'{name}.json').read_text())


class Record(Fixture):
    def test_import_makes_one_record_for_each_line_and_sync_gives_the_same_settings(self):   # SDD-PJ-01
        before = {name: self.tier(name) for name in ('own', 'company', 'domains')}
        done = self.run_cli('import')
        self.assertIn('3 records to write', done.stdout)
        self.assertFalse(self.projects.exists())   # nothing is written with no --write
        self.run_cli('import', '--write')
        own, company, domains = (self.record(n)['repositories'][0] for n in ('own', 'company', 'domains'))
        self.assertEqual((own['remote'], own['git']['tier'], own['git']['mode'], own['git']['base']), ('me/own', 2, 'local', 'main'))   # the personal list
        self.assertEqual(company['git'], {'tier': 3, 'mode': 'owner', 'base': 'develop', 'forge': 'github', 'keep': ['main', 'release'],
                                          'slots': 4, 'large': False})
        self.assertEqual(company['work'], {'tracker': 'github', 'tasks': 'md', 'decisions': 'open', 'incoming': 'state',
                                           'check_path': ['~/.bun/bin'], 'env': {'BUN_PATH': '~/.bun/bin/bun'}})
        self.assertEqual((domains['layout'], domains['work']['decisions'], domains['work']['tasks']), ('domains', 'frozen', 'json'))
        self.assertIn('2 files differ', self.run_cli('sync').stdout)
        self.run_cli('sync', '--check', expected=1)
        done = self.run_cli('sync', '--write')
        self.assertIn('# a note of the owner', (self.tmp / 'repos.conf.by-hand').read_text())   # the notes of the owner are kept one time
        self.assertTrue(self.conf.read_text().startswith('# Made by dev-project sync'))
        (self.tmp / 'personal.conf').unlink()   # each line has its tier now: the personal list is read for no line
        self.assertEqual({name: self.tier(name) for name in before}, before)
        self.assertIn(f'export PATH={Path.home()}/.bun/bin:"$PATH"', (self.tmp / 'env.d/company.sh').read_text())
        self.run_cli('sync', '--check')
        self.assertIn('equal to the records', self.run_cli('sync').stdout)
        self.assertIn('Each line of the registry has a record', self.run_cli('import').stdout)

    def test_the_record_is_the_source_a_change_of_it_changes_the_registry(self):   # SDD-PJ-01
        self.run_cli('import', '--write')
        self.run_cli('sync', '--write')
        data = self.record('company')
        data['repositories'][0]['git']['tier'] = 4
        data['repositories'][0]['layout'] = 'domains'   # the layout of the record gives the registry field spec=
        data['repositories'][0]['work']['check'] = 'make check'
        (self.projects / 'company.json').write_text(json.dumps(data))
        self.run_cli('sync', '--check', expected=1)
        self.run_cli('sync', '--write')
        tier = self.tier('company')
        self.assertEqual((tier['tier'], tier['spec']), ('4', 'domains'))
        self.assertIn("export DEV_PLATFORM_CHECK='make check'", (self.tmp / 'env.d/company.sh').read_text())
        shown = self.run_cli('show', str(self.tmp / 'company')).stdout
        self.assertIn('tier=4', shown)
        self.assertIn('"check": "make check"', shown)

    def test_a_ghost_project_keeps_its_tasks_in_the_side_folder(self):   # SDD-PJ-10
        self.run_cli('import', '--write')
        data = self.record('company')
        data['repositories'][0]['work']['tracker'] = 'side'
        (self.projects / 'company.json').write_text(json.dumps(data))
        self.assertIn('work.tracker is side, so the repository needs spec_root', self.run_cli('sync', expected=1).stderr)
        side = self.tmp / 'rig'
        sh(self.tmp, 'git', 'init', '-q', str(side))
        data['repositories'][0]['spec_root'] = str(side)
        (self.projects / 'company.json').write_text(json.dumps(data))
        self.run_cli('sync', '--write')
        tier = self.tier('company')
        self.assertEqual((tier['tracker'], tier['side']), ('side', str(side)))

    def test_sync_refuses_a_wrong_record_and_a_line_with_no_record(self):   # SDD-PJ-01
        self.assertIn('has no record with Git settings', self.run_cli('sync', expected=1).stderr)
        self.run_cli('import', '--write')
        data = self.record('own')
        data['repositories'][0]['git']['tier'] = 9
        (self.projects / 'own.json').write_text(json.dumps(data))
        self.assertIn('unknown or invalid field: tier=9', self.run_cli('sync', expected=1).stderr)
        data['repositories'][0]['git'] = {'tier': 2, 'mode': 'local', 'colour': 'red'}
        (self.projects / 'own.json').write_text(json.dumps(data))
        self.assertIn('git.colour is unknown', self.run_cli('sync', expected=1).stderr)
        shutil.copy(self.projects / 'company.json', self.projects / 'second.json')
        (self.projects / 'own.json').write_text(json.dumps(self.record('domains') | {'name': 'own'}))
        self.assertIn('is in two records', self.run_cli('sync', expected=1).stderr)
        self.assertEqual(self.conf.read_text().splitlines()[0], '# a note of the owner')   # nothing was written

    def test_an_environment_file_that_is_no_list_of_exports_stays_as_it_is(self):   # SDD-PJ-01
        (self.tmp / 'env.d/company.sh').write_text('export PATH="$HOME/.bun/bin:$PATH"\nsource ~/.secrets\n')
        done = self.run_cli('import', '--write')
        self.assertIn('is not `export NAME=value`', done.stdout)
        self.assertNotIn('check_path', self.record('company')['repositories'][0]['work'])
        self.run_cli('sync', '--write')
        self.assertIn('source ~/.secrets', (self.tmp / 'env.d/company.sh').read_text())

    def test_the_compiler_reads_a_record_that_holds_the_git_and_work_settings(self):   # SDD-PJ-01
        self.run_cli('import', '--write')
        done = subprocess.run([sys.executable, '-I', str(SPEC), 'check', 'own'], env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_the_stop_check_runs_the_check_command_of_the_record(self):   # SDD-PJ-01
        self.run_cli('import', '--write')
        data = self.record('own')
        data['repositories'][0]['work']['check'] = 'echo the check of the record'
        (self.projects / 'own.json').write_text(json.dumps(data))
        self.run_cli('sync', '--write')
        env = dict(self.env, DEV_PLATFORM_CHECK='false')   # a variable of the session does not state the check
        done = subprocess.run(['bash', str(HOOK)], cwd=self.tmp / 'own', env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('the check of the record', done.stdout + done.stderr)
        done = subprocess.run(['bash', str(HOOK)], cwd=self.tmp / 'domains', env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)   # no command in the record and no check in the repository
        self.assertIn('refusing to record a pass', done.stderr)


class Parts(Fixture):
    """A record states the parts of the platform that are on; a part that is off does not act (SDD-PJ-03, SDD-PJ-04)."""

    def setUp(self):
        super().setUp()
        self.run_cli('import', '--write')
        self.run_cli('sync', '--write')
        (self.tmp / 'gitconfig').write_text(f'[core]\n\thooksPath = {ROOT / "hooks/git"}\n[user]\n\tname = t\n\temail = t@example.invalid\n')
        self.env['GIT_CONFIG_GLOBAL'] = str(self.tmp / 'gitconfig')

    def parts(self, name, *on):
        data = self.record(name)
        data['parts'] = list(on)
        (self.projects / f'{name}.json').write_text(json.dumps(data))
        self.run_cli('sync', '--write')

    def commit(self, name, message):
        repo = self.tmp / name
        (repo / 'a.txt').write_text(message + '\n')
        sh(repo, 'git', 'add', '-A')
        return subprocess.run(['git', 'commit', '-q', '-m', message], cwd=repo, env=self.env, capture_output=True, text=True)

    def guard(self, name, command):
        done = subprocess.run([sys.executable, '-I', str(ROOT / 'hooks/guard_git.py'), '--cwd', str(self.tmp / name)], input=command,
                              env=self.env, capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def test_a_record_with_no_list_has_each_part_on(self):   # SDD-PJ-03
        self.assertEqual(self.tier('company')['off'], '')
        self.assertNotIn('off=', self.conf.read_text())
        self.assertIn('each part', self.run_cli('show', str(self.tmp / 'company')).stdout)

    def test_the_git_rules_that_are_off_refuse_nothing(self):   # SDD-PJ-04
        attributed = 'feat: change\n\nCo-Authored-By: Claude <noreply@anthropic.com>'
        done = self.commit('company', attributed)   # tier 3 with the Git rules on: no attribution
        self.assertEqual(done.returncode, 1)
        self.assertIn('no tool or model attribution', done.stderr)
        self.assertEqual(self.guard('company', 'git push --no-verify origin main')[0], 2)
        self.parts('company', 'check', 'tree', 'loop', 'team')
        self.assertEqual(self.tier('company')['off'], 'git')
        self.assertEqual(self.commit('company', attributed).returncode, 0)
        self.assertEqual(self.guard('company', 'git push --no-verify origin main'), (0, ''))
        self.assertEqual(self.guard('company', 'gh pr merge 5')[0], 0)
        # The rules that protect the hooks of the platform are no rules of the project: they stay.
        self.assertEqual(self.guard('company', 'git config core.hooksPath /tmp/x')[0], 2)
        self.assertEqual(self.guard('own', 'git push --no-verify origin main')[0], 2)   # a second project is not changed

    def test_the_full_check_that_is_off_does_not_run_at_a_stop(self):   # SDD-PJ-04
        repo = self.tmp / 'own'
        (repo / 'bin').mkdir()
        (repo / 'bin/check').write_text('#!/bin/sh\nexit 1\n')
        (repo / 'bin/check').chmod(0o755)
        (repo / 'a.txt').write_text('a change that is not committed\n')   # a clean tree with nothing to push runs no check
        stop = lambda: subprocess.run(['bash', str(ROOT / 'hooks/stop-check.sh')], cwd=repo, env=self.env, input='', capture_output=True, text=True)
        self.assertEqual(stop().returncode, 2)   # the check fails and blocks the stop
        self.parts('own', 'git', 'tree', 'loop', 'team')
        done = stop()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('the full check is off for this project', done.stdout)

    def test_the_tree_the_loop_and_the_team_that_are_off_do_not_act(self):   # SDD-PJ-04
        self.parts('own', 'git', 'check')
        self.assertEqual(self.tier('own')['off'], 'tree,loop,team')
        done = subprocess.run([sys.executable, '-I', str(SPEC), 'compile', 'own'], env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn('the tree is off for the project own', done.stderr)
        loop = ROOT / 'skills/loop/scripts/loop.sh'
        env = dict(self.env, LOOP_STATE_DIR=str(self.tmp / 'loop'))
        done = subprocess.run(['bash', str(loop), 'start', 'me/own', 'feat/x'], env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn('the loop is off for me/own', done.stderr)
        done = subprocess.run(['bash', str(loop), 'tier', 'me/own'], env=env, capture_output=True, text=True)
        self.assertIn('off=tree,loop,team', done.stdout)
        done = subprocess.run([sys.executable, str(ROOT / 'bin/dev-workspace'), 'plan', 'claude', '--cwd', str(self.tmp / 'own')],
                              env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn('the team is off for this project', done.stderr)

    def test_the_list_of_parts_turns_the_control_of_the_specification_on(self):   # SDD-PJ-03
        sys.path.insert(0, str(ROOT / 'lib'))
        from ai_ecosystem import spectree
        os.environ['DEV_PLATFORM_PROJECTS'] = str(self.projects)
        self.addCleanup(os.environ.pop, 'DEV_PLATFORM_PROJECTS', None)
        load = lambda: spectree.load_config(self.projects / 'own.json')
        self.assertEqual((load()['control'], load()['parts']), (False, None))
        self.parts('own', 'git', 'check', 'tree', 'control')
        self.assertTrue(load()['control'])
        self.parts('own', 'git', 'check', 'tree')
        self.assertFalse(load()['control'])
        data = self.record('own')
        data['parts'] = ['git', 'colour']
        (self.projects / 'own.json').write_text(json.dumps(data))
        self.assertIn('parts is a list of: git, check, tree, control, loop, team', self.run_cli('sync', expected=1).stderr)


if __name__ == '__main__':
    unittest.main()
