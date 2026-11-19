"""api-rig: a project's team on API keys alone, running the lifecycle with nobody at the keyboard.

One supervisor per project (the unit api-rig@<engagement>, or `api-rig run` in a terminal) runs
this cycle, again and again, in the project's team folder:

  spend    OpenRouter's key usage against the daily and monthly caps; over either cap, or with
           no current reading, dispatch stops, running workers are stopped and the room is told
  team     its own OpenRig daemon (own state folder and port, the OpenRouter key in its
           environment and nowhere else) and the project's Pi team from rig.yaml
  loop     the goal's rig branch; dispatch on the steer; each finished worker's check, run here;
           a passing child goes to the control seat, which has the overseers review it and folds
  inbox    the owner's records (inbox/) go to the control seat to distill into candidates; the
           owner promotes a candidate in an intake session, which drafts decisions as proposed;
           a task waits until the owner accepts every decision it cites, and the room is told
  steps    when everything dispatched is folded: the control seat drives the staging deploy, the
           runner and the journeys through `api-rig step`, which runs the project's own helpers
           and records the result; a green head gets its merge request written (dev-loop close)
  fresh    the control and overseer seats re-open on a fresh context at the cadence (every fold,
           or N turns, or a context of N tokens), from their checkpoint files

It holds quietly, with one line in the room, when the check fails twice on a task or the
deploy fails once, and holds with an ask to the owner when OpenRouter refuses the seats (402:
the account's credits are spent; 401 or 403: the key); `api-rig release` clears it. Landing stays the owner's. See docs/api-rig.md.

State lives in the team folder: api-rig.json (the owner's settings, tracked with rig.yaml)
and .run/ (state, log, step results, the seats' checkpoints handoff-<seat>.md). No key is ever
written, logged or put in a prompt: the key comes from the unit's credential and is passed only
to the OpenRig daemon and the loop, by name.
"""
import argparse
import calendar
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import time

from . import paths, piseat, rigasks, rigshape, workspace

PLATFORM = Path(__file__).resolve().parents[2]
LOOP = PLATFORM / 'skills/loop/scripts/loop.sh'
HOOKS = PLATFORM / 'hooks'
CHAT = '/var/lib/dev-server/chat'
CREDENTIAL = 'openrouter'
KEY = 'OPENROUTER_API_KEY'
USAGE_REFRESH = ['sudo', '-n', '/usr/local/bin/ol-login-root', 'usage', '--provider', 'openrouter', '--max-age', '120']
SEATS = ('control', 'review')            # the pods whose seats re-open at the cadence
STEPS = ('deploy', 'runner', 'journeys')
SOFT = ('cap-day', 'cap-month', 'spend-unknown')   # holds that clear themselves
UNIT = '''\
# api-rig@<engagement>: one project's API rig (dev-platform docs/api-rig.md).
# Installed by `api-rig switch <project> --to api`; the owner's sudo password enables it.
[Unit]
Description=API rig for %i: Pi seats on OpenRouter, spend caps, the development lifecycle
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
Group={user}
Environment=HOME={home}
Environment=PATH=/usr/local/bin:/usr/bin
Environment=OL_PORTAL=unit
# The OpenRouter key, root's file, handed to this service alone; never in an argument or a log.
LoadCredential=openrouter:/etc/dev-server/accounts/openrouter.key
ExecStart={platform}/bin/api-rig run %i
Restart=on-failure
RestartSec=120

[Install]
WantedBy=multi-user.target
'''

DEFAULTS = {
    'version': 1,
    # The goal's rig branch: started when none is open; an open one is used as it is.
    'goal': None,
    # Dollars on the OpenRouter key; over either, dispatch stops until the window turns.
    'caps': {'day_usd': 15.0, 'month_usd': 200.0},
    # When the control and overseer seats re-open on a fresh context.
    'cadence': {'per_fold': True, 'turns': 20, 'tokens': 250000},
    # mode headless: the loop's own one-task Pi runs (any repository); seat: OpenRig worker seats
    # (personal repositories only: OpenRig writes its context into the worktree).
    # Dollars per worker run (the retry on the stronger model has its own), turns, and the turn by
    # which a run must show a change in its worktree or stop.
    'workers': {'mode': 'headless', 'cap': 2, 'max_seconds': 2700, 'max_turns': 80, 'max_tokens': 20000000,
                'max_usd': 2.0, 'retry_usd': 6.0, 'first_change_turns': 20},
    # The project's own helpers, run from the rig worktree; [] skips the step.
    'steps': {'deploy': [], 'runner': [], 'journeys': []},
    'tag_prefix': 'staging-',
    'poll_seconds': 60,
    'nudge_minutes': 30,
    'seat_wait': 120,
    'openrig_home': '~/.local/state/dev-platform/api-rig/openrig',
    'port': 7533,
    # A Pi models.json given to every seat and worker (a custom endpoint, model metadata); no key.
    'pi_models': None,
    # Task labels that may not dispatch without an accepted decision (the owner's gate).
    'governed_labels': ['legal', 'insurance', 'privacy', 'payments', 'policy'],
    # The company's Nextcloud Talk room the asks go to and answers come from, with the company agent in it:
    # {"url": "https://<nextcloud>", "room": "<token>", "host": null, "owners": ["<owner's Talk ids>"],
    #  "staff": ["<staff ids that may send records>"], "relay": "acme"}. None: answers on dev-server only.
    'talk': None,
}


class Refused(Exception):
    pass


# ---- the project and its files -------------------------------------------------------------

def merge(base, extra):
    out = dict(base)
    for key, value in (extra or {}).items():
        out[key] = merge(base[key], value) if isinstance(value, dict) and isinstance(base.get(key), dict) else value
    return out


def resolve(name, config=None):
    """A project by id, owner/repo, checkout path, or its team folder's name (the unit's %i)."""
    config = Path(config or os.environ.get('DEV_PLATFORM_REPOS', Path.home() / '.config/dev-platform/repos.conf'))
    projects = workspace.catalog(config)[0]
    try:
        return workspace.find_project(projects, name)
    except ValueError:
        marker = rigshape.teams() / name / 'project'
        if marker.is_file():
            return workspace.find_project(projects, marker.read_text().strip())
        raise Refused(f'no project or team named {name}')


