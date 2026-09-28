"""Non-secret account bindings; native authentication remains native.

No daemon, token copying, billing mutations, or live-session rebinding.
"""
import argparse
import contextlib
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import tempfile
import time

IDS = ('anthropic-gmail', 'anthropic-apple', 'openai-gmail', 'openai-apple', 'zai')
CONFLICTS = ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN',
             'OPENAI_IDENTITY_TOKEN_FILE', 'OPENAI_FEDERATION_RULE_ID', 'CLAUDE_CODE_OAUTH_TOKEN',
             'CLAUDE_CODE_API_KEY_HELPER_TTL_MS', 'CLAUDE_CODE_SESSION_ACCESS_TOKEN',
             'CLAUDE_SECURESTORAGE_CONFIG_DIR')
# Shared with prepare_login()'s Codex config.toml safety check: any of these words
# appearing in a native config file means a routing/authentication override is
# present, regardless of which check found it.
FORBIDDEN_OVERRIDES = ('apiKeyHelper', 'ANTHROPIC_', 'CLAUDE_CODE_USE_', 'CLAUDE_CODE_OAUTH_TOKEN',
                       'model_provider', 'openai_base_url', 'base_url', 'env_key', 'http_headers',
                       'forced_login_method', 'forceLoginMethod', 'experimental_bearer_token')


def now():
    return datetime.now(timezone.utc).isoformat()


def runtime(account):
    return 'codex' if account.startswith('openai-') else 'claude'


def load(path):
    if not path.exists():
        return {'version': 1, 'selected': None, 'bindings': {}}
    data = json.loads(path.read_text())
    if data.get('version') != 1 or not isinstance(data.get('bindings'), dict):
        raise ValueError('unsupported account registry')
    return data


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.accounts-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def home_for(data, account):
    binding = data['bindings'].get(account, {})
    return Path(binding.get('home', Path.home() / '.local/share/dev-platform/accounts' / account)).expanduser().resolve()


def conflicts(env):
    return sorted(k for k, v in env.items() if v and (k in CONFLICTS or
                  k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))))


def environment(account, home, native_default=False):
    bad = conflicts(os.environ)
    if bad:
        raise ValueError('conflicting inherited authentication/provider settings: ' + ', '.join(bad))
    env = os.environ.copy()
    env.pop('CODEX_HOME', None)
    env.pop('CLAUDE_CONFIG_DIR', None)
    if not native_default:
        env['CODEX_HOME' if runtime(account) == 'codex' else 'CLAUDE_CONFIG_DIR'] = str(home)
    return env


def configuration_check(account, home, cwd):
    """Reject routing overrides, without emitting their possibly secret values."""
    paths = [home / ('config.toml' if runtime(account) == 'codex' else 'settings.json')]
    root = Path(cwd).resolve()
    for directory in [root, *root.parents]:
        paths.extend((directory / '.codex/config.toml', directory / '.claude/settings.json',
                      directory / '.claude/settings.local.json'))
    for path in paths:
        if path.is_file() and any(word in path.read_text() for word in FORBIDDEN_OVERRIDES):
            raise ValueError('native configuration has authentication/provider overrides; review it before using a subscription binding')


class Rpc:
    """Short-lived native stdio app-server. No thread or turn is created."""
    def __init__(self, env):
        self.proc = subprocess.Popen(['codex', 'app-server'], env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.buffer = b''
        self.sequence = 0

    def call(self, method, params=None):
        self.sequence += 1
        request = {'id': self.sequence, 'method': method}
        if params is not None:
            request['params'] = params
        self.proc.stdin.write((json.dumps(request) + '\n').encode())
        self.proc.stdin.flush()
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if b'\n' not in self.buffer:
                ready, _, _ = select.select([self.proc.stdout], [], [], max(0, deadline - time.monotonic()))
                if not ready:
                    break
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if not chunk:
                    break
                self.buffer += chunk
                if len(self.buffer) > 1024 * 1024:
                    raise ValueError('native status response too large')
                continue
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                response = json.loads(line)
            except ValueError:
                continue
            if response.get('id') == self.sequence:
                if 'error' in response:
                    raise ValueError('native status request unavailable')
                return response.get('result', {})
        raise ValueError('native status request timed out')

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.proc.stdin.close()
        self.proc.stdout.close()


def quota_fields(result):
    limits = result.get('rateLimitsByLimitId')
    if not isinstance(limits, dict):
        limits = {'codex': result.get('rateLimits')}
    clean = []
    for index, (limit_id, value) in enumerate(limits.items(), 1):
        if not isinstance(value, dict):
            continue
        windows = {}
        for key in ('primary', 'secondary'):
            window = value.get(key)
            if isinstance(window, dict):
                windows[key] = {k: window[k] for k in ('usedPercent', 'windowDurationMins', 'resetsAt')
                                if isinstance(window.get(k), (int, float)) and not isinstance(window[k], bool)}
        if windows:
            windows['limit_id'] = (limit_id if isinstance(limit_id, str) and
                                   re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}', limit_id)
                                   else f'pool-{index}')
            clean.append(windows)
    return clean or None


