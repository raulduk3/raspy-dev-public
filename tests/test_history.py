"""Exercise a real SQLite history store and prove reads preserve its bytes."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from ai_ecosystem.history import connect, messages, search, windows


class History(unittest.TestCase):
    def test_literal_search_pagination_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sqlite-consistent').mkdir()
            db = root / 'sqlite-consistent/hermes.sqlite'
            with sqlite3.connect(db) as c:
                c.executescript('''CREATE TABLE session_nodes(session_key, current_session_id,
                    label, display_name, updated_at);
                    CREATE TABLE session_windows(session_id, session_key,
                        previous_session_id, reason, created_at, updated_at);
                    CREATE TABLE transcript_events(session_id, seq, event_json, created_at);
                    INSERT INTO session_nodes VALUES('key','id','100% preserved','label',1);
                    INSERT INTO session_windows VALUES('old','key',NULL,'start',0,0);
                    INSERT INTO session_windows VALUES('id','key','old','reset',1,1);''')
                for seq in range(3):
                    c.execute('INSERT INTO transcript_events VALUES(?,?,?,?)',
                              ('id', seq, json.dumps({'message': {'role': 'user',
                               'content': [{'type': 'text', 'text': str(seq)}]}}), seq))
            before = hashlib.sha256(db.read_bytes()).hexdigest()
            c = connect(root, 'engineer')
            try:
                self.assertEqual(len(search(c, '%', 10)), 1)
                self.assertEqual(search(c, "' OR 1=1 --", 10), [])
                timeline = windows(c, 'key', 10)
                self.assertEqual([row['session_id'] for row in timeline], ['old', 'id'])
                self.assertEqual(timeline[1]['previous_session_id'], 'old')
                self.assertEqual(windows(c, 'missing', 10), [])
                page = messages(c, 'id', -1, 2)
                self.assertTrue(page['has_more'])
                self.assertEqual(page['next_after'], 1)
                self.assertEqual(messages(c, 'id', 1, 2)['messages'][0]['text'], '2')
                with self.assertRaises(sqlite3.OperationalError):
                    c.execute('DELETE FROM session_nodes')
                with self.assertRaises(ValueError):
                    messages(c, 'missing', -1, 2)
            finally:
                c.close()
            self.assertEqual(before, hashlib.sha256(db.read_bytes()).hexdigest())


class OldPiConversations(unittest.TestCase):
    """A role's memory/old holds the old machine's Pi conversations; ai-history finds and reads them."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.archive = Path(self.dir.name)
        def conversation(cid, agent, title, lines):
            folder = self.archive / 'conversations' / cid
            (folder / 'native/pi').mkdir(parents=True)
            (folder / 'conversation.json').write_text(json.dumps(
                {'id': cid, 'slug': cid, 'agent': agent, 'title': title, 'created_at': 1}))
            session = folder / 'native/pi/2026-09-29T23-19-07-348Z_one.jsonl'
            session.write_text('\n'.join(json.dumps(e) for e in [
                {'type': 'session', 'version': 3, 'id': 'one', 'timestamp': '2026-09-29T23:19:07Z', 'cwd': '/x'},
                *({'type': 'message', 'timestamp': '2026-09-29T23:20:00Z',
                   'message': {'role': 'user', 'content': [{'type': 'text', 'text': text}]}} for text in lines)]) + '\n')
        conversation('conversation-aaaaaaaaaaaaaaaaaaaa', 'assistant', 'invoices', ['the October invoice'])
        conversation('conversation-bbbbbbbbbbbbbbbbbbbb', 'ops', 'disk', ['the invoice is not mine'])

    def tearDown(self):
        self.dir.cleanup()

    def run_cli(self, *args):
        import io, contextlib
        from ai_ecosystem import history
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = history.main(['--archive', str(self.archive), '--agent', 'assistant', *args])
        return code, json.loads(out.getvalue()) if out.getvalue() else None

    def test_find_matches_text_and_keeps_to_the_role(self):
        code, data = self.run_cli('find', 'october')
        self.assertEqual(code, 0)
        self.assertEqual([r['session_key'] for r in data['result']], ['pi:conversation-aaaaaaaaaaaaaaaaaaaa'])
        self.assertEqual(self.run_cli('find', 'not mine')[1]['result'], [])

    def test_windows_then_read_shows_text_not_json(self):
        _, found = self.run_cli('find', 'invoices')
        _, sessions = self.run_cli('windows', found['result'][0]['session_key'])
        _, page = self.run_cli('read', sessions['result'][0]['session_id'])
        text = '\n'.join(m['text'] for m in page['result']['messages'])
        self.assertIn('the October invoice', text)
        self.assertNotIn('"type"', text)