class Rig:
    """One project's API rig: its files, its settings, and the commands it runs."""

    def __init__(self, project, env=None, clock=time.time):
        self.project = project
        self.repo = project['repo']
        self.folder = rigshape.team_folder(project)
        self.spec = self.folder / 'rig.yaml'
        self.run_dir = self.folder / '.run'
        self.env = dict(os.environ if env is None else env)
        self.key = self.env.pop(KEY, None) or read_credential(self.env)
        self.clock = clock
        settings = self.folder / 'api-rig.json'
        try:
            self.config = merge(DEFAULTS, json.loads(settings.read_text()) if settings.is_file() else {})
        except ValueError as error:
            raise Refused(f'{settings} is not JSON: {error}')
        self.openrig_home = Path(os.path.expanduser(self.config['openrig_home']))
        # A socket path must stay under the kernel's ~108 bytes, so not under a deep state folder.
        self.tmux_dir = Path(self.env.get('HOME', str(Path.home()))) / '.local/state/dev-platform/api-rig' / f"tmux-{self.config['port']}"

    # files
    @property
    def team(self):
        found = re.search(r'^name: (\S+)', self.spec.read_text(), re.MULTILINE) if self.spec.is_file() else None
        if not found:
            raise Refused(f'{self.repo} has no team spec; rig-shape write {self.repo} review --all pi')
        return found.group(1)

    def path(self, name):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir / name

    @property
    def ledger(self):
        return rigasks.Ledger(self.path('asks.json'), self.clock)

    def checkpoint(self, member):
        return self.path(f'handoff-{member}.md')

    @contextlib.contextmanager
    def locked(self):
        """One writer of the state at a time: a pass of the cycle, or an owner's verb."""
        with self.path('api-rig.lock').open('w') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def steps(self):
        """The latest result of each step, from the append-only step log (the control seat writes it
        while a pass may be running, so it never goes through the state file)."""
        found = {}
        try:
            for line in self.path('api-rig-steps.jsonl').read_text().splitlines():
                record = json.loads(line)
                found[record['step']] = record
        except (OSError, ValueError, KeyError):
            pass
        return found

    def load(self):
        try:
            return json.loads(self.path('api-rig-state.json').read_text())
        except (OSError, ValueError):
            return {}

    def save(self, state):
        target = self.path('api-rig-state.json')
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + '\n')
        tmp.replace(target)

    def log(self, line):
        with self.path('api-rig.log').open('a') as stream:
            stream.write(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime(self.clock())) + line + '\n')

    def room(self, words):
        """One line in the room everybody reads (the owner's chat)."""
        self.log('room: ' + words)
        try:
            with open(self.env.get('OL_CHAT', CHAT), 'a') as stream:
                stream.write(f"{time.strftime('%H:%M', time.localtime(self.clock()))} api-rig {self.repo}: {words}\n")
        except OSError:
            pass

    # commands
    def base_env(self):
        """Everything a child gets: never the key, unless it is named for it below."""
        env = {k: v for k, v in self.env.items() if k not in (KEY, 'CREDENTIALS_DIRECTORY')}
        env['OPENRIG_HOME'] = str(self.openrig_home)
        env['OPENRIG_PORT'] = str(self.config['port'])
        # Its own tmux server: a seat's pane takes its environment from the tmux server, so the
        # server must be the one this rig's daemon starts with the key. It also keeps the API
        # rig's panes apart from the owner's tmux (attach with TMUX_TMPDIR set, see the runbook).
        env['TMUX_TMPDIR'] = str(self.tmux_dir)
        env.pop('TMUX', None)
        if self.config.get('pi_models'):
            env['DEV_PLATFORM_PI_MODELS'] = os.path.expanduser(self.config['pi_models'])
        return env

    def rig(self, *args, key=False, check=False, timeout=180):
        env = self.base_env()
        if key and self.key:
            env[KEY] = self.key
        rig = self.env.get('API_RIG_RIG') or str(PLATFORM / 'bin/rig')
        result = subprocess.run([rig, *args], env=env, capture_output=True, text=True, timeout=timeout)
        if check and result.returncode:
            raise Refused(f'rig {args[0]} failed: {(result.stderr or result.stdout).strip()[:300]}')
        return result

    def rig_json(self, *args):
        result = self.rig(*args, '--json')
        try:
            return json.loads(result.stdout)
        except ValueError:
            return None

    def loop(self, *args, timeout=900):
        env = self.base_env()
        workers = self.config['workers']
        env.update(LOOP_CAP=str(workers['cap']), LOOP_WORKER_MAX_SECONDS=str(workers['max_seconds']),
                   LOOP_WORKER_MAX_TURNS=str(workers['max_turns']), LOOP_WORKER_TOKEN_LIMIT=str(workers['max_tokens']),
                   LOOP_WORKER_COST_LIMIT=str(workers['max_usd']), LOOP_WORKER_RETRY_COST_LIMIT=str(workers['retry_usd']),
                   LOOP_WORKER_FIRST_CHANGE=str(workers['first_change_turns']))
        env['LOOP_GOVERNED_LABELS'] = ','.join(self.config.get('governed_labels') or [])
        if workers['mode'] == 'seat':
            env.update(LOOP_SEAT_RIG=self.team, LOOP_SEAT_RUNTIME='pi')
        else:
            env['LOOP_RUNTIME'] = 'pi'
            if self.key:
                env[KEY] = self.key           # the headless workers' one key, by name
        loop = self.env.get('API_RIG_LOOP') or str(LOOP)
        return subprocess.run([loop, args[0], self.repo, *args[1:]], env=env,
                              capture_output=True, text=True, timeout=timeout)

    def loop_state(self):
        result = self.loop('state')
        try:
            return json.loads(result.stdout)
        except ValueError:
            raise Refused(f'dev-loop state failed: {(result.stderr or result.stdout).strip()[:300]}')

    def send(self, session, text):
        return self.rig('send', session, text).returncode == 0

    # ---- spend ---------------------------------------------------------------------------

    def reading(self):
        """The OpenRouter key's usage record, refreshed first (password-free reading)."""
        refresh = self.env.get('API_RIG_USAGE_REFRESH')
        command = shlex.split(refresh) if refresh is not None else USAGE_REFRESH
        if command:
            subprocess.run(command, capture_output=True, timeout=60, env=self.base_env())
        source = self.env.get('API_RIG_USAGE_FILE') or '/var/lib/dev-server/usage/openrouter.json'
        try:
            return json.loads(Path(source).read_text())
        except (OSError, ValueError):
            return None


def read_credential(env):
    folder = env.get('CREDENTIALS_DIRECTORY')
    if folder and (Path(folder) / CREDENTIAL).is_file():
        return (Path(folder) / CREDENTIAL).read_text().strip() or None
    return None


def windows(now):
    """The start of the current UTC day and month, as OpenRouter counts them."""
    t = time.gmtime(now)
    day = calendar.timegm((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0))
    month = calendar.timegm((t.tm_year, t.tm_mon, 1, 0, 0, 0))
    return day, month


