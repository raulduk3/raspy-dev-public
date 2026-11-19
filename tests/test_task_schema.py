"""The task schema (SDD-TK-02, TK-03, TK-04, TK-09) accepts one example of each kind and refuses
each broken shape. An existing validator runs it: jsonschema, or check-jsonschema through uvx."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'schemas/task/v1.schema.json'
EXAMPLES = ROOT / 'tests/fixtures/tasks'

spec = importlib.util.spec_from_file_location('tasks_check', ROOT / 'templates/scripts/checks/tasks.py')
assert spec and spec.loader
tasks_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tasks_check)


def have_validator():
    return importlib.util.find_spec('jsonschema') is not None or shutil.which('uvx') is not None


def example(number):
    return json.loads((EXAMPLES / f'{number}.json').read_text())


def without(task, *keys):
    for key in keys:
        task.pop(key, None)
    return task


# name -> (example to start from, change). Each result must fail.
BROKEN = {
    'unknown top-level field': (1, lambda t: t.update(lane='backend')),
    'no goal': (1, lambda t: without(t, 'goal')),
    'no check': (1, lambda t: t.update(acceptance=[])),
    'nine checks': (1, lambda t: t.update(acceptance=[t['acceptance'][1]] * 9)),
    'blocked with no reason': (1, lambda t: t.update(state='blocked')),
    'reason while ready': (7, lambda t: t.update(state='ready')),
    'code with no scope': (1, lambda t: t['work'].pop('scope')),
    'no brief': (1, lambda t: without(t, 'brief')),
    'empty brief': (1, lambda t: t.update(brief='')),
    'title over 140': (1, lambda t: t.update(title='x' * 141)),
    'spec outside docs': (2, lambda t: t['work'].update(scope=['src/'])),
    'research with no deliverable': (3, lambda t: t['work'].pop('deliverable')),
    'ops with no rollback': (4, lambda t: t['work'].pop('rollback')),
    'decision with one option': (5, lambda t: t['work'].update(options=t['work']['options'][:1])),
    'writing with an unknown form': (6, lambda t: t['work'].update(form='tweet')),
    'data with no transform': (7, lambda t: t['work'].pop('transform')),
    'eval with no metric': (7, lambda t: t['acceptance'][0].pop('metric')),
    'command check with a path': (1, lambda t: t['acceptance'][1].update(path='x')),
    'a local decision that is not four digits': (1, lambda t: t['refs'][1].update(id='98')),
    'ext key without x-': (1, lambda t: t.update(ext={'program': 'C'})),
    'unknown kind': (1, lambda t: t.update(kind='chore')),
    'done as a state': (1, lambda t: t.update(state='done')),
    'two-line title': (1, lambda t: t.update(title='One\nTwo')),
}


@unittest.skipUnless(have_validator(), 'no JSON Schema validator (jsonschema or uvx)')
class TaskSchema(unittest.TestCase):
    def test_one_example_of_each_kind_is_valid(self):
        files = sorted(EXAMPLES.glob('*.json'))
        kinds = {json.loads(f.read_text())['kind'] for f in files}
        self.assertEqual(kinds, {'code', 'spec', 'research', 'ops', 'decision', 'writing', 'data'})
        self.assertEqual(tasks_check.problems(files, SCHEMA), [])

    def test_each_broken_shape_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = {}
            for number, (name, (start, change)) in enumerate(sorted(BROKEN.items()), start=100):
                task = copy.deepcopy(example(start))
                task['id'] = number
                change(task)
                path = Path(tmp) / f'{number}.json'
                path.write_text(json.dumps(task))
                paths[name] = path
            found = '\n'.join(tasks_check.problems(list(paths.values()), SCHEMA))
            for name, path in paths.items():
                with self.subTest(name):
                    self.assertIn(str(path), found)

    def test_file_name_must_match_the_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '5.json'
            path.write_text(json.dumps(example(1)))
            self.assertTrue(any('does not match the file name' in p for p in tasks_check.problems([path], SCHEMA)))

    def test_template_schema_is_the_platform_schema(self):
        self.assertEqual((ROOT / 'templates/docs/tasks/task.schema.json').read_bytes(), SCHEMA.read_bytes())


if __name__ == '__main__':
    unittest.main()
