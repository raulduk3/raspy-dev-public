"""The one account registry, the one resolver, and the one usage record.

Registry: which accounts exist (stable ID, provider, kind, clients, expected
identity, default flag, quota source). Never a credential. The template is
config/accounts.json; the machine's copy is /var/lib/dev-server/accounts/registry.json,
where ol-login-root records the identity each account was first signed in as.

Credentials live only in the root store (/etc/dev-server/accounts/ID.CLIENT, 0600).
Nothing here reads them. What a non-root caller can know is the sign-in record
ol-login-root leaves beside the registry: ID.CLIENT.json with who the client said
it was, whether that matched, and when.

Usage: one reading per account in /var/lib/dev-server/usage/ID.json, written by
ol-status (Claude, from the status line) and ol-login-root (Codex rate limits,
OpenRouter credits). Unknown is not zero.

Billing is per account and client (the owner's launch model, 2026-10-05): a
subscription account is billed as its plan through its own client, but the same
account through another harness can be metered API cost (Pi on an Anthropic plan);
an API key is metered; the model on this machine is free. Every option says which.

Resolver: every launcher asks `resolve` which account a new session gets.
A named account is used or the launch fails. Otherwise the eligible account with
the most remaining observed quota; unknown ranks after any known remainder and
before nothing; exhausted is never chosen. Rotation never chooses a metered option
and never crosses from one billing to another: a metered option starts only when
it is named and confirmed for that launch (metered_ok). A change of account from the last
launch for that provider is written to the rotation record and, when the caller
names who is launching, to the chat. A running session is never touched.
"""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import time

PLATFORM = Path(__file__).resolve().parents[2]
# Accounts renamed when there became one per provider (owner, 2026-10-14): old id -> new id.
RENAMED = {'anthropic-alpha': 'anthropic', 'openai-alpha': 'openai'}
MODEL_PROVIDERS = ('anthropic', 'openai', 'openrouter', 'local')   # named, usable in any place
TEMPLATE = Path(os.environ.get('DEV_PLATFORM_ACCOUNTS_TEMPLATE') or PLATFORM / 'config/accounts.json')  # tests: a fixed list
CLIENTS = ('claude', 'codex', 'pi', 'gh', 'key', 'local')
KINDS = ('subscription', 'api-key', 'oauth', 'local')
BILLINGS = ('subscription', 'metered', 'free', 'none')
# What an account costs through a client unless its entry says otherwise ("billing": {client: ...}).
KIND_BILLING = {'subscription': 'subscription', 'api-key': 'metered', 'local': 'free', 'oauth': 'none'}
# Never in the registry: a value under one of these names would be a credential.
# The name a service key reaches its tool under (secret.py, $CREDENTIALS_DIRECTORY/NAME).
SERVICE_NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,63}')
SECRET_WORDS = ('token', 'secret', 'password', 'api_key', 'apikey', 'refresh', 'access')


def paths():
    """Locations. A user (tests, a second machine) may move them with OL_* variables;
    root never does: whatever reaches root through its environment is ignored."""
    env = {} if os.geteuid() == 0 else os.environ
    state = Path(env.get('OL_ACCOUNTS_STATE', '/var/lib/dev-server/accounts'))
    return {
        'state': state,
        'registry': Path(env.get('OL_ACCOUNTS_REGISTRY', state / 'registry.json')),
        'store': Path(env.get('OL_ACCOUNTS_STORE', '/etc/dev-server/accounts')),
        'usage': Path(env.get('OL_USAGE_DIR', '/var/lib/dev-server/usage')),
        'chat': Path(env.get('OL_CHAT', '/var/lib/dev-server/chat')),
    }


# The usage folder is the agents' to write (owner:agents 2775), and root reads and writes
# there too (the launcher's resolver, ol-login-root's readings). Root never follows a
# name an agent may have planted there: a new file is made under a random name and
# renamed over the old entry (a rename replaces a link, it does not follow it); an
# append opens without following links and only into an ordinary file with one name;
# a read takes only an ordinary file with one name, small, and never waits on it.