def spend(state, reading, now, stale=900):
    """(day, month) dollars on the key, or None when there is no current reading. OpenRouter's
    own daily and monthly figures win; otherwise the difference from the first reading of the
    window this rig recorded (state['spend'] keeps the samples). Unknown is never zero."""
    credits = (reading or {}).get('credits') or {}
    used, captured = credits.get('used'), (reading or {}).get('captured')
    if not isinstance(used, (int, float)) or not isinstance(captured, (int, float)) or now - captured > stale:
        return None
    samples = [s for s in state.get('spend', []) if isinstance(s, list) and len(s) == 2]
    if not samples or samples[-1][0] != captured:
        samples.append([captured, used])
    day_start, month_start = windows(now)
    samples = [s for s in samples if s[0] >= month_start - 86400][-500:]
    state['spend'] = samples

    def since(start):
        before = [s for s in samples if s[0] <= start]
        base = before[-1][1] if before else min(s[1] for s in samples if s[0] >= start)
        return max(0.0, used - base)

    day = credits['daily'] if isinstance(credits.get('daily'), (int, float)) else since(day_start)
    month = credits['monthly'] if isinstance(credits.get('monthly'), (int, float)) else since(month_start)
    return float(day), float(month)


# ---- holds -----------------------------------------------------------------------------------

def hold(rig, state, kind, reason):
    if (state.get('hold') or {}).get('kind') == kind:
        return
    state['hold'] = {'kind': kind, 'reason': reason, 'since': rig.clock()}
    rig.loop('pause')
    stop_running(rig)
    rig.room(f'holding: {reason}. ' + ('It clears by itself when the window turns.' if kind in SOFT
                                       else f'The owner releases it with: api-rig release {rig.repo}'))
    if kind not in SOFT:
        rig.ledger.ask(f'The rig holds: {reason}. What should change before it goes on? (Release it with '
                       f'`api-rig release {rig.repo}` once that is done.)', kind='hold', key=f'hold-{kind}',
                       unblocks='all dispatch for the project')


def stop_running(rig):
    """Stop the spend now: running headless workers end (their supervisor stops the group), and
    every Pi seat of the team aborts its turn."""
    ledger = loop_ledger(rig)
    for pid_file in ledger.glob('*/workers/*.pid') if ledger.is_dir() else []:
        if pid_file.with_suffix('.exit').exists():
            continue
        try:
            os.kill(int(pid_file.read_text().strip()), signal.SIGTERM)
        except (OSError, ValueError):
            pass
    nodes = rig.rig_json('ps', '--nodes', '--rig', rig.team) if rig.spec.is_file() else None
    for node in nodes or []:
        if node.get('runtime') == 'pi' and node.get('canonicalSessionName'):
            rig.rig('send', node['canonicalSessionName'], '/abort', '--raw')


def loop_ledger(rig):
    state = rig.env.get('LOOP_STATE_DIR')
    brief = Path(rig.env.get('DEV_PLATFORM_BRIEF', Path.home() / '.config/dev-platform/brief.conf'))
    if not state and brief.is_file():
        found = re.search(r'^LOOP_STATE_DIR=["\']?([^"\'\n]+)', brief.read_text(), re.MULTILINE)
        state = found and os.path.expanduser(os.path.expandvars(found.group(1)))
    return Path(state or Path.home() / '.local/state/dev-platform/loop') / rig.repo.replace('/', '__')


def gate_spend(rig, state):
    """True when spending may continue. Over a cap, or with no current reading, hold."""
    caps = rig.config['caps']
    found = spend(state, rig.reading(), rig.clock())
    current = (state.get('hold') or {}).get('kind')
    if found is None:
        hold(rig, state, 'spend-unknown', 'no current OpenRouter usage reading, so spend is unknown')
        return False
    day, month = found
    state['spent'] = {'day': round(day, 4), 'month': round(month, 4), 'at': rig.clock()}
    if month >= caps['month_usd']:
        hold(rig, state, 'cap-month', f"the monthly cap is reached: ${month:.2f} of ${caps['month_usd']:.2f} this month")
        return False
    if day >= caps['day_usd']:
        hold(rig, state, 'cap-day', f"the daily cap is reached: ${day:.2f} of ${caps['day_usd']:.2f} today (UTC)")
        return False
    if current in SOFT:
        state['hold'] = None
        rig.room(f"spend is back under the caps (${day:.2f} today, ${month:.2f} this month); dispatch resumes")
        rig.loop('go')
    return True


# ---- seats -----------------------------------------------------------------------------------

def members(rig):
    """(pod, member, runtime) for each seat the spec declares."""
    out, pod = [], None
    for line in rig.spec.read_text().splitlines():
        found = re.match(r'^  - id: (\S+)', line)
        if found:
            pod = found.group(1)
        found = re.match(r'^      - id: (\S+)', line)
        if found:
            out.append([pod, found.group(1), None])
        found = re.match(r'^        runtime: (\S+)', line)
        if found and out:
            out[-1][2] = found.group(1)
    return [tuple(m) for m in out]


def session_of(rig, pod, member):
    return f'{pod}-{member}@{rig.team}'


def member_fragment(rig, pod, member):
    """The member's YAML from rig.yaml, re-indented as a fragment, with an absolute cwd."""
    lines = rig.spec.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l == f'      - id: {member}')
    body = [lines[start][8:]]
    for line in lines[start + 1:]:
        if not line.startswith('        ') or line.startswith('      - '):
            break
        body.append(line[8:])
    body = [f'cwd: {json.dumps(str(rig.folder))}' if b.startswith('cwd:') else b for b in body]
    target = rig.path(f'{pod}-{member}.member.yaml')
    target.write_text('\n'.join(body) + '\n')
    return target


def stats(rig, session):
    """turns, context tokens and idleness of a Pi seat's current session, from its own file."""
    sidecar = rig.openrig_home / 'state/pi' / session / 'runner-state.json'
    try:
        file = Path(json.loads(sidecar.read_text())['sessionFile'])
        lines = file.read_text().splitlines()
    except (OSError, ValueError, KeyError, TypeError):
        return None
    turns, context, last = 0, 0, None
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get('message') if entry.get('type') == 'message' else None
        if not message:
            continue
        last = message
        if message.get('role') == 'user':
            turns += 1
        elif message.get('role') == 'assistant' and isinstance((message.get('usage') or {}).get('totalTokens'), int):
            context = message['usage']['totalTokens']
    idle = bool(last and last.get('role') == 'assistant' and last.get('stopReason') not in ('toolUse', 'tool_use')
                and rig.clock() - file.stat().st_mtime > 15)
    return {'file': str(file), 'turns': turns, 'context': context, 'idle': idle}


