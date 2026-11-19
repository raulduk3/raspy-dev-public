"""ai-prompt-verbs keeps only the prompts the owner typed, and counts vague verbs in them."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import prompt_verbs  # noqa: E402


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))


def user(text, kind='human', ts='2026-11-01T00:00:00Z', **extra):
    row = {'type': 'user', 'timestamp': ts, 'uuid': f'{text}-{ts}', 'message': {'content': text}}
    if kind:
        row['origin'] = {'kind': kind}
    row.update(extra)
    return row


class PromptVerbs(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home)
        jsonl(self.home / '.claude/projects/-home-owner-dev-acme-app/a.jsonl', [
            user('Make it better'),
            user('Make it better', ts='2026-11-01T01:00:00Z'),                 # repeated text
            user('Push the branch and make sure tests pass'),
            user('Yes'),
            user('done', kind='peer'),                                         # another session
            user('# Worker brief\nDo the task', kind=None),
            user('hidden', isMeta=True),
            user('side', isSidechain=True),
            user('<command-name>/goal</command-name><command-args>improve the app</command-args>', kind=None),
            user('x' * 3001),
        ])
        jsonl(self.home / '.claude/projects/-home-owner-other/b.jsonl', [user('Do it')])
        parent = {'type': 'session_meta', 'payload': {'id': 'p', 'thread_source': 'user', 'cwd': '/home/owner/dev/acme'}}
        typed = {'type': 'response_item', 'timestamp': '2026-11-02T00:00:00Z',
                 'payload': {'type': 'message', 'role': 'user', 'content': [
                     {'type': 'input_text', 'text': '# AGENTS.md instructions'},
                     {'type': 'input_text', 'text': '<environment_context>'},
                     {'type': 'input_text', 'text': 'Clean up the repo'}]}}
        jsonl(self.home / '.codex/sessions/2026/11/02/rollout-p.jsonl', [parent, typed])
        child = {'type': 'session_meta', 'payload': {'id': 'c', 'thread_source': 'subagent', 'cwd': '/home/owner/dev/acme'}}
        jsonl(self.home / '.codex/sessions/2026/11/02/rollout-c.jsonl', [child, parent, typed])
        jsonl(self.home / '.pi/agent/sessions/x/s.jsonl', [
            {'type': 'session', 'id': 's', 'cwd': '/home/owner/dev/acme'},
            {'type': 'message', 'timestamp': '2026-11-03T00:00:00Z',
             'message': {'role': 'user', 'content': [{'type': 'text', 'text': 'Write the report to docs'}]}}])

    def test_extraction_and_count(self):
        rows = prompt_verbs.collect(self.home, 'acme')
        texts = [r['text'] for r in rows if not r['dup']]
        self.assertEqual(sorted(texts), sorted([
            'Make it better', 'Push the branch and make sure tests pass', 'Yes', '/goal improve the app',
            'x' * 3001, 'Clean up the repo', 'Write the report to docs']))
        result = prompt_verbs.count(rows)
        self.assertEqual(result['prompts'], 6)
        self.assertEqual(result['long_removed'], 1)
        self.assertEqual(result['agents'], {'claude': 4, 'codex': 1, 'pi': 1})
        # vague: make, make sure (+push), improve, clean up; only vague: make, improve, clean up
        self.assertEqual(result['any_vague'], 4)
        self.assertEqual(result['only_vague'], 3)
        self.assertEqual(result['three_words_or_less'], 3)     # "Make it better", "Yes", "improve the app"

    def test_time_window(self):
        rows = prompt_verbs.collect(self.home, 'acme', until='2026-11-02')
        self.assertEqual({r['agent'] for r in rows}, {'claude'})


if __name__ == '__main__':
    unittest.main()
