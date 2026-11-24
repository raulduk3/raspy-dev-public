"""dev-project: the project record is the one source of the settings of a project (docs/spec/SDD.md, area PJ).

    dev-project show   PATH|NAME        the record of a folder or a project, and the registry line that it gives
    dev-project import [--write]        make or complete a record for each line of the registry (one time)
    dev-project sync   [--write|--check]  make the registry and the check environment files from the records
    dev-project connect PATH [--name N] [--ghost [--side DIR]] [--tier T] [--base B] [--check CMD] [--layout L] [--yes]
                                        propose a record for a folder; write it after the owner confirms each value
    dev-project brief  [PATH] [--hook]  the text for an agent at the start of a session in a connected folder

A record is ~/.config/dev-platform/projects/<name>.json. Beside the fields of the specification tree, a repository
of a record has:

    "remote": "owner/name",          and the record itself:  "parts": ["git", "check", "tree", "control", "loop", "team"]
    "git":  {"tier": 3, "mode": "owner", "base": "develop", "forge": "github", "keep": ["main"], "slots": 2, "large": false},
    "work": {"tracker": "github", "tasks": "md", "decisions": "none", "incoming": "state",
             "check": "bun run check", "check_path": ["~/.bun/bin"], "env": {"NAME": "value"}}

The registry (repos.conf) and the check environment files (env.d/<folder>.sh) stay as files, because the hooks, the
loop and the menu read them. They are made from the records by `sync`; a person changes the record, not the file.
The layout of the specification gives the registry field spec=, and each line gets its tier, so the personal list
is read for no line.

`connect` writes one record and changes no tracked file of the repository: it only reads the repository with Git
(SDD-PJ-05). `brief` reads the record and the rules below; it reads no instruction file of the repository (SDD-PJ-07).
"""
import argparse
import difflib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

from . import tiers

SCHEMA = 'dev-platform.spec-tree@1'
HEAD = '# Made by dev-project sync from the project records. Do not edit: change the record, then run dev-project sync.'
GIT = {'tier': int, 'mode': str, 'base': str, 'forge': str, 'keep': list, 'slots': int, 'large': bool}
WORK = {'tracker': str, 'tasks': str, 'decisions': str, 'incoming': str, 'check': str, 'check_path': list, 'env': dict}
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
# The parts of the platform that a record can turn on (SDD-PJ-03). A record with no list has each part on, and the
# control of the specification as its field `control` says. The registry carries each other part that is off.
PARTS = ('git', 'check', 'tree', 'control', 'loop', 'team')


def parts_off(record_file, data):
    parts = data.get('parts')
    if parts is None:
        return []
    if not isinstance(parts, list) or any(p not in PARTS for p in parts):
        raise Refused(f'{record_file}: parts is a list of: {", ".join(PARTS)}')
    return [p for p in PARTS if p not in parts and p != 'control']


class Refused(Exception):
    pass


def projects_dir():
    return Path(os.environ.get('DEV_PLATFORM_PROJECTS') or Path.home() / '.config/dev-platform/projects')


def env_dir():
    return Path(os.environ.get('DEV_PLATFORM_ENV_DIR') or Path.home() / '.config/dev-platform/env.d')


def checkout(record_file, repo):
    return str((Path(record_file).parent / Path(repo.get('path', '')).expanduser()).resolve())


def load_records():
    """[(file, data)] for each record, by name. A file that is no JSON object is a problem of that file."""
    out = []
    folder = projects_dir()
    for file in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        try:
            data = json.loads(file.read_text())
        except ValueError as error:
            raise Refused(f'{file}: {error}') from None
        if not isinstance(data, dict) or not isinstance(data.get('repositories'), list):
            raise Refused(f'{file}: a record is an object with a list of repositories')
        out.append((file, data))
    return out


