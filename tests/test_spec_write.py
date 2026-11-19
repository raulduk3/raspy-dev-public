"""dev-spec changes a specification through commands (docs/spec/SDD.md, area SW)."""
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_spec_tree import CLI, Fixture, sh  # noqa: E402

SDD = """\
# SDD

## 1. System requirements

**ID-01.** The product MUST answer each call.
<!-- id: SYS-ID-01 -->

## 2. Calls
<!-- section: SDD-2 | sys: SYS-ID-01 -->

**CA-01.** When a call arrives, the service MUST answer the call.
<!-- id: SDD-CA-01 | tdd: TDD-1.1, TDD-1.2 -->

- Actor: a caller.
- Verified by: the answer test.

**CA-02.** When a call ends, the service MUST store the call record.
<!-- id: SDD-CA-02 | tdd: TDD-1.2 | status: implemented -->

- Trigger: the end of a call.
- Verified by: the store test.

**CA-03.** The service MUST refuse a call with no number.
<!-- id: SDD-CA-03 | tdd: none -->

- Verified by: the refuse test.

## 3. Records
<!-- section: SDD-3 | sys: SYS-ID-01 -->

**RE-01.** The service MUST keep each call record for one year.
<!-- id: SDD-RE-01 | tdd: none -->

- Verified by: the retention test.
"""

TDD = """\
# TDD

## 1. Calls

#### TDD-1.1 Answer
<!-- id: TDD-1.1 | implements: SDD-CA-01 | code: src/answer.ts | tests: tests/pass.test.ts -->

The handler answers.

#### TDD-1.2 Store
<!-- id: TDD-1.2 | implements: SDD-CA-01, SDD-CA-02 | code: src/store.ts | tests: none -->

The store keeps the record.
"""

GOOD = """When a call ends, the service MUST store one call record.

- Actor: the service.
- Verified by: the store test.
"""


class Write(Fixture):
    def setUp(self):
        super().setUp()
        self.write('docs/spec/SDD.md', SDD)
        self.write('docs/spec/TDD.md', TDD)
        self.commit('standard')

    def spec(self, *args, text=None, expected=0):
        done = subprocess.run([sys.executable, '-I', str(CLI), *args, '--config', str(self.config)], env=self.env, input=text,
                              capture_output=True, text=True, cwd=self.repo)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        return done

    def sdd(self):
        return (self.repo / 'docs/spec/SDD.md').read_text()

    def tdd(self):
        return (self.repo / 'docs/spec/TDD.md').read_text()

    def state(self, name):
        return self.tmp / 'state/spec/fixture' / name

    def answers(self, done, **other):
        """The number and the answers of the confirm line that a proposal prints, with a different answer for some items."""
        line = [line for line in done.stdout.splitlines() if line.startswith('dev-spec confirm ')][-1].split()[2:]
        return [line[0]] + [f'{i}={other.get(i.replace("-", "_").replace(".", "_"), "same")}' for i in (a.split('=')[0] for a in line[1:])]


class Explain(Write):
    def test_find_lists_the_matching_items_in_the_order_of_the_sections(self):   # SDD-SW-15
        lines = self.spec('find', 'call record').stdout.splitlines()
        self.assertEqual([line.split()[0] for line in lines], ['SYS-ID-01', 'CA-01', 'CA-02', 'CA-03', 'RE-01', 'TDD-1.2'])
        self.assertIn('[docs/spec/SDD.md:17]', lines[2])

    def test_why_prints_the_chain_of_an_item_and_of_a_path(self):   # SDD-SW-14
        chain = self.spec('why', 'CA-02').stdout
        self.assertEqual([line.split()[0] for line in chain.splitlines()], ['SYS-ID-01', 'CA-02', 'TDD-1.2', 'code:'])
        chain = self.spec('why', 'src/answer.ts').stdout
        self.assertIn('src/answer.ts is named by TDD-1.1', chain)
        self.assertIn('which implements CA-01', chain)
        self.assertIn('under SYS-ID-01', chain)
        done = self.spec('why', 'src/alone.ts', expected=1)
        self.assertIn('no TDD item names src/alone.ts', done.stdout)


