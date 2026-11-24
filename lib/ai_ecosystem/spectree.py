"""dev-spec: compile a project's specification tree (docs/spec/SDD.md, area ST).

    dev-spec compile <project> | --config FILE     write the page and the JSON tree
    dev-spec check   <project> | --config FILE     exit 1 when the tree has a fault
    dev-spec test    <project> | --config FILE     run each repository's tests and keep the results

The levels: an optional top document, the SDD, the TDD, and the code and test paths that the TDD
items name. The compiler reads; it writes only the page, the JSON tree, its state folder and its
own worktree. It rewrites no requirement and writes no status into a document.

The start of this module was the tree script of one company specification (2026-11-17).
"""
import argparse
import collections
import fcntl
import fnmatch
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

SCHEMA = 'dev-platform.spec-tree@1'
# A config that a repository owns names no platform: it can use the neutral name of the schema (SDD-ST-18).
SCHEMAS = (SCHEMA, 'spec-tree@1')
LAYOUTS = ('single', 'domains', 'sections', 'none')
WORKTREE = '.claude/worktrees/spec-tree'

# The status of a TDD item, worst first. An SDD item takes the worst status of its TDD items.
ORDER = ['failing', 'no TDD', 'no code', 'no test', 'test not run', 'proved']
MEANING = {
    'failing': 'a named test fails',
    'no TDD': 'no TDD item names the SDD item',
    'no code': 'the TDD item names no path that exists',
    'no test': 'code exists; no test path with a test case is named',
    'test not run': 'a test is named; no valid result is kept for it',
    'proved': 'each named test has a result and passes',
}
TEST_PATH = re.compile(r'(\.test\.|\.check\.|(^|/)tests?/|_test\.|(^|/)test_)')
# The name of a file that holds test cases. A file in a test folder with no such name can be a support file.
TEST_NAME = re.compile(r'(\.test\.|\.check\.|\.spec\.|_test\.|^test_)')
# A code name inside backticks: a file, a path, a call, a snake_case or camelCase identifier.
CODE_NAME = re.compile(r'`[^`]*(?:\.(?:ts|tsx|sql|json|py|sh|md)\b|/|\(\)|_[a-z]|[a-z][A-Z])[^`]*`')
MUST = re.compile(r'\bmust\b', re.I)
SDD_LINE = re.compile(r'\*\*([A-Z]{2}-\d+[a-z]?)\.\*\* (.+)$')
TDD_HEAD = re.compile(r'#{4,5} (TDD-[\d.]+)\s*(.*)$')
# A table row with an identifier, for example an acceptance row '| AC-01 | ...': known, shown as text, no level of the tree.
ROW = re.compile(r'\|\s*([A-Z]{2}-\d+[a-z]?)\s*\|\s*(.*)$')
GAP_KINDS = ('pending', 'deviation', 'unverified', 'gap')
# The form of an item in the specification standard (docs/spec/SDD.md, area SP).
PARTS = ('Actor', 'Behavior', 'Observable', 'On failure', 'Verified by', 'Limits')
RULES = collections.OrderedDict((
    ('SP-07', 'one sentence in one EARS pattern, with MUST or MUST NOT one time'),
    ('SP-08', '25 words or less in the requirement sentence'),
    ('SP-09', 'no MUST outside the requirement sentence'),
    ('SP-10', 'only the parts Actor, Behavior, Observable, On failure, Verified by, Limits; Verified by is necessary'),
    ('SP-11', 'no name of a part of the implementation'),
    ('SP-12', 'an identifier of area and number'),
    ('SP-13', 'no status in the trace comment'),
    ('SP-14', 'a gap cites its task or issue as #N'),
))
NOT_EARS = re.compile(r'(After|Before|Unless|Whenever|Once|Until|Upon|As soon as|In case|Provided)\b')
ID_FORM = re.compile(r'[A-Z]{2}-\d{2,}[a-z]?$')
SYS_COMMENT = re.compile(r'\s*<!--.*?\bsys:\s*([^|>]*?)\s*(?:\||-->)')

REPO_FIELDS = {
    'name': (str, None), 'path': (str, None), 'layout': (str, None),
    'title': (str, ''), 'source': (str, 'checkout'), 'sdd': (str, ''), 'tdd': (str, ''),
    'test': ((str, type(None)), None), 'prepare': ((str, type(None)), None),
    'code_endings': (list, ['.ts', '.tsx', '.js', '.mjs', '.py', '.sh', '.sql']),
    'not_counted': (list, ['docs/', '.claude/', 'node_modules/']),
    'flag_words': (list, []), 'result_prefixes': (list, []), 'interface_names': (list, []),
    # The Git and work settings of the repository (lib/ai_ecosystem/projectrecord.py). The compiler does not read them.
    'remote': (str, ''), 'git': (dict, {}), 'work': (dict, {}),
    # A ghost project: the SDD and the TDD are in a side folder outside the repository (the rig folder), and the
    # code paths and test paths of the TDD items are in the checkout (SDD-PJ-10).
    'spec_root': (str, ''),
}
TOP_FIELDS = {'schema': str, 'name': str, 'top': (str, dict, type(None)), 'repositories': list, 'note': str,
              'control': bool, 'page': str, 'parts': list, 'config': str}
PLATFORM_PARTS = ('git', 'check', 'tree', 'control', 'loop', 'team')
PAGE, DATA = 'tree.html', 'tree.data.json'


class ConfigError(Exception):
    def __init__(self, problems):
        super().__init__('\n'.join(problems))
        self.problems = problems


# ---------- small tools ----------

def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def git(root, *args):
    r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def state_root():
    return Path(os.environ.get('DEV_PLATFORM_STATE') or Path.home() / '.local/state/dev-platform') / 'spec'


def is_test(path):
    return bool(TEST_PATH.search(path))


def split_list(value):
    return [x.strip() for x in re.split(r',\s*', value or '') if x.strip() and x.strip() != 'none']


def lines_outside_fences(text):
    """Yield (number, line) for each line that is not inside a ``` block."""
    inside = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith('```'):
            inside = not inside
            continue
        if not inside:
            yield n, line


def trace_comment(line):
    """Parse '<!-- id: A | key: value | ... -->' into a dict, or None."""
    m = re.match(r'\s*<!--\s*(id:.*?)\s*-->\s*$', line)
    if not m:
        return None
    out = collections.OrderedDict()
    for part in m.group(1).split('|'):
        if ':' in part:
            k, v = part.split(':', 1)
            out[k.strip()] = v.strip()
    return out


def bare(item_id):
    """The id of an SDD item without its 'SDD-' prefix."""
    return item_id[4:] if item_id.startswith('SDD-') else item_id


def natural(name):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', name)]


# ---------- the config (SDD-ST-15) ----------

def arguments_config(folder, layout, sdd=None, tdd=None, spec_root=None):
    """The config of one repository from arguments only, for a folder that no project record holds (SDD-PJ-09)."""
    folder = Path(folder).expanduser().resolve()
    repo = {'name': folder.name, 'path': '.', 'layout': layout}
    for key, value in (('sdd', sdd), ('tdd', tdd), ('spec_root', spec_root)):
        if value:
            repo[key] = str(Path(value).expanduser().resolve()) if key == 'spec_root' else value
    return load_config(folder / '(arguments)', {'schema': SCHEMA, 'name': folder.name, 'top': None, 'repositories': [repo]})


def settings_arguments(parser):
    """The settings of a folder that no project record holds, as arguments of a read command (SDD-PJ-09)."""
    parser.add_argument('--layout', choices=LAYOUTS, help='the settings as arguments: the layout of the specification; '
                        'no record and no config file is read')
    parser.add_argument('--sdd', help='with --layout: the SDD file or folder, relative to the checkout or to --spec-root')
    parser.add_argument('--tdd', help='with --layout: the TDD file or folder')
    parser.add_argument('--spec-root', help='with --layout: a side folder that holds the specification')


def load_config(path, data=None):
    """Read and validate one project config. Raises ConfigError with one line for each problem.
    With data, PATH is only the label of the problems and its folder is the base of the relative paths."""
    path = Path(path).expanduser().resolve()
    if data is None:
        if not path.is_file():
            raise ConfigError([f'{path}: no such config file'])
        try:
            data = json.loads(read(path))
        except ValueError as error:
            raise ConfigError([f'{path}: not valid JSON: {error}'])
    problems = []
    if not isinstance(data, dict):
        raise ConfigError([f'{path}: the config must be one JSON object'])
    for key in data:
        if key not in TOP_FIELDS:
            problems.append(f'{path}: unknown field: {key}')
    for key in ('schema', 'name', 'repositories'):
        if key not in data:
            problems.append(f'{path}: missing field: {key}')
    for key, kinds in TOP_FIELDS.items():
        if key in data and not isinstance(data[key], kinds):
            problems.append(f'{path}: {key} has the wrong type')
    if data.get('schema') not in (None, *SCHEMAS):
        problems.append(f'{path}: schema is {data.get("schema")!r}, not {SCHEMA}')
    problems += native_config(path, data)
    base = path.parent
    parts = data.get('parts') if isinstance(data.get('parts'), list) else None
    for part in parts or []:
        if part not in PLATFORM_PARTS:
            problems.append(f'{path}: parts: unknown part: {part}; the parts are {", ".join(PLATFORM_PARTS)}')
    # A record with a list of parts states each part that is on (SDD-PJ-03). With no list, each part is on and the
    # field `control` turns the control of the specification on.
    conf = {'file': str(path), 'base': str(base), 'name': data.get('name', ''), 'top': None, 'parts': parts,
            'control': ('control' in parts) if parts is not None else data.get('control') is True, 'page': data.get('page'),
            'repositories': []}
    top = data.get('top')
    if isinstance(top, str):
        top = {'path': top}
    if isinstance(top, dict):
        for key in top:
            if key not in ('path', 'prefix', 'repository'):
                problems.append(f'{path}: top: unknown field: {key}')
        if not isinstance(top.get('path'), str):
            problems.append(f'{path}: top: missing field: path')
        else:
            conf['top'] = {'path': top['path'], 'prefix': top.get('prefix', 'TOP'), 'repository': top.get('repository')}
    names = set()
    for number, entry in enumerate(data.get('repositories') if isinstance(data.get('repositories'), list) else [], 1):
        where = f'{path}: repository {number}'
        if not isinstance(entry, dict):
            problems.append(f'{where}: must be an object')
            continue
        repo = {}
        for key in entry:
            if key not in REPO_FIELDS:
                problems.append(f'{where}: unknown field: {key}')
        for key, (kinds, default) in REPO_FIELDS.items():
            if key in entry:
                if not isinstance(entry[key], kinds):
                    problems.append(f'{where}: {key} has the wrong type')
                repo[key] = entry[key]
            elif default is None and key in ('name', 'path', 'layout'):
                problems.append(f'{where}: missing field: {key}')
            else:
                repo[key] = list(default) if isinstance(default, list) else dict(default) if isinstance(default, dict) else default
        if repo.get('layout') not in LAYOUTS + (None,):
            problems.append(f'{where}: layout is {repo.get("layout")!r}; use one of {", ".join(LAYOUTS)}')
        if isinstance(repo.get('name'), str):
            if repo['name'] in names:
                problems.append(f'{where}: the name {repo["name"]} is used two times')
            names.add(repo['name'])
        if isinstance(repo.get('path'), str):
            repo['checkout'] = str((base / Path(repo['path']).expanduser()).resolve())
            if not Path(repo['checkout']).is_dir():
                problems.append(f'{where}: no folder at {repo["checkout"]}')
        if repo.get('spec_root'):
            side = (base / Path(repo['spec_root']).expanduser()).resolve()
            repo['spec_root'] = str(side)
            if not side.is_dir():
                problems.append(f'{where}: spec_root: no folder at {side}')
            elif (top_of := git(side, 'rev-parse', '--show-toplevel')) and os.path.realpath(top_of) != str(side):
                problems.append(f'{where}: spec_root: {side} must be the top folder of its Git repository ({top_of})')
        layout = repo.get('layout')
        if layout == 'single':
            repo['sdd'] = repo.get('sdd') or 'docs/spec/SDD.md'
            repo['tdd'] = repo.get('tdd') or 'docs/spec/TDD.md'
        elif layout == 'domains':
            repo['sdd'] = repo.get('sdd') or 'docs/spec'
            repo['tdd'] = repo.get('tdd') or repo['sdd']
        elif layout == 'sections':
            if not repo.get('sdd') or not repo.get('tdd'):
                problems.append(f'{where}: the sections layout needs the fields sdd and tdd')
        conf['repositories'].append(repo)
    if conf['top'] and conf['top']['repository'] is not None and conf['top']['repository'] not in names:
        problems.append(f'{path}: top: repository names no repository of this config')
    if problems:
        raise ConfigError(problems)
    return conf


