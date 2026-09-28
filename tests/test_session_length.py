"""Session-length guard."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SessionLength(unittest.TestCase):
    def run_guard(self, turns):
        with tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False) as transcript:
            for _ in range(turns):
                transcript.write(json.dumps({'type': 'user', 'message': {'content': 'q'}}) + '\n')
                transcript.write(json.dumps({'type': 'user', 'message': {'content': [{'type': 'tool_result'}]}}) + '\n')
            transcript.write(json.dumps({'type': 'user', 'message': {'content': '<task-notification>x'}}) + '\n')
        return subprocess.run([str(ROOT / 'hooks' / 'session-length.sh')], input=json.dumps({'transcript_path': transcript.name}),
                              capture_output=True, text=True)

    def test_short_session_passes_silently(self):
        result = self.run_guard(5)
        self.assertEqual((result.returncode, result.stdout), (0, ''))

    def test_long_session_warns(self):
        result = self.run_guard(19)
        self.assertEqual(result.returncode, 0)
        self.assertIn('turn 20 of 30', result.stdout)

    def test_session_past_the_limit_is_blocked(self):
        self.assertEqual(self.run_guard(30).returncode, 2)
        self.assertEqual(self.run_guard(29).returncode, 0)


if __name__ == '__main__':
    unittest.main()
