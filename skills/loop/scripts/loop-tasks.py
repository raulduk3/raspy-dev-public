#!/usr/bin/env python3
"""Tasks for a local repository, read from docs/tasks/ on a Git ref, in the shape `gh` returns.

A task is `docs/tasks/<N>-<slug>.md`: its first `# ` heading is the title and the file is the
body. A `Status:` line of `ready` makes it selectable (the `sprint-ready` label); `Labels:` adds
comma-separated labels. A task moved to `docs/tasks/done/` is closed. The number N is the join
key the loop uses everywhere else: worktree, branch, ledger and `Closes #N`.

A task can also be `docs/tasks/<N>.json`, a typed item that `schemas/task/v1.schema.json` checks
(decision 0002, SDD area TK). It gets the same shape: a body with `Scope:` and `Depends on:`
lines, written from its fields. A commit with the trailer `Closes: #N` closes it. It is `sprint-ready` only when its state is ready, its kind is
code or spec and its assignee is not a person; another ready task is `not-for-workers`.

Usage: loop-tasks.py <checkout> <ref> issues          open tasks, as `gh issue list --json`
       loop-tasks.py <checkout> <ref> closed          closed task numbers, as [{"number": N}]
       loop-tasks.py <checkout> <ref> view <N>        one task, as `gh issue view --json`
       loop-tasks.py <checkout> <ref> path <N>        the task file's path in the repository
       loop-tasks.py <checkout> <ref> html            the open tasks as one HTML table with no styles
       loop-tasks.py <checkout> <ref> to-move <N>     the path to move to done/ at fold or close: a
                                                      Markdown task only; a JSON task stays, git's
                                                      `Closes: #N` trailer closes it

Writing tasks works on the checkout's files, committed or not:
       loop-tasks.py <checkout> <ref> next            the next unused task number
       loop-tasks.py <checkout> <ref> new <title> --scope <prefixes> [--depends '#1, #2'|none]
                     [--labels a,b] [--ready]         write a task file (Status: draft unless
                     [--goal G-n] [--kind code]       --ready) and print its path. With LOOP_TASKS=json
                                                      (repos.conf tasks=json) it writes <N>.json, a draft
                                                      whose placeholder lines `check` refuses once ready
       loop-tasks.py <checkout> <ref> check           report task files the loop would skip or
                                                      misread; exit 1 when there is one
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

TASKS = 'docs/tasks/'
DONE = TASKS + 'done/'
NAME = re.compile(r'^(\d+)(?:-[^/]+\.md|\.json)$')
PLATFORM = Path(__file__).resolve().parents[3]
SCHEMA = 'docs/tasks/task.schema.json'
WORKER_KINDS = ('code', 'spec')


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


PLACEHOLDER = 'TO WRITE: '


def new_json(checkout, number, args):
    if not re.fullmatch(r'[A-Z][A-Z0-9]*-[0-9]+', args.goal or ''):
        sys.exit('loop-tasks: a JSON task needs --goal, for example --goal G-1')
    scope = [p.strip() for p in args.scope.split(',') if p.strip()]
    depends = [int(n) for n in re.findall(r'#(\d+)', args.depends or '')]
    data = {'$schema': 'task.schema.json', 'schema': 'dev-platform/task@1', 'id': number, 'title': args.title.strip(),
            'kind': args.kind, 'goal': args.goal, 'state': 'ready' if args.ready else 'draft',
            'depends_on': depends, 'refs': [],
            'brief': PLACEHOLDER + 'the task in prose: what is true now, the change and why',
            'work': {'scope': scope},
            'acceptance': [{'by': 'review', 'statement': PLACEHOLDER + 'one check for each result', 'reviewer': 'owner'}],
            'created': __import__('datetime').date.today().isoformat()}
    labels = [label.strip() for label in args.labels.split(',') if label.strip()]
    if labels:
        data['labels'] = labels
    path = f'{TASKS}{number}.json'
    target = Path(checkout) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'x') as handle:
        handle.write(json.dumps(data, indent=2) + '\n')
    print(path)


def new(checkout, ref, argv):
    parser = argparse.ArgumentParser(prog='loop-tasks.py <checkout> <ref> new')
    parser.add_argument('title')
    parser.add_argument('--scope', required=True)
    parser.add_argument('--depends', default='none')
    parser.add_argument('--labels', default='')
    parser.add_argument('--ready', action='store_true')
    parser.add_argument('--goal')
    parser.add_argument('--kind', default='code', choices=['code', 'spec'])
    args = parser.parse_args(argv)
    if '\n' in args.title or not args.title.strip():
        sys.exit('loop-tasks: a task title is one non-empty line')
    number = next_number(checkout, ref)
    if os.environ.get('LOOP_TASKS') == 'json':
        return new_json(checkout, number, args)
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
    json_paths = []
    for number, paths in sorted(found.items()):
        path = paths[0]
        if path.startswith(DONE):
            continue
        if path.endswith('.json'):
            json_paths.append(root / path)
            problems += json_depends(root / path, number, found)
            try:
                data = json.loads((root / path).read_text())
            except ValueError:
                data = None  # the schema check reports it
            if isinstance(data, dict) and data.get('state') == 'ready' and PLACEHOLDER in json.dumps(data):
                problems.append(f'{path}: ready, but it still has a "{PLACEHOLDER.strip()}" line')
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
    if json_paths:
        schema = root / SCHEMA
        problems += schema_check().problems(json_paths, schema if schema.is_file() else PLATFORM / 'schemas/task/v1.schema.json')
    return problems


def schema_check():
    """The template's task check: the same code that a repository's own `scripts/check` runs."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('tasks_check', PLATFORM / 'templates/scripts/checks/tasks.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_depends(path, number, found):
    try:
        data = json.loads(path.read_text())
    except ValueError:
        return []  # the schema check reports it
    out = []
    for dep in data.get('depends_on') or [] if isinstance(data, dict) else []:
        if dep == number:
            out.append(f'{path}: depends on itself')
        elif isinstance(dep, int) and dep not in found:
            out.append(f'{path}: depends on #{dep}, which has no task file')
    return out