# The settings of the specification that a native project keeps in a config file of its own repository.
NATIVE_KEYS = ('layout', 'sdd', 'tdd', 'test', 'prepare', 'code_endings', 'not_counted', 'flag_words', 'interface_names', 'result_prefixes')


def native_config(path, data):
    """A record of a native project names a config file in its repository (the field `config`). That file is the one
    source of the specification settings: its values take the place of the values of the record. Returns the problems."""
    name = data.get('config')
    repos = data.get('repositories')
    if not isinstance(name, str):
        return []
    if not isinstance(repos, list) or not repos or not isinstance(repos[0], dict) or not isinstance(repos[0].get('path'), str):
        return [f'{path}: config needs a first repository with a path']
    checkout = (Path(path).parent / Path(repos[0]['path']).expanduser()).resolve()
    source = repos[0].get('source') or 'checkout'
    if source == 'checkout':
        file = checkout / name
        text = read(file) if file.is_file() else ''
    else:   # the same revision that the compiler reads: the config of the ref, not of the branch of the checkout
        text = git(checkout, 'show', f'{source}:{name}')
    if not text:
        return [f'{path}: config: {name} is not in the repository at {checkout} ({source})']
    try:
        own = json.loads(text)
    except ValueError as error:
        return [f'{path}: config: {name}: {error}']
    theirs = own.get('repositories') if isinstance(own, dict) and isinstance(own.get('repositories'), list) else []
    for entry in repos:
        match = next((r for r in theirs if isinstance(r, dict) and r.get('name') == entry.get('name')), None) \
            or (theirs[0] if len(theirs) == 1 and len(repos) == 1 and isinstance(theirs[0], dict) else None)
        if match is None:
            return [f'{path}: config: {name} holds no repository with the name {entry.get("name")}']
        for key in NATIVE_KEYS:
            if key in match:
                entry[key] = match[key]
    if isinstance(own.get('top'), (str, dict)):
        data['top'] = own['top']
    return []


def projects_dir():
    """The project records of the platform, outside each repository (SDD-PJ-01)."""
    return Path(os.environ.get('DEV_PLATFORM_PROJECTS') or Path.home() / '.config/dev-platform/projects')


def find_config(project):
    """The config of a named project: its record in the projects folder."""
    record = projects_dir() / f'{project}.json'
    if record.is_file():
        return record
    raise ConfigError([f'no project named {project}: the projects folder has no record {project}.json'])


# ---------- the source of a repository (SDD-ST-10) ----------

def source_root(repo, fetch=True):
    """The folder to compile. 'checkout' is the primary checkout as it is; a ref is the compiler's own worktree."""
    checkout = repo['checkout']
    if repo['source'] == 'checkout':
        return checkout, None
    ref = repo['source']
    tree = os.path.join(checkout, WORKTREE)
    note = None
    if fetch and '/' in ref:
        remote, branch = ref.split('/', 1)
        if remote in git(checkout, 'remote').split():
            r = subprocess.run(['git', '-C', checkout, 'fetch', '-q', remote, branch], capture_output=True, text=True)
            if r.returncode != 0:
                note = f'the fetch of {ref} failed; the last fetched revision is compiled'
    commit = git(checkout, 'rev-parse', '--verify', '-q', ref + '^{commit}')
    if not commit:
        raise ConfigError([f'{repo["name"]}: the source {ref} is no revision of {checkout}'])
    if not os.path.isdir(tree):
        r = subprocess.run(['git', '-C', checkout, 'worktree', 'add', '-q', '--detach', tree, commit], capture_output=True, text=True)
        if r.returncode != 0:
            raise ConfigError([f'{repo["name"]}: cannot make the worktree {tree}: {r.stderr.strip()}'])
    elif git(tree, 'rev-parse', 'HEAD') != commit:
        r = subprocess.run(['git', '-C', tree, 'checkout', '-q', '--detach', commit], capture_output=True, text=True)
        if r.returncode != 0:
            raise ConfigError([f'{repo["name"]}: cannot move the worktree {tree}: {r.stderr.strip()}'])
    return tree, note


# ---------- the top document (SDD-ST-04) ----------

def parse_top(path, label, prefix):
    text = read(path)
    sections, reqs, faults = [], [], []
    section, pending = None, None
    first = re.search(r'^## \d+\. ', text, re.M)
    front = (text[:first.start()] if first else text).splitlines()
    for n, line in lines_outside_fences(text):
        m = re.match(r'## (\d+)\. (.+)$', line)
        if m:
            section = {'number': m.group(1), 'title': m.group(2).strip(), 'reqs': []}
            sections.append(section)
            continue
        m = re.match(r'\*\*([A-Z]{2}-\d{2})\.\*\* (.+)$', line)
        if m:
            if section is None:
                faults.append(f'{label}:{n}: {m.group(1)} is outside a numbered section')
                continue
            pending = {'id': f'{prefix}-{m.group(1)}', 'text': m.group(2).strip(), 'line': n, 'sdd': None, 'outside': False,
                       'applies': [], 'domain': None, 'areas': [], 'notes': [], 'file': label, 'has_sdd': False}
            section['reqs'].append(pending)
            reqs.append(pending)
            continue
        if pending is not None:
            t = trace_comment(line)
            if t is not None:
                if t.get('id') != pending['id']:
                    faults.append(f'{label}:{n}: the trace comment names {t.get("id")}, the line above is {pending["id"]}')
                pending['outside'] = t.get('sdd', '').strip() == 'outside'
                pending['sdd'] = [] if pending['outside'] else split_list(t.get('sdd', ''))
                pending['applies'] = split_list(t.get('applies', ''))
                pending['domain'] = t.get('domain', '').strip() or None
                pending['areas'] = split_list(t.get('areas', ''))
                pending['has_sdd'] = 'sdd' in t
            elif line.startswith('- '):
                pending['notes'].append(line[2:].strip())
    seen = collections.Counter(r['id'] for r in reqs)
    faults += [f'{label}: {i} is used {c} times' for i, c in seen.items() if c > 1]
    faults += [f'{label}:{r["line"]}: {r["id"]} has no trace comment' for r in reqs if r['sdd'] is None]
    for r in reqs:
        r['sdd'] = r['sdd'] or []
    return sections, reqs, faults, front


# ---------- the specification of one repository (SDD-ST-02) ----------

def new_item(repo, side, item_id, title, file, line, group, meta):
    return {'repo': repo, 'side': side, 'id': item_id, 'title': title, 'file': file, 'line': line, 'end': line,
            'group': group, 'meta': meta, 'tdd': [], 'implements': [], 'rows': [], 'paths': [], 'status': None,
            'declared': meta.get('status') or ('gap:' + meta['gap'] if meta.get('gap') else None),
            'tasks': split_list(meta.get('tasks', '')), 'sentence': None, 'sys': split_list(meta.get('sys', ''))}


def keep(store, item, faults):
    if item['id'] in store:
        first = store[item['id']]
        faults.append(f'{item["file"]}:{item["line"]}: {item["id"]} occurs two times; the first is at {first["file"]}:{first["line"]}')
        return False
    store[item['id']] = item
    return True


def set_spans(rows, total, things, stop):
    """Give each item and each section its last line: the line before the next item, section or heading."""
    marks = sorted({t['line'] for t in things} | {n for n, line in rows if stop.match(line)})
    for thing in things:
        later = [m for m in marks if m > thing['line']]
        thing['end'] = later[0] - 1 if later else total


def open_file(ctx, root, rel):
    lines = read(os.path.join(root, rel)).splitlines()
    ctx['files'][rel] = lines
    return list(lines_outside_fences('\n'.join(lines)))


DOMAIN_STOP = re.compile(r'#{1,3} ')
SDD_STOP = re.compile(r'#{1,3} ')
TDD_STOP = re.compile(r'#{1,5} ')
SINGLE_HEAD = [re.compile(r'## ([A-Za-z0-9]+)\. (.+)$')]
SECTION_HEAD = [re.compile(r'### ([\d.]+\d) (.+)$'), re.compile(r'## (\d+)\. (.+)$')]


def parse_domains(name, root, conf, ctx):
    """One folder for each domain with sdd.md and tdd.md; an item is a '### <id> <title>' heading with metadata lines."""
    sdd, tdd, groups = {}, {}, []
    base = os.path.join(root, conf['sdd'])
    for domain in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        folder = os.path.join(base, domain)
        if not os.path.isdir(folder):
            continue
        found = False
        for side, file_name, store in (('SDD', 'sdd.md', sdd), ('TDD', 'tdd.md', tdd)):
            if not os.path.isfile(os.path.join(folder, file_name)):
                continue
            rel = os.path.relpath(os.path.join(folder, file_name), root)
            rows = open_file(ctx, root, rel)
            made = []
            for i, (n, line) in enumerate(rows):
                m = re.match(r'### (\S+)\s*(.*)$', line)
                if not m:
                    continue
                meta, codes, tests, body = collections.OrderedDict(), [], [], []
                for j, (_, nxt) in enumerate(rows[i + 1:]):
                    k = re.match(r'([a-z_]+):\s*(.*)$', nxt)
                    if not k:
                        for _, b in rows[i + 1 + j:]:
                            if b.startswith('### '):
                                break
                            body.append(b)
                        break
                    if k.group(1) == 'code':
                        codes += split_list(k.group(2))
                    elif k.group(1) == 'tests':
                        tests += split_list(k.group(2))
                    else:
                        meta[k.group(1)] = k.group(2).strip()
                key = 'tdd' if side == 'SDD' else 'implements'
                if key not in meta:
                    continue
                it = new_item(name, side, m.group(1), m.group(2).strip(), rel, n, 'domain/' + domain, meta)
                it['code_named'], it['tests_named'] = codes, tests
                it['body'] = m.group(2) + ' ' + ' '.join(body)
                it[key] = [bare(x) for x in split_list(meta[key])]
                if keep(store, it, ctx['faults']):
                    made.append(it)
                    found = True
            set_spans(rows, len(ctx['files'][rel]), made, DOMAIN_STOP)
            if not made and not any(line.startswith('#') for _, line in rows):
                ctx['faults'].append(f'{rel}: the file holds no item and no heading')
        if found:
            groups.append({'key': 'domain/' + domain, 'title': domain, 'file': None, 'line': 0, 'end': 0, 'sys': []})
    return sdd, tdd, groups, []


