#!/usr/bin/env python3
"""One-shot account readiness for callers; never replays work or swaps credentials."""
import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from . import accounts
from .accounts import save
from .environments import ACCOUNTS

# Reuse the native account probe inside the selected container, where its own
# credentials and binaries live. No provider tokens travel back to the caller.
PROBE = '''
import hashlib
try:
    value = probe(ACCOUNT, Path('/home/node/.codex' if ACCOUNT.startswith('openai-') else '/home/node/.claude'), usage=True)
    email = value.pop('email', None)
    value['identity'] = hashlib.sha256(email.casefold().encode()).hexdigest() if email else None
    print(json.dumps(value))
except Exception:
    print(json.dumps({'error': 'native_probe_unavailable'}))
'''


def container(name):
    return 'helm-account-environments-' + name + '-1'


def registry(root):
    path = root / 'readiness.json'
    return json.loads(path.read_text()) if path.exists() else {'identities': {}}


def remaining(quota):
    # The core Codex pool is the only eligible routing signal. Separate model
    # pools must not be mistaken for an interchangeable core allowance.
    pools = [p for p in quota or [] if p.get('limit_id') == 'codex']
    windows = [p[w] for p in pools for w in ('primary', 'secondary') if w in p]
    values = [w['usedPercent'] for w in windows if isinstance(w.get('usedPercent'), (int, float))]
    return max(0, min(100, 100 - max(values))) if values else None


def observe(name, expected=None, root=None):
    row = {'account': name, 'runtime': 'codex' if name.startswith('openai-') else 'claude',
           'state': 'unavailable', 'observed_at': time.time(), 'remaining_percent': None,
           'capabilities': {'codex': 'unverified', 'claude': 'unverified', 'pi': 'unverified'}}
    try:
        inspected = subprocess.run(['docker', 'inspect', container(name)], capture_output=True, text=True, timeout=8)
        if inspected.returncode:
            return dict(row, reason='Docker or container unavailable; retry after Docker starts')
        inspection = json.loads(inspected.stdout)[0]
        if root is not None:
            mounts = {m['Destination']: m['Source'] for m in inspection['Mounts']}
            if mounts.get('/home/node') != str(root / name / 'home'):
                return dict(row, state='storage_mismatch', reason='running home does not match declared environment root')
        state = inspection['State']
        if not state['Running']:
            return dict(row, reason='container stopped; history retained; no automatic work replay')
        port = 17433 + ACCOUNTS.index(name)
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5) as response:
            if response.status != 200:
                return dict(row, reason='OpenRig daemon unavailable')
        command = ['codex', 'login', 'status'] if row['runtime'] == 'codex' else ['claude', 'auth', 'status', '--json']
        login = subprocess.run(['docker', 'exec', container(name), *command], capture_output=True, text=True, timeout=15)
        if row['runtime'] == 'claude':
            authenticated = bool(json.loads(login.stdout).get('loggedIn'))
        else:
            authenticated = login.returncode == 0
        if not authenticated:
            return dict(row, state='login_required', reason='complete native login in this environment')
        source = (Path(__file__).with_name('accounts.py')).read_text()
        script = source + '\nACCOUNT = ' + repr(name) + '\n' + PROBE
        probe = subprocess.run(['docker', 'exec', '-i', container(name), 'python3', '-'], input=script,
                               capture_output=True, text=True, timeout=45)
        native = json.loads(probe.stdout)
        if native.get('error') or not native.get('identity'):
            return dict(row, state='probe_unavailable', reason='native identity or provider status unavailable; do not infer logout')
        identity = native.pop('identity')
        row.update(identity_fingerprint=identity, plan=native.get('plan'), quota=native.get('quota'),
                   container=container(name), image=inspection['Config']['Image'])
        if expected is None:
            return dict(row, state='unenrolled', reason='explicit enrollment required')
        if identity != expected:
            return dict(row, state='identity_mismatch', reason='login differs from enrolled account; new work refused')
        row['capabilities'][row['runtime']] = 'authenticated'
        left = remaining(native.get('quota'))
        row['remaining_percent'] = left
        if left is None:
            return dict(row, state='quota_unknown', reason=native.get('quota_reason') or 'usage unavailable')
        return dict(row, state='ready' if left > 0 else 'exhausted', reason='native quota observation')
    except (OSError, ValueError, subprocess.SubprocessError):
        return dict(row, reason='health probe unavailable; retry later; saved sessions unchanged')


