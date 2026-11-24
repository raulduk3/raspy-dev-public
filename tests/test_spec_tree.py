"""dev-spec compiles a project's specification tree (docs/spec/SDD.md, area ST)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/dev-spec'
sys.path.insert(0, str(PLATFORM / 'lib'))
from ai_ecosystem import spectree  # noqa: E402

JUNIT = '''<?xml version="1.0"?>
<testsuites>
 <testsuite name="tests/pass.test.ts" file="tests/pass.test.ts"><testcase name="a"/><testcase name="b"/></testsuite>
 <testsuite name="tests/fail.test.ts" file="tests/fail.test.ts"><testcase name="a"><failure/></testcase></testsuite>
</testsuites>
'''

SDD = '''\
# SDD

## 1. First

**AA-01.** The service must answer.
<!-- id: SDD-AA-01 | tdd: TDD-1.1 | status: implemented -->

- Behavior: it answers.

**AA-02.** The service must refuse a bad call.
<!-- id: SDD-AA-02 | tdd: TDD-1.2 | status: implemented -->

**AA-03.** The service must store the call.
<!-- id: SDD-AA-03 | tdd: TDD-1.3 | status: pending:#7 -->

**AA-04.** The service keeps `the_call_row` in `calls.ts` with `storeCall()`.
<!-- id: SDD-AA-04 | tdd: TDD-1.4 | status: implemented -->

**AA-05.** The service must log.
<!-- id: SDD-AA-05 | tdd: TDD-1.5 | status: deviation:#9 -->

**AA-06.** The page must show a button.
<!-- id: SDD-AA-06 | tdd: none | status: pending:#8 -->
'''

TDD = '''\
# TDD

## 1. First

#### TDD-1.1 Answer
<!-- id: TDD-1.1 | implements: AA-01 | code: src/answer.ts#answer | tests: tests/pass.test.ts | status: implemented -->

#### TDD-1.2 Refuse
<!-- id: TDD-1.2 | implements: AA-02 | code: src/answer.ts#refuse | tests: tests/fail.test.ts | status: implemented -->

#### TDD-1.3 Store
<!-- id: TDD-1.3 | implements: AA-03 | code: src/store.ts | tests: none | status: pending:#7 -->

#### TDD-1.4 Keep
<!-- id: TDD-1.4 | implements: AA-04 | code: src/gone.ts | tests: none | status: implemented -->

#### TDD-1.5 Log
<!-- id: TDD-1.5 | implements: AA-05 | code: src/folder/ | tests: tests/notrun.test.ts | status: deviation:#9 -->
'''


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Fixture(unittest.TestCase):
    """One repository with the single layout, one item of each status, and kept results for its revision."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='spec-tree-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / 'repo'
        self.env = dict(os.environ, DEV_PLATFORM_STATE=str(self.tmp / 'state'),
                        DEV_PLATFORM_REPOS=str(self.tmp / 'repos.conf'), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        self.write('docs/spec/SDD.md', SDD)
        self.write('docs/spec/TDD.md', TDD)
        self.write('src/answer.ts', 'export function answer() {}\nexport function refuse() {}\n')
        self.write('src/store.ts', 'export const store = 1\n')
        self.write('src/folder/in.ts', 'export const a = 1\n')
        self.write('src/alone.ts', 'export const b = 1\n')
        for name in ('pass', 'fail', 'notrun', 'unnamed'):
            self.write(f'tests/{name}.test.ts', '// test\n')
        sh(self.tmp, 'git', 'init', '-q', '-b', 'main', str(self.repo))
        self.commit('first')
        self.config = self.tmp / 'tree.json'
        self.entry = {'name': 'r', 'path': 'repo', 'layout': 'single', 'flag_words': ['button'],
                      'test': f'cp {self.tmp}/junit.xml {{out}}'}
        self.save()
        (self.tmp / 'junit.xml').write_text(JUNIT)

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, message):
        sh(self.repo, 'git', 'add', '-A')
        sh(self.repo, 'git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '-m', message)
        return sh(self.repo, 'git', 'rev-parse', 'HEAD')

    def save(self, **top):
        # The tests read the page beside the config; the default place is the Git folder of the repository (SDD-ST-11).
        data = {'schema': spectree.SCHEMA, 'name': 'fixture', 'top': None, 'page': str(self.tmp), 'repositories': [self.entry]}
        data.update(top)
        self.config.write_text(json.dumps(data))

    def run_cli(self, *args, expected=0):
        done = subprocess.run([sys.executable, '-I', str(CLI), *args, '--config', str(self.config)], env=self.env,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        return done

    def tree(self):
        self.run_cli('compile')
        return json.loads((self.tmp / 'tree.data.json').read_text())

    def page(self):
        return (self.tmp / 'tree.html').read_text()


class Markdown(unittest.TestCase):
    def test_a_line_break_tag_is_a_line_break_and_each_other_tag_is_text(self):   # SDD-ST-11
        html = spectree.md_html(['| Step | Text |', '| --- | --- |', '| 1 | first<br>second<BR/>third<br />`a<br>b` <b>bold</b> |', '',
                                 'One line<br>of a paragraph.'])
        self.assertIn('<td>first<br>second<br>third<br><code>a&lt;br&gt;b</code> &lt;b&gt;bold&lt;/b&gt;</td>', html)
        self.assertIn('<p>One line<br>of a paragraph.</p>', html)


class Status(Fixture):
    def test_each_status_comes_from_the_files_and_the_kept_results(self):   # SDD-ST-05, SDD-ST-08
        self.run_cli('test')
        repo = self.tree()['repositories']['r']
        self.assertEqual({i: t['status'] for i, t in repo['tdd'].items()},
                         {'TDD-1.1': 'proved', 'TDD-1.2': 'failing', 'TDD-1.3': 'no test', 'TDD-1.4': 'no code', 'TDD-1.5': 'test not run'})
        self.assertEqual({i: s['status'] for i, s in repo['sdd'].items()},
                         {'AA-01': 'proved', 'AA-02': 'failing', 'AA-03': 'no test', 'AA-04': 'no code', 'AA-05': 'test not run',
                          'AA-06': 'no TDD'})
        self.assertEqual(repo['results_valid'], True)
        page = self.page()
        self.assertIn('id="r-AA-01"><h4><code>AA-01</code> <span class="status s-proved">proved</span></h4>'
                      '<p class="req">The service must answer.</p>', page)
        self.assertIn('declared: implemented', page)
        self.assertIn('docs/spec/SDD.md:5', page)

    def test_a_support_file_in_the_test_paths_is_no_test(self):   # SDD-ST-05
        self.write('tests/helpers.ts', 'export const help = 1\n')
        self.write('docs/spec/TDD.md', TDD.replace('tests: tests/pass.test.ts |', 'tests: tests/pass.test.ts, tests/helpers.ts |')
                   .replace('code: src/store.ts | tests: none', 'code: src/store.ts | tests: tests/helpers.ts'))
        self.commit('a helper of the tests')
        repo = self.tree()['repositories']['r']   # no result is kept: the compiler does not know that the file holds no case
        self.assertEqual((repo['tdd']['TDD-1.1']['status'], repo['tdd']['TDD-1.3']['status']), ('test not run', 'test not run'))
        self.run_cli('test')
        repo = self.tree()['repositories']['r']
        self.assertEqual(repo['tdd']['TDD-1.1']['status'], 'proved')         # the helper does not hold the item at "test not run"
        self.assertEqual(repo['tdd']['TDD-1.3']['status'], 'no test')        # a helper alone is no test
        self.assertEqual(repo['tdd']['TDD-1.5']['status'], 'test not run')   # a file with a test name and no case did not run
        self.assertIn('a support file: no test case', self.page())
        # A named support file is owned. It is a measure and no gap: the item with a helper alone is the gap ("no test").
        self.assertNotIn('tests/helpers.ts', repo['tests_no_tdd'])
        gaps, _, measures = self.page().partition('<h2 id="measures"')
        self.assertNotIn('support files', gaps)
        self.assertIn('support paths that a TDD item names, with no test case: 2', measures)

    def test_a_named_folder_of_support_files_is_no_test(self):   # SDD-ST-05
        self.write('tests/fixtures/one.ts', 'export const one = 1\n')
        self.write('tests/fixtures/deep/two.ts', 'export const two = 2\n')
        self.write('tests/cases/later.test.ts', '// test\n')
        self.write('docs/spec/TDD.md', TDD.replace('tests: tests/pass.test.ts |', 'tests: tests/pass.test.ts, tests/fixtures/ |')
                   .replace('code: src/store.ts | tests: none', 'code: src/store.ts | tests: tests/cases/'))
        self.commit('a folder of fixtures')
        self.run_cli('test')
        repo = self.tree()['repositories']['r']
        self.assertEqual(repo['tdd']['TDD-1.1']['status'], 'proved')         # the folder holds no file with a test name
        self.assertEqual(repo['tdd']['TDD-1.3']['status'], 'test not run')   # a folder with a test file that has no result
        self.assertFalse([f for f in repo['tests_no_tdd'] if f.startswith('tests/fixtures/')])
        self.assertIn('a support folder: no test case', self.page())

    def test_compile_runs_no_test_and_says_test_not_run_with_no_result(self):   # SDD-ST-08
        self.entry['test'] = f'touch {self.tmp}/ran && false'
        self.save()
        repo = self.tree()['repositories']['r']
        self.assertFalse((self.tmp / 'ran').exists())
        self.assertEqual(repo['tdd']['TDD-1.1']['status'], 'test not run')

    def test_declared_and_computed_status_are_shown_and_their_differences_listed(self):   # SDD-ST-07
        self.run_cli('test')
        repo = self.tree()['repositories']['r']
        differ = sorted(i for side in ('sdd', 'tdd') for i, item in repo[side].items() if item['differs'])
        # implemented but not proved: AA-02, AA-04 and their TDD items. A gap marker with no proof is no difference.
        self.assertEqual(differ, ['AA-02', 'AA-04', 'TDD-1.2', 'TDD-1.4'])
        self.assertIn('declared: implemented; computed: failing', self.page())
        # A gap marker over a proved item is a difference.
        self.write('docs/spec/TDD.md', TDD.replace('tests: tests/pass.test.ts | status: implemented', 'tests: tests/pass.test.ts | status: deviation:#3'))
        self.commit('marker')
        self.assertTrue(self.tree()['repositories']['r']['tdd']['TDD-1.1']['differs'])
        self.assertIn('declared: deviation:#3; computed: proved; cites #3', self.page())

    def test_a_result_counts_only_for_its_revision_or_a_change_of_the_specification(self):   # SDD-ST-09
        self.run_cli('test')
        self.write('docs/spec/SDD.md', SDD + '\n')
        self.commit('spec only')
        repo = self.tree()['repositories']['r']
        self.assertTrue(repo['results_valid'])
        self.assertEqual(repo['tdd']['TDD-1.1']['status'], 'proved')
        self.write('src/answer.ts', 'export function answer() { return 1 }\nexport function refuse() {}\n')
        self.commit('code')
        repo = self.tree()['repositories']['r']
        self.assertFalse(repo['results_valid'])
        self.assertEqual(repo['tdd']['TDD-1.1']['status'], 'test not run')
        self.assertEqual(repo['tdd']['TDD-1.2']['status'], 'test not run')
        self.assertIn('NOT VALID for this revision', self.page())


class Structure(Fixture):
    def test_the_compiler_changes_no_tracked_file_and_gives_the_same_page_two_times(self):   # SDD-ST-06, SDD-ST-11
        self.run_cli('test')
        self.run_cli('compile')
        first = self.page(), (self.tmp / 'tree.data.json').read_text()
        self.run_cli('compile')
        self.assertEqual(first, (self.page(), (self.tmp / 'tree.data.json').read_text()))
        self.assertEqual(sh(self.repo, 'git', 'status', '--porcelain'), '')
        page = self.page()
        self.assertEqual((page.count('<style>'), page.count('<script'), page.count('style='), page.count('<link'), page.count(' src=')),
                         (1, 0, 0, 0, 0))   # one embedded style sheet, no script, no external file
        order = [page.index(h) for h in ('<nav>', '<h2 id="summary">', '<h2 id="faults">', '<h2 id="gaps">', '<h2 id="differ">',
                                         '<h2 id="spec-r">', '<h2 id="measures">', '<h2 id="unnamed">')]
        self.assertEqual(order, sorted(order))

    def test_links_paths_and_symbols(self):   # SDD-ST-03
        self.write('docs/spec/TDD.md', TDD.replace('src/answer.ts#refuse', 'src/answer.ts#gone')
                   + '\n#### TDD-1.6 Extra\n<!-- id: TDD-1.6 | implements: AA-01, ZZ-09 | code: src/store.ts#Store.keep, src/store.ts#Store.gone, src/store.ts#Gone.keep '
                   '| tests: none | status: implemented -->\n')
        self.write('src/store.ts', 'export class Store {\n  keep() {}\n}\n')
        self.commit('links')
        tree = self.tree()
        repo = tree['repositories']['r']
        self.assertEqual(repo['sdd']['AA-01']['tdd'], ['TDD-1.1', 'TDD-1.6'])
        self.assertEqual([p['symbol_found'] for p in repo['tdd']['TDD-1.2']['paths'] if p['kind'] == 'code'], [False])
        self.assertEqual([p['symbol_found'] for p in repo['tdd']['TDD-1.6']['paths']], [True, False, False])   # Class.method
        self.assertEqual([f for f in tree['faults'] if 'ZZ-09' in f], ['docs/spec/TDD.md:20: TDD-1.6 implements ZZ-09, which is no current SDD item'])
        self.assertEqual(repo['one_sided'], ['docs/spec/TDD.md:20: TDD-1.6 implements AA-01, but AA-01 does not name it'])
        self.assertIn('symbol not found in the file', self.page())
        self.assertIn('PATH MISSING', self.page())

    def test_structure_faults_fail_the_check_and_a_measure_does_not(self):   # SDD-ST-03, SDD-ST-12
        done = self.run_cli('check')
        self.assertEqual(done.stderr, '')
        self.write('docs/spec/SDD.md', SDD + '\n**AA-01.** A second one.\n<!-- id: SDD-AA-09 | tdd: TDD-9.9 | status: implemented -->\n')
        self.commit('faults')
        done = self.run_cli('check', expected=1)
        lines = done.stderr.splitlines()
        self.assertIn('docs/spec/SDD.md:25: the trace comment names SDD-AA-09, the line above is AA-01', lines)
        self.assertIn('docs/spec/SDD.md:25: AA-01 occurs two times; the first is at docs/spec/SDD.md:5', lines)

    def test_form_measures_and_files_with_no_owner(self):   # SDD-ST-13, SDD-ST-14
        repo = self.tree()['repositories']['r']
        self.assertEqual([i for i, s in repo['sdd'].items() if not s['has_must']], ['AA-04'])
        self.assertEqual(repo['sdd']['AA-04']['code_names'], 3)
        self.assertEqual(repo['sdd']['AA-06']['flag_words'], {'button': 1})
        self.assertEqual(repo['code_no_tdd'], ['src/alone.ts'])   # src/folder/in.ts is owned by the folder that TDD-1.5 names
        self.assertEqual(repo['tests_no_tdd'], ['tests/unnamed.test.ts'])
        self.run_cli('check')   # a measure fails nothing

    def test_the_page_holds_the_full_text_of_each_section_and_each_item(self):   # SDD-ST-11
        self.write('docs/spec/SDD.md', SDD + '\n## 2. Scope\n\nThis section is prose with **no** numbered requirement.\n\n'
                                             '| Part | In scope |\n| --- | --- |\n| calls | yes |\n')
        self.write('docs/spec/TDD.md', TDD.replace('#### TDD-1.2 Refuse', 'The handler calls `answer` first.\n\n- Step one\n  - Detail of step one\n- Step two\n\n```ts\nanswer()\n```\n\n#### TDD-1.2 Refuse'))
        self.commit('text')
        self.run_cli('compile')
        page = self.page()
        answer = page[page.index('id="r-AA-01"'):page.index('id="r-AA-02"')]
        self.assertIn('<ul><li>Behavior: it answers.</li></ul>', answer)   # the body of the SDD item
        self.assertIn('<p>The handler calls <code>answer</code> first.</p>', answer)   # the body of its TDD item, below it
        self.assertIn('<ul><li>Step one<ul><li>Detail of step one</li></ul></li><li>Step two</li></ul>', answer)
        self.assertIn('<pre><code>answer()</code></pre>', answer)
        self.assertIn('code: <code>src/answer.ts#answer</code>', answer)
        self.assertNotIn('&lt;!-- id:', page)   # a trace comment is not text of the page
        scope = page[page.index('id="r-section-2"'):]
        self.assertIn('This section has no numbered requirement; its text is below.', scope)
        self.assertIn('<p>This section is prose with <strong>no</strong> numbered requirement.</p>', scope)
        self.assertIn('<table><thead><tr><th>Part</th><th>In scope</th></tr></thead><tbody><tr><td>calls</td><td>yes</td></tr></tbody></table>', scope)


class Layouts(Fixture):
    def test_the_sections_layout_reads_one_file_for_each_section(self):   # SDD-ST-02
        for old in ('docs/spec/SDD.md', 'docs/spec/TDD.md'):
            (self.repo / old).unlink()
        self.write('spec/SDD/2.1.md', '### 2.1 Calls\n<!-- spec-lock: SDD-2.1 sha256:00 -->\n\n**CX-01.** The server owns the call.\n'
                                      '<!-- id: SDD-CX-01 | tdd: TDD-2.1.1 | status: implemented -->\n- Trigger: a call.\n')
        self.write('spec/SDD/6.md', '## 6. Acceptance\n\n| AC-01 | The call is answered. |\n')
        self.write('spec/SDD/10.1.md', '### 10.1 Later\n\n**OP-01.** The server must start.\n<!-- id: SDD-OP-01 | tdd: TDD-10.1.1.1 | status: implemented -->\n')
        self.write('spec/TDD/2.1.md', '### 2.1 Transport\n\n#### TDD-2.1.1 Transport\n'
                                      '<!-- id: TDD-2.1.1 | implements: SDD-CX-01, AC-01 | code: src/answer.ts | tests: tests/pass.test.ts | status: implemented -->\n')
        self.write('spec/TDD/10.1.md', '### 10.1 Start\n\n##### TDD-10.1.1.1 Start\n'
                                       '<!-- id: TDD-10.1.1.1 | implements: SDD-OP-01 | code: src/store.ts | tests: none | status: implemented -->\n')
        self.write('spec/TDD/9.9.md', 'Text with no item.\n')
        self.write('spec/TDD/10.2.md', '### 10.2 Stop\n\n#### Stop with no identifier in the heading\n'
                                       '<!-- id: TDD-10.2.1 | implements: SDD-OP-01 | code: src/store.ts | tests: none | status: implemented -->\n')
        self.commit('sections')
        self.entry.update(layout='sections', sdd='spec/SDD', tdd='spec/TDD')
        self.save()
        tree = self.tree()
        repo = tree['repositories']['r']
        self.assertEqual([g['key'] for g in repo['groups']], ['section/2.1', 'section/6', 'section/10.1'])   # in number order
        self.assertEqual(repo['sdd']['CX-01']['file'], 'spec/SDD/2.1.md')
        self.assertEqual(repo['sdd']['CX-01']['has_must'], False)
        self.assertEqual(repo['tdd']['TDD-2.1.1']['implements'], ['CX-01'])
        self.assertEqual(repo['tdd']['TDD-2.1.1']['rows'], ['AC-01'])   # a table row is known and is no fault
        self.assertIn('TDD-10.1.1.1', repo['tdd'])
        self.assertEqual(repo['tdd']['TDD-10.2.1']['title'], 'Stop with no identifier in the heading')   # the item is not lost
        self.assertEqual(tree['faults'], ['spec/TDD/9.9.md: the file holds no item and no section heading',
                                          'spec/TDD/10.2.md:3: the heading of TDD-10.2.1 does not hold its identifier'])

    def test_the_domains_layout_reads_one_folder_for_each_domain(self):   # SDD-ST-02
        self.write('docs/spec/refunds/sdd.md', '### D76 A missed visit\nlayer: rule\ntdd: TDD-12.81\ntasks: none\n\nA missed visit is paid.\n')
        self.write('docs/spec/refunds/tdd.md', '### TDD-12.81 The miss fee\nimplements: D76\ncode: src/store.ts\ntests: tests/pass.test.ts\n\nHow.\n')
        self.commit('domains')
        self.entry.update(layout='domains', sdd='docs/spec')
        self.save()
        repo = self.tree()['repositories']['r']
        self.assertEqual([(g['key'], g['title']) for g in repo['groups']], [('domain/refunds', 'refunds')])
        self.assertEqual(repo['sdd']['D76']['tdd'], ['TDD-12.81'])
        self.assertEqual([p['path'] for p in repo['tdd']['TDD-12.81']['paths']], ['src/store.ts', 'tests/pass.test.ts'])


TOP = '''\
# Product

## 1. What it is

**ID-01.** The product must answer each call.
<!-- id: PR-ID-01 | sdd: r:AA-01, r:AA-0[23] -->

**ID-02.** The product must keep each call.
<!-- id: PR-ID-02 | sdd: r:section/1 -->

**ID-03.** The product must be honest.
<!-- id: PR-ID-03 | sdd: none -->

**ID-04.** The owner must pay the bill.
<!-- id: PR-ID-04 | sdd: outside -->
'''


class Top(Fixture):
    def test_a_top_document_is_the_first_level_and_names_its_sdd_items(self):   # SDD-ST-01, SDD-ST-04
        self.assertEqual(self.tree()['top'], [])
        self.assertNotIn('id="top"', self.page())
        self.write('PRODUCT.md', TOP)
        self.commit('top')
        self.save(top={'path': 'PRODUCT.md', 'prefix': 'PR', 'repository': 'r'})
        tree = self.tree()
        reqs = {r['id']: r for s in tree['top'] for r in s['requirements']}
        self.assertEqual(reqs['PR-ID-01']['items'], [['r', 'AA-01'], ['r', 'AA-02'], ['r', 'AA-03']])
        self.assertEqual(reqs['PR-ID-02']['groups'], [['r', 'section/1']])
        self.assertEqual(tree['repositories']['r']['sdd']['AA-01']['named_by'], ['PR-ID-01', 'PR-ID-02'])
        self.assertEqual(tree['gaps'], ['PRODUCT.md:11: PR-ID-03 names no SDD item'])
        self.assertEqual(tree['faults'], [])
        page = self.page()
        self.assertLess(page.index('<h2 id="top">'), page.index('<h2 id="spec-r">'))
        self.assertIn('id="PR-ID-01"><h4><code>PR-ID-01</code>', page)
        self.assertIn('<p class="req">The product must answer each call.</p>', page)
        self.assertIn('<a href="#r-section-1"><code>r:section/1</code> 1. First</a>', page)

    def test_a_name_that_matches_nothing_and_a_second_owner_are_faults(self):   # SDD-ST-04
        self.write('PRODUCT.md', TOP.replace('sdd: none', 'sdd: r:ZZ-*, r:section/1'))
        self.commit('top')
        self.save(top={'path': 'PRODUCT.md', 'prefix': 'PR', 'repository': 'r'})
        done = self.run_cli('check', expected=1)
        self.assertIn("PRODUCT.md:11: PR-ID-03: 'r:ZZ-*' matches no SDD item", done.stderr)
        self.assertIn("PRODUCT.md:11: PR-ID-03: 'r:section/1' already belongs to PR-ID-02", done.stderr)

    def test_a_top_requirement_can_name_an_area_of_a_capability_catalogue(self):   # SDD-ST-04
        self.write('docs/spec/refunds/sdd.md', '### D76 A missed visit\ntdd: none\n\nText.\n\n### D77 A second visit\ntdd: none\n\nText.\n')
        self.write('docs/spec/capability-catalog.json', json.dumps({
            'area_contracts': {'0139': {'name': 'Missed visits', 'sdd_refs': ['D76']}},
            'features': [{'id': 'F-1', 'title': 'Second visit', 'area': '0139', 'scope': 'core', 'sdd': 'D77', 'tdd': ''}]}))
        self.write('PRODUCT.md', '# Product\n\n## 1. Domains\n\n**DM-01.** The refunds domain must hold each refund rule.\n'
                                 '<!-- id: PR-DM-01 | domain: refunds | areas: r:0139 | sdd: r:domain/refunds -->\n\n'
                                 '**FN-01.** A missed visit must cost the fee of the offer.\n'
                                 '<!-- id: PR-FN-01 | domain: refunds | sdd: r:area/0139 -->\n\n'
                                 '**FN-02.** A late visit must cost nothing.\n<!-- id: PR-FN-02 | domain: refunds | sdd: r:area/9999 -->\n')
        self.commit('catalogue')
        self.entry.update(layout='domains', sdd='docs/spec')
        self.save(top={'path': 'PRODUCT.md', 'prefix': 'PR', 'repository': 'r'})
        tree = self.tree()
        reqs = {r['id']: r for s in tree['top'] for r in s['requirements']}
        self.assertEqual(reqs['PR-FN-01']['items'], [['r', 'D76'], ['r', 'D77']])   # the area's own items and its features' items
        self.assertEqual(reqs['PR-DM-01']['area_list'], [['r', '0139']])
        self.assertEqual(reqs['PR-DM-01']['features'], ['PR-FN-01', 'PR-FN-02'])
        self.assertEqual(tree['faults'], ["PRODUCT.md:11: PR-FN-02: 'r:area/9999' is no area of the capability catalogue"])
        self.assertIn('Capability catalogue', self.page())



STANDARD = """\
# SDD

## 1. System requirements

**ID-01.** The product MUST answer each call.
<!-- id: SYS-ID-01 -->

**ID-02.** The product MUST keep each call.
<!-- id: SYS-ID-02 -->

## 2. Calls
<!-- section: SDD-2 | sys: SYS-ID-01 -->

**CA-01.** When a call arrives, the service MUST answer it.
<!-- id: SDD-CA-01 | tdd: TDD-1.1 | gap: #7 -->

- Actor: a caller.
- Behavior: the service answers.
- Verified by: the answer test.

**CA-02.** The service keeps `the_call_row` and must log. It MUST store and MUST send the call, and after that it writes many more words than the limit of the standard allows here.
<!-- id: SDD-CA-02 | tdd: none | status: implemented | gap: later -->

- Trigger: a call.
- Behavior: the service MUST store.

Loose text.

**RI-1.** Unless the line is busy, the service MUST ring.
<!-- id: SDD-RI-1 | tdd: none | sys: SYS-ID-02 -->

- Verified by: the ring test.
"""


class Standard(Fixture):
    def setUp(self):
        super().setUp()
        self.write('docs/spec/SDD.md', STANDARD)
        self.write('docs/spec/TDD.md', '# TDD\n\n#### TDD-1.1 Answer\n<!-- id: TDD-1.1 | implements: CA-01 | code: src/answer.ts | tests: tests/pass.test.ts -->\n')
        self.commit('standard')

    def test_the_form_rules_name_each_break_of_an_item(self):   # SDD-SP-07 to SDD-SP-14
        sdd = self.tree()['repositories']['r']['sdd']
        self.assertEqual(sdd['CA-01']['form'], [])
        self.assertEqual(sdd['CA-02']['form'], [
            ['SP-07', 'MUST 2 times'], ['SP-07', 'more than one sentence'], ['SP-08', '31 words'], ['SP-10', 'part Trigger'],
            ['SP-09', 'MUST in a part'], ['SP-10', 'text outside the parts'], ['SP-10', 'no Verified by'],
            ['SP-11', '1 code names, first `the_call_row`'], ['SP-13', 'status in the trace comment'], ['SP-14', 'gap is later']])
        self.assertEqual(sdd['RI-1']['form'], [['SP-07', 'no EARS pattern'], ['SP-12', 'the identifier is not area and number']])
        page = self.page()
        self.assertIn('<h2 id="form">The item form of the standard</h2>', page)
        self.assertIn('1 of 3 SDD items break no rule.', page)
        self.entry['interface_names'] = ['the_call_row']
        self.save()
        self.assertNotIn('SP-11', [rule for rule, _ in self.tree()['repositories']['r']['sdd']['CA-02']['form']])

    def test_form_with_a_base_examines_only_the_items_that_a_change_touches(self):   # SDD-SP-17
        base = sh(self.repo, 'git', 'rev-parse', 'HEAD')
        done = self.run_cli('form', expected=1)
        self.assertIn('docs/spec/SDD.md:21: CA-02: SP-13: status in the trace comment', done.stdout.splitlines())
        self.assertIn('docs/spec/SDD.md:29: RI-1: SP-12: the identifier is not area and number', done.stdout.splitlines())
        done = self.run_cli('form', '--base', base)   # nothing changed: the old items are measured, not refused
        self.assertEqual(done.stdout, '')
        text = STANDARD.replace('- Verified by: the ring test.', '- Verified by: the ring test of the line.')
        self.write('docs/spec/SDD.md', text)
        self.commit('touch RI-1')
        done = self.run_cli('form', '--base', base, expected=1)
        self.assertEqual([line.split(': ')[1] for line in done.stdout.splitlines()], ['RI-1', 'RI-1'])
        self.write('docs/spec/SDD.md', text.replace('- Behavior: the service answers.', '- Behavior: the service answers at once.'))
        self.commit('touch CA-01 only')
        self.assertEqual(self.run_cli('form', '--base', 'HEAD~1').stdout, '')   # the changed item keeps the form

    def test_the_first_chapter_holds_the_system_requirements_and_each_section_names_its_owner(self):   # SDD-SP-03, SDD-SP-04
        tree = self.tree()
        reqs = {r['id']: r for s in tree['top'] for r in s['requirements']}
        self.assertEqual(sorted(reqs), ['SYS-ID-01', 'SYS-ID-02'])
        self.assertEqual(reqs['SYS-ID-01']['groups'], [['r', 'section/2']])
        self.assertEqual(reqs['SYS-ID-02']['items'], [['r', 'RI-1']])   # one item names a second system requirement
        sdd = tree['repositories']['r']['sdd']
        self.assertEqual(sorted(sdd), ['CA-01', 'CA-02', 'RI-1'])   # a system requirement is no SDD item
        self.assertEqual(sdd['RI-1']['named_by'], ['SYS-ID-01', 'SYS-ID-02'])
        self.assertEqual(tree['faults'], [])
        page = self.page()
        self.assertLess(page.index('id="SYS-ID-01"'), page.index('id="r-CA-01"'))
        self.write('docs/spec/SDD.md', STANDARD.replace('sys: SYS-ID-01 -->', 'sys: SYS-ID-09 -->')
                   + '\n## 3. Later\n\n**LA-01.** The service MUST stop.\n<!-- id: SDD-LA-01 | tdd: none -->\n')
        self.commit('owners')
        done = self.run_cli('check', expected=1)
        self.assertIn('docs/spec/SDD.md:11: the section 2. Calls names SYS-ID-09, which is no system requirement', done.stderr)
        self.assertIn('docs/spec/SDD.md:34: the section 3. Later names 0 owners; it needs exactly one (sys:)', done.stderr)

    def test_a_gap_over_passing_tests_is_a_difference(self):   # SDD-SP-14
        self.run_cli('test')
        repo = self.tree()['repositories']['r']
        self.assertEqual((repo['sdd']['CA-01']['status'], repo['sdd']['CA-01']['declared'], repo['sdd']['CA-01']['differs']),
                         ('proved', 'gap:#7', True))
        self.assertIn('declared: gap:#7; computed: proved; cites #7', self.page())

    def test_a_separate_system_document_is_joined_through_the_owners_of_the_sections(self):   # SDD-SP-02, SDD-SP-04
        self.write('docs/spec/SDD.md', STANDARD.split('## 2. Calls')[0].split('## 1. System requirements')[0]
                   + '## 2. Calls' + STANDARD.split('## 2. Calls')[1])
        self.write('SYSTEM.md', '# System\n\n## 1. What it is\n\n**ID-01.** The system MUST answer each call.\n<!-- id: SYS-ID-01 -->\n\n'
                                '**ID-02.** The system MUST keep each call.\n<!-- id: SYS-ID-02 -->\n')
        self.commit('system document')
        self.save(top={'path': 'SYSTEM.md', 'prefix': 'SYS', 'repository': 'r'})
        tree = self.tree()
        reqs = {r['id']: r for s in tree['top'] for r in s['requirements']}
        self.assertEqual(reqs['SYS-ID-01']['groups'], [['r', 'section/2']])
        self.assertEqual(reqs['SYS-ID-02']['items'], [['r', 'RI-1']])
        self.assertEqual(tree['faults'], [])   # with owners in the sections, a system requirement needs no sdd: field


class Source(Fixture):
    def test_a_ref_is_compiled_in_the_compilers_own_worktree(self):   # SDD-ST-10
        first = sh(self.repo, 'git', 'rev-parse', 'HEAD')
        sh(self.repo, 'git', 'branch', 'release')
        self.write('docs/spec/SDD.md', SDD.replace('The service must answer.', 'The service must answer fast.'))
        second = self.commit('main moves')
        self.write('src/dirty.ts', 'export const dirty = 1\n')   # the session's checkout is dirty and must stay as it is
        self.entry['source'] = 'release'
        self.save()
        repo = self.tree()['repositories']['r']
        self.assertEqual(repo['head'], first)
        self.assertEqual(repo['sdd']['AA-01']['title'], 'The service must answer.')
        self.assertEqual(repo['dirty'], 0)
        self.assertTrue((self.repo / '.claude/worktrees/spec-tree/docs/spec/SDD.md').is_file())
        self.assertEqual(sh(self.repo, 'git', 'rev-parse', 'HEAD'), second)
        self.assertEqual(sh(self.repo, 'git', 'rev-parse', '--abbrev-ref', 'HEAD'), 'main')
        self.assertTrue((self.repo / 'src/dirty.ts').is_file())
        sh(self.repo, 'git', 'branch', '-f', 'release', second)   # the ref moves; only the compiler's worktree follows
        self.assertEqual(self.tree()['repositories']['r']['head'], second)
        self.assertEqual(sh(self.repo, 'git', 'for-each-ref', '--format=%(refname:short)', 'refs/heads'), 'main\nrelease')

    def test_the_checkout_source_counts_uncommitted_paths(self):   # SDD-ST-10
        self.write('src/dirty.ts', 'export const dirty = 1\n')
        self.assertEqual(self.tree()['repositories']['r']['dirty'], 1)
        self.assertIn('<td>1</td><td>single</td>', self.page())


class Config(Fixture):
    def test_each_config_problem_is_one_line_and_stops_the_compile(self):   # SDD-ST-15
        self.config.write_text(json.dumps({'schema': 'other', 'name': 'x', 'extra': 1,
                                           'repositories': [{'name': 'r', 'path': 'nowhere', 'layout': 'tables', 'colour': 'red'}]}))
        done = self.run_cli('compile', expected=2)
        problems = [line.split(': ', 2)[2] for line in done.stderr.splitlines()]
        self.assertEqual(problems, ['unknown field: extra', "schema is 'other', not dev-platform.spec-tree@1",
                                    'repository 1: unknown field: colour', "repository 1: layout is 'tables'; use one of single, domains, sections, none",
                                    f'repository 1: no folder at {self.tmp}/nowhere'])
        self.assertFalse((self.tmp / 'tree.html').exists())

    def test_a_project_record_of_the_platform_names_the_repository_and_the_page(self):   # SDD-PJ-01, SDD-PJ-06
        projects = self.tmp / 'projects'
        projects.mkdir()
        (projects / 'fixture.json').write_text(json.dumps({
            'schema': spectree.SCHEMA, 'name': 'fixture', 'top': None,
            'repositories': [{'name': 'r', 'path': str(self.repo), 'layout': 'single'}]}))
        env = dict(self.env, DEV_PLATFORM_PROJECTS=str(projects))
        done = subprocess.run([sys.executable, '-I', str(CLI), 'compile', 'fixture'], env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.repo / '.git/dev-platform/tree.html').is_file())   # scoped to the repository, in its Git folder
        self.assertFalse((projects / 'tree.html').exists())
        self.assertEqual(sh(self.repo, 'git', 'status', '--porcelain', '--ignored'), '')   # the compiler writes no file into the working tree
        sh(self.repo, 'git', 'worktree', 'add', '-q', '--detach', str(self.tmp / 'second'))
        self.assertEqual(sh(self.tmp / 'second', 'git', 'status', '--porcelain', '--ignored'), '')   # a second worktree shares the Git folder
        record = json.loads((projects / 'fixture.json').read_text())
        (projects / 'fixture.json').write_text(json.dumps(dict(record, page=str(self.tmp / 'elsewhere'))))
        done = subprocess.run([sys.executable, '-I', str(CLI), 'compile', 'fixture'], env=env, capture_output=True, text=True)
        self.assertTrue((self.tmp / 'elsewhere/tree.html').is_file(), done.stderr)   # the record can name a different folder
        self.assertFalse((self.tmp / 'elsewhere/.gitignore').exists())
        # A folder in the working tree, for example for a CI job: its own ignore file hides it; no file of the repository changes.
        (projects / 'fixture.json').write_text(json.dumps(dict(record, page=str(self.repo / 'out/spec'))))
        done = subprocess.run([sys.executable, '-I', str(CLI), 'compile', 'fixture'], env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.repo / 'out/spec/tree.html').is_file())
        self.assertEqual((self.repo / 'out/spec/.gitignore').read_text().splitlines()[-1], '*')
        self.assertEqual(sh(self.repo, 'git', 'status', '--porcelain'), '')
        self.assertIn('a formatter or a check of the repository can still read it', done.stdout)
        done = subprocess.run([sys.executable, '-I', str(CLI), 'compile', 'other'], env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn('no project named other', done.stderr)

    def test_the_command_uses_the_standard_library_only(self):   # SDD-ST-16
        done = subprocess.run([sys.executable, '-I', '-S', str(CLI), '--help'], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('compile,check,test', done.stdout.replace(' ', ''))
        source = (PLATFORM / 'lib/ai_ecosystem/spectree.py').read_text()
        imports = {line.split()[1].split('.')[0] for line in source.splitlines() if line.startswith('import ')}
        self.assertLessEqual(imports, set(sys.stdlib_module_names))



class Native(Fixture):
    """A repository that owns its tool and its config: the pipeline runs the copy (SDD-ST-17, SDD-ST-18, SDD-PJ-02)."""

    def test_a_junit_file_of_a_pipeline_is_kept_as_the_result_and_no_test_runs(self):   # SDD-ST-08
        self.entry['test'] = f'touch {self.tmp}/ran && false'
        self.save()
        done = self.run_cli('test', '--junit', str(self.tmp / 'junit.xml'))
        self.assertIn('no test ran', done.stdout)
        self.assertFalse((self.tmp / 'ran').exists())
        repo = self.tree()['repositories']['r']
        self.assertEqual((repo['results_valid'], repo['tdd']['TDD-1.1']['status'], repo['tdd']['TDD-1.2']['status']), (True, 'proved', 'failing'))
        self.assertIn('is no file', self.run_cli('test', '--junit', str(self.tmp / 'absent.xml'), expected=2).stderr)

    def test_the_proof_gate_fails_on_an_item_that_is_not_proved_and_names_no_gap(self):   # SDD-ST-17
        self.run_cli('test')
        self.run_cli('check')   # the fixture has no fault: the plain check passes
        done = self.run_cli('check', '--proved', expected=1)
        self.assertIn('docs/spec/SDD.md:10: AA-02 is not proved: failing (a named test fails)', done.stderr)
        self.assertIn('5 SDD items are not proved and name no gap', done.stdout)
        self.assertNotIn('AA-01', done.stderr)
        self.write('docs/spec/SDD.md', '# SDD\n\n## 1. First\n\n**AA-01.** The service MUST answer.\n<!-- id: SDD-AA-01 | tdd: TDD-1.1 -->\n\n'
                   '**AA-03.** The service MUST store the call.\n<!-- id: SDD-AA-03 | tdd: TDD-1.3 | gap: #7 -->\n')
        self.write('docs/spec/TDD.md', '# TDD\n\n## 1. First\n\n#### TDD-1.1 Answer\n<!-- id: TDD-1.1 | implements: AA-01 | code: src/answer.ts '
                   '| tests: tests/pass.test.ts -->\n\n#### TDD-1.3 Store\n<!-- id: TDD-1.3 | implements: AA-03 | code: src/store.ts | tests: none -->\n')
        self.commit('one proved item and one gap that names its task')
        self.assertIn('0 SDD items are not proved and name no gap', self.run_cli('check', '--proved').stdout)

    def test_a_record_of_a_native_project_takes_the_settings_from_the_config_of_the_repository(self):   # SDD-PJ-02
        own = {'schema': 'spec-tree@1', 'name': 'fixture', 'top': None,
               'repositories': [{'name': 'r', 'path': '.', 'layout': 'single', 'flag_words': ['service']}]}
        self.write('spec-tree.json', json.dumps(own))
        self.commit('the repository owns its config')
        projects = self.tmp / 'projects'
        projects.mkdir()
        record = {'schema': spectree.SCHEMA, 'name': 'fixture', 'config': 'spec-tree.json', 'page': str(self.tmp),
                  'repositories': [{'name': 'r', 'path': str(self.repo), 'flag_words': ['button']}]}
        (projects / 'fixture.json').write_text(json.dumps(record))
        env = dict(self.env, DEV_PLATFORM_PROJECTS=str(projects))
        run = lambda *args: subprocess.run([sys.executable, '-I', str(CLI), *args], env=env, capture_output=True, text=True)
        done = run('compile', 'fixture')
        self.assertEqual(done.returncode, 0, done.stderr)
        repo = json.loads((self.tmp / 'tree.data.json').read_text())['repositories']['r']
        self.assertEqual(len(repo['sdd']), 6)                                     # the layout came from the config of the repository
        self.assertIn('service', repo['sdd']['AA-01'].get('flag_words', {}))      # and its value wins over the value of the record
        sh(self.repo, 'git', 'branch', 'spec')            # the compiler reads a ref: it takes the config of that ref
        sh(self.repo, 'git', 'rm', '-q', 'spec-tree.json')
        self.commit('this branch has no config')
        self.assertIn('spec-tree.json is not in the repository', run('compile', 'fixture').stderr)
        record['repositories'][0]['source'] = 'spec'
        (projects / 'fixture.json').write_text(json.dumps(record))
        (self.repo / '.git/info/exclude').write_text('.claude/\n')
        self.assertEqual(run('compile', 'fixture', '--no-fetch').returncode, 0)

    def test_an_exported_copy_names_no_platform_and_compiles_a_tree(self):   # SDD-ST-18
        out = self.tmp / 'tools'
        done = subprocess.run([sys.executable, '-I', str(CLI), 'export', str(out)], env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        manifest = json.loads((out / 'MANIFEST.json').read_text())
        import hashlib
        for rel, digest in manifest['files'].items():
            text = (out / rel).read_text()
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), digest)
            for word in ('dev-platform', 'dev-spec', 'ai_ecosystem', 'DEV_PLATFORM', 'export-begin'):
                self.assertNotIn(word, text, rel)
        self.write('spec-tree.json', json.dumps({'schema': 'spec-tree@1', 'name': 'fixture', 'top': None,
                                                 'repositories': [{'name': 'r', 'path': '.', 'layout': 'single'}]}))
        self.commit('the config of the repository')
        env = {'PATH': os.environ['PATH'], 'HOME': str(self.tmp), 'SPEC_TREE_STATE': str(self.tmp / 'ci-state'),
               'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
        copy = lambda *args: subprocess.run([sys.executable, '-I', str(out / 'spec-tree'), *args, '--config', 'spec-tree.json'],
                                            cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertIn('results kept', copy('test', '--junit', str(self.tmp / 'junit.xml')).stdout)
        done = copy('compile')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(f'page: {self.repo}/.git/spec-tree/tree.html', done.stdout)   # the folder has the neutral name also
        self.assertIn('spec-tree@1', (self.repo / '.git/spec-tree/tree.data.json').read_text())
        self.assertEqual(copy('check', '--proved').returncode, 1)
        self.assertTrue((self.tmp / 'ci-state').is_dir())
        self.assertEqual(sh(self.repo, 'git', 'status', '--porcelain'), '')
        done = subprocess.run([sys.executable, '-I', str(out / 'spec-tree'), 'export', str(self.tmp / 'again')], env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)   # a copy makes no copy
        done = subprocess.run([sys.executable, '-I', str(CLI), 'export', str(out), '--name', 'dev-spec'], env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)


if __name__ == '__main__':
    unittest.main()