class Change(Write):
    def test_a_change_is_a_proposal_until_each_related_item_has_an_answer(self):   # SDD-SW-03, SDD-SW-04, SDD-SW-10
        before = self.sdd()
        done = self.spec('set', 'CA-02', '--text', '-', text=GOOD, expected=3)
        self.assertEqual(self.sdd(), before)   # nothing is written
        shown = [line.split()[1] for line in done.stdout.splitlines() if line.startswith('--- ')]
        # its TDD item, the item that shares that TDD item, the system requirement, its neighbours, then shared terms:
        # the same level first, then the other level (a TDD item of a different SDD item)
        self.assertEqual(shown, ['TDD-1.2', 'CA-01', 'SYS-ID-01', 'CA-03', 'RE-01', 'TDD-1.1'])
        self.assertIn('**CA-01.** When a call arrives, the service MUST answer the call.', done.stdout)
        self.assertIn('dev-spec confirm 1 TDD-1.2=same CA-01=same SYS-ID-01=same CA-03=same RE-01=same TDD-1.1=same', done.stdout)
        done = self.spec('confirm', '1', 'TDD-1.2=same', 'CA-01=same', expected=1)
        self.assertIn('SW-04: no answer for: SYS-ID-01, CA-03, RE-01, TDD-1.1', done.stderr)
        self.assertEqual(self.sdd(), before)
        self.spec('confirm', *self.answers(done=self.spec('set', 'CA-02', '--text', '-', text=GOOD, expected=3)))
        after = self.sdd()
        self.assertIn('**CA-02.** When a call ends, the service MUST store one call record.\n<!-- id: SDD-CA-02 | tdd: TDD-1.2 -->\n\n'
                      '- Actor: the service.\n- Verified by: the store test.\n\n**CA-03.**', after)   # the status and the old part are gone
        record = json.loads(self.state('journal.jsonl').read_text().splitlines()[-1])
        self.assertEqual((record['command'], record['target'], record['number']), ('set', 'CA-02', 2))
        import hashlib
        self.assertEqual(record['files']['docs/spec/SDD.md'], hashlib.sha256(after.encode()).hexdigest())
        self.assertEqual(json.loads((self.tmp / 'tree.data.json').read_text()) if (self.tmp / 'tree.data.json').exists() else {}, {})

    def test_a_text_that_breaks_the_form_is_refused_and_nothing_is_written(self):   # SDD-SW-06
        before = self.sdd()
        long = 'When a call ends, the service MUST store the record ' + 'and the next record ' * 5 + 'in the store.\n\n- Verified by: a test.\n'
        done = self.spec('set', 'CA-02', '--text', '-', text=long, expected=1)
        self.assertIn('SW-06: the item breaks the item form', done.stderr)
        self.assertIn('SP-08: 33 words', done.stderr)
        done = self.spec('set', 'CA-02', '--text', '-', text='The service stores the record.\n\n- Note: a note.\n', expected=1)
        self.assertIn('SP-07: no MUST', done.stderr)
        self.assertIn('SP-10: part Note', done.stderr)
        self.assertEqual(self.sdd(), before)
        self.assertFalse(self.state('proposals').exists())
        done = self.spec('set', 'TDD-1.1', '--text', '-', text='Answer\n\nThe handler MUST answer.\n', expected=1)
        self.assertIn('SP-09', done.stderr)

    def test_a_conflict_writes_nothing_and_a_change_answer_stays_open(self):   # SDD-SW-04, SDD-SW-05
        before = self.sdd()
        done = self.spec('set', 'CA-02', '--text', '-', text=GOOD, expected=3)
        done = self.spec('confirm', *self.answers(done, CA_01='conflict'), expected=1)
        self.assertIn('CA-02 contradicts CA-01. Nothing is written.', done.stderr)
        self.assertEqual(self.sdd(), before)
        done = self.spec('set', 'CA-02', '--text', '-', text=GOOD, expected=3)
        done = self.spec('confirm', *self.answers(done, TDD_1_2='change'))
        self.assertIn('Open items that must change also: TDD-1.2', done.stdout)
        self.assertEqual(self.spec('open', expected=1).stdout.split()[0], 'TDD-1.2')
        done = self.spec('set', 'TDD-1.2', '--text', '-', text='Store\n\nThe store keeps one record for each call.\n', expected=3)
        self.spec('confirm', *self.answers(done))
        self.assertIn('#### TDD-1.2 Store\n<!-- id: TDD-1.2 | implements: SDD-CA-01, SDD-CA-02 | code: src/store.ts | tests: none -->\n\n'
                      'The store keeps one record for each call.\n', self.tdd())
        self.assertEqual(self.spec('open').stdout, '')   # the change of TDD-1.2 closed it

    def test_a_proposal_is_refused_when_its_file_changed_after_it(self):   # SDD-SW-07
        done = self.spec('set', 'CA-03', '--text', '-', text='The service MUST refuse a call that has no number.\n\n- Verified by: the refuse test.\n', expected=3)
        self.write('docs/spec/SDD.md', SDD + '\n')
        done = self.spec('confirm', *self.answers(done), expected=1)
        self.assertIn('docs/spec/SDD.md changed after the proposal', done.stderr)


