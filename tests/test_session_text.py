"""ai-session across homes and harnesses: Pi sessions, readable text, export/ingest, agent resume."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/ai-session'
sys.path.insert(0, str(PLATFORM / 'lib'))
from ai_ecosystem import transcript  # noqa: E402

PI_ID = '01a0ed90-0000-7000-8000-000000000001'
CLAUDE_ID = 'aaaaaaaa-0000-4000-8000-000000000002'
SECRET = 'sk-ant-oat01-' + 'x' * 40


def jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r) + '\n' for r in records))


def pi_session(path, cwd, account='openai-bravo:pi', agent='engineer'):
    jsonl(path, [
        {'type': 'session', 'version': 3, 'id': PI_ID, 'timestamp': '2026-09-29T14:28:01.547Z', 'cwd': cwd},
        {'type': 'custom', 'customType': 'dev-platform-binding', 'data': {'accountRef': account, 'agent': agent}},
        {'type': 'model_change', 'provider': 'openai-codex', 'modelId': 'gpt-5.5'},
        {'type': 'message', 'timestamp': '2026-09-29T14:29:00Z',
         'message': {'role': 'user', 'content': [{'type': 'text', 'text': f'plan the spec work, key {SECRET}'}]}},
        {'type': 'message', 'timestamp': '2026-09-29T14:29:05Z',
         'message': {'role': 'assistant', 'content': [{'type': 'thinking', 'thinking': 'PRIVATE THOUGHT'},
                                                       {'type': 'toolCall', 'name': 'bash', 'arguments': {'command': 'git status'}}]}},
        {'type': 'message', 'message': {'role': 'toolResult', 'content': [{'type': 'text', 'text': 'clean'}]}},
        {'type': 'message', 'timestamp': '2026-09-29T14:30:00Z',
         'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'The tree is clean.'}]}},
    ])


def claude_session(project, cwd):
    jsonl(project / f'{CLAUDE_ID}.jsonl', [
        {'type': 'user', 'sessionId': CLAUDE_ID, 'cwd': cwd, 'timestamp': '2026-10-05T14:52:17Z',
         'message': {'role': 'user', 'content': 'the journal is broken'}},
        {'type': 'ai-title', 'aiTitle': 'Journal broken', 'sessionId': CLAUDE_ID},
        {'type': 'assistant', 'sessionId': CLAUDE_ID, 'cwd': cwd, 'timestamp': '2026-10-05T14:52:19Z',
         'message': {'model': 'claude-opus-5-5', 'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'ls ~/journal'}}]}},
        {'type': 'user', 'sessionId': CLAUDE_ID, 'cwd': cwd,
         'message': {'content': [{'type': 'tool_result', 'content': 'log tasks'}]}},
        {'type': 'assistant', 'sessionId': CLAUDE_ID, 'cwd': cwd, 'timestamp': '2026-10-05T14:53:00Z',
         'message': {'content': [{'type': 'text', 'text': 'It is readable; the index was stale.'}]}},
    ])


class SessionText(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='ai-session-text-')
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.owner, self.agent, self.state = base / 'owner', base / 'assistant', base / 'state'
        self.owner.mkdir()
        claude_session(self.agent / '.claude/projects/-home-assistant', str(self.agent))
        pi_session(self.agent / '.pi/agent/sessions/--home-assistant--/2026-09-29T14-28-01-547Z_x.jsonl', str(self.agent))
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))}
        self.env.update(HOME=str(self.owner), PYTHONDONTWRITEBYTECODE='1')

    def cli(self, *args, stdin=None, home=None):
        env = dict(self.env, HOME=str(home or self.owner))
        run = subprocess.run([str(CLI), '--state-root', str(self.state), *args],
                             capture_output=True, text=True, env=env, input=stdin)
        self.assertEqual(run.returncode, 0, run.stderr)
        return run.stdout

    def ingest_agent(self, *extra):
        exported = self.cli('export', '--home', str(self.agent), home=self.agent)
        self.assertNotIn(SECRET, exported)
        return self.cli('ingest', '--owner', 'assistant', *extra, stdin=exported)

    def listed(self):
        return json.loads(self.cli('list', '--json', '--limit', '0'))['sessions']

    def test_export_writes_no_store(self):
        self.cli('export', '--home', str(self.agent), home=self.agent)
        self.assertFalse(self.state.exists())

    def test_agent_sessions_are_listed_under_the_agent(self):
        self.ingest_agent()
        rows = self.listed()
        self.assertEqual({(m['runtime'], m['owner']) for m in rows}, {('claude', 'assistant'), ('pi', 'assistant')})
        pi = next(m for m in rows if m['runtime'] == 'pi')
        self.assertEqual(pi['derived']['account'], 'openai-bravo:pi')
        self.assertEqual(pi['derived']['model'], 'openai-codex/gpt-5.5')
        claude = next(m for m in rows if m['runtime'] == 'claude')
        self.assertEqual(claude['derived']['title'], 'Journal broken')
        self.assertIn('assistant', self.cli('list', '--owner', 'assistant'))

    def test_show_is_readable_text_with_secrets_masked(self):
        self.ingest_agent()
        for m in self.listed():
            shown = self.cli('show', m['id'])
            self.assertNotIn('{"type"', shown)
            self.assertNotIn(SECRET, shown)
            self.assertNotIn('PRIVATE THOUGHT', shown)
            self.assertIn('## user', shown)
            self.assertIn('Resume:' if m['runtime'] == 'claude' else 'Not resumable:', shown)
        pi = next(m for m in self.listed() if m['runtime'] == 'pi')
        shown = self.cli('show', pi['id'])
        self.assertIn('→ bash: git status', shown)
        self.assertIn('The tree is clean.', shown)
        self.assertIn('[secret hidden]', shown)

    def test_agent_claude_session_resumes_through_the_launcher(self):
        self.ingest_agent()
        claude = next(m for m in self.listed() if m['runtime'] == 'claude')
        plan = json.loads(subprocess.run([str(CLI), '--state-root', str(self.state), 'resume', claude['id']],
                                         capture_output=True, text=True, env=self.env).stdout)
        self.assertEqual(plan['argv'], ['agent', 'assistant', '--', '--resume', CLAUDE_ID])

    def test_agent_pi_session_resumes_as_the_role_on_its_account(self):
        conv = self.agent / '.local/state/dev-platform/sessions/conversations/conversation-0123456789abcdef0123'
        conv.mkdir(parents=True)
        (conv / 'conversation.json').write_text(json.dumps({'id': conv.name, 'agent': 'assistant', 'title': 'budget',
                                                            'scope': {'kind': 'personal'}}))
        native = conv / 'native/pi/2026-10-05T10-00-00-000Z_y.jsonl'
        pi_session(native, str(conv / 'workspace'), account='openai-alpha:pi', agent='assistant')
        self.ingest_agent()
        live = [m for m in self.listed() if m['runtime'] == 'pi' and (m.get('native') or {}).get('conversation')]
        self.assertEqual(len(live), 1)
        plan = json.loads(subprocess.run([str(CLI), '--state-root', str(self.state), 'resume', live[0]['id']],
                                         capture_output=True, text=True, env=self.env).stdout)
        self.assertEqual(plan['argv'][:4], ['env', 'OL_MODEL=pi', 'OL_ACCOUNT=openai-alpha', 'agent'])
        self.assertEqual(plan['argv'][4:8], ['assistant', '--', '--conversation', conv.name])
        self.assertEqual(plan['argv'][-2], '--resume')

    def test_agent_pi_session_on_a_metered_account_resumes_with_the_owners_yes(self):
        # OpenRouter through Pi is metered: the launcher refuses it without OL_METERED_OK=1. The
        # resume command is the owner's own, for the account the session ran on, so it carries it.
        conv = self.agent / '.local/state/dev-platform/sessions/conversations/conversation-0123456789abcdef0124'
        conv.mkdir(parents=True)
        (conv / 'conversation.json').write_text(json.dumps({'id': conv.name, 'agent': 'assistant', 'title': 'invoice',
                                                            'scope': {'kind': 'personal'}}))
        native = conv / 'native/pi/2026-11-02T16-17-23-601Z_z.jsonl'
        pi_session(native, str(conv / 'workspace'), account='openrouter:pi', agent='assistant')
        self.ingest_agent()
        live = [m for m in self.listed() if m['runtime'] == 'pi' and (m.get('native') or {}).get('conversation')]
        plan = json.loads(subprocess.run([str(CLI), '--state-root', str(self.state), 'resume', live[0]['id']],
                                         capture_output=True, text=True, env=self.env).stdout)
        self.assertEqual(plan['argv'][:5], ['env', 'OL_MODEL=pi', 'OL_ACCOUNT=openrouter', 'OL_METERED_OK=1', 'agent'])
        self.assertIn('OL_METERED_OK=1', plan['command'])

    def test_owner_scan_keeps_ingested_agent_sources(self):
        self.ingest_agent()
        self.cli('scan')
        self.assertTrue(all(not m['missing'] for m in self.listed()))
        sources = json.loads((self.state / 'sources.json').read_text())
        self.assertEqual({v['state'] for k, v in sources.items() if k.startswith('assistant:')}, {'ok'})

    def test_launch_facts_go_on_the_sessions_of_that_run(self):
        self.ingest_agent('--launch', 'kind=chat', '--launch', 'account=anthropic-bravo', '--launch-since', '0')
        self.assertTrue(all(m['launch'] == {'kind': 'chat', 'account': 'anthropic-bravo'} for m in self.listed()))
        later = str(2 ** 40)
        self.ingest_agent('--launch', 'kind=run', '--launch-since', later)
        self.assertTrue(all(m['launch']['kind'] == 'chat' for m in self.listed()))

    def test_a_vanished_agent_session_goes_stale(self):
        self.ingest_agent()
        for path in (self.agent / '.claude/projects').rglob('*.jsonl'):
            path.unlink()
        self.ingest_agent()
        claude = next(m for m in self.listed() if m['runtime'] == 'claude')
        self.assertTrue(claude['missing'])

    def test_old_conversations_split_by_agent_and_read_as_archived(self):
        old = self.agent.parent / 'old'
        for cid, agent in (('conversation-' + 'a' * 20, 'engineer'), ('conversation-' + 'b' * 20, 'assistant')):
            pi_session(old / cid / 'native/pi/s.jsonl', '/Users/owner/Dev/x', agent=agent)
            (old / cid / 'conversation.json').write_text(json.dumps({'agent': agent, 'id': cid}))
            (old / cid / '.pi-writer.lock').write_text('')
        dest = self.agent.parent / 'split'
        self.assertEqual(json.loads(self.cli('import-old', str(old), str(dest))), {'engineer': 1, 'assistant': 1})
        self.assertFalse(list(dest.rglob('.pi-writer.lock')))
        target = self.agent / 'memory/old'
        target.mkdir(parents=True)
        (dest / 'assistant/conversations').rename(target / 'conversations')
        self.ingest_agent()
        archived = [m for m in self.listed() if m['native'].get('archived')]
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]['native']['conversation'], 'conversation-' + 'b' * 20)
        self.assertIn('Not resumable: history from the old machine', self.cli('show', archived[0]['id']))


class Masking(unittest.TestCase):
    def test_common_credentials_are_hidden(self):
        for secret in ('sk-ant-api03-' + 'a' * 30, 'ghp_' + 'b' * 36, 'github_pat_' + 'c' * 30,
                       'xoxb-' + '1' * 20, 'AKIA' + 'D' * 16, 'pplx-' + 'e' * 30, 'sk-or-v1-' + 'f' * 40):
            self.assertNotIn(secret, transcript.mask(f'value {secret} end'))
        self.assertEqual(transcript.mask('Authorization: Bearer abcdefghijklmnopqrstu'), 'Authorization: Bearer [secret hidden]')
        self.assertEqual(transcript.mask('PASSWORD="hunter2hunter2"'), 'PASSWORD="[secret hidden]"')
        self.assertEqual(transcript.mask('-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----'), '[secret hidden]')
        self.assertEqual(transcript.mask('the token count was 5000'), 'the token count was 5000')


if __name__ == '__main__':
    unittest.main()


class Mask(unittest.TestCase):
    """One mask for transcripts and the old archive; has_secret agrees with it exactly."""

    PLANTED = ['postgres://app:FAKEpass99@db.example/x', 'OPENAI_API_KEY=FAKEFAKEFAKE1234567', '{"client_secret": "FAKEsecret0000"}',
               'Authorization: Bearer FAKEFAKEFAKEFAKEFAKE', 'sk-ant-api03-FAKEFAKEFAKEFAKE',
               '-----BEGIN OPENSSH PRIVATE KEY-----\nFAKE\n-----END OPENSSH PRIVATE KEY-----',
               'eyJhbGciOiJub25lIn0.eyJmYWtlIjoxMjM0NTY3OH0.FAKEFAKEFAKEFAKE', 'ghp_FAKEFAKEFAKEFAKEFAKEFAKE']

    def test_every_planted_secret_is_hidden_and_nothing_remains(self):
        from ai_ecosystem.transcript import mask, has_secret
        for text in self.PLANTED:
            with self.subTest(kind=text[:12]):
                self.assertTrue(has_secret(text))
                self.assertNotIn('FAKE', mask(text).replace('[secret hidden]', ''))
                self.assertFalse(has_secret(mask(text)))

    def test_ordinary_text_is_left_alone(self):
        from ai_ecosystem.transcript import mask, has_secret
        for text in ('the token count was 42', '"max_tokens": 4096', 'reset your password tomorrow'):
            self.assertFalse(has_secret(text))
            self.assertEqual(mask(text), text)