def refusal(rig, since=0):
    """(kind, why) when a seat's latest reply is OpenRouter refusing the account itself: 402, the
    account's credits are spent (the key's own limit may still show room); 401 or 403, the key no
    longer works. Every seat then fails each turn, silently, until a person acts; None otherwise."""
    for pod, member, runtime in members(rig) if rig.spec.is_file() else []:
        if runtime != 'pi':
            continue
        sidecar = rig.openrig_home / 'state/pi' / session_of(rig, pod, member) / 'runner-state.json'
        try:
            lines = Path(json.loads(sidecar.read_text())['sessionFile']).read_text().splitlines()
        except (OSError, ValueError, KeyError, TypeError):
            continue
        last = None
        for line in lines:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            message = entry.get('message') if entry.get('type') == 'message' else None
            if message and message.get('role') == 'assistant' and (message.get('timestamp') or 0) / 1000 > since:
                last = message
        error = str((last or {}).get('errorMessage') or '') if (last or {}).get('stopReason') == 'error' else ''
        code = re.match(r'\s*(\d{3})\b', error)
        code = code and code.group(1)
        if code == '402' or 'more credits' in error:
            return 'credits', (f'the OpenRouter account is out of credits: every request from {member} is refused '
                               f'(402). Add credits at https://openrouter.ai/settings/credits')
        if code in ('401', '403'):
            return 'key', f'OpenRouter refuses the rig\'s key ({code}) for {member}. Re-enter it with ol-login openrouter'
    return None


def reopen_text(rig, pod, member):
    return (f'You are re-opened on a fresh context: the API rig keeps every session short. '
            f'Read your checkpoint {rig.checkpoint(member)} (if it is not there, this is your first session), '
            f'then `api-rig status {rig.repo}` and the top of the loop\'s status (`dev-loop status {rig.repo} | sed -n 1,25p`; '
            f'its fold history is long and costs money to read), and continue where they say. Read only what the next '
            f'step needs: every token on this rig is paid for. '
            f'Keep the checkpoint current: after every fold, verdict or decision, rewrite it with the state, '
            f'what you wait on and the next step. Use ask_advice when a wrong call would be expensive.')


def checkpoint_text(rig, member):
    return (f'Checkpoint now: write {rig.checkpoint(member)} with the state of the work, the decisions and their '
            f'reasons, what you are waiting on and your next step, so a fresh session can continue from it alone. '
            f'Then reply `checkpoint written` and stop. Your next session starts from that file.')


def ensure_team(rig, state):
    """The rig's daemon, with the key, and the project's team running fresh from its spec."""
    status = rig.rig('daemon', 'status')
    if 'running' not in status.stdout:
        if not rig.key:
            raise Refused('no OpenRouter key: run under the api-rig unit (LoadCredential) or with the key in the environment')
        rig.openrig_home.mkdir(parents=True, exist_ok=True)
        rig.tmux_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        rig.rig('daemon', 'start', '--no-kernel', '--port', str(rig.config['port']), key=True, check=True)
        rig.log(f"daemon started on port {rig.config['port']} ({rig.openrig_home})")
    elif not daemon_has_key(rig):
        raise Refused(f"the OpenRig daemon on port {rig.config['port']} has no OpenRouter key; stop it so the rig starts its own")
    rigs = rig.rig_json('ps') or []
    mine = next((r for r in rigs if r.get('name') == rig.team and not r.get('isArchived')), None)
    if mine and mine.get('status') == 'running':
        state['rig_id'] = mine['rigId']
        return False
    if mine:
        rig.rig('down', mine['rigId'], '--delete')
    for pod, member, runtime in members(rig):
        if runtime == 'pi':
            piseat.prepare(session_of(rig, pod, member), rig.openrig_home, models=rig.base_env().get('DEV_PLATFORM_PI_MODELS'))
    result = rig.rig('up', str(rig.spec), '--cwd', str(rig.folder), '--yes', '--json', timeout=600)
    try:
        state['rig_id'] = json.loads(result.stdout)['rigId']
    except (ValueError, KeyError):
        raise Refused(f'rig up failed: {(result.stderr or result.stdout).strip()[:300]}')
    state['seats'] = {}
    for pod, member, runtime in members(rig):
        if pod in SEATS:
            rig.send(session_of(rig, pod, member), reopen_text(rig, pod, member))
            # The fold count is unknown until the loop is read: the first rotation pass sets it.
            state['seats'][member] = {'opened': rig.clock(), 'folds': None, 'asked': None, 'asks': 0}
    rig.log(f'team {rig.team} up fresh ({len(members(rig))} seats)')
    return True


def daemon_has_key(rig):
    """Whether the running daemon was started with the key in its environment (name only)."""
    pid = re.search(r'pid (\d+)', rig.rig('daemon', 'status').stdout)
    try:
        return pid is not None and f'{KEY}='.encode() in Path(f'/proc/{pid.group(1)}/environ').read_bytes()
    except OSError:
        return False


def rotate(rig, state):
    """Re-open a control or overseer seat on a fresh context when its cadence is due."""
    cadence = rig.config['cadence']
    folds = len(state.get('folded', []))
    for pod, member, runtime in members(rig):
        if pod not in SEATS or runtime != 'pi':
            continue
        seat = state.setdefault('seats', {}).setdefault(member, {'opened': rig.clock(), 'folds': folds, 'asked': None, 'asks': 0})
        if seat.get('folds') is None:
            seat['folds'] = folds   # the baseline: folds before this seat opened are not its cadence
            continue
        session = session_of(rig, pod, member)
        found = stats(rig, session)
        if found is None:
            continue
        due = [why for why, hit in (
            (f'{folds - seat["folds"]} fold(s)', cadence['per_fold'] and folds > seat['folds']),
            (f'{found["turns"]} turns', found['turns'] >= cadence['turns']),
            (f'a {found["context"]}-token context', found['context'] >= cadence['tokens'])) if hit]
        if not due:
            continue
        if not seat['asked']:
            if found['idle'] and rig.send(session, checkpoint_text(rig, member)):
                seat.update(asked=rig.clock(), asks=seat.get('asks', 0) + 1, why=', '.join(due))
            continue
        written = rig.checkpoint(member).is_file() and rig.checkpoint(member).stat().st_mtime >= seat['asked']
        late = rig.clock() - seat['asked'] > rig.config['nudge_minutes'] * 60
        if not written and not late:
            continue
        if not written and seat['asks'] < 3:
            seat['asked'] = None                      # ask again on the next pass
            continue
        rig.rig('remove', state['rig_id'], f'{pod}.{member}', check=True)
        piseat.prepare(session, rig.openrig_home, models=rig.base_env().get('DEV_PLATFORM_PI_MODELS'))
        rig.rig('add', state['rig_id'], pod, str(member_fragment(rig, pod, member)), check=False, timeout=300)
        deadline = time.monotonic() + rig.config['seat_wait']
        while time.monotonic() < deadline:
            nodes = rig.rig_json('ps', '--nodes', '--rig', rig.team) or []
            if any(n.get('canonicalSessionName') == session and n.get('startupStatus') == 'ready' for n in nodes):
                break
            time.sleep(3)
        rig.send(session, reopen_text(rig, pod, member))
        rig.log(f'{session} re-opened fresh ({seat.get("why")}); checkpoint {"written" if written else "NOT written"}')
        if not written:
            rig.room(f'{session} re-opened without a new checkpoint after {seat["asks"]} asks ({seat.get("why")})')
        state['seats'][member] = {'opened': rig.clock(), 'folds': folds, 'asked': None, 'asks': 0}