def parse_sdd_rows(name, rel, rows, total, groups, store, ctx, headings):
    """SDD items of one file: '**XX-nn.**' lines with a trace comment. headings: the patterns that start a section."""
    group, things, found = None, [], 0
    for i, (n, line) in enumerate(rows):
        row = ROW.match(line)
        if row:
            ctx['table'].setdefault(row.group(1), {'file': rel, 'line': n, 'text': row.group(2).strip(' |')})
        for pattern in headings:
            m = pattern.match(line)
            if m:
                group = 'section/' + m.group(1)
                title = f'{m.group(1)}. {m.group(2).strip()}' if pattern.pattern.startswith('## ') else f'{m.group(1)} {m.group(2).strip()}'
                if not any(g['key'] == group for g in groups):
                    owner = next((o.group(1) for _, l in rows[i + 1:i + 4] if (o := SYS_COMMENT.match(l))), '')
                    groups.append({'key': group, 'title': title, 'file': rel, 'line': n, 'end': n, 'sys': split_list(owner)})
                    things.append(groups[-1])
                found += 1
                break
        m = SDD_LINE.match(line)
        if not m or group is None:
            continue
        meta = next((t for _, l in rows[i + 1:i + 4] if (t := trace_comment(l))), None)
        if meta is not None and meta.get('id', '').startswith('SYS-'):
            # A system requirement in the first chapter of the SDD: the flattened form of a project with one repository.
            if meta['id'] != 'SYS-' + m.group(1):
                ctx['faults'].append(f'{rel}:{n}: the trace comment names {meta["id"]}, the line above is {m.group(1)}')
            ctx['sys'].append({'id': meta['id'], 'text': m.group(2).strip(), 'line': n, 'file': rel, 'sdd': [], 'outside': False,
                               'applies': [], 'domain': None, 'areas': [], 'notes': [], 'has_sdd': False, 'chapter': (name, group)})
            found += 1
            continue
        it = new_item(name, 'SDD', m.group(1), m.group(2).strip(), rel, n, group, meta or collections.OrderedDict())
        if meta is None:
            ctx['faults'].append(f'{rel}:{n}: {it["id"]} has no trace comment')
        elif bare(meta.get('id', '')) != it['id']:
            ctx['faults'].append(f'{rel}:{n}: the trace comment names {meta.get("id")}, the line above is {it["id"]}')
        body = []
        for _, b in rows[i + 1:]:
            if SDD_LINE.match(b) or b.startswith(('## ', '### ')):
                break
            body.append(b)
        it['sentence'] = m.group(2).strip()
        it['body'] = m.group(2) + ' ' + ' '.join(body)
        it['tdd'] = split_list(it['meta'].get('tdd', ''))
        if keep(store, it, ctx['faults']):
            things.append(it)
            found += 1
    set_spans([(n, line) for n, line in rows if not SDD_LINE.match(line)] + [(t['line'], '# item') for t in things if t.get('side')],
              total, things, SDD_STOP)
    return found


def parse_tdd_rows(name, rel, rows, total, groups, store, ctx, headings):
    """TDD items of one file, and the sections of the TDD with the text that is outside an item."""
    things, found = [], 0
    for i, (n, line) in enumerate(rows):
        row = ROW.match(line)
        if row:
            ctx['table'].setdefault(row.group(1), {'file': rel, 'line': n, 'text': row.group(2).strip(' |')})
        m = TDD_HEAD.match(line)
        if not m and re.match(r'#{4,5} \S', line):
            # A heading of an item with no identifier in it: the trace comment below still names a TDD item (one project had five).
            below = next((t for _, l in rows[i + 1:i + 4] if (t := trace_comment(l))), None)
            if below is not None and TDD_HEAD.match('#### ' + below.get('id', '')):
                ctx['faults'].append(f'{rel}:{n}: the heading of {below["id"]} does not hold its identifier')
                m = TDD_HEAD.match(f'#### {below["id"]} ' + line.lstrip('#').strip())
        if not m:
            for pattern in headings:
                h = pattern.match(line)
                if h:
                    title = f'{h.group(1)}. {h.group(2).strip()}' if pattern.pattern.startswith('## ') else f'{h.group(1)} {h.group(2).strip()}'
                    groups.append({'key': 'section/' + h.group(1), 'title': title, 'file': rel, 'line': n, 'end': n})
                    things.append(groups[-1])
                    break
            if line.startswith('#'):
                found += 1
            continue
        meta = next((t for _, l in rows[i + 1:i + 4] if (t := trace_comment(l))), None)
        if meta is None:
            continue
        it = new_item(name, 'TDD', m.group(1), m.group(2).strip(), rel, n, None, meta)
        if meta.get('id') != it['id']:
            ctx['faults'].append(f'{rel}:{n}: the trace comment names {meta.get("id")}, the heading is {it["id"]}')
        it['implements'] = [bare(x) for x in split_list(meta.get('implements', ''))]
        it['code_named'], it['tests_named'] = split_list(meta.get('code', '')), split_list(meta.get('tests', ''))
        if keep(store, it, ctx['faults']):
            things.append(it)
            found += 1
    set_spans(rows, total, things, TDD_STOP)
    return found


def parse_single(name, root, conf, ctx):
    """One SDD file and one TDD file; '**XX-nn.**' lines and '#### TDD-x.y.z' headings with trace comments."""
    sdd, tdd, groups, tdd_groups = {}, {}, [], []
    for rel, side in ((conf['sdd'], 'SDD'), (conf['tdd'], 'TDD')):
        if not os.path.isfile(os.path.join(root, rel)):
            continue
        rows = open_file(ctx, root, rel)
        total = len(ctx['files'][rel])
        if side == 'SDD':
            parse_sdd_rows(name, rel, rows, total, groups, sdd, ctx, SINGLE_HEAD)
        else:
            parse_tdd_rows(name, rel, rows, total, tdd_groups, tdd, ctx, SINGLE_HEAD)
    return sdd, tdd, groups, tdd_groups


def parse_sections(name, root, conf, ctx):
    """One file for each section: the SDD files in one folder and the TDD files in a second folder."""
    sdd, tdd, groups, tdd_groups = {}, {}, [], []
    for folder, side in ((conf['sdd'], 'SDD'), (conf['tdd'], 'TDD')):
        base = os.path.join(root, folder)
        for file_name in sorted(os.listdir(base), key=natural) if os.path.isdir(base) else []:
            if not file_name.endswith('.md'):
                continue
            rel = os.path.join(folder, file_name)
            rows = open_file(ctx, root, rel)
            total = len(ctx['files'][rel])
            if side == 'SDD':
                found = parse_sdd_rows(name, rel, rows, total, groups, sdd, ctx, SECTION_HEAD)
            else:
                found = parse_tdd_rows(name, rel, rows, total, tdd_groups, tdd, ctx, SECTION_HEAD)
            if not found:
                ctx['faults'].append(f'{rel}: the file holds no item and no section heading')
    return sdd, tdd, groups, tdd_groups


# ---------- the kept test results (SDD-ST-08, SDD-ST-09) ----------

def result_files(project, name):
    folder = state_root() / project
    return folder / f'{name}.xml', folder / f'{name}.rev', folder / f'{name}.lock'


def load_results(project, repo, root):
    """JUnit report -> {repository path: [passed, failed, skipped]}, and the revision the tests ran on."""
    xml, rev_file, _ = result_files(project, repo['name'])
    if not xml.is_file():
        return None, None
    results = collections.defaultdict(lambda: [0, 0, 0])

    def norm(f):
        if os.path.isabs(f):
            f = os.path.relpath(f, root)
        if not os.path.exists(os.path.join(root, f)):
            for prefix in repo['result_prefixes']:
                if os.path.exists(os.path.join(root, prefix, f)):
                    return os.path.join(prefix, f)
        return f

    def walk(node, file):
        file = node.get('file') or file
        if node.tag == 'testsuite' and not file and '/' in (node.get('name') or ''):
            file = node.get('name')
        if node.tag == 'testcase':
            f = node.get('file') or file
            if f:
                row = results[norm(f)]
                kinds = {c.tag for c in node}
                row[1 if kinds & {'failure', 'error'} else 2 if 'skipped' in kinds else 0] += 1
            return
        for child in node:
            walk(child, file)

    try:
        walk(ET.parse(xml).getroot(), None)
    except ET.ParseError as error:
        print(f'{xml}: {error}', file=sys.stderr)
        return None, None
    rev = read(rev_file).split() if rev_file.is_file() else None
    return dict(results), rev


def results_valid(repo, root, head, rev):
    """A kept result counts for the compiled revision, or when only specification files changed since."""
    if not rev or not head:
        return False
    if rev[0] == head:
        return True
    if not git(root, 'rev-parse', '--verify', '-q', rev[0] + '^{commit}'):
        return False
    spec = sorted({repo['sdd'], repo['tdd']} - {''})
    r = subprocess.run(['git', '-C', str(root), 'diff', '--quiet', rev[0], head, '--', '.', *[f':(exclude){p}' for p in spec]],
                       capture_output=True, text=True)
    return r.returncode == 0


def keep_results(conf, junit):
    """dev-spec test --junit FILE: a pipeline ran the tests already. Keep its report as the result of the present revision."""
    repos = [r for r in conf['repositories'] if r['layout'] != 'none']
    if len(repos) != 1:
        raise ConfigError([f'--junit needs a config with one repository that has a specification; this one has {len(repos)}'])
    if not os.path.isfile(junit):
        raise ConfigError([f'--junit: {junit} is no file'])
    repo = repos[0]
    root, _ = source_root(repo)
    try:
        ET.parse(junit)
    except ET.ParseError as error:
        raise ConfigError([f'--junit: {junit}: {error}']) from None
    xml, rev_file, _ = result_files(conf['name'], repo['name'])
    xml.parent.mkdir(parents=True, exist_ok=True)
    xml.write_bytes(Path(junit).read_bytes())
    head = git(root, 'rev-parse', 'HEAD')
    rev_file.write_text(f'{head} {len(git(root, "status", "--porcelain").splitlines())}\n')
    print(f'{repo["name"]}: results kept for {head[:9]} (from {junit}; no test ran)')
    return 0


def not_proved(tree):
    """The SDD items that stop the proof gate: not proved, and with no gap that names its task (SDD-ST-17)."""
    rows = []
    for repo in tree['repos'].values():
        for item in repo['sdd'].values():
            if item['status'] != 'proved' and not item['meta'].get('gap'):
                rows.append(f'{item["file"]}:{item["line"]}: {item["id"]} is not proved: {item["status"]} ({MEANING[item["status"]]})')
    return rows


def run_tests(conf):
    """dev-spec test: run each repository's test command and keep the JUnit report with its revision."""
    status = 0
    for repo in conf['repositories']:
        if not repo.get('test') or repo['layout'] == 'none':
            continue
        root, _ = source_root(repo)
        xml, rev_file, lock = result_files(conf['name'], repo['name'])
        xml.parent.mkdir(parents=True, exist_ok=True)
        with open(lock, 'w') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                print(f'{repo["name"]}: a test run is in progress; nothing started', file=sys.stderr)
                status = 3
                continue
            head = git(root, 'rev-parse', 'HEAD')
            dirty = len(git(root, 'status', '--porcelain').splitlines())
            if repo.get('prepare'):
                done = subprocess.run(repo['prepare'], shell=True, cwd=root)
                if done.returncode != 0:
                    print(f'{repo["name"]}: the prepare command failed ({done.returncode}); no test ran', file=sys.stderr)
                    status = 2
                    continue
            temp = xml.with_suffix('.xml.new')
            if temp.exists():
                temp.unlink()
            done = subprocess.run(repo['test'].replace('{out}', str(temp)), shell=True, cwd=root)
            if not temp.is_file():
                print(f'{repo["name"]}: the test command wrote no report to {temp} (exit {done.returncode})', file=sys.stderr)
                status = 2
                continue
            os.replace(temp, xml)
            rev_file.write_text(f'{head} {dirty}\n')
            print(f'{repo["name"]}: results kept for {head[:9]} (test command exit {done.returncode})')
    return status


