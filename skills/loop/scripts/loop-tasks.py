#!/usr/bin/env python3
"""Tasks for a local repository, read from docs/tasks/ on a Git ref, in the shape `gh` returns.

A task is `docs/tasks/<N>-<slug>.md`: its first `# ` heading is the title and the file is the
body. A `Status:` line of `ready` makes it selectable (the `sprint-ready` label); `Labels:` adds
comma-separated labels. A task moved to `docs/tasks/done/` is closed. The number N is the join
key the loop uses everywhere else: worktree, branch, ledger and `Closes #N`.

Usage: loop-tasks.py <checkout> <ref> issues          open tasks, as `gh issue list --json`
       loop-tasks.py <checkout> <ref> closed          closed task numbers, as [{"number": N}]
       loop-tasks.py <checkout> <ref> view <N>        one task, as `gh issue view --json`
       loop-tasks.py <checkout> <ref> path <N>        the task file's path in the repository

Writing tasks works on the checkout's files, committed or not:
       loop-tasks.py <checkout> <ref> next            the next unused task number
       loop-tasks.py <checkout> <ref> new <title> --scope <prefixes> [--depends '#1, #2'|none]
                     [--labels a,b] [--ready]         write a task file (Status: draft unless
                                                      --ready) and print its path
       loop-tasks.py <checkout> <ref> check           report task files the loop would skip or
                                                      misread; exit 1 when there is one
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

TASKS = 'docs/tasks/'
DONE = TASKS + 'done/'
NAME = re.compile(r'^(\d+)-[^/]+\.md$')


def collect(paths):
    found = {}
    for path in paths:
        folder, _, name = path.rpartition('/')
        match = NAME.match(name)
        if match and folder + '/' in (TASKS, DONE):
            found.setdefault(int(match.group(1)), []).append(path)
    return found


def files(checkout, ref, required=True):
    listing = subprocess.run(['git', '-C', checkout, 'ls-tree', '-r', '--name-only', ref, '--', TASKS],
                             capture_output=True, text=True)
    if listing.returncode:
        if required:
            sys.exit(f'loop-tasks: cannot read {TASKS} on {ref}')
        return {}
    return collect(listing.stdout.splitlines())


def disk_files(checkout):  # the task files as they stand in the checkout, committed or not
    root = Path(checkout)
    return collect(str(p.relative_to(root)) for folder in (TASKS, DONE)
                   if (root / folder).is_dir() for p in (root / folder).iterdir() if p.is_file())


def next_number(checkout, ref):
    # Numbers are never reused: a number seen on the base or on disk, open or done, is taken.
    taken = set(files(checkout, ref, required=False)) | set(disk_files(checkout))
    return max(taken, default=0) + 1


def slug(title):
    words = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return words[:48].rstrip('-') or 'task'


def new(checkout, ref, argv):
    parser = argparse.ArgumentParser(prog='loop-tasks.py <checkout> <ref> new')
    parser.add_argument('title')
    parser.add_argument('--scope', required=True)
    parser.add_argument('--depends', default='none')
    parser.add_argument('--labels', default='')
    parser.add_argument('--ready', action='store_true')
    args = parser.parse_args(argv)
    if '\n' in args.title or not args.title.strip():
        sys.exit('loop-tasks: a task title is one non-empty line')
    number = next_number(checkout, ref)
    path = f'{TASKS}{number}-{slug(args.title)}.md'
    lines = [f'# {args.title.strip()}', '', f'Status: {"ready" if args.ready else "draft"}']
    if args.labels.strip():
        lines.append(f'Labels: {args.labels.strip()}')
    lines += [f'Scope: {args.scope.strip()}', f'Depends on: {args.depends.strip() or "none"}', '',
              'What to build, the acceptance criteria, and the specification sections that govern it.', '']
    target = Path(checkout) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'x') as handle:
        handle.write('\n'.join(lines))
    print(path)


def check(checkout):
    """Problems in the checkout's open task files, as `path: problem` lines."""
    root = Path(checkout)
    found = disk_files(checkout)
    problems = [f'{", ".join(paths)}: more than one task file for #{n}'
                for n, paths in sorted(found.items()) if len(paths) > 1]
    for number, paths in sorted(found.items()):
        path = paths[0]
        if path.startswith(DONE):
            continue
        body = (root / path).read_text()
        field = lambda name: next((m.group(1).strip() for m in re.finditer(rf'(?m)^{name}: *(.*)$', body)), None)
        if not any(line.startswith('# ') and line[2:].strip() for line in body.splitlines()):
            problems.append(f'{path}: no `# ` title heading')
        status = field('Status')
        if (status or '').lower() not in ('ready', 'draft'):
            problems.append(f'{path}: Status must be ready or draft, not {status!r}')
        if not field('Scope'):
            problems.append(f'{path}: no Scope: line with path prefixes; the loop will skip it')
        depends = field('Depends on')
        if not depends:
            problems.append(f'{path}: no Depends on: line; write `Depends on: none`')
        elif depends.lower() != 'none':
            for item in (part.strip() for part in depends.split(',')):
                cited = re.fullmatch(r'#(\d+)', item)
                if not cited:
                    problems.append(f'{path}: Depends on: {item!r} is not #N')
                elif int(cited.group(1)) == number:
                    problems.append(f'{path}: depends on itself')
                elif int(cited.group(1)) not in found:
                    problems.append(f'{path}: depends on #{cited.group(1)}, which has no task file')
    return problems


def task(checkout, ref, number, path):
    body = subprocess.run(['git', '-C', checkout, 'show', f'{ref}:{path}'],
                          capture_output=True, text=True, check=True).stdout
    title = next((line[2:].strip() for line in body.splitlines() if line.startswith('# ')), path)
    field = lambda name: next((m.group(1).strip() for m in re.finditer(rf'(?m)^{name}: *(.+)$', body)), '')
    labels = [label.strip() for label in field('Labels').split(',') if label.strip()]
    if field('Status').lower() == 'ready' and path.startswith(TASKS) and not path.startswith(DONE):
        labels.append('sprint-ready')
    return {'number': number, 'title': title, 'body': body, 'milestone': None,
            'labels': [{'name': label} for label in labels], 'path': path}


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    checkout, ref, verb, *rest = argv
    if verb == 'next' and not rest:
        print(next_number(checkout, ref))
        return
    if verb == 'new':
        new(checkout, ref, rest)
        return
    if verb == 'check' and not rest:
        problems = check(checkout)
        print('\n'.join(problems) if problems else
              f'ok: {sum(1 for p in disk_files(checkout).values() if not p[0].startswith(DONE))} open task(s)')
        sys.exit(1 if problems else 0)
    found = files(checkout, ref)
    duplicate = sorted(n for n, paths in found.items() if len(paths) > 1)
    if duplicate:
        sys.exit('loop-tasks: more than one task file for ' + ', '.join(f'#{n}' for n in duplicate))
    closed = {n for n, (path,) in found.items() if path.startswith(DONE)}
    if verb == 'issues':
        print(json.dumps([task(checkout, ref, n, found[n][0]) for n in sorted(found) if n not in closed]))
    elif verb == 'closed':
        print(json.dumps([{'number': n} for n in sorted(closed)]))
    elif verb in ('view', 'path') and len(rest) == 1 and rest[0].isdigit():
        number = int(rest[0])
        if number not in found:
            sys.exit(f'loop-tasks: no task #{number} in {TASKS} on {ref}')
        item = task(checkout, ref, number, found[number][0])
        print(item['path'] if verb == 'path' else json.dumps(item))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