class Relations(Write):
    def do(self, *args, text=None):
        done = self.spec(*args, text=text, expected=3)
        self.spec('confirm', *self.answers(done))
        return done

    def test_a_link_is_written_on_its_two_sides(self):   # SDD-SW-08
        self.do('link', 'TDD-1.1', 'CA-03')
        self.assertIn('<!-- id: TDD-1.1 | implements: SDD-CA-01, SDD-CA-03 |', self.tdd())
        self.assertIn('<!-- id: SDD-CA-03 | tdd: TDD-1.1 -->', self.sdd())
        self.do('unlink', 'TDD-1.2', 'CA-01')
        self.assertIn('<!-- id: TDD-1.2 | implements: SDD-CA-02 |', self.tdd())
        self.assertIn('<!-- id: SDD-CA-01 | tdd: TDD-1.1 -->', self.sdd())
        self.assertEqual(self.tree()['faults'], [])
        self.assertEqual(self.tree()['repositories']['r']['one_sided'], [])

    def test_a_path_is_bound_only_when_it_exists(self):   # SDD-SW-02
        self.do('bind', 'TDD-1.2', '--test', 'tests/pass.test.ts')
        self.assertIn('| code: src/store.ts | tests: tests/pass.test.ts -->', self.tdd())
        done = self.spec('bind', 'TDD-1.2', '--code', 'src/gone.ts', expected=1)
        self.assertIn('src/gone.ts does not exist in this checkout', done.stderr)
        self.do('unbind', 'TDD-1.2', '--code', 'src/store.ts')
        self.assertIn('| code: none | tests: tests/pass.test.ts -->', self.tdd())

    def test_a_new_item_gets_the_next_number_and_a_removed_number_is_not_used_again(self):   # SDD-SW-09, SDD-SW-07
        text = 'While a call is active, the service MUST keep the line open.\n\n- Verified by: the line test.\n'
        self.do('add', '--level', 'sdd', '--section', '2', '--area', 'CA', '--text', '-', text=text)
        self.assertIn('- Verified by: the refuse test.\n\n**CA-04.** While a call is active, the service MUST keep the line open.\n'
                      '<!-- id: SDD-CA-04 | tdd: none -->\n\n- Verified by: the line test.\n\n## 3. Records', self.sdd())
        self.do('remove', 'CA-04')
        self.assertIn('- Verified by: the refuse test.\n\n<!-- retired: SDD-CA-04 -->\n\n## 3. Records', self.sdd())
        self.do('add', '--level', 'sdd', '--section', '2', '--area', 'CA', '--text', '-', text=text)
        self.assertIn('**CA-05.** While a call is active', self.sdd())
        self.assertNotIn('**CA-04.**', self.sdd())
        self.do('remove', 'CA-02')   # its TDD item loses the link, so the removal leaves no link to no item
        self.assertIn('<!-- id: TDD-1.2 | implements: SDD-CA-01 |', self.tdd())
        self.assertEqual(self.tree()['faults'], [])
        self.do('add', '--level', 'tdd', '--section', '1', '--implements', 'CA-03', '--text', '-', text='Refuse\n\nThe handler refuses.\n')
        # `add` writes the link in the form that `link` writes.
        self.assertIn('#### TDD-1.3 Refuse\n<!-- id: TDD-1.3 | implements: SDD-CA-03 | code: none | tests: none -->\n\nThe handler refuses.\n', self.tdd())
        self.assertIn('<!-- id: SDD-CA-03 | tdd: TDD-1.3 -->', self.sdd())

    def test_renumber_changes_an_item_that_the_base_branch_does_not_hold(self):   # SDD-SW-02, SDD-SW-08
        self.assertIn('names no base branch', self.spec('renumber', 'TDD-1.2', 'TDD-1.9', expected=1).stderr)
        self.entry['git'] = {'base': 'main'}
        self.save()
        sh(self.repo, 'git', 'checkout', '-q', '-b', 'work')
        self.do('add', '--level', 'tdd', '--section', '1', '--implements', 'CA-03', '--text', '-', text='Refuse\n\nThe handler refuses.\n')
        self.do('add', '--level', 'tdd', '--section', '1', '--text', '-', text='Log\n\nThe handler logs. It follows TDD-1.3, not TDD-1.31.\n')
        self.write('src/refuse.ts', '// TDD-1.3\n')
        sh(self.repo, 'git', 'add', 'src/refuse.ts')
        self.assertIn('TDD-1.2 is on the base branch (main)', self.spec('renumber', 'TDD-1.2', 'TDD-1.9', expected=1).stderr)
        self.assertIn('TDD-1.4 is used', self.spec('renumber', 'TDD-1.3', 'TDD-1.4', expected=1).stderr)
        self.assertIn('a number of the same section', self.spec('renumber', 'TDD-1.3', 'TDD-2.1', expected=1).stderr)
        self.assertIn('takes a TDD item', self.spec('renumber', 'CA-03', 'CA-09', expected=1).stderr)
        done = self.spec('renumber', 'TDD-1.3', 'TDD-1.7', expected=3)
        self.assertIn('src/refuse.ts:1', done.stdout)   # a file outside the specification that names the item: the command does not change it
        self.assertIn('#### TDD-1.3 Refuse', self.tdd())   # nothing is written yet
        self.spec('confirm', *self.answers(done))
        self.assertIn('#### TDD-1.7 Refuse\n<!-- id: TDD-1.7 | implements: SDD-CA-03 |', self.tdd())
        self.assertIn('It follows TDD-1.7, not TDD-1.31.', self.tdd())
        self.assertIn('<!-- id: SDD-CA-03 | tdd: TDD-1.7 -->', self.sdd())
        self.assertNotIn('TDD-1.3 ', self.tdd() + self.sdd())
        self.assertEqual(self.tree()['faults'], [])
        self.do('remove', 'TDD-1.4')   # a retired number is a used number
        self.assertIn('TDD-1.4 is used', self.spec('renumber', 'TDD-1.7', 'TDD-1.4', expected=1).stderr)
        self.do('renumber', 'TDD-1.7', 'TDD-1.3')   # the old number is free again
        self.assertIn('#### TDD-1.3 Refuse', self.tdd())

    def test_a_number_that_only_a_text_names_is_not_a_used_number(self):   # SDD-SW-09
        self.do('add', '--level', 'tdd', '--section', '1', '--text', '-',
                text='Refuse\n\nThe handler refuses. A later item (TDD-1.7) and SDD-CA-09 give the details.\n\n```\n#### TDD-1.9 An example\n```\n')
        self.assertIn('#### TDD-1.3 Refuse', self.tdd())
        self.do('add', '--level', 'tdd', '--section', '1', '--text', '-', text='Log\n\nThe handler logs.\n')
        self.assertIn('#### TDD-1.4 Log', self.tdd())
        self.do('add', '--level', 'sdd', '--section', '2', '--area', 'CA', '--text', '-',
                text='While a call is active, the service MUST keep the line open.\n\n- Verified by: the line test.\n')
        self.assertIn('**CA-04.** While a call is active', self.sdd())

    def test_a_section_with_no_item_and_a_system_requirement_with_no_section_leave(self):   # SDD-SW-02, SDD-SW-09
        self.write('docs/spec/SDD.md', SDD.replace('\n## 2. Calls', '\n**ID-02.** The product MUST call each requester back.\n<!-- id: SYS-ID-02 -->\n\n'
                                                   '- Limits: one line.\n\n## 2. Calls')
                   + '\n## 4. Callbacks\n<!-- section: SDD-4 | sys: SYS-ID-02 -->\n\nThe callback line is closed.\n\n<!-- retired: SDD-CB-01 -->\n')
        self.commit('a section with no item')
        self.assertIn('SYS-ID-02 is the owner of: 4. Callbacks', self.spec('remove', 'SYS-ID-02', expected=1).stderr)
        self.assertIn('holds: CA-01, CA-02, CA-03', self.spec('remove', '--level', 'sdd', '--section', '2', expected=1).stderr)
        self.assertIn('holds: SYS-ID-01, SYS-ID-02', self.spec('remove', '--level', 'sdd', '--section', '1', expected=1).stderr)
        self.assertIn('give one identifier, or --level', self.spec('remove', expected=1).stderr)
        done = self.spec('remove', '--level', 'sdd', '--section', '4', expected=3)
        self.assertIn('The callback line is closed.', done.stdout)                     # the proposal shows the text that leaves
        self.assertIn('--- SYS-ID-02  (the system requirement above it', done.stdout)   # and the owner of the section
        self.assertIn('## 4. Callbacks', self.sdd())                                   # nothing is written yet
        self.spec('confirm', *self.answers(done))
        self.assertTrue(self.sdd().endswith('- Verified by: the retention test.\n'), self.sdd()[-200:])
        # The retired comment left with the section. Its number stays used.
        self.do('add', '--level', 'sdd', '--section', '3', '--area', 'CB', '--text', '-',
                text='While a call is active, the service MUST keep the line open.\n\n- Verified by: the line test.\n')
        self.assertIn('**CB-02.**', self.sdd())
        self.assertIn('SYS-ID-01 is the owner of: 2. Calls, 3. Records', self.spec('remove', 'SYS-ID-01', expected=1).stderr)
        done = self.spec('remove', 'SYS-ID-02', expected=3)
        self.assertIn('- Limits: one line.', done.stdout)
        self.spec('confirm', *self.answers(done))
        self.assertIn('<!-- id: SYS-ID-01 -->\n\n<!-- retired: SYS-ID-02 -->\n\n## 2. Calls', self.sdd())
        self.assertEqual(self.tree()['faults'], [])
        self.assertIn('SYS-ID-02 is no item', self.spec('remove', 'SYS-ID-02', expected=1).stderr)

    def test_the_owner_of_a_section_is_one_command(self):   # SDD-SW-02
        self.write('docs/spec/SDD.md', SDD.replace('## 3. Records\n<!-- section: SDD-3 | sys: SYS-ID-01 -->\n', '## 3. Records\n'))
        self.commit('no owner')
        self.assertEqual(len(self.tree()['faults']), 1)
        self.do('own', '3', 'SYS-ID-01')
        self.assertIn('## 3. Records\n<!-- section: SDD-3 | sys: SYS-ID-01 -->\n', self.sdd())
        self.assertEqual(self.tree()['faults'], [])

    def test_one_item_gets_one_more_owner_and_loses_it(self):   # SDD-SW-02, SDD-SP-04
        done = self.do('own', 'RE-01', 'SYS-ID-01')
        self.assertIn('--- SYS-ID-01  (', done.stdout)
        self.assertIn('<!-- id: SDD-RE-01 | tdd: none | sys: SYS-ID-01 -->', self.sdd())
        self.assertEqual(self.tree()['faults'], [])
        self.assertIn('SYS-ID-9 is no system requirement', self.spec('own', 'RE-01', 'SYS-ID-9', expected=1).stderr)
        self.do('own', 'RE-01', 'none')
        self.assertIn('<!-- id: SDD-RE-01 | tdd: none -->', self.sdd())

    def test_remove_takes_out_an_old_block_that_only_a_trace_comment_names(self):   # SDD-SW-02
        old = ('<!-- id: SDD-3.1 | tdd: TDD-1.1 | status: implemented -->\n- One process runs in each deployment.\n\n'
               '```text\n# no heading: a code block\n```\n\n')
        self.write('docs/spec/SDD.md', SDD.replace('**RE-01.**', old + '**RE-01.**'))
        self.write('docs/spec/TDD.md', TDD.replace('implements: SDD-CA-01 |', 'implements: SDD-CA-01, SDD-3.1 |'))
        self.commit('an old block')
        self.assertEqual(len(self.tree()['faults']), 1)   # TDD-1.1 names an identifier that is no item
        self.assertIn('SDD-9.9 is no item', self.spec('remove', 'SDD-9.9', expected=1).stderr)
        done = self.do('remove', 'SDD-3.1')
        self.assertIn('--- TDD-1.1  (', done.stdout)
        self.assertIn('names the old block', done.stdout)
        self.assertIn('<!-- section: SDD-3 | sys: SYS-ID-01 -->\n\n**RE-01.** The service MUST keep', self.sdd())
        self.assertNotIn('One process runs', self.sdd())
        self.assertIn('<!-- id: TDD-1.1 | implements: SDD-CA-01 | code:', self.tdd())
        self.assertEqual(self.tree()['faults'], [])

    def test_the_text_of_a_section_outside_its_items_is_one_command(self):   # SDD-SW-02
        self.do('text', '--level', 'sdd', '--section', '3', '--text', '-', text='The service keeps records.\n\n- One list.\n')
        self.assertIn('## 3. Records\n<!-- section: SDD-3 | sys: SYS-ID-01 -->\n\nThe service keeps records.\n\n- One list.\n\n**RE-01.**', self.sdd())
        self.do('text', '--level', 'sdd', '--section', '3', '--text', '-', text='Records.\n')
        self.assertIn('<!-- section: SDD-3 | sys: SYS-ID-01 -->\n\nRecords.\n\n**RE-01.**', self.sdd())
        self.do('text', '--level', 'sdd', '--text', '-', text='This document states what the service does.\n')
        self.assertTrue(self.sdd().startswith('# SDD\n\nThis document states what the service does.\n\n## 1. System requirements\n'))
        self.do('text', '--level', 'tdd', '--section', '1', '--text', '-', text='The design of the call path.\n')
        self.assertIn('## 1. Calls\n\nThe design of the call path.\n\n#### TDD-1.1 Answer\n', self.tdd())
        before = self.sdd()
        for bad, reason in (('**RE-02.** The service MUST do more.\n', 'holds an item'), ('### 3.1 More\n', 'holds an item'),
                            ('The service MUST keep records.\n', 'SP-09')):
            self.assertIn(reason, self.spec('text', '--level', 'sdd', '--section', '3', '--text', '-', text=bad, expected=1).stderr)
        # the chapter of the system requirements holds items below its heading: no text command changes them
        self.assertIn('the text of today holds an item', self.spec('text', '--level', 'sdd', '--section', '1', '--text', '-', text='x\n', expected=1).stderr)
        self.assertEqual(self.sdd(), before)
        self.assertEqual(self.tree()['faults'], [])

    def test_a_command_removes_the_status_of_an_item_that_it_changes(self):   # SDD-SP-13
        self.write('docs/spec/TDD.md', TDD.replace('| tests: none -->', '| tests: none | status: pending:#15 -->'))
        self.commit('a status in the TDD')
        self.do('link', 'TDD-1.1', 'CA-02')
        self.assertIn('<!-- id: SDD-CA-02 | tdd: TDD-1.2, TDD-1.1 -->', self.sdd())   # the status "implemented" is gone
        self.do('bind', 'TDD-1.2', '--test', 'tests/pass.test.ts')
        self.assertIn('| code: src/store.ts | tests: tests/pass.test.ts | gap: #15 -->', self.tdd())   # a cited task stays as the gap
        done = self.spec('set', 'TDD-1.2', '--gap', 'none', expected=3)   # a change of the gap only has no related item
        self.spec('confirm', done.stdout.split()[1].rstrip(':'))
        self.assertIn('| code: src/store.ts | tests: tests/pass.test.ts -->', self.tdd())

    def test_an_open_item_belongs_to_the_checkout_of_its_proposal(self):   # SDD-SW-05
        done = self.spec('set', 'CA-02', '--text', '-', text=GOOD, expected=3)
        self.spec('confirm', *self.answers(done, TDD_1_2='change'))
        self.assertEqual(self.spec('open', expected=1).stdout.split()[0], 'TDD-1.2')
        second = self.tmp / 'second'
        sh(self.repo, 'git', 'worktree', 'add', '-q', '--detach', str(second))
        done = subprocess.run([sys.executable, '-I', str(CLI), 'open', '--config', str(self.config)], env=self.env, capture_output=True, text=True, cwd=second)
        self.assertEqual((done.returncode, done.stdout), (0, ''), done.stderr)
        self.assertTrue(self.state('lock').exists())   # one write command at a time for each project

    def test_a_command_works_in_a_worktree_of_the_registered_repository(self):   # SDD-PJ-09
        (self.repo / 'tree.json').write_text(json.dumps({'schema': 'dev-platform.spec-tree@1', 'name': 'fixture', 'top': None,
                                                         'repositories': [{'name': 'r', 'path': '.', 'layout': 'single'}]}))
        (self.repo / '.git/info/exclude').write_text('tree.json\ntree.html\ntree.data.json\n')
        (self.tmp / 'repos.conf').write_text(f'owner/repo {self.repo} local main tree=tree.json\n')
        sh(self.repo, 'git', 'worktree', 'add', '-q', '-b', 'work', str(self.tmp / 'work'))
        work = self.tmp / 'work'
        done = subprocess.run([sys.executable, '-I', str(CLI), 'set', 'CA-03', '--text', '-'], env=self.env, capture_output=True, text=True,
                              cwd=work, input='The service MUST refuse a call that has no number.\n\n- Verified by: the refuse test.\n')
        self.assertEqual(done.returncode, 3, done.stderr)
        answers = [line for line in done.stdout.splitlines() if line.startswith('dev-spec confirm ')][-1].split()[2:]
        done = subprocess.run([sys.executable, '-I', str(CLI), 'confirm', *answers], env=self.env, capture_output=True, text=True, cwd=work)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('a call that has no number', (work / 'docs/spec/SDD.md').read_text())   # the worktree of the session changed
        self.assertNotIn('a call that has no number', self.sdd())                            # and no other checkout

    def test_a_read_command_in_the_primary_checkout_uses_the_source_of_the_config(self):   # SDD-PJ-09
        sh(self.repo, 'git', 'branch', 'spec')            # the branch with the specification
        sh(self.repo, 'git', 'rm', '-q', '-r', 'docs/spec')
        self.commit('main has no specification')
        (self.repo / 'tree.json').write_text(json.dumps({'schema': 'dev-platform.spec-tree@1', 'name': 'fixture', 'top': None,
                                                         'repositories': [{'name': 'r', 'path': '.', 'layout': 'single', 'source': 'spec'}]}))
        (self.repo / '.git/info/exclude').write_text('tree.json\ntree.html\ntree.data.json\n.claude/\n')
        (self.tmp / 'repos.conf').write_text(f'owner/repo {self.repo} local main tree=tree.json\n')
        run = lambda *args, **kw: subprocess.run([sys.executable, '-I', str(CLI), *args], env=self.env, capture_output=True, text=True,
                                                 cwd=self.repo, **kw)
        done = run('why', 'CA-02')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('CA-02  [no test]  When a call ends, the service MUST store the call record.', done.stdout)
        done = run('set', 'CA-02', '--text', '-', input='When a call ends, the service MUST store one record.\n\n- Verified by: a test.\n')
        self.assertEqual(done.returncode, 1)   # a write works on this folder, and this branch has no specification
        self.assertIn('this checkout holds no item of the specification', done.stderr)



