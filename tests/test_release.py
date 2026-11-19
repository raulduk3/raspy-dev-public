"""ai-release builds releases from commits and reports any that drift from theirs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/ai-release'
sys.path.insert(0, str(PLATFORM / 'lib'))

from ai_ecosystem import doctor  # noqa: E402


class Release(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='ai-release-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.checkout = self.root / 'checkout'
        self.share = self.root / 'share'
        (self.checkout / 'bin').mkdir(parents=True)
        (self.checkout / 'bin/check').write_text('#!/bin/sh\nexit 0\n')
        (self.checkout / 'bin/check').chmod(0o755)
        (self.checkout / 'README.md').write_text('first\n')
        os.symlink('README.md', self.checkout / 'LINK.md')
        self.git('init', '-q')
        self.commit('first')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.checkout), '-c', 'user.name=t', '-c',
                               'user.email=t@example.invalid', *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def cli(self, *args):
        run = subprocess.run([str(CLI), '--checkout', str(self.checkout), '--share', str(self.share),
                              *args], capture_output=True, text=True, timeout=30)
        return run.returncode, run.stdout, run.stderr

    def test_activate_builds_the_commit_not_the_working_tree(self):
        head = self.git('rev-parse', 'HEAD')
        (self.checkout / 'README.md').write_text('uncommitted edit\n')
        code, out, err = self.cli('activate', 'HEAD')
        self.assertEqual(code, 0, err)
        current = self.share / 'current'
        self.assertEqual(os.readlink(current), f'releases/{head}')
        self.assertEqual((current / 'README.md').read_text(), 'first\n')
        self.assertTrue(os.access(current / 'bin/check', os.X_OK))
        self.assertTrue((current / 'LINK.md').is_symlink())
        self.assertEqual(json.loads(self.cli('verify')[1])['state'], 'ok')

    def test_a_release_is_written_by_its_owner_alone(self):
        # git archive's default modes give group write; a release root runs must not have it,
        # and one built before that rule is closed when it is activated again.
        old = os.umask(0o002)
        self.addCleanup(os.umask, old)
        code, _, err = self.cli('activate', 'HEAD')
        self.assertEqual(code, 0, err)
        current = (self.share / 'current').resolve()
        def open_paths():
            return [p for p in [current, *current.rglob('*')]
                    if not p.is_symlink() and p.stat().st_mode & 0o022]
        self.assertEqual(open_paths(), [])
        (current / 'bin/check').chmod(0o775)
        current.chmod(0o775)
        code, _, err = self.cli('activate', 'HEAD')
        self.assertEqual(code, 0, err)
        self.assertEqual(open_paths(), [])
        self.assertEqual(json.loads(self.cli('verify')[1])['state'], 'ok')

    def test_an_edit_in_place_is_reported_as_drift(self):
        self.cli('activate', 'HEAD')
        (self.share / 'current/README.md').write_text('patched in place\n')
        (self.share / 'current/bin/check').unlink()
        (self.share / 'current/node_modules').mkdir()
        (self.share / 'current/LINK.md').unlink()
        (self.share / 'current/LINK.md').mkdir()
        code, out, _ = self.cli('verify')
        report = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual((report['state'], report['changed'], report['missing']),
                         ('broken', ['LINK.md', 'README.md'], ['bin/check']))

    def test_activate_refuses_to_reuse_a_drifted_release(self):
        self.cli('activate', 'HEAD')
        first = os.readlink(self.share / 'current')
        (self.checkout / 'README.md').write_text('second\n')
        second = self.commit('second')
        self.cli('activate', second)
        (self.share / 'releases' / second / 'README.md').write_text('patched\n')
        self.cli('activate', first.split('/')[-1])
        code, _, err = self.cli('activate', second)
        self.assertEqual(code, 1)
        self.assertIn('move it aside', err)
        self.assertEqual(os.readlink(self.share / 'current'), first)

    def test_an_unknown_ref_changes_nothing(self):
        code, _, err = self.cli('activate', 'no-such-branch')
        self.assertEqual(code, 1)
        self.assertIn('is not a commit', err)
        self.assertFalse((self.share / 'current').exists())
        self.assertEqual(json.loads(self.cli('verify')[1])['state'], 'missing')

    def test_doctor_reports_release_integrity(self):
        self.cli('activate', 'HEAD')
        release = (self.share / 'current').resolve()
        self.assertEqual(doctor.verify_release(release, self.checkout)['state'], 'ok')
        self.assertEqual(doctor.verify_release(self.checkout, self.checkout)['state'], 'unsupported')
        self.assertEqual(doctor.verify_release(release, self.root / 'elsewhere')['state'], 'unverified')


if __name__ == '__main__':
    unittest.main()
