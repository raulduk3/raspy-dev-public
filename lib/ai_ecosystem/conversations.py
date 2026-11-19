"""Durable conversation associations over the existing native session index."""
import json
from pathlib import Path
from . import workspace as projects
import re
import time
import uuid

CONVERSATION = re.compile(r'^conversation-[0-9a-f]{20}$')
REFERENCE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$')
SLUG = re.compile(r'^[a-z0-9][a-z0-9._-]{0,119}$')
SCHEMA = 'dev-platform.conversation.v1'


def slugify(text, fallback='conversation'):
    slug = re.sub(r'[^a-z0-9._-]+', '-', text.strip().casefold())
    slug = re.sub(r'-+', '-', slug).strip('-._')
    return (slug or fallback)[:80].strip('-._') or fallback


def safe_segment(text, fallback='scope'):
    return slugify(str(text).replace('/', '__'), fallback)


def resolve_id(store, reference):
    if CONVERSATION.fullmatch(reference):
        return reference
    if not SLUG.fullmatch(reference):
        raise ValueError('invalid conversation identifier')
    path = store.root / 'work' / 'conversations' / reference / 'ref.json'
    if path.is_symlink():
        raise ValueError('conversation reference cannot be a symlink')
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise ValueError('conversation not found') from None
    if not isinstance(data, dict) or not CONVERSATION.fullmatch(data.get('id') or ''):
        raise ValueError('invalid conversation reference')
    return data['id']


def path_for(store, identifier):
    identifier = resolve_id(store, identifier)
    root = store.root / 'conversations'
    if root.is_symlink():
        raise ValueError('conversation root cannot be a symlink')
    folder = root / identifier
    if folder.is_symlink():
        raise ValueError('conversation home cannot be a symlink')
    return folder


def _manifest_path(store, identifier):
    folder = path_for(store, identifier)
    preferred = folder / 'conversation.json'
    if preferred.exists():
        return preferred
    return folder / 'session.json'


def read(store, identifier):
    identifier = resolve_id(store, identifier)
    path = _manifest_path(store, identifier)
    if path.is_symlink():
        raise ValueError('conversation manifest cannot be a symlink')
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise ValueError('conversation not found') from None
    if not isinstance(data, dict):
        raise ValueError('invalid conversation manifest')
    if data.get('version') != 1 or data.get('id') != identifier:
        raise ValueError('unsupported conversation manifest')
    if data.get('schema') not in (None, SCHEMA):
        raise ValueError('unsupported conversation manifest')
    return data


def _unique_slug(store, base):
    root = store.root / 'work' / 'conversations'
    candidate = base
    suffix = 2
    while (root / candidate).exists():
        candidate = f'{base[:72]}-{suffix}'
        suffix += 1
    return candidate


def _write_ref(store, folder, conversation):
    if folder.is_symlink():
        raise ValueError('conversation view cannot be a symlink')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    ref = {
        'schema': 'dev-platform.conversation-ref.v1',
        'id': conversation['id'],
        'slug': conversation['slug'],
        'title': conversation['title'],
        'agent': conversation['agent'],
        'scope': conversation['scope'],
        'home': str(path_for(store, conversation['id'])),
    }
    store._write_atomic(folder / 'ref.json', json.dumps(ref, indent=2, sort_keys=True) + '\n')


def _sync_views(store, conversation):
    slug = conversation['slug']
    _write_ref(store, store.root / 'work' / 'conversations' / slug, conversation)
    _write_ref(store, store.root / 'work' / 'agents' / conversation['agent'] / slug, conversation)
    scope = conversation['scope']
    if scope['kind'] == 'project':
        _write_ref(store, store.root / 'work' / 'projects' / safe_segment(scope['project_id'], 'project') / slug, conversation)
    elif scope['kind'] == 'formation':
        _write_ref(store, store.root / 'work' / 'formations' / slug, conversation)
    elif scope['kind'] == 'system':
        _write_ref(store, store.root / 'work' / 'resources' / safe_segment(scope['resource'], 'resource') / slug, conversation)
    else:
        _write_ref(store, store.root / 'work' / 'personal' / conversation['agent'] / slug, conversation)