# ---------- one repository: parse, join, measure, resolve ----------

def load_repo(project, conf, fetch=True):
    root, note = (conf['checkout'], None) if conf['layout'] == 'none' else source_root(conf, fetch)
    name = conf['name']
    # The folder of the specification files: the checkout, or the side folder of a ghost project.
    spec_root = conf.get('spec_root') or root
    repo = {'name': name, 'title': conf['title'] or conf['path'], 'path': conf['path'], 'root': root, 'spec_root': spec_root,
            'layout': conf['layout'],
            'source': conf['source'], 'note': note, 'sdd': {}, 'tdd': {}, 'groups': [], 'faults': [], 'deferred': set(),
            'areas': {}, 'catalog': [], 'head': git(root, 'rev-parse', 'HEAD'),
            'branch': conf['source'] if conf['source'] != 'checkout' else git(root, 'rev-parse', '--abbrev-ref', 'HEAD'),
            'dirty': len(git(root, 'status', '--porcelain').splitlines()), 'results': None, 'results_rev': None,
            'results_valid': False, 'unowned_code': [], 'unowned_tests': [], 'tracked_code': 0, 'tracked_tests': 0, 'rows': {}, 'one_sided': [],
            'files': {}, 'tdd_groups': [], 'sys': []}
    if conf['layout'] == 'none' or not os.path.isdir(root):
        return repo
    parser = {'single': parse_single, 'domains': parse_domains, 'sections': parse_sections}[conf['layout']]
    ctx = {'faults': repo['faults'], 'table': repo['rows'], 'files': repo['files'], 'sys': repo['sys']}
    repo['sdd'], repo['tdd'], repo['groups'], repo['tdd_groups'] = parser(name, spec_root, conf, ctx)
    sdd, tdd = repo['sdd'], repo['tdd']
    # Join the two directions of the trace: SDD 'tdd:' and TDD 'implements:'. A link that only one side states is a
    # measure (two projects had 473 and 176 on 2026-11-17). A link to a table row is shown as text.
    rows, one = repo['rows'], repo['one_sided']
    for t in tdd.values():
        for s in list(t['implements']):
            if s in sdd:
                if t['id'] not in sdd[s]['tdd']:
                    one.append(f'{t["file"]}:{t["line"]}: {t["id"]} implements {s}, but {s} does not name it')
                    sdd[s]['tdd'].append(t['id'])
            elif s in rows:
                t['implements'].remove(s)
                t['rows'].append(s)
            else:
                repo['faults'].append(f'{t["file"]}:{t["line"]}: {t["id"]} implements {s}, which is no current SDD item')
    for s in sdd.values():
        for t in list(s['tdd']):
            if t not in tdd:
                s['tdd'].remove(t)
                if t in rows:
                    s['rows'].append(t)
                else:
                    repo['faults'].append(f'{s["file"]}:{s["line"]}: {s["id"]} names {t}, which is no current TDD item')
            elif s['id'] not in tdd[t]['implements']:
                one.append(f'{s["file"]}:{s["line"]}: {s["id"]} names {t}, but {t} does not implement it')
    base = os.path.join(spec_root, conf['sdd']) if conf['layout'] == 'domains' else os.path.dirname(os.path.join(spec_root, conf['sdd']))
    index = os.path.join(base, 'index.json')
    if os.path.isfile(index):
        repo['deferred'] = {bare(k) for k in json.loads(read(index)).get('deferred_items', {})}
    catalog = os.path.join(base, 'capability-catalog.json')
    if os.path.isfile(catalog):
        cat = json.loads(read(catalog))
        for code, area in cat.get('area_contracts', {}).items():
            repo['areas'][code] = {'name': area.get('name', ''), 'ids': list(area.get('sdd_refs', []))}
        for f in cat.get('features', []):
            ids = f.get('sdd') or []
            ids = re.split(r'[,\s]+', ids) if isinstance(ids, str) else ids
            repo['catalog'].append({'id': f.get('id'), 'title': f.get('title', ''), 'area': f.get('area'), 'scope': f.get('scope', ''),
                                    'sdd': [bare(x) for x in ids if x],
                                    'tdd': split_list(f.get('tdd') or '') if isinstance(f.get('tdd'), str) else list(f.get('tdd') or [])})
            area = repo['areas'].get(f.get('area'))
            if area is not None:
                area['ids'] += [bare(x) for x in ids if x and bare(x) not in area['ids']]
    # Measures of the form of each SDD item (SDD-ST-13): a count, never a refusal.
    flag = conf['flag_words']
    pattern = re.compile(r'(?<![\w-])(' + '|'.join(re.escape(w) for w in sorted(flag, key=len, reverse=True)) + r')(?![\w-])', re.I) if flag else None
    for s in sdd.values():
        body = s.get('body', '')
        s['has_must'] = bool(MUST.search(s['sentence'] if s['sentence'] is not None else body))
        s['code_names'] = len(CODE_NAME.findall(body))
        s['words'] = len(body.split())
        if pattern:
            hits = collections.Counter(x.lower() for x in pattern.findall(body))
            s['flag_words'] = dict(hits.most_common())
            s['flag_in_title'] = bool(pattern.search(s['title']))
    for s in sdd.values():
        s['form'] = form_faults(repo, s, set(conf['interface_names']))
    results, rev = load_results(project, conf, root)
    repo['results_rev'] = rev
    repo['results_valid'] = results is not None and results_valid(conf, root, repo['head'], rev)
    repo['results_kept'] = results
    repo['results'] = results if repo['results_valid'] else None
    resolve_paths(repo, conf)
    return repo


def outside_code(text):
    return re.sub(r'`[^`]*`', ' ', text)


def form_faults(repo, item, allowed):
    """Where an SDD item breaks the item form of the standard: a list of (rule, reason). A measure; a commit check uses it."""
    out = []

    def add(rule, reason):
        if (rule, reason) not in out:
            out.append((rule, reason))

    sentence = item.get('sentence')
    if sentence is None:
        add('SP-07', 'no requirement sentence')
    else:
        plain = outside_code(sentence)
        count_must = len(re.findall(r'\bMUST\b', plain))
        if count_must != 1:
            add('SP-07', 'no MUST' if not count_must else f'MUST {count_must} times')
        if re.search(r'[.;]\s+[A-Z]', plain.rstrip('. ')):
            add('SP-07', 'more than one sentence')
        if NOT_EARS.match(plain) or (plain.startswith('If ') and ', then ' not in plain):
            add('SP-07', 'no EARS pattern')
        if len(sentence.split()) > 25:
            add('SP-08', f'{len(sentence.split())} words')
    lines = repo['files'].get(item.get('file') or '', [])[item['line']:item['end']] if repo['layout'] != 'domains' else []
    labels, fence = [], False
    for line in lines:
        if line.lstrip().startswith('```'):
            fence = not fence
            continue
        if fence or not line.strip() or re.match(r'\s*<!--.*-->\s*$', line):
            continue
        if re.search(r'\bMUST\b', outside_code(line)):
            add('SP-09', 'MUST in a part')
        part = re.match(r'- ([^:]{1,24}):(\s|$)', line)
        if part:
            labels.append(part.group(1))
            if part.group(1) not in PARTS:
                add('SP-10', f'part {part.group(1)}')
        elif not line.startswith((' ', '\t')):
            add('SP-10', 'text outside the parts')
    if repo['layout'] != 'domains' and 'Verified by' not in labels:
        add('SP-10', 'no Verified by')
    names = [x for x in CODE_NAME.findall(item.get('body', '')) if x.strip('`') not in allowed]
    if names:
        add('SP-11', f'{len(names)} code names, first {names[0]}')
    if not ID_FORM.match(item['id']):
        add('SP-12', 'the identifier is not area and number')
    if 'status' in item['meta']:
        add('SP-13', 'status in the trace comment')
    gap = item['meta'].get('gap')
    if gap is not None and not re.fullmatch(r'#\d+', gap):
        add('SP-14', f'gap is {gap}')
    return out


def touched_lines(root, base, rels):
    """{file: [(first, last)]}: the lines of the specification files that differ from the revision `base`."""
    out = collections.defaultdict(list)
    done = subprocess.run(['git', '-C', str(root), 'diff', '-U0', base, '--', *rels], capture_output=True, text=True)
    file = None
    for line in done.stdout.splitlines():
        if line.startswith('+++ '):
            file = line[6:] if line.startswith('+++ b/') else None
        m = re.match(r'@@ -\S+ \+(\d+)(?:,(\d+))? @@', line)
        if m and file:
            first, size = int(m.group(1)), int(m.group(2) or 1)
            out[file].append((first, first + max(size, 1) - 1))
    return out


def resolve_paths(repo, conf):
    root, results = repo['root'], repo['results']
    texts = {}
    files = git(root, 'ls-files').splitlines()
    for t in repo['tdd'].values():
        for kind, named in (('code', t.get('code_named', [])), ('test', t.get('tests_named', []))):
            for raw in named:
                # A TDD can write 'missing <path>' for a path that it plans and that is not built.
                planned = raw.startswith('missing ')
                path, _, symbol = (raw[8:] if planned else raw).partition('#')
                path = path.strip()
                full = os.path.join(root, path)
                p = {'raw': raw, 'path': path, 'kind': 'test' if kind == 'test' or is_test(path) else 'code',
                     'exists': os.path.exists(full), 'planned': planned, 'symbol_found': None, 'result': None, 'support': False, 'folder': os.path.isdir(full)}
                if symbol and os.path.isfile(full):
                    if full not in texts:
                        try:
                            texts[full] = read(full)
                        except OSError:
                            texts[full] = ''
                    # `Class.method` names a method of a class: code holds the two names, never the text with the dot.
                    p['symbol_found'] = all(re.search(r'(?<![\w$])' + re.escape(name) + r'(?![\w$])', texts[full])
                                            for name in symbol.strip().split('.') if name)
                if p['kind'] == 'test' and p['exists'] and results is not None:
                    rows = [v for f, v in results.items() if f == path or f.startswith(path.rstrip('/') + '/')]
                    if rows:
                        p['result'] = [sum(r[i] for r in rows) for i in range(3)]
                    elif os.path.isfile(full):
                        # A valid result has no case of this file, and its name is no test name: a helper of the tests.
                        p['support'] = not TEST_NAME.search(os.path.basename(path))
                    else:
                        # A folder with no case and with no file that has a test name: fixtures or helpers of the tests.
                        below = path.rstrip('/') + '/'
                        p['support'] = not any(TEST_NAME.search(os.path.basename(f)) for f in files if f.startswith(below))
                t['paths'].append(p)
        code = [p for p in t['paths'] if p['kind'] == 'code' and p['exists']]
        tests = [p for p in t['paths'] if p['kind'] == 'test' and p['exists'] and not p['support']]
        if any(p['result'] and p['result'][1] for p in tests):
            t['status'] = 'failing'
        elif not code and not tests:
            t['status'] = 'no code'
        elif not tests:
            t['status'] = 'no test'
        elif any(not p['result'] or p['result'][0] == 0 for p in tests):
            t['status'] = 'test not run'
        else:
            t['status'] = 'proved'
    for s in repo['sdd'].values():
        statuses = [repo['tdd'][t]['status'] for t in s['tdd']]
        s['status'] = min(statuses, key=ORDER.index) if statuses else 'no TDD'
    # Files that no TDD item names (SDD-ST-14).
    named = {p['path'].rstrip('/') for t in repo['tdd'].values() for p in t['paths'] if p['exists']}

    def owned(f):
        return f in named or any(f.startswith(n + '/') for n in named)

    endings, skip = tuple(conf['code_endings']), tuple(conf['not_counted'])
    tracked = [f for f in files if f.endswith(endings) and not (skip and f.startswith(skip))]
    repo['unowned_code'] = sorted(f for f in tracked if not is_test(f) and not owned(f))
    repo['unowned_tests'] = sorted(f for f in tracked if is_test(f) and not owned(f))
    repo['tracked_code'] = sum(1 for f in tracked if not is_test(f))
    repo['tracked_tests'] = sum(1 for f in tracked if is_test(f))


