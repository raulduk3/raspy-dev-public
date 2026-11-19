"""ai-usage reads the one usage record; unknown is never zero; OpenRig seat readings join
the record under the account the seat was launched on."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
sys.path.insert(0, str(ROOT / 'tests'))
from ai_ecosystem import registry, usage  # noqa: E402
from test_registry import Fake  # noqa: E402


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')


class UnifiedView(Fake):
    def rows(self, **kw):
        return {r['account']: r for r in usage.unified_view(**kw)['accounts']}

    def test_missing_reading_is_unknown_never_zero(self):
        self.signed('anthropic-bravo', 'claude')
        row = self.rows()['anthropic-bravo']
        self.assertEqual(row['state'], 'quota_unknown')
        self.assertIsNone(row['remaining_percent'])
        self.assertEqual(row['summary'], 'unknown')

    def test_a_window_past_its_reset_is_dropped(self):
        self.signed('anthropic-bravo', 'claude')
        self.used('anthropic-bravo', 90, resets_in=-10)
        row = self.rows()['anthropic-bravo']
        self.assertIsNone(row['remaining_percent'])
        self.assertIn('no current window', row['summary'])

    def test_exhausted_and_ready(self):
        for a in ('openai-bravo', 'openai-alpha'):
            self.signed(a, 'codex')
        self.used('openai-bravo', 100)
        self.used('openai-alpha', 25)
        rows = self.rows()
        self.assertEqual(rows['openai-bravo']['state'], 'exhausted')
        self.assertEqual((rows['openai-alpha']['state'], rows['openai-alpha']['remaining_percent']), ('ready', 75.0))

    def test_openrouter_credits_count_as_remaining(self):
        self.signed('openrouter', 'key')
        (self.tmp / 'usage/openrouter.json').write_text(json.dumps(
            {'captured': int(time.time()), 'credits': {'used': 2, 'limit': 10, 'remaining': 8}}))
        row = self.rows()['openrouter']
        self.assertEqual(row['remaining_percent'], 80.0)
        self.assertIn('credits 8.00 left', row['summary'])

    def test_table_shows_recent_switches(self):
        (self.tmp / 'state/rotations.log').write_text('2026-10-05T12:00:00+00:00 anthropic/claude a -> b\n')
        self.assertIn('a -> b', usage.table(usage.unified_view()))

    def test_seat_reading_joins_the_record_under_the_seats_account(self):
        openrig = self.tmp / 'openrig'
        (openrig / 'state/provider-usage').mkdir(parents=True)
        conn = sqlite3.connect(openrig / 'openrig.sqlite')
        conn.executescript('CREATE TABLE nodes (id TEXT, runtime TEXT, config_home TEXT);'
                           'CREATE TABLE sessions (node_id TEXT, session_name TEXT);')
        conn.executemany('INSERT INTO nodes VALUES (?, ?, ?)', [('n1', 'claude-code', None), ('n2', 'codex', None)])
        conn.executemany('INSERT INTO sessions VALUES (?, ?)', [('n1', 'lead@team'), ('n2', 'planner@team')])
        conn.commit()
        conn.close()
        (self.tmp / 'usage/seats').mkdir()
        (self.tmp / 'usage/seats/lead@team').write_text('anthropic-alpha\n')
        (self.tmp / 'usage/seats/planner@team').write_text('openai-bravo\n')
        now = time.time()
        for seat in ('lead@team', 'planner@team'):
            (openrig / 'state/provider-usage' / f'{seat}.json').write_text(json.dumps(
                {'seatSession': seat, 'asOf': iso(now - 60),
                 'rateLimits': {'five_hour': {'usedPercent': 33, 'resetsAt': iso(now + 3600)}}}))
        self.signed('anthropic-alpha', 'claude')
        rows = self.rows(openrig_home=openrig)
        self.assertEqual(rows['anthropic-alpha']['remaining_percent'], 67.0)
        self.assertIn('openrig seat lead@team', registry.reading('anthropic-alpha')['by'])
        self.assertIsNone(registry.reading('openai-bravo'))          # a Codex seat says nothing here
        # an older seat reading never replaces a newer record
        self.used('anthropic-alpha', 5)
        self.rows(openrig_home=openrig)
        self.assertEqual(registry.reading('anthropic-alpha')['five_hour']['used_percentage'], 5)


if __name__ == '__main__':
    unittest.main()