def registry_line(record_file, repo, off=()):
    """The repos.conf line of one repository of a record, or None when the record gives no Git settings for it."""
    git, work = repo.get('git'), repo.get('work') or {}
    if not isinstance(git, dict) or not repo.get('remote'):
        return None
    where = f'{record_file}: repository {repo.get("name")}'
    for section, kinds in ((git, GIT), (work, WORK)):
        for key, value in section.items():
            if key not in kinds or not isinstance(value, kinds[key]) or (kinds[key] is int and isinstance(value, bool)):
                raise Refused(f'{where}: {"git" if section is git else "work"}.{key} is unknown or has the wrong type')
    for key in ('tier', 'mode'):
        if key not in git:
            raise Refused(f'{where}: git.{key} is necessary')
    fields = [repo['remote'], checkout(record_file, repo), git['mode']] + ([git['base']] if git.get('base') else [])
    pairs = {'tier': git['tier'], 'forge': git.get('forge'), 'tracker': work.get('tracker'), 'tasks': work.get('tasks'),
             'slots': git.get('slots'), 'large': None if 'large' not in git else int(git['large']),
             'keep': ','.join(git['keep']) if git.get('keep') else None,
             # One source for the layout: the registry field follows the record (the two were set apart before).
             'spec': 'domains' if repo.get('layout') == 'domains' else 'single',
             'decisions': work.get('decisions'), 'incoming': work.get('incoming'), 'off': ','.join(off) or None}
    if work.get('tracker') == 'side':   # a ghost project: the tasks are in the side folder that also holds its specification
        if not repo.get('spec_root'):
            raise Refused(f'{where}: work.tracker is side, so the repository needs spec_root, the side folder')
        pairs['side'] = str((Path(record_file).parent / Path(repo['spec_root']).expanduser()).resolve())
    line = ' '.join(fields + [f'{key}={value}' for key, value in pairs.items() if value is not None])
    try:
        tiers.parse_line(line)
    except ValueError as error:
        raise Refused(f'{where}: {error}: {line}') from None
    return line


def env_text(record_name, repo):
    """The check environment file of one repository, or None when the record states no check setting."""
    work = repo.get('work') or {}
    rows = []
    if work.get('check_path'):
        folders = ':'.join(str(Path(p).expanduser()) for p in work['check_path'])
        rows.append(f'export PATH={shlex.quote(folders)}:"$PATH"')
    for key, value in sorted((work.get('env') or {}).items()):
        if not NAME.fullmatch(key) or not isinstance(value, str):
            raise Refused(f'record {record_name}: work.env.{key} is no variable name with a text value')
        rows.append(f'export {key}={shlex.quote(str(Path(value).expanduser()) if value.startswith("~") else value)}')
    if work.get('check'):
        rows.append(f'export DEV_PLATFORM_CHECK={shlex.quote(work["check"])}')
    if not rows:
        return None
    return '\n'.join([HEAD.replace('the project records', f'the project record {record_name}')] + rows) + '\n'


def generated():
    """(the text of the registry, {name of an environment file: text}, the checkouts that the records hold)."""
    lines, envs, seen = [], {}, {}
    for file, data in load_records():
        for repo in data['repositories']:
            if not isinstance(repo, dict):
                raise Refused(f'{file}: a repository is an object')
            line = registry_line(file, repo, parts_off(file, data))
            if line is None:
                continue
            folder = checkout(file, repo)
            if folder in seen:
                raise Refused(f'{folder} is in two records: {seen[folder]} and {file.name}')
            seen[folder] = file.name
            lines.append(line)
            text = env_text(data.get('name', file.stem), repo)
            if text:
                envs[Path(folder).name + '.sh'] = text
    return '\n'.join([HEAD] + lines) + '\n', envs, seen


def read_env(file):
    """A check environment file that a person wrote -> (check_path, env), or None when a line is not `export NAME=value`."""
    path, env = [], {}
    for row in file.read_text().splitlines():
        row = row.strip()
        if not row or row.startswith('#'):
            continue
        found = re.fullmatch(r'export ([A-Za-z_][A-Za-z0-9_]*)=(.*)', row)
        if not found:
            return None
        try:
            parts = shlex.split(found.group(2))
        except ValueError:
            return None
        if len(parts) != 1 or '`' in parts[0] or '$(' in parts[0]:
            return None
        key, value = found.group(1), parts[0].replace('$HOME', '~').replace('${HOME}', '~')
        if key == 'PATH':
            folders = value.split(':')
            if folders[-1] not in ('$PATH', '${PATH}') or any('$' in f for f in folders[:-1]):
                return None
            path += folders[:-1]
        elif '$' in value or key == 'DEV_PLATFORM_CHECK':
            return None
        else:
            env[key] = value
    return path, env


