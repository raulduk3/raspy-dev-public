"""Read-only native adapters. Each reads minimal metadata and never writes native storage.

An adapter yields Source objects; a source that raises is reported as an error and its
existing index entries are left untouched.
"""
import json
from pathlib import Path
import sqlite3
import time

HEADER_LINES = 40
HEADER_BYTES = 256 * 1024


class Source:
    def __init__(self, key, runtime, store, owner, read):
        self.key, self.runtime, self.store, self.owner, self.read = key, runtime, store, owner, read


def _rec(native_id, cwd=None, title=None, branch=None, updated_at=None, extra=None):
    if not isinstance(native_id, (str, int)) or isinstance(native_id, bool):
        raise ValueError('unsupported native identifier')
    # Native metadata can be malformed. Never copy nested prompt/request objects through
    # a field that normally contains a scalar title, path, date or identifier.
    scalar = lambda value: value if value is None or isinstance(value, (str, int, float, bool)) else None
    text = lambda value: value if isinstance(value, str) else None
    return {'native_id': str(native_id), 'cwd': text(cwd), 'title': text(title), 'branch': text(branch),
            'updated_at': scalar(updated_at),
            'native': {key: scalar(value) for key, value in (extra or {}).items()}}


def read_codex(codex_home):
    if not codex_home.is_dir():
        raise FileNotFoundError('native store unavailable')
    dbs = sorted(codex_home.glob('state_*.sqlite'), key=lambda p: p.stat().st_mtime)
    if dbs:
        conn = sqlite3.connect(f'file:{dbs[-1]}?mode=ro', uri=True)
        try:
            cols = {row[1] for row in conn.execute('PRAGMA table_info(threads)')}
            if not {'id', 'cwd', 'updated_at'} <= cols:
                raise RuntimeError('codex threads schema not recognized')
            wanted = [c for c in ('id', 'rollout_path', 'cwd', 'title', 'name', 'git_branch', 'archived', 'updated_at') if c in cols]
            for row in conn.execute(f"SELECT {', '.join(wanted)} FROM threads ORDER BY updated_at DESC"):
                r = dict(zip(wanted, row))
                yield _rec(r['id'], r.get('cwd'), r.get('title') or r.get('name'), r.get('git_branch'),
                           r.get('updated_at'), extra={'archived': bool(r.get('archived')), 'rollout_path': r.get('rollout_path')})
        finally:
            conn.close()
        return
    index = codex_home / 'session_index.jsonl'
    if not index.exists():
        raise FileNotFoundError('native metadata unavailable')
    with index.open() as handle:
        for line in handle:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get('id'):
                yield _rec(r['id'], None, r.get('thread_name') or r.get('title'), None, r.get('updated_at'))


def _claude_header(path):
    found = {}
    with path.open('rb') as handle:
        data = handle.read(HEADER_BYTES)
    for line in data.splitlines()[:HEADER_LINES]:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict):
            continue
        for key in ('sessionId', 'cwd', 'gitBranch', 'timestamp', 'customTitle'):
            if isinstance(r.get(key), str) and key not in found:
                found[key] = r[key]
    return found


def read_claude(claude_home, map_path=None):
    if not (claude_home / 'projects').is_dir():
        raise FileNotFoundError('native store unavailable')
    seen = set()
    for index in sorted(claude_home.glob('projects/*/sessions-index.json')):
        entries = json.loads(index.read_text()).get('entries', [])
        for e in entries:
            if isinstance(e, dict) and e.get('sessionId'):
                seen.add(e['sessionId'])
                if isinstance(e.get('fullPath'), str) and e['fullPath']:
                    path = Path(e['fullPath'])
                    if not path.is_absolute():
                        path = index.parent / path
                else:
                    path = index.parent / f"{e['sessionId']}.jsonl"
                if map_path is not None and isinstance(e.get('fullPath'), str) and Path(e['fullPath']).is_absolute():
                    path = map_path(path)
                yield _rec(e['sessionId'], e.get('projectPath'), e.get('customTitle'), e.get('gitBranch'),
                           e.get('modified'), extra={'sidechain': bool(e.get('isSidechain')),
                           'index_path': str(index), 'transcript_path': str(path),
                           'transcript_missing': not path.is_file()})
    for path in sorted(claude_home.glob('projects/*/*.jsonl')):
        if path.stem in seen:
            continue
        h = _claude_header(path)
        if h.get('sessionId') == path.stem:
            yield _rec(path.stem, h.get('cwd'), h.get('customTitle'), h.get('gitBranch'), h.get('timestamp'),
                       extra={'transcript_path': str(path), 'transcript_missing': False})


