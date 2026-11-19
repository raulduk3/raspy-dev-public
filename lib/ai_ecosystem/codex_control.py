"""Name a Codex thread through the app-server control socket (`thread/name/set`).

The Codex app-server daemon listens on `$CODEX_HOME/app-server-control/app-server-control.sock`.
The socket speaks WebSocket and JSON-RPC. This is the supported rename path: it is what the
TUI `/rename` command and the desktop app call. Nothing here writes SQLite or the session index.
Reads of the thread table are read-only and only classify the thread.
"""
import base64
import json
import os
import re
from pathlib import Path
import socket
import sqlite3
import struct

from . import naming

TIMEOUT = 5


def codex_home():
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')


def socket_path(home=None):
    return (Path(home) if home else codex_home()) / 'app-server-control' / 'app-server-control.sock'


class Control:
    """One short WebSocket session to the app-server: initialize, then requests."""

    def __init__(self, sock_path=None, timeout=TIMEOUT):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(timeout)
        self.sock.connect(str(sock_path or socket_path()))
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(('GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        head = b''
        while b'\r\n\r\n' not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError('app-server closed the connection')
            head += chunk
        head, self.buffer = head.split(b'\r\n\r\n', 1)
        if b' 101 ' not in head.split(b'\r\n', 1)[0]:
            raise ConnectionError('app-server refused the WebSocket upgrade')
        self.next_id = 0
        self.request('initialize', {'clientInfo': {'name': 'ai-title', 'title': 'dev-platform session naming',
                                                   'version': '1'}})
        self.send({'method': 'initialized'})

    def _read(self, count):
        while len(self.buffer) < count:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError('app-server closed the connection')
            self.buffer += chunk
        data, self.buffer = self.buffer[:count], self.buffer[count:]
        return data

    def _frame(self):
        """Next complete text message (control frames are answered or skipped)."""
        message = b''
        while True:
            first, second = self._read(2)
            length = second & 0x7f
            if length == 126:
                length = struct.unpack('>H', self._read(2))[0]
            elif length == 127:
                length = struct.unpack('>Q', self._read(8))[0]
            payload = self._read(length)       # a server frame is never masked
            opcode = first & 0x0f
            if opcode == 8:
                raise ConnectionError('app-server closed the WebSocket')
            if opcode == 9:
                self._write(10, payload)
                continue
            if opcode in (1, 0):
                message += payload
                if first & 0x80:
                    return message.decode()

    def _write(self, opcode, payload):
        mask = os.urandom(4)
        n = len(payload)
        head = bytes([0x80 | opcode]) + (bytes([0x80 | n]) if n < 126 else
                                         bytes([0x80 | 126]) + struct.pack('>H', n) if n < 65536 else
                                         bytes([0x80 | 127]) + struct.pack('>Q', n))
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send(self, message):
        self._write(1, json.dumps(message).encode())

    def request(self, method, params):
        self.next_id += 1
        self.send({'id': self.next_id, 'method': method, 'params': params})
        while True:
            reply = json.loads(self._frame())
            if reply.get('id') == self.next_id and ('result' in reply or 'error' in reply):
                if 'error' in reply:
                    raise RuntimeError(f"{method}: {reply['error'].get('message', reply['error'])}")
                return reply['result']

    def close(self):
        try:
            self._write(8, b'')
        except OSError:
            pass
        self.sock.close()


def set_thread_name(thread_id, name, sock_path=None):
    control = Control(sock_path)
    try:
        control.request('thread/name/set', {'threadId': thread_id, 'name': name})
    finally:
        control.close()


def trust_hooks(command_part, cwd='/', sock_path=None):
    """Trust the user hooks whose command contains `command_part`, as the Codex hook review does.

    Codex runs a hook only after its hash is in `[hooks.state."KEY"]` of config.toml. The write goes
    through the app-server's own config writer, with the hash Codex computed (`currentHash`).
    Returns the keys trusted now."""
    control = Control(sock_path)
    try:
        listing = control.request('hooks/list', {'cwds': [cwd]})
        edits = []
        for entry in listing.get('data', []):
            for hook in entry.get('hooks', []):
                if command_part in (hook.get('command') or '') and hook.get('trustStatus') != 'trusted':
                    edits.append({'keyPath': f'hooks.state."{hook["key"]}".trusted_hash', 'mergeStrategy': 'replace',
                                  'value': hook['currentHash']})
        if edits:
            control.request('config/batchWrite', {'edits': edits, 'reloadUserConfig': True})
        return [edit['keyPath'] for edit in edits]
    finally:
        control.close()


def thread_row(thread_id, home=None):
    """Read-only facts about a thread from Codex's own state database, or None."""
    db = (Path(home) if home else codex_home()) / 'state_5.sqlite'
    try:
        conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=2)
    except sqlite3.Error:
        return None
    try:
        conn.row_factory = sqlite3.Row
        return conn.execute('select source, thread_source, originator, name, model, model_provider, cwd, '
                            'first_user_message, created_at, git_branch from threads where id = ?', (thread_id,)).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def client_of(source, originator=None):
    """Title client from the thread's `source` (and `originator` for the desktop app)."""
    source = source or ''
    if source.startswith('{'):
        return 'codex-app' if originator == 'Codex Desktop' else 'codex-cli'
    if source == 'exec':
        return 'codex-exec'
    if source == 'cli':
        return 'codex-cli'
    if source == 'vscode':
        return 'codex-app' if originator == 'Codex Desktop' else 'codex-vscode'
    return 'codex-cli'


def spawn_of(source):
    """The `thread_spawn` facts of a subagent thread (parent, agent path, nickname), or None."""
    try:
        spawn = json.loads(source).get('subagent', {}).get('thread_spawn') if (source or '').startswith('{') else None
    except (ValueError, AttributeError):
        return None
    return spawn if isinstance(spawn, dict) else None


def subagent_part(spawn, home=None):
    """(what, who) for a spawned thread, from data only: its agent path, nickname and parent.

    `/root/splash_audit` by Jason under a `fix(web): ...` parent gives
    `review(splash): Splash audit` and `jason@web`."""
    words = ' '.join(re.split(r'[_\-\s]+', str(spawn.get('agent_path') or '').rstrip('/').rsplit('/', 1)[-1])).strip()
    if not words:
        return None
    purpose, area = naming.infer_purpose(words, default='research')
    parent_id = str(spawn.get('parent_thread_id') or '')
    parent = thread_row(parent_id, home) if parent_id else None
    part = naming.contextual_part(parent['name'] if parent else '')
    owner = naming.WHAT.match(part[0])['area'] if part else naming.token(parent_id[:8], 'parent')
    nickname = naming.token(str(spawn.get('agent_nickname') or 'worker').lower(), 'worker')
    return f'{purpose}({area}): {words[0].upper()}{words[1:]}', f'{nickname}@{owner}'


def type_of(source, thread_source=None):
    if (source or '').startswith('{') or thread_source in ('subagent', 'guardian_review'):
        return 'subagent'
    if source == 'exec':
        return os.environ.get('DEV_SESSION_TYPE') or 'headless'
    return os.environ.get('DEV_SESSION_TYPE') or 'interactive'


def title_for(thread_id, what, row=None, cwd=None, home=None, model=None, who=None):
    row = row if row is not None else thread_row(thread_id, home)
    source = row['source'] if row else ''
    originator = row['originator'] if row else None
    provider = os.environ.get('DEV_SESSION_PROVIDER') or (row['model_provider'] if row and row['model_provider'] else 'openai')
    created = row['created_at'] if row else None
    return naming.format_title(
        what, client=client_of(source, originator), cwd=cwd or (row['cwd'] if row else None), who=who,
        provider=provider, model=os.environ.get('DEV_SESSION_MODEL') or model or (row['model'] if row else None),
        kind=type_of(source, row['thread_source'] if row else None), date=created and created * 1000,
        branch=row['git_branch'] if row else None)