READ_LIMIT = 64 * 1024


def read_safe(path, limit=READ_LIMIT, tail=False):
    """The bytes of an ordinary file with one name, at most limit long; None for anything
    else (missing, a link, a pipe, a device, a second name, too large). tail: a longer
    file gives its last limit bytes instead (a log)."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError:
        return None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            return None
        if st.st_size > limit:
            if not tail:
                return None
            os.lseek(fd, st.st_size - limit, os.SEEK_SET)
        chunks, size = [], 0
        while size <= limit:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        return None if size > limit else b''.join(chunks)
    except OSError:
        return None
    finally:
        os.close(fd)


def read_json(path, limit=READ_LIMIT):
    raw = read_safe(path, limit)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, RecursionError):            # an agent's file may be nested past the parser
        return None


def write_atomic(path, text, mode=0o664):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.')
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w') as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)


def append_line(path, line):
    # O_NONBLOCK: a pipe left in a file's place cannot keep the writer waiting on it
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o664)
    try:
        st = os.fstat(fd)
        if stat.S_ISREG(st.st_mode) and st.st_nlink == 1:
            os.write(fd, (line + '\n').encode())
    finally:
        os.close(fd)


class Refused(ValueError):
    """A launch or sign-in that must not go ahead; the message says why, in plain words."""


def _check_entry(entry):
    for key in ('id', 'provider', 'kind', 'clients'):
        if key not in entry:
            raise ValueError(f'registry entry without {key}: {entry.get("id", "?")}')
    if entry['kind'] not in KINDS:
        raise ValueError(f'{entry["id"]}: kind must be one of {", ".join(KINDS)}')
    bad = [c for c in entry['clients'] if c not in CLIENTS]
    if bad:
        raise ValueError(f'{entry["id"]}: unknown client {bad[0]}')
    billing_ = entry.get('billing', {})
    own = (*entry['clients'], *(['key'] if entry['kind'] == 'api-key' else []))
    if not isinstance(billing_, dict) or any(c not in own or b not in BILLINGS for c, b in billing_.items()):
        raise ValueError(f'{entry["id"]}: billing maps its own clients to one of {", ".join(BILLINGS)}')
    if 'places' in entry:
        # bound to folders: used for work under them, never elsewhere, and work there uses
        # only the accounts bound to it (no fallback to an unbound one)
        places = entry['places']
        if not isinstance(places, list) or not places or entry.get('default') \
                or any(not isinstance(p, str) or not p.startswith('/') or '..' in p.split('/') for p in places):
            raise ValueError(f'{entry["id"]}: places is a list of absolute folders, and a bound account is never a default')
    if 'service' in entry:
        # a service key (Perplexity, Harvest, Jev): handed to tools by this name, never a harness
        if entry['kind'] != 'api-key' or entry['clients'] or not SERVICE_NAME.fullmatch(str(entry['service'])):
            raise ValueError(f'{entry["id"]}: a service is an api-key with no clients and a secret name')

    def walk(value, where):
        if isinstance(value, dict):
            for k, v in value.items():
                if any(word in k.lower() for word in SECRET_WORDS):
                    raise ValueError(f'{entry["id"]}: the registry never holds credentials ({where}{k})')
                walk(v, f'{where}{k}.')
    walk(entry, '')


def load(path=None):
    path = Path(path) if path else paths()['registry']
    if not path.exists():
        path = TEMPLATE
    data = json.loads(path.read_text())
    if data.get('version') != 2 or not isinstance(data.get('accounts'), list):
        raise ValueError(f'unsupported account registry: {path}')
    seen = set()
    for entry in data['accounts']:
        _check_entry(entry)
        if entry['id'] in seen:
            raise ValueError(f'account listed twice: {entry["id"]}')
        seen.add(entry['id'])
    for provider in {e['provider'] for e in data['accounts']}:
        if sum(1 for e in data['accounts'] if e['provider'] == provider and e.get('default')) > 1:
            raise ValueError(f'more than one default for {provider}')
    return data


def merge(template, live):
    """Bootstrap's merge: the template decides which accounts exist and how they are
    described; the live copy keeps the identities recorded at sign-in."""
    known = {RENAMED.get(e['id'], e['id']): e for e in (live or {}).get('accounts', [])}
    out = dict(template)
    out['accounts'] = []
    for entry in template['accounts']:
        entry = dict(entry)
        recorded = known.get(entry['id'], {}).get('expected_identity')
        if recorded:
            entry['expected_identity'] = recorded
        out['accounts'].append(entry)
    return out


def ids(data):
    return [e['id'] for e in data['accounts']]


def get(data, account):
    for entry in data['accounts']:
        if entry['id'] == account:
            return entry
    raise Refused(f'no such account: {account} (known: {", ".join(ids(data))})')


def first_client(entry):
    """The client an account is shown and checked under: a service key has none but its key."""
    return entry['clients'][0] if entry['clients'] else 'key'


def service(data, name):
    """The registry entry whose key is handed to tools as NAME (dev-platform-jev ...), or None."""
    return next((e for e in data['accounts'] if e.get('service') == name), None)


def credential_client(entry, client):
    """The name a credential is kept under: an API key serves every client of its
    account and is kept once, as ID.key; a sign-in is kept per client, as ID.CLIENT."""
    return 'key' if entry['kind'] == 'api-key' else client


def billing(entry, client):
    """What a session on this account through this client costs: subscription, metered or free."""
    return entry.get('billing', {}).get(client) or KIND_BILLING[entry['kind']]


def signin(account, client):
    """What ol-login-root recorded for this account and credential, or None."""
    record = read_json(paths()['state'] / f'{account}.{client}.json')
    return record if isinstance(record, dict) else None


def signed_in(account, client):
    if account == 'local':
        return True             # the model on this machine needs no login
    record = signin(account, client)
    return bool(record and record.get('verified'))


# ---- usage -------------------------------------------------------------------

def _num(value, low, high):
    """A plain finite number in [low, high], or None. Readings are written by agents."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) and low <= value <= high else None


