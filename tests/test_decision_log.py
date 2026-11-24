"""The decision log helper of the show-me-your-work skill (skills/show-me-your-work/scripts/log.sh, SDD-SK-37)."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / 'skills/show-me-your-work/scripts/log.sh'
HEADER = 'ts\tphase\tdecision\twhy\tevidence\tresult'


class DecisionLog(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='decision-log-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.file = self.tmp / 'new/folder/decisions.tsv'

    def log(self, *cells):
        return subprocess.run(['bash', str(LOG), str(self.file), *cells], capture_output=True, text=True, timeout=10)

    def test_each_decision_is_one_row_of_a_time_stamp_and_five_cells_under_one_header(self):
        self.assertEqual(self.log('plan', 'take A', 'a\tb', 'line\nbreak', '=SUM(A1)').returncode, 0)
        self.assertEqual(self.log('+1', '-x', '@me', 'ok\r', 'done').returncode, 0)
        lines = self.file.read_text().split('\n')
        self.assertEqual(lines[0], HEADER)
        self.assertEqual(lines[-1], '')
        rows = [line.split('\t') for line in lines[1:-1]]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(len(row), 6)
            self.assertRegex(row[0], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')
        self.assertEqual(rows[0][1:], ['plan', 'take A', 'a b', 'line break', "'=SUM(A1)"])
        self.assertEqual(rows[1][1:], ["'+1", "'-x", "'@me", 'ok ', 'done'])

    def test_the_helper_never_truncates_the_file(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_text(HEADER + '\nold\trow\tstays\there\tx\ty\n')
        self.log('a', 'b', 'c', 'd', 'e')
        lines = self.file.read_text().splitlines()
        self.assertEqual(lines[:2], [HEADER, 'old\trow\tstays\there\tx\ty'])
        self.assertEqual(len(lines), 3)

    def test_a_wrong_count_of_arguments_prints_the_usage_and_exits_with_1(self):
        done = self.log('only', 'four', 'cells', 'here')
        self.assertEqual(done.returncode, 1)
        self.assertTrue(re.match(r'usage: log\.sh <logfile>', done.stderr), done.stderr)
        self.assertFalse(self.file.exists())


if __name__ == '__main__':
    unittest.main()
