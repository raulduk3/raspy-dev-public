"""Real harmless supervisor/process probes: never touch installed loop records."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from test_stability import Fixture, PLATFORM, RIG

RUNNER = PLATFORM / 'skills/loop/scripts/worker-run.py'


class WorkerIdentityTests(Fixture):
    def supervisor(self, issue=1, ctl=None, cwd=None):
        workers = (ctl or self.ctl()) / '2026-01-01/workers'
        workers.mkdir(parents=True, exist_ok=True)
        result = workers / f'{issue}.exit'
        release = self.base / f'release-{issue}'
        code = ('from pathlib import Path; import time; '
                f'p=Path({str(release)!r});\nwhile not p.exists(): time.sleep(.02)')
        process = subprocess.Popen([sys.executable, str(RUNNER), '15', str(result), '--',
                                    sys.executable, '-c', code], cwd=cwd or self.repo,
                                   env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        def cleanup():
            release.touch()
            try:
                process.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.communicate(timeout=8)
        self.addCleanup(cleanup)
        result.with_suffix('.pid').write_text(str(process.pid))
        receipt = result.with_suffix('.identity.json')
        deadline = time.monotonic() + 4
        while not receipt.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(receipt.exists(), 'actual supervisor must record identity before work')
        return process, result, release

    def test_live_supervisor_counts_and_completion_stops_counting(self):
        process, result, release = self.supervisor()
        self.assertIn(f'issue #1 pid {process.pid}', self.loop('status').stdout)
        release.touch()
        process.communicate(timeout=4)
        self.assertTrue(result.exists())
        self.assertIn('running:\n  none', self.loop('status').stdout)

    def test_unrelated_live_pid_invalid_and_dead_records_are_not_workers(self):
        workers = self.ctl() / '2026-01-01/workers'
        workers.mkdir(parents=True)
        for issue, pid in enumerate((os.getpid(), 999999999, 'not-a-pid'), 1):
            (workers / f'{issue}.pid').write_text(str(pid))
        self.assertIn('running:\n  none', self.loop('status').stdout)
        os.kill(os.getpid(), 0)

    def test_other_repository_and_unowned_legacy_records_are_not_counted(self):
        process, result, _ = self.supervisor(2, self.base / 'state/other__repo')
        legacy = self.base / 'state/old-day'
        legacy.mkdir()
        (legacy / 'worker-391.pid').write_text(str(process.pid))
        self.assertIn('running:\n  none', self.loop('status').stdout)
        os.kill(process.pid, 0)

    def test_wrong_checkout_cannot_claim_this_repository(self):
        other = self.base / 'other'
        self.run_cmd('git', 'init', '-q', other)
        self.supervisor(cwd=other)
        self.assertIn('running:\n  none', self.loop('status').stdout)

    def test_receipt_reuse_and_copied_ledger_do_not_match(self):
        process, result, _ = self.supervisor()
        receipt = result.with_suffix('.identity.json')
        identity = json.loads(receipt.read_text())
        identity['started'] = 'a previous occupant of this PID'
        receipt.write_text(json.dumps(identity))
        self.assertIn('identity changed', self.loop('status', expected=1).stdout)
        for verb in ('go', 'tick', 'resume'):
            args = (verb, '2') if verb == 'resume' else (verb,)
            self.assertIn('identity changed', self.loop(*args, expected=1).stdout)
            self.assertFalse((self.ctl() / 'dispatch-lock').exists())
        receipt.unlink()
        result.with_suffix('.pid').unlink()
        result.with_name('9.pid').write_text(str(process.pid))
        self.assertIn('running:\n  none', self.loop('status').stdout)

    def test_pre_receipt_supervisor_is_still_live_and_caps_dispatch(self):
        process, result, _ = self.supervisor()
        result.with_suffix('.identity.json').unlink()
        self.assertIn(f'issue #1 pid {process.pid}', self.loop('status').stdout)
        self.setup_remote()
        self.loop('start', RIG)
        self.assertIn('cap reached', self.loop('resume', '2', env=dict(self.env, LOOP_CAP='1')).stdout)
