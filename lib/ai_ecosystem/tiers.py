#!/usr/bin/env python3
"""The source control tier of a repository (SDD-SC-01, decision 0001).

A repos.conf line is `owner/repo checkout local|owner|bot [base] [key=value ...]`. The keys are:

  tier=0..4         0 no git, 1 solo trunk, 2 personal shared, 3 protected company, 4 fork
  forge=github|bare|none
  tracker=files|github|side   side: task files in the side folder (side=<folder>), not in the repository
  tasks=md|json   (decision 0002: json keeps each task as docs/tasks/<N>.json; default md)
  slots=N           worker slots (default 2)
  large=1           workers get a sparse cone from the task scope
  keep=a,b          trunks that tidy never lists or deletes, beside the base: the branches that the
                    host protects or checks (the pre-receive hook of a bare repository)
  spec=single|domains
                    single (default): docs/spec/SDD.md and TDD.md; domains: docs/spec/<domain>/sdd.md
                    and tdd.md, found through docs/spec/index.json, with the steps of the
                    repository's AGENTS.md
  decisions=none|frozen|open
                    none (default of a registered line): the repository keeps no decision record.
                    Nothing adds or changes a file under docs/decisions/ or adds a
                    SPEC-AMENDMENTS.md (the git pre-commit hook and the loop's fold refuse it).
                    A deletion of an old record is allowed.
                    Intake changes the specification after the owner accepts the change; git
                    records the change and the commit message gives the reason (SDD-LP-60,
                    SDD-LP-61).
                    frozen: as none, with no deletion of a record, and intake changes no
                    specification (SDD-SC-20).
                    open: intake drafts decision records. A path that no line names is open: the
                    platform sets no rule for the decision files of a repository that it does not know.
  incoming=state|project
                    the place of the distill candidates (SDD-SC-10). state (default):
                    ~/.local/state/dev-platform/incoming/<repo>.html; project: docs/incoming.html in
                    the main checkout, which git must ignore. The record gives the path as incoming_file.

  off=a,b           the parts of the platform that are off for this repository: git (the Git rules of the
                    hooks and the guard), check (the stop check), tree, loop, team. The project record
                    states the parts that are on; dev-project sync writes this field.

A line without `tier=` gets tier 3. A path that no line names gets tier 3 if it is a Git
checkout, else tier 0. Tier 3 is the safe default for push and forge rules.

  tiers.py [--conf FILE] [--field NAME | --json] PATH|owner/repo

prints `key=value` lines that a shell can read, one field, or JSON.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_RE = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
MODES = ('local', 'owner', 'bot')
KEYS = {'tier': re.compile(r'[0-4]'), 'forge': re.compile(r'github|bare|none'),
        'tracker': re.compile(r'files|github|side'), 'tasks': re.compile(r'md|json'), 'slots': re.compile(r'[1-9][0-9]?'),
        'large': re.compile(r'[01]'), 'base': re.compile(r'[A-Za-z0-9._/-]+'),
        'keep': re.compile(r'[A-Za-z0-9._/-]+(,[A-Za-z0-9._/-]+)*'),
        'spec': re.compile(r'single|domains'), 'decisions': re.compile(r'none|frozen|open'),
        'incoming': re.compile(r'state|project'),
        # off=<part>,<part>: the parts of the platform that are off for the project (SDD-PJ-03, SDD-PJ-04).
        'off': re.compile(r'(git|check|tree|loop|team)(,(git|check|tree|loop|team))*'),
        # side=<folder>: the side folder of a ghost project (the rig folder). With tracker=side, the tasks are files
        # in docs/tasks/ of that folder, and the repository holds no task file (SDD-PJ-10).
        'side': re.compile(r'/[A-Za-z0-9._/-]+')}


def conf_path():
    return Path(os.environ.get('DEV_PLATFORM_REPOS', Path.home() / '.config/dev-platform/repos.conf'))


def identity(path):
    """The repository's common git dir, resolved; None when PATH is no checkout."""
    try:
        out = subprocess.run(['git', '-C', str(path), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode or not out.stdout.strip():
        return None
    return str(Path(out.stdout.strip()).resolve())


def parse_line(line):
    """One repos.conf line -> dict, or None for a blank or comment line. ValueError when malformed."""
    if not line.strip() or line.lstrip().startswith('#'):
        return None
    fields = line.split()
    positional = [f for f in fields if '=' not in f]
    keys = [f for f in fields if '=' in f]
    if len(positional) not in (3, 4) or not REPO_RE.fullmatch(positional[0]) or positional[2] not in MODES:
        raise ValueError('expected owner/repo checkout local|owner|bot [base] [key=value ...]')
    entry = dict(repo=positional[0], path=str(Path(positional[1]).expanduser()), mode=positional[2])
    if len(positional) == 4:
        entry['base'] = positional[3]
    for item in keys:
        key, _, value = item.partition('=')
        if key not in KEYS or not KEYS[key].fullmatch(value):
            raise ValueError(f'unknown or invalid field: {item}')
        entry[key] = value
    return entry


def read_conf(conf=None):
    conf = Path(conf) if conf else conf_path()
    entries = []
    if conf.is_file():
        for number, line in enumerate(conf.read_text().splitlines(), 1):
            try:
                entry = parse_line(line)
            except ValueError as error:
                raise ValueError(f'{conf}:{number}: {error}') from None
            if entry:
                entries.append(entry)
    return entries


def complete(entry):
    """Fill the defaults of one registered entry."""
    out = dict(entry)
    out['registered'] = 1
    if 'tier' not in out:
        out['tier'] = '3'
    if 'forge' not in out:
        if out['mode'] in ('owner', 'bot'):
            out['forge'] = 'github'
        else:
            remote = subprocess.run(['git', '-C', out['path'], 'remote', 'get-url', 'origin'],
                                    capture_output=True, text=True)
            out['forge'] = 'bare' if remote.returncode == 0 and remote.stdout.strip() else 'none'
    out.setdefault('tracker', 'files' if out['mode'] == 'local' else 'github')
    out.setdefault('tasks', 'md')
    out.setdefault('slots', '2')
    out.setdefault('large', '0')
    out.setdefault('base', '')
    out.setdefault('keep', '')
    out.setdefault('spec', 'single')
    out.setdefault('decisions', 'none')
    out.setdefault('incoming', 'state')
    return with_incoming(out)


def with_incoming(record):
    """Add incoming_file: the distill candidates of the repository (SDD-SC-10)."""
    out = dict(record)
    out.setdefault('incoming', 'state')
    out.setdefault('off', '')
    if out['incoming'] == 'project' and out.get('path'):
        out['incoming_file'] = str(Path(out['path']) / 'docs' / 'incoming.html')
    else:
        name = (out.get('repo') or '').rpartition('/')[2] or Path(out.get('path') or '').name
        out['incoming_file'] = str(Path.home() / '.local/state/dev-platform/incoming' / f'{name}.html') if name else ''
    return out


def resolve(target, conf=None):
    """PATH or owner/repo -> the tier record."""
    entries = read_conf(conf)
    if REPO_RE.fullmatch(target) and not Path(target).exists():
        for entry in entries:
            if entry['repo'] == target:
                return complete(entry)
        return with_incoming(dict(repo=target, path='', registered=0, tier='3', mode='', forge='none', tracker='files',
                                  tasks='md', slots='2', large='0', base='', keep='', spec='single', decisions='open'))
    path = Path(target).expanduser().resolve()
    common = identity(path)
    if common:
        for entry in entries:
            if identity(entry['path']) == common:
                return complete(entry)
    tier = '0' if not common else '3'
    return with_incoming(dict(repo='', path=str(path), registered=0, tier=tier, mode='', forge='none',
                              tracker='files', tasks='md', slots='2', large='0', base='', keep='', spec='single',
                              decisions='open'))


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description='Print the source control tier of a repository.')
    p.add_argument('--conf')
    p.add_argument('--field')
    p.add_argument('--json', action='store_true')
    p.add_argument('target')
    args = p.parse_args(argv)
    try:
        record = resolve(args.target, args.conf)
    except ValueError as error:
        print(f'tiers: {error}', file=sys.stderr)
        return 2
    if args.field:
        print(record.get(args.field, ''))
    elif args.json:
        print(json.dumps(record, sort_keys=True))
    else:
        for key in sorted(record):
            print(f'{key}={record[key]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