YEAR = 400 * 86400


def clean(data, now=None):
    """A reading with every number it carries checked: a window whose numbers are out of
    range is dropped, a bad `captured` or credit figure is left out. What is not plainly
    true stays unknown, never zero and never a crash."""
    if not isinstance(data, dict):
        return None
    now = now or time.time()
    out = {}
    for key, value in data.items():
        if key == 'captured':
            if _num(value, 0, now + 300) is not None:   # a reading from the future is not one
                out[key] = value
        elif key == 'credits':
            if isinstance(value, dict):
                out[key] = {k: v for k, v in value.items()
                            if not isinstance(v, (int, float)) or _num(v, -1e12, 1e12) is not None}
        elif isinstance(value, dict) and ('used_percentage' in value or 'resets_at' in value):
            if _num(value.get('used_percentage'), 0, 1000) is not None \
                    and _num(value.get('resets_at'), 0, now + YEAR) is not None:
                out[key] = value
        else:
            out[key] = value
    return out


def reading(account):
    return clean(read_json(paths()['usage'] / f'{account}.json'))


def windows(data, now=None):
    """Current windows of a reading: (name, used percent, resets at). A window whose
    reset has passed says nothing about now and is dropped."""
    now = now or time.time()
    out = []
    for name, value in (data or {}).items():
        if not isinstance(value, dict):
            continue
        used, resets = _num(value.get('used_percentage'), 0, 1000), _num(value.get('resets_at'), 0, now + YEAR)
        if used is not None and resets is not None and resets > now:
            out.append((name, float(used), int(resets)))
    return out