class Controlled(Write):
    """A project with a record and the control on."""

    def setUp(self):
        super().setUp()
        self.projects = self.tmp / 'projects'
        self.projects.mkdir()
        self.record(control=True)
        self.env['DEV_PLATFORM_PROJECTS'] = str(self.projects)

    def record(self, control):
        data = {'schema': 'dev-platform.spec-tree@1', 'name': 'fixture', 'top': None, 'control': control,
                'repositories': [{'name': 'r', 'path': str(self.repo), 'layout': 'single'}]}
        (self.projects / 'fixture.json').write_text(json.dumps(data))
        self.config = self.projects / 'fixture.json'

    def here(self, *args, expected=0, **kw):
        done = subprocess.run([sys.executable, '-I', str(CLI), *args], env=self.env, capture_output=True, text=True, cwd=self.repo, **kw)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        return done

    def by_command(self):
        done = self.here('set', 'CA-03', '--text', '-', expected=3,
                         input='The service MUST refuse a call that has no number.\n\n- Verified by: the refuse test.\n')
        answers = [line for line in done.stdout.splitlines() if line.startswith('dev-spec confirm ')][-1].split()[2:]
        return answers

    def commit_with_the_hook(self, expected):
        done = subprocess.run(['git', '-c', f'core.hooksPath={CLI.parents[1] / "hooks/git"}', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                               'commit', '-q', '-m', 'docs(spec): change'], env=self.env, capture_output=True, text=True, cwd=self.repo)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        return done