def choose(rows, runtime):
    eligible = [r for r in rows if r['runtime'] == runtime and r['state'] == 'ready']
    return max(eligible, key=lambda r: r['remaining_percent']) if eligible else None


def launch_plan(rows, root, client, provider, preferred=None, allow_unknown=False):
    if client == 'pi':
        return {'version': 1, 'client': client, 'provider': provider, 'execution_kind': 'host',
                'selected': None, 'launch_allowed': False, 'observed_at': time.time(),
                'reason': 'host-native Pi profile and authentication integration pending; container fallback refused'}
    runtime = 'codex' if provider == 'openai' else 'claude'
    candidates = [r for r in rows if r['runtime'] == runtime]
    if preferred:
        candidates = [r for r in candidates if r['account'] == preferred]
    selected = choose(candidates, runtime)
    if selected is None and allow_unknown and preferred:
        selected = next((r for r in candidates if r['state'] == 'quota_unknown'), None)
    capability = runtime if client == 'openrig' else client
    allowed = bool(selected and selected['capabilities'].get(capability) == 'authenticated')
    result = {'version': 1, 'client': client, 'provider': provider,
              'selected': selected['account'] if selected else None, 'execution_kind': 'container',
              'launch_allowed': allowed, 'observed_at': time.time(),
              'reason': 'account preflight passed' if allowed else 'no eligible environment or client authentication unverified',
              'scope': 'new or explicitly resumed execution only; never replay interrupted turns'}
    if selected:
        account = selected['account']
        result.update(container=selected['container'], image=selected['image'],
                      readiness=selected['state'], capabilities=selected['capabilities'],
                      quota=selected['quota'], quota_observed_at=selected['observed_at'],
                      mounts=[{'host': str(root / account / name), 'container': target}
                              for name, target in [('home', '/home/node'), ('workspace', '/workspace')]])
    return result


def host_observations(data):
    """Use native client APIs in their existing registered profiles, never Docker."""
    rows = []
    for name in ACCOUNTS:
        native = accounts.status(data, name, usage=True)
        left = remaining(native.get('quota'))
        verified = native['identity'] == 'verified'
        state = ('ready' if left > 0 else 'exhausted') if verified and left is not None else (
            'quota_unknown' if verified else 'unverified')
        rows.append(dict(account=name, runtime=accounts.runtime(name), state=state,
                         observed_at=time.time(), remaining_percent=left, quota=native.get('quota'),
                         reason=native.get('reason') or native.get('quota_reason'),
                         capabilities={client: 'authenticated' if verified and client == accounts.runtime(name)
                                       else 'unverified' for client in ('codex', 'claude', 'pi')}))
    return rows


# OpenRig 0.5.14 (patched for per-seat config_home) names runtimes "codex" and
# "claude-code"; this service's own runtime names stay "codex"/"claude" so this
# is the one place that translates for the RigSpec member fragment.
OPENRIG_RUNTIME = {'codex': 'codex', 'claude': 'claude-code'}


