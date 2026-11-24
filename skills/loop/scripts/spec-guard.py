#!/usr/bin/env python3
"""The fold's specification guard for one worker branch.

  spec-guard.py <checkout> <rig> <commit> <spec single|domains> <decisions none|frozen|open> <spec-task 0|1>

The task's body (the text `loop-tasks.py view` gives) comes on stdin. Prints one problem a line
and exits 1 when the branch may not fold; prints nothing and exits 0 otherwise.

- decisions=none or frozen: no task adds, changes or deletes a file under docs/decisions/ or adds a
  SPEC-AMENDMENTS.md, a spec task included. With decisions=none a deletion is allowed.
- spec=domains, a task that is not a spec task: under docs/spec/ it may change only the `status:`,
  `tests:` and `code:` metadata lines of the items its body cites (`SDD-…`, `TDD-…`), and the
  generated docs/spec/index.json. A spec task may edit docs/spec/<domain>/ freely.
- spec=single keeps the rule in loop.sh: a build branch moves only `<!-- id: … -->` and
  `<!-- spec-lock … -->` lines.
"""
import re
import subprocess
import sys

HEADING = re.compile(r'^#{2,6} +((?:SDD|TDD)-[A-Za-z0-9][A-Za-z0-9._-]*)')
CITED = re.compile(r'\b((?:SDD|TDD)-[A-Za-z0-9][A-Za-z0-9._-]*)')
MARKER = re.compile(r'^(status|tests|code): ')
DOMAIN_FILE = re.compile(r'^docs/spec/[a-z0-9-]+/(sdd|tdd)\.md$')
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def git(checkout, *args):
    return subprocess.run(['git', '-C', checkout, *args], capture_output=True, text=True, check=True).stdout


def ident(text):
    return text.rstrip('.,;:)')


def record_problems(names, decisions):
    out = []
    for status, path in names:
        if decisions == 'none' and status == 'D':
            continue   # the owner's removal of the old records
        if path.startswith('docs/decisions/'):
            out.append(f'{path}: decision records are read-only (decisions={decisions})')
        elif status == 'A' and (path == 'SPEC-AMENDMENTS.md' or path.endswith('/SPEC-AMENDMENTS.md')):
            out.append(f'{path}: an amendment ledger is refused (decisions={decisions}); git records spec changes')
    return out


def owner_of(lines, number):
    """The id of the item whose heading is at or above line NUMBER (1-based), or ''."""
    for text in reversed(lines[:number]):
        m = HEADING.match(text)
        if m:
            return ident(m.group(1))
    return ''


def domain_problems(checkout, base, commit, names, cited):
    out = []
    for _, path in names:
        if not path.startswith('docs/spec/') or path == 'docs/spec/index.json':
            continue
        if not DOMAIN_FILE.match(path):
            out.append(f'{path}: only a spec task changes this file')
            continue
        old = git(checkout, 'show', f'{base}:{path}').splitlines() if exists(checkout, base, path) else []
        new = git(checkout, 'show', f'{commit}:{path}').splitlines() if exists(checkout, commit, path) else []
        diff = git(checkout, 'diff', '-U0', '--no-renames', base, commit, '--', path).splitlines()
        o = n = 0
        for line in diff:
            m = HUNK.match(line)
            if m:
                o, n = int(m.group(1)), int(m.group(3))
                continue
            if line.startswith(('+++', '---')) or not line[:1] in ('+', '-'):
                continue
            text = line[1:]
            if line[0] == '-':
                item, o = owner_of(old, o), o + 1
            else:
                item, n = owner_of(new, n), n + 1
            if not MARKER.match(text):
                out.append(f'{path}: changes requirement text; only a spec task may: {line[:100]}')
            elif item not in cited:
                out.append(f'{path}: changes a marker of {item or "no item"}, which the task does not cite: {line[:100]}')
    return out


def exists(checkout, ref, path):
    return subprocess.run(['git', '-C', checkout, 'cat-file', '-e', f'{ref}:{path}'],
                          capture_output=True).returncode == 0


def main(argv):
    if len(argv) != 6:
        sys.exit(__doc__)
    checkout, rig, commit, spec, decisions, spec_task = argv
    base = git(checkout, 'merge-base', rig, commit).strip()
    names = [tuple(line.split('\t', 1)) for line in
             git(checkout, 'diff', '--name-status', '--no-renames', base, commit).splitlines() if '\t' in line]
    problems = record_problems(names, decisions) if decisions in ('none', 'frozen') else []
    if spec == 'domains' and spec_task != '1':
        cited = {ident(m) for m in CITED.findall(sys.stdin.read())}
        problems += domain_problems(checkout, base, commit, names, cited)
    print('\n'.join(problems))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