def _readme(conversation):
    return (f"# {conversation['title']}\n\n"
            f"- Conversation: `{conversation['id']}`\n"
            f"- Name: `{conversation['slug']}`\n"
            f"- Agent: `{conversation['agent']}`\n"
            f"- Scope: `{conversation['scope']['kind']}`\n\n"
            "Native transcripts stay in their owning runtime stores. This folder holds "
            "the platform envelope, handoff, native-session references and local artifacts.\n")


def ensure_envelope(store, conversation):
    """Materialize the filesystem envelope for old and new conversation records."""
    folder = path_for(store, conversation['id'])
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if 'slug' not in conversation:
        stamp = time.strftime('%Y-%m-%d', time.localtime(conversation.get('created_at', time.time())))
        base = slugify(f"{conversation.get('agent', 'agent')}-{stamp}-{conversation.get('title', conversation['id'])}")
        conversation = dict(conversation, slug=_unique_slug(store, base), schema=SCHEMA, native_sessions=[])
    else:
        conversation = dict(conversation, schema=conversation.get('schema', SCHEMA),
                            native_sessions=conversation.get('native_sessions', []))
    if not (folder / 'handoff.md').exists():
        store._write_atomic(folder / 'handoff.md', '# Checkpoint\n\nNo work recorded yet.\n')
    for child in ('native', 'native/pi', 'sessions', 'events', 'artifacts', 'worktrees'):
        (folder / child).mkdir(exist_ok=True, mode=0o700)
    store._write_atomic(folder / 'README.md', _readme(conversation))
    payload = json.dumps(conversation, indent=2, sort_keys=True) + '\n'
    store._write_atomic(folder / 'conversation.json', payload)
    store._write_atomic(folder / 'session.json', payload)
    _sync_views(store, conversation)
    return conversation


def create(store, agent, title, project=None, workspace=None, resource=None, formation=False, repos=None, name=None):
    if agent not in ('assistant', 'engineer', 'ops'):
        raise ValueError('unknown agent')
    if not title.strip() or len(title) > 200:
        raise ValueError('title must contain 1 to 200 characters')
    if name is not None and not SLUG.fullmatch(name):
        raise ValueError('name must be a lowercase filesystem slug')
    if formation and project:
        raise ValueError('choose an existing project or project formation')
    if bool(project or formation) != bool(workspace):
        raise ValueError('project scope requires a project or formation and workspace')
    if (project or formation) and resource:
        raise ValueError('choose project or system scope, not both')
    if agent == 'assistant' and (project or workspace or resource or formation):
        raise ValueError('Assistant conversations have personal scope')
    if agent == 'engineer' and not (project or formation):
        raise ValueError('Engineer requires a project identity and real workspace')
    if agent == 'ops' and not (project or formation or resource):
        raise ValueError('Ops requires an explicit system resource or project')
    if project or formation:
        cwd = Path(workspace).expanduser().resolve(strict=True)
        if not cwd.is_dir():
            raise ValueError('workspace must be a directory')
        if formation:
            scope = {'kind': 'formation'}
        else:
            catalog, _ = projects.catalog(Path(repos) if repos else Path.home() / '.config/dev-platform/repos.conf')
            selected = projects.find_project(catalog, project)
            if not selected['available'] or projects.identity(cwd) != selected['common_dir']:
                raise ValueError('workspace does not belong to the selected catalog project')
            scope = {'kind': 'project', 'project_id': selected['id']}
        binding = {'workspace': str(cwd)}
    elif resource:
        if not REFERENCE.fullmatch(resource):
            raise ValueError('invalid system resource reference')
        scope, binding = {'kind': 'system', 'resource': resource}, {}
    else:
        scope, binding = {'kind': 'personal'}, {}
    identifier = 'conversation-' + uuid.uuid4().hex[:20]
    base = name or slugify(f'{agent}-{time.strftime("%Y-%m-%d")}-{title}')
    slug = _unique_slug(store, base)
    folder = path_for(store, identifier)
    folder.mkdir(parents=True, mode=0o700)
    data = dict(version=1, schema=SCHEMA, id=identifier, slug=slug, agent=agent, title=title,
                scope=scope, binding=binding, created_at=time.time(), native_sessions=[])
    # session.json is the legacy creation commit marker; conversation.json is the canonical envelope.
    store._write_atomic(folder / 'handoff.md', '# Checkpoint\n\nNo work recorded yet.\n')
    for child in ('native', 'native/pi', 'sessions', 'events', 'artifacts', 'worktrees'):
        (folder / child).mkdir(mode=0o700)
    return ensure_envelope(store, data)


