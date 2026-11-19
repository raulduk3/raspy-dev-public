"""The API rig: spend against the caps, quiet holds, the check and deploy gates, seat cadence,
and the key's boundary. Offline: a fake `rig` and a fake loop record what they are asked."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import apirig  # noqa: E402

DAY = 86400
SPEC = '''version: "0.2"
name: engineer-sample
pods:
  - id: control
    label: Control
    members:
      - id: lead
        label: Coding control
        agent_ref: "path:/x/agents/control"
        profile: default
        runtime: pi
        model: "openrouter/deepseek/deepseek-v4-pro-0813:high"
        cwd: "."
    edges: []
  - id: review
    label: Review
    members:
      - id: overseer
        label: Overseer
        agent_ref: "path:/x/agents/overseer"
        profile: default
        runtime: pi
        model: "openrouter/anthropic/claude-fable-5.1:max"
        cwd: "."
    edges: []
edges: []
'''


class ApiRig(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.checkout = self.base / 'sample'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.checkout)], check=True)
        (self.base / 'repos.conf').write_text(f'owner/sample {self.checkout} local main\n')
        self.folder = self.base / 'eng/sample'
        self.folder.mkdir(parents=True)
        (self.folder / 'project').write_text('owner/sample\n')
        (self.folder / 'rig.yaml').write_text(SPEC)
        (self.folder / 'api-rig.json').write_text(json.dumps({'caps': {'day_usd': 10, 'month_usd': 100}, 'seat_wait': 0,
                                                              'openrig_home': str(self.base / 'openrig')}))
        self.calls = self.base / 'calls.jsonl'
        fake = self.base / 'fake'
        fake.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                        'with open(os.environ["CALLS"], "a") as f:\n'
                        '    f.write(json.dumps({"argv": sys.argv[1:], "key": "OPENROUTER_API_KEY" in os.environ}) + "\\n")\n'
                        'print(os.environ.get("FAKE_OUT", "[]"))\n')
        fake.chmod(0o755)
        self.usage = self.base / 'usage.json'
        self.now = time.time()
        self.env = {**os.environ, 'HOME': str(self.base / 'home'), 'DEV_PLATFORM_REPOS': str(self.base / 'repos.conf'),
                    'DEV_PLATFORM_TEAMS': str(self.base / 'eng'), 'LOOP_STATE_DIR': str(self.base / 'loop'),
                    'OL_CHAT': str(self.base / 'chat'), 'API_RIG_USAGE_REFRESH': '', 'API_RIG_USAGE_FILE': str(self.usage),
                    'API_RIG_LOOP': str(fake), 'API_RIG_RIG': str(fake), 'CALLS': str(self.calls),
                    'GIT_CONFIG_GLOBAL': os.devnull, 'OPENROUTER_API_KEY': 'not-a-real-key-123'}
        os.environ['DEV_PLATFORM_REPOS'] = self.env['DEV_PLATFORM_REPOS']
        os.environ['DEV_PLATFORM_TEAMS'] = self.env['DEV_PLATFORM_TEAMS']
        self.addCleanup(os.environ.pop, 'DEV_PLATFORM_REPOS', None)
        self.addCleanup(os.environ.pop, 'DEV_PLATFORM_TEAMS', None)

    def rig(self, now=None):
        project = apirig.resolve('owner/sample', self.base / 'repos.conf')
        return apirig.Rig(project, env=self.env, clock=lambda: now or self.now)

    def reading(self, used, captured=None, **extra):
        self.usage.write_text(json.dumps({'credits': {'used': used, **extra}, 'captured': captured or self.now}))

    def recorded(self):
        return [json.loads(l) for l in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def chat(self):
        return (self.base / 'chat').read_text() if (self.base / 'chat').exists() else ''

    # spend ---------------------------------------------------------------------------------

    def test_openrouter_daily_and_monthly_figures_win(self):
        state = {}
        self.assertEqual(apirig.spend(state, {'credits': {'used': 50, 'daily': 3.5, 'monthly': 41}, 'captured': self.now},
                                      self.now), (3.5, 41.0))

    def test_without_them_spend_is_the_difference_since_the_window_began(self):
        day_start, _ = apirig.windows(self.now)
        state = {'spend': [[day_start - 3600, 20.0]]}
        day, month = apirig.spend(state, {'credits': {'used': 26.0}, 'captured': self.now}, self.now)
        self.assertEqual(day, 6.0)
        self.assertGreaterEqual(month, 6.0)

    def test_no_reading_or_an_old_one_is_unknown_never_zero(self):
        self.assertIsNone(apirig.spend({}, None, self.now))
        self.assertIsNone(apirig.spend({}, {'credits': {'used': 1}, 'captured': self.now - 3600}, self.now))

    def test_the_daily_cap_stops_dispatch_and_says_so(self):
        rig = self.rig()
        state = {'spend': [[apirig.windows(self.now)[0] - 60, 0.0]]}
        self.reading(12.5)
        self.assertFalse(apirig.gate_spend(rig, state))
        self.assertEqual(state['hold']['kind'], 'cap-day')
        self.assertIn('the daily cap is reached: $12.50 of $10.00 today', self.chat())
        self.assertIn(['pause', 'owner/sample'], [c['argv'][0:2] for c in self.recorded()])
        # Still over: no second line in the room.
        self.assertFalse(apirig.gate_spend(rig, state))
        self.assertEqual(self.chat().count('daily cap'), 1)

    def test_the_monthly_cap_wins_over_the_daily_one(self):
        rig = self.rig()
        self.reading(150, daily=1, monthly=120)
        state = {}
        self.assertFalse(apirig.gate_spend(rig, state))
        self.assertEqual(state['hold']['kind'], 'cap-month')

    def test_unknown_spend_holds_and_a_soft_hold_clears_itself(self):
        rig = self.rig()
        state = {}
        self.assertFalse(apirig.gate_spend(rig, state))     # no reading at all
        self.assertEqual(state['hold']['kind'], 'spend-unknown')
        self.reading(1, daily=1, monthly=1)
        self.assertTrue(apirig.gate_spend(rig, state))
        self.assertIsNone(state['hold'])
        self.assertIn('dispatch resumes', self.chat())
        self.assertIn(['go', 'owner/sample'], [c['argv'][0:2] for c in self.recorded()])

    def test_a_hard_hold_stops_the_whole_pass(self):
        rig = self.rig()
        rig.save({'hold': {'kind': 'deploy', 'reason': 'the staging deploy failed', 'since': self.now}})
        self.reading(0, daily=0, monthly=0)
        state = apirig.tick(rig)
        self.assertEqual(state['hold']['kind'], 'deploy')
        self.assertEqual(self.recorded(), [])

    def seat_reply(self, session, message):
        folder = self.base / 'openrig/state/pi' / session
        folder.mkdir(parents=True, exist_ok=True)
        log = folder / 'session.jsonl'
        log.write_text(json.dumps({'type': 'message', 'message': {'role': 'user', 'content': 'go'}}) + '\n' +
                       json.dumps({'type': 'message', 'message': {'role': 'assistant', 'content': [],
                                                                  'timestamp': self.now * 1000, **message}}) + '\n')
        (folder / 'runner-state.json').write_text(json.dumps({'sessionFile': str(log)}))

    def test_spent_account_credits_hold_with_an_ask_and_release_settles_them(self):
        rig = self.rig()
        self.reading(5, daily=5, monthly=5, limit=250, remaining=245)   # the key's own limit has room
        self.seat_reply('review-overseer@engineer-sample', {'stopReason': 'error', 'errorMessage':
                        '402: {"message":"This request requires more credits, or fewer max_tokens."}'})
        state = apirig.tick(rig)
        self.assertEqual(state['hold']['kind'], 'credits')
        self.assertIn('out of credits', self.chat())
        self.assertIn('hold-credits', [a['key'] for a in rig.ledger.open()])
        self.assertIn(['pause', 'owner/sample'], [c['argv'][0:2] for c in self.recorded()])
        # The owner adds credits and releases: the old refusal no longer holds the rig.
        later = self.rig(now=self.now + 60)
        subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, sys.argv[1]); from ai_ecosystem import apirig; '
                        'apirig.main(["release", "owner/sample"])', str(ROOT / 'lib')], env=self.env, check=True,
                       capture_output=True)
        self.assertIsNone(apirig.refusal(later, later.load()['released_at']))

    def test_a_refused_key_holds_and_an_ordinary_error_does_not(self):
        rig = self.rig()
        self.seat_reply('control-lead@engineer-sample', {'stopReason': 'error', 'errorMessage': '401: invalid key'})
        self.assertEqual(apirig.refusal(rig)[0], 'key')
        self.seat_reply('control-lead@engineer-sample', {'stopReason': 'error', 'errorMessage': '429: rate limited'})
        self.assertIsNone(apirig.refusal(rig))

    # the gates -----------------------------------------------------------------------------

    def worktree(self, check_exit):
        wt = self.base / 'wt'
        subprocess.run(['git', 'init', '-q', str(wt)], check=True)
        (wt / 'bin').mkdir()
        (wt / 'bin/check').write_text(f'#!/bin/sh\necho checking\nexit {check_exit}\n')
        (wt / 'bin/check').chmod(0o755)
        subprocess.run(['git', '-C', str(wt), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(wt), '-c', 'user.name=t', '-c', 'user.email=t@x', 'commit', '-qm', 'x'], check=True)
        (wt / '.worker-pr.md').write_text('## What changed and why\n')
        (wt / '.worker-brief.md').write_text('# Worker brief: issue #4\n')
        return wt

    def test_a_failing_check_goes_back_to_its_worker_and_a_second_one_holds(self):
        rig = self.rig()
        wt = self.worktree(1)
        facts = {'workers': [{'issue': 4, 'branch': 'fix/x-4', 'worktree': str(wt), 'state': 'ready for review'}]}
        state = {}
        self.assertTrue(apirig.gate_workers(rig, state, facts))
        self.assertIn('## The check failed', (wt / '.worker-brief.md').read_text())
        self.assertIn(['resume', 'owner/sample', '4'], [c['argv'][0:3] for c in self.recorded()])
        self.assertFalse((wt / '.worker-pr.md').exists())
        # The worker answers with a new head that still fails.
        (wt / 'note').write_text('x')
        subprocess.run(['git', '-C', str(wt), 'add', 'note'], check=True)
        subprocess.run(['git', '-C', str(wt), '-c', 'user.name=t', '-c', 'user.email=t@x', 'commit', '-qm', 'y'], check=True)
        (wt / '.worker-pr.md').write_text('again\n')
        self.assertFalse(apirig.gate_workers(rig, state, facts))
        self.assertEqual(state['hold']['kind'], 'check')
        self.assertIn('the check failed twice on #4', self.chat())

    def test_a_passing_check_goes_to_the_control_seat_once_per_interval(self):
        rig = self.rig()
        wt = self.worktree(0)
        facts = {'workers': [{'issue': 4, 'branch': 'fix/x-4', 'worktree': str(wt), 'state': 'ready for review'}]}
        state = {}
        apirig.gate_workers(rig, state, facts)
        apirig.gate_workers(rig, state, facts)
        apirig.gate_workers(rig, state, facts)
        sends = [c['argv'] for c in self.recorded() if c['argv'][:1] == ['send']]
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0][1], 'control-lead@engineer-sample')
        self.assertIn('Review #4', sends[0][2])

    def test_a_failed_deploy_holds_once_and_other_steps_ask_for_fix_tasks(self):
        rig = self.rig()
        wt = self.worktree(0)
        head = apirig.head_of(wt)
        facts = {'rig': 'feat/x', 'worktree': str(wt), 'folded': [1], 'workers': [], 'mode': 'local'}
        rig.path('api-rig-steps.jsonl').write_text(json.dumps(
            {'step': 'deploy', 'head': head, 'tag': 'staging-1', 'ok': False, 'code': 1, 'tail': 'boom'}) + '\n')
        state = {}
        apirig.drive_steps(rig, state, facts)
        self.assertEqual(state['hold']['kind'], 'deploy')
        self.assertIn('the staging deploy of staging-1 failed', self.chat())

    def test_steps_wait_for_the_plan_and_end_in_the_merge_request(self):
        rig = self.rig()
        wt = self.worktree(0)
        head = apirig.head_of(wt)
        facts = {'rig': 'feat/x', 'worktree': str(wt), 'folded': [1], 'workers': [], 'mode': 'local'}
        state = {}
        apirig.drive_steps(rig, state, facts, ready=1)
        self.assertEqual(self.recorded(), [])               # a ready task: no deploy yet
        apirig.drive_steps(rig, state, facts)
        self.assertIn('api-rig step owner/sample deploy', self.recorded()[-1]['argv'][2])
        with rig.path('api-rig-steps.jsonl').open('a') as log:
            for step in apirig.STEPS:
                log.write(json.dumps({'step': step, 'head': head, 'tag': 'staging-1', 'ok': True}) + '\n')
        apirig.drive_steps(rig, state, facts)
        self.assertEqual(state['green'], head)
        self.assertIn(['close', 'owner/sample'], [c['argv'][0:2] for c in self.recorded()])
        self.assertIn('merge request ready', self.chat())
        self.assertIn('dev-loop close owner/sample --merge', self.chat())

    def test_step_runs_the_helper_tags_the_head_and_records_it(self):
        wt = self.worktree(0)
        config = json.loads((self.folder / 'api-rig.json').read_text())
        config['steps'] = {'deploy': ['sh', '-c', 'echo "deploying $API_RIG_TAG"; test -z "$OPENROUTER_API_KEY"']}
        (self.folder / 'api-rig.json').write_text(json.dumps(config))
        self.env['FAKE_OUT'] = json.dumps({'rig': 'feat/x', 'worktree': str(wt)})
        record = apirig.step(self.rig(), 'deploy')
        self.assertTrue(record['ok'], record)
        self.assertEqual(record['tag'], 'staging-1')
        self.assertIn('deploying staging-1', record['tail'])
        tags = subprocess.run(['git', '-C', str(wt), 'tag'], capture_output=True, text=True).stdout.split()
        self.assertEqual(tags, ['staging-1'])
        self.assertEqual(apirig.step(self.rig(), 'deploy')['tag'], 'staging-2')
        self.assertTrue(apirig.step(self.rig(), 'runner')['tail'].startswith('skipped'))

    # seats ---------------------------------------------------------------------------------

    def seat_session(self, rig, session, turns, context, age=60):
        folder = rig.openrig_home / 'state/pi' / session
        folder.mkdir(parents=True)
        file = folder / 'session.jsonl'
        lines = [json.dumps({'type': 'session'})]
        for _ in range(turns):
            lines.append(json.dumps({'type': 'message', 'message': {'role': 'user', 'content': 'x'}}))
            lines.append(json.dumps({'type': 'message', 'message': {'role': 'assistant', 'stopReason': 'stop',
                                                                    'usage': {'totalTokens': context}}}))
        file.write_text('\n'.join(lines) + '\n')
        os.utime(file, (self.now - age, self.now - age))
        (folder / 'runner-state.json').write_text(json.dumps({'ready': True, 'sessionFile': str(file)}))

    def test_a_seat_past_its_cadence_checkpoints_then_re_opens_fresh(self):
        rig = self.rig()
        self.seat_session(rig, 'control-lead@engineer-sample', turns=21, context=1000)
        self.seat_session(rig, 'review-overseer@engineer-sample', turns=2, context=1000)
        state = {'rig_id': 'RIG1', 'folded': []}
        apirig.rotate(rig, state)
        sends = [c['argv'] for c in self.recorded() if c['argv'][:1] == ['send']]
        self.assertEqual([s[1] for s in sends], ['control-lead@engineer-sample'])
        self.assertIn('Checkpoint now: write', sends[0][2])
        self.assertIn('21 turns', state['seats']['lead']['why'])
        # The seat writes its checkpoint; the next pass re-opens it from the same member.
        rig.checkpoint('lead').write_text('# state\n')
        os.utime(rig.checkpoint('lead'), (self.now + 1, self.now + 1))
        apirig.rotate(rig, state)
        argv = [c['argv'] for c in self.recorded()]
        self.assertIn(['remove', 'RIG1', 'control.lead'], argv)
        add = next(a for a in argv if a[0] == 'add')
        self.assertEqual(add[1:3], ['RIG1', 'control'])
        fragment = Path(add[3]).read_text()
        self.assertIn('runtime: pi', fragment)
        self.assertIn(f'cwd: "{rig.folder}"', fragment)
        self.assertIn('re-opened on a fresh context', argv[-1][2])
        self.assertIsNone(state['seats']['lead']['asked'])
        settings = json.loads((rig.openrig_home / 'state/pi/control-lead@engineer-sample/agent/settings.json').read_text())
        self.assertTrue(any(e.endswith('seat-guard.mjs') for e in settings['extensions']))

    def test_a_fresh_team_takes_the_fold_count_as_its_baseline(self):
        rig = self.rig()
        self.seat_session(rig, 'control-lead@engineer-sample', turns=1, context=1000)
        state = {'rig_id': 'RIG1', 'folded': list(range(418)),
                 'seats': {'lead': {'opened': 0, 'folds': None, 'asked': None, 'asks': 0}}}
        apirig.rotate(rig, state)
        self.assertEqual([c for c in self.recorded() if c['argv'][:1] == ['send']], [])
        self.assertEqual(state['seats']['lead']['folds'], 418)
        state['folded'].append(999)
        apirig.rotate(rig, state)
        self.assertIn('1 fold(s)', state['seats']['lead']['why'])

    def test_a_fold_re_opens_the_seats_and_a_large_context_does_too(self):
        rig = self.rig()
        self.seat_session(rig, 'control-lead@engineer-sample', turns=1, context=1000)
        self.seat_session(rig, 'review-overseer@engineer-sample', turns=1, context=400000)
        state = {'rig_id': 'RIG1', 'folded': [3], 'seats': {'lead': {'opened': 0, 'folds': 0, 'asked': None, 'asks': 0}}}
        apirig.rotate(rig, state)
        self.assertIn('1 fold(s)', state['seats']['lead']['why'])
        self.assertIn('400000-token context', state['seats']['overseer']['why'])

    def test_a_busy_seat_is_not_interrupted(self):
        rig = self.rig()
        self.seat_session(rig, 'control-lead@engineer-sample', turns=25, context=1000, age=2)
        state = {'rig_id': 'RIG1', 'folded': []}
        apirig.rotate(rig, state)
        self.assertEqual([c for c in self.recorded() if c['argv'][:1] == ['send']], [])

    # the owner's governance ---------------------------------------------------------------------

    def test_a_record_goes_to_distill(self):
        rig = self.rig()
        box = self.folder / 'inbox'
        box.mkdir(parents=True)
        (box / 'insurer-letter.txt').write_text('The insurer requires ...\n')
        (box / '.hidden').write_text('x')
        apirig.inbox(rig, {})
        sends = [c['argv'] for c in self.recorded() if c['argv'][:1] == ['send']]
        self.assertEqual(len(sends), 1)
        self.assertIn('Distill it with the distill skill', sends[0][2])
        self.assertIn('insurer-letter.txt', sends[0][2])
        self.assertFalse((box / 'insurer-letter.txt').exists())
        self.assertEqual(len(list((box / 'sent').iterdir())), 1)
        self.assertTrue((box / '.hidden').exists())
        self.assertIn('distilling insurer-letter.txt', self.chat())
        apirig.inbox(rig, {})
        self.assertEqual(len([c for c in self.recorded() if c['argv'][:1] == ['send']]), 1)

    def test_the_room_hears_once_which_decision_holds_which_tasks(self):
        self.env['FAKE_OUT'] = '#4 waits (decision 0007 is proposed) Refunds\n#5 waits (decision 0007 is proposed) Refund mail\n#6 ready Other'
        rig = self.rig()
        state = {}
        apirig.waiting_on_owner(rig, state)
        apirig.waiting_on_owner(rig, state)
        self.assertEqual(self.chat().count('waiting on the owner: decision 0007 is proposed (holds #4, #5)'), 1)
        self.assertEqual(state['waiting'], {'decision 0007 is proposed': ['#4', '#5']})

    def test_governed_labels_reach_the_loop(self):
        self.rig().loop('status')
        env_seen = self.base / 'env-seen'
        fake = Path(self.env['API_RIG_LOOP'])
        fake.write_text(fake.read_text() + f'open({str(env_seen)!r}, "w").write(os.environ.get("LOOP_GOVERNED_LABELS", ""))\n')
        self.rig().loop('status')
        self.assertEqual(env_seen.read_text(), 'legal,insurance,privacy,payments,policy')

    def test_asks_from_decisions_and_holds_and_answers_from_dev_server(self):
        self.env['FAKE_OUT'] = '#4 waits (decision 0007 is proposed) Refunds\n'
        rig = self.rig()
        state = {}
        apirig.waiting_on_owner(rig, state)
        apirig.waiting_on_owner(rig, state)
        asks = rig.ledger.open()
        self.assertEqual(len(asks), 1)
        self.assertEqual((asks[0]['id'], asks[0]['kind'], asks[0]['unblocks']), ('A1', 'decision', '#4'))
        self.assertIn('Decision 0007 is proposed. Accept it, change it, or reject it?', asks[0]['question'])
        apirig.hold(rig, state, 'check', 'the check failed twice on #4')
        self.assertEqual([a['kind'] for a in rig.ledger.open()], ['decision', 'hold'])
        result = apirig.answered(rig, state, 'A1', 'Accept it, 30 days is right.', 'the owner on dev-server')
        self.assertEqual(result, 'answered A1')
        record = rig.path('answers/A1.md').read_text()
        self.assertIn('Answer: Accept it, 30 days is right.', record)
        self.assertIn('set its Status to accepted', record)
        self.assertIn('The owner answered A1', [c['argv'] for c in self.recorded() if c['argv'][:1] == ['send']][-1][2])
        self.assertIn('not taken', apirig.answered(rig, state, 'A1', 'again', 'x'))
        # The decision accepted on the base: its ask is withdrawn on the next pass.
        self.env['FAKE_OUT'] = ''
        rig.ledger.ask('Decision 0008 is proposed.', kind='decision', key='decision-0008')
        apirig.waiting_on_owner(self.rig(), state)
        self.assertEqual([a['kind'] for a in self.rig().ledger.open()], ['hold'])

    def test_the_answer_command_and_the_ask_command(self):
        def cli(*argv):
            out = subprocess.run([str(ROOT / 'bin/api-rig'), *argv], capture_output=True, text=True, env=self.env)
            return out.returncode, out.stdout + out.stderr
        code, out = cli('ask', 'owner/sample', 'Which', 'insurer', 'covers', 'electrical', 'work?', '--kind', 'owner-owed',
                        '--unblocks', 'the insurance page', '--option', 'Alpha', '--option', 'Beta')
        self.assertEqual((code, out.strip()), (0, 'A1: asked'))
        self.assertIn('A1 open (owner-owed): Which insurer covers electrical work?', cli('asks', 'owner/sample')[1])
        code, out = cli('answer', 'owner/sample', 'a1', 'Beta,', 'policy', 'number', 'to', 'follow')
        self.assertEqual((code, out.strip()), (0, 'answered A1'))
        self.assertEqual(cli('asks', 'owner/sample')[1].strip(), 'no open asks')
        self.assertIn('answer (the owner on dev-server): Beta, policy number to follow', cli('asks', 'owner/sample', '--all')[1])
        self.assertEqual(cli('answer', 'owner/sample', 'A9', 'x')[0], 2)

    # the key ---------------------------------------------------------------------------------

    def test_the_key_reaches_only_the_daemon_and_the_headless_workers(self):
        rig = self.rig()
        self.assertNotIn('OPENROUTER_API_KEY', rig.base_env())
        rig.rig('ps')
        rig.rig('daemon', 'start', key=True)
        rig.loop('status')
        calls = self.recorded()
        self.assertEqual([c['key'] for c in calls], [False, True, True])
        config = json.loads((self.folder / 'api-rig.json').read_text())
        config['workers'] = {'mode': 'seat'}
        (self.folder / 'api-rig.json').write_text(json.dumps(config))
        self.rig().loop('status')
        self.assertFalse(self.recorded()[-1]['key'])

    def test_the_key_comes_from_the_unit_credential(self):
        creds = self.base / 'creds'
        creds.mkdir()
        (creds / 'openrouter').write_text('from-the-credential\n')
        env = {k: v for k, v in self.env.items() if k != 'OPENROUTER_API_KEY'}
        env['CREDENTIALS_DIRECTORY'] = str(creds)
        rig = apirig.Rig(apirig.resolve('owner/sample', self.base / 'repos.conf'), env=env)
        self.assertEqual(rig.key, 'from-the-credential')
        self.assertNotIn('CREDENTIALS_DIRECTORY', rig.base_env())

    def test_the_unit_loads_the_key_as_a_credential_and_names_no_key(self):
        text = apirig.unit_text(user='owner', home='/home/owner')
        self.assertIn('LoadCredential=openrouter:/etc/dev-server/accounts/openrouter.key', text)
        self.assertIn('Environment=OL_PORTAL=unit', text)
        self.assertIn('ExecStart=', text)
        self.assertNotIn('OPENROUTER_API_KEY', text)

    def test_the_engagement_name_finds_the_project(self):
        self.assertEqual(apirig.resolve('sample', self.base / 'repos.conf')['repo'], 'owner/sample')
        with self.assertRaises(apirig.Refused):
            apirig.resolve('nothing-here', self.base / 'repos.conf')

    def test_switch_plans_the_shape_and_the_unit_both_ways(self):
        project = apirig.resolve('owner/sample', self.base / 'repos.conf')
        to_api = [' '.join(c) for c in apirig.switch(project, 'api', dry_run=True)]
        self.assertTrue(to_api[0].endswith('write owner/sample review --all pi'))
        self.assertIn('sudo systemctl enable --now api-rig@sample.service', to_api)
        back = [' '.join(c) for c in apirig.switch(project, 'subscription', dry_run=True)]
        self.assertEqual(back[0], 'sudo systemctl disable --now api-rig@sample.service')
        self.assertTrue(back[1].endswith('write owner/sample build'))


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class SeatExtensions(unittest.TestCase):
    def test_guard_advice_and_worker_limits(self):
        env = {**os.environ, 'DEV_PLATFORM_PSTACK_SYSTEM': '/nonexistent', 'DEV_PLATFORM_PSTACK_MODELS': '/nonexistent'}
        env.pop('OPENROUTER_API_KEY', None)
        result = subprocess.run(['node', str(ROOT / 'integrations/pi/check-seat-extensions.mjs')],
                                capture_output=True, text=True, env=env, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('seat extensions ok', result.stdout)


if __name__ == '__main__':
    unittest.main()


class FakeTalk:
    """Nextcloud Talk's chat API, in memory: the rig is user `rig`, the owner `owner`, the company agent `acme`."""

    def __init__(self):
        self.messages = []

    def add(self, actor, message, parent=None):
        item = {'id': len(self.messages) + 100, 'actorType': 'users', 'actorId': actor, 'message': message}
        if parent:
            item['parent'] = {'id': parent}
        self.messages.append(item)
        return item['id']

    def __call__(self, request, timeout=None):
        import io
        from urllib.parse import parse_qs, urlparse
        assert request.get_header('Authorization', '').startswith('Basic ')
        assert request.get_header('Ocs-apirequest') == 'true'
        url = urlparse(request.full_url)
        if request.get_method() == 'POST':
            body = json.loads(request.data)
            data = {'id': self.add('rig', body['message'], body.get('replyTo'))}
        else:
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            last = int(q['lastKnownMessageId'])
            data = [m for m in self.messages if m['id'] > last] if q['lookIntoFuture'] == '1' else \
                [m for m in self.messages if m['id'] < last][-int(q['limit']):]

        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return Response(json.dumps({'ocs': {'data': data}}).encode())