class Control(Controlled):
    """The control of the specification is on: a direct edit is refused at the edit and at the commit (SDD-SW-01)."""

    def test_the_commit_hook_refuses_content_that_no_command_recorded(self):   # SDD-SW-11
        self.write('docs/spec/SDD.md', SDD.replace('with no number', 'that has no number'))   # a direct edit
        sh(self.repo, 'git', 'add', '-A')
        done = self.commit_with_the_hook(expected=1)
        self.assertIn('docs/spec/SDD.md: this content was not written by a dev-spec command', done.stderr)
        sh(self.repo, 'git', 'checkout', '-q', 'HEAD', '--', 'docs/spec/SDD.md')
        self.here('confirm', *self.by_command())   # the same change through the command
        self.write('README.md', 'A free document.\n')   # each other document is free
        sh(self.repo, 'git', 'add', '-A')
        self.commit_with_the_hook(expected=0)
        self.record(control=False)   # with the control off, the hook refuses nothing (SDD-PJ-04)
        self.write('docs/spec/SDD.md', self.sdd() + '\nLoose text.\n')
        sh(self.repo, 'git', 'add', '-A')
        self.commit_with_the_hook(expected=0)

    def test_the_commit_hook_refuses_a_commit_while_an_item_is_open(self):   # SDD-SW-05
        answers = [a.replace('CA-02=same', 'CA-02=change') for a in self.by_command()]
        self.here('confirm', *answers)
        sh(self.repo, 'git', 'add', '-A')
        done = self.commit_with_the_hook(expected=1)
        self.assertIn('open items that must change also: CA-02', done.stderr)

    def test_accept_records_the_hand_edit_of_the_owner_in_a_terminal_only(self):   # SDD-SW-13
        import pty
        self.write('docs/spec/SDD.md', SDD.replace('with no number', 'that has no number'))
        done = self.here('accept', expected=1)
        self.assertIn('runs in a terminal, never from an agent', done.stderr)

        def in_terminal():
            master, slave = pty.openpty()
            done = subprocess.run([sys.executable, '-I', str(CLI), 'accept'], env=self.env, stdin=slave, stdout=slave,
                                  stderr=subprocess.PIPE, text=True, cwd=self.repo)
            os.close(slave)
            try:
                shown = os.read(master, 4096).decode()
            except OSError:   # the command printed nothing to the terminal
                shown = ''
            os.close(master)
            return done.returncode, shown + done.stderr

        code, shown = in_terminal()
        self.assertEqual(code, 0, shown)
        self.assertIn('Accepted as the owner', shown)
        sh(self.repo, 'git', 'add', '-A')
        self.commit_with_the_hook(expected=0)
        self.write('docs/spec/SDD.md', self.sdd().replace('The service MUST refuse a call that has no number.', 'The service refuses a call.'))
        code, shown = in_terminal()   # the owner's edit also keeps the form
        self.assertEqual(code, 1, shown)
        self.assertIn('CA-03: SP-07: no MUST', shown)

    def test_move_puts_an_sdd_item_into_a_different_section_with_its_identifier(self):   # SDD-SW-02
        done = self.here('move', 'CA-03', '--section', '3', expected=3)
        self.here('confirm', *[line for line in done.stdout.splitlines() if line.startswith('dev-spec confirm ')][-1].split()[2:])
        after = self.sdd()
        self.assertIn('- Verified by: the retention test.\n\n**CA-03.** The service MUST refuse a call with no number.\n'
                      '<!-- id: SDD-CA-03 | tdd: none -->\n\n- Verified by: the refuse test.\n', after)
        self.assertIn('- Verified by: the store test.\n\n## 3. Records', after)
        self.here('compile', 'fixture')
        tree = json.loads((self.repo / '.git/dev-platform/tree.data.json').read_text())
        self.assertEqual((tree['repositories']['r']['sdd']['CA-03']['group'], tree['faults']), ('section/3', []))
        done = self.here('move', 'TDD-1.1', '--section', '3', expected=1)
        self.assertIn('move takes an SDD item', done.stderr)

    def test_the_guard_refuses_a_direct_write_and_names_the_command(self):   # SDD-SW-12
        guard = CLI.parents[1] / 'hooks/spec_guard.py'

        def ask(tool, **given):
            done = subprocess.run([sys.executable, '-I', str(guard)], env=self.env, capture_output=True, text=True,
                                  input=json.dumps({'tool_name': tool, 'tool_input': given, 'cwd': str(self.repo)}))
            return done.returncode, done.stderr

        code, reason = ask('Edit', file_path=str(self.repo / 'docs/spec/SDD.md'))
        self.assertEqual(code, 2)
        self.assertIn('docs/spec/SDD.md is a specification file of a controlled project', reason)
        self.assertIn('dev-spec set', reason)
        self.assertEqual(ask('Write', file_path='docs/spec/TDD.md')[0], 2)
        self.assertEqual(ask('Write', file_path=str(self.repo / 'README.md'))[0], 0)          # each other document is free
        self.assertEqual(ask('Write', file_path=str(self.repo / 'docs/spec/notes.txt'))[0], 0)
        for command in ("sed -i 's/a/b/' docs/spec/SDD.md", 'echo x >> docs/spec/SDD.md', 'cat new.md | tee docs/spec/TDD.md',
                        'cp /tmp/new.md docs/spec/SDD.md', 'git rm docs/spec/TDD.md', "perl -pi -e 's/a/b/' ./docs/spec/SDD.md"):
            with self.subTest(command=command):
                self.assertEqual(ask('Bash', command=command)[0], 2)
        for command in ('cat docs/spec/SDD.md', "sed -n '1,5p' docs/spec/SDD.md", 'cp docs/spec/SDD.md /tmp/copy.md', 'grep -n MUST docs/spec/SDD.md',
                        'dev-spec set CA-03 --text new.txt', 'git diff -- docs/spec/SDD.md', 'echo x > notes.md'):
            with self.subTest(command=command):
                self.assertEqual(ask('Bash', command=command)[0], 0)
        self.record(control=False)
        self.assertEqual(ask('Edit', file_path=str(self.repo / 'docs/spec/SDD.md'))[0], 0)


