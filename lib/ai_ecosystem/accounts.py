"""ai-account: the account registry's command, and the launch guards every launcher shares.

The registry, the resolver and the usage record are registry.py. Credentials are only
in the root store and only ol-login-root touches them (sign-in: ol-login). This module
keeps the old verbs working over that one registry:

  ai-account list | status [--table|--json]
  ai-account resolve --provider P --client C [--account ID] [--who NAME] [--json]
  ai-account run --client claude|codex [--account ID] [--model M] [--cwd DIR] -- ARGS
  ai-account select ID | select --clear [--provider P]
                                           the owner names an account for a provider: every
                                           launch through this user's resolver uses it or fails
  ai-account selected | status ID          (old loop verbs; selected = the resolver's choice)

`run` starts the session through the launcher (agent owner), which hands the session its
credential: no login lives in anyone's home.
"""
import argparse
import json
import os
from pathlib import Path
import sys

from . import registry
import subprocess

PSTACK_MODEL = Path(__file__).resolve().parents[2] / 'bin/pstack-model'


def default_model(client):
    """An interactive session's model when none is named: the `judgment and prose` line of the
    one model file, through pstack-model, for this client's runtime."""
    found = subprocess.run([sys.executable, str(PSTACK_MODEL), 'resolve', 'judgment and prose',
                            '--runtime', client, '--no-inherit'], capture_output=True, text=True)
    model = found.stdout.split('\t', 1)[0].strip()
    if found.returncode or not model:
        raise registry.Refused(f'no model for {client} in the model file (pstack-model show)')
    return model

CONFLICTS = ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN',
             'OPENAI_IDENTITY_TOKEN_FILE', 'OPENAI_FEDERATION_RULE_ID', 'CLAUDE_CODE_OAUTH_TOKEN',
             'CLAUDE_CODE_API_KEY_HELPER_TTL_MS', 'CLAUDE_CODE_SESSION_ACCESS_TOKEN',
             'CLAUDE_SECURESTORAGE_CONFIG_DIR')
# Any of these words in a native config file means a routing/authentication override.
FORBIDDEN_OVERRIDES = ('apiKeyHelper', 'ANTHROPIC_', 'CLAUDE_CODE_USE_', 'CLAUDE_CODE_OAUTH_TOKEN',
                       'model_provider', 'openai_base_url', 'base_url', 'env_key', 'http_headers',
                       'forced_login_method', 'forceLoginMethod', 'experimental_bearer_token')
CLIENT_PROVIDER = {'claude': 'anthropic', 'codex': 'openai'}


def selection_path():
    """The owner's named accounts, one per provider: a plain file in his own config, as
    `ai-account select` kept it before. Naming is never a fallback: a named account that
    cannot serve the launch makes it fail."""
    return Path(os.environ.get('DEV_PLATFORM_ACCOUNT_SELECTION')
                or Path.home() / '.config/dev-platform/account-selection.json')


def selection():
    path = selection_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text())   # unreadable: refuse rather than launch unnamed
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise ValueError(f'unreadable account selection: {path}')
    return data


def select(account=None, provider=None, clear=False):
    reg = registry.load()
    saved = selection()
    if clear:
        if provider:
            saved.pop(provider, None)
        else:
            saved = {}
    else:
        entry = registry.get(reg, account)
        verified = any(registry.signed_in(account, registry.credential_client(entry, c)) for c in entry['clients'])
        if not verified:
            raise registry.Refused(f'{account} is not signed in and verified; selection refused (ol-login {account})')
        saved[entry['provider']] = account
    path = selection_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}')
    tmp.write_text(json.dumps(saved, indent=2, sort_keys=True) + '\n')
    os.replace(tmp, path)
    return saved


def _ids():
    try:
        return tuple(registry.ids(registry.load()))
    except (OSError, ValueError):
        return ()


IDS = _ids()


def runtime(account):
    """The native client of a subscription account, from its registry entry: codex for an
    account with a Codex client, claude otherwise. An id the registry does not know keeps
    the old reading of its name."""
    for entry in registry.load()['accounts']:
        if entry['id'] == account:
            return 'codex' if 'codex' in entry['clients'] else 'claude'
    return 'codex' if account.partition('-')[0] == 'openai' else 'claude'


def conflicts(env):
    return sorted(k for k, v in env.items() if v and (k in CONFLICTS or
                  k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))))


def configuration_check(cwd, homes=()):
    """Refuse routing overrides in project or client config, without showing their values."""
    root = Path(cwd).resolve()
    paths = [Path(h) / name for h in homes for name in ('config.toml', 'settings.json')]
    for directory in [root, *root.parents]:
        paths.extend((directory / '.codex/config.toml', directory / '.claude/settings.json',
                      directory / '.claude/settings.local.json'))
    for path in paths:
        if path.is_file() and any(word in path.read_text(errors='replace') for word in FORBIDDEN_OVERRIDES):
            raise registry.Refused(f'{path} overrides authentication or the provider; review it first')