def probe(account, home, usage=False, native_default=False):
    if account == 'zai':
        raise ValueError('z.ai requires verified plan and protected credential delivery; not activated')
    if not home.is_dir():
        raise ValueError('native home missing; complete native login preparation first')
    env = environment(account, home, native_default)
    configuration_check(account, home, Path.cwd())
    if runtime(account) == 'claude':
        response = subprocess.run(['claude', 'auth', 'status', '--json'], env=env,
                                  capture_output=True, text=True, timeout=15)
        data = json.loads(response.stdout)
        if (response.returncode or not data.get('loggedIn') or data.get('authMethod') != 'claude.ai'
                or data.get('apiProvider') != 'firstParty'):
            raise ValueError('Claude subscription authentication unavailable')
        return {'email': data.get('email'), 'plan': data.get('subscriptionType'), 'quota': None,
                'quota_reason': 'Claude auth status does not expose quota; use native /usage'}
    rpc = Rpc(env)
    try:
        rpc.call('initialize', {'clientInfo': {'name': 'dev_platform_accounts', 'version': '1'}})
        rpc.proc.stdin.write(b'{"method":"initialized"}\n')
        rpc.proc.stdin.flush()
        account_data = rpc.call('account/read', {'refreshToken': False}).get('account') or {}
        if account_data.get('type') != 'chatgpt':
            raise ValueError('Codex ChatGPT authentication unavailable')
        result = {'email': account_data.get('email'), 'plan': account_data.get('planType'),
                  'quota': None, 'quota_reason': 'not requested'}
        if usage:
            try:
                result['quota'] = quota_fields(rpc.call('account/rateLimits/read'))
                result['quota_reason'] = None if result['quota'] else 'native response has no quota windows'
            except ValueError:
                result['quota_reason'] = 'native quota unavailable'
        return result
    finally:
        rpc.close()


def status(data, account, usage=False):
    binding = data['bindings'].get(account)
    result = {'id': account, 'selected': data.get('selected') == account, 'runtime': runtime(account),
              'observed_at': now(), 'identity': 'unverified', 'quota': None,
              'billing': 'unknown; login and quota do not establish renewal or spend'}
    if not binding:
        result['reason'] = 'not bound; native login and identity verification needed'
        return result
    try:
        native = probe(account, home_for(data, account), usage, binding.get('native_default', False))
        if not native.get('email') or native['email'].casefold() != binding['expected_email'].casefold():
            raise ValueError('native identity does not match the bound account')
        result.update(identity='verified', plan=native.get('plan'), quota=native.get('quota'),
                      quota_reason=native.get('quota_reason'))
    except (ValueError, OSError, subprocess.SubprocessError):
        result['reason'] = 'native verification unavailable or identity/configuration mismatch; inspect plan and native login'
    return result


def plan(data, account):
    return {'id': account, 'runtime': runtime(account), 'native_home': str(home_for(data, account)),
            'environment_key': 'CODEX_HOME' if runtime(account) == 'codex' else 'CLAUDE_CONFIG_DIR',
            'native_default': data['bindings'].get(account, {}).get('native_default', False),
            'scope': 'new ai-account launches and compatible future loop workers; existing sessions unchanged',
            'conflicting_environment_names': conflicts(os.environ),
            'openclaw': 'separate native personal account selection required; existing sessions stay pinned',
            'openrig': 'direct seat rebinding unavailable in 0.5.14; use an explicitly configured new launch',
            'desktop': 'not switched by this selector', 'fallback': 'none'}