# ---- the loop ------------------------------------------------------------------------------

def say_once(rig, state, key, session, text):
    """Send `text`, again only after the nudge interval, at most three times; then tell the room."""
    said = state.setdefault('said', {}).setdefault(key, {'at': 0, 'n': 0})
    if rig.clock() - said['at'] < rig.config['nudge_minutes'] * 60:
        return
    if said['n'] >= 3:
        if said['n'] == 3:
            rig.room(f'{session} has not acted on: {text[:120]}')
            said['n'] += 1
        return
    if rig.send(session, text):
        said.update(at=rig.clock(), n=said['n'] + 1)


def control(rig):
    return session_of(rig, 'control', 'lead')


def head_of(path):
    result = subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    status = subprocess.run(['git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no'],
                            capture_output=True, text=True)
    return result.stdout.strip() + ('+dirty' if status.stdout.strip() else '')


def gate_workers(rig, state, facts):
    """Each worker ready for review gets the repository's check here, once per head. A pass goes
    to the control seat; a failure goes back to the worker's task, and a second one holds."""
    for worker in facts.get('workers', []):
        n, wt = str(worker['issue']), Path(worker['worktree'])
        record = state.setdefault('workers', {}).setdefault(n, {'checked': None, 'failures': 0})
        if worker['state'] == 'blocked':
            say_once(rig, state, f'blocked-{n}-{head_of(wt)}', control(rig),
                     f'Task #{n} is blocked: read {wt}/.worker-blocked.md and decide (widen the scope, split it, '
                     f'resume it with `dev-loop resume {rig.repo} {n}`, or drop it).')
            continue
        if worker['state'] in ('working', 'no commits'):
            # Not running, no .worker-pr.md, no blocker: the worker stopped short.
            say_once(rig, state, f'stopped-{n}-{head_of(wt)}', control(rig),
                     f'Task #{n} ({worker["branch"]}) stopped without .worker-pr.md or a blocker. Read its log in '
                     f'the loop ledger and resume it (`dev-loop resume {rig.repo} {n}`) or drop it.')
            continue
        if worker['state'] != 'ready for review':
            continue
        head = head_of(wt)
        if record['checked'] == head:
            if record.get('passed'):
                say_once(rig, state, f'review-{n}-{head}', control(rig),
                         f'Review #{n}: {worker["branch"]} is ready and its check passed here. Ask each reviewer in '
                         f'the review pod, then `dev-loop fold {rig.repo} {n}` on a pass, or send the findings back.')
            continue
        check = subprocess.run(['bash', str(HOOKS / 'check-once.sh')], cwd=wt, capture_output=True, text=True,
                               timeout=3600, env=rig.base_env())
        record.update(checked=head, passed=check.returncode == 0)
        if check.returncode == 0:
            rig.log(f'#{n}: check passed at {head[:10]}')
            continue
        record['failures'] += 1
        tail = '\n'.join((check.stdout + check.stderr).strip().splitlines()[-15:])
        rig.log(f'#{n}: check failed ({record["failures"]}) at {head[:10]}')
        if record['failures'] >= 2:
            hold(rig, state, 'check', f'the check failed twice on #{n} ({worker["branch"]})')
            return False
        # Back to the same worker, on the same branch, with the failure as the brief's last word.
        (wt / '.worker-pr.md').rename(wt / '.worker-pr.failed.md')
        with (wt / '.worker-brief.md').open('a') as brief:
            brief.write(f'\n## The check failed on your last head ({head[:10]})\n\nThis section wins over the ones '
                        f'above. Fix what the check reports, run the check again, then write .worker-pr.md.\n\n'
                        f'```\n{tail}\n```\n')
        resumed = rig.loop('resume', n)
        rig.log(f'#{n}: resumed with the failure: {(resumed.stdout or resumed.stderr).strip()[:200]}')
    return True


def drive_steps(rig, state, facts, ready=0):
    """With every task folded, none ready and the head not yet green: the control seat drives the
    staging deploy, the runner and the journeys through `api-rig step`; then the merge request."""
    head = facts.get('rig') and head_of(facts['worktree'])
    if not head or not facts.get('folded') or ready or state.get('green') == head:
        return
    if any(w['state'] in ('running', 'ready for review', 'working') for w in facts.get('workers', [])):
        return
    results = rig.steps()
    for step in STEPS:
        done = results.get(step) or {}
        if done.get('head') == head and done.get('ok'):
            continue
        if done.get('head') == head:              # failed on this head
            if step == 'deploy':
                hold(rig, state, 'deploy', f'the staging deploy of {done.get("tag")} failed')
            else:
                say_once(rig, state, f'fix-{step}-{head}', control(rig),
                         f'The {step} failed on {done.get("tag")}: read {rig.path("api-rig-steps.jsonl")} and write fix '
                         f'tasks for what it found; the loop dispatches them.')
            return
        say_once(rig, state, f'step-{step}-{head}', control(rig),
                 f'Every task is folded into {facts["rig"]}. Run the {step} now: `api-rig step {rig.repo} {step}` '
                 f'(it runs the project\'s own helper and records the result), then report what it said.')
        return
    close = rig.loop('close')
    state['green'] = head
    rig.log(f'{head[:10]} green: deploy, runner and journeys passed; merge request written')
    land = 'dev-loop close {} --merge'.format(rig.repo) if facts.get('mode') == 'local' else f'dev-loop close {rig.repo} --push'
    rig.room(f'merge request ready: {facts["rig"]} at {head[:10]} ({results.get("deploy", {}).get("tag")}) passed '
             f'the staging deploy, the runner and the journeys. Read {loop_ledger(rig)}/'
             f'{facts["rig"].replace("/", "__")}/pr.md; the owner lands it with: {land}'
             + ('' if close.returncode == 0 else ' (close reported a problem; see the rig log)'))


