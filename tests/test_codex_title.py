"""Codex session naming: control client, thread classification and the hook."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import struct
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
sys.path.insert(0, str(ROOT / 'hooks'))
from ai_ecosystem import codex_control, naming  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location('codex_session_title', ROOT / 'hooks/codex-session-title.py')
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def make_home(tmp, rows):
    db = sqlite3.connect(tmp / 'state_5.sqlite')
    db.execute('create table threads (id text, source text, thread_source text, originator text, name text, '
               'model text, model_provider text, cwd text, first_user_message text, created_at integer, git_branch text)')
    for row in rows:
        db.execute('insert into threads values (?,?,?,?,?,?,?,?,?,?,?)', row)
    db.commit()
    db.close()


class FakeServer(threading.Thread):
    """Just enough of the app-server: WebSocket upgrade, then JSON-RPC replies."""
    def __init__(self, path):
        super().__init__(daemon=True)
        self.server = socket.socket(socket.AF_UNIX)
        self.server.bind(str(path))
        self.server.listen(1)
        self.requests = []

    def read(self, conn, n):
        data = b''
        while len(data) < n:
            data += conn.recv(n - len(data))
        return data

    def run(self):
        conn, _ = self.server.accept()
        head = b''
        while b'\r\n\r\n' not in head:
            head += conn.recv(4096)
        key = [l.split(b': ')[1] for l in head.split(b'\r\n') if l.lower().startswith(b'sec-websocket-key')][0]
        accept = base64.b64encode(hashlib.sha1(key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
        conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                     b'Sec-WebSocket-Accept: ' + accept + b'\r\n\r\n')
        while True:
            first, second = self.read(conn, 2)
            if first & 0x0f == 8:
                return
            length = second & 0x7f
            if length == 126:
                length = struct.unpack('>H', self.read(conn, 2))[0]
            mask = self.read(conn, 4)
            body = bytes(b ^ mask[i % 4] for i, b in enumerate(self.read(conn, length)))
            message = json.loads(body)
            self.requests.append(message)
            if 'id' in message:
                reply = json.dumps({'id': message['id'], 'result': {}}).encode()
                conn.sendall(bytes([0x81, len(reply)]) + reply if len(reply) < 126
                             else bytes([0x81, 126]) + struct.pack('>H', len(reply)) + reply)


class CodexTitle(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for name in ('DEV_SESSION_WHO', 'DEV_SESSION_PROVIDER', 'DEV_SESSION_MODEL', 'DEV_SESSION_TYPE'):
            os.environ.pop(name, None)

    def test_client_and_type_come_from_the_thread_source(self):
        self.assertEqual(codex_control.client_of('cli'), 'codex-cli')
        self.assertEqual(codex_control.client_of('exec'), 'codex-exec')
        self.assertEqual(codex_control.client_of('vscode'), 'codex-vscode')
        self.assertEqual(codex_control.client_of('vscode', 'Codex Desktop'), 'codex-app')
        self.assertEqual(codex_control.type_of('exec'), 'headless')
        self.assertEqual(codex_control.type_of('cli'), 'interactive')
        self.assertEqual(codex_control.type_of('{"subagent":{"other":"guardian"}}'), 'subagent')

    def test_the_control_names_a_thread_over_the_socket(self):
        sock = self.tmp / 's.sock'
        server = FakeServer(sock)
        server.start()
        codex_control.set_thread_name('t1', 'x', sock)
        server.join(5)
        methods = [r['method'] for r in server.requests]
        self.assertEqual(methods, ['initialize', 'initialized', 'thread/name/set'])
        self.assertEqual(server.requests[2]['params'], {'threadId': 't1', 'name': 'x'})

    def test_the_hook_names_a_new_exec_thread_from_its_prompt(self):
        make_home(self.tmp, [('t1', 'exec', 'user', 'codex_exec', '', 'gpt-5-codex', 'openai', str(ROOT),
                              'Fix the login bug', 1793977732, None)])
        calls = []
        title = hook.run({'session_id': 't1', 'hook_event_name': 'UserPromptSubmit', 'prompt': 'Fix the login bug\nmore',
                          'cwd': str(ROOT)}, self.tmp, lambda *a: calls.append(a))
        self.assertEqual(calls[0][:2], ('t1', title))
        self.assertEqual(naming.problems(title), [])
        fields = naming.parse(title)
        self.assertEqual((fields['client'], fields['type'], fields['model'], fields['purpose']),
                         ('codex-exec', 'headless', 'openai/gpt-5-codex', 'fix'))

    def test_the_hook_keeps_good_titles_resumed_threads_and_other_events(self):
        good = naming.format_title('fix(ui): Keep me', client='codex-cli', who='owner', model='gpt-5', provider='openai')
        make_home(self.tmp, [('t1', 'cli', 'user', None, good, 'gpt-5', 'openai', str(ROOT), 'x', 1793977732, None),
                             ('t2', 'cli', 'user', None, 'Old plain name', 'gpt-5', 'openai', str(ROOT), 'x', 1793977732, None)])
        calls = []
        spy = lambda *a: calls.append(a)  # noqa: E731
        self.assertIsNone(hook.run({'session_id': 't1', 'hook_event_name': 'Stop'}, self.tmp, spy))
        self.assertIsNone(hook.run({'session_id': 't2', 'hook_event_name': 'SessionStart', 'source': 'resume'},
                                   self.tmp, spy))
        self.assertIsNone(hook.run({'session_id': 't2', 'hook_event_name': 'PreToolUse'}, self.tmp, spy))
        self.assertEqual(calls, [])
        title = hook.run({'session_id': 't2', 'hook_event_name': 'SessionStart', 'source': 'startup'}, self.tmp, spy)
        self.assertIn('): Old plain name', title)

    def test_a_subagent_thread_is_typed_subagent_and_a_failure_does_not_escape(self):
        source = '{"subagent":{"thread_spawn":{"parent_thread_id":"p"}}}'
        make_home(self.tmp, [('t3', source, 'subagent', 'Codex Desktop', '', 'gpt-5', 'openai', str(ROOT), 'Judge it', 1793977732, None)])
        title = hook.run({'session_id': 't3', 'hook_event_name': 'Stop'}, self.tmp, lambda *a: None)
        self.assertEqual(naming.parse(title)['type'], 'subagent')
        os.environ['CODEX_HOME'] = str(self.tmp)
        self.addCleanup(os.environ.pop, 'CODEX_HOME')
        stdin = sys.stdin
        sys.stdin = open(os.devnull)
        self.addCleanup(setattr, sys, 'stdin', stdin)
        self.assertEqual(hook.main(), 0)

    def test_post_tool_use_wraps_a_model_written_part_at_once(self):
        make_home(self.tmp, [('t4', 'vscode', 'user', 'Codex Desktop', 'fix(web): Humanize splash and learn pages',
                              'gpt-5', 'openai', str(ROOT), 'Fix front-end UI', 1793977732, None),
                             ('t5', 'vscode', 'user', 'Codex Desktop', '', 'gpt-5', 'openai', str(ROOT), 'x', 1793977732, None)])
        title = hook.run({'session_id': 't4', 'hook_event_name': 'PostToolUse'}, self.tmp, lambda *a: None)
        fields = naming.parse(title)
        self.assertEqual((fields['what'], fields['client'], fields['type']),
                         ('fix(web): Humanize splash and learn pages', 'codex-app', 'interactive'))
        self.assertIsNone(hook.run({'session_id': 't5', 'hook_event_name': 'PostToolUse'}, self.tmp, lambda *a: None))

    def test_a_spawned_thread_is_named_from_its_agent_path_and_parent(self):
        parent = naming.format_title('fix(web): Humanize splash and learn pages', client='codex-app', who='owner',
                                     model='gpt-5', provider='openai')
        source = json.dumps({'subagent': {'thread_spawn': {'parent_thread_id': 'p1', 'depth': 1,
                                                           'agent_path': '/root/splash_audit', 'agent_nickname': 'Jason'}}})
        make_home(self.tmp, [('p1', 'vscode', 'user', 'Codex Desktop', parent, 'gpt-5', 'openai', str(ROOT), 'x', 1793977732, None),
                             ('s1', source, None, 'Codex Desktop', None, 'gpt-5', 'openai', str(ROOT), '', 1793977732, None)])
        fields = naming.parse(hook.run({'session_id': 's1', 'hook_event_name': 'Stop'}, self.tmp, lambda *a: None))
        self.assertEqual((fields['what'], fields['who'], fields['type']),
                         ('review(splash): Splash audit', 'jason@web', 'subagent'))


if __name__ == '__main__':
    unittest.main()
