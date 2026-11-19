#!/usr/bin/env python3
"""Validate JSON task items (docs/tasks/<N>.json) against docs/tasks/task.schema.json.

Decision 0002 (dev-platform), SDD-TK-02. The schema is JSON Schema 2020-12; an existing validator
checks it: the `jsonschema` package when Python has it, else `check-jsonschema` through `uvx`.
This file adds only what a schema cannot say: the file name matches the task's id.

Usage: tasks.py [--cwd DIR] [--schema PATH] [FILE ...]
Exit 0 when every task is valid or there is none, 1 on a finding, 2 when no validator runs.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

NAME = re.compile(r'^(\d+)\.json$')


def task_files(root):
    folder = root / 'docs' / 'tasks'
    return sorted((p for p in folder.glob('*.json') if NAME.match(p.name)),
                  key=lambda p: int(p.stem)) if folder.is_dir() else []


def problems(files, schema_path):
    """`path: problem` lines for the given task files."""
    found = []
    loaded = {}
    for path in files:
        try:
            loaded[path] = json.loads(path.read_text())
        except (OSError, ValueError) as error:
            found.append(f'{path}: not JSON: {error}')
            continue
        match = NAME.match(path.name)
        if match and isinstance(loaded[path], dict) and loaded[path].get('id') != int(match.group(1)):
            found.append(f'{path}: id {loaded[path].get("id")!r} does not match the file name')
    if not loaded:
        return found
    schema = json.loads(Path(schema_path).read_text())
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        Draft202012Validator = None
    if Draft202012Validator:
        validator = Draft202012Validator(schema)
        for path, data in loaded.items():
            for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
                where = '/'.join(str(p) for p in error.absolute_path) or '(task)'
                found.append(f'{path}: {where}: {error.message}')
        return found
    uvx = shutil.which('uvx')
    if not uvx:
        sys.exit('tasks.py: no JSON Schema validator: install the Python package jsonschema, or uv for check-jsonschema')
    run = subprocess.run([uvx, '--quiet', 'check-jsonschema', '--schemafile', str(schema_path),
                          *[str(p) for p in loaded]], capture_output=True, text=True)
    if run.returncode not in (0, 1):
        sys.exit(f'tasks.py: check-jsonschema failed to run: {run.stderr.strip() or run.stdout.strip()}')
    if run.returncode == 1:
        found += [line for line in (run.stdout + run.stderr).splitlines()
                  if line.strip() and not line.startswith('Schema validation errors')]
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--cwd', default='.')
    parser.add_argument('--schema')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)
    root = Path(args.cwd)
    schema = Path(args.schema) if args.schema else root / 'docs' / 'tasks' / 'task.schema.json'
    files = [Path(f) for f in args.files] if args.files else task_files(root)
    if files and not schema.is_file():
        print(f'{schema}: no task schema; copy it from the platform templates', file=sys.stderr)
        return 1
    found = problems(files, schema)
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