INBOX_SKIP = ('.', '~')


def inbox(rig, state):
    """The owner's records, handed to the control seat. A record dropped in inbox/ (an email, a
    meeting's notes, an insurer's letter, counsel's edits) is distilled into candidates. The
    owner promotes a candidate in an intake session, not here. Records stay in the engagement
    folder, never in the repository. A handed file moves to inbox/sent/."""
    root = rig.folder / 'inbox'
    for sub in ('', 'sent'):
        (root / sub).mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S', time.localtime(rig.clock()))
    for item in sorted(p for p in root.iterdir() if p.is_file() and not p.name.startswith(INBOX_SKIP)):
        sent = root / 'sent' / f'{stamp}-distill-{item.name}'
        item.rename(sent)
        text = (f'A new record for {rig.repo}: {sent}. Distill it with the distill skill '
                f'(skills/distill/SKILL.md): ranked candidate requirements written to the incoming file '
                f'of the repository, outside it, nothing filed or decided. The record stays where it is; '
                f'never copy it into the repository. Then tell the owner in one line how many candidates it gave.')
        rig.send(control(rig), text)
        rig.room(f'distilling {item.name} (the control seat has it)')


def waiting_on_owner(rig, state):
    """One room line per proposed decision that holds tasks back."""
    listed = rig.loop('tasks', 'list').stdout
    waits = {}
    for line in listed.splitlines():
        found = re.match(r'^#(\d+) waits \((.+?)\) ', line)
        if found:
            waits.setdefault(found.group(2), []).append('#' + found.group(1))
    told = state.setdefault('told_waits', {})
    for reason, tasks in sorted(waits.items()):
        key = f'{reason}|{",".join(tasks)}'
        if told.get(reason) != key:
            told[reason] = key
            rig.room(f'waiting on the owner: {reason} (holds {", ".join(tasks)})')
    for reason in list(told):
        if reason not in waits:
            del told[reason]
    state['waiting'] = waits
    ledger = rig.ledger
    open_keys = set()
    for reason, tasks in waits.items():
        found = re.match(r'decision (\d{4}) is (\w+)', reason)
        if not found:
            continue
        key = f'decision-{found.group(1)}'
        open_keys.add(key)
        ledger.ask(f'Decision {found.group(1)}{decision_title(rig, found.group(1))} is {found.group(2)}. '
                   f'Accept it, change it, or reject it?', kind='decision', key=key,
                   unblocks=', '.join(tasks), recommendation='see the recommendation in the decision record')
    for item in ledger.open():
        if item['kind'] == 'decision' and item.get('key') not in open_keys:
            ledger.withdraw(item['key'])


def decision_title(rig, number):
    root = rig.project['root']
    listing = subprocess.run(['git', '-C', root, 'ls-files', 'docs/decisions/'], capture_output=True, text=True).stdout
    path = next((p for p in listing.split() if p.startswith(f'docs/decisions/{number}-')), None)
    try:
        heading = next(l for l in (Path(root) / path).read_text().splitlines() if l.startswith('# '))
    except (TypeError, OSError, StopIteration):
        return ''
    return f' ("{heading.lstrip("# ").split(". ", 1)[-1]}")'


def answered(rig, state, ask_id, words, by):
    """Record an answer and hand it to the control seat."""
    try:
        item = rig.ledger.answer(ask_id, words, by)
    except ValueError as error:
        rig.log(f'answer to {ask_id} not taken: {error}')
        return f'not taken: {error}'
    record = rig.path(f'answers/{ask_id}.md')
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(rigasks.record_text(item))
    rig.send(control(rig), f'The owner answered {ask_id}: read {record} and act on it.')
    rig.room(f'{ask_id} answered by {by}: {words.strip()[:120]}')
    return f'answered {ask_id}'


def inbox_record(rig, text, by):
    """A record sent from the room becomes a file in the inbox, distilled on the next pass."""
    stamp = time.strftime('%Y%m%d-%H%M%S', time.localtime(rig.clock()))
    target = rig.folder / 'inbox' / f'talk-{stamp}.md'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f'# A record sent from the company room\n\nFrom: {by}\n\n{text.strip()}\n')
    return f'record from {by}'


def talk(rig, state):
    """The asks go to the company's room; the owner's answers and the records come back."""
    config = rig.config.get('talk')
    if not config:
        return
    login = rigasks.talk_login(rig.env)
    if not login:
        rig.log('talk is configured but the unit has no nextcloud credential (ol-login nextcloud-rig)')
        return
    channel = rigasks.Talk(config['url'], config['room'], login, config.get('host'))
    events = rigasks.sync_talk(channel, rig.ledger, rig.path('talk.json'), set(config.get('owners') or []),
                               set(config.get('staff') or []), config.get('relay') or 'acme',
                               lambda ask_id, words, by: answered(rig, state, ask_id, words, by),
                               lambda text, by: inbox_record(rig, text, by))
    for event in events:
        rig.log(f'talk: {event}')


def tick(rig):
    """One pass of the cycle. Returns the state it leaves."""
    with rig.locked():
        return _tick(rig)