class TalkSync(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        from ai_ecosystem import rigasks
        self.rigasks = rigasks
        self.room = FakeTalk()
        self.ledger = rigasks.Ledger(self.base / 'asks.json')
        self.talk = rigasks.Talk('https://cloud.example.invalid', 'roomtoken', 'rig:app-pass', opener=self.room)
        self.answers, self.records = [], []

    def sync(self):
        return self.rigasks.sync_talk(self.talk, self.ledger, self.base / 'talk.json', {'owner'}, {'office'}, 'acme',
                                      lambda i, w, b: self.answers.append((i, w, b)) or f'answered {i}',
                                      lambda t, b: self.records.append((t, b)) or 'record')

    def test_asks_are_posted_once_and_the_owners_reply_answers(self):
        self.room.add('owner', 'A1 an old message before the rig joined')
        first, _ = self.ledger.ask('Accept decision 0007?', kind='decision', key='decision-0007', unblocks='#4')
        self.ledger.ask('Which opening day?', kind='owner-owed')
        self.assertEqual(self.sync(), ['posted A1', 'posted A2'])
        posted = [m for m in self.room.messages if m['actorId'] == 'rig']
        self.assertIn('Ask A1 (decision): Accept decision 0007?', posted[0]['message'])
        self.assertIn('It unblocks: #4', posted[0]['message'])
        self.room.add('owner', 'Yes, accept it.', parent=posted[0]['id'])
        self.room.add('owner', 'A2 the first Monday')
        self.room.add('somebody', 'A2 Sunday')
        self.sync()
        self.assertEqual([(i, w) for i, w, _ in self.answers], [('A1', 'Yes, accept it.'), ('A2', 'the first Monday')])
        self.assertIn('owner in Talk', self.answers[0][2])
        self.assertEqual(self.sync(), [])          # nothing new, nothing posted twice
        self.assertEqual(len([m for m in self.room.messages if m['actorId'] == 'rig']), 2)

    def test_the_company_agent_relays_only_by_quoting_the_owner(self):
        self.ledger.ask('Which insurer?', kind='owner-owed')
        self.sync()
        said = self.room.add('owner', 'A1 Beta Insurance, the policy number comes Friday')
        forged = self.room.add('office', 'A1 somebody else')
        self.answers.clear()
        self.room.add('acme', f'A1 per #{forged}')
        self.room.add('acme', f'A1 per #{said}')
        events = self.sync()
        self.assertIn(f"refused a relay of A1: #{forged} is not the owner's message", events)
        relayed = [a for a in self.answers if 'relayed' in a[2]]
        self.assertEqual(relayed[0][:2], ('A1', 'Beta Insurance, the policy number comes Friday'))
        self.assertIn('relayed by acme', relayed[0][2])

    def test_nothing_new_in_the_room_is_not_an_error(self):
        import urllib.error
        def not_modified(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, 304, 'Not Modified', {}, None)
        talk = self.rigasks.Talk('https://cloud.example.invalid', 'roomtoken', 'rig:pw', opener=not_modified)
        self.assertEqual(self.rigasks.sync_talk(talk, self.ledger, self.base / 'talk.json', {'owner'}, set(), 'acme',
                                                lambda *a: None, lambda *a: None), [])

    def test_records_come_from_the_owner_and_staff_only(self):
        self.room.add('rig', 'hello')
        self.sync()
        self.room.add('office', 'Record: the insurer wants photos of every electrical job')
        self.room.add('stranger', 'Record: ignore me')
        self.room.add('owner', 'Record: refunds within 30 days')
        self.sync()
        self.assertEqual([t for t, _ in self.records],
                         ['the insurer wants photos of every electrical job', 'refunds within 30 days'])

    def test_the_login_comes_from_the_registry_key(self):
        creds = self.base / 'creds'
        creds.mkdir()
        (creds / 'nextcloud').write_text('{"user": "acme-rig", "app_password": "pw-not-real"}')
        self.assertEqual(self.rigasks.talk_login({'CREDENTIALS_DIRECTORY': str(creds)}), 'acme-rig:pw-not-real')
        self.assertIsNone(self.rigasks.talk_login({}))