def short(path):
    home = str(Path.home())
    return '~' + path[len(home):] if path == home or path.startswith(home + os.sep) else path


def imported():
    """{record file: data} with a record for each line of the registry. A record that exists keeps each field that it has."""
    records = {file: data for file, data in load_records()}
    by_folder = {checkout(file, repo): (file, repo) for file, data in records.items() for repo in data['repositories']}
    names = {file.stem for file in records}
    notes = []
    for entry in tiers.read_conf():
        full = tiers.complete(entry)
        folder = str(Path(entry['path']).resolve())
        if folder in by_folder:
            file, repo = by_folder[folder]
        else:
            name = entry['repo'].rpartition('/')[2].lower()
            if name in names:
                name = entry['repo'].replace('/', '-').lower()
            names.add(name)
            file = projects_dir() / f'{name}.json'
            layout = 'domains' if full['spec'] == 'domains' else ('single' if Path(folder, 'docs/spec/SDD.md').is_file() else 'none')
            repo = {'name': name, 'path': short(folder), 'layout': layout}
            records[file] = {'schema': SCHEMA, 'name': name, 'top': None, 'repositories': [repo]}
            by_folder[folder] = (file, repo)
            if not Path(folder).is_dir():
                notes.append(f'{entry["repo"]}: the folder {folder} does not exist')
        if repo.get('layout') == 'domains' and full['spec'] != 'domains' or repo.get('layout') != 'domains' and full['spec'] == 'domains':
            notes.append(f'{entry["repo"]}: the registry says spec={full["spec"]} and the record says layout {repo.get("layout")}; the record wins')
        repo.setdefault('remote', entry['repo'])
        git = repo.setdefault('git', {})
        for key, value in (('tier', int(full['tier'])), ('mode', full['mode']), ('base', full['base']), ('forge', full['forge']),
                           ('keep', [k for k in full['keep'].split(',') if k]), ('slots', int(full['slots'])),
                           ('large', full['large'] == '1')):
            if value not in ('', []):
                git.setdefault(key, value)
        work = repo.setdefault('work', {})
        for key in ('tracker', 'tasks', 'decisions', 'incoming'):
            work.setdefault(key, full[key])
        env_file = env_dir() / (Path(folder).name + '.sh')
        if env_file.is_file() and HEAD.split(' from ')[0] not in env_file.read_text():
            read = read_env(env_file)
            if read is None:
                notes.append(f'{env_file}: a line is not `export NAME=value`; this file is not in the record, and sync will not write it')
            else:
                if read[0]:
                    work.setdefault('check_path', read[0])
                if read[1]:
                    work.setdefault('env', read[1])
    return records, notes


def differences(registry, envs):
    """[(file, the text of today, the new text)] for each file that sync changes."""
    out = []
    conf = tiers.conf_path()
    now = conf.read_text() if conf.is_file() else ''
    if now != registry:
        out.append((conf, now, registry))
    for name, text in sorted(envs.items()):
        file = env_dir() / name
        now = file.read_text() if file.is_file() else ''
        if now != text:
            out.append((file, now, text))
    return out


def sync(args):
    registry, envs, seen = generated()
    for entry in tiers.read_conf():
        if str(Path(entry['path']).resolve()) not in seen:
            raise Refused(f'the registry line of {entry["repo"]} has no record with Git settings; run dev-project import --write first')
    changed = differences(registry, envs)
    for file, now, new in changed:
        if args.write:
            file.parent.mkdir(parents=True, exist_ok=True)
            if now and not now.startswith(HEAD.split(' from ')[0]):   # a file that a person wrote: keep its notes one time
                kept = file.with_name(file.name + '.by-hand')
                if not kept.exists():
                    kept.write_text(now)
                    print(f'kept: {kept}')
            file.write_text(new)
            print(f'written: {file}')
        else:
            sys.stdout.writelines(difflib.unified_diff(now.splitlines(True), new.splitlines(True), str(file), 'from the records', n=0))
    if not changed:
        print('The registry and the check environment files are equal to the records.')
    elif not args.write:
        print(f'{len(changed)} files differ from the records. Write them with: dev-project sync --write')
    return 1 if changed and args.check else 0