class SectionFiles(Controlled):
    """The sections layout: one file for each section. A removed section takes its file with it."""

    def setUp(self):
        super().setUp()
        sh(self.repo, 'git', 'rm', '-q', 'docs/spec/SDD.md', 'docs/spec/TDD.md')
        self.write('docs/spec/SDD/1.1.md', '### 1.1 System requirements\n\n**ID-01.** The product MUST answer each call.\n<!-- id: SYS-ID-01 -->\n\n'
                                           '**ID-02.** The product MUST call each requester back.\n<!-- id: SYS-ID-02 -->\n')
        self.write('docs/spec/SDD/2.1.md', '### 2.1 Calls\n<!-- section: SDD-2.1 | sys: SYS-ID-01 -->\n\n'
                                           '**CA-01.** When a call arrives, the service MUST answer the call.\n<!-- id: SDD-CA-01 | tdd: TDD-1.1.1 -->\n\n'
                                           '- Verified by: the answer test.\n')
        self.write('docs/spec/SDD/2.6.md', '### 2.6 Callbacks\n<!-- section: SDD-2.6 | sys: SYS-ID-02 -->\n\n<!-- retired: SDD-CB-01 -->\n')
        self.write('docs/spec/TDD/1.1.md', '### 1.1 Calls\n\n#### TDD-1.1.1 Answer\n'
                                           '<!-- id: TDD-1.1.1 | implements: SDD-CA-01 | code: src/answer.ts | tests: tests/pass.test.ts -->\n\nThe handler answers.\n')
        self.write('docs/spec/TDD/2.11.md', '### 2.11 Callback contract\n\n<!-- retired: TDD-2.11.1 -->\n\n<!-- retired: TDD-2.11.2 -->\n')
        self.record(control=True)
        self.commit('sections')

    def record(self, control):
        data = {'schema': 'dev-platform.spec-tree@1', 'name': 'fixture', 'top': None, 'control': control, 'page': str(self.tmp),
                'repositories': [{'name': 'r', 'path': str(self.repo), 'layout': 'sections', 'sdd': 'docs/spec/SDD', 'tdd': 'docs/spec/TDD'}]}
        (self.projects / 'fixture.json').write_text(json.dumps(data))
        self.config = self.projects / 'fixture.json'

    def confirmed(self, *args):
        done = self.here(*args, expected=3)
        return self.here('confirm', *self.answers(done))

    def test_a_removed_section_takes_its_file_and_the_hook_accepts_the_commit(self):   # SDD-SW-02, SDD-SW-10, SDD-SW-11
        self.assertEqual(self.tree()['faults'], [])
        self.assertIn('holds: TDD-1.1.1', self.here('remove', '--level', 'tdd', '--section', '1.1', expected=1).stderr)
        done = self.here('remove', '--level', 'tdd', '--section', '2.11', expected=3)
        self.assertIn('the file leaves also', done.stdout)
        self.assertTrue((self.repo / 'docs/spec/TDD/2.11.md').is_file())   # a proposal writes nothing
        self.here('confirm', *self.answers(done))
        self.assertFalse((self.repo / 'docs/spec/TDD/2.11.md').exists())
        self.confirmed('remove', '--level', 'sdd', '--section', '2.6')
        self.assertFalse((self.repo / 'docs/spec/SDD/2.6.md').exists())
        self.confirmed('remove', 'SYS-ID-02')
        self.assertIn('<!-- id: SYS-ID-01 -->\n\n<!-- retired: SYS-ID-02 -->\n', (self.repo / 'docs/spec/SDD/1.1.md').read_text())
        self.assertEqual(self.tree()['faults'], [])
        sh(self.repo, 'git', 'add', '-A')
        self.commit_with_the_hook(expected=0)
        (self.repo / 'docs/spec/TDD/1.1.md').unlink()   # a file that no command removed
        sh(self.repo, 'git', 'add', '-A')
        self.assertIn('docs/spec/TDD/1.1.md: this content was not written by a dev-spec command', self.commit_with_the_hook(expected=1).stderr)


