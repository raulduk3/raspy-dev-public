"""The notify hook (hooks/notify.sh, SDD-GD-38) with a fake notify command.

PATH holds only links to the tools that the hook needs and, where a test wants it, a fake
`notify` that records each call. The machine's own notify command is never on PATH, so no test
sends a message. HOME and the runtime folder of the stamps are temporary.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'hooks/notify.sh'
TOOLS = ('bash', 'python3', 'cat', 'find', 'touch', 'id', 'hostname', 'timeout')
SESSION = '0123456789abcdef-session'


class NotifyHook(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='notify-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / 'home'
        (self.home / 'project').mkdir(parents=True)
        self.runtime = self.tmp / 'run'
        self.runtime.mkdir()
        self.bin = self.tmp / 'bin'
        self.bin.mkdir()
        for tool in TOOLS:
            (self.bin / tool).symlink_to(shutil.which(tool))
        self.calls = self.tmp / 'calls.jsonl'
        self.env = {'PATH': str(self.bin), 'HOME': str(self.home), 'XDG_RUNTIME_DIR': str(self.runtime),
                    'LANG': os.environ.get('LANG', 'C.UTF-8')}

    def fake_notify(self, code=0):
        notify = self.bin / 'notify'
        notify.write_text('#!' + shutil.which('python3') + ' -I\n'
                          'import json, sys\n'
                          f'with open({str(self.calls)!r}, "a") as f:\n'
                          '    f.write(json.dumps({"args": sys.argv[1:], "body": sys.stdin.read()}) + "\\n")\n'
                          f'sys.exit({code})\n')
        notify.chmod(0o755)

    def hook(self, event, kind=None, session=SESSION, message='Claude needs your permission', **env):
        payload = {'hook_event_name': event, 'session_id': session, 'cwd': str(self.home / 'project'),
                   'message': message}
        if kind:
            payload['notification_type' if event == 'Notification' else 'error_type'] = kind
        return subprocess.run([shutil.which('bash'), str(HOOK)], input=json.dumps(payload),
                              env={**self.env, **env}, capture_output=True, text=True, timeout=30)

    def sent(self):
        if not self.calls.exists():
            return []
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_a_notification_sends_one_message_with_the_reason_user_host_folder_and_session(self):
        self.fake_notify()
        self.assertEqual(self.hook('Notification', 'permission_prompt').returncode, 0)
        [call] = self.sent()
        self.assertEqual(call['args'], ['Claude: permission_prompt', '-', 'default'])
        lines = call['body'].splitlines()
        self.assertEqual(lines[0], 'Claude needs your permission')
        user = subprocess.run(['id', '-un'], capture_output=True, text=True).stdout.strip()
        host = subprocess.run(['hostname', '-s'], capture_output=True, text=True).stdout.strip()
        self.assertEqual(lines[1], f'{user}@{host} in ~/project (session 01234567)')

    def test_a_stop_on_an_error_has_high_priority(self):
        self.fake_notify()
        self.assertEqual(self.hook('StopFailure', 'rate_limit', message='Rate limit reached').returncode, 0)
        [call] = self.sent()
        self.assertEqual(call['args'], ['Claude: rate_limit', '-', 'high'])
        self.assertTrue(call['body'].startswith('Rate limit reached\n'))

    def test_the_same_session_and_reason_send_one_message_in_ten_minutes(self):
        self.fake_notify()
        for _ in range(3):
            self.hook('Notification', 'permission_prompt')
        self.assertEqual(len(self.sent()), 1)
        self.hook('StopFailure', 'billing_error')
        self.hook('Notification', 'permission_prompt', session='fedcba9876543210')
        self.assertEqual(len(self.sent()), 3, 'another reason or session sends its own message')
        stamp = next(self.runtime.glob('claude-notify-*-01234567-Notification-permission_prompt'))
        old = stamp.stat().st_mtime - 11 * 60
        os.utime(stamp, (old, old))
        self.hook('Notification', 'permission_prompt')
        self.assertEqual(len(self.sent()), 4, 'a stamp older than 10 minutes does not stop the message')

    def test_an_idle_prompt_a_sign_in_and_a_completed_question_send_nothing(self):
        self.fake_notify()
        for kind in ('idle_prompt', 'auth_success', 'elicitation_complete', 'elicitation_response'):
            with self.subTest(kind=kind):
                self.assertEqual(self.hook('Notification', kind).returncode, 0)
        self.assertEqual(self.sent(), [])

    def test_the_switch_off_or_no_notify_command_sends_nothing(self):
        self.assertEqual(self.hook('StopFailure', 'rate_limit').returncode, 0)   # no notify on PATH
        self.fake_notify()
        self.assertEqual(self.hook('StopFailure', 'rate_limit', DEV_PLATFORM_NOTIFY='off').returncode, 0)
        self.assertEqual(self.sent(), [])

    def test_a_fault_of_the_notify_command_does_not_fail_the_session(self):
        self.fake_notify(code=3)
        self.assertEqual(self.hook('StopFailure', 'server_error').returncode, 0)
        self.assertEqual(len(self.sent()), 1)

    def test_the_hook_settings_name_the_hook_for_the_two_events(self):
        hooks = json.loads((ROOT / 'hooks/claude-settings.hooks.json').read_text())['hooks']
        for event in ('Notification', 'StopFailure'):
            with self.subTest(event=event):
                commands = [h['command'] for group in hooks[event] for h in group['hooks']]
                self.assertTrue(any(c.endswith('/hooks/notify.sh') for c in commands), commands)


if __name__ == '__main__':
    unittest.main()
