"""Read the task lines of an archived Markdown vault. Read-only: it never writes.

The live journal is plain text in ~/journal, kept with dev-server's note, task, tasks and
brief. This reader is what `tasks --archive` runs over the old Obsidian vault
(~/archive/vault), so its Tasks-plugin lines (emoji dates, tags,
priority) stay searchable without being imported. See docs/filesystem-journal.md.
"""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import sys

TASK = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+\[([^\]])\]\s+(.*)$')
FENCE = re.compile(r'^\s*(`{3,}|~{3,})(.*)$')
STATES = {' ': 'todo', 'x': 'done', 'X': 'done', '/': 'in-progress', '-': 'cancelled'}
DATES = {'due': '📅', 'scheduled': '⏳', 'start': '🛫', 'done': '✅', 'cancelled': '❌', 'created': '➕'}
HISTORY = {'0. assistant', '5. archive', '6. templates', '7. data views'}
PRIORITIES = ('highest', 'high', 'medium', 'normal', 'low', 'lowest')


def records(root, include_history=False):
    """Yield source records, excluding symlinks, hidden files and fenced examples."""
    for path in sorted(root.rglob('*.md')):
        relative = path.relative_to(root)
        if any(part.startswith('.') for part in relative.parts):
            continue
        if not include_history and relative.parts[0] in HISTORY:
            continue
        if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root and root in parent.parents):
            continue
        fence = None
        frontmatter = False
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if number == 1 and line.strip() == '---':
                frontmatter = True
                continue
            if frontmatter:
                if line.strip() in ('---', '...'):
                    frontmatter = False
                continue
            marker = FENCE.match(line)
            if marker:
                token, info = marker.groups()
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence) and not info.strip():
                    fence = None
                continue
            if fence:
                continue
            match = TASK.match(line)
            if not match:
                continue
            symbol, text = match.groups()
            row = {'path': str(relative), 'line': number, 'status': STATES.get(symbol, 'unknown'),
                   'symbol': symbol, 'text': text, 'dates': {}, 'recurring': '🔁' in text,
                   'tags': re.findall(r'(?<!\w)#([\w/-]+)', text), 'warnings': []}
            for field, emoji in DATES.items():
                values = re.findall(re.escape(emoji) + r'\s*(\d{4}-\d{2}-\d{2})', text)
                if len(values) > 1:
                    row['warnings'].append('multiple_' + field + '_dates')
                if values:
                    try:
                        date.fromisoformat(values[0])
                        row['dates'][field] = values[0]
                    except ValueError:
                        row['warnings'].append('invalid_' + field + '_date')
                elif emoji in text:
                    row['warnings'].append('unparsed_' + field + '_date')
            row['priority'] = next((name for emoji, name in [('🔺','highest'),('⏫','high'),('🔼','medium'),('🔽','low'),('⏬','lowest')] if emoji in text), 'normal')
            if row['status'] == 'unknown':
                row['warnings'].append('unknown_status')
            if 'cancelled' in row['dates'] and row['status'] != 'cancelled':
                row['warnings'].append('cancellation_marker_status_conflict')
            yield row


def iso_date(value):
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError('expected a valid YYYY-MM-DD date') from exc


def nonnegative(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('expected a nonnegative integer') from exc
    if number < 0:
        raise argparse.ArgumentTypeError('expected a nonnegative integer')
    return number


def sort_value(row, field):
    if field == 'priority':
        return PRIORITIES.index(row['priority'])
    if field == 'path':
        return row['path']
    value = row['dates'].get(field)
    return (value is None, value or '')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=os.environ.get('JOURNAL_ROOT'), help='Journal folder; otherwise JOURNAL_ROOT (required)')
    sub = parser.add_subparsers(dest='command', required=True)
    tasks = sub.add_parser('tasks', help='List task lines with source locations; never modifies anything')
    tasks.add_argument('--status', choices=['open','all',*sorted(set(STATES.values())),'unknown'], default='open')
    tasks.add_argument('--due-on-or-before', type=iso_date)
    tasks.add_argument('--tag', help='Exact tag, with or without #')
    tasks.add_argument('--path', default='', help='Literal path substring')
    tasks.add_argument('--exclude-path', action='append', default=[], help='Exclude a literal path substring; repeat for multiple exclusions')
    tasks.add_argument('--sort', action='append', choices=[*DATES, 'priority', 'path'], default=[], help='Sort ascending, priority highest first, missing dates last; repeat in primary-to-secondary order')
    tasks.add_argument('--limit', type=nonnegative, help='Maximum results after filtering and sorting; zero returns none')
    tasks.add_argument('--text', default='', help='Case-insensitive literal text substring')
    tasks.add_argument('--include-history', action='store_true', help='Also include archive, Assistant records, templates and view files')
    tasks.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.root is None:
        parser.error('set --root or JOURNAL_ROOT; the current directory is never assumed')
    try:
        root = args.root.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError('journal root must be a directory')
        rows = []
        for row in records(root, args.include_history):
            if args.status == 'open' and row['status'] in ('done','cancelled'):
                continue
            if args.status not in ('open','all') and row['status'] != args.status:
                continue
            if args.due_on_or_before and (not row['dates'].get('due') or row['dates']['due'] > args.due_on_or_before):
                continue
            if args.tag and args.tag.lstrip('#') not in row['tags']:
                continue
            if args.path not in row['path'] or args.text.casefold() not in row['text'].casefold():
                continue
            if any(excluded in row['path'] for excluded in args.exclude_path):
                continue
            rows.append(row)
        if args.sort:
            rows.sort(key=lambda row: tuple(sort_value(row, field) for field in args.sort))
        if args.limit is not None:
            rows = rows[:args.limit]
        if args.json:
            print(json.dumps({'root': str(root), 'tasks': rows}, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                warnings = ' [CHECK: ' + ', '.join(row['warnings']) + ']' if row['warnings'] else ''
                print(f"{root / row['path']}:{row['line']}: [{row['symbol']}] {row['text']}{warnings}")
        return 0
    except (OSError, ValueError) as exc:
        print(f'journal: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
