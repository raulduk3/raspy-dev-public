"""ai-usage: what each account has left, from the one usage record.

Readings live in /var/lib/dev-server/usage/ACCOUNT.json (registry.paths()['usage']):
Claude from the status line of a running session (ol-status), Codex rate limits and
OpenRouter credits from ol-login-root. A Claude reading is a snapshot with an age; it
updates only while a session runs on that account. A window whose reset has passed is
not current. Unknown reads as unknown, never as zero. Account switches are in
rotations.log in the accounts folder (root's).
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time

from . import registry


def _parse_iso(value):
    """ISO 8601 with a trailing Z, with or without fractional seconds (OpenRig writes ms)."""
    if not isinstance(value, str) or not value.endswith('Z'):
        return None
    try:
        return datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        return None


def seat_account(seat):
    """The account a seat was launched on, as its launcher recorded it (usage/seats/SEAT)."""
    try:
        return (registry.paths()['usage'] / 'seats' / seat).read_text().strip() or None
    except OSError:
        return None


def openrig_seat_readings(openrig_home):
    """OpenRig's own status line cache: one `{seatSession, asOf, rateLimits}` file per seat under
    `state/provider-usage/`. Only Claude seats count; a reading is attributed to the account the
    seat was launched on. Read-only: the daemon database is opened read-only."""
    usage_dir = Path(openrig_home) / 'state' / 'provider-usage'
    db = Path(openrig_home) / 'openrig.sqlite'
    if not usage_dir.is_dir() or not db.is_file():
        return []
    try:
        conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
        try:
            rows = conn.execute('SELECT s.session_name, n.runtime FROM sessions s '
                                'JOIN nodes n ON n.id = s.node_id').fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    seats = dict(rows)
    readings = []
    for path in sorted(usage_dir.glob('*.json')):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        seat = data.get('seatSession') if isinstance(data, dict) else None
        if seats.get(seat) != 'claude-code':
            continue
        account = seat_account(seat)
        captured = _parse_iso(data.get('asOf'))
        limits = data.get('rateLimits') if isinstance(data.get('rateLimits'), dict) else {}
        reading = {}
        for key in ('five_hour', 'seven_day'):
            window = limits.get(key)
            if not isinstance(window, dict):
                continue
            used, reset = window.get('usedPercent'), _parse_iso(window.get('resetsAt'))
            if isinstance(used, (int, float)) and not isinstance(used, bool) and reset is not None:
                reading[key] = {'used_percentage': used, 'resets_at': reset.timestamp()}
        if account and captured and reading:
            reading.update(account=account, captured=captured.timestamp(), by='openrig seat ' + seat)
            readings.append(reading)
    return readings


def absorb(seat_readings, now=None):
    """A seat's reading fresher than the record goes into the record, so the resolver and
    every view read one place."""
    now = now or time.time()
    for seat in seat_readings:
        if not registry.windows(seat, now):
            continue
        current = registry.reading(seat['account']) or {}
        if (current.get('captured') or 0) >= seat['captured']:
            continue
        path = registry.paths()['usage'] / f"{seat['account']}.json"
        try:
            tmp = path.with_name(f'.{path.name}.seat')
            tmp.write_text(json.dumps(dict(seat, captured=int(seat['captured']))) + '\n')
            tmp.replace(path)
        except OSError:
            pass


CLIENT_NAME = {'claude': 'Claude Code', 'codex': 'Codex', 'pi': 'Pi', 'gh': 'GitHub', 'key': 'API key'}


def _row(entry, now):
    reading = registry.reading(entry['id'])
    current = registry.windows(reading, now)
    client = registry.credential_client(entry, registry.first_client(entry))
    record = registry.signin(entry['id'], client) or {}
    left = registry.remaining(reading, now)
    if not record.get('verified'):
        state = 'unverified'
    elif left is None:
        state = 'quota_unknown'
    else:
        state = 'exhausted' if left <= 0 else 'ready'
    captured = (reading or {}).get('captured')
    age = int(now - captured) if isinstance(captured, (int, float)) else None
    return {'account': entry['id'], 'client': CLIENT_NAME.get(registry.first_client(entry), registry.first_client(entry)),
            'provider': entry['provider'], 'state': state, 'remaining_percent': left,
            'windows': [{'window': n, 'used_percent': u, 'reset_at': r} for n, u, r in current] or None,
            'freshness': 'unknown: no reading yet' if age is None else f'{age // 60} minutes old',
            'source': (reading or {}).get('by'),
            'summary': registry.describe(reading, now), 'reason': record.get('note')}


def unified_view(data=None, observe=None, cache_root=None, now=None, openrig_home=None):
    """One row per account in registry order. Older callers pass their own registry view;
    the one registry is read either way."""
    now = now.timestamp() if isinstance(now, datetime) else (now or time.time())
    reg = registry.load()
    if openrig_home:
        absorb(openrig_seat_readings(openrig_home), now)
    return {'observed_at': datetime.fromtimestamp(now, timezone.utc).isoformat(),
            'accounts': [_row(entry, now) for entry in reg['accounts'] if entry.get('quota_source') != 'none'
                         or entry['kind'] == 'subscription']}


def rotations(limit=10):
    raw = registry.read_safe(registry.rotations_path(), 64 * 1024, tail=True)
    return raw.decode(errors='replace').splitlines()[-limit:] if raw else []


def table(view):
    lines = [f'{"ACCOUNT":<17}{"STATE":<15}USAGE']
    for row in view['accounts']:
        lines.append(f'{row["account"]:<17}{row["state"]:<15}{row["summary"]}')
    switched = rotations(5)
    if switched:
        lines.append('Recent account switches:')
        lines.extend('  ' + line for line in switched)
    lines.append('Unknown is not zero. A Claude reading is a snapshot from the last session on that account.')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='ai-usage', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        view = unified_view(openrig_home=Path.home() / '.openrig')
        print(json.dumps(view, indent=2) if args.json else table(view))
        return 0
    except (OSError, ValueError) as error:
        print('ai-usage: ' + str(error), file=sys.stderr)
        return 2
