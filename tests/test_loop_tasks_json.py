"""dev-loop reads Markdown and JSON tasks in one repository in one shape (SDD-TK-06, TK-07)."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'skills/loop/scripts/loop-tasks.py'
EXAMPLES = ROOT / 'tests/fixtures/tasks'
ENV = {'PATH': '/usr/bin:/bin:' + str(Path.home() / '.local/bin'), 'HOME': str(Path.home()),
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com',
       'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.com'}

MARKDOWN = """# Fix the menu

Status: ready
Labels: enhancement
Scope: src/menu/
Depends on: none

Acceptance:
- The menu opens.
"""


def example(number, **change):
    data = json.loads((EXAMPLES / f'{number}.json').read_text())
    data.update(change)
    return data


class LoopTasksJson(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        tasks = self.repo / 'docs/tasks'
        tasks.mkdir(parents=True)
        shutil.copy(ROOT / 'schemas/task/v1.schema.json', tasks / 'task.schema.json')
        (tasks / '1-fix-the-menu.md').write_text(MARKDOWN)
        self.write(2, example(1, id=2, depends_on=[1], refs=[]))
        self.write(3, example(5, id=3))
        self.git('init', '-q', '-b', 'main')
        self.git('add', '.')
        self.git('commit', '-q', '-m', 'tasks')

    def write(self, number, data):
        (self.repo / f'docs/tasks/{number}.json').write_text(json.dumps(data, indent=2))

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.repo), *args], check=True, env=ENV)

    def run_tasks(self, *args):
        return subprocess.run(['python3', str(TASKS), str(self.repo), 'HEAD', *args],
                              capture_output=True, text=True, env=ENV)

    def test_both_formats_list_in_one_shape(self):
        items = {i['number']: i for i in json.loads(self.run_tasks('issues').stdout)}
        self.assertEqual(sorted(items), [1, 2, 3])
        for number in (1, 2):
            self.assertRegex(items[number]['body'], r'(?m)^Scope: ')
            self.assertRegex(items[number]['body'], r'(?m)^Depends on: ')
        self.assertIn('Depends on: #1', items[2]['body'])
        self.assertIn('sprint-ready', [label['name'] for label in items[2]['labels']])
        self.assertEqual(items[2]['path'], 'docs/tasks/2.json')

    def test_the_worker_body_ends_with_the_brief_whole(self):
        item = json.loads(self.run_tasks('view', '2').stdout)
        self.assertTrue(item['body'].rstrip().endswith(example(1)['brief']))

    def test_a_ready_decision_task_is_not_for_workers(self):
        item = json.loads(self.run_tasks('view', '3').stdout)
        names = [label['name'] for label in item['labels']]
        self.assertIn('not-for-workers', names)
        self.assertNotIn('sprint-ready', names)

    def test_a_task_for_a_person_is_not_for_workers(self):
        self.write(2, example(1, id=2, assignee={'type': 'person', 'name': 'owner'}, refs=[]))
        self.git('commit', '-qam', 'person')
        item = json.loads(self.run_tasks('view', '2').stdout)
        self.assertIn('not-for-workers', [label['name'] for label in item['labels']])

    @unittest.skipUnless(shutil.which('uvx') or __import__('importlib').util.find_spec('jsonschema'), 'no validator')
    def test_check_reports_an_invalid_json_task(self):
        self.assertEqual(self.run_tasks('check').returncode, 0, self.run_tasks('check').stdout)
        broken = example(1, id=2, depends_on=[9], refs=[])
        del broken['goal']
        self.write(2, broken)
        result = self.run_tasks('check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('depends on #9', result.stdout)
        self.assertIn('2.json', result.stdout)

    def test_a_task_trailer_closes_a_json_task_and_it_stays(self):
        (self.repo / 'src').mkdir()
        (self.repo / 'src/menu.txt').write_text('done')
        self.git('add', '.')
        self.git('commit', '-q', '-m', 'feat: menu (#2)', '-m', 'Task #2: 1 commit(s) from b, folded as one.', '-m', 'Task: #2\nCloses: #2')
        self.assertEqual(json.loads(self.run_tasks('closed').stdout), [{'number': 2}])
        self.assertNotIn(2, [i['number'] for i in json.loads(self.run_tasks('issues').stdout)])
        self.assertTrue((self.repo / 'docs/tasks/2.json').is_file())

    def test_a_task_trailer_alone_leaves_a_json_task_open(self):
        self.git('commit', '-q', '--allow-empty', '-m', 'work on the menu', '-m', 'Task: #2')
        self.assertEqual(json.loads(self.run_tasks('closed').stdout), [])

    def test_a_trailer_does_not_close_a_markdown_task(self):
        self.git('commit', '-q', '--allow-empty', '-m', 'x', '-m', 'Closes: #1')
        self.assertEqual(json.loads(self.run_tasks('closed').stdout), [])

    def test_only_a_markdown_task_moves_at_fold(self):
        self.assertEqual(self.run_tasks('to-move', '1').stdout.strip(), 'docs/tasks/1-fix-the-menu.md')
        self.assertEqual(self.run_tasks('to-move', '2').stdout.strip(), '')

    def test_fold_writes_the_task_trailer(self):
        script = (ROOT / 'skills/loop/scripts/loop.sh').read_text()
        self.assertIn("folded as one.\\n\\nTask: #%s\\nCloses: #%s\\n", script)
        self.assertIn('to-move "$i"', script)

    def test_view_is_plain_html_for_both_formats(self):
        from html.parser import HTMLParser
        out = self.run_tasks('html').stdout
        tags, attrs = set(), set()

        class Collect(HTMLParser):
            def handle_starttag(self, tag, attributes):
                tags.add(tag)
                attrs.update(name for name, _ in attributes)
        Collect().feed(out)
        self.assertFalse({'style', 'script', 'link'} & tags)
        self.assertFalse({'style', 'class'} & attrs)
        self.assertEqual(out.count('<tr><td>'), 3)
        self.assertIn('<td>#1</td><td>Fix the menu</td><td></td><td></td>', out)
        self.assertIn('G-1', out)

    def test_new_writes_a_json_draft_when_the_repository_opts_in(self):
        env = dict(ENV, LOOP_TASKS='json')
        made = subprocess.run(['python3', str(TASKS), str(self.repo), 'HEAD', 'new', 'Add the menu icon', '--scope', 'src/menu/',
                               '--depends', '#1', '--goal', 'G-1'], capture_output=True, text=True, env=env)
        self.assertEqual(made.stdout.strip(), 'docs/tasks/4.json', made.stderr)
        data = json.loads((self.repo / 'docs/tasks/4.json').read_text())
        self.assertEqual((data['state'], data['kind'], data['depends_on'], data['work']['scope']), ('draft', 'code', [1], ['src/menu/']))
        self.assertTrue(data['brief'].startswith('TO WRITE:'))
        if shutil.which('uvx') or __import__('importlib').util.find_spec('jsonschema'):
            self.assertEqual(self.run_tasks('check').returncode, 0, self.run_tasks('check').stdout)
            data['state'] = 'ready'
            self.write(4, data)
            self.assertIn('still has a "TO WRITE:" line', self.run_tasks('check').stdout)

    def test_new_without_a_goal_is_refused_for_json(self):
        made = subprocess.run(['python3', str(TASKS), str(self.repo), 'HEAD', 'new', 'X', '--scope', 'src/'],
                              capture_output=True, text=True, env=dict(ENV, LOOP_TASKS='json'))
        self.assertNotEqual(made.returncode, 0)
        self.assertIn('--goal', made.stderr)

    def test_new_writes_markdown_by_default(self):
        made = self.run_tasks('new', 'Add the menu icon', '--scope', 'src/menu/')
        self.assertTrue(made.stdout.strip().endswith('.md'), made.stdout)

    def test_two_files_for_one_number_fail(self):
        (self.repo / 'docs/tasks/2-dup.md').write_text(MARKDOWN)
        self.assertIn('more than one task file for #2', self.run_tasks('check').stdout)


if __name__ == '__main__':
    unittest.main()