def do_import(args):
    records, notes = imported()
    before = {file: (json.loads(file.read_text()) if file.is_file() else None) for file in records}
    changed = [file for file, data in records.items() if data != before[file]]
    for file in changed:
        if args.write:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(json.dumps(records[file], indent=2) + '\n')
        print(f'{"written" if args.write else "to write"}: {file}  ({"new" if before[file] is None else "Git and work settings added"})')
    for note in notes:
        print(f'note: {note}')
    if not changed:
        print('Each line of the registry has a record with its settings.')
    elif not args.write:
        print(f'{len(changed)} records to write. Write them with: dev-project import --write')
    return 0


def show(args):
    target = args.target
    wanted = str(Path(target).expanduser().resolve())
    common = tiers.identity(wanted)
    for file, data in load_records():
        for repo in data['repositories']:
            folder = checkout(file, repo)
            if data.get('name') == target or folder == wanted or (common and tiers.identity(folder) == common):
                print(f'record: {file}')
                print(json.dumps(repo, indent=2))
                print(f'parts that are on: {", ".join(data["parts"]) if "parts" in data else "each part; the control as the field control says"}')
                print(f'registry line: {registry_line(file, repo, parts_off(file, data)) or "none: the record has no Git settings"}')
                if data.get('name') != target:
                    return 0
    if not any(data.get('name') == target for _, data in load_records()):
        print(f'no record holds {target}', file=sys.stderr)
        return 1
    return 0


# ---------- connect a folder (SDD-PJ-05) and tell a session its rules (SDD-PJ-07) ----------

LAYOUTS = ('single', 'domains', 'sections', 'none')
PROJECT = re.compile(r'[A-Za-z0-9_][A-Za-z0-9._-]*')
# The landing rule of each tier (docs/source-control.md) and the rule of each part that is on (SDD-PJ-04).
LANDING = {
    0: 'no Git: no refs and no landing',
    1: 'solo trunk: work on the base branch and fast-forward it; push is allowed',
    2: 'personal shared: one goal branch; the owner lands it with dev-loop land',
    3: 'protected company: one goal branch; one push, then one draft pull request; the owner merges',
    4: 'fork: one local/* patch branch; never push upstream',
}
RULES = {
    'git': 'the Git hooks and the guard apply the rules of the tier',
    'check': 'a stop runs the full check (hooks/check-once.sh) on a changed tree',
    'tree': 'dev-spec compiles the specification tree',
    'control': 'change the specification only with the dev-spec write commands; the guard refuses an edit',
    'loop': 'the loop starts, dispatches, folds and lands the work of a goal',
    'team': 'the seats of a team can start in the project',
}


