"""Exercise conversation creation and native association through real CLI/files."""
import json
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'bin/ai-session'


class Conversations(unittest.TestCase):
    def test_scopes_and_native_association_survive_rescan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, state, project = root / 'home', root / 'state', root / 'project'
            project.mkdir()
            native = home / '.claude/projects/example'
            native.mkdir(parents=True)
            transcript = native / 'native-one.jsonl'
            original = json.dumps({'sessionId': 'native-one', 'cwd': str(project),
                                   'type': 'user', 'message': {'content': 'private history'}}) + '\n'
            transcript.write_text(original)
            env = dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE='1')

            def run(*args, ok=True):
                p = subprocess.run([str(CLI), '--state-root', str(state), *args],
                                   env=env, capture_output=True, text=True)
                if ok:
                    self.assertEqual(p.returncode, 0, p.stderr)
                    return json.loads(p.stdout)
                self.assertNotEqual(p.returncode, 0)

            assistant = run('conversation', 'create', '--agent', 'assistant', '--title', 'Personal', '--name', 'personal-planning')
            self.assertEqual(assistant['scope'], {'kind': 'personal'})
            self.assertEqual(assistant['binding'], {})
            self.assertEqual(assistant['slug'], 'personal-planning')
            named = run('conversation', 'show', 'personal-planning')
            self.assertEqual(named['id'], assistant['id'])
            self.assertTrue((state / 'work/conversations/personal-planning/ref.json').is_file())
            self.assertTrue((state / 'work/agents/assistant/personal-planning/ref.json').is_file())
            run('conversation', 'create', '--agent', 'assistant', '--title', 'Wrong',
                '--project', 'example', '--workspace', str(project), ok=False)
            run('conversation', 'create', '--agent', 'engineer', '--title', 'Missing project', ok=False)
            run('conversation', 'create', '--agent', 'ops', '--title', 'Missing scope', ok=False)
            ops = run('conversation', 'create', '--agent', 'ops', '--title', 'Operations', '--resource', 'local-host')
            self.assertEqual(ops['scope']['kind'], 'system')
            engineer = run('conversation', 'create', '--agent', 'engineer', '--title', 'Formation',
                        '--formation', '--workspace', str(project))
            self.assertEqual(engineer['scope'], {'kind': 'formation'})
            repository = root / 'repo'
            repository.mkdir()
            subprocess.run(['git', 'init', '-q', str(repository)], check=True)
            config = root / 'repos.conf'
            config.write_text(f'owner/example {repository} owner develop\n')
            run('conversation', 'create', '--agent', 'engineer', '--title', 'Wrong checkout',
                '--project', 'owner/example', '--workspace', str(project), '--repos', str(config), ok=False)
            engineering = run('conversation', 'create', '--agent', 'engineer', '--title', 'Known project',
                '--project', 'owner/example', '--workspace', str(repository), '--repos', str(config))
            self.assertEqual(engineering['scope']['kind'], 'project')
            self.assertNotEqual(engineering['scope']['project_id'], 'owner/example')
            run('scan', '--home', str(home))
            record = run('list', '--json')['sessions'][0]
            run('conversation', 'bind', engineering['id'], record['id'], '--expect-revision', str(record['revision']), ok=False)
            run('conversation', 'bind', engineer['id'], record['id'], '--expect-revision', str(record['revision']))
            run('scan', '--home', str(home))
            result = run('conversation', 'show', engineer['id'])
            self.assertEqual(result['native_sessions'][0]['id'], record['id'])
            self.assertEqual(result['native_sessions'][0]['conversation_id'], engineer['id'])
            revision = result['native_sessions'][0]['revision']
            run('conversation', 'bind', ops['id'], record['id'], '--expect-revision', str(revision), ok=False)
            self.assertTrue((Path(result['home']) / 'native/pi').is_dir())
            self.assertTrue((Path(result['home']) / 'conversation.json').is_file())
            self.assertTrue((Path(result['home']) / 'sessions' / f"{record['id']}.json").is_file())
            self.assertEqual(run('conversation', 'show', engineer['slug'])['id'], engineer['id'])
            self.assertEqual(transcript.read_text(), original)
            self.assertNotIn('private history', json.dumps(result))
            self.assertEqual(Path(result['home']).stat().st_mode & 0o777, 0o700)
            legacy_id = 'conversation-' + 'a' * 20
            legacy_home = state / 'conversations' / legacy_id
            legacy_home.mkdir(parents=True)
            (legacy_home / 'session.json').write_text(json.dumps({
                'version': 1, 'id': legacy_id, 'agent': 'assistant', 'title': 'Old thread',
                'scope': {'kind': 'personal'}, 'binding': {}, 'created_at': 1,
            }))
            listed = run('conversation', 'list')['conversations']
            self.assertEqual({r['id'] for r in listed}, {assistant['id'], ops['id'], engineer['id'], engineering['id'], legacy_id})
            legacy = run('conversation', 'show', legacy_id)
            self.assertTrue((Path(legacy['home']) / 'conversation.json').is_file())
            self.assertTrue((state / 'work/conversations' / legacy['slug'] / 'ref.json').is_file())
            self.assertIn('slug', listed[0])