def _pi_header(path):
    found = {}
    with path.open('rb') as handle:
        data = handle.read(HEADER_BYTES)
    for line in data.splitlines()[:HEADER_LINES]:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict):
            continue
        if r.get('type') == 'session':
            found.setdefault('id', r.get('id'))
            found.setdefault('cwd', r.get('cwd'))
        elif r.get('type') == 'model_change':
            found.setdefault('model', f"{r.get('provider')}/{r.get('modelId')}")
        elif r.get('type') == 'custom' and r.get('customType') == 'dev-platform-binding' and isinstance(r.get('data'), dict):
            found.setdefault('account', r['data'].get('accountRef'))
        elif r.get('type') == 'session_info' and isinstance(r.get('name'), str):
            found['title'] = r['name']
    return found


def pi_roots(home):
    """Where Pi sessions live in one home: Pi's own store, the platform's conversation
    homes, and conversations imported from the old machine (read-only history)."""
    home = Path(home)
    return [(home / '.pi/agent/sessions', 'pi:default', False),
            (home / '.local/state/dev-platform/sessions/conversations', 'pi:conversations', False),
            (home / 'memory/old/conversations', 'pi:old', True)]


def read_pi(root, archived=False):
    if not root.is_dir():
        raise FileNotFoundError('native store unavailable')
    for path in sorted(root.rglob('*.jsonl')):
        if path.is_symlink() or not path.is_file() or len(path.relative_to(root).parts) > 4:
            continue
        h = _pi_header(path)
        if not h.get('id'):
            continue
        conversation = next((part for part in path.parts if part.startswith('conversation-')), None)
        stamp = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(path.stat().st_mtime)) + 'Z'
        yield _rec(h['id'], h.get('cwd'), h.get('title'), None, stamp,
                   extra={'transcript_path': str(path), 'transcript_missing': False, 'model': h.get('model'),
                          'account': h.get('account'), 'conversation': conversation, 'archived': archived})


def discover(home=None, previous=None):
    home = Path(home or Path.home())
    sources = []
    if (home / '.codex').is_dir():
        sources.append(Source('codex:default', 'codex', str(home / '.codex'), 'user',
                              lambda: read_codex(home / '.codex')))
    for root, key, archived in pi_roots(home):
        if root.is_dir():
            sources.append(Source(key, 'pi', str(root), 'user', lambda r=root, a=archived: read_pi(r, a)))
    if (home / '.claude/projects').is_dir():
        sources.append(Source('claude:default', 'claude', str(home / '.claude'), 'user',
                              lambda: read_claude(home / '.claude')))
    # Read only the non-secret account registry, never authentication files. A
    # configured profile is a history locator, not proof of the current login.
    registry = home / '.config/dev-platform/accounts.json'
    if registry.exists():
        try:
            from .accounts import load, IDS, runtime
            bindings = load(registry)['bindings']
            known = {(s.runtime, str(Path(s.store).resolve())) for s in sources}
            for account, binding in sorted(bindings.items()):
                if account not in IDS or account == 'zai':
                    continue
                if not isinstance(binding, dict) or not isinstance(binding.get('home'), str):
                    raise ValueError('invalid native profile locator')
                path = Path(binding['home'])
                if not path.is_absolute():
                    raise ValueError('native profile locator must be absolute')
                native_runtime = runtime(account)
                locator = (native_runtime, str(path.resolve()))
                if locator in known:
                    continue
                known.add(locator)
                reader = read_codex if native_runtime == 'codex' else read_claude
                def read_profile(p=path, read=reader):
                    for record in read(p):
                        record['native']['isolated_profile'] = True
                        yield record
                sources.append(Source(f'{native_runtime}:account:{account}', native_runtime,
                                      str(path), 'user', read_profile))
        except (ValueError, TypeError, AttributeError, OSError):
            def invalid_registry():
                raise ValueError('account registry unavailable or malformed')
            sources.append(Source('accounts:registry', 'registry', str(registry), 'user', invalid_registry))
    # A vanished previously indexed store is unavailable, not an empty successful scan.
    keys = {s.key for s in sources}
    for key, old in (previous or {}).items():
        if key in keys:
            continue
        if not all(old.get(k) for k in ('runtime', 'store', 'owner')):
            continue
        def unavailable():
            raise FileNotFoundError('previous native source unavailable')
        sources.append(Source(key, old['runtime'], old['store'], old['owner'], unavailable))
    return sources