def git_out(folder, *args):
    """The output of a Git command that only reads, or '' when it fails."""
    done = subprocess.run(['git', '-C', str(folder), *args], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ''


def remote_of(url, folder):
    """(owner/name, forge, mode) from the URL of origin. A folder with no origin gets local/<folder>."""
    found = re.search(r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(\.git)?/?$', url or '')
    name = f'{found.group(1)}/{found.group(2)}' if found else f'local/{Path(folder).name}'
    if not url:
        return name, 'none', 'local'
    return (name, 'github', 'owner') if 'github.com' in url else (name, 'bare', 'local')


def check_of(folder):
    """The check command that hooks/check-once.sh finds in a repository, in the same order; '' when there is none."""
    root = Path(folder)
    if (root / 'bin/check').is_file() and os.access(root / 'bin/check', os.X_OK):
        return 'bin/check'
    try:
        if isinstance(json.loads((root / 'package.json').read_text()).get('scripts', {}).get('check'), str):
            return 'bun run check'
    except (OSError, ValueError, AttributeError):
        pass
    if (root / 'scripts/check').is_file() and os.access(root / 'scripts/check', os.X_OK):
        return 'scripts/check'
    return ''


def spec_of(folder):
    """(layout, sdd, tdd) that the files of a folder show: the default paths of a layout, else one SDD.md and one
    TDD.md that Git tracks. sdd and tdd are '' where the layout gives them."""
    root = Path(folder)
    if (root / 'docs/spec/index.json').is_file():
        return 'domains', '', ''
    if (root / 'docs/spec/SDD.md').is_file():
        return 'single', '', ''
    if (root / 'docs/spec/sdd').is_dir() and (root / 'docs/spec/tdd').is_dir():
        return 'sections', 'docs/spec/sdd', 'docs/spec/tdd'
    files = git_out(root, 'ls-files').splitlines() if root.is_dir() else []
    sdd = [f for f in files if Path(f).name.upper() == 'SDD.MD']
    tdd = [f for f in files if Path(f).name.upper() == 'TDD.MD']
    if len(sdd) == 1 and len(tdd) == 1:
        return 'single', sdd[0], tdd[0]
    return 'none', '', ''


def side_of(file, repo):
    return str((Path(file).parent / Path(repo['spec_root']).expanduser()).resolve()) if repo.get('spec_root') else ''


def record_at(folder):
    """(record file, data, repository) of the record that holds a folder: the checkout, a folder in it, a worktree of
    it, or the side folder. None when no record holds it."""
    folder = Path(folder).expanduser().resolve()
    places = []
    for file, data in load_records():
        for repo in data['repositories']:
            if isinstance(repo, dict):
                places += [(Path(place), (file, data, repo)) for place in (checkout(file, repo), side_of(file, repo)) if place]
    for place, held in places:
        if folder == place or place in folder.parents:
            return held
    common = tiers.identity(folder)   # a worktree outside the checkout: the same Git repository
    for place, held in places if common else []:
        if tiers.identity(place) == common:
            return held
    return None


def proposal(args):
    """(checkout, {key: value}) that connect proposes for a folder. It runs only Git commands that read."""
    here = Path(args.path).expanduser().resolve()
    common = tiers.identity(here)
    if not common:
        raise Refused(f'{here} is no Git checkout')
    folder = Path(common).parent if Path(common).name == '.git' else Path(git_out(here, 'rev-parse', '--show-toplevel') or here)
    held = record_at(folder)
    if held:
        raise Refused(f'the record {held[0]} already holds {folder}; change that record, or see it with: dev-project show {folder}')
    name = args.name or folder.name.lower()
    if not PROJECT.fullmatch(name):
        raise Refused(f'{name} is no project name; give --name with letters, digits, ".", "_" and "-"')
    if (projects_dir() / f'{name}.json').exists():
        raise Refused(f'the record {name}.json exists for a different folder; give --name')
    remote, forge, mode = remote_of(git_out(folder, 'remote', 'get-url', 'origin'), folder)
    # The rule of tiers.py for a folder that no line names (tier 3); a fork has upstream.
    tier = 4 if git_out(folder, 'remote', 'get-url', 'upstream') else int(tiers.resolve(str(folder))['tier'])
    head = git_out(folder, 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD')
    base = head.partition('/')[2] if head else (git_out(folder, 'symbolic-ref', '--short', 'HEAD') or 'main')
    values = {'name': name, 'remote': remote, 'tier': tier, 'mode': mode, 'base': base, 'forge': forge,
              'tracker': 'github' if forge == 'github' else 'files', 'decisions': 'none', 'check': check_of(folder),
              # A repository with JSON task files (the template of new-repo copies the schema) keeps that format.
              'tasks': 'json' if list((folder / 'docs/tasks').glob('*.json')) else 'md'}
    if args.ghost:   # a ghost project: the specification and the tasks are in the side folder (SDD-PJ-10)
        side = Path(args.side or Path.home() / 'dev/rigs' / name).expanduser().resolve()
        layout, sdd, tdd = spec_of(side)
        values.update(tracker='side', decisions='frozen', side=str(side), layout='single' if layout == 'none' else layout)
    else:
        layout, sdd, tdd = spec_of(folder)
        values['layout'] = layout
    values.update(sdd=sdd, tdd=tdd)
    for key in ('tier', 'base', 'check', 'layout'):
        if getattr(args, key) is not None:
            values[key] = getattr(args, key)
    return folder, values


def record_of(folder, values):
    """The record of one repository from the values that the owner confirmed. A wrong value stops it."""
    if str(values['tier']) not in ('0', '1', '2', '3', '4'):
        raise Refused(f'tier is {values["tier"]}; use 0, 1, 2, 3 or 4')
    if values['layout'] not in LAYOUTS:
        raise Refused(f'layout is {values["layout"]}; use one of {", ".join(LAYOUTS)}')
    if values['layout'] == 'sections' and not (values['sdd'] and values['tdd']):
        raise Refused('the sections layout needs sdd and tdd: the folders of the SDD files and of the TDD files')
    if not PROJECT.fullmatch(values['name']) or (projects_dir() / f'{values["name"]}.json').exists():
        raise Refused(f'{values["name"]} is no free project name')
    repo = {'name': values['name'], 'path': short(str(folder)), 'layout': values['layout']}
    for key in ('sdd', 'tdd'):
        if values[key]:
            repo[key] = values[key]
    if values.get('side'):
        repo['spec_root'] = short(values['side'])
    repo['remote'] = values['remote']
    repo['git'] = {'tier': int(values['tier']), 'mode': values['mode'], 'base': values['base'], 'forge': values['forge']}
    repo['work'] = {'tracker': values['tracker'], 'tasks': values.get('tasks') or 'md', 'decisions': values['decisions'], 'incoming': 'state'}
    if values['check']:
        repo['work']['check'] = values['check']
    file = projects_dir() / f'{values["name"]}.json'
    registry_line(file, repo)   # the parser of tiers.py examines each Git and work value
    return file, {'schema': SCHEMA, 'name': values['name'], 'top': None, 'repositories': [repo]}


def connect(args):
    folder, values = proposal(args)
    print(f'Proposed record for {folder}. The repository gets no file.')
    for key, value in values.items():
        print(f'  {key}: {value if value != "" else "(none)"}')
    if not args.yes:
        if not sys.stdin.isatty():
            print('Nothing written. Run connect in a terminal to confirm each value, or give --yes.')
            return 0
        print('Confirm each value: push Enter to keep it, type a new value, or type - for none.')
        for key in values:
            answer = input(f'  {key} [{values[key]}]: ').strip()
            values[key] = '' if answer == '-' else (answer or values[key])
        if input('Write the record? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('Nothing written.')
            return 0
    file, data = record_of(folder, values)
    if values.get('side'):   # the side folder is the top folder of its own Git repository, outside the checkout
        side = Path(values['side'])
        if side == folder or folder in side.parents:
            raise Refused(f'the side folder {side} is in the checkout; it must be outside the repository')
        if not side.exists():
            side.mkdir(parents=True)
            subprocess.run(['git', 'init', '-q', str(side)], check=True)
            print(f'made: {side} (a new Git repository for the specification and the tasks)')
        elif os.path.realpath(git_out(side, 'rev-parse', '--show-toplevel') or '/') != str(side):
            raise Refused(f'the side folder {side} must be the top folder of its own Git repository')
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, indent=2) + '\n')
    print(f'written: {file}')
    print('Next: write the registry line and the check environment file with: dev-project sync --write')
    return 0


def brief_text(folder):
    """The text for an agent at the start of a session in a connected folder, or None. It comes from the record and
    from the rules of the platform; no instruction file of the repository holds it (SDD-PJ-07)."""
    held = record_at(folder)
    if not held:
        return None
    file, data, repo = held
    git, work = repo.get('git') or {}, repo.get('work') or {}
    listed = data.get('parts')
    on = [p for p in PARTS if (p in listed if isinstance(listed, list) else (p != 'control' or data.get('control') is True))]
    lines = [f'dev-platform: this folder belongs to the project {data.get("name", file.stem)} (record {short(str(file))}). '
             'The record holds its settings; the files of the repository do not. Change a setting with dev-project.']
    if isinstance(git.get('tier'), int) and git['tier'] in LANDING:
        lines.append(f'- Tier {git["tier"]}, {LANDING[git["tier"]]}. Base branch: {git.get("base") or "the default branch"}.')
    else:
        lines.append('- The record states no tier: the rules of tier 3 apply.')
    lines.append('- Parts that are on: ' + ('; '.join(f'{p} ({RULES[p]})' for p in on) if on else 'none') + '.')
    off = [p for p in PARTS if p not in on]
    if off:
        lines.append(f'- Parts that are off: {", ".join(off)}. The platform does not act through them.')
    side = side_of(file, repo)
    place = side or checkout(file, repo)
    layout = repo.get('layout', 'none')
    if layout == 'none':
        lines.append('- Specification: none.')
    else:
        paths = ', '.join(filter(None, (repo.get('sdd'), repo.get('tdd')))) or 'the default paths'
        lines.append(f'- Specification: layout {layout} in {short(place)} ({paths}). Read and change it with dev-spec.'
                     + (' It is in the side folder: put no file of the specification into the repository.' if side else ''))
    tasks = {'side': f'task files in {short(side)}/docs/tasks', 'github': f'GitHub issues of {repo.get("remote")}',
             'files': 'task files in docs/tasks of the repository'}.get(work.get('tracker'), 'none stated')
    lines.append(f'- Tasks: {tasks}.' + (' Decisions are frozen: add no decision record and change no specification '
                                        'by hand.' if work.get('decisions') == 'frozen' else ''))
    command = work.get('check') or check_of(checkout(file, repo))
    lines.append(f'- Check: {command}, run once through hooks/check-once.sh.' if command else '- Check: none.')
    return '\n'.join(lines)


def brief(args):
    if args.hook:   # the session start hook: the folder is in the hook input; a fault never stops the session
        try:
            payload = json.loads(sys.stdin.read() or '{}')
            text = brief_text(payload.get('cwd') or os.getcwd())
        except (Refused, ValueError, OSError, AttributeError):
            return 0
        if text:
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': text}}))
        return 0
    text = brief_text(args.path)
    if not text:
        print(f'no record holds {Path(args.path).resolve()}; connect it with: dev-project connect {args.path}', file=sys.stderr)
        return 1
    print(text)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='dev-project', description='The project record is the source of the settings of a project.')
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('show', help='the record of a folder or a project').add_argument('target')
    p = sub.add_parser('connect', help='propose a record for a folder; write it after the owner confirms each value')
    p.add_argument('path')
    p.add_argument('--name', help='the name of the project; the default is the name of the folder')
    p.add_argument('--ghost', action='store_true', help='keep the specification and the tasks in a side folder')
    p.add_argument('--side', help='with --ghost: the side folder; the default is ~/dev/rigs/<name>')
    p.add_argument('--tier', type=int, choices=range(5))
    p.add_argument('--base')
    p.add_argument('--check', help='the check command; give "" for none')
    p.add_argument('--layout', choices=LAYOUTS)
    p.add_argument('--yes', action='store_true', help='write the proposal with no questions')
    p = sub.add_parser('brief', help='the text for an agent at the start of a session in a connected folder')
    p.add_argument('path', nargs='?', default='.')
    p.add_argument('--hook', action='store_true', help='read the folder from the hook input and print the hook output')
    p = sub.add_parser('import', help='make or complete a record for each line of the registry')
    p.add_argument('--write', action='store_true')
    p = sub.add_parser('sync', help='make the registry and the check environment files from the records')
    p.add_argument('--write', action='store_true')
    p.add_argument('--check', action='store_true', help='exit with 1 when a file differs from the records')
    args = ap.parse_args(argv)
    try:
        return {'show': show, 'import': do_import, 'sync': sync, 'connect': connect, 'brief': brief}[args.command](args)
    except Refused as error:
        print(f'dev-project: refused: {error}', file=sys.stderr)
        return 1
    except ValueError as error:   # a malformed line of the registry
        print(f'dev-project: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
