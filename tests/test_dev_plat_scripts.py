"""The scripts of the engineering mode (skills/dev-plat/scripts): the plan check (SDD-SK-38) and
the worktree audit (SDD-SK-39), with its copy in the pstack overlay.

Each test works in a temporary folder. The audit gets a fake `gh` on PATH and a bare origin on disk,
so it reaches no network and no account.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECK_PLAN = ROOT / 'skills/dev-plat/scripts/check-plan.mjs'
AUDITS = (ROOT / 'skills/dev-plat/scripts/worktree-audit.sh',
          ROOT / 'integrations/pstack/overlays/poteto-mode/scripts/worktree-audit.sh')
RULE = ('Tests alone are not sufficient verification. A PR is verified only when its unit, live, '
        'and perf boxes are all checked.')


def good_plan():
    lanes = '\n'.join(f'- [ ] Lane {n}. Save `lane-{n}.png`. Pass when the page shows the list.' for n in range(1, 11))
    return f"""---
title: fixture
---
# Fixture plan

One short intro line.

## How to read this

One box is one unit of work. Each box names the evidence. Check a box only when its evidence exists.
The steps are in playbooks/ of the skill. {RULE}

## Program checklist

### Arm the program
- [ ] Run /goal with the plan.
### Spawn owners
- [ ] Read `git show origin/main:README.md` first.
### PR mechanics
- [ ] Send a status message each 30 minute period.
### Verdict and merge
- [ ] Merge when each box is checked.
### Boot recipe
- [ ] Start the app.

## PR 1. The list page

**Depends on.** Nothing.
**Files.**
- [ ] `app/list.py`
**Build.**
- [ ] Add the list.
**You see.**
- [ ] The list shows three rows.
**Verify, unit.** {RULE}
- [ ] The unit test of the list passes.
**Verify, live.** {RULE} Ten lanes on `fixture-model` at the PR head.
{lanes}
**Verify, perf.** {RULE}
- [ ] Metric. Load time.
- [ ] Probe. A timer.
- [ ] Baseline. The old page.
- [ ] Rule. Not slower.
**Review gate.** None.
**Merge.**
- [ ] Merge the PR.

## Close the program

- [ ] Close the goal.

## Appendix A. Prototype evidence

The prototype ran.
"""


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class PlanCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='plan-check-'))
        self.addCleanup(shutil.rmtree, self.tmp)

    def check(self, text):
        plan = self.tmp / 'plan.md'
        plan.write_text(text)
        return plan, subprocess.run(['node', str(CHECK_PLAN), str(plan)], capture_output=True, text=True, timeout=30)

    def test_a_good_plan_passes_with_one_summary_line_for_each_pr_section(self):
        _, done = self.check(good_plan())
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, '')
        self.assertIn('PR 1. The list page  boxes=19  files=1 build=1 you-see=1 verify-unit=1 verify-live=10 verify-perf=4 review-gate=0 merge=1', done.stdout)
        self.assertIn('1 PR sections, 0 problems', done.stdout)

    def test_a_missing_block_is_a_fault_with_its_file_and_line(self):
        text = good_plan().replace('**Merge.**\n- [ ] Merge the PR.\n', '')
        plan, done = self.check(text)
        self.assertEqual(done.returncode, 1)
        line = text.splitlines().index('## PR 1. The list page') + 1
        self.assertIn(f'{plan}:{line}: PR 1. The list page: sub-blocks are [', done.stderr)
        self.assertIn('1 PR sections, 1 problems', done.stdout)

    def test_each_fault_is_printed_with_its_line(self):
        text = good_plan().replace('One short intro line.', 'One short intro line — with a dash.')
        plan, done = self.check(text.replace('- [ ] Add the list.', '- [ ] Add the list: now.'))
        self.assertEqual(done.returncode, 1)
        lines = text.splitlines()
        self.assertIn(f'{plan}:{lines.index("One short intro line — with a dash.") + 1}: long dash', done.stderr)
        self.assertIn(f'{plan}:{lines.index("- [ ] Add the list.") + 1}: mid-sentence colon', done.stderr)

    def test_no_file_exits_with_2(self):
        done = subprocess.run(['node', str(CHECK_PLAN)], capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 2)


class WorktreeAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='worktree-audit-'))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / 'home'
        self.home.mkdir()
        fakebin = self.tmp / 'bin'
        fakebin.mkdir()
        gh = fakebin / 'gh'
        gh.write_text('#!/bin/sh\necho \'[{"number": 7, "state": "OPEN", "headRefName": "feat/open"}]\'\n')
        gh.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'TMPDIR')}
        self.env.update(PATH=f'{fakebin}{os.pathsep}{self.env["PATH"]}', HOME=str(self.home),
                        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0',
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
                        TMPDIR=str(self.tmp / 'scratch'))
        (self.tmp / 'scratch').mkdir()
        self.repo = self.tmp / 'repo'
        self.git(self.tmp, 'init', '-q', '-b', 'main', str(self.repo))
        (self.repo / 'file').write_text('x\n')
        self.git(self.repo, 'add', '.')
        self.git(self.repo, 'commit', '-qm', 'test: first')
        self.git(self.tmp, 'clone', '-q', '--bare', str(self.repo), str(self.tmp / 'origin.git'))
        self.git(self.repo, 'remote', 'add', 'origin', str(self.tmp / 'origin.git'))
        self.clean = self.tmp / 'wt-clean'
        self.changed = self.tmp / 'wt-changed'
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'fix/done', str(self.clean))
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'feat/work', str(self.changed))
        (self.changed / 'file').write_text('changed\n')

    def git(self, cwd, *args):
        done = subprocess.run(['git', *args], cwd=cwd, env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_one_row_for_each_linked_worktree_with_a_bucket_and_no_change(self):
        for audit in AUDITS:
            with self.subTest(audit=str(audit.relative_to(ROOT))):
                before = self.git(self.repo, 'worktree', 'list', '--porcelain')
                done = subprocess.run(['bash', str(audit), str(self.repo)], env=self.env,
                                      capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 0, done.stderr)
                header, *rows = done.stdout.splitlines()
                self.assertEqual(header.split('\t'), ['SIZE', 'AGE', 'MERGED', 'DIRTY', 'REMOTE', 'PR',
                                                      'LAST_CHAT', 'BUCKET', 'WORKTREE'])
                rows = {row.split('\t')[-1]: row.split('\t') for row in rows}
                self.assertEqual(set(rows), {str(self.clean), str(self.changed)})
                self.assertEqual(rows[str(self.clean)][2:8], ['YES', 'clean', 'no-remote', '-', '-', 'safe'])
                self.assertEqual(rows[str(self.changed)][2:4], ['YES', 'wip:1'])
                self.assertEqual(rows[str(self.changed)][7], 'hold-wip')
                self.assertEqual(self.git(self.repo, 'worktree', 'list', '--porcelain'), before)
                self.assertEqual((self.changed / 'file').read_text(), 'changed\n')
                self.assertEqual(list((self.tmp / 'scratch').iterdir()), [], 'the audit removes its own temporary file')

    def test_an_open_pull_request_holds_a_clean_worktree(self):
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'feat/open', str(self.tmp / 'wt-open'))
        done = subprocess.run(['bash', str(AUDITS[0]), str(self.repo)], env=self.env,
                              capture_output=True, text=True, timeout=60)
        row = next(r.split('\t') for r in done.stdout.splitlines() if r.endswith('/wt-open'))
        self.assertEqual(row[5], '#7/OPEN')
        self.assertEqual(row[7], 'hold-open-pr')


if __name__ == '__main__':
    unittest.main()