def _tick(rig):
    state = rig.load()
    try:
        if (state.get('hold') or {}).get('kind') not in (None, *SOFT):
            return state
        if not gate_spend(rig, state):
            return state
        refused = refusal(rig, state.get('released_at') or 0)
        if refused:
            hold(rig, state, *refused)
            return state
        fresh = ensure_team(rig, state)
        facts = rig.loop_state()
        state['folded'] = facts.get('folded', [])
        if not facts.get('rig'):
            goal = rig.config.get('goal')
            if not goal:
                say_once(rig, state, 'no-goal', control(rig),
                         f'There is no open rig branch for {rig.repo} and no goal in api-rig.json. Ask the owner for '
                         f'the next goal; do not start one yourself.')
                return state
            started = rig.loop('start', goal)
            rig.log(f'start {goal}: {(started.stdout or started.stderr).strip().splitlines()[0:1]}')
            facts = rig.loop_state()
        if facts.get('mode') == 'local':
            waiting_on_owner(rig, state)
        try:
            talk(rig, state)
        except (OSError, ValueError) as error:
            rig.log(f'talk failed: {error}')
        inbox(rig, state)
        if facts.get('steer') != 'go':
            rig.loop('go')
        else:
            rig.loop('tick')
        facts = rig.loop_state()
        state['folded'] = facts.get('folded', [])
        if not gate_workers(rig, state, facts):
            return state
        plan = loop_ledger(rig) / facts['rig'].replace('/', '__') / 'plan.md'
        ready = len(re.findall(r'^  #\d+ lane=', plan.read_text(), re.MULTILINE)) if plan.is_file() else 0
        if not ready and not facts.get('workers') and not facts.get('folded'):
            say_once(rig, state, f'intake-{facts["rig"]}', control(rig),
                     f'The plan for {facts["rig"]} has no ready task. Run intake for the goal: specification first, '
                     f'then task files with Scope and Depends on (`dev-loop tasks {rig.repo} new`, the intake skill), '
                     f'tests first in each task. The loop dispatches them as they are ready.')
        drive_steps(rig, state, facts, ready)
        if not fresh:
            rotate(rig, state)
        state.pop('error', None)
    except (Refused, subprocess.SubprocessError, OSError) as error:
        rig.log(f'pass failed: {error}')
        state['error'] = {'at': rig.clock(), 'what': str(error)[:300]}
    finally:
        rig.save(state)
    return state


# ---- the steps the control seat drives -----------------------------------------------------

def step(rig, name):
    """Run one of the project's helpers on the rig branch head and record it. The deploy tags the
    head first (a local tag; pushing tags is the owner's)."""
    if name not in STEPS:
        raise Refused(f'steps: {", ".join(STEPS)}')
    facts = rig.loop_state()
    if not facts.get('rig'):
        raise Refused('no rig branch is open')
    wt = Path(facts['worktree'])
    head = head_of(wt)
    tag = (rig.steps().get('deploy') or {}).get('tag') if name != 'deploy' else None
    if name == 'deploy':
        prior = subprocess.run(['git', '-C', str(wt), 'tag', '--list', f'{rig.config["tag_prefix"]}*'],
                               capture_output=True, text=True).stdout.split()
        numbers = [int(t[len(rig.config['tag_prefix']):]) for t in prior if t[len(rig.config['tag_prefix']):].isdigit()]
        tag = f'{rig.config["tag_prefix"]}{max(numbers, default=0) + 1}'
        subprocess.run(['git', '-C', str(wt), 'tag', tag, 'HEAD'], check=True, capture_output=True)
    command = rig.config['steps'].get(name) or []
    if command:
        env = {**rig.base_env(), 'API_RIG_TAG': tag or '', 'API_RIG_HEAD': head, 'API_RIG_STEP': name}
        result = subprocess.run(command, cwd=wt, env=env, capture_output=True, text=True, timeout=7200)
        ok, code = result.returncode == 0, result.returncode
        tail = '\n'.join((result.stdout + result.stderr).strip().splitlines()[-20:])
    else:
        ok, code, tail = True, 0, f'skipped: no {name} helper in api-rig.json'
    record = {'step': name, 'head': head, 'tag': tag, 'ok': ok, 'code': code, 'at': rig.clock(), 'tail': tail}
    with rig.path('api-rig-steps.jsonl').open('a') as stream:
        stream.write(json.dumps(record) + '\n')
    rig.log(f'step {name} on {head[:10]} ({tag}): {"ok" if ok else f"failed ({code})"}')
    return record


# ---- the owner's verbs -------------------------------------------------------------------------

def unit_text(user=None, home=None):
    return UNIT.format(user=user or os.environ.get('USER', 'owner'), home=home or str(Path.home()),
                       platform=str(paths.install()))


def switch(project, to, dry_run=False, run=subprocess.run):
    """Move a project's team to the API rig or back. Returns the commands it ran (or would run)."""
    rig = Rig(project)
    unit = f'api-rig@{rig.folder.name}.service'
    shape = [str(PLATFORM / 'bin/rig-shape'), 'write', project['repo']]
    if to == 'api':
        settings = rig.folder / 'api-rig.json'
        steps = [shape + ['review', '--all', 'pi']]
        root_steps = [['sudo', 'install', '-m', '0644', str(rig.path('api-rig@.service')), '/etc/systemd/system/api-rig@.service'],
                      ['sudo', 'systemctl', 'daemon-reload'], ['sudo', 'systemctl', 'enable', '--now', unit]]
        if rig.config.get('talk'):
            # The Talk login reaches this project's unit alone, as its second credential.
            dropin = f'/etc/systemd/system/api-rig@{rig.folder.name}.service.d'
            root_steps[1:1] = [['sudo', 'install', '-d', '-m', '0755', dropin],
                               ['sudo', 'install', '-m', '0644', str(rig.path('api-rig-talk.conf')), f'{dropin}/talk.conf']]
        if dry_run:
            return steps + root_steps
        rig.path('api-rig@.service').write_text(unit_text())
        rig.path('api-rig-talk.conf').write_text('[Service]\nLoadCredential=nextcloud:/etc/dev-server/accounts/nextcloud-rig.key\n')
        if not settings.is_file():
            settings.parent.mkdir(parents=True, exist_ok=True)
            settings.write_text(json.dumps({'goal': None, 'caps': DEFAULTS['caps'], 'steps': DEFAULTS['steps']}, indent=2) + '\n')
    elif to == 'subscription':
        steps = [shape + ['build']]
        root_steps = [['sudo', 'systemctl', 'disable', '--now', unit]]
        if dry_run:
            return root_steps + steps
        steps = root_steps + steps
        root_steps = []
    else:
        raise Refused('switch --to api|subscription')
    for command in steps + root_steps:
        if run(command).returncode:
            raise Refused('stopped at: ' + ' '.join(command))
    return steps + root_steps