# ---------- the join of the top document with the repositories (SDD-ST-04) ----------

def resolve_selector(token, repos):
    """'app:domain/estimate', 'ops:section/1', 'app:area/0139', 'ops:LN-*', 'web:PB-03' -> (kind, repo, key, ids, fault)."""
    if ':' not in token:
        return None, None, token, [], f"'{token}' names no repository"
    name, key = token.split(':', 1)
    repo = repos.get(name)
    if repo is None:
        return None, None, key, [], f"'{token}' names an unknown repository"
    if key.startswith(('domain/', 'section/')):
        ids = [s['id'] for s in repo['sdd'].values() if s['group'] == key]
        return 'group', repo, key, ids, None if ids else f"'{token}' holds no SDD item"
    if key.startswith('area/'):
        area = repo['areas'].get(key[5:])
        if area is None:
            return None, repo, key, [], f"'{token}' is no area of the capability catalogue"
        return 'items', repo, key, [i for i in area['ids'] if i in repo['sdd']], None
    if any(c in key for c in '*?['):
        ids = [i for i in repo['sdd'] if fnmatch.fnmatchcase(i, key)]
        return 'items', repo, key, ids, None if ids else f"'{token}' matches no SDD item"
    if bare(key) in repo['sdd']:
        return 'items', repo, key, [bare(key)], None
    why = 'is deferred to the front end' if bare(key) in repo['deferred'] else 'is no current SDD item'
    return None, repo, key, [], f"'{token}' {why}"


def join(reqs, repos, label, prefix, upward=False):
    """Connect each top requirement to its SDD items. Returns (faults, gaps)."""
    owner = {}     # (repo, group) -> the top requirement that owns the group
    faults, gaps = [], []
    dm, fn = f'{prefix}-DM-', f'{prefix}-FN-'
    for r in reqs:
        r['groups'], r['items'] = [], []
    by_id = {r['id']: r for r in reqs}
    chapters = {r['chapter'] for r in reqs if r.get('chapter')}
    if upward:
        # The standard: each section names its one owner, and an item can name more (SDD-SP-04).
        for repo in repos.values():
            for g in repo['groups']:
                names = g.get('sys') or []
                where = f'{g["file"]}:{g["line"]}' if g.get('file') else f'{repo["name"]}:{g["key"]}'
                if (repo['name'], g['key']) in chapters:
                    continue   # the chapter of the system requirements has no owner
                if len(names) != 1:
                    faults.append(f'{where}: the section {g["title"]} names {len(names)} owners; it needs exactly one (sys:)')
                for name in names[:1]:
                    if name not in by_id:
                        faults.append(f'{where}: the section {g["title"]} names {name}, which is no system requirement')
                        continue
                    owner[(repo['name'], g['key'])] = name
                    by_id[name]['groups'].append((repo['name'], g['key']))
                    for s in repo['sdd'].values():
                        if s['group'] == g['key']:
                            s.setdefault('named_by', []).append(name)
            for s in repo['sdd'].values():
                for name in s.get('sys') or []:
                    if name not in by_id:
                        faults.append(f'{s["file"]}:{s["line"]}: {s["id"]} names {name}, which is no system requirement')
                    elif (repo['name'], s['id']) not in by_id[name]['items']:
                        by_id[name]['items'].append((repo['name'], s['id']))
                        if name not in s.setdefault('named_by', []):
                            s['named_by'].append(name)
    for r in reqs:
        for token in r['sdd']:
            kind, repo, key, ids, fault = resolve_selector(token, repos)
            if fault:
                faults.append(f'{label}:{r["line"]}: {r["id"]}: {fault}')
            if kind == 'group':
                if (repo['name'], key) in owner:
                    faults.append(f'{label}:{r["line"]}: {r["id"]}: \'{token}\' already belongs to {owner[(repo["name"], key)]}')
                else:
                    owner[(repo['name'], key)] = r['id']
                    r['groups'].append((repo['name'], key))
            elif kind == 'items':
                r['items'] += [(repo['name'], i) for i in ids if (repo['name'], i) not in r['items']]
            for i in ids:
                named = repos[repo['name']]['sdd'][i].setdefault('named_by', [])
                if r['id'] not in named:
                    named.append(r['id'])
    # Domains: a requirement with id <prefix>-DM-nn defines one; each other requirement with 'domain:' belongs to one.
    domains = collections.OrderedDict()
    for r in reqs:
        r['features'], r['area_list'] = [], []
        if r['id'].startswith(dm):
            if not r['domain']:
                faults.append(f'{label}:{r["line"]}: {r["id"]} has no \'domain:\' field')
            elif r['domain'] in domains:
                faults.append(f'{label}:{r["line"]}: {r["id"]}: the domain \'{r["domain"]}\' is defined two times')
            else:
                domains[r['domain']] = r
    area_owner = {}
    for r in reqs:
        if r['id'].startswith(dm):
            for token in r['areas']:
                name, _, code = token.partition(':')
                if name not in repos or code not in repos[name]['areas']:
                    faults.append(f'{label}:{r["line"]}: {r["id"]}: \'{token}\' is no area of a capability catalogue')
                elif (name, code) in area_owner:
                    faults.append(f'{label}:{r["line"]}: {r["id"]}: the area \'{token}\' already belongs to {area_owner[(name, code)]}')
                else:
                    area_owner[(name, code)] = r['id']
                    r['area_list'].append((name, code))
        elif r['domain']:
            if r['domain'] in domains:
                domains[r['domain']]['features'].append(r['id'])
            else:
                faults.append(f'{label}:{r["line"]}: {r["id"]}: \'{r["domain"]}\' is no domain of the top document')
        elif r['id'].startswith(fn):
            faults.append(f'{label}:{r["line"]}: {r["id"]} names no domain')
    for repo in repos.values():
        for code, area in repo['areas'].items():
            if domains and (repo['name'], code) not in area_owner:
                gaps.append(f'{label}: no domain holds the catalogue area {repo["name"]}:{code} ({area["name"]})')
    for r in reqs:
        # A rule for more than one repository: each repository that 'applies:' names must hold an SDD item for it.
        r['carried'] = collections.OrderedDict()
        for name in r['applies']:
            if name not in repos:
                faults.append(f'{label}:{r["line"]}: {r["id"]}: \'applies:\' names an unknown repository \'{name}\'')
                continue
            r['carried'][name] = [i for n, i in r['items'] if n == name]
        for n, _ in r['items']:
            if r['applies'] and n not in r['applies']:
                faults.append(f'{label}:{r["line"]}: {r["id"]}: \'sdd:\' names {n}, which \'applies:\' does not name')
    for repo in repos.values():
        for g in repo['groups']:
            if (repo['name'], g['key']) not in owner and not upward:
                gaps.append(f'{label}: no requirement owns {repo["name"]}:{g["key"]} ({g["title"]})')
    return faults, gaps


# ---------- the declared status (SDD-ST-07) ----------

def declared_kinds(declared):
    """('implemented'?, gap kinds, the tasks or issues that the marker cites)."""
    parts = [p.strip() for p in (declared or '').split(',') if p.strip()]
    implemented = any(p == 'implemented' for p in parts)
    gaps = [p.split(':', 1)[0] for p in parts if p.split(':', 1)[0] in GAP_KINDS]
    cites = [p.split(':', 1)[1] for p in parts if ':' in p]
    return implemented, gaps, cites


def differs(item):
    """True when the declared status and the computed status disagree."""
    if not item.get('declared'):
        return False
    implemented, gaps, _ = declared_kinds(item['declared'])
    if gaps:
        return item['status'] == 'proved'
    return implemented and item['status'] != 'proved'


# ---------- the build ----------

def build(conf, fetch=True):
    repos = collections.OrderedDict((c['name'], load_repo(conf['name'], c, fetch)) for c in conf['repositories'])
    tree = {'conf': conf, 'repos': repos, 'sections': [], 'reqs': [], 'front': [], 'faults': [], 'gaps': [], 'top': None}
    if conf['top']:
        top = conf['top']
        base = repos[top['repository']]['spec_root'] if top['repository'] else conf['base']
        path = os.path.join(base, top['path'])
        tree['top'] = {'label': top['path'], 'prefix': top['prefix']}
        if not os.path.isfile(path):
            tree['faults'].append(f'{top["path"]}: the top document does not exist')
        else:
            tree['sections'], tree['reqs'], faults, tree['front'] = parse_top(path, top['path'], top['prefix'])
            upward = is_upward(repos)
            more, gaps = join(tree['reqs'], repos, top['path'], top['prefix'], upward)
            if not upward:
                faults += [f'{top["path"]}:{r["line"]}: {r["id"]} has no \'sdd:\' field' for r in tree['reqs'] if not r['has_sdd']]
            tree['faults'] += faults + more
            tree['gaps'] += gaps
            tree['gaps'] += [f'{top["path"]}:{r["line"]}: {r["id"]} names no SDD item' for r in tree['reqs']
                             if not r['items'] and not r['groups'] and not r['outside']]
    flat = [req for r in repos.values() for req in r['sys']]
    if flat and not conf['top']:
        # The flattened form: the first chapter of the SDD holds the system requirements (SDD-SP-03).
        tree['top'] = {'label': 'the first chapter of the SDD', 'prefix': 'SYS'}
        tree['sections'] = [{'number': '1', 'title': 'System requirements', 'reqs': flat}]
        tree['reqs'] = flat
        more, gaps = join(flat, repos, 'system requirements', 'SYS', True)
        tree['faults'] += more
        tree['gaps'] += gaps + [f'{r["file"]}:{r["line"]}: {r["id"]} owns no section and no SDD item' for r in flat
                                if not r['items'] and not r['groups']]
    for r in repos.values():
        tree['faults'] += r['faults']
    return tree


def is_upward(repos):
    """True when the sections name their owner (the field sys:), the form of the standard (SDD-SP-04)."""
    return any(g.get('sys') for r in repos.values() for g in r['groups']) or any(r['sys'] for r in repos.values())


def count(items):
    c = collections.Counter(i['status'] for i in items)
    return {k: c[k] for k in ORDER if c[k]}


# ---------- the page (SDD-ST-11) ----------

