"""A rig the owner starts himself may run paid seats; nothing else asks for that approval."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PLATFORM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM / 'lib'))
from ai_ecosystem import rigapproval  # noqa: E402


class RigApproval(unittest.TestCase):
    def test_the_rig_is_named_or_its_spec_declares_it(self):
        self.assertEqual(rigapproval.rig_name(['kernel']), 'kernel')
        with tempfile.TemporaryDirectory() as d:
            spec = Path(d) / 'rig.yaml'
            spec.write_text('version: "0.2"\nname: engineer-research-agent\npods: []\n')
            self.assertEqual(rigapproval.rig_name([str(spec), '--cwd', d]), 'engineer-research-agent')
            spec.write_text('pods: []\n')
            self.assertIsNone(rigapproval.rig_name([str(spec)]))
        self.assertIsNone(rigapproval.rig_name(['../etc']))
        self.assertIsNone(rigapproval.rig_name([]))

    def test_only_a_start_asks_never_a_plan(self):
        self.assertTrue(rigapproval.needs_approval(['up', 'kernel']))
        self.assertFalse(rigapproval.needs_approval(['up', 'kernel', '--plan']))
        self.assertFalse(rigapproval.needs_approval(['up', '--help']))
        self.assertFalse(rigapproval.needs_approval(['ps']))
        self.assertFalse(rigapproval.needs_approval([]))

    def test_away_from_the_terminal_nothing_is_asked(self):
        run = mock.Mock()
        with mock.patch('sys.stderr'):
            self.assertFalse(rigapproval.approve('kernel', run=run, tty=False))
            self.assertFalse(rigapproval.approve(None, run=run, tty=True))
        run.assert_not_called()

    def test_at_the_terminal_the_owner_is_asked_through_sudo(self):
        run = mock.Mock(return_value=subprocess.CompletedProcess([], 0))
        self.assertTrue(rigapproval.approve('kernel', run=run, tty=True))
        run.assert_called_once_with(['sudo', '/usr/local/bin/ol-rig-approve', 'kernel'])
        run.return_value = subprocess.CompletedProcess([], 1)
        self.assertFalse(rigapproval.approve('kernel', run=run, tty=True))

    def test_the_wrappers_never_boot_the_kernel_rig_on_their_own(self):
        for name in ('bin/rig', 'bin/dev-workspace'):
            text = (PLATFORM / name).read_text()
            self.assertIn('OPENRIG_NO_KERNEL', text, name)
            self.assertIn('rigapproval.approve', text, name)


if __name__ == '__main__':
    unittest.main()
