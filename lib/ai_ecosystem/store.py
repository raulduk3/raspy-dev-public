"""Filesystem session index: versioned manifests, Markdown handoffs, append-only events.

Layout under the state root:
  manifests/<id>.json   one manifest per session, replaced atomically
  handoffs/<id>.md      user-authored handoff
  events/<id>/*.json    immutable event files with unique names
  locks/<id>.lock       per-session flock
  sources.json          last scan result per native source
Temporary files start with '.' and are ignored by readers.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

VERSION = 1
ID_RE = re.compile(r'^[a-z]+-[0-9a-f]{20}$')
MAX_HANDOFF = 64 * 1024


class RevisionConflict(Exception):
    pass


def default_root():
    return Path(os.environ.get('AI_SESSION_STATE') or Path.home() / '.local/state/dev-platform/sessions')


def session_id(runtime, store, native_id):
    digest = hashlib.sha256(f'{runtime}\0{store}\0{native_id}'.encode()).hexdigest()[:20]
    return f'{runtime}-{digest}'


def check_id(sid):
    if not isinstance(sid, str) or not ID_RE.match(sid):
        raise ValueError(f'invalid session id: {sid!r}')
    return sid


class Store:
    def __init__(self, root=None):
        self.root = Path(root) if root else default_root()
        for sub in ('manifests', 'handoffs', 'events', 'locks'):
            (self.root / sub).mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)

    def _write_atomic(self, path, data):
        tmp = path.parent / f'.{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp'
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, 'w') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)

    @contextlib.contextmanager
    def lock(self, sid):
        fd = os.open(self.root / 'locks' / f'{check_id(sid)}.lock', os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def get(self, sid):
        path = self.root / 'manifests' / f'{check_id(sid)}.json'
        try:
            data = json.loads(path.read_text())
        except (FileNotFoundError, ValueError):
            return None
        return data if data.get('version') == VERSION else None

    def all(self):
        out = []
        for path in sorted((self.root / 'manifests').glob('*.json')):
            if path.name.startswith('.') or not ID_RE.match(path.stem):
                continue
            item = self.get(path.stem)
            if item:
                out.append(item)
        return out

    def put(self, manifest, expect_revision=None):
        """Write under the caller's lock; bumps revision, fails on a stale expectation."""
        current = self.get(manifest['id'])
        revision = current['revision'] if current else 0
        if expect_revision is not None and expect_revision != revision:
            raise RevisionConflict(f'revision is {revision}, expected {expect_revision}')
        manifest = dict(manifest, version=VERSION, revision=revision + 1)
        self._write_atomic(self.root / 'manifests' / f"{manifest['id']}.json",
                           json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        return manifest

    def event(self, sid, kind, **fields):
        folder = self.root / 'events' / check_id(sid)
        folder.mkdir(exist_ok=True, mode=0o700)
        name = f'{time.time_ns():020d}-{os.getpid()}-{uuid.uuid4().hex[:12]}.json'
        self._write_atomic(folder / name,
                           json.dumps(dict(fields, kind=kind, at=time.time()), sort_keys=True) + '\n')

    def events(self, sid):
        folder = self.root / 'events' / check_id(sid)
        return [json.loads(p.read_text()) for p in sorted(folder.glob('[0-9]*.json'))] if folder.is_dir() else []

    def read_handoff(self, sid):
        path = self.root / 'handoffs' / f'{check_id(sid)}.md'
        return path.read_text() if path.exists() else None

    def write_handoff(self, sid, text, expect_revision):
        if len(text.encode()) > MAX_HANDOFF:
            raise ValueError(f'handoff exceeds {MAX_HANDOFF} bytes')
        with self.lock(sid):
            manifest = self.get(sid)
            if manifest is None:
                raise KeyError(sid)
            manifest = self.put(dict(manifest, has_handoff=True), expect_revision)
            self._write_atomic(self.root / 'handoffs' / f'{sid}.md', text)
            self.event(sid, 'handoff', revision=manifest['revision'])
            return manifest

    def sources(self):
        try:
            return json.loads((self.root / 'sources.json').read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def save_sources(self, data):
        self._write_atomic(self.root / 'sources.json', json.dumps(data, indent=2, sort_keys=True) + '\n')
