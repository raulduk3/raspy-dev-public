"""dev-spec: the commands that explain and change a specification (docs/spec/SDD.md, area SW).

    dev-spec find  "text"                      the items that match, in the order of the sections
    dev-spec why   ID | PATH                   the chain from the system requirement to the tests
    dev-spec set   ID --text FILE [--gap #N]   a new text for an item
    dev-spec add   --level sdd|tdd --section S [--area XX] --text FILE [--implements IDS]
    dev-spec remove ID                         an item, or an old text block that only a trace comment names
    dev-spec remove SYS-ID                     a system requirement that no section and no SDD item names
    dev-spec remove --level sdd|tdd --section S    a section that holds no item
    dev-spec move  ID --section S
    dev-spec renumber TDD-ID TDD-ID            a free number of the same section, for a TDD item that the base branch does not hold
    dev-spec text  --level sdd|tdd [--section S] --text FILE    the text of a section that is outside its items
    dev-spec link | unlink  TDD-ID SDD-ID
    dev-spec bind | unbind  TDD-ID --code PATH | --test PATH
    dev-spec own   SECTION SYS-ID              the one owner of a section
    dev-spec own   ID SYS-ID | none            one more owner for one SDD item
    dev-spec confirm N ID=same|change|conflict ...
    dev-spec open

No agent edits a specification file. A write command is a proposal first: it examines the form, shows each
related item and writes nothing. `confirm` takes one answer for each related item, writes the change,
compiles the whole tree and undoes a change that adds a fault. Each write is recorded in the platform's state.
"""
import argparse
import collections
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

from . import spectree as st

READ = ('find', 'why', 'open')
WRITE = ('set', 'add', 'remove', 'link', 'unlink', 'bind', 'unbind', 'own', 'move', 'text', 'renumber')
COMMANDS = READ + WRITE + ('confirm', 'accept', 'staged')
ANSWERS = ('same', 'change', 'conflict')
STOP = set('''about above after again also been before being below between both cannot could does doing down during
each from further have having here into itself more most must only other over same shall should some such than that
their them then there these they this those through under until very were what when where which while with would
your item items each when must not the and for are has its one two any can not'''.split())


class Refused(Exception):
    pass


# ---------- the project of the folder ----------

