"""One install for every user: where the platform, its runtimes and secrets are found."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import paths, secret  # noqa: E402


class Paths(unittest.TestCase):
    def test_defaults_are_shared_not_in_a_home(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(paths.share(), Path('/opt/dev-platform'))
            self.assertEqual(paths.install(), Path('/opt/dev-platform/current'))
            self.assertEqual(paths.pi_runtimes(), Path('/opt/dev-platform/pi-runtime'))

    def test_environment_moves_each(self):
        env = {'DEV_PLATFORM_SHARE': '/x', 'DEV_PLATFORM_CHECKOUT': '/y'}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(paths.install(), Path('/x/current'))
            self.assertEqual(paths.checkout(), Path('/y'))
        with mock.patch.dict(os.environ, {'DEV_PLATFORM_HOME': '/z'}, clear=True):
            self.assertEqual(paths.install(), Path('/z'))

    def test_shell_form_expands_like_a_hook_shell(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(paths.expand(paths.SHELL_HOME + '/hooks'), Path('/opt/dev-platform/current/hooks'))
        with mock.patch.dict(os.environ, {'DEV_PLATFORM_HOME': '/r'}, clear=True):
            self.assertEqual(paths.expand(paths.SHELL_HOME + '/hooks'), Path('/r/hooks'))

    def test_node_platform_names_a_real_distribution(self):
        self.assertRegex(paths.node_platform(), r'^(linux|darwin)-(arm64|x64)$')

    def test_the_daemon_path_puts_the_seat_programs_first_only_when_they_exist(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {'DEV_PLATFORM_SEAT_BIN': d, 'PATH': '/usr/bin'}, clear=True):
                self.assertEqual(paths.daemon_path('/node/bin'), f'{d}:/node/bin:/usr/bin')
        with mock.patch.dict(os.environ, {'DEV_PLATFORM_SEAT_BIN': '/nonexistent', 'PATH': '/usr/bin'}, clear=True):
            self.assertEqual(paths.daemon_path('/node/bin'), '/node/bin:/usr/bin')


class Secret(unittest.TestCase):
    def test_reads_only_the_handed_in_credential(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'dev-platform-jev').write_text('synthetic\n')
            with mock.patch.dict(os.environ, {'CREDENTIALS_DIRECTORY': folder}):
                self.assertEqual(secret.read('dev-platform-jev'), 'synthetic')
                # never assertIsNone on a secret: a failure would print the key
                self.assertTrue(secret.read('harvest-api') is None, 'a key outside the handed-in folder was read')
                with self.assertRaises(ValueError):
                    secret.read('../etc/shadow')
        with mock.patch.dict(os.environ, {secret.OFF: '1'}, clear=True):
            self.assertFalse(secret.available('dev-platform-jev'))


if __name__ == '__main__':
    unittest.main()
