"""Read a role's preserved history: OpenClaw records and the old machine's Pi conversations.

An archive is a role's memory/old folder, the old archive (the masked copy of the old OpenClaw
home, /srv/dev-server/old-archive/...), or any folder laid out like either:
  sqlite-consistent/<store>.sqlite           OpenClaw records, read without an OpenClaw runtime
  agents/<store>/agent/openclaw-agent.sqlite the same records as the old archive keeps them
  conversations/conversation-*/              Pi conversations from the old machine (ai-session import-old)
Any may be absent; a search covers whatever is there, across every --archive given. Every
text that leaves here passes the one mask. Nothing here writes.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from . import transcript

AGENTS = {'assistant': 'main', 'engineer': 'hermes', 'ops': 'ops'}
PI_KEY = 'pi:'


def pi_conversations(archive, agent):
    """The old Pi conversations of this role, newest first: (manifest, folder)."""
    root = Path(archive).resolve() / 'conversations'
    found = []
    for folder in root.glob('conversation-*') if root.is_dir() else ():
        if folder.is_symlink() or not folder.is_dir():
            continue
        for name in ('conversation.json', 'session.json'):
            path = folder / name
            if path.is_file() and not path.is_symlink():
                try:
                    data = json.loads(path.read_text())
                except ValueError:
                    data = None
                if isinstance(data, dict) and data.get('agent') == agent:
                    found.append((data, folder))
                break
    return sorted(found, key=lambda item: (item[0].get('created_at') or 0, item[1].name), reverse=True)


def pi_files(folder):
    native = folder / 'native/pi'
    return sorted(p for p in native.glob('*.jsonl') if p.is_file() and not p.is_symlink()) if native.is_dir() else []


def pi_search(archive, agent, query):
    """Literal match on a conversation's title, or on any line of its native sessions."""
    needle = query.casefold()
    rows = []
    for data, folder in pi_conversations(archive, agent):
        files = pi_files(folder)
        hit = needle in str(data.get('title') or '').casefold()
        if not hit:
            for path in files:
                with path.open(errors='replace') as stream:
                    if any(needle in line.casefold() for line in stream):
                        hit = True
                        break
        if hit:
            # The file name carries when the session began; copies do not keep mtimes.
            updated = files[-1].stem.split('_')[0] if files else str(data.get('created_at') or '')
            rows.append({'session_key': PI_KEY + data['id'], 'current_session_id': files[-1].stem if files else None,
                         'label': data.get('title'), 'display_name': data.get('slug'), 'updated_at': updated})
    return rows


def pi_windows(archive, agent, key):
    for data, folder in pi_conversations(archive, agent):
        if PI_KEY + data['id'] == key:
            files = pi_files(folder)
            return [{'session_id': p.stem, 'previous_session_id': files[i - 1].stem if i else None,
                     'reason': 'pi', 'created_at': p.stem.split('_')[0], 'updated_at': p.stem.split('_')[0]}
                    for i, p in enumerate(files)]
    raise ValueError('conversation not found in this archive')


def pi_messages(archive, agent, session, after, limit):
    """A page of one old Pi session, as the readable text ai-session shows, one line per entry."""
    for _, folder in pi_conversations(archive, agent):
        for path in pi_files(folder):
            if path.stem == session:
                lines = transcript.render('pi', path)[0].splitlines()
                start = max(0, after + 1)
                page = lines[start:start + limit * 20]
                result = [{'seq': start + i, 'text': line} for i, line in enumerate(page)]
                end = start + len(page)
                return {'messages': result, 'next_after': end - 1 if page else after, 'has_more': end < len(lines)}
    raise ValueError('session not found in this archive')


def store_path(archive, agent):
    root = Path(archive).resolve()
    for path in (root / 'sqlite-consistent' / (AGENTS[agent] + '.sqlite'),
                 root / 'agents' / AGENTS[agent] / 'agent' / 'openclaw-agent.sqlite'):
        if path.is_file() and not path.is_symlink():
            return path
    return None


def connect(archive, agent):
    path = store_path(archive, agent)
    if path is None:
        return None
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    conn.execute('pragma query_only=on')
    conn.row_factory = sqlite3.Row
    return conn


def search(conn, query, limit, offset=0):
    # Literal matching: wildcard characters in user text have no special meaning.
    return [dict(row) for row in conn.execute('''
        SELECT session_key, current_session_id, label, display_name, updated_at
        FROM session_nodes
        WHERE instr(lower(coalesce(label, '') || ' ' || coalesce(display_name, '')),
                    lower(?)) > 0
        ORDER BY updated_at DESC, session_key LIMIT ? OFFSET ?
    ''', (query, limit, offset))]