STYLE = """
:root { color-scheme: light dark; --line: #8884; --soft: #8882; --ok: #2a8a4a; --bad: #c0392b; --warn: #b7791f; --none: #777; }
body { font: 16px/1.55 system-ui, sans-serif; max-width: 62rem; margin: 2rem auto; padding: 0 1.25rem; }
h1 { font-size: 1.7rem; margin: 0 0 .5rem; }
h2 { font-size: 1.35rem; margin: 3rem 0 .75rem; padding-top: 1rem; border-top: 2px solid var(--line); }
h3 { font-size: 1.15rem; margin: 2.5rem 0 .5rem; }
h4 { font-size: 1rem; margin: 0 0 .4rem; }
p, ul, ol, table, pre, dl { margin: 0 0 1rem; }
ul, ol { padding-left: 1.4rem; }
li { margin: .2rem 0; }
li > ul, li > ol { margin: .2rem 0 .3rem; }
code { font-size: .88em; }
pre { overflow: auto; padding: .75rem; background: var(--soft); border-radius: 4px; }
table { border-collapse: collapse; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: .3rem .6rem; text-align: left; vertical-align: top; }
nav ul { columns: 2; }
.meta { font-size: .85rem; opacity: .75; margin-bottom: .6rem; }
.status { font-size: .78rem; font-weight: 600; padding: .1rem .5rem; border-radius: 1rem; border: 1px solid; white-space: nowrap; }
.s-proved { --c: var(--ok); } .s-failing { --c: var(--bad); } .s-no-TDD, .s-no-code, .s-no-test, .s-test-not-run { --c: var(--warn); }
.status { color: var(--c, var(--none)); }
.sdd, .top { border-left: 4px solid var(--c, var(--none)); padding: .9rem 0 .2rem 1rem; margin: 0 0 2rem; }
.req { font-size: 1.05rem; font-weight: 600; margin-bottom: .5rem; }
.tdd { border: 1px solid var(--line); border-left: 4px solid var(--c, var(--none)); border-radius: 4px; margin: 0 0 .6rem; }
.tdd > summary, .list > summary, .text > summary { cursor: pointer; padding: .45rem .7rem; }
.tdd > div, .list > ul, .text > div { padding: .4rem .9rem .2rem; }
.list, .text { border: 1px solid var(--line); border-radius: 4px; margin: 0 0 .6rem; }
.label { font-size: .8rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; opacity: .7; margin: 1rem 0 .4rem; }
.paths li { list-style: none; margin-left: -1.2rem; }
.differ { color: var(--bad); }
"""


def e(s):
    return html.escape(str(s), quote=True)


def words(counts):
    return ', '.join(f'{n} {k}' for k, n in counts.items()) or 'no item'


def inline(text):
    """The inline part of Markdown that a specification uses: code, bold, links to the web, and the line break tag."""
    out, parts = [], re.split(r'(`[^`]+`)', text)
    for part in parts:
        if len(part) > 1 and part.startswith('`') and part.endswith('`'):
            out.append(f'<code>{e(part[1:-1])}</code>')
            continue
        part = e(part)
        part = re.sub(r'&lt;br\s*/?&gt;', '<br>', part, flags=re.I)   # the one tag that a table cell needs; each other tag stays text
        part = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', part)
        part = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2">\1</a>', part)
        part = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', part)   # a link inside the repository: keep its text
        out.append(part)
    return ''.join(out)


def md_html(lines):
    """Markdown to HTML for the body of a section or an item: paragraphs, lists with levels, tables, code blocks, headings."""
    out, para, stack, table, fence = [], [], [], [], None

    def flush_para():
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>')
            para.clear()

    def close_lists(depth=0):
        while len(stack) > depth:
            out.append('</li></' + stack.pop()[1] + '>')

    def flush_table():
        if not table:
            return
        rows = [[c.strip() for c in r.strip().strip('|').split('|')] for r in table]
        head = len(rows) > 1 and all(re.fullmatch(r':?-{2,}:?', c) for c in rows[1])
        out.append('<table>')
        if head:
            out.append('<thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in rows[0]) + '</tr></thead>')
        out.append('<tbody>' + ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in (rows[2:] if head else rows))
                   + '</tbody></table>')
        table.clear()

    for raw in lines:
        if fence is not None:
            if raw.lstrip().startswith('```'):
                out.append('<pre><code>' + e('\n'.join(fence)) + '</code></pre>')
                fence = None
            else:
                fence.append(raw)
            continue
        line = raw.rstrip()
        if line.lstrip().startswith('```'):
            flush_para(), flush_table(), close_lists()
            fence = []
            continue
        if re.match(r'\s*<!--.*-->\s*$', line) or re.match(r'\s*<a id="[^"]*"></a>\s*$', line):
            continue
        if not line.strip():
            flush_para(), flush_table()
            continue
        if line.lstrip().startswith('|'):
            flush_para(), close_lists()
            table.append(line)
            continue
        flush_table()
        m = re.match(r'(\s*)([-*]|\d+\.)\s+(.*)$', line)
        if m:
            flush_para()
            indent, kind = len(m.group(1)), 'ol' if m.group(2)[0].isdigit() else 'ul'
            while stack and stack[-1][0] > indent:
                out.append('</li></' + stack.pop()[1] + '>')
            if stack and stack[-1][0] == indent:
                out.append('</li><li>')
            else:
                stack.append((indent, kind))
                out.append(f'<{kind}><li>')
            out.append(inline(m.group(3)))
            continue
        m = re.match(r'(#{1,6})\s+(.*)$', line)
        if m:
            flush_para(), close_lists()
            out.append(f'<p><strong>{inline(m.group(2))}</strong></p>')
            continue
        if stack and raw.startswith(' '):
            out.append(' ' + inline(line.strip()))   # a continued line of a list item
            continue
        close_lists()
        para.append(line.strip())
    if fence is not None:
        out.append('<pre><code>' + e('\n'.join(fence)) + '</code></pre>')
    flush_para(), flush_table(), close_lists()
    return ''.join(out)


def body_lines(repo, thing, skip=1):
    """The source lines of an item or a section, without its first line."""
    lines = repo['files'].get(thing.get('file') or '', [])
    return lines[thing['line'] - 1 + skip:thing['end']]


def badge(status):
    return f'<span class="status s-{status.replace(" ", "-")}">{e(status)}</span>'


def cls(status):
    return 's-' + status.replace(' ', '-')


def declared_text(item):
    if not item['declared']:
        return ''
    mark = ' class="differ"' if differs(item) else ''
    return f' · <span{mark}>declared: {e(item["declared"])}' + (' (differs)' if differs(item) else '') + '</span>'


def render_path(p):
    note = []
    if p['planned']:
        note.append('planned, not built' if not p['exists'] else 'the TDD says missing, but the path exists')
    elif not p['exists']:
        note.append('PATH MISSING')
    if p['symbol_found'] is False:
        note.append('symbol not found in the file')
    if p['support']:
        note.append(('a support folder' if p['folder'] else 'a support file') + ': no test case')
    elif p['kind'] == 'test' and p['exists']:
        r = p['result']
        note.append(f'{r[0]} pass, {r[1]} fail, {r[2]} skipped' if r else 'no valid result kept')
    return f'<li>{p["kind"]}: <code>{e(p["raw"])}</code>{" — " + e("; ".join(note)) if note else ""}</li>'


def item_body(repo, item):
    """The full text of an item as HTML. In the domains layout the metadata lines come first, as a list of terms."""
    lines = body_lines(repo, item)
    if repo['layout'] == 'domains':
        meta = []
        while lines and re.match(r'[a-z_]+:\s', lines[0] + ' '):
            key, _, value = lines[0].partition(':')
            meta.append(f'<dt>{e(key)}</dt><dd>{inline(value.strip()) or "&nbsp;"}</dd>')
            lines = lines[1:]
        return (f'<details class="text"><summary>metadata</summary><div><dl>{"".join(meta)}</dl></div></details>' if meta else '') + md_html(lines)
    return md_html(lines)


def render_tdd(t, repo, anchors):
    aid = f'{t["repo"]}-{t["id"]}'
    attr = f' id="{e(aid)}"' if aid not in anchors else ''
    anchors.add(aid)
    tests = [p for p in t['paths'] if p['kind'] == 'test' and p['exists'] and p['result']]
    total = [sum(p['result'][i] for p in tests) for i in range(3)] if tests else None
    summary = f' — {total[0]} pass, {total[1]} fail' if total else ''
    paths = ''.join(render_path(p) for p in t['paths']) or '<li>The item names no path.</li>'
    if t['rows']:
        paths += '<li>rows: ' + ', '.join(f'<code>{e(r)}</code>' for r in t['rows']) + '</li>'
    serves = ', '.join(f'<a href="#{e(t["repo"])}-{e(i)}">{e(i)}</a>' for i in t['implements'])
    return (f'<details class="tdd {cls(t["status"])}"{attr}><summary><code>{e(t["id"])}</code> {e(t["title"])} {badge(t["status"])}{e(summary)}</summary><div>'
            f'<p class="meta"><code>{e(t["file"])}:{t["line"]}</code>{declared_text(t)} · implements {serves or "no SDD item"}</p>'
            f'{item_body(repo, t)}<p class="label">Code and tests</p><ul class="paths">{paths}</ul></div></details>')


def render_sdd(s, repo, anchors):
    aid = f'{s["repo"]}-{s["id"]}'
    anchors.add(aid)
    named = ''
    if s.get('named_by'):
        named = ' · named by ' + ', '.join(f'<a href="#{e(i)}">{e(i)}</a>' for i in s['named_by'])
    tdds = ''.join(render_tdd(repo['tdd'][t], repo, anchors) for t in s['tdd']) or '<p>No TDD item implements this requirement.</p>'
    return (f'<article class="sdd {cls(s["status"])}" id="{e(aid)}"><h4><code>{e(s["id"])}</code> {badge(s["status"])}</h4>'
            f'<p class="req">{inline(s["title"])}</p>'
            f'<p class="meta"><code>{e(s["file"])}:{s["line"]}</code>{declared_text(s)}{named}</p>'
            f'{item_body(repo, s)}<p class="label">Technical design: {len(s["tdd"])} TDD items</p>{tdds}</article>')


def group_id(repo, key):
    return f'{repo["name"]}-{key.replace("/", "-")}'


def render_group(repo, g, anchors):
    items = [s for s in repo['sdd'].values() if s['group'] == g['key']]
    where = f'<code>{e(g["file"])}:{g["line"]}</code> · ' if g.get('file') else ''
    intro = md_html(body_lines(repo, g)) if g.get('file') else ''
    state = f'{len(items)} SDD items: {words(count(items))}' if items else 'This section has no numbered requirement; its text is below.'
    return (f'<section id="{e(group_id(repo, g["key"]))}"><h3>{e(g["title"])}</h3><p class="meta">{where}{e(state)}</p>{intro}'
            + ''.join(render_sdd(s, repo, anchors) for s in items) + '</section>')