def context(args):
    """The config and the tree for the folder of the command: its repository is compiled as the checkout that it is."""
    here = Path(args.root or os.getcwd()).resolve()
    top = st.git(here, 'rev-parse', '--show-toplevel')
    if getattr(args, 'layout', None):
        if args.config:
            raise Refused('give --config FILE or --layout, not both')
        conf = st.arguments_config(top or here, args.layout, args.sdd, args.tdd, args.spec_root)
    elif args.config:
        conf = st.load_config(args.config)
    else:
        if not top:
            raise Refused('this folder is no Git checkout; give --config FILE')
        conf = st.load_config(config_of(top))
    if top:
        common = st.git(top, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        for repo in conf['repositories']:
            if repo['layout'] != 'none' and st.git(repo['checkout'], 'rev-parse', '--path-format=absolute', '--git-common-dir') == common:
                # A read command in the primary checkout uses the source of the config (for example origin/develop):
                # that checkout can be on a branch with no specification. A write command, and each command in a
                # worktree of a session, works on the folder where it runs.
                primary = os.path.realpath(top) == os.path.realpath(repo['checkout'])
                if args.command in READ and primary and repo['source'] != 'checkout' and not args.root:
                    continue
                repo['checkout'], repo['source'] = top, 'checkout'
    return conf


def config_of(top):
    """The project record that names the repository of this checkout."""
    common = st.git(top, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    for record in sorted(st.projects_dir().glob('*.json')) if st.projects_dir().is_dir() else []:
        try:
            base = record.parent
            for repo in json.loads(st.read(record)).get('repositories', []):
                # the checkout of the repository, or the side folder that holds the specification of a ghost project
                for place in filter(None, (repo.get('path'), repo.get('spec_root'))):
                    folder = str((base / Path(place).expanduser()).resolve())
                    if st.git(folder, 'rev-parse', '--path-format=absolute', '--git-common-dir') == common:
                        return record
        except (OSError, ValueError, AttributeError):
            continue
    raise Refused('no project record names this repository; give --config FILE')


def state(conf):
    folder = st.state_root() / conf['name']
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ---------- the items ----------

def catalogue(tree):
    """Each item of each level in the order of the documents: (repo, level, id, item)."""
    out = []
    for req in tree['reqs']:
        out.append((None, 'SYS', req['id'], req))
    for repo in tree['repos'].values():
        out += [(repo, 'SDD', i, s) for i, s in repo['sdd'].items()]
        out += [(repo, 'TDD', i, t) for i, t in repo['tdd'].items()]
    return out


def locate(tree, item_id):
    wanted = st.bare(item_id)
    for repo, level, i, item in catalogue(tree):
        if i == wanted or i == item_id:
            return repo, level, item
    if not any(level != 'SYS' for _, level, _, _ in catalogue(tree)):
        raise Refused(f'this checkout holds no item of the specification; is it on the correct branch? ({item_id} was not found)')
    raise Refused(f'{item_id} is no item of this specification')


def text_of(repo, level, item):
    if level == 'SYS':
        return item['text']
    return '\n'.join(repo['files'][item['file']][item['line'] - 1:item['end']]).strip('\n')


def label(level, item):
    return item['text'] if level == 'SYS' else item['title']


def terms(text):
    """The words of a text with their endings removed, so that "release", "released" and "releases" are one term."""
    return {re.sub(r'(?<=[a-z]{4})(ing|ed|es|s|e)$', '', w) for w in re.findall(r'[a-z][a-z-]{3,}', st.outside_code(text).lower())
            if w not in STOP}


def by_terms(tree, text, skip=(), levels=('SYS', 'SDD', 'TDD')):
    """Items by shared terms, most first. A rare term counts more than a common one. No model."""
    rows = [(repo, level, i, item, terms(text_of(repo, level, item))) for repo, level, i, item in catalogue(tree) if level in levels]
    frequency = collections.Counter(t for *_, own in rows for t in own)
    wanted = terms(text)
    scored = []
    for position, (repo, level, i, item, own) in enumerate(rows):
        shared = wanted & own
        if shared and i not in skip:
            scored.append((-sum(math.log(1 + len(rows) / frequency[t]) for t in shared), position, repo, level, i, item))
    return [(repo, level, i, item) for _, _, repo, level, i, item in sorted(scored, key=lambda row: row[:2])]


def related(tree, repo, level, item, text):
    """The items that a change of this item can affect: {id: [reason]} in a fixed order (SDD-SW-03)."""
    out = collections.OrderedDict()

    def add(i, reason):
        if i != item.get('id'):
            out.setdefault(i, []).append(reason)

    if level == 'SDD':
        for t in item['tdd']:
            add(t, 'implements it')
            for other in repo['tdd'][t]['implements']:
                add(other, f'shares {t}')
        siblings = [s for s in repo['sdd'].values() if s['group'] == item['group']]
        owner = next((g for g in repo['groups'] if g['key'] == item['group']), {})
        for name in list(owner.get('sys') or []) + list(item.get('sys') or []):
            add(name, 'the system requirement above it')
    elif level == 'TDD':
        for s in item['implements']:
            add(s, 'it implements')
        mine = {p['path'] for p in item['paths']}
        for other in repo['tdd'].values():
            if other is not item and mine & {p['path'] for p in other['paths']}:
                add(other['id'], 'names the same path')
        siblings = [t for t in repo['tdd'].values() if t['file'] == item['file']]
    else:
        siblings = []
    if item in siblings:
        at = siblings.index(item)
        for near in siblings[max(0, at - 2):at] + siblings[at + 1:at + 3]:
            add(near['id'], 'next to it in its section')
    elif level == 'TDD' and item.get('file') is None:   # a new TDD item: the last items of its section
        prefix = item['id'].rsplit('.', 1)[0] + '.'
        for near in [t for t in repo['tdd'].values() if t['id'].startswith(prefix)][-2:]:
            add(near['id'], 'next to it in its section')
    else:   # a new SDD item, or the owner of a section: the last items of the section
        for near in siblings[-2:]:
            add(near['id'], 'next to it in its section')
    # The same level first, then the other level: a TDD item of a different SDD item can contradict this item.
    same, other = (('SDD', 'SYS'), ('TDD',)) if level == 'SDD' else (('TDD',), ('SDD',))
    for levels, limit in ((same, 5), (other, 3)):
        count = 0
        for _, _, i, _ in by_terms(tree, text, skip={item.get('id')}, levels=levels):
            if count == limit:
                break
            if i not in out:
                add(i, 'shares terms')
                count += 1
    return out


# ---------- read commands ----------

def find(tree, query):
    rows = by_terms(tree, query)
    order = {i: n for n, (_, _, i, _) in enumerate(catalogue(tree))}
    for repo, level, i, item in sorted(rows[:25], key=lambda row: order[row[2]]):
        where = f'{item.get("file") or tree["top"]["label"]}:{item["line"]}'
        print(f'{i}  {label(level, item)}  [{where}]')
    print(f'{min(len(rows), 25)} of {len(rows)} items that share a term, in the order of the sections', file=sys.stderr)
    return 0


def why(tree, target):
    names = {i for _, _, i, _ in catalogue(tree)}
    if st.bare(target) in names or target in names:
        repo, level, item = locate(tree, target)
        if level == 'SYS':
            print(f'{item["id"]}  {item["text"]}')
            for n, key in item['groups']:
                print(f'  section {n}:{key}')
                for s in tree['repos'][n]['sdd'].values():
                    if s['group'] == key:
                        print(f'    {s["id"]}  [{s["status"]}]  {s["title"]}')
            for n, i in item['items']:
                print(f'  {i}  [{tree["repos"][n]["sdd"][i]["status"]}]  {tree["repos"][n]["sdd"][i]["title"]}')
            return 0
        sdds = [item] if level == 'SDD' else [repo['sdd'][s] for s in item['implements']]
        if level == 'TDD' and not sdds:
            print('no SDD item requires this TDD item')
        for s in sdds:
            for name in s.get('named_by') or ['no system requirement']:
                print(f'{name}')
            print(f'  {s["id"]}  [{s["status"]}]  {s["title"]}  ({s["file"]}:{s["line"]})')
            for t in ([repo['tdd'][x] for x in s['tdd']] if level == 'SDD' else [item]):
                print(f'    {t["id"]}  [{t["status"]}]  {t["title"]}  ({t["file"]}:{t["line"]})')
                for p in t['paths']:
                    result = f'{p["result"][0]} pass, {p["result"][1]} fail' if p['result'] else ('no result' if p['kind'] == 'test' else '')
                    print(f'      {p["kind"]}: {p["raw"]}' + ('' if p['exists'] else '  PATH MISSING') + (f'  ({result})' if result else ''))
        return 0
    path, found = target.rstrip('/'), False
    for repo in tree['repos'].values():
        for t in repo['tdd'].values():
            if any(p['path'].rstrip('/') == path or path.startswith(p['path'].rstrip('/') + '/') for p in t['paths']):
                found = True
                print(f'{path} is named by {t["id"]}  [{t["status"]}]  {t["title"]}')
                for s in t['implements']:
                    sdd = repo['sdd'][s]
                    print(f'  which implements {s}  [{sdd["status"]}]  {sdd["title"]}')
                    for name in sdd.get('named_by') or []:
                        print(f'    under {name}')
    if not found:
        print(f'no TDD item names {path}: the specification does not explain this file')
        return 1
    return 0


# ---------- the text of an item ----------

def trace_line(fields):
    return '<!-- ' + ' | '.join(f'{k}: {v}' for k, v in fields.items()) + ' -->'


def trace_at(lines, item):
    """(index of the trace comment in the lines of the file, its fields)."""
    for index in range(item['line'], min(item['line'] + 3, len(lines))):
        fields = st.trace_comment(lines[index])
        if fields is not None:
            return index, fields
    raise Refused(f'{item["id"]} has no trace comment')


def join_ids(values):
    return ', '.join(values) if values else 'none'


def drop_status(fields):
    """A command removes the status of an item that it changes (SDD-SP-13). A status that cites a task stays as the gap."""
    status = fields.pop('status', None)
    cited = re.search(r'#\d+', status or '')
    if cited and not status.startswith('implemented') and 'gap' not in fields:
        fields['gap'] = cited.group(0)


def new_text(level, raw):
    rows = [r.rstrip() for r in raw.strip('\n').splitlines()]
    if not rows or not rows[0].strip():
        raise Refused('the text is empty: the first line is the requirement sentence (SDD) or the title (TDD)')
    first, rest = rows[0].strip(), rows[1:]
    while rest and not rest[0].strip():
        rest = rest[1:]
    if level == 'TDD' and re.search(r'\bMUST\b', st.outside_code('\n'.join(rows))):
        raise Refused('SP-09: a TDD item holds no MUST; a requirement belongs to the SDD')
    return first, rest


# ---------- the changes: each returns {relative file: new lines} and the ids that it changed ----------

def change_set(tree, repo, level, item, args):
    lines = list(repo['files'][item['file']])
    at, fields = trace_at(lines, item)
    if args.text is None:   # only the gap changes; the text stays
        if not args.gap:
            raise Refused('give --text FILE, or --gap to change only the gap')
        drop_status(fields)
        fields.pop('gap', None)
        if args.gap != 'none':
            fields['gap'] = args.gap
        lines[at] = trace_line(fields)
        return {item['file']: lines}, st_text(repo, item)
    first, rest = new_text(level, read_text(args.text))
    drop_status(fields)
    if args.gap:
        fields.pop('gap', None)
        if args.gap != 'none':
            fields['gap'] = args.gap
    head = f'**{item["id"]}.** {first}' if level == 'SDD' else re.sub(r'^(#{4,5}) .*$', rf'\1 {item["id"]} {first}', lines[item['line'] - 1])
    block = lines[item['line'] - 1:at]
    block[0] = head
    block += [trace_line(fields), ''] + rest + ['']
    end = item['end']
    while end < len(lines) and not lines[end].strip():
        end += 1
    lines[item['line'] - 1:end] = block
    return {item['file']: lines}, first + ' ' + ' '.join(rest)


def change_links(tree, repo, updates):
    """updates: {item id: (field, function that maps the list of values to the new list)}."""
    files = {}
    for item_id, (field, change) in updates.items():
        item = repo['tdd'].get(item_id) or repo['sdd'][item_id]
        lines = files.setdefault(item['file'], list(repo['files'][item['file']]))
        at, fields = trace_at(lines, item)
        values = change(st.split_list(fields.get(field, '')))
        fields[field] = join_ids(values)
        drop_status(fields)
        lines[at] = trace_line(fields)
    return files


def retired_before(conf):
    """The identifiers that a removed section held: its retired comments left the documents with it (SDD-SW-09)."""
    journal = state(conf) / 'journal.jsonl'
    return [i for line in (st.read(journal).splitlines() if journal.is_file() else []) for i in json.loads(line).get('retired', [])]


def numbers_used(tree, repo, pattern):
    """The numbers that an item holds or held: the identifier of each item and each old block, each `retired` comment, and
    each identifier of a removed section. A text that only names an identifier uses no number."""
    names = list(retired_before(tree['conf']))
    for lines in repo['files'].values():
        for _, line in st.lines_outside_fences('\n'.join(lines)):
            fields, item, head = st.trace_comment(line), st.SDD_LINE.match(line), st.TDD_HEAD.match(line)
            gone = re.match(r'\s*<!--\s*retired:\s*(\S+)\s*-->', line)
            names += [fields.get('id', '')] if fields is not None else []
            names += ['**' + item.group(1)] if item else []
            names += [head.group(1)] if head else []
            names += [gone.group(1)] if gone else []
    # A system requirement and an SDD item of one area share the numbers of that area.
    return {int(n) for name in names for n in pattern.findall(re.sub(r'^SYS-', 'SDD-', name))}


def change_add(tree, repo, args):
    first, rest = new_text(args.level.upper(), read_text(args.text))
    if args.level == 'sdd':
        if not args.area or not re.fullmatch(r'[A-Z]{2}', args.area):
            raise Refused('give --area XX: the two letters of the area of the new SDD item')
        group = next((g for g in repo['groups'] if g['key'] == 'section/' + args.section), None)
        if group is None:
            raise Refused(f'{args.section} is no section of the SDD')
        used = numbers_used(tree, repo, re.compile(rf'(?:\*\*|SDD-){args.area}-(\d+)'))
        new_id = f'{args.area}-{max(used, default=0) + 1:02d}'
        inside = [s for s in repo['sdd'].values() if s['group'] == group['key']]
        after = max([s['end'] for s in inside] + [group['end']])
        block = ['', f'**{new_id}.** {first}', trace_line({'id': f'SDD-{new_id}', 'tdd': 'none'}), ''] + rest + ['']
        file = group['file']
    else:
        prefix = f'TDD-{args.section}.'
        inside = [t for t in repo['tdd'].values() if t['id'].startswith(prefix) and '.' not in t['id'][len(prefix):]]
        group = next((g for g in repo['tdd_groups'] if g['key'] == 'section/' + args.section), None)
        if group is None and not inside:
            raise Refused(f'{args.section} is no section of the TDD')
        used = numbers_used(tree, repo, re.compile(rf'TDD-{re.escape(args.section)}\.(\d+)(?![\d.])'))
        new_id = f'{prefix}{max(used, default=0) + 1}'
        implements = [st.bare(x) for x in st.split_list(args.implements or '')]
        for s in implements:
            if s not in repo['sdd']:
                raise Refused(f'--implements names {s}, which is no SDD item')
        after = max([t['end'] for t in inside] + ([group['end']] if group else []))
        file = (inside[0] if inside else group)['file']
        block = ['', f'#### {new_id} {first}', trace_line({'id': new_id, 'implements': join_ids(['SDD-' + s for s in implements]), 'code': 'none', 'tests': 'none'}), ''] + rest + ['']
    lines = list(repo['files'][file])
    while after > 0 and not lines[after - 1].strip():
        after -= 1
    if after < len(lines) and not lines[after].strip():
        block = block[:-1]   # one empty line stays between the new item and the text after it
    lines[after:after] = block
    files = {file: lines}
    if args.level == 'tdd':
        for name, changed in change_links(tree, repo, {s: ('tdd', lambda v, n=new_id: v + [n]) for s in implements}).items():
            if name == file:   # the same file holds both sides: apply the link change to the new lines
                raise Refused('the SDD and the TDD are in one file; add the item, then link it')
            files[name] = changed
    return files, new_id, first + ' ' + ' '.join(rest)


def change_remove(tree, repo, level, item):
    full = ('SDD-' if level == 'SDD' else '') + item['id']
    others = {t: ('implements', lambda v, i=item['id']: [x for x in v if st.bare(x) != i]) for t in item['tdd']} if level == 'SDD' \
        else {s: ('tdd', lambda v, i=item['id']: [x for x in v if x != i]) for s in item['implements']}
    files = change_links(tree, repo, others)
    lines = files.setdefault(item['file'], list(repo['files'][item['file']]))
    end = item['end']
    while end < len(lines) and not lines[end].strip():
        end += 1
    lines[item['line'] - 1:end] = [f'<!-- retired: {full} -->', '']
    return files


def change_retire(tree, repo, req):
    """A system requirement of the first chapter of the SDD leaves, when no section and no SDD item names it."""
    names = [next(g['title'] for g in tree['repos'][r]['groups'] if g['key'] == key) for r, key in req['groups']] + [i for _, i in req['items']]
    if names:
        raise Refused(f'{req["id"]} is the owner of: ' + ', '.join(names) + '\n'
                      '  give each one a different owner (dev-spec own), or remove it, and then remove the system requirement')
    lines = list(repo['files'][req['file']])
    end = req['line']
    while end < len(lines):
        row, fields = lines[end], st.trace_comment(lines[end])
        ahead = next((r for r in lines[end:] if r.strip()), '')
        if (fields is not None and fields.get('id') == req['id']) or row.startswith(('- ', '  ', '\t')) \
                or (not row.strip() and ahead.startswith('- ')):
            end += 1   # the trace comment and the parts of the requirement
        else:
            break
    text = '\n'.join(lines[req['line'] - 1:end]).strip('\n')
    while end < len(lines) and not lines[end].strip():
        end += 1
    lines[req['line'] - 1:end] = [f'<!-- retired: {req["id"]} -->', '']
    return {req['file']: lines}, text


def change_section(tree, repo, level, section):
    """A section with no item leaves the document. In the sections layout its file leaves, when it holds no other line.
    Returns (files, the text of the section, the section, the identifiers that its retired comments hold)."""
    groups = repo['groups'] if level == 'SDD' else repo['tdd_groups']
    group = next((g for g in groups if g['key'] == 'section/' + section), None)
    if group is None:
        raise Refused(f'{section} is no section of the {level}')
    rel, first = group['file'], group['line']
    lines = repo['files'][rel]
    depth = len(lines[first - 1]) - len(lines[first - 1].lstrip('#'))
    last = next((n - 1 for n, row in st.lines_outside_fences('\n'.join(lines)) if n > first and re.match(rf'#{{1,{depth}}} ', row)), len(lines))
    inside = lambda thing: thing.get('file') == rel and first < thing['line'] <= last   # noqa: E731
    held = [s['id'] for s in repo['sdd'].values() if inside(s)] + [t['id'] for t in repo['tdd'].values() if inside(t)] \
        + [r['id'] for r in tree['reqs'] if r.get('chapter') == (repo['name'], group['key']) or (r.get('chapter') and inside(r))]
    if held:
        raise Refused(f'the section {group["title"]} holds: ' + ', '.join(held) + '\n  this command removes a section with no item')
    below = [g['title'] for g in groups if g is not group and inside(g)]
    if below:
        raise Refused(f'the section {group["title"]} holds a section: ' + ', '.join(below) + '\n  remove each one first')
    span = lines[first - 1:last]
    old = [row.strip()[:60] for _, row in st.lines_outside_fences('\n'.join(span)) if st.trace_comment(row) is not None]
    if old:
        raise Refused(f'the section {group["title"]} holds an old text block: {old[0]}\n  remove it first with: dev-spec remove ID')
    retired = re.findall(r'<!--\s*retired:\s*(\S+)\s*-->', '\n'.join(span))
    rest = lines[:first - 1] + lines[last:]
    rest = [row for n, row in enumerate(rest) if row.strip() or n == 0 or rest[n - 1].strip()]
    while rest and not rest[-1].strip():
        rest.pop()
    gone = repo['layout'] == 'sections' and not rest
    return {rel: None if gone else rest}, '\n'.join(span).strip('\n'), group, retired


def change_move(tree, repo, item, section):
    """An SDD item goes to the end of a different section. Its identifier stays: it names the area, not the section."""
    target = next((g for g in repo['groups'] if g['key'] == 'section/' + section), None)
    if target is None:
        raise Refused(f'{section} is no section of the SDD')
    if target['key'] == item['group']:
        raise Refused(f'{item["id"]} is in section {section} already')
    files = {item['file']: list(repo['files'][item['file']])}
    lines = files[item['file']]
    end = item['end']
    while end < len(lines) and not lines[end].strip():
        end += 1
    block = lines[item['line'] - 1:item['end']]
    while block and not block[-1].strip():
        block.pop()
    inside = [s for s in repo['sdd'].values() if s['group'] == target['key']]
    after = max([s['end'] for s in inside] + [target['end']])
    if target['file'] == item['file']:
        if after >= end:   # the target is below the item: put the block in first, then take the old lines out
            lines[after:after] = [''] + block + ['']
            del lines[item['line'] - 1:end]
        else:
            del lines[item['line'] - 1:end]
            lines[after:after] = [''] + block + ['']
    else:
        del lines[item['line'] - 1:end]
        other = files.setdefault(target['file'], list(repo['files'][target['file']]))
        while after > 0 and not other[after - 1].strip():
            after -= 1
        other[after:after] = [''] + block + ['']
    for name, rows in files.items():   # no two empty lines in sequence
        files[name] = [row for n, row in enumerate(rows) if row.strip() or n == 0 or rows[n - 1].strip()]
    return files


def base_ref(entry, root):
    """The base branch of a repository as a ref of this checkout: the record's `git.base`, else the source of the repository."""
    base = (entry.get('git') or {}).get('base')
    names = ([f'origin/{base}', base] if base else []) + ([entry['source']] if entry.get('source') not in (None, '', 'checkout') else [])
    for name in names:
        if name.startswith('origin/'):   # a base that is not fetched does not show an item that was merged a moment ago
            try:
                subprocess.run(['git', '-C', root, 'fetch', '-q', 'origin', name[7:]], capture_output=True, timeout=30)
            except subprocess.TimeoutExpired:
                pass
        if subprocess.run(['git', '-C', root, 'rev-parse', '--verify', '--quiet', name + '^{commit}'], capture_output=True).returncode == 0:
            return name
    raise Refused('the record of the project names no base branch that this checkout has (git.base, or the source of the repository)\n'
                  '  renumber needs it: an identifier that the base branch holds does not change')


def change_renumber(tree, repo, item, new):
    """A TDD item gets a different number of its section. Each file of the specification that names the item changes.
    Returns (files, the other tracked files that name the item)."""
    old, root = item['id'], repo['spec_root']
    if not re.fullmatch(r'TDD-\d+(\.\d+)+', new) or old.rsplit('.', 1)[0] != new.rsplit('.', 1)[0] or old == new:
        raise Refused(f'the identifier of a TDD item holds its section; give a number of the same section ({old.rsplit(".", 1)[0]}.N)')
    below = [t for t in repo['tdd'] if t.startswith(old + '.')]
    if below:
        raise Refused(f'{old} holds items below it: ' + ', '.join(below))
    section, number = old[4:].rsplit('.', 1)[0], int(new.rsplit('.', 1)[1])
    if new in repo['tdd'] or number in numbers_used(tree, repo, re.compile(rf'TDD-{re.escape(section)}\.(\d+)(?![\d.])')):
        raise Refused(f'{new} is used: an item, a retired comment or a removed section holds that number')
    entry = next(c for c in tree['conf']['repositories'] if c['name'] == repo['name'])
    base = base_ref(entry, root)
    held = subprocess.run(['git', '-C', root, 'grep', '-q', '-E', '-e', '<!-- id: ' + old.replace('.', '\\.') + '( |\\|)', base, '--', '*.md'],
                          capture_output=True).returncode == 0
    if held:
        raise Refused(f'{old} is on the base branch ({base}): an identifier that is merged does not change')
    name = re.compile(r'(?<![\w-])' + re.escape(old) + r'(?!\d|\.\d)')
    files = {rel: [name.sub(new, row) for row in lines] for rel, lines in repo['files'].items() if any(name.search(row) for row in lines)}
    found = subprocess.run(['git', '-C', root, 'grep', '-n', '-I', '-F', '-e', old, '--', '.'], capture_output=True, text=True).stdout
    others = [':'.join(row.split(':', 2)[:2]) for row in found.splitlines()
              if row.split(':', 1)[0] not in repo['files'] and name.search(row.split(':', 2)[-1])]
    return files, others


def sdd_files(repo):
    return sorted({g['file'] for g in repo['groups'] if g.get('file')})


def group_at(repo, rel, line):
    inside = [g for g in repo['groups'] if g.get('file') == rel and g['line'] <= line]
    return max(inside, key=lambda g: g['line']) if inside else None


def loose_block(repo, item_id):
    """An old text block of the SDD: a trace comment whose identifier is no item, and the text below it.
    Returns (file, first line, last line, section), or None."""
    wanted = st.bare(item_id)
    if wanted in repo['sdd'] or wanted in repo['tdd']:
        return None
    for rel in sdd_files(repo):
        rows = list(st.lines_outside_fences('\n'.join(repo['files'][rel])))
        for index, (n, line) in enumerate(rows):
            fields = st.trace_comment(line)
            if fields is None or st.bare(fields.get('id', '')) != wanted or fields['id'].startswith('SYS-'):
                continue
            last = len(repo['files'][rel])
            for m, later in rows[index + 1:]:
                if st.trace_comment(later) is not None or st.SDD_LINE.match(later) or st.SDD_STOP.match(later) \
                        or later.startswith('<!-- retired:'):
                    last = m - 1
                    break
            return rel, n, last, group_at(repo, rel, n)
    return None


def change_loose(tree, repo, item_id, block):
    """Take the old block out, and its identifier out of each TDD item that names it."""
    rel, first, last, _ = block
    wanted = st.bare(item_id)
    named = [t['id'] for t in repo['tdd'].values() if wanted in t['implements']]
    files = change_links(tree, repo, {t: ('implements', lambda v: [x for x in v if st.bare(x) != wanted]) for t in named})
    lines = files.setdefault(rel, list(repo['files'][rel]))
    text = '\n'.join(lines[first - 1:last])
    while last < len(lines) and not lines[last].strip():
        last += 1
    del lines[first - 1:last]
    return files, text, named


def free_span(repo, level, section):
    """The lines of a section that are outside its items: (file, first index, end index, section).
    With no section: the lines between the title of the one file and its first section."""
    groups = repo['groups'] if level == 'SDD' else repo['tdd_groups']
    if section is None:
        if repo['layout'] != 'single':
            raise Refused('give --section: only the single layout has a text before the first section')
        inside = [g for g in groups if g.get('file')]
        if len({g['file'] for g in inside}) != 1:
            raise Refused(f'the {level} has no file with a section')
        return inside[0]['file'], 1, min(g['line'] for g in inside) - 1, None
    group = next((g for g in groups if g['key'] == 'section/' + section), None)
    if group is None:
        raise Refused(f'{section} is no section of the {level}')
    lines, first = repo['files'][group['file']], group['line']
    while first < len(lines) and re.match(r'\s*<!--\s*(section|spec-lock):', lines[first]):
        first += 1   # the owner comment and the lock comment stay
    return group['file'], first, max(first, group['end']), group


def change_text(repo, level, section, raw):
    rel, first, end, group = free_span(repo, level, section)
    lines = list(repo['files'][rel])
    stop = st.SDD_STOP if level == 'SDD' else st.TDD_STOP
    for name, rows in (('the text of today', lines[first:end]), ('the new text', raw.splitlines())):
        for _, row in st.lines_outside_fences('\n'.join(rows)):
            if st.SDD_LINE.match(row) or st.trace_comment(row) is not None or stop.match(row) or re.match(r'\s*<!--\s*(section|retired):', row):
                raise Refused(f'{name} holds an item, a trace comment or a heading: {row.strip()[:60]}\n'
                              '  this command changes only text that is outside each item')
    if re.search(r'\bMUST\b', st.outside_code('\n'.join(r for _, r in st.lines_outside_fences(raw)))):
        raise Refused('SP-09: MUST is only in the requirement sentence of an SDD item')
    new = [r.rstrip() for r in raw.strip('\n').splitlines()]
    lines[first:end] = ([''] + new + [''] if new else [''])
    files = {rel: [row for n, row in enumerate(lines) if row.strip() or n == 0 or lines[n - 1].strip()]}
    return files, group


def read_text(source):
    if source is None:
        raise Refused('give --text FILE, or --text - to read the text from the input')
    if source != '-' and not os.path.isfile(source):
        raise Refused(f'{source}: no such text file')
    return sys.stdin.read() if source == '-' else st.read(source)


# ---------- propose and confirm ----------

def sha(lines):
    return hashlib.sha256(('\n'.join(lines) + '\n').encode()).hexdigest()


def write_lines(path, lines):
    """Write the lines of a file. With no lines, the file leaves: a section file of a removed section."""
    if lines is None:
        path.unlink()
    else:
        path.write_text('\n'.join(lines).rstrip('\n') + '\n', encoding='utf-8')


def trial(conf, root, files, check):
    """Write the files, compile, run `check(tree)`, and put the old content back. Returns the tree after the change."""
    before = {rel: st.read(os.path.join(root, rel)) for rel in files}
    try:
        for rel, lines in files.items():
            write_lines(Path(root, rel), lines)
        tree = st.build(conf, fetch=False)
        check(tree)
        return tree
    finally:
        for rel, text in before.items():
            Path(root, rel).write_text(text, encoding='utf-8')


def plain(faults):
    return {re.sub(r':\d+:', ':', f) for f in faults}


def propose(conf, args):
    tree = st.build(conf, fetch=False)
    repos = [r for r in tree['repos'].values() if r['layout'] in ('single', 'sections')]
    block, extra, retire, retired, note = None, {}, False, [], ''
    whole = args.command == 'remove' and args.id is None   # a section, not an item
    if args.command == 'remove' and bool(args.id) == bool(args.level and args.section):
        raise Refused('give one identifier, or --level sdd|tdd with --section S for a section that holds no item')
    if args.command == 'remove' and not whole:
        block = next(((r, b) for r in repos if (b := loose_block(r, args.id))), None)
    if block:
        repo, block = block
    elif args.command in ('set', 'remove', 'move', 'renumber') and not whole:
        repo, level, item = locate(tree, args.id)
        retire = level == 'SYS' and args.command == 'remove'
        if retire:
            repo = tree['repos'].get(item['chapter'][0]) if item.get('chapter') else None
            if repo is None or repo['layout'] == 'domains':
                raise Refused(f'{args.id}: this command removes a system requirement of the first chapter of an SDD in the single or the '
                              'sections layout; a top document is the owner\'s to change')
        elif level == 'SYS' or repo is None or repo['layout'] == 'domains':
            raise Refused(f'{args.id}: the write commands change an SDD or a TDD item in the single or the sections layout')
    else:
        if len(repos) != 1:
            raise Refused('this command needs one repository with the single or the sections layout')
        repo = repos[0]
    new_id = None
    if block:
        files, text, named = change_loose(tree, repo, args.id, block)
        extra = {t: 'names the old block' for t in named}
        focus = ('SDD', {'id': None, 'tdd': [], 'group': block[3]['key'] if block[3] else None, 'sys': []})
        target = ('' if args.id.startswith('SDD-') else 'SDD-') + args.id
    elif args.command == 'text':
        level = args.level.upper()
        text = read_text(args.text)
        files, group = change_text(repo, level, args.section, text)
        if level == 'SDD':
            focus = ('SDD', {'id': None, 'tdd': [], 'group': group['key'] if group else None, 'sys': []})
        else:
            focus = ('TDD', {'id': f'TDD-{args.section or 0}.0', 'implements': [], 'paths': [], 'file': None})
        target = f'text:{args.level}:{args.section or "front"}'
    elif args.command == 'set':
        files, text = change_set(tree, repo, level, item, args)
        focus, target = (level, item), item['id']
    elif whole:
        level = args.level.upper()
        files, text, group, retired = change_section(tree, repo, level, args.section)
        if level == 'SDD':
            focus = ('SDD', {'id': None, 'tdd': [], 'group': group['key'], 'sys': []})
        else:
            focus = ('TDD', {'id': f'TDD-{args.section}.0', 'implements': [], 'paths': [], 'file': None})
        target = f'section:{args.level}:{args.section}'
        gone = [rel for rel, lines in files.items() if lines is None]
        note = f'The section {group["title"]} leaves {group["file"]}' + ('; the file leaves also' if gone else '') + '. Its text of today:\n\n' + text + '\n'
    elif retire:
        files, text = change_retire(tree, repo, item)
        focus, target = ('SDD', {'id': item['id'], 'tdd': [], 'group': None, 'sys': []}), item['id']
        note = f'The system requirement leaves {item["file"]}. Its text of today:\n\n' + text + '\n'
    elif args.command == 'remove':
        files, text = change_remove(tree, repo, level, item), st_text(repo, item)
        focus, target = (level, item), item['id']
    elif args.command == 'add':
        files, new_id, text = change_add(tree, repo, args)
        focus, target = (args.level.upper(), {'id': new_id, 'tdd': [], 'implements': [st.bare(x) for x in st.split_list(args.implements or '')],
                                              'group': 'section/' + args.section, 'paths': [], 'file': None}), new_id
    elif args.command in ('link', 'unlink'):
        tdd, sdd = repo['tdd'].get(args.tdd), repo['sdd'].get(st.bare(args.sdd))
        if tdd is None or sdd is None:
            raise Refused('give one TDD item and one SDD item that exist')
        on = args.command == 'link'
        files = change_links(tree, repo, {
            tdd['id']: ('implements', lambda v: [x for x in v if st.bare(x) != sdd['id']] + (['SDD-' + sdd['id']] if on else [])),
            sdd['id']: ('tdd', lambda v: [x for x in v if x != tdd['id']] + ([tdd['id']] if on else []))})
        text, focus, target = st_text(repo, tdd) + ' ' + st_text(repo, sdd), ('TDD', tdd), f'{tdd["id"]} {sdd["id"]}'
    elif args.command in ('bind', 'unbind'):
        tdd = repo['tdd'].get(args.tdd)
        if tdd is None or not (args.code or args.test) or (args.code and args.test):
            raise Refused('give one TDD item that exists and one of --code PATH or --test PATH')
        field, value = ('code', args.code) if args.code else ('tests', args.test)
        if args.command == 'bind' and not os.path.exists(os.path.join(repo['root'], value.partition('#')[0])):
            raise Refused(f'{value.partition("#")[0]} does not exist in this checkout')
        on = args.command == 'bind'
        files = change_links(tree, repo, {tdd['id']: (field, lambda v: [x for x in v if x != value] + ([value] if on else []))})
        text, focus, target = st_text(repo, tdd), ('TDD', tdd), f'{tdd["id"]} {value}'
    elif args.command == 'renumber':
        if level != 'TDD':
            raise Refused('renumber takes a TDD item; the identifier of an SDD item names its area and stays')
        files, others = change_renumber(tree, repo, item, args.new)
        text, focus, target = st_text(repo, item), ('TDD', item), f'{item["id"]} {args.new}'
        if others:
            note = 'These files are outside the specification and name the item. The command does not change them:\n  ' + '\n  '.join(others[:20]) + '\n'
    elif args.command == 'move':
        _, level, item = locate(tree, args.id)
        if level != 'SDD':
            raise Refused('move takes an SDD item; the identifier of a TDD item holds its section and does not change')
        files, text = change_move(tree, repo, item, args.section), st_text(repo, item)
        focus, target = ('SDD', dict(item, group='section/' + args.section)), item['id']
    elif st.bare(args.section) in repo['sdd']:   # own, for one item: one more owner beside the owner of its section (SDD-SP-04)
        item = repo['sdd'][st.bare(args.section)]
        if args.sys != 'none' and args.sys not in {r['id'] for r in tree['reqs']}:
            raise Refused(f'{args.sys} is no system requirement; give one that exists, or none to remove each owner of the item')
        lines = list(repo['files'][item['file']])
        at, fields = trace_at(lines, item)
        owners = [] if args.sys == 'none' else [x for x in st.split_list(fields.get('sys', '')) if x != args.sys] + [args.sys]
        fields.pop('sys', None)
        if owners:
            fields['sys'] = ', '.join(owners)
        drop_status(fields)
        lines[at] = trace_line(fields)
        files, text = {item['file']: lines}, st_text(repo, item)
        focus, target = ('SDD', item), f'{item["id"]} {args.sys}'
        extra = {name: 'the system requirement that it gets' for name in owners}
    else:   # own, for a section
        group = next((g for g in repo['groups'] if g['key'] == 'section/' + args.section), None)
        if group is None or args.sys not in {r['id'] for r in tree['reqs']}:
            raise Refused('give one section of the SDD and one system requirement that exist')
        lines = list(repo['files'][group['file']])
        comment = f'<!-- section: SDD-{args.section} | sys: {args.sys} -->'
        at = next((n for n in range(group['line'], min(group['line'] + 3, len(lines))) if st.SYS_COMMENT.match(lines[n])), None)
        if at is None:
            lines.insert(group['line'], comment)
        else:
            lines[at] = comment
        files, text = {group['file']: lines}, group['title']
        focus, target = ('SDD', {'id': None, 'tdd': [], 'group': group['key'], 'sys': [args.sys]}), f'{args.section} {args.sys}'

    old_faults = plain(tree['faults'])

    def check(after):
        added = plain(after['faults']) - old_faults
        if added:
            raise Refused('SW-07: the change adds a fault of the tree:\n  ' + '\n  '.join(sorted(added)))
        if args.command in ('set', 'add') and focus[0] == 'SDD':
            new = after['repos'][repo['name']]['sdd'].get(target)
            if new is None:
                raise Refused('SW-06: the text is no SDD item in the item form')
            if new['form']:
                raise Refused('SW-06: the item breaks the item form:\n  ' + '\n  '.join(f'{rule}: {reason}' for rule, reason in new['form']))

    trial(conf, repo['spec_root'], files, check)
    # A change of the gap only changes no meaning: it has no related item.
    affected = {} if args.command == 'set' and args.text is None else related(tree, repo, focus[0], focus[1], text)
    for i, reason in extra.items():
        affected.setdefault(i, []).append(reason)
    folder = state(conf)
    (folder / 'proposals').mkdir(exist_ok=True)
    number = max([int(p.stem) for p in (folder / 'proposals').iterdir() if p.stem.isdigit()] + [0]) + 1
    (folder / 'proposals' / f'{number}.json').write_text(json.dumps({
        'number': number, 'command': args.command, 'target': target, 'root': repo['spec_root'], 'repository': repo['name'],
        'before': {rel: sha(repo['files'][rel]) for rel in files}, 'files': files, 'related': affected, 'retired': retired}, indent=1))
    print(f'Proposal {number}: {args.command} {target}. Nothing is written yet.')
    if note:
        print(note)
    if not affected:
        print(f'No related item. Write the change with: dev-spec confirm {number}')
        return 3
    print(f'Read each related item. Then answer for each one: same (it still agrees), change (it must change also), conflict (the two contradict).\n')
    for i, reasons in affected.items():
        other_repo, other_level, other = locate(tree, i)
        print(f'--- {i}  ({"; ".join(reasons)})')
        print(text_of(other_repo or repo, other_level, other))
        print()
    print(f'dev-spec confirm {number} ' + ' '.join(f'{i}=same' for i in affected))
    return 3


def open_files(conf, root):
    """(the file of the open items of this checkout, the one file of the release before, which held each checkout)."""
    folder = state(conf)
    name = hashlib.sha256(os.path.realpath(root).encode()).hexdigest()[:16] + '.json'
    return folder / 'open' / name, folder / 'open.json'


def read_open(conf, root):
    """{item: proposal number} for this checkout. A session in a second worktree has its own list."""
    out = {}
    for path in reversed(open_files(conf, root)):
        if path.is_file():
            out.update(json.loads(path.read_text() or '{}'))
    return out


@contextlib.contextmanager
def locked(conf):
    """One write command at a time for each project: the proposal numbers and the records are shared by each session."""
    with open(state(conf) / 'lock', 'w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def spec_home(conf, here):
    """The folder whose specification a command of this place works on: the side folder of a ghost project when the
    command runs in its checkout or in that side folder, else the checkout of the command."""
    common = st.git(here, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    for repo in conf['repositories']:
        if repo.get('spec_root') and common and common in (
                st.git(repo['checkout'], 'rev-parse', '--path-format=absolute', '--git-common-dir'),
                st.git(repo['spec_root'], 'rev-parse', '--path-format=absolute', '--git-common-dir')):
            return repo['spec_root']
    return here


def st_text(repo, item):
    return '\n'.join(repo['files'][item['file']][item['line'] - 1:item['end']])


def confirm(conf, args):
    folder = state(conf)
    path = folder / 'proposals' / f'{args.number}.json'
    if not path.is_file():
        raise Refused(f'there is no proposal {args.number}')
    proposal = json.loads(path.read_text())
    answers = {}
    for pair in args.answers:
        i, _, answer = pair.partition('=')
        if answer not in ANSWERS:
            raise Refused(f'{pair}: the answer is one of {", ".join(ANSWERS)}')
        answers[i] = answer
    missing = [i for i in proposal['related'] if i not in answers]
    if missing:
        raise Refused('SW-04: no answer for: ' + ', '.join(missing))
    conflicts = [i for i, a in answers.items() if a == 'conflict']
    if conflicts:
        path.rename(path.with_suffix('.conflict'))
        raise Refused(f'SW-04: {proposal["target"]} contradicts {", ".join(conflicts)}. Nothing is written. '
                      'Write one question for the owner with the two texts.')
    root = proposal['root']
    for rel, digest in proposal['before'].items():
        if sha(st.read(os.path.join(root, rel)).splitlines()) != digest:
            raise Refused(f'{rel} changed after the proposal; propose the change again')
    tree = st.build(conf, fetch=False)
    old_faults = plain(tree['faults'])
    kept = {rel: st.read(os.path.join(root, rel)) for rel in proposal['files']}
    for rel, lines in proposal['files'].items():
        write_lines(Path(root, rel), lines)
    after = st.build(conf, fetch=False)
    added = plain(after['faults']) - old_faults
    if added:   # the trial of the proposal passed, so this is a change of a different file in between
        for rel, text in kept.items():
            Path(root, rel).write_text(text, encoding='utf-8')
        raise Refused('SW-07: the change adds a fault; the files are put back:\n  ' + '\n  '.join(sorted(added)))
    own_file, old_file = open_files(conf, root)
    opened = json.loads(own_file.read_text()) if own_file.is_file() else {}
    before = json.loads(old_file.read_text() or '{}') if old_file.is_file() else {}
    closed = set(proposal['target'].split()) | {i for i, answer in answers.items() if answer == 'same'}
    for i in closed:
        opened.pop(i, None)
    for i, answer in answers.items():
        if answer == 'change':
            opened[i] = proposal['number']
    own_file.parent.mkdir(exist_ok=True)
    own_file.write_text(json.dumps(opened, indent=1, sort_keys=True))
    if closed & set(before):
        old_file.write_text(json.dumps({i: n for i, n in before.items() if i not in closed}, indent=1, sort_keys=True))
    opened = read_open(conf, root)
    with open(folder / 'journal.jsonl', 'a', encoding='utf-8') as journal:
        journal.write(json.dumps({'number': proposal['number'], 'command': proposal['command'], 'target': proposal['target'],
                                  'answers': answers, 'head': st.git(root, 'rev-parse', 'HEAD'),
                                  'retired': proposal.get('retired', []),
                                  'files': {rel: 'deleted' if lines is None else file_sha(os.path.join(root, rel))
                                            for rel, lines in proposal['files'].items()}}, sort_keys=True) + '\n')
    path.rename(path.with_suffix('.done'))
    print(f'Written: {proposal["command"]} {proposal["target"]} ({", ".join(proposal["files"])}). The tree has no new fault.')
    if opened:
        print('Open items that must change also: ' + ', '.join(sorted(opened)) + '  (dev-spec open)')
    return 0


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def spec_paths(conf, top):
    """The paths of the system requirements, the SDD and the TDD of the repository of this checkout, relative to it."""
    common = st.git(top, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    out = []
    for repo in conf['repositories']:
        home = repo.get('spec_root') or repo['checkout']   # the specification of a ghost project is in its side folder only
        if repo['layout'] != 'none' and st.git(home, 'rev-parse', '--path-format=absolute', '--git-common-dir') == common:
            out += [p for p in (repo['sdd'], repo['tdd']) if p]
            if conf['top'] and conf['top'].get('repository') == repo['name']:
                out.append(conf['top']['path'])
    return sorted(set(out))


def is_spec(rel, paths):
    return rel.endswith('.md') and any(rel == p or rel.startswith(p.rstrip('/') + '/') for p in paths)


def recorded(conf):
    """{relative file: the hashes that a command or an accept recorded}."""
    out = collections.defaultdict(set)
    journal = state(conf) / 'journal.jsonl'
    for line in st.read(journal).splitlines() if journal.is_file() else []:
        for rel, digest in json.loads(line).get('files', {}).items():
            out[rel].add(digest)
    return out


def staged(conf, top):
    """The commit hook: refuse specification content that no command recorded, and a commit with an open item."""
    if not conf['control']:
        return 0
    paths, known, problems = spec_paths(conf, top), recorded(conf), []
    names = subprocess.run(['git', '-C', top, 'diff', '--cached', '--no-renames', '--name-status'], capture_output=True, text=True).stdout
    touched = False
    for row in names.splitlines():
        status, _, rel = row.partition('\t')
        if not is_spec(rel, paths):
            continue
        touched = True
        if status.startswith('D'):
            digest = 'deleted'
        else:
            blob = subprocess.run(['git', '-C', top, 'show', f':{rel}'], capture_output=True).stdout
            digest = hashlib.sha256(blob).hexdigest()
        if digest not in known.get(rel, ()):
            problems.append(f'{rel}: this content was not written by a dev-spec command')
    still = read_open(conf, top)
    if touched and still:
        problems.append('open items that must change also: ' + ', '.join(sorted(still)) + ' (dev-spec open)')
    for problem in problems:
        print(f'dev-spec: {problem}', file=sys.stderr)
    if problems:
        print('dev-spec: change a specification file with dev-spec set, add, remove, link, bind, own, move, renumber or text. '
              'The owner records a hand edit with: dev-spec accept (in a terminal).', file=sys.stderr)
    return 1 if problems else 0


def accept(conf, top):
    """The owner's hand edit: record the present content, in a terminal only, after the form and tree checks (SDD-SW-13)."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise Refused('accept is the owner\'s own act and runs in a terminal, never from an agent')
    paths = spec_paths(conf, top)
    names = subprocess.run(['git', '-C', top, 'status', '--porcelain', '--no-renames', '--untracked-files=all'], capture_output=True, text=True).stdout
    changed = {row[3:]: row[:2] for row in names.splitlines() if is_spec(row[3:], paths)}
    if not changed:
        print('No specification file differs from the last commit.')
        return 0
    tree = st.build(conf, fetch=False)
    problems = [f for f in tree['faults'] if f.split(':')[0] in changed]
    for repo in tree['repos'].values():
        touched = st.touched_lines(repo['spec_root'], 'HEAD', sorted({s['file'] for s in repo['sdd'].values()}))
        for s in repo['sdd'].values():
            new_file = changed.get(s['file'], '').strip() in ('??', 'A')
            if new_file or any(first <= s['end'] and last >= s['line'] for first, last in touched.get(s['file'], [])):
                problems += [f'{s["file"]}:{s["line"]}: {s["id"]}: {rule}: {reason}' for rule, reason in s['form']]
    if problems:
        raise Refused('the hand edit breaks the form or the tree:\n  ' + '\n  '.join(problems))
    files = {rel: ('deleted' if 'D' in status else file_sha(os.path.join(top, rel))) for rel, status in changed.items()}
    with open(state(conf) / 'journal.jsonl', 'a', encoding='utf-8') as journal:
        journal.write(json.dumps({'command': 'accept', 'target': 'the owner\'s hand edit', 'head': st.git(top, 'rev-parse', 'HEAD'),
                                  'files': files}, sort_keys=True) + '\n')
    print('Accepted as the owner\'s edit: ' + ', '.join(sorted(files)))
    return 0


def open_items(conf, root):
    opened = read_open(conf, root)
    for i, number in sorted(opened.items()):
        print(f'{i}  must change also (answer of proposal {number})')
    print(f'{len(opened)} open items', file=sys.stderr)
    return 1 if opened else 0


# ---------- the command ----------

def main(argv):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--config', default=argparse.SUPPRESS, help='the tree config; the default is the config of the repository of this folder')
    common.add_argument('--root', default=argparse.SUPPRESS, help='the checkout to work on; the default is this folder')
    ap = argparse.ArgumentParser(prog='dev-spec', description='Explain and change a specification through commands.', parents=[common])
    sub = ap.add_subparsers(dest='command', required=True)
    settings = argparse.ArgumentParser(add_help=False)   # a read command works on a folder that no record holds (SDD-PJ-09)
    st.settings_arguments(settings)
    sub.add_parser('find', parents=[common, settings]).add_argument('query')
    sub.add_parser('why', parents=[common, settings]).add_argument('target')
    sub.add_parser('open', parents=[common])
    p = sub.add_parser('set', parents=[common])
    p.add_argument('id')
    p.add_argument('--text')
    p.add_argument('--gap')
    p = sub.add_parser('add', parents=[common])
    p.add_argument('--level', choices=('sdd', 'tdd'), required=True)
    p.add_argument('--section', required=True)
    p.add_argument('--area')
    p.add_argument('--text')
    p.add_argument('--implements')
    p = sub.add_parser('remove', parents=[common], description='An item, an old text block, a system requirement that nothing names, '
                                                               'or a section that holds no item.')
    p.add_argument('id', nargs='?')
    p.add_argument('--level', choices=('sdd', 'tdd'), help='with --section: the level of the section')
    p.add_argument('--section', help='a section that holds no item')
    for name in ('link', 'unlink'):
        p = sub.add_parser(name, parents=[common])
        p.add_argument('tdd')
        p.add_argument('sdd')
    for name in ('bind', 'unbind'):
        p = sub.add_parser(name, parents=[common])
        p.add_argument('tdd')
        p.add_argument('--code')
        p.add_argument('--test')
    p = sub.add_parser('own', parents=[common], description='The owner of a section, or one more owner for one SDD item.')
    p.add_argument('section', help='a section of the SDD (2.1), or an SDD item (CX-02)')
    p.add_argument('sys', help='a system requirement; for an item also: none')
    p = sub.add_parser('text', parents=[common], description='The text of a section that is outside its items.')
    p.add_argument('--level', choices=('sdd', 'tdd'), required=True)
    p.add_argument('--section', help='with no section: the text before the first section (single layout)')
    p.add_argument('--text')
    p = sub.add_parser('renumber', parents=[common], description='A free number of the same section for a TDD item that the base branch does not hold.')
    p.add_argument('id', help='the TDD item')
    p.add_argument('new', help='the new identifier, in the same section')
    p = sub.add_parser('move', parents=[common])
    p.add_argument('id')
    p.add_argument('--section', required=True)
    sub.add_parser('accept', parents=[common])
    sub.add_parser('staged', parents=[common])
    p = sub.add_parser('confirm', parents=[common])
    p.add_argument('number', type=int)
    p.add_argument('answers', nargs='*')
    args = ap.parse_args(argv)
    args.config, args.root = getattr(args, 'config', None), getattr(args, 'root', None)
    try:
        if args.command == 'staged':   # the commit hook: a repository with no project, or with the control off, passes
            top = st.git(Path(args.root or os.getcwd()), 'rev-parse', '--show-toplevel')
            try:
                return staged(st.load_config(args.config or config_of(top)), top) if top else 0
            except (Refused, st.ConfigError):
                return 0
        conf = context(args)
        if args.command == 'accept':
            return accept(conf, st.git(Path(args.root or os.getcwd()), 'rev-parse', '--show-toplevel'))
        here = st.git(Path(args.root or os.getcwd()), 'rev-parse', '--show-toplevel') or os.getcwd()
        if args.command == 'open':
            return open_items(conf, spec_home(conf, here))
        if args.command == 'confirm' or args.command in WRITE:
            with locked(conf):
                return confirm(conf, args) if args.command == 'confirm' else propose(conf, args)
        tree = st.build(conf, fetch=False)
        return find(tree, args.query) if args.command == 'find' else why(tree, args.target)
    except Refused as error:
        print(f'dev-spec: refused: {error}', file=sys.stderr)
        return 1
    except st.ConfigError as error:
        for line in error.problems:
            print(f'dev-spec: {line}', file=sys.stderr)
        return 2