def json_body(data):
    """A JSON task as the plain lines a Markdown task carries, so plan, dispatch and fold read it."""
    work = data.get('work') or {}
    deps = ', '.join(f'#{d}' for d in data.get('depends_on') or []) or 'none'
    lines = [f'# {data.get("title", "")}', '', f'Status: {data.get("state", "")}', f'Kind: {data.get("kind", "")}',
             f'Goal: {data.get("goal", "")}']
    if data.get('labels'):
        lines.append('Labels: ' + ', '.join(data['labels']))
    if work.get('scope'):
        lines.append('Scope: ' + ','.join(work['scope']))
    lines.append(f'Depends on: {deps}')
    local = [r['id'] for r in data.get('refs') or [] if r.get('type') == 'decision' and not r.get('repo')]
    if local:
        lines.append('Decisions: ' + ', '.join(local))
    if data.get('assignee'):
        lines.append('Assignee: ' + ' '.join(filter(None, (data['assignee'].get('type'), data['assignee'].get('name')))))
    if data.get('blocked'):
        lines.append(f'Blocked: {data["blocked"]["reason"]} (needs {data["blocked"]["needs"]})')
    for name, items in (('References', [' '.join(filter(None, (r.get('type'), r.get('repo'), r.get('id'), r.get('note'))))
                                        for r in data.get('refs') or []]),
                        ('Facts', [f['text'] + (f' (as of {f["as_of"]})' if f.get('as_of') else '') for f in data.get('facts') or []]),
                        ('Work', [f'{k}: {v}' for k, v in work.items() if k not in ('scope', 'changes', 'steps', 'transform')]),
                        ('Changes', work.get('changes') or work.get('steps') or work.get('transform') or []),
                        ('Acceptance', [check_line(c) for c in data.get('acceptance') or []])):
        if items:
            lines += ['', f'{name}:'] + [f'- {item}' for item in items]
    if data.get('brief'):
        lines += ['', 'Brief:', '', data['brief'].strip()]  # the task in its own words, whole (SDD-TK-11)
    return '\n'.join(lines) + '\n'