def remaining(data, now=None):
    """Percent left in the tightest current window, or None when nothing is known.
    Credits (OpenRouter) count as remaining share of the limit."""
    if not data:
        return None
    current = windows(data, now)
    if current:
        return max(0.0, 100.0 - max(used for _, used, _ in current))
    credits = data.get('credits')
    if isinstance(credits, dict):
        limit, left = _num(credits.get('limit'), 1e-9, 1e12), _num(credits.get('remaining'), -1e12, 1e12)
        if limit is not None and left is not None:
            return max(0.0, 100.0 * left / limit)
    return None


def describe(data, now=None):
    """One line about a reading, with its age. Never a number that is not there."""
    if not data:
        return 'unknown'
    now = now or time.time()
    parts = []
    for name, used, resets in windows(data, now):
        # a reading is written by agents: only a plain window name is ever repeated
        label = {'five_hour': '5h', 'seven_day': 'week'}.get(name, name if re.fullmatch(r'[a-z0-9_]{1,30}', name) else 'window')
        parts.append(f'{label} {used:.0f}% until {time.strftime("%H:%M", time.localtime(resets))}')
    credits = data.get('credits')
    left = _num(credits.get('remaining'), -1e12, 1e12) if isinstance(credits, dict) else None
    if left is not None:
        parts.append(f'credits {left:.2f} left')
    if not parts:
        parts.append('no current window')
    captured = _num(data.get('captured'), 0, now + 300)
    if captured is not None:
        age = max(0, int(now - captured))
        parts.append(f'read {age // 60}m ago' if age < 7200 else f'read {age // 3600}h ago')
    return ', '.join(parts)


# ---- the resolver ------------------------------------------------------------

# The last choice per provider and the rotation record are root's (the accounts folder,
# root 755): the launcher's resolver runs as root, and what it reads back and repeats in
# the chat must not be a file an agent can point elsewhere. A user's own resolve (tests,
# ai-account as owner) reads them and cannot write there; it records nothing.
NAME = re.compile(r'[a-z0-9][a-z0-9-]{0,40}')


def _last_path(provider, client):
    return paths()['state'] / f'last-{provider}-{client}'


def rotations_path():
    return paths()['state'] / 'rotations.log'


def _record(line):
    try:
        append_line(rotations_path(), line)
    except OSError:
        pass


def _named(data, word):
    """word when it is an account ID in the registry; None for anything else, which is never repeated."""
    return word if word and NAME.fullmatch(word) and word in ids(data) else None


def _say(who, words):
    try:
        append_line(paths()['chat'], f'{time.strftime("%H:%M")} {who} {words}')
    except OSError:
        pass


def within(place, places):
    """Whether a folder is one of the places, or inside one (real paths, whole names)."""
    if not place:
        return False
    real = os.path.realpath(place)
    for p in places:
        root = os.path.realpath(p)
        if real == root or real.startswith(root.rstrip('/') + '/'):
            return True
    return False


def for_place(pool, place):
    """The accounts that may serve work at this place: the ones bound to it, if any, and
    otherwise only the unbound ones. Work in a bound place never falls back."""
    bound = [e for e in pool if e.get('places') and within(place, e['places'])]
    return bound or [e for e in pool if not e.get('places')]


def candidates(data, provider, client, now=None, place=None, anywhere=False):
    """Every account of the provider and kind that could serve this client, with why
    it can or cannot. Kind never crosses: subscriptions are never replaced by API billing.
    An account bound to places serves only work there, and work there only it."""
    pool = [e for e in data['accounts'] if e['provider'] == provider and client in e['clients']]
    if not pool:
        raise Refused(f'no account in the registry serves {client} for {provider}')
    pool = pool if anywhere else for_place(pool, place)
    if not pool:
        raise Refused(f'no {provider} account serves {client} outside the places bound to its accounts')
    default = next((e for e in pool if e.get('default')), pool[0])
    out = []
    for entry in pool:
        row = {'account': entry['id'], 'default': entry is default, 'kind': entry['kind'],
               'billing': billing(entry, client)}
        reading_ = reading(entry['id'])
        left = remaining(reading_, now)
        row['remaining'] = left
        row['usage'] = describe(reading_, now)
        if row['billing'] != billing(default, client):
            row['state'] = 'other billing'
        elif not signed_in(entry['id'], credential_client(entry, client)):
            row['state'] = 'not signed in'
        elif left is not None and left <= 0:
            row['state'] = 'exhausted'
        else:
            row['state'] = 'eligible'
        out.append(row)
    return out