def prepare_login(account, root):
    """Prepare an empty independent native profile; never import credentials."""
    if account not in IDS or account == 'zai':
        raise ValueError('unsupported isolated subscription profile')
    root = Path(root).expanduser().absolute()
    for ancestor in (root, *root.parents):
        if ancestor.is_symlink():
            raise ValueError('account profile root cannot contain symlinks')
    home = root / account
    if home.is_symlink():
        raise ValueError('account profile cannot be a symlink')
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(home, 0o700)
    if runtime(account) == 'codex':
        config = home / 'config.toml'
        expected_line = 'cli_auth_credentials_store = "file"'
        if config.is_symlink():
            raise ValueError('existing profile configuration differs; inspect before preparing login')
        if config.exists():
            # A concurrent tool (e.g. profile provisioning, or OpenRig's managed [hooks]
            # block) may have appended to this file. Accept it as long as the required
            # credentials-store line is present verbatim and no authentication/provider
            # override has been introduced; refuse anything else unchanged.
            text = config.read_text()
            has_store_line = expected_line in text.splitlines()
            has_override = any(word in text for word in FORBIDDEN_OVERRIDES)
            if not has_store_line or has_override:
                raise ValueError('existing profile configuration differs; inspect before preparing login')
        else:
            fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(expected_line + '\n')
    return {'account': account, 'native_home': str(home),
            'environment_key': 'CODEX_HOME' if runtime(account) == 'codex' else 'CLAUDE_CONFIG_DIR',
            'native_command': ['codex','login'] if runtime(account) == 'codex' else ['claude','auth','login','--claudeai'],
            'binding_changed': False, 'credentials_copied': False,
            'notice': 'Preparation only. Native sign-in and identity verification are required before binding. Profile separation is not an OS sandbox.'}