class Ghost(Write):
    """A ghost project: the specification is in a side folder (the rig folder), and the repository holds no file of it (SDD-PJ-10)."""

    def setUp(self):
        super().setUp()
        self.side = self.tmp / 'rig'
        sh(self.tmp, 'git', 'init', '-q', '-b', 'main', str(self.side))
        (self.side / 'docs/spec').mkdir(parents=True)
        for name in ('SDD.md', 'TDD.md'):
            (self.side / 'docs/spec' / name).write_text((self.repo / 'docs/spec' / name).read_text())
        sh(self.side, 'git', 'add', '-A')
        sh(self.side, 'git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '-m', 'the specification of a foreign repository')
        sh(self.repo, 'git', 'rm', '-q', '-r', 'docs/spec')   # the foreign repository has no specification of ours
        self.commit('a repository that is not ours')
        self.projects = self.tmp / 'projects'
        self.projects.mkdir()
        (self.projects / 'fixture.json').write_text(json.dumps({
            'schema': 'dev-platform.spec-tree@1', 'name': 'fixture', 'top': None, 'control': True, 'page': str(self.tmp),
            'repositories': [{'name': 'r', 'path': str(self.repo), 'layout': 'single', 'spec_root': str(self.side)}]}))
        self.env['DEV_PLATFORM_PROJECTS'] = str(self.projects)

    def at(self, folder, *args, expected=0, **kw):
        done = subprocess.run([sys.executable, '-I', str(CLI), *args], env=self.env, capture_output=True, text=True, cwd=folder, **kw)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        return done

    def side_sdd(self):
        return (self.side / 'docs/spec/SDD.md').read_text()

    def commit_side(self, expected):
        sh(self.side, 'git', 'add', '-A')
        done = subprocess.run(['git', '-c', f'core.hooksPath={CLI.parents[1] / "hooks/git"}', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                               'commit', '-q', '-m', 'docs(spec): change'], env=self.env, capture_output=True, text=True, cwd=self.side)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        return done

    def test_the_tree_joins_the_side_specification_with_the_code_of_the_checkout(self):
        done = self.at(self.repo, 'why', 'CA-01')
        self.assertIn('code: src/answer.ts', done.stdout)
        self.assertNotIn('PATH MISSING', done.stdout)
        self.assertIn('is named by TDD-1.2', self.at(self.repo, 'why', 'src/store.ts').stdout)
        self.at(self.repo, 'compile', 'fixture')
        tree = json.loads((self.tmp / 'tree.data.json').read_text())
        self.assertEqual((len(tree['repositories']['r']['sdd']), tree['faults']), (4, []))
        self.assertEqual(sh(self.repo, 'git', 'status', '--porcelain', '--ignored'), '')

    def test_a_command_in_the_checkout_writes_the_side_folder_and_no_file_of_the_repository(self):
        text = 'The service MUST refuse a call that has no number.\n\n- Verified by: the refuse test.\n'
        done = self.at(self.repo, 'set', 'CA-03', '--text', '-', input=text, expected=3)
        self.at(self.repo, 'confirm', *self.answers(done, TDD_1_2='change'))
        self.assertIn('a call that has no number', self.side_sdd())
        self.assertEqual(sh(self.repo, 'git', 'status', '--porcelain', '--ignored'), '')
        self.assertEqual(self.at(self.repo, 'open', expected=1).stdout.split()[0], 'TDD-1.2')   # the open list of the side folder
        self.assertEqual(self.at(self.side, 'open', expected=1).stdout.split()[0], 'TDD-1.2')
        self.assertIn('open items that must change also: TDD-1.2', self.commit_side(expected=1).stderr)
        done = self.at(self.side, 'set', 'TDD-1.2', '--text', '-', input='Store\n\nThe store keeps one record.\n', expected=3)
        self.at(self.side, 'confirm', *self.answers(done))   # the same commands work in the side folder
        self.commit_side(expected=0)

    def test_the_control_holds_in_the_side_folder(self):
        (self.side / 'docs/spec/SDD.md').write_text(self.side_sdd().replace('with no number', 'that has no number'))   # a direct edit
        self.assertIn('docs/spec/SDD.md: this content was not written by a dev-spec command', self.commit_side(expected=1).stderr)
        guard = CLI.parents[1] / 'hooks/spec_guard.py'
        ask = lambda path, cwd: subprocess.run([sys.executable, '-I', str(guard)], env=self.env, capture_output=True, text=True, input=json.dumps(
            {'tool_name': 'Edit', 'tool_input': {'file_path': str(path)}, 'cwd': str(cwd)})).returncode
        self.assertEqual(ask(self.side / 'docs/spec/SDD.md', self.repo), 2)
        self.assertEqual(ask(self.side / 'notes.md', self.side), 0)
        self.assertEqual(ask(self.repo / 'docs/spec/SDD.md', self.repo), 0)   # a file of the foreign repository is its own

    def test_a_side_folder_must_be_a_folder_and_the_top_of_its_repository(self):
        record = json.loads((self.projects / 'fixture.json').read_text())
        record['repositories'][0]['spec_root'] = str(self.side / 'docs')
        (self.projects / 'fixture.json').write_text(json.dumps(record))
        self.assertIn('must be the top folder of its Git repository', self.at(self.repo, 'compile', 'fixture', expected=2).stderr)
        record['repositories'][0]['spec_root'] = str(self.tmp / 'absent')
        (self.projects / 'fixture.json').write_text(json.dumps(record))
        self.assertIn('spec_root: no folder at', self.at(self.repo, 'compile', 'fixture', expected=2).stderr)