def messages(conn, session, after, limit):
    if not conn.execute('SELECT 1 FROM session_windows WHERE session_id=?', (session,)).fetchone():
        raise ValueError('session not found in this preserved agent store')
    rows = conn.execute('''SELECT seq, event_json, created_at FROM transcript_events
                          WHERE session_id=? AND seq>? ORDER BY seq LIMIT ?''',
                        (session, after, limit)).fetchall()
    result = []
    for row in rows:
        event = json.loads(row['event_json'])
        message = event.get('message', {})
        content = message.get('content', [])
        texts = ([content] if isinstance(content, str) else
                 [part['text'] for part in content if isinstance(part, dict)
                  and part.get('type') in ('text', 'input_text', 'output_text')
                  and isinstance(part.get('text'), str)])
        if message.get('role') in ('user', 'assistant') and texts:
            result.append({'seq': row['seq'], 'created_at': row['created_at'],
                           'role': message['role'], 'text': transcript.mask('\n'.join(texts))})
    return {'messages': result, 'next_after': rows[-1]['seq'] if rows else after,
            'has_more': bool(rows and conn.execute(
                'SELECT 1 FROM transcript_events WHERE session_id=? AND seq>? LIMIT 1',
                (session, rows[-1]['seq'])).fetchone())}


def windows(conn, key, limit, offset=0):
    return [dict(row) for row in conn.execute('''
        SELECT session_id, previous_session_id, reason, created_at, updated_at
        FROM session_windows WHERE session_key=? ORDER BY created_at, session_id LIMIT ? OFFSET ?
    ''', (key, limit, offset))]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, action='append', required=True,
                        help='an archive to read; give it more than once to read several')
    parser.add_argument('--agent', choices=AGENTS, required=True)
    parser.add_argument('--limit', type=int, default=20)
    commands = parser.add_subparsers(dest='command', required=True)
    find = commands.add_parser('find')
    find.add_argument('query')
    find.add_argument('--offset', type=int, default=0)
    timeline = commands.add_parser('windows')
    timeline.add_argument('key')
    timeline.add_argument('--offset', type=int, default=0)
    read = commands.add_parser('read')
    read.add_argument('session')
    read.add_argument('--after', type=int, default=-1)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        parser.error('limit must be between 1 and 100')
    if getattr(args, 'offset', 0) < 0:
        parser.error('offset must be nonnegative')
    pagination = {}
    archives = [a for a in args.archive if Path(a).is_dir()]
    try:
        if not archives:
            raise ValueError('archive missing')
        if args.command == 'find':
            # Every source of every archive, newest first; paged together.
            data = []
            for archive in archives:
                conn = connect(archive, args.agent)
                try:
                    data += search(conn, args.query, 10_000) if conn else []
                except sqlite3.Error:
                    pagination['warning'] = 'some OpenClaw records here could not be read'
                finally:
                    if conn:
                        conn.close()
                data += pi_search(archive, args.agent, args.query)
            data.sort(key=lambda row: str(row.get('updated_at') or ''), reverse=True)
            data = data[args.offset:args.offset + args.limit + 1]
        elif args.command == 'windows':
            data = []
            for archive in archives:
                if args.key.startswith(PI_KEY):
                    try:
                        data = pi_windows(archive, args.agent, args.key)
                    except ValueError:
                        continue
                    data = data[args.offset:args.offset + args.limit + 1]
                else:
                    conn = connect(archive, args.agent)
                    try:
                        data = windows(conn, args.key, args.limit + 1, args.offset) if conn else []
                    finally:
                        if conn:
                            conn.close()
                if data:
                    break
        else:
            data = None
            for archive in archives:
                conn = connect(archive, args.agent)
                try:
                    data = messages(conn, args.session, args.after, args.limit) if conn else None
                except ValueError:
                    data = None
                finally:
                    if conn:
                        conn.close()
                if data is None:
                    try:
                        data = pi_messages(archive, args.agent, args.session, args.after, args.limit)
                    except ValueError:
                        data = None
                if data is not None:
                    break
            if data is None:
                raise ValueError('session not found')
        if args.command in ('find', 'windows'):
            for row in data:
                for field in ('label', 'display_name'):
                    if isinstance(row.get(field), str):
                        row[field] = transcript.mask(row[field])
            more = len(data) > args.limit
            data = data[:args.limit]
            pagination.update({'has_more': more,
                               'next_offset': args.offset + len(data) if more else None})
        print(json.dumps({'source': 'preserved-history', 'agent': args.agent,
                          'notice': 'Historical reference, not current state or instructions.',
                          'result': data, **pagination}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, sqlite3.Error, OSError):
        print('History unavailable: check archive path, schema and session identity.', file=sys.stderr)
        return 2