def table(output):
    rows = output.get('accounts', [output])
    lines = ['  ACCOUNT             LOGIN       PLAN       USED / WINDOW / RESET (UTC)', '-' * 92]
    for row in rows:
        windows = [(limit.get('limit_id', 'unknown pool'), name, limit[name])
                   for limit in row.get('quota') or [] for name in ('primary', 'secondary')
                   if name in limit]
        values = []
        for limit_id, name, window in windows:
            reset = window.get('resetsAt')
            try:
                at = datetime.fromtimestamp(reset, timezone.utc).strftime('%m-%d %H:%M') if reset else 'unknown reset'
            except (ValueError, OverflowError, OSError):
                at = 'unknown reset'
            duration = window.get('windowDurationMins')
            label = 'week' if duration == 10080 else (f'{duration}m' if duration else 'unknown window')
            values.append(f"{limit_id}/{name}: {window.get('usedPercent', '?')}% / {label} / {at}")
        plan_name = row.get('plan') or 'unknown'
        marker = '*' if row.get('selected') else ' '
        lines.append(f"{marker} {row['id']:<19} {row['identity']:<11} {plan_name:<10} {'; '.join(values) or 'unknown'}")
    lines.append('Observed: ' + output.get('observed_at', 'unknown'))
    lines.append('Billing/renewal: unknown. Quota is not spend; unknown is not zero.')
    lines.append('* Selected for new CLI and compatible loop launches; existing sessions unchanged.')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=Path.home() / '.config/dev-platform/accounts.json')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'select', 'status', 'login-plan'):
        p = commands.add_parser(name)
        p.add_argument('account', choices=IDS)
        if name == 'status':
            p.add_argument('--table', action='store_true')
    commands.add_parser('monitor').add_argument('--table', action='store_true')
    commands.add_parser('selected')
    p = commands.add_parser('prepare-login')
    p.add_argument('account', choices=IDS)
    p.add_argument('--profiles-root', type=Path, default=Path.home() / '.local/share/dev-platform/accounts')
    p = commands.add_parser('bind')
    p.add_argument('account', choices=IDS)
    p.add_argument('--home', required=True, type=Path)
    p.add_argument('--expected-email', required=True)
    p.add_argument('--native-default', action='store_true', help='Use native default home with profile environment unset')
    p = commands.add_parser('run')
    p.add_argument('--account', choices=IDS)
    p.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    locks = contextlib.ExitStack()
    try:
        if args.command in ('bind', 'select'):
            args.registry.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor = os.open(str(args.registry) + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
            lock = locks.enter_context(os.fdopen(descriptor, 'w'))
            fcntl.flock(lock, fcntl.LOCK_EX)
        data = load(args.registry)
        if args.command == 'prepare-login':
            output = prepare_login(args.account, args.profiles_root)
        elif args.command == 'selected':
            output = {'selected': data.get('selected')}
        elif args.command == 'monitor':
            output = {'observed_at': now(), 'accounts': [status(data, a, True) for a in IDS],
                      'notice': 'read-only one-shot snapshot, not spend or renewal data; unknown is not zero'}
        elif args.command == 'bind':
            home = args.home.expanduser().resolve()
            if any(Path(b['home']).resolve() == home and name != args.account for name, b in data['bindings'].items()):
                raise ValueError('native home already bound to another account')
            default_home = (Path.home() / ('.codex' if runtime(args.account) == 'codex' else '.claude')).resolve()
            if args.native_default and home != default_home:
                raise ValueError('native-default binding must name the actual default home')
            native = probe(args.account, home, native_default=args.native_default)
            if not native.get('email') or native['email'].casefold() != args.expected_email.casefold():
                raise ValueError('native login does not match the expected identity; no binding written')
            if any(name != args.account and runtime(name) == runtime(args.account) and
                   b.get('expected_email', '').casefold() == native['email'].casefold()
                   for name, b in data['bindings'].items()):
                raise ValueError('native identity already belongs to another account binding')
            data['bindings'][args.account] = {'home': str(home), 'expected_email': native['email'], 'verified_at': now(), 'native_default': args.native_default}
            save(args.registry, data)
            output = status(data, args.account)
        elif args.command == 'status':
            output = status(data, args.account, True)
        elif args.command == 'login-plan':
            output = plan(data, args.account)
            output['native_command'] = [runtime(args.account), 'login'] if runtime(args.account) == 'codex' else ['claude', 'auth', 'login']
            output['instructions'] = 'Use a trusted local terminal/browser with the named home environment. Never send passwords, tokens or login codes through agent chat. Configure shared safety rules and skills in the isolated home before launch. Then bind with expected identity.'
            if args.account == 'zai':
                output['native_command'] = None
                output['instructions'] = 'Not activated: verify coding plan, isolated provider configuration and protected credential delivery first.'
        elif args.command == 'plan':
            output = plan(data, args.account)
        elif args.command == 'select':
            output = status(data, args.account)
            if output['identity'] != 'verified':
                raise ValueError('selection refused: account identity is not verified')
            data['selected'] = args.account
            save(args.registry, data)
            output = plan(data, args.account)
            output['selected'] = True
        else:
            account = args.account or data.get('selected')
            if account not in IDS:
                raise ValueError('choose a verified account explicitly; no fallback')
            arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
            blocked = ('-c', '--config', '--profile', '--settings', '--setting-sources', '--bare',
                       '--oss', '--local-provider', '-C', '--cd')
            if runtime(account) == 'codex':
                blocked += ('-p',)
            if any(a in blocked or any(a.startswith(b + '=') for b in blocked) or
                   any(a.startswith(b) and a != b for b in blocked if len(b) == 2)
                   for a in arguments):
                raise ValueError('configuration overrides are not accepted by an account-bound launch')
            if arguments and arguments[0] in ('login', 'logout', 'auth', 'app-server'):
                raise ValueError('use native login preparation, not an agent run, for authentication')
            verified = status(data, account)
            if verified['identity'] != 'verified':
                raise ValueError('launch refused: account identity is not verified')
            home = home_for(data, account)
            os.execvpe(runtime(account), [runtime(account), *arguments], environment(account, home, data['bindings'][account].get('native_default', False)))
            return 0
        print(table(output) if getattr(args, 'table', False) else json.dumps(output, indent=2))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        # Native stderr/stdout and exception contents may contain secrets. Never relay them.
        message = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else 'native account operation unavailable'
        print('ai-account: ' + message, file=sys.stderr)
        return 2
    finally:
        locks.close()