def resolve(data, provider, client, named=None, who=None, now=None, metered_ok=False, place=None):
    """The account a new session gets. Raises Refused with the reason when none can.
    A metered option is used only when named and confirmed for this launch (metered_ok);
    rotation never chooses one. Work at a place bound to accounts gets those by default; a named
    model account is used anywhere (owner, 2026-10-14: any account anywhere, chosen by name). Git
    logins stay bound: client code is pushed only as the client's login, and never the reverse."""
    anywhere = named and provider in MODEL_PROVIDERS
    rows = candidates(data, provider, client, now, place, anywhere=bool(anywhere))
    who = who if who and NAME.fullmatch(who) else None
    if named:
        get(data, named)
        row = next((r for r in rows if r['account'] == named), None)
        if row is None:
            if get(data, named).get('places') or any(get(data, r['account']).get('places') for r in rows):
                raise Refused(f'{named} does not serve work in {place or "this place"}: '
                              f'{client} there uses only {", ".join(r["account"] for r in rows)}')
            raise Refused(f'{named} does not serve {client} for {provider}')
        if row['billing'] == 'metered' and not metered_ok:
            raise Refused(f'{named} through {client} is metered API cost, not a subscription; '
                          'it starts only after a yes for this launch (--metered-ok)')
        if row['state'] == 'other billing' and row['billing'] == 'metered' and metered_ok:
            row = dict(row, state='eligible') if signed_in(named, credential_client(get(data, named), client)) \
                else dict(row, state='not signed in')
        if row['state'] != 'eligible':
            raise Refused(f'{named} is {row["state"]} ({row["usage"]}); named accounts are never substituted')
        chosen, reason = row, 'named' + (', metered, confirmed for this launch' if row['billing'] == 'metered' else '')
    else:
        if all(r['billing'] == 'metered' for r in rows):
            raise Refused(f'{provider} through {client} is metered API cost: never chosen for you; '
                          'name the account and confirm it for this launch (--metered-ok)')
        eligible = [r for r in rows if r['state'] == 'eligible' and r['billing'] != 'metered']
        if not eligible:
            summary = '; '.join(f'{r["account"]} {r["state"]} ({r["usage"]})' for r in rows)
            if who:
                _say(who, f'no {provider} account left for {client}: {summary}')
                _record(f'{datetime.now(timezone.utc).isoformat(timespec="seconds")} {provider}/{client} '
                        f'none left for {who}: {summary}')
            raise Refused(f'no {provider} account left for {client}: {summary}')
        known = sorted((r for r in eligible if r['remaining'] is not None),
                       key=lambda r: (-r['remaining'], not r['default']))
        unknown = sorted((r for r in eligible if r['remaining'] is None), key=lambda r: not r['default'])
        chosen = (known or unknown)[0]
        reason = 'most remaining observed quota' if known else 'no quota observed yet; default first'
    result = {'account': chosen['account'], 'provider': provider, 'client': client, 'reason': reason,
              'usage': chosen['usage'], 'candidates': rows, 'rotated_from': None}
    if get(data, chosen['account']).get('places'):
        return result                                # chosen by place, not rotation: nothing to record
    last = _last_path(provider, client)
    before = _named(data, (read_safe(last, 256) or b'').decode(errors='replace').strip())
    if before and before != chosen['account']:
        prior = next((r for r in rows if r['account'] == before), None)
        why = f'{before} {prior["state"]} ({prior["usage"]})' if prior else f'{before} does not serve {client}'
        result['rotated_from'] = before
        stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
        _record(f'{stamp} {provider}/{client} {before} -> {chosen["account"]} ({reason}; {why}){" for " + who if who else ""}')
        if who:
            _say(who, f'switched {provider} account for {client}: {before} -> {chosen["account"]} ({why})')
    try:
        write_atomic(last, chosen['account'] + '\n', mode=0o644)
    except OSError:
        pass
    return result