def lists(tree):
    """The lists of the page: (kind, title, rows of HTML)."""
    repos, reqs = tree['repos'], tree['reqs']
    out = [('fault', 'Faults of the structure', [e(f) for f in tree['faults']])]
    if tree['top']:
        out.append(('gap', 'Top document: gaps', [e(g) for g in tree['gaps']]))
        out.append(('gap', 'Rules for more than one repository that a repository does not carry',
                    [f'<a href="#{e(r["id"])}">{e(r["id"])}</a> {e(r["text"])} — no SDD item in: '
                     f'{e(", ".join(n for n, i in r["carried"].items() if not i))}' for r in reqs if any(not i for i in r['carried'].values())]))
    for r in repos.values():
        if r['layout'] == 'none':
            continue
        t = e(r['title'])

        def link(i, r=r):
            return f'<a href="#{e(r["name"])}-{e(i["id"])}"><code>{e(i["id"])}</code></a> {e(i["title"])}'

        paths_of = [(x, p) for x in r['tdd'].values() for p in x['paths']]
        out.append(('gap', f'{t}: SDD items with no TDD item', [link(s) for s in r['sdd'].values() if s['status'] == 'no TDD']))
        out.append(('gap', f'{t}: TDD items with a failing test', [link(x) for x in r['tdd'].values() if x['status'] == 'failing']))
        out.append(('gap', f'{t}: TDD items with no code', [link(x) for x in r['tdd'].values() if x['status'] == 'no code']))
        out.append(('gap', f'{t}: TDD items with code and no named test', [link(x) for x in r['tdd'].values() if x['status'] == 'no test']))
        out.append(('gap', f'{t}: TDD items whose named test has no valid kept result', [link(x) for x in r['tdd'].values() if x['status'] == 'test not run']))
        out.append(('gap', f'{t}: paths that the TDD plans and that are not built', [f'{link(x)}: <code>{e(p["path"])}</code>' for x, p in paths_of if p['planned'] and not p['exists']]))
        out.append(('gap', f'{t}: paths that the TDD says are missing, but that exist', [f'{link(x)}: <code>{e(p["path"])}</code>' for x, p in paths_of if p['planned'] and p['exists']]))
        out.append(('gap', f'{t}: named paths that do not exist', [f'{link(x)}: <code>{e(p["raw"])}</code>' for x, p in paths_of if not p['exists'] and not p['planned']]))
        out.append(('gap', f'{t}: named symbols that the file does not hold', [f'{link(x)}: <code>{e(p["raw"])}</code>' for x, p in paths_of if p['symbol_found'] is False]))
        if r['results']:
            out.append(('gap', f'{t}: test files with a failing case', [f'<code>{e(f)}</code> — {v[0]} pass, {v[1]} fail' for f, v in sorted(r['results'].items()) if v[1]]))
        rows = []
        for item in list(r['sdd'].values()) + list(r['tdd'].values()):
            if differs(item):
                cites = ', '.join(declared_kinds(item['declared'])[2])
                rows.append(f'{link(item)} — declared: {e(item["declared"])}; computed: {item["status"]}' + (f'; cites {e(cites)}' if cites else ''))
        out.append(('differ', f'{t}: declared and computed status differ', rows))
        for rule, meaning in RULES.items():
            rows = [f'{link(s)} — ' + e('; '.join(reason for code, reason in s['form'] if code == rule)) for s in r['sdd'].values()
                    if any(code == rule for code, _ in s['form'])]
            out.append(('form', f'{t}: {rule} ({meaning})', rows))
        # A named support path is owned and is no gap: an item with a support path alone has the status "no test".
        out.append(('measure', f'{t}: support paths that a TDD item names, with no test case', [f'{link(x)}: <code>{e(p["raw"])}</code>' for x, p in paths_of if p['support']]))
        out.append(('measure', f'{t}: links that only one side states', [e(x) for x in r['one_sided']]))
        out.append(('measure', f'{t}: SDD items with no "must" in their requirement sentence', [link(s) for s in r['sdd'].values() if not s['has_must']]))
        out.append(('measure', f'{t}: SDD items with 3 or more code names in their text, most first',
                    [f'{link(s)} — {s["code_names"]}' for s in sorted(r['sdd'].values(), key=lambda s: -s['code_names']) if s['code_names'] >= 3]))
        out.append(('measure', f'{t}: SDD items longer than 800 words, longest first',
                    [f'{link(s)} — {s["words"]}' for s in sorted(r['sdd'].values(), key=lambda s: -s['words']) if s['words'] > 800]))
        if any('flag_words' in s for s in r['sdd'].values()):
            flagged = sorted((s for s in r['sdd'].values() if s.get('flag_words')), key=lambda s: -sum(s['flag_words'].values()))
            out.append(('measure', f'{t}: SDD items whose title holds a flagged word', [link(s) for s in flagged if s['flag_in_title']]))
            out.append(('measure', f'{t}: SDD items that hold a flagged word, most first',
                        [f'{link(s)} — {sum(s["flag_words"].values())}: ' + e(', '.join(f'{w} {k}' for w, k in s['flag_words'].items())) for s in flagged]))
        out.append(('unnamed', f'{t}: code files that no TDD item names ({len(r["unowned_code"])} of {r["tracked_code"]})', [f'<code>{e(f)}</code>' for f in r['unowned_code']]))
        rows = []
        for f in r['unowned_tests']:
            res = (r['results'] or {}).get(f)
            rows.append(f'<code>{e(f)}</code>' + (f' — {res[0]} pass, {res[1]} fail, {res[2]} skipped' if res else ' — no valid result kept'))
        out.append(('unnamed', f'{t}: test files that no TDD item names ({len(r["unowned_tests"])} of {r["tracked_tests"]})', rows))
    return out


def render_lists(h, anchor, heading, blocks, note=''):
    h.append(f'<h2 id="{anchor}">{e(heading)}</h2>' + (f'<p>{e(note)}</p>' if note else ''))
    if not any(rows for _, rows in blocks):
        h.append('<p>None.</p>')
        return
    for t, rows in blocks:
        if rows:
            h.append(f'<details class="list"><summary>{e(t)}: {len(rows)}</summary><ul>' + ''.join(f'<li>{x}</li>' for x in rows) + '</ul></details>')


def render_top(h, tree, anchors):
    repos, reqs, top = tree['repos'], tree['reqs'], tree['top']
    by_id = {x['id']: x for x in reqs}
    for sec in tree['sections']:
        h.append(f'<h3>{e(sec["number"])}. {e(sec["title"])}</h3>')
        for r in sec['reqs']:
            below = [repos[n]['sdd'][i] for n, i in r['items']]
            for n, key in r['groups']:
                below += [s for s in repos[n]['sdd'].values() if s['group'] == key]
            worst = min((s['status'] for s in below), key=ORDER.index) if below else None
            state = f'{len(below)} SDD items: {words(count(below))}' if below else 'outside the specifications, by design' if r['outside'] else 'no SDD item below'
            domain_def = r['id'].startswith(top['prefix'] + '-DM-')
            domain = f' · domain {e(r["domain"])}' if r['domain'] else ''
            h.append(f'<article class="top {cls(worst) if worst else ""}" id="{e(r["id"])}"><h4><code>{e(r["id"])}</code>'
                     + (f' <strong>{e(r["domain"])}</strong>' if domain_def else '') + (f' {badge(worst)}' if worst else '') + '</h4>'
                     f'<p class="req">{inline(r["text"])}</p><p class="meta"><code>{e(r.get("file") or top["label"])}:{r["line"]}</code>{"" if domain_def else domain} · {e(state)}</p>')
            if r['notes']:
                h.append('<ul>' + ''.join(f'<li>{inline(n)}</li>' for n in r['notes']) + '</ul>')
            if r['carried']:
                h.append('<p class="meta">Must be carried by: ' + '; '.join(
                    f'{e(repos[n]["title"])}: ' + (f'{len(i)} SDD items' if i else 'NO SDD ITEM') for n, i in r['carried'].items()) + '</p>')
            if r['features']:
                h.append('<p class="label">Features</p><ul>' + ''.join(
                    f'<li><a href="#{e(i)}"><code>{e(i)}</code></a> {e(by_id[i]["text"])}</li>' for i in r['features']) + '</ul>')
            if r['groups']:
                h.append('<p class="label">Specification</p><ul>')
                for n, key in r['groups']:
                    g = next(x for x in repos[n]['groups'] if x['key'] == key)
                    inside = [s for s in repos[n]['sdd'].values() if s['group'] == key]
                    h.append(f'<li><a href="#{e(group_id(repos[n], key))}"><code>{e(n)}:{e(key)}</code> {e(g["title"])}</a> — {len(inside)} SDD items: {e(words(count(inside)))}</li>')
                h.append('</ul>')
            if r['items']:
                h.append('<p class="label">SDD items</p><ul>')
                for n, i in r['items']:
                    s = repos[n]['sdd'][i]
                    h.append(f'<li><a href="#{e(n)}-{e(i)}"><code>{e(n)}:{e(i)}</code></a> {e(s["title"])} {badge(s["status"])}</li>')
                h.append('</ul>')
            for n, code in r['area_list']:
                cat = [f for f in repos[n]['catalog'] if f['area'] == code]
                scopes = collections.Counter(f['scope'] for f in cat)
                h.append(f'<details class="list"><summary>Capability catalogue <code>{e(n)}:area/{e(code)}</code> {e(repos[n]["areas"][code]["name"])}: '
                         f'{len(cat)} rows ({e(", ".join(f"{k} {v}" for k, v in scopes.most_common()))})</summary><ul>')
                for f in cat:
                    links = ', '.join((f'<a href="#{e(n)}-{e(i)}"><code>{e(i)}</code></a>' if i in repos[n]['sdd'] else f'<code>{e(i)}</code> (no current SDD item)') for i in f['sdd']) or 'no SDD item'
                    h.append(f'<li><code>{e(f["id"])}</code> {e(f["title"])} [{e(f["scope"])}] &gt; {links} &gt; '
                             + (', '.join(f'<code>{e(t)}</code>' for t in f['tdd']) or 'no TDD') + '</li>')
                h.append('</ul></details>')
            h.append('</article>')


