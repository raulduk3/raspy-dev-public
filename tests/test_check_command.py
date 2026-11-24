"""The check command of the platform (bin/check, SDD-RL-24 to SDD-RL-29) on a small release folder.

The test copies bin/check, the test package and the JUnit runner into a temporary folder that has
no Git data, as an activated release has none, and gives it two probe tests in place of the suite.
So the command runs here without the real suite and without recursion.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

PROBE = '''import json, os, unittest
from pathlib import Path

NAMES = ('DEV_PLATFORM_JEV_GUARD', 'OL_SECRET_LAUNCH_ONLY', 'DEV_PLATFORM_ACCOUNTS_TEMPLATE',
         'OL_ACCOUNTS_STATE', 'DEV_PLATFORM_ACCOUNT_SELECTION')


class Probe(unittest.TestCase):
    def test_probe(self):
        out = Path(os.environ['PROBE_OUT']) / (Path(__file__).stem + '.json')
        out.write_text(json.dumps({name: os.environ.get(name) for name in NAMES}))
        self.assertNotEqual(os.environ.get('PROBE_FAIL'), Path(__file__).stem)
'''


class CheckCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='check-command-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.release = self.tmp / 'release'
        (self.release / 'bin').mkdir(parents=True)
        (self.release / 'tests/support').mkdir(parents=True)
        shutil.copy(ROOT / 'bin/check', self.release / 'bin/check')
        shutil.copy(ROOT / 'tests/__init__.py', self.release / 'tests/__init__.py')
        shutil.copy(ROOT / 'tests/support/junit_run.py', self.release / 'tests/support/junit_run.py')
        for name in ('test_alpha.py', 'test_beta.py'):
            (self.release / 'tests' / name).write_text(PROBE)
        # The two scripts with no shell ending that the command examines too.
        for rel in ('bin/new-repo', 'skills/loop/scripts/ghx'):
            path = self.release / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('#!/usr/bin/env bash\necho ok\n')
        (self.release / 'hooks').mkdir()
        (self.release / 'hooks/good.sh').write_text('#!/usr/bin/env bash\nif true; then echo ok; fi\n')
        self.out = self.tmp / 'out'
        self.out.mkdir()
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'TMPDIR')}
        self.env.update(HOME=str(self.tmp / 'home'), PROBE_OUT=str(self.out),
                        GIT_CEILING_DIRECTORIES=str(self.tmp))

    def check(self, **env):
        return subprocess.run(['bash', str(self.release / 'bin/check')], cwd=self.tmp, env={**self.env, **env},
                              capture_output=True, text=True, timeout=120)

    def probes(self):
        return {p.stem: json.loads(p.read_text()) for p in self.out.glob('*.json')}

    def test_it_runs_each_test_file_and_a_failed_test_fails_the_command(self):
        done = self.check()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(set(self.probes()), {'test_alpha', 'test_beta'})
        self.assertNotEqual(self.check(PROBE_FAIL='test_beta').returncode, 0)

    def test_a_syntax_fault_in_a_shell_script_stops_it_before_a_test(self):
        for rel in ('hooks/bad.sh', 'skills/loop/scripts/ghx'):
            with self.subTest(script=rel):
                path = self.release / rel
                kept = path.read_text() if path.exists() else None
                path.write_text('#!/usr/bin/env bash\nif then fi (\n')
                done = self.check()
                self.assertNotEqual(done.returncode, 0)
                self.assertIn(rel, done.stderr)
                self.assertEqual(self.probes(), {}, 'no test ran')
                path.unlink() if kept is None else path.write_text(kept)

    def test_the_packages_of_the_pi_runtime_are_left_out_in_a_release(self):
        bad = self.release / 'integrations/pi/node_modules/pkg/bad.sh'
        bad.parent.mkdir(parents=True)
        bad.write_text('if then fi (\n')
        done = self.check()
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_an_absent_tool_is_named_and_the_exit_code_is_2(self):
        tools = self.tmp / 'tools'
        tools.mkdir()
        for tool in ('bash', 'env', 'dirname', 'readlink', 'git', 'python3', 'jq'):
            (tools / tool).symlink_to(shutil.which(tool))
        (tools / 'jq').unlink()
        done = self.check(PATH=str(tools))
        self.assertEqual((done.returncode, done.stderr.strip()), (2, 'check: missing jq'))
        # A python3 with no site packages has no PyYAML.
        (tools / 'jq').symlink_to(shutil.which('jq'))
        (tools / 'python3').unlink()
        (tools / 'python3').write_text(f'#!/bin/sh\nexec {shutil.which("python3")} -S "$@"\n')
        (tools / 'python3').chmod(0o755)
        done = self.check(PATH=str(tools))
        self.assertEqual(done.returncode, 2)
        self.assertIn('check: missing PyYAML', done.stderr)
        self.assertEqual(self.probes(), {})

    def test_the_tests_get_no_account_credential_or_paid_call_of_the_machine(self):
        done = self.check(DEV_PLATFORM_JEV_GUARD='1', OL_SECRET_LAUNCH_ONLY='0',
                          OL_ACCOUNTS_STATE=str(self.tmp / 'home/accounts'),
                          DEV_PLATFORM_ACCOUNT_SELECTION=str(self.tmp / 'home/selection.json'))
        self.assertEqual(done.returncode, 0, done.stderr)
        for name, seen in self.probes().items():
            with self.subTest(probe=name):
                self.assertEqual(seen['DEV_PLATFORM_JEV_GUARD'], '0')
                self.assertEqual(seen['OL_SECRET_LAUNCH_ONLY'], '1')
                self.assertEqual(seen['DEV_PLATFORM_ACCOUNTS_TEMPLATE'],
                                 str(self.release / 'tests/support/accounts.json'))
                for name in ('OL_ACCOUNTS_STATE', 'DEV_PLATFORM_ACCOUNT_SELECTION'):
                    self.assertFalse(Path(seen[name]).exists(), seen[name])
                    self.assertTrue(seen[name].startswith('/nonexistent/'), seen[name])

    def test_a_named_report_file_gets_one_junit_report_of_the_same_tests(self):
        self.check()
        plain = self.probes()
        for p in self.out.glob('*.json'):
            p.unlink()
        report = self.tmp / 'report.xml'
        done = self.check(CHECK_JUNIT=str(report))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.probes(), plain, 'the same environment with and without a report')
        cases = ET.parse(report).getroot().findall('./testsuite/testcase')
        self.assertEqual(sorted(c.get('file') for c in cases), ['tests/test_alpha.py', 'tests/test_beta.py'])
        self.assertTrue(all(len(c) == 0 for c in cases), 'each case passed')
        self.assertNotEqual(self.check(CHECK_JUNIT=str(report), PROBE_FAIL='test_alpha').returncode, 0)
        failed = [c.get('file') for c in ET.parse(report).getroot().iter('testcase') if c.find('failure') is not None]
        self.assertEqual(failed, ['tests/test_alpha.py'])


if __name__ == '__main__':
    unittest.main()