def host_plan(rows, data, client, provider, cwd, preferred=None, allow_unknown=False):
    runtime = 'codex' if provider == 'openai' else 'claude'
    result = dict(version=1, execution_kind='host', client=client, provider=provider,
                  selected=None, launch_allowed=False, observed_at=time.time(), cwd=str(cwd),
                  reason='no verified native profile with eligible quota',
                  scope='new or explicitly resumed execution; no credential swaps or turn replay')
    if client not in (runtime, 'openrig', 'pi'):
        return dict(result, reason='client and provider do not match')
    if client == 'pi':
        return dict(result, reason='Pi requires separately verified native authentication; worker login is not Pi authentication')
    candidates = [r for r in rows if r['runtime'] == runtime and (not preferred or r['account'] == preferred)]
    selected = choose(candidates, runtime)
    if selected is None and preferred and allow_unknown:
        selected = next((r for r in candidates if r['state'] == 'quota_unknown'), None)
    if selected is None:
        return result
    name = selected['account']
    binding = data['bindings'][name]
    home = accounts.home_for(data, name)
    # Checked again by the native launcher immediately before exec.
    accounts.configuration_check(name, home, cwd)
    key = 'CODEX_HOME' if runtime == 'codex' else 'CLAUDE_CONFIG_DIR'
    native_default = bool(binding.get('native_default'))
    expected_email = binding.get('expected_email')
    # Doubles as the OpenRig eligibility gate below: a binding that never
    # recorded an expected identity cannot be fingerprinted for resume/fork
    # revalidation, so it is not "verified and eligible" for a seat.
    identity_ref = hashlib.sha256(expected_email.casefold().encode()).hexdigest() if expected_email else None
    result.update(selected=name, readiness=selected['state'], capabilities=selected['capabilities'],
                  quota=selected['quota'], quota_observed_at=selected['observed_at'],
                  profile={'ref': name + ':' + runtime, 'client': runtime, 'home': str(home),
                           'identity_ref': identity_ref,
                           'environment': {} if native_default else {key: str(home)},
                           'native_default': native_default},
                  history={'owner': runtime, 'profile_home': str(home), 'copy_transcripts': False})
    if client == runtime:
        result.update(launch_allowed=True, reason='native profile preflight passed')
        return result
    # Only 'openrig' remains here; 'pi' and provider/client mismatches already returned above.
    if identity_ref is None:
        result.update(reason='OpenRig launch requires an enrolled account binding with a verified '
                             'identity; an unenrolled binding cannot be revalidated on resume or fork')
        return result
    member = {'runtime': OPENRIG_RUNTIME[runtime], 'cwd': str(cwd)}
    if not native_default:
        # A native-default binding must emit no config_home: the seat uses
        # the daemon's own default home, not a profile override.
        member['config_home'] = str(home)
        result['config_home'] = str(home)
    result.update(launch_allowed=True, member=member,
                  reason='native profile preflight passed; OpenRig seat carries this account binding')
    return result


def host_table(rows):
    lines = ['ACCOUNT              CLIENT   READINESS       REMAINING', '-' * 62]
    for row in rows:
        left = row['remaining_percent']
        lines.append(f"{row['account']:<20} {row['runtime']:<8} {row['state']:<15} {str(left) + '%' if left is not None else 'unknown'}")
    lines.append('Native host profiles. Unknown quota is not zero; no running sessions changed.')
    return '\n'.join(lines)


def profile_plan(client, account, root, prepare=False):
    if client not in ('pi', accounts.runtime(account)):
        raise ValueError('client and account provider do not match')
    root = root.expanduser().absolute()
    if any(part.is_symlink() for part in (root, *root.parents)):
        raise ValueError('profile roots cannot contain symlinks')
    if client != 'pi':
        if prepare:
            accounts.prepare_login(account, root)
        home = root / account
        command = ['codex', 'login', '--device-auth'] if client == 'codex' else ['claude', 'auth', 'login', '--claudeai']
        environment = {'CODEX_HOME' if client == 'codex' else 'CLAUDE_CONFIG_DIR': str(home)}
    else:
        home = root / 'pi' / account
        if any(part.is_symlink() for part in (home, home.parent)):
            raise ValueError('Pi profile cannot contain symlinks')
        if prepare:
            home.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(home, 0o700)
        cli = Path(__file__).resolve().parents[2] / 'integrations/pi/node_modules/@earendil-works/pi-coding-agent/dist/cli.js'
        if not cli.is_file():
            cli = Path.home() / '.local/share/dev-platform/pi-runtime/0.87.1/node_modules/@earendil-works/pi-coding-agent/dist/cli.js'
        node = shutil.which('node')
        command = [node, str(cli)] if node and cli.is_file() else None
        environment = {'PI_CODING_AGENT_DIR': str(home)}
    return dict(version=1, execution_kind='host', account=account, client=client,
                profile_home=str(home), environment=environment, native_login_argv=command,
                instructions='Complete native sign-in in your terminal; Pi uses /login. No credentials are imported.',
                launch_allowed=False, reason='Profile preparation is not authentication verification',
                filesystem='Host HOME and cwd unchanged; account profiles are not OS sandboxes')