def status(data, now=None):
    """Every account and client: signed in as whom, verified, quota and its age."""
    rows = []
    for entry in data['accounts']:
        reading_ = reading(entry['id'])
        for client in (['key'] if entry['kind'] == 'api-key' else entry['clients']):
            record = signin(entry['id'], client) or {}
            rows.append({'account': entry['id'], 'client': client, 'default': bool(entry.get('default')),
                         'kind': entry['kind'],
                         'billing': billing(entry, client),
                         # the provider's name for the login, else the address the owner confirmed
                         'identity': record.get('identity')
                                     or (entry.get('expected_identity') if record.get('verified') else None)
                                     or ('this machine' if entry['kind'] == 'local' else None),
                         'verified': bool(record.get('verified')) or entry['kind'] == 'local',
                         # usable, but the provider could not say whose login it is
                         'identity_checked': bool(record.get('identity_checked', record.get('identity')))
                                             or entry['kind'] == 'local',
                         'checked_at': record.get('checked_at'),
                         'note': record.get('note'),
                         'quota': describe(reading_, now) if entry.get('quota_source') != 'none' else 'not reported',
                         'remaining': remaining(reading_, now)})
    return rows


def table(rows):
    lines = [f'{"ACCOUNT":<17}{"CLIENT":<8}{"BILLING":<14}{"SIGNED IN AS":<34}{"VERIFIED":<10}QUOTA (and how old the reading is)']
    for r in rows:
        never = not r['checked_at'] or r['note'] == 'not signed in'
        who = r['identity'] or ('not signed in' if never else '(not reported)')
        verified = ('yes' if r['identity_checked'] else 'yes (you)') if r['verified'] else \
            ('-' if never else 'NO: ' + (r['note'] or '')[:40])
        # a plan's windows say nothing of a client billed per use on the same account
        quota = 'per use, not the plan' if r.get('billing') == 'metered' and r.get('kind') == 'subscription' \
            else r['quota']
        mark = '*' if r['default'] else ' '
        lines.append(f'{mark}{r["account"]:<16}{r["client"]:<8}{r.get("billing", ""):<14}{who[:33]:<34}{verified:<10}{quota}')
    lines.append('* default for its provider. Unknown quota is not zero. Sign in: ol-login ACCOUNT [CLIENT]')
    if any(r['verified'] and not r['identity_checked'] for r in rows):
        lines.append('yes (you): the login works and you confirmed whose it is at sign-in; the provider does not report it')
    return '\n'.join(lines)


# ---- the owner's launch choice: harness first, then provider and account ----------------

HARNESSES = (('claude', 'Claude Code'), ('codex', 'Codex'), ('pi', 'Pi'), ('local', 'This machine\'s model'))


def options(data, now=None):
    """Every way a role can be started, for the menus: harness, then each account that serves
    it with its billing and state. Metered options are listed, marked, never preselected."""
    out = []
    for client, label in HARNESSES:
        rows = []
        for provider in dict.fromkeys(e['provider'] for e in data['accounts'] if client in e['clients']):
            try:
                found = candidates(data, provider, client, now)
            except Refused:
                continue
            for r in found:
                rows.append(dict(r, provider=provider))
        if rows:
            out.append({'harness': client, 'label': label, 'accounts': rows})
    return out