def _write_session_ref(store, conversation, native):
    folder = path_for(store, conversation['id']) / 'sessions'
    folder.mkdir(exist_ok=True, mode=0o700)
    fields = ['id', 'runtime', 'store', 'source', 'owner', 'native_id', 'cwd', 'title', 'title_override',
              'branch', 'updated_at', 'status', 'missing', 'revision', 'conversation_id']
    data = {'schema': 'dev-platform.native-session-ref.v1'}
    data.update({key: native[key] for key in fields if key in native})
    store._write_atomic(folder / f"{native['id']}.json", json.dumps(data, indent=2, sort_keys=True) + '\n')


def _update_native_refs(store, conversation):
    natives = [m for m in store.all() if m.get('conversation_id') == conversation['id']]
    refs = [{'id': m['id'], 'runtime': m.get('runtime'), 'native_id': m.get('native_id'),
             'cwd': m.get('cwd'), 'owner': m.get('owner'), 'status': m.get('status')}
            for m in natives]
    updated = dict(conversation, native_sessions=refs)
    payload = json.dumps(updated, indent=2, sort_keys=True) + '\n'
    folder = path_for(store, conversation['id'])
    store._write_atomic(folder / 'conversation.json', payload)
    store._write_atomic(folder / 'session.json', payload)
    for native in natives:
        _write_session_ref(store, updated, native)
    _sync_views(store, updated)
    return updated


def bind(store, identifier, native_id, expected_revision):
    conversation = ensure_envelope(store, read(store, identifier))
    with store.lock(native_id):
        native = store.get(native_id)
        if native is None:
            raise ValueError('native session is not indexed')
        if conversation['scope']['kind'] in ('project', 'formation'):
            observed = native.get('cwd')
            expected = Path(conversation['binding']['workspace'])
            if not observed:
                raise ValueError('native session has no observed workspace')
            actual = Path(observed).expanduser().resolve()
            if conversation['scope']['kind'] == 'project':
                common = projects.identity(expected)
                matches = common is not None and projects.identity(actual) == common
            else:
                matches = actual == expected or expected in actual.parents
            if not matches:
                raise ValueError('native session workspace does not match conversation scope')
        previous = native.get('conversation_id')
        if previous and previous != conversation['id']:
            raise ValueError('native session already belongs to another conversation')
        result = store.put(dict(native, conversation_id=conversation['id']), expected_revision)
        store.event(native_id, 'conversation-bound', conversation_id=conversation['id'],
                    revision=result['revision'])
        _write_session_ref(store, conversation, result)
    _update_native_refs(store, conversation)
    return result


def show(store, identifier):
    data = _update_native_refs(store, ensure_envelope(store, read(store, identifier)))
    natives = [m for m in store.all() if m.get('conversation_id') == data['id']]
    return dict(data, home=str(path_for(store, data['id'])), native_sessions=natives,
                work_home=str(store.root / 'work' / 'conversations' / data['slug']))


def list_conversations(store):
    root = store.root / 'conversations'
    if root.is_symlink():
        raise ValueError('conversation root cannot be a symlink')
    return [ensure_envelope(store, read(store, folder.name)) for folder in sorted(root.glob('conversation-*'))
            if CONVERSATION.fullmatch(folder.name) and ((folder / 'conversation.json').exists() or (folder / 'session.json').exists())]