def check_line(check):
    how = {k: v for k, v in check.items() if k not in ('by', 'statement')}
    return f'[{check.get("by")}] {check.get("statement")}' + (' (' + ', '.join(f'{k}: {v}' for k, v in how.items()) + ')' if how else '')


DECISIONS = 'docs/decisions/'
# A citation is explicit: a path under docs/decisions/ or a `Decision:`/`Decisions:` line. Prose such
# as "the demo's decision 0027" names another repository's record and is not a citation.
CITED = re.compile(r'(?mi)docs/decisions/(\d{4})-|^(?:- )?Decisions?: *((?:\d{4}[ ,]*(?:and )?)+)')


def decision_status(checkout, ref, cache={}):
    """{number: (status, title)} for the decision files on the ref."""
    if (checkout, ref) not in cache:
        listing = subprocess.run(['git', '-C', checkout, 'ls-tree', '-r', '--name-only', ref, '--', DECISIONS],
                                 capture_output=True, text=True).stdout.split()
        found = {}
        for path in listing:
            match = re.match(r'^docs/decisions/(\d{4})-[^/]+\.md$', path)
            if not match or match.group(1) == '0000':
                continue
            text = subprocess.run(['git', '-C', checkout, 'show', f'{ref}:{path}'], capture_output=True, text=True).stdout
            status = re.search(r'(?mi)^(?:- )?Status: *([A-Za-z-]+)', text)
            title = next((line.lstrip('# ').strip() for line in text.splitlines() if line.startswith('# ')), path)
            found[match.group(1)] = ((status.group(1).lower() if status else 'unknown'), title)
        cache[(checkout, ref)] = found
    return cache[(checkout, ref)]


def governance(checkout, ref, body, labels):
    """Why a ready task must wait on the owner, or None. A task that cites a decision file waits
    until every cited decision is accepted; a task carrying a governed label (LOOP_GOVERNED_LABELS,
    for example legal, insurance) also needs at least one accepted decision. The owner's
    acceptance is the gate: intake drafts decisions as `Status: proposed` and stops.
    With LOOP_DECISIONS=none or frozen (no decision record) a cited decision is history and gates
    nothing, and a governed label waits on the owner's word, since no new decision can be written."""
    governed = {g.strip().lower() for g in os.environ.get('LOOP_GOVERNED_LABELS', '').split(',') if g.strip()}
    hit = sorted(governed & {label.lower() for label in labels})
    if os.environ.get('LOOP_DECISIONS') in ('none', 'frozen'):
        return f"a {hit[0]} task needs the owner's word" if hit else None
    cited = set()
    for match in CITED.finditer(body):
        cited.update(re.findall(r'\d{4}', ''.join(g or '' for g in match.groups())))
    cited.discard('0000')
    decisions = decision_status(checkout, ref) if cited else {}
    for number in sorted(cited):
        status, _ = decisions.get(number, ('missing', ''))
        if status != 'accepted':
            return f'decision {number} is {status}'
    if hit and not cited:
        return f'a {hit[0]} task needs an accepted decision'
    return None


def task(checkout, ref, number, path):
    body = subprocess.run(['git', '-C', checkout, 'show', f'{ref}:{path}'],
                          capture_output=True, text=True, check=True).stdout
    if path.endswith('.json'):
        return json_task(checkout, ref, number, path, body)
    title = next((line[2:].strip() for line in body.splitlines() if line.startswith('# ')), path)
    field = lambda name: next((m.group(1).strip() for m in re.finditer(rf'(?m)^{name}: *(.+)$', body)), '')
    labels = [label.strip() for label in field('Labels').split(',') if label.strip()]
    waits = None
    if field('Status').lower() == 'ready' and path.startswith(TASKS) and not path.startswith(DONE):
        waits = governance(checkout, ref, body, labels)
        labels.append('waits-on-owner' if waits else 'sprint-ready')
    item = {'number': number, 'title': title, 'body': body, 'milestone': None,
            'labels': [{'name': label} for label in labels], 'path': path}
    if waits:
        item['waits'] = waits
    return item