def check_pi_profile(plan):
    """Read-only native configuration check, deliberately not remote authentication."""
    home = Path(plan['profile_home'])
    if not plan['native_login_argv']:
        return dict(state='runtime_unavailable', capability='unverified')
    if not home.is_dir():
        return dict(state='profile_missing', capability='unverified')
    if (home / 'auth.json').is_symlink() or (home / 'models.json').exists() or accounts.conflicts(os.environ):
        return dict(state='configuration_review_required', capability='unverified')
    # No provider API keys or unrelated agent settings are inherited by this
    # status subprocess. Native Pi's no-refresh path uses read-only auth storage.
    env = {key: os.environ[key] for key in ('HOME','PATH','LANG','TMPDIR') if key in os.environ}
    env.update(plan['environment'], PI_OFFLINE='1')
    provider = 'openai-codex' if plan['account'].startswith('openai-') else 'anthropic'
    result = subprocess.run([*plan['native_login_argv'], 'auth', 'check', '--provider', provider,
                             '--json', '--no-refresh'], env=env, capture_output=True, text=True, timeout=20)
    native = json.loads(result.stdout)
    status = native.get('status')
    if status not in ('ready','not_ready','invalid'):
        raise ValueError('unknown native Pi auth status')
    return dict(state='configured' if status == 'ready' else status, capability='unverified',
                provider=provider, auth_type=native.get('authType') if native.get('authType') in ('oauth','api_key') else None,
                reason='Native local check does not verify identity, token freshness, subscription entitlement or remote acceptance')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, help='Explicit container storage root; required for container operations')
    p.add_argument('--execution-kind', choices=('host', 'container'), default='host')
    p.add_argument('--registry', type=Path, default=Path.home() / '.config/dev-platform/accounts.json')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status').add_argument('--table', action='store_true')
    sub.add_parser('enroll')
    profile = sub.add_parser('profile')
    profile.add_argument('--client', required=True, choices=('pi','codex','claude'))
    profile.add_argument('--account', required=True, choices=ACCOUNTS)
    profile.add_argument('--profiles-root', type=Path, default=Path.home() / '.local/share/dev-platform/accounts')
    action = profile.add_mutually_exclusive_group()
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--check', action='store_true', help='Pi native read-only profile check; does not establish authenticated capability')
    for name in ('plan', 'run'):
        plan = sub.add_parser(name)
        plan.add_argument('--client', required=True, choices=('pi', 'openrig', 'codex', 'claude'))
        plan.add_argument('--provider', required=True, choices=('openai', 'anthropic'))
        plan.add_argument('--preferred-account', choices=ACCOUNTS)
        plan.add_argument('--allow-unknown-quota', action='store_true')
        plan.add_argument('--cwd', type=Path, default=Path.cwd())
        if name == 'run':
            plan.add_argument('arguments', nargs=argparse.REMAINDER)
    select = sub.add_parser('choose')
    select.add_argument('runtime', choices=('codex', 'claude'))
    args = p.parse_args(argv)
    if args.execution_kind == 'host':
        if args.root is not None:
            p.error('--root is container storage; add --execution-kind container explicitly')
        try:
            args.registry = args.registry.expanduser().absolute()
            if args.command == 'profile':
                value = profile_plan(args.client, args.account, args.profiles_root, args.prepare)
                if args.check:
                    if args.client != 'pi':
                        raise ValueError('Native worker identity checks use status and enrolled bindings')
                    value['observation'] = check_pi_profile(value)
                print(json.dumps(value, indent=2))
                return 0
            if args.command == 'enroll':
                raise ValueError('Enroll each native profile with ai-account bind after its own native sign-in')
            data = accounts.load(args.registry)
            if args.command in ('plan', 'run'):
                if args.command == 'run' and args.client == 'openrig':
                    raise ValueError('OpenRig seats are launched with dev-workspace --account, not ai-environment run')
                if args.command == 'run' and not args.preferred_account and any(
                    argument.split('=',1)[0] in ('resume','fork','--resume','-r','--continue','--fork-session')
                    for argument in args.arguments):
                    raise ValueError('resume/fork requires the original explicit account binding')
                cwd = args.cwd.expanduser().resolve(strict=True)
                if not cwd.is_dir():
                    raise ValueError('cwd must be a real host directory')
                if args.client == 'pi':
                    rows = []
                else:
                    rows = host_observations(data)
                result = host_plan(rows, data, args.client, args.provider, cwd,
                                   args.preferred_account, args.allow_unknown_quota)
                if args.command == 'run' and result['launch_allowed']:
                    os.chdir(cwd)
                    return accounts.main(['--registry', str(args.registry.resolve()), 'run',
                                          '--account', result['selected'], *args.arguments])
                print(json.dumps(result, indent=2))
                return 0 if result['launch_allowed'] else 2
            rows = host_observations(data)
            if args.command == 'choose':
                selected = choose(rows, args.runtime)
                print(json.dumps({'execution_kind':'host', 'selected':selected['account'] if selected else None}))
                return 0 if selected else 2
            print(host_table(rows) if args.table else json.dumps(rows, indent=2))
            return 0
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            message = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else 'native profile operation unavailable; inspect profile, cwd and configuration'
            print('ai-environment: ' + message, file=sys.stderr)
            return 2
    if args.root is None:
        p.error('--root is required for explicit container operations')
    if args.command in ('run','profile'):
        p.error('container execution remains owned by the native OpenRig integration')
    root = args.root.expanduser().resolve()
    if args.command == 'plan' and args.client == 'pi':
        print(json.dumps(launch_plan([], root, 'pi', args.provider), indent=2))
        return 2
    data = registry(root)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda n: observe(n, data['identities'].get(n), root), ACCOUNTS))
    if args.command == 'enroll':
        identities = {r['account']: r.get('identity_fingerprint') for r in rows}
        if not all(identities.values()):
            raise SystemExit('Enrollment refused: all four native identity probes must succeed')
        for provider in ('openai', 'anthropic'):
            if identities[provider+'-apple'] == identities[provider+'-gmail']:
                raise SystemExit('Enrollment refused: duplicate provider identities')
        if data['identities'] and data['identities'] != identities:
            raise SystemExit('Enrollment refused: existing identities differ; review native logins')
        save(root / 'readiness.json', {'identities': identities})
        print('Four distinct provider bindings enrolled; credentials remain native.')
    elif args.command == 'plan':
        result = launch_plan(rows, root, args.client, args.provider, args.preferred_account, args.allow_unknown_quota)
        print(json.dumps(result, indent=2))
        return 0 if result['launch_allowed'] else 2
    elif args.command == 'choose':
        selected = choose(rows, args.runtime)
        print(json.dumps({'selected': selected['account'] if selected else None,
                          'reason': 'greatest observed core quota' if selected else 'no verified account with known available quota',
                          'scope': 'new work only; no running session migration'}, indent=2))
        return 0 if selected else 2
    else:
        for row in rows:
            row.pop('identity_fingerprint', None)
        print(json.dumps(rows, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