def status(rig):
    state = rig.load()
    caps = rig.config['caps']
    spent = state.get('spent') or {}
    lines = [f'{rig.repo}: API rig {rig.team if rig.spec.is_file() else "(no spec)"} in {rig.folder}',
             f"  spend: ${spent.get('day', '?')} of ${caps['day_usd']} today, ${spent.get('month', '?')} of "
             f"${caps['month_usd']} this month" + (f" (read {int(rig.clock() - spent['at'])}s ago)" if spent.get('at') else ' (no reading yet)'),
             f"  hold: {(state.get('hold') or {}).get('reason') or 'none'}"]
    for member, seat in sorted((state.get('seats') or {}).items()):
        lines.append(f"  {member}: opened {time.strftime('%H:%M', time.localtime(seat['opened']))}"
                     + (f", checkpoint asked ({seat.get('why')})" if seat.get('asked') else ''))
    for name, record in sorted(rig.steps().items()):
        lines.append(f"  {name}: {'ok' if record['ok'] else 'FAILED'} on {record['head'][:10]} ({record.get('tag')})")
    for item in rig.ledger.open():
        lines.append(f"  ask {item['id']} ({item['kind']}): {item['question'][:110]}")
    if state.get('error'):
        lines.append(f"  last error: {state['error']['what']}")
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='api-rig', description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    for name, text in (('status', 'spend against the caps, the hold, the seats and the steps'),
                       ('run', 'the supervised cycle, until stopped (the unit runs this)'),
                       ('release', 'clear a hold (the owner)'), ('hold', 'hold the rig now (the owner)'),
                       ('step', 'run one of the project\'s helpers on the rig head (the control seat)'),
                       ('switch', 'move the project\'s team to the API rig or back (the owner)'),
                       ('asks', 'the rig\'s open questions for people'),
                       ('ask', 'add a question for the owner (the control seat, the overseers, the company agent)'),
                       ('answer', 'answer an ask (the owner, here or from a seat he drives)'),
                       ('go', 'dispatch now with the rig\'s own workers (Pi on OpenRouter); never plain dev-loop go')):
        p = sub.add_parser(name, help=text)
        p.add_argument('project')
        if name == 'run':
            p.add_argument('--once', action='store_true', help='one pass, then exit')
        if name == 'hold':
            p.add_argument('reason', nargs='*')
        if name == 'step':
            p.add_argument('name', choices=STEPS)
        if name == 'switch':
            p.add_argument('--to', required=True, choices=('api', 'subscription'))
            p.add_argument('--dry-run', action='store_true')
        if name in ('status', 'asks'):
            p.add_argument('--json', action='store_true')
        if name == 'asks':
            p.add_argument('--all', action='store_true')
        if name == 'ask':
            p.add_argument('question', nargs='+')
            p.add_argument('--kind', default='clarification', choices=rigasks.KINDS)
            p.add_argument('--unblocks', default='')
            p.add_argument('--option', action='append', default=[])
            p.add_argument('--recommend', default='')
        if name == 'answer':
            p.add_argument('id')
            p.add_argument('words', nargs='+')
            p.add_argument('--by', default='the owner on dev-server')
    sub.add_parser('unit', help='the systemd unit the switch installs')
    args = parser.parse_args(argv)
    try:
        if args.command == 'unit':
            sys.stdout.write(unit_text())
            return 0
        project = resolve(args.project)
        if args.command == 'switch':
            for command in switch(project, args.to, args.dry_run):
                print(('would run: ' if args.dry_run else 'ran: ') + ' '.join(shlex.quote(c) for c in command))
            return 0
        rig = Rig(project)
        if args.command == 'status':
            print(json.dumps(rig.load(), indent=2) if args.json else status(rig))
        elif args.command == 'release':
            with rig.locked():
                state = rig.load()
                was = (state.get('hold') or {}).get('reason')
                state['hold'] = None
                state['released_at'] = rig.clock()   # a seat's refusal from before this is settled
                state.pop('said', None)
                for item in rig.ledger.open():
                    if item['kind'] == 'hold':
                        rig.ledger.withdraw(item['key'])
                for record in (state.get('workers') or {}).values():
                    record['failures'] = 0
                rig.save(state)
                rig.loop('go')
                rig.room(f'released by the owner{f" (was: {was})" if was else ""}; dispatch resumes')
        elif args.command == 'hold':
            with rig.locked():
                state = rig.load()
                hold(rig, state, 'owner', ' '.join(args.reason) or 'held by the owner')
                rig.save(state)
        elif args.command == 'asks':
            items = rig.ledger.all() if args.all else rig.ledger.open()
            if args.json:
                print(json.dumps(items, indent=2))
            for item in [] if args.json else items:
                print(f"{item['id']} {item['status']} ({item['kind']}): {item['question']}"
                      + (f"\n    unblocks {item['unblocks']}" if item.get('unblocks') else '')
                      + (f"\n    answer ({item['answered_by']}): {item['answer']}" if item.get('answer') else ''))
            if not items and not args.json:
                print('no open asks')
        elif args.command == 'ask':
            item, new = rig.ledger.ask(' '.join(args.question), args.kind, unblocks=args.unblocks,
                                       options=args.option, recommendation=args.recommend,
                                       by=rig.env.get('OPENRIG_SESSION_NAME') or 'a person on dev-server')
            print(f"{item['id']}: {'asked' if new else 'already open'}")
            if new:
                rig.room(f"asks the owner {item['id']} ({item['kind']}): {item['question'][:140]}")
        elif args.command == 'answer':
            with rig.locked():
                state = rig.load()
                result = answered(rig, state, args.id.upper(), ' '.join(args.words), args.by)
                rig.save(state)
            print(result)
            return 0 if result.startswith('answered') else 2
        elif args.command == 'go':
            # The loop with the rig's settings: Pi workers on the key, the rig's caps and governed labels.
            # Run in the owner's terminal, the loop sees him present.
            result = subprocess.run([rig.env.get('API_RIG_LOOP') or str(LOOP), 'go', rig.repo], env={
                **rig.base_env(), 'LOOP_RUNTIME': 'pi', 'LOOP_CAP': str(rig.config['workers']['cap']),
                'LOOP_WORKER_MAX_SECONDS': str(rig.config['workers']['max_seconds']),
                'LOOP_WORKER_MAX_TURNS': str(rig.config['workers']['max_turns']),
                'LOOP_WORKER_TOKEN_LIMIT': str(rig.config['workers']['max_tokens']),
                'LOOP_WORKER_COST_LIMIT': str(rig.config['workers']['max_usd']),
                'LOOP_WORKER_RETRY_COST_LIMIT': str(rig.config['workers']['retry_usd']),
                'LOOP_WORKER_FIRST_CHANGE': str(rig.config['workers']['first_change_turns']),
                'LOOP_GOVERNED_LABELS': ','.join(rig.config.get('governed_labels') or []),
                **({KEY: rig.key} if rig.key else {})})
            return result.returncode
        elif args.command == 'step':
            record = step(rig, args.name)
            print(f"{args.name} {'ok' if record['ok'] else 'FAILED'} on {record['head'][:10]} ({record['tag']}):\n{record['tail']}")
            return 0 if record['ok'] else 1
        elif args.command == 'run':
            while True:
                state = tick(rig)
                if args.once:
                    print(status(rig))
                    return 0
                time.sleep(rig.config['poll_seconds'])
        return 0
    except Refused as error:
        print(f'api-rig: {error}', file=sys.stderr)
        return 2
