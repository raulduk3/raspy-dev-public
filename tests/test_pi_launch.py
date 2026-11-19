"""Actual subprocess/exec/flock behavior, including crash recovery."""
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

LIB = str(Path(__file__).resolve().parents[1] / 'lib')
LAUNCH = '''
import os, sys
from ai_ecosystem.pi_launch import exec_conversation
try:
    exec_conversation(sys.argv[1], [sys.argv[2], '-e', sys.argv[3]], os.environ)
except ValueError as error:
    print(str(error), flush=True)
    sys.exit(2)
'''
WRITER = '''
require('node:fs').fstatSync(Number(process.env.DEV_PLATFORM_PI_LOCK_FD));
console.log('ready');
process.stdin.resume();
'''


class PiLaunch(unittest.TestCase):
    def start(self, home):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for the real Pi-runtime process boundary check')
        process = subprocess.Popen([sys.executable, '-u', '-c', LAUNCH, str(home), str(Path(node).resolve()), WRITER],
            env={**os.environ, 'PYTHONPATH': LIB}, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.finish, process)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(5), 'launcher produced no readiness/error result')
        return process, process.stdout.readline().strip()

    @staticmethod
    def finish(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def test_exclusion_and_recovery_after_exec_and_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            first, result = self.start(home)
            self.assertEqual(result, 'ready')
            second, result = self.start(home)
            self.assertEqual(result, 'conversation already has an active Pi writer')
            self.assertEqual(second.wait(timeout=5), 2)
            first.send_signal(signal.SIGKILL)
            first.wait(timeout=5)
            # The unchanged lock file remains. No unlink or PID cleanup is needed.
            inode = (home / '.pi-writer.lock').stat().st_ino
            third, result = self.start(home)
            self.assertEqual(result, 'ready')
            self.assertEqual((home / '.pi-writer.lock').stat().st_ino, inode)
            third.communicate(timeout=5)
            self.assertEqual(third.returncode, 0)
            fourth, result = self.start(home)
            self.assertEqual(result, 'ready')
            fourth.communicate(timeout=5)

    def test_failed_exec_releases_lock(self):
        sys.path.insert(0, LIB)
        from ai_ecosystem.pi_launch import exec_conversation
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            with self.assertRaises(FileNotFoundError):
                exec_conversation(home, ['/nonexistent/pi-runtime'], {})
            process, result = self.start(home)
            self.assertEqual(result, 'ready')
            process.communicate(timeout=5)
