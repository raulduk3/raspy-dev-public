"""Account-bound Pi role launcher: conversation -> identity -> profile -> lock -> exec.

The root launcher (agent-run) resolves the account, hands this process the Pi login as
a private agent directory (--agent-dir) or an API key as a credential, and runs it as
the role's own Linux user; this module needs no registry of its own, and without a
handed agent directory it starts nothing. The launcher never
imports account credentials, never claims Pi identity equals the account's Codex or
Claude binding, and holds the conversation's writer lock across exec. The one secret
it handles is the search tool's API key, the root-held secret the outer launcher hands in
(secret.py), passed on only in the Pi process environment. The launcher's credential
folder itself ($CREDENTIALS_DIRECTORY) goes on to Pi unread, so a tool's command run from
Pi's shell finds the key handed to this session by its own name.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from . import accounts, registry as account_registry, conversations, memory as agent_memory, naming, paths, pi_launch, secret
from .store import Store

PLATFORM = Path(__file__).resolve().parents[2]
# What the Pi process keeps of this environment. CREDENTIALS_DIRECTORY is the folder of
# credentials the root launcher handed this session (secret.py): without it the commands
# Pi's tools run cannot find their key and, as a role, have no other way.
KEEP_ENV = ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TERM', 'COLORTERM', 'TERM_PROGRAM', 'SHELL', 'TMPDIR',
            'CREDENTIALS_DIRECTORY')
# The Perplexity key for the roles' search tool: a root-held secret by this name (secret.py).
SEARCH_SECRET = 'dev-platform-perplexity'
# OpenRouter names a model by its maker: z-ai/glm-5, so a slash is allowed.
MODEL_ID = r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}'
JOURNAL_CONF = Path.home() / '.config/dev-platform/journal.conf'
DEFAULT_JOURNAL = Path('/home/owner/journal')
PI_RUNTIMES = paths.pi_runtimes()
PI_PACKAGE = '@earendil-works/pi-coding-agent'
ACCOUNT_ID = r'[a-z0-9][a-z0-9-]{0,62}'
# Registry provider -> the provider Pi names. A provider absent here is passed through as is,
# so a new one is a registry entry (and, if Pi spells it differently, one line here).
PI_PROVIDER = {'openai': 'openai-codex', 'anthropic': 'anthropic'}
# Providers Pi reaches with an API key: the key the launcher hands in as the pi-key credential
# goes to Pi in this variable, for this one process.
KEY_ENV = {'openrouter': 'OPENROUTER_API_KEY', 'zai': 'ZAI_API_KEY'}
KEY_SECRET = 'pi-key'
# Each role's start model comes from the one model file (the `<role> start` lines, read by
# pstack-model for the pi runtime; owner's decisions 2026-10-05). --model overrides.
PSTACK_MODEL = PLATFORM / 'bin/pstack-model'


def provider_for(account, provider=None):
    if provider:
        return PI_PROVIDER.get(provider, provider)
    known = {e['id']: e['provider'] for e in account_registry.load()['accounts']}
    if account in known:
        return PI_PROVIDER.get(known[account], known[account])
    return 'openai-codex' if account.partition('-')[0] == 'openai' else 'anthropic'


def role_model(agent, provider):
    """The role's start model on this Pi provider, from the one model file; None when the
    file starts the role on another provider (the profile's own default then applies)."""
    import subprocess
    import sys
    try:
        out = subprocess.run([sys.executable, str(PSTACK_MODEL), 'resolve', f'{agent} start', '--runtime', 'pi', '--all'],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    # The start line lists models in order (e.g. Grok on OpenRouter, then GPT on ChatGPT): the
    # first one this session's provider runs.
    for line in out.stdout.splitlines() if out.returncode == 0 else []:
        on, _, model = (line.split() or [''])[0].partition('/')
        if model and on == provider:
            return model
    return None


def identity_file(agent, agents_root):
    for candidate in (Path(agents_root) / agent / 'identity.md', PLATFORM / 'agents' / agent / 'identity.md'):
        if candidate.is_symlink():
            raise ValueError('identity file cannot be a symlink')
        if candidate.is_file():
            return candidate.resolve()
    raise ValueError(f'no identity file for {agent}; author agents/{agent}/identity.md')


def pi_modules(platform=None):
    """Where Node finds the Pi package.

    Node resolves a bare import from node_modules beside the importing file. A release
    carries none, because integrations/pi/.gitignore excludes it, so the pinned runtime
    is linked there once. Without this a launch fails on an unresolved import, which is
    exactly how a working checkout hides the problem from a released install.
    """
    root = Path(platform or PLATFORM) / 'integrations/pi'
    local = root / 'node_modules'
    if (local / PI_PACKAGE).is_dir():
        return local
    if local.exists() and not local.is_symlink():
        raise ValueError('integrations/pi/node_modules exists without the Pi package; '
                         'reinstall it rather than letting a launch guess')
    try:
        pin = json.loads((root / 'package.json').read_text())['dependencies'][PI_PACKAGE]
    except (OSError, ValueError, KeyError):
        raise ValueError('integrations/pi/package.json names no Pi version') from None
    pinned = PI_RUNTIMES / pin / 'node_modules'
    if not (pinned / PI_PACKAGE).is_dir():
        raise ValueError(f'the pinned Pi runtime {pin} is not installed; install it before launching a role')
    if local.is_symlink():
        local.unlink()
    local.symlink_to(pinned)
    return local


def journal_root(conf=None):
    """The journal folder, one absolute path per the config file's first real line."""
    path = Path(conf or JOURNAL_CONF).expanduser()
    if not path.is_file():
        # No journal.conf: the owner's journal on dev-server, if it is there.
        return str(DEFAULT_JOURNAL) if conf is None and DEFAULT_JOURNAL.is_dir() else None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            root = Path(line).expanduser()
            return str(root) if root.is_dir() else None
    return None


def default_model(profile_home, provider, requested, agent=None):
    import re
    if requested:
        if not re.fullmatch(MODEL_ID, requested):
            raise ValueError('invalid model id')
        return requested
    chosen = role_model(agent, provider) if agent else None
    if chosen and re.fullmatch(MODEL_ID, chosen):
        return chosen
    settings = Path(profile_home) / 'settings.json'
    if settings.is_file() and not settings.is_symlink():
        try:
            saved = json.loads(settings.read_text())
        except ValueError:
            saved = {}
        if isinstance(saved, dict) and saved.get('defaultProvider') == provider and \
                isinstance(saved.get('defaultModel'), str) and re.fullmatch(MODEL_ID, saved['defaultModel']):
            return saved['defaultModel']
    raise ValueError('choose --model; the Pi profile has no default model for this provider')


def resume_file(home, requested):
    if not requested:
        return None
    directory = (home / 'native/pi').resolve()
    if requested == 'latest':
        files = sorted((p for p in directory.glob('*.jsonl') if not p.is_symlink() and p.is_file()),
                       key=lambda p: p.stat().st_mtime)
        if not files:
            raise ValueError('no native Pi session in this conversation yet')
        return files[-1].resolve()
    path = Path(requested).expanduser()
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or path.parent.resolve() != directory:
        raise ValueError('resume file must be an existing native session inside this conversation')
    return path.resolve()


def handed_profile(agent_dir, account, provider):
    """The Pi agent directory the launcher prepared for this one session (dev-server)."""
    import re
    if not re.fullmatch(ACCOUNT_ID, account or ''):
        raise ValueError('name the account the launcher resolved')
    home = Path(agent_dir)
    if not home.is_absolute() or not home.is_dir() or any(p.is_symlink() for p in (home, *home.parents)):
        raise ValueError('the agent directory must be an existing absolute directory without symlinks')
    if provider in KEY_ENV:
        observation = {'state': 'configured', 'provider': provider, 'auth_type': 'api_key'}
    elif (home / 'auth.json').is_file() and not (home / 'auth.json').is_symlink():
        observation = {'state': 'configured', 'provider': provider, 'auth_type': 'oauth'}
    else:
        raise ValueError(f'no Pi login was handed to this session for {account}; sign it in from the Mac: ol-login {account} pi')
    return {'profile_home': str(home), 'environment': {'PI_CODING_AGENT_DIR': str(home)}}, observation


def plan(conversation_id, *, state_root=None, account=None, model=None, resume=None,
         agents_root=None, history_archive=None, offline=False, environ=None,
         agent_dir=None, provider=None, journal=None, inbox=None, prompt=None):
    environ = os.environ if environ is None else environ
    bad = accounts.conflicts(environ)
    if bad:
        raise ValueError('conflicting inherited provider settings: ' + ', '.join(bad) + '; launch from a clean shell')
    store = Store(state_root)
    conversation = conversations.read(store, conversation_id)
    home = conversations.path_for(store, conversation_id)
    if not (home / 'native/pi').is_dir():
        raise ValueError('conversation has no native Pi directory')
    if not agent_dir:
        raise ValueError('a Pi role starts through the launcher, which hands it the Pi login folder (--agent-dir)')
    name = account
    provider = provider_for(name or '', provider)
    profile, observation = handed_profile(agent_dir, name, provider)
    model_id = default_model(profile['profile_home'], provider, model, conversation['agent'])
    state = Path(agents_root or Path.home() / '.local/share/dev-platform/agents').expanduser().resolve()
    identity = identity_file(conversation['agent'], state)
    # Memory is derived from the role, never a flag: a role launched without it
    # is exactly the complaint this exists to answer.
    memory_status = agent_memory.status(conversation['agent'], state)
    memory_index = state / conversation['agent'] / 'memory' / 'MEMORY.md'
    # Every role reads the journal and none writes it; additions go to the owner's inbox.
    journal = str(Path(journal).resolve()) if journal and Path(journal).is_dir() else journal_root()
    # What a role adds goes to the owner's inbox: on dev-server the launcher names /home/owner/inbox.
    inbox = Path(inbox or os.environ.get('DEV_PLATFORM_INBOX') or Path.home() / 'inbox')
    # The role's own memory/old and the old archive: each an existing absolute directory.
    archives = []
    for given in ([history_archive] if isinstance(history_archive, (str, Path)) else history_archive or []):
        archive = Path(given).expanduser()
        if not archive.is_absolute() or not archive.is_dir():
            raise ValueError('history archive must be an existing absolute directory')
        archives.append(str(archive.resolve()))
    node = shutil.which('node')
    if not node:
        raise ValueError('node is required for the Pi runtime')
    modules = pi_modules()
    entry = PLATFORM / 'integrations/pi/role-launch.mjs'
    if not entry.is_file():
        raise ValueError('role launch entry missing from the platform checkout')
    binding = conversation.get('binding') or {}
    cwd = binding.get('workspace') or str(home / 'workspace')
    session_title = naming.format_title(conversation.get('title') or '', client='pi', cwd=cwd,
                                        who=conversation['agent'], account=name, provider=provider,
                                        model=model_id, kind='interactive', purpose='chat')
    launch = {'version': 1, 'sessionTitle': session_title,
              'conversation': {key: conversation[key] for key in ('id', 'agent', 'scope')} | {'binding': binding},
              'conversationHome': str(home), 'platformRoot': str(PLATFORM),
              'agentDir': profile['profile_home'], 'identityFile': str(identity),
              'historyArchive': archives or None,
              'memoryState': str(state),
              'journalRoot': journal, 'inboxRoot': str(Path(inbox).resolve()) if journal else None,
              'prompt': prompt,
              'accountRef': name + ':pi', 'provider': provider, 'modelId': model_id,
              'resumeFile': str(resume_file(home, resume)) if resume else None, 'offline': bool(offline)}
    env = {key: environ[key] for key in KEEP_ENV if key in environ}
    env.update(profile['environment'])
    if provider in KEY_ENV and not offline:
        key = secret.read(KEY_SECRET)
        if not key:
            raise ValueError(f'no API key was handed to this session for {name}; store it from the Mac: ol-login {name}')
        env[KEY_ENV[provider]] = key
    # /goal state belongs to the conversation, beside its native sessions, never in the project.
    env['PI_GOAL_ROOT'] = str(home / 'goals')
    if offline:
        env['PI_OFFLINE'] = '1'
    env['DEV_PLATFORM_ROLE_LAUNCH'] = json.dumps(launch)
    # Naming context for hooks and the Pi runtime. See docs/session-naming.md.
    env.update({'DEV_SESSION_WHO': conversation['agent'], 'DEV_SESSION_ACCOUNT': name,
                'DEV_SESSION_PROVIDER': 'openai' if provider == 'openai-codex' else provider,
                'DEV_SESSION_MODEL': model_id, 'DEV_SESSION_TYPE': 'interactive'})
    attribution = {'account': name, 'pi_profile': observation['state'], 'auth_type': observation.get('auth_type'),
                   'identity': 'unverified',
                   'reason': "Pi sign-in is separate from this account's Codex/Claude binding; equivalence is not established"}
    header = (f"{conversation['agent']} | {conversation['scope']['kind']} | cwd {cwd} | pi {provider}/{model_id} | "
              f"account {name} (identity unverified) | memory {memory_status['total_entries']} entries | rig unbound")
    memory_view = {'state_root': str(state), 'entries': memory_status['total_entries'],
                   'roots': [{'label': r['label'], 'entries': r['entries'], 'writable': r['writable']}
                             for r in memory_status['roots']],
                   'index_in_context': memory_index.is_file(),
                   'index_bytes': memory_index.stat().st_size if memory_index.is_file() else 0,
                   'note': 'The index rides in context; the rest is behind the agent_memory tool'}
    env_keys = sorted(env)
    result = {'version': 1, 'conversation_id': conversation_id, 'agent': conversation['agent'],
              'scope': conversation['scope'], 'cwd': cwd, 'account': attribution,
              'model': provider + '/' + model_id, 'resume_file': launch['resumeFile'], 'memory': memory_view, 'journal': journal, 'pi_modules': str(modules),
              'argv': [str(Path(node).resolve()), str(entry)], 'environment_keys': env_keys,
              'launch': launch, 'header': header,
              'scope_note': 'New or explicitly resumed execution; the launcher records no account equivalence and replays nothing'}
    return result, env


def with_search(env, offline):
    """Give the role's Perplexity tool its key for this one process. The key is the secret the
    launcher handed in, passed only in the Pi environment, and never printed or written."""
    if offline:
        return env, 'offline'
    key = secret.read(SEARCH_SECRET)
    if not key:
        return env, f'off: the {SEARCH_SECRET} secret was not handed to this launch'
    return {**env, 'PERPLEXITY_API_KEY': key}, 'on'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root', type=Path)
    parser.add_argument('--agents-root', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    # turn: one message (read from stdin), its answer printed, no terminal needed (the shared chat).
    for name in ('plan', 'launch', 'turn'):
        command = sub.add_parser(name)
        command.add_argument('conversation')
        command.add_argument('--account', help='the account id the launcher resolved')
        command.add_argument('--provider', help='the registry provider of the account (anthropic, openai, openrouter, zai, ...)')
        command.add_argument('--agent-dir', type=Path, help="the Pi login directory the launcher handed this session")
        command.add_argument('--model')
        command.add_argument('--resume', help="'latest' or an absolute native session path inside the conversation")
        command.add_argument('--history-archive', type=Path, action='append',
                             help='a preserved history to read (memory/old, the old archive); may repeat')
        command.add_argument('--journal', type=Path, help="the owner's journal, read-only (default: journal.conf, else /home/owner/journal)")
        command.add_argument('--inbox', type=Path, help="where a role's additions go (the owner's inbox)")
        command.add_argument('--offline', action='store_true', help='no model network; wiring checks only')
    args = parser.parse_args(argv)
    try:
        prompt = None
        if args.command == 'turn':
            prompt = sys.stdin.read(64 * 1024).strip()
            if not prompt:
                raise ValueError('a turn needs its message on stdin')
        result, env = plan(args.conversation, state_root=args.state_root,
                           account=args.account, model=args.model, resume=args.resume,
                           agents_root=args.agents_root,
                           history_archive=args.history_archive, offline=args.offline,
                           agent_dir=args.agent_dir, provider=args.provider,
                           journal=args.journal, inbox=args.inbox, prompt=prompt)
        if args.command == 'plan':
            print(json.dumps(result, indent=2))
            return 0
        if args.command == 'launch' and (not sys.stdin.isatty() or not sys.stdout.isatty()):
            raise ValueError('launch needs an interactive terminal; use plan to inspect, turn for one message')
        env, search = with_search(env, args.offline)
        print(result['header'] + f' | search {search}', file=sys.stderr, flush=True)
        pi_launch.exec_conversation(result['launch']['conversationHome'], result['argv'], env)
    except (OSError, ValueError) as error:
        print('ai-role: ' + str(error), file=sys.stderr)
        return 2
    return 0
