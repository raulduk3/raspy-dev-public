"""Every role identity carries the canonical rules verbatim."""
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RULES = (ROOT / 'agents' / 'rules.md').read_text().strip()


class RoleRules(unittest.TestCase):
    def test_every_identity_carries_the_rules(self):
        identities = sorted((ROOT / 'agents').glob('*/identity.md'))
        self.assertTrue(identities)
        for identity in identities:
            with self.subTest(identity=identity.parent.name):
                self.assertIn(RULES, identity.read_text())


class SessionLength(unittest.TestCase):
    def run_guard(self, turns):
        with tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False) as transcript:
            for _ in range(turns):
                transcript.write(json.dumps({'type': 'user', 'message': {'content': 'q'}}) + '\n')
                transcript.write(json.dumps({'type': 'user', 'message': {'content': [{'type': 'tool_result'}]}}) + '\n')
            transcript.write(json.dumps({'type': 'user', 'message': {'content': '<task-notification>x'}}) + '\n')
        # The limit itself, with no owner exempted: the machine's own owner file (which may
        # name whoever runs the suite) is not this test's.
        hook = Path(tempfile.mkdtemp()) / 'session-length.sh'
        hook.write_text((ROOT / 'hooks' / 'session-length.sh').read_text()
                        .replace('/etc/dev-platform/owner', str(hook.parent / 'no-owner')))
        return subprocess.run(['bash', str(hook)], input=json.dumps({'transcript_path': transcript.name}),
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


class SessionLengthOwner(unittest.TestCase):
    """Only the agents and loop workers are limited; the owner's own sessions never are."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.owner_file = self.tmp / 'owner'
        # The hook reads a fixed root path; the test gives it its own file in that place.
        text = (ROOT / 'hooks' / 'session-length.sh').read_text()
        self.assertIn('/etc/dev-platform/owner', text)
        self.hook = self.tmp / 'session-length.sh'
        self.hook.write_text(text.replace('/etc/dev-platform/owner', str(self.owner_file)))
        transcript = self.tmp / 't.jsonl'
        transcript.write_text(''.join(json.dumps({'type': 'user', 'message': {'content': 'q'}}) + '\n'
                                      for _ in range(40)))
        self.input = json.dumps({'transcript_path': str(transcript)})

    def run_hook(self, owner, **env):
        if owner is not None:
            self.owner_file.write_text(owner + '\n')
        environment = {k: v for k, v in os.environ.items() if k != 'DEV_PLATFORM_LOOP_WORKER'}
        environment.update(env)
        return subprocess.run(['bash', str(self.hook)], input=self.input, capture_output=True,
                              text=True, env=environment)

    def test_the_owners_session_is_never_warned_or_blocked(self):
        result = self.run_hook(getpass.getuser())
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))

    def test_an_agents_session_is_still_blocked(self):
        # Any user other than the one named: assistant, ops, engineer.
        self.assertEqual(self.run_hook('someone-else').returncode, 2)

    def test_a_loop_worker_is_limited_even_as_the_owner(self):
        self.assertEqual(self.run_hook(getpass.getuser(), DEV_PLATFORM_LOOP_WORKER='1').returncode, 2)

    def test_an_agent_cannot_pass_as_the_owner_with_its_own_id_command(self):
        fake = self.tmp / 'bin'
        fake.mkdir()
        (fake / 'id').write_text('#!/bin/sh\necho someone-else\n')
        (fake / 'id').chmod(0o755)
        path = f'{fake}:{os.environ.get("PATH", "/usr/bin")}'
        self.assertEqual(self.run_hook('someone-else', PATH=path).returncode, 2)

    def test_without_the_owner_file_everyone_is_limited(self):
        self.assertEqual(self.run_hook(None).returncode, 2)

    def test_the_owner_cannot_be_named_from_the_environment(self):
        result = self.run_hook('someone-else', DEV_PLATFORM_OWNER=getpass.getuser(), USER='someone-else')
        self.assertEqual(result.returncode, 2)


class RoleSessionLength(unittest.TestCase):
    def test_role_guard_check_passes(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for the role session guard check')
        result = subprocess.run([node, str(ROOT / 'integrations/pi/check-session-length.mjs')],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('session-length: ok', result.stdout)


class CodexRules(unittest.TestCase):
    """hooks/codex.rules, checked by the installed Codex itself (`codex execpolicy check`)."""

    def decision(self, command):
        codex = shutil.which('codex')
        if not codex:
            self.skipTest('Codex is not installed')
        done = subprocess.run([codex, 'execpolicy', 'check', '--rules', str(ROOT / 'hooks/codex.rules'), '--',
                               *command.split()], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout).get('decision')

    def test_listed_forms_are_forbidden(self):
        for command in ('git push -u origin main', 'git push origin main', 'git push origin develop',
                        'git push origin +HEAD', 'git push origin +main', 'git push origin HEAD:refs/heads/main',
                        'git push -u origin HEAD:refs/heads/main', 'git push --no-verify origin x',
                        'git commit --no-verify -m x', 'git commit -n -m x', 'git push --force origin x',
                        'git branch -D x', 'git worktree remove ../x', 'git clean -fd', 'gh pr merge 1'):
            with self.subTest(command=command):
                self.assertEqual(self.decision(command), 'forbidden')

    def test_ordinary_forms_are_not_forbidden(self):
        for command in ('git push -u origin fix/x', 'git status', 'git commit -m x'):
            with self.subTest(command=command):
                self.assertNotEqual(self.decision(command), 'forbidden')


if __name__ == '__main__':
    unittest.main()