def load(path=None):
    """The registry as older callers read it: bindings by account, verified ones only."""
    if path and Path(path).is_file():
        try:
            old = json.loads(Path(path).read_text())
            if old.get('version') == 1:
                return old
        except ValueError:
            pass
    data = registry.load()
    bindings = {}
    for entry in data['accounts']:
        for client in entry['clients']:
            record = registry.signin(entry['id'], registry.credential_client(entry, client))
            if record and record.get('verified'):
                bindings[entry['id']] = {'expected_email': record.get('identity'), 'clients': entry['clients']}
    return {'version': 1, 'selected': None, 'bindings': bindings, 'registry': data}


def status(data, account, usage=False):
    """One account as older callers read it."""
    reg = data.get('registry') or registry.load()
    entry = registry.get(reg, account)
    client = registry.credential_client(entry, registry.first_client(entry))
    record = registry.signin(account, client) or {}
    reading = registry.reading(account)
    return {'id': account, 'runtime': runtime(account), 'provider': entry['provider'],
            'identity': ('verified' if record.get('identity_checked', record.get('identity')) else 'unchecked')
                        if record.get('verified') else 'unverified',
            'remaining_percent': registry.remaining(reading), 'quota': registry.describe(reading),
            'reason': record.get('note'), 'selected': selection().get(entry['provider']) == account}


def _resolve(args):
    data = registry.load()
    provider = args.provider or CLIENT_PROVIDER.get(args.client)
    if not provider:
        raise registry.Refused('name the provider: --provider')
    # An account named for this launch wins; otherwise the owner's saved name for the
    # provider. Either one is used or the launch fails: never substituted.
    named = args.account or selection().get(provider)
    result = registry.resolve(data, provider, args.client, named, args.who,
                              metered_ok=getattr(args, 'metered_ok', False))
    if not args.account and named:
        result['reason'] = 'selected by the owner (ai-account select)'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog='ai-account', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    st = sub.add_parser('status')
    st.add_argument('account', nargs='?')
    st.add_argument('--table', action='store_true')
    st.add_argument('--json', action='store_true')
    sub.add_parser('monitor').add_argument('--table', action='store_true')
    sub.add_parser('options', help='every harness, then each account that serves it, with billing and state')
    sel = sub.add_parser('select')
    sel.add_argument('account', nargs='?')
    sel.add_argument('--clear', action='store_true')
    sel.add_argument('--provider')
    for name in ('resolve', 'selected', 'run'):
        p = sub.add_parser(name)
        p.add_argument('--provider')
        p.add_argument('--client', default='claude', choices=('claude', 'codex', 'pi', 'gh'))
        p.add_argument('--account')
        p.add_argument('--who')
        p.add_argument('--json', action='store_true')
        p.add_argument('--metered-ok', action='store_true',
                       help='a metered option, named, confirmed for this one launch')
        if name == 'run':
            p.add_argument('--model')
            p.add_argument('--cwd', type=Path, default=Path.cwd())
            p.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.command == 'list':
            for entry in registry.load()['accounts']:
                print(f'{entry["id"]:<17}{entry["provider"]:<12}{entry["kind"]:<14}'
                      f'{",".join(entry["clients"]):<12}{"default" if entry.get("default") else ""}')
            return 0
        if args.command == 'options':
            print(json.dumps(registry.options(registry.load()), indent=2))
            return 0
        if args.command in ('status', 'monitor'):
            if getattr(args, 'account', None):
                print(json.dumps(status(load(), args.account), indent=2))
                return 0
            rows = registry.status(registry.load())
            print(json.dumps(rows, indent=2) if getattr(args, 'json', False) else registry.table(rows))
            return 0
        if args.command == 'select':
            if args.clear == bool(args.account):
                raise registry.Refused('name one account, or --clear [--provider P]')
            print(json.dumps({'selected': select(args.account, args.provider, args.clear)}, indent=2))
            return 0
        if args.command == 'selected':
            result = _resolve(args)
            print(json.dumps({'selected': result['account'], 'reason': result['reason']}))
            return 0
        if args.command == 'resolve':
            result = _resolve(args)
            print(json.dumps(result, indent=2) if args.json else result['account'])
            return 0
        # run: the launcher hands the credential; this only names the account and model.
        if args.client not in ('claude', 'codex'):
            raise registry.Refused('ai-account run starts claude or codex; Pi roles start through ai-role')
        bad = conflicts(os.environ)
        if bad:
            raise registry.Refused('inherited provider settings would override the account: ' + ', '.join(bad))
        configuration_check(args.cwd)
        # The launcher resolves (and announces a switch) once; a named account is passed on.
        model = args.model or default_model(args.client)
        arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
        env = dict(os.environ, OL_MODEL=model)
        env.pop('OL_ACCOUNT', None)
        if args.account:
            env['OL_ACCOUNT'] = args.account
            env['DEV_SESSION_ACCOUNT'] = args.account
        # Naming context for hooks in the child session. See docs/session-naming.md.
        env['DEV_SESSION_PROVIDER'] = 'openai' if args.client == 'codex' else 'anthropic'
        env['DEV_SESSION_MODEL'] = model
        os.execvpe('agent', ['agent', 'owner', str(args.cwd.resolve()), '--', *arguments], env)
    except registry.Refused as error:
        print(f'ai-account: {error}', file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f'ai-account: {error}', file=sys.stderr)
        return 2
    return 0