def render(tree):
    conf, repos, reqs = tree['conf'], tree['repos'], tree['reqs']
    anchors = set()
    spec_repos = [r for r in repos.values() if r['layout'] != 'none']
    title = f'Specification tree: {conf["name"]}'
    h = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">', f'<title>{e(title)}</title>',
         f'<style>{STYLE}</style>', '</head>', '<body>', f'<h1>{e(title)}</h1>',
         '<p>This page is compiled from the Markdown specification. To change a requirement, edit the file and line that the item shows, '
         'then compile again. Each requirement has its full text; below it is each TDD item that implements it, with its full text, '
         'its code paths and its unit test results.</p>']

    # Contents: the parts of this page for this project's shape (with or without a top document; one or more repositories).
    h.append('<nav><p class="label">Contents</p><ul><li><a href="#summary">Summary</a></li><li><a href="#faults">Faults</a></li>'
             '<li><a href="#gaps">Gaps</a></li><li><a href="#differ">Declared and computed status differ</a></li>')
    if tree['top']:
        h.append(f'<li><a href="#top">Top document: {e(tree["top"]["label"])}</a></li>')
    for r in spec_repos:
        h.append(f'<li><a href="#spec-{e(r["name"])}">Specification: {e(r["title"])}</a><ul>'
                 + ''.join(f'<li><a href="#{e(group_id(r, g["key"]))}">{e(g["title"])}</a></li>' for g in r['groups']) + '</ul></li>')
    h.append('<li><a href="#form">The item form of the standard</a></li><li><a href="#measures">Measures</a></li>'
             '<li><a href="#unnamed">Files that no TDD item names</a></li></ul></nav>')

    h.append('<h2 id="summary">Summary</h2><table><thead><tr><th>Repository</th><th>Source</th><th>Revision</th>'
             '<th>Uncommitted paths</th><th>Layout</th><th>Test result</th></tr></thead><tbody>')
    for r in repos.values():
        kept = r.get('results_kept')
        if kept is None:
            res = 'none kept' if r['layout'] != 'none' else 'not applicable'
        else:
            total = [sum(v[i] for v in kept.values()) for i in range(3)]
            rev = r['results_rev'][0][:9] if r['results_rev'] else 'an unknown revision'
            res = f'{len(kept)} test files: {total[0]} pass, {total[1]} fail, {total[2]} skipped; the tests ran on {rev}; '
            res += 'valid for this revision' if r['results_valid'] else 'NOT VALID for this revision: code changed after the test run'
        note = f' ({e(r["note"])})' if r.get('note') else ''
        h.append(f'<tr><td>{e(r["title"])}</td><td>{e(r["branch"])}{note}</td>'
                 f'<td><code>{e(r["head"][:9])}</code></td><td>{r["dirty"]}</td><td>{e(r["layout"])}</td><td>{e(res)}</td></tr>')
    h.append('</tbody></table>')
    h.append('<table><thead><tr><th>Repository</th><th>SDD items</th>' + ''.join(f'<th>{k}</th>' for k in reversed(ORDER))
             + '<th>TDD items</th>' + ''.join(f'<th>TDD: {k}</th>' for k in ('proved', 'test not run', 'no test', 'no code', 'failing'))
             + '</tr></thead><tbody>')
    for r in spec_repos:
        cs, ct = count(r['sdd'].values()), count(r['tdd'].values())
        h.append(f'<tr><td>{e(r["title"])}</td><td>{len(r["sdd"])}</td>' + ''.join(f'<td>{cs.get(k, 0)}</td>' for k in reversed(ORDER))
                 + f'<td>{len(r["tdd"])}</td>' + ''.join(f'<td>{ct.get(k, 0)}</td>' for k in ('proved', 'test not run', 'no test', 'no code', 'failing'))
                 + '</tr>')
    h.append('</tbody></table>')
    total = sum(len(r['sdd']) for r in repos.values())
    rows = [('SDD items', total), ('TDD items', sum(len(r['tdd']) for r in repos.values())),
            ('TDD items connected to no SDD item', sum(1 for r in repos.values() for t in r['tdd'].values() if not t['implements']))]
    if tree['top']:
        linked = sum(1 for r in repos.values() for s in r['sdd'].values() if s.get('named_by'))
        rows = [('Requirements of the top document', len(reqs)), ('SDD items connected to a top requirement', linked),
                ('SDD items not connected', total - linked)] + rows
    h.append('<table><tbody>' + ''.join(f'<tr><th>{e(k)}</th><td>{v}</td></tr>' for k, v in rows) + '</tbody></table>')
    h.append('<dl>' + ''.join(f'<dt>{badge(k)}</dt><dd>{e(MEANING[k])}</dd>' for k in reversed(ORDER)) + '</dl>')

    blocks = collections.OrderedDict((k, []) for k in ('fault', 'gap', 'differ', 'form', 'measure', 'unnamed'))
    for kind, heading, rows in lists(tree):
        blocks[kind].append((heading, rows))
    render_lists(h, 'faults', 'Faults', blocks['fault'], 'A fault is a break of the structure. Each count must be zero.')
    render_lists(h, 'gaps', 'Gaps', blocks['gap'], 'Work that remains below a requirement.')
    render_lists(h, 'differ', 'Declared and computed status differ', blocks['differ'],
                 'The status that a trace comment declares by hand, against the status that the files and the test results give.')

    if tree['top']:
        h.append(f'<h2 id="top">Top document: {e(tree["top"]["label"])}</h2>'
                 '<p>Each requirement of the top document, with the sections and the SDD items that realize it. The full text of each SDD item is in the specification part below.</p>')
        render_top(h, tree, anchors)

    for r in spec_repos:
        h.append(f'<h2 id="spec-{e(r["name"])}">Specification: {e(r["title"])}</h2>'
                 f'<p class="meta">layout: {e(r["layout"])} · {len(r["sdd"])} SDD items · {len(r["tdd"])} TDD items</p>')
        h += [render_group(r, g, anchors) for g in r['groups']]
        orphans = [t for t in r['tdd'].values() if not t['implements']]
        if orphans:
            h.append('<h3>TDD items that implement no SDD item</h3>' + ''.join(render_tdd(t, r, anchors) for t in orphans))
        prose = [(g, md_html(body_lines(r, g))) for g in r['tdd_groups']]
        prose = [(g, text) for g, text in prose if text]
        if prose:
            h.append('<h3>TDD: the text of each section that is outside an item</h3>'
                     + ''.join(f'<details class="text"><summary>{e(g["title"])} <span class="meta"><code>{e(g["file"])}:{g["line"]}</code></span></summary>'
                               f'<div>{text}</div></details>' for g, text in prose))

    clean = sum(1 for r in spec_repos for s in r['sdd'].values() if not s['form'])
    render_lists(h, 'form', 'The item form of the standard', blocks['form'],
                 f'SDD items that break a rule of the specification standard (area SP). {clean} of {total} SDD items break no rule. '
                 'dev-spec form refuses these for the items that a change touches.')
    render_lists(h, 'measures', 'Measures', blocks['measure'], 'A measure counts. It fails nothing.')
    render_lists(h, 'unnamed', 'Files that no TDD item names', blocks['unnamed'])
    h += ['</body>', '</html>']
    return '\n'.join(h) + '\n'


def as_json(tree):
    repos = tree['repos']

    def item(i, keys):
        return {k: i.get(k) for k in keys}

    data = {'schema': SCHEMA, 'name': tree['conf']['name'],
            'top': [{'section': s['title'], 'requirements': [item(r, ('id', 'text', 'line', 'domain', 'features', 'area_list', 'sdd', 'applies',
                                                                       'carried', 'groups', 'items', 'outside', 'file')) for r in s['reqs']]}
                    for s in tree['sections']],
            'repositories': {n: {'head': r['head'], 'source': r['branch'], 'dirty': r['dirty'], 'layout': r['layout'],
                                 'results_revision': r['results_rev'][0] if r['results_rev'] else None, 'results_valid': r['results_valid'],
                                 'groups': r['groups'],
                                 'sdd': {i: item(s, ('title', 'file', 'line', 'group', 'tdd', 'status', 'declared', 'has_must', 'code_names',
                                                     'words', 'flag_words', 'form')) | {'named_by': s.get('named_by', []), 'differs': differs(s)}
                                         for i, s in r['sdd'].items()},
                                 'tdd': {i: item(t, ('title', 'file', 'line', 'implements', 'rows', 'paths', 'status', 'declared')) | {'differs': differs(t)}
                                         for i, t in r['tdd'].items()},
                                 'code_no_tdd': r['unowned_code'], 'tests_no_tdd': r['unowned_tests'], 'one_sided': r['one_sided']}
                             for n, r in repos.items()},
            'faults': tree['faults'], 'gaps': tree['gaps']}
    return json.dumps(data, indent=1, sort_keys=True) + '\n'


# ---------- the command ----------

PAGE_FOLDER = 'dev-platform'


def home_git_dir(conf):
    """The Git folder of the repository that keeps the page of the project: the repository of the top document,
    else the first one with a specification. Each worktree of that repository shares this folder."""
    name = (conf['top'] or {}).get('repository')
    repos = [r for r in conf['repositories'] if r.get('checkout')]
    repo = next((r for r in repos if r['name'] == name), None) or next((r for r in repos if r['layout'] != 'none'), None)
    common = git(repo['checkout'], 'rev-parse', '--path-format=absolute', '--git-common-dir') if repo else ''
    return Path(common) if common else None


def in_checkout(folder):
    """True when the folder is in the working tree of a Git repository: a commit or a tool of that repository could read a file there."""
    here = Path(folder)
    while not here.is_dir() and here != here.parent:
        here = here.parent
    done = subprocess.run(['git', '-C', str(here), 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True)
    return done.returncode == 0 and done.stdout.strip() == 'true'


def output_paths(conf):
    """The page and the JSON tree (SDD-ST-11): the folder that the record names, else the folder of the platform in
    the Git folder of the project's repository, where no commit and no tool of the repository reads."""
    if conf.get('page'):
        folder = Path(conf['page']).expanduser()
    else:
        home = home_git_dir(conf)
        folder = home / PAGE_FOLDER if home else Path(conf['base'])
    return folder / PAGE, folder / DATA


def own_ignore(folder):
    """A page folder in a working tree hides itself from Git with its own ignore file: no file of the repository
    names the platform (SDD-PJ-06). True when the folder is in a working tree."""
    if not in_checkout(folder):
        return False
    ignore = Path(folder) / '.gitignore'
    if not ignore.is_file():
        ignore.write_text('# Written by dev-spec: this folder holds compiled files of the platform.\n*\n', encoding='utf-8')
    return True


def form_command(tree, base):
    """dev-spec form: one line for each rule that an SDD item breaks. With --base, only the items that a change touches."""
    found = 0
    for r in tree['repos'].values():
        if r['layout'] == 'none':
            continue
        touched = touched_lines(r['spec_root'], base, sorted({s['file'] for s in r['sdd'].values()})) if base else None
        for s in r['sdd'].values():
            if touched is not None and not any(first <= s['end'] and last >= s['line'] for first, last in touched.get(s['file'], [])):
                continue
            for rule, reason in s['form']:
                print(f'{s["file"]}:{s["line"]}: {s["id"]}: {rule}: {reason}')
                found += 1
    scope = f'in the items that differ from {base}' if base else 'in all SDD items'
    print(f'{found} breaks of the item form {scope}', file=sys.stderr)
    return 1 if found else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    known = ('compile', 'check', 'test', 'form')
    # export-begin: this part is not in a copy of the tool
    if argv[:1] == ['export']:
        from . import specexport
        return specexport.main(argv[1:])
    # export-end
    from . import specwrite   # the commands that explain and change a specification (area SW)
    first = next((word for word in argv if word in known + specwrite.COMMANDS), None)
    if first in specwrite.COMMANDS:
        return specwrite.main(argv)
    ap = argparse.ArgumentParser(prog='dev-spec', description='Compile a project\'s specification tree: top document > SDD > TDD > code and tests.',
                                 epilog='Explain and change: find, why, open, set, add, remove, move, text, link, unlink, bind, unbind, own, confirm, accept. '
                                        'See dev-spec find --help.')
    ap.add_argument('command', choices=('compile', 'check', 'test', 'form'))
    ap.add_argument('project', nargs='?', help='the name of a project that has a record in the projects folder of the platform')
    ap.add_argument('--config', help='the path of a project config')
    ap.add_argument('--no-fetch', action='store_true', help='do not fetch the source ref of a repository')
    ap.add_argument('--base', help='form: examine only the SDD items whose lines differ from this revision')
    ap.add_argument('--junit', help='test: keep this JUnit report of a pipeline as the result of the present revision; run no test')
    ap.add_argument('--proved', action='store_true',
                    help='check: fail also when an SDD item is not proved and names no gap')
    ap.add_argument('--root', help='with --layout: the checkout; the default is this folder')
    settings_arguments(ap)
    args = ap.parse_args(argv)
    try:
        if args.layout:
            if args.config or args.project:
                raise ConfigError(['give a project name, --config FILE or --layout, not two of them'])
            conf = arguments_config(args.root or os.getcwd(), args.layout, args.sdd, args.tdd, args.spec_root)
        elif not args.config and not args.project:
            raise ConfigError(['give a project name, --config FILE, or the settings: --layout with --sdd, --tdd, --spec-root'])
        else:
            conf = load_config(args.config or find_config(args.project))
        if conf['parts'] is not None and 'tree' not in conf['parts']:
            raise ConfigError([f'the tree is off for the project {conf["name"]}: its record does not list the part "tree" (SDD-PJ-04)'])
        if args.command == 'test':
            return keep_results(conf, args.junit) if args.junit else run_tests(conf)
        tree = build(conf, fetch=not args.no_fetch)
    except ConfigError as error:
        for line in error.problems:
            print(f'dev-spec: {line}', file=sys.stderr)
        return 2
    if args.command == 'form':
        return form_command(tree, args.base)
    for r in tree['repos'].values():
        if r['layout'] != 'none':
            print(f'{r["name"]}: {len(r["sdd"])} SDD ({words(count(r["sdd"].values()))}); {len(r["tdd"])} TDD ({words(count(r["tdd"].values()))})')
    if tree['top']:
        print(f'top document: {len(tree["reqs"])} requirements')
    print(f'{len(tree["faults"])} faults, {len(tree["gaps"])} gaps')
    if args.command == 'check':
        for fault in tree['faults']:
            print(fault, file=sys.stderr)
        open_items = not_proved(tree) if args.proved else []
        for row in open_items:
            print(row, file=sys.stderr)
        if args.proved:
            print(f'{len(open_items)} SDD items are not proved and name no gap')
        return 1 if tree['faults'] or open_items else 0
    page, data = output_paths(conf)
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(render(tree), encoding='utf-8')
    data.write_text(as_json(tree), encoding='utf-8')
    print(f'page: {page}')
    if own_ignore(page.parent):
        print(f'The page folder is in a working tree. Its own ignore file hides it from Git; '
              f'a formatter or a check of the repository can still read it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