def html_table(items, ref):
    """Open tasks as plain HTML (SDD-TK-08): semantic elements only, no style, class or script."""
    from html import escape
    rows = []
    for item in items:
        names = [label['name'] for label in item['labels']]
        state = item.get('state') or next((m.group(1) for m in re.finditer(r'(?m)^Status: *(\S+)', item['body'])), '')
        deps = item.get('depends_on') or re.findall(r'#(\d+)', next(iter(re.findall(r'(?m)^Depends on: *(.+)$', item['body'])), ''))
        checks = '<br>'.join(escape(check_line(c)) for c in item.get('acceptance') or [])
        cells = [f'#{item["number"]}', escape(item['title']), escape(item.get('kind') or ''), escape(item.get('goal') or ''),
                 escape(state + (' (waits: ' + item['waits'] + ')' if item.get('waits') else '')),
                 escape(', '.join(f'#{d}' for d in deps)), escape(', '.join(n for n in names)), checks,
                 escape(item['path'])]
        rows.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
    head = ''.join(f'<th>{h}</th>' for h in ('Task', 'Title', 'Kind', 'Goal', 'State', 'Depends on', 'Labels', 'Checks', 'File'))
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Open tasks</title></head><body>\n'
            f'<h1>Open tasks</h1>\n<p>{len(items)} open task(s) on {escape(ref)}.</p>\n'
            f'<table><thead><tr>{head}</tr></thead><tbody>\n' + '\n'.join(rows) + '\n</tbody></table>\n</body></html>')


def trailer_closed(checkout, ref):
    """Task numbers that a commit on the ref closes with the trailer `Closes: #N` (SDD-TK-05). A
    `Task: #N` trailer means work on task N and closes nothing."""
    log = subprocess.run(['git', '-C', checkout, 'log', ref, '--format=%(trailers:key=Closes,valueonly,separator=%x0A)'],
                         capture_output=True, text=True).stdout
    return {int(m) for m in re.findall(r'(?m)^#(\d+)\s*$', log)}


def json_task(checkout, ref, number, path, text):
    try:
        data = json.loads(text)
    except ValueError:
        data = {}
    body = json_body(data) if isinstance(data, dict) else ''
    labels = list(data.get('labels') or []) if isinstance(data, dict) else []
    if data.get('kind') == 'spec' and 'spec' not in labels:
        labels.append('spec')
    waits = None
    if data.get('state') == 'ready':
        worker = data.get('kind') in WORKER_KINDS and (data.get('assignee') or {}).get('type') != 'person'
        if worker:
            waits = governance(checkout, ref, body, labels)
            labels.append('waits-on-owner' if waits else 'sprint-ready')
        else:
            labels.append('not-for-workers')
    item = {'number': number, 'title': data.get('title') or path, 'body': body, 'milestone': None,
            'labels': [{'name': label} for label in labels], 'path': path,
            'kind': data.get('kind'), 'goal': data.get('goal'), 'state': data.get('state'),
            'depends_on': data.get('depends_on') or [], 'acceptance': data.get('acceptance') or []}
    if waits:
        item['waits'] = waits
    return item


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
    if any(path.endswith('.json') for (path,) in found.values()):
        closed |= {n for n in trailer_closed(checkout, ref) if n in found and found[n][0].endswith('.json')}
    if verb == 'issues':
        print(json.dumps([task(checkout, ref, n, found[n][0]) for n in sorted(found) if n not in closed]))
    elif verb == 'closed':
        print(json.dumps([{'number': n} for n in sorted(closed)]))
    elif verb == 'html' and not rest:
        print(html_table([task(checkout, ref, n, found[n][0]) for n in sorted(found) if n not in closed], ref))
    elif verb == 'to-move' and len(rest) == 1 and rest[0].isdigit():
        path = (found.get(int(rest[0])) or [''])[0]
        if path.endswith('.md') and not path.startswith(DONE):
            print(path)
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
