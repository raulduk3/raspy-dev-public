import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import naming, retitle  # noqa: E402

OLD = time.time() - 3 * 86400
SCHEMA = '''CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL, source TEXT NOT NULL, model_provider TEXT NOT NULL, cwd TEXT NOT NULL,
  title TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0, git_branch TEXT, first_user_message TEXT NOT NULL DEFAULT '',
  agent_nickname TEXT, agent_path TEXT, model TEXT, name TEXT, originator TEXT, updated_at_ms INTEGER)'''


def jl(*records):
    return ''.join(json.dumps(r, separators=(',', ':')) + '\n' for r in records)


def user(text, **extra):
    base = {'type': 'user', 'entrypoint': 'cli', 'cwd': '/home/u/dev/app', 'gitBranch': 'main',
            'timestamp': '2026-10-12T18:16:40.121Z', 'isSidechain': False, 'sessionId': 's',
            'message': {'role': 'user', 'content': text}}
    base.update(extra)
    return base


def assistant(model='claude-opus-5-5'):
    return {'type': 'assistant', 'timestamp': '2026-10-12T18:17:00.000Z', 'message': {'role': 'assistant', 'model': model, 'content': []}}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / 'home'
        self.backup = self.tmp / 'backup'
        self.home.mkdir()

    def write(self, rel, text, age=OLD):
        path = self.home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        os.utime(path, (age, age))
        return path

    def run_rename(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return retitle.main(['--home', str(self.home), '--backup-dir', str(self.backup), '--no-app-server', '--no-llm', *args])

    def undo(self, manifest):
        with contextlib.redirect_stdout(io.StringIO()):
            return retitle.main(['--undo', str(manifest)])

    def manifests(self):
        return sorted(self.backup.glob('*/manifest.json'))

    def build_claude(self):
        proj = '.claude/projects/-home-u-dev-app/'
        self.chat = self.write(proj + 'chat.jsonl', jl(user('Why does the build fail on arm64? My key sk-abcdefghijklmnopqrstu'), assistant()))
        self.fixed = self.write(proj + 'fixed.jsonl', jl(user('x'), assistant(), {'type': 'custom-title', 'customTitle': 'feat(repo): Add login #12', 'sessionId': 'fixed'}))
        self.ok = self.write(proj + 'ok.jsonl', jl(user('hi'), {'type': 'custom-title', 'sessionId': 'ok', 'customTitle':
            '[dev-server/app] chat(misc): Hello · owner · claude-cli · anthropic/opus-5-5 · interactive · 2026-10-12'}))
        self.live = self.write(proj + 'live.jsonl', jl(user('Recent work'), assistant()), age=time.time())
        self.loop = self.write(proj + 'loop.jsonl', jl(user('# Worker brief: issue #228 Repository x/app. Branch `feat/add-sections-228`',
                                                              entrypoint='sdk-cli', cwd='/home/u/dev/app/.claude/worktrees/loop-228-add',
                                                              gitBranch='feat/add-sections-228'), assistant('claude-sonnet-5-5')))
        self.side = self.write(proj + 'side.jsonl', jl(user('Review the diff for the parser', isSidechain=True), assistant()))
        self.nonl = self.write(proj + 'nonl.jsonl', jl(user('Document the API'), assistant()).rstrip('\n'))
        self.acme = self.write('.claude-accounts/acme/projects/-home-u-dev-app/acme.jsonl', jl(user('Plan the work', entrypoint='claude-desktop'), assistant('claude-haiku-5-5')))
        self.write(proj + 'sessions-index.json', json.dumps({'version': 1, 'entries': [
            {'sessionId': 'fixed', 'customTitle': 'feat(repo): Add login #12', 'modified': '2026-10-12'}]}, indent=2))


class PureTest(unittest.TestCase):
    def test_clean_prompt(self):
        text = '<system-reminder>ignore me</system-reminder>\n\n# Fix the login page sk-abcdefghijklmnopqrstu and then a very long tail of words that goes on'
        out = retitle.clean_prompt(text)
        self.assertLessEqual(len(out), retitle.DESCRIPTION_MAX)
        self.assertNotIn('sk-abc', out)
        self.assertNotIn('ignore', out)
        self.assertTrue(out.startswith('Fix the login page'))
        self.assertIsNone(retitle.clean_prompt('<x> </x>\n--'))
        self.assertEqual(retitle.clean_title('https://example.com/pull/7\n\nFix the parser'), 'Fix the parser')
        self.assertEqual(retitle.build_what({'old_title': 'dev-lead@app', 'branch': 'main'})[0][-25:], 'OpenRig seat dev-lead@app')

    def test_purpose_and_area(self):
        self.assertEqual(retitle.guess_purpose('Why is the build slow'), 'spike')
        self.assertEqual(retitle.guess_purpose('Fix crash in parser'), 'fix')
        self.assertEqual(retitle.guess_purpose('Review the diff'), 'review')
        self.assertEqual(retitle.guess_purpose('Deploy to staging'), 'ops')
        self.assertEqual(retitle.guess_purpose('Update the README'), 'docs')
        self.assertEqual(retitle.guess_purpose('Talk about dinner'), 'chat')
        self.assertEqual(retitle.area_of('feat/anthropic-acme-account'), 'anthropic-acme')
        self.assertEqual(retitle.area_of('wip/naming-renamer-070d5b'), 'naming-renamer')
        self.assertEqual(retitle.area_of('feat/add-sections-228'), 'add-sections')
        self.assertEqual(retitle.area_of('main'), 'misc')
        self.assertEqual(retitle.area_of(None), 'misc')

    def test_keep_valid_prefix_and_replace_invalid(self):
        self.assertEqual(retitle.build_what({'old_title': 'feat(repo): Add login #12'}), ('feat(repo): Add login #12', True))
        what, confident = retitle.build_what({'old_title': 'wip(ui): Tidy buttons', 'branch': 'main'})
        self.assertEqual((what, confident), ('chat(ui): Tidy buttons', False))

    def test_yaml_name_round_trip(self):
        block = 'id: x\nclient_name: zed\nname: |-\n  line one\n\n  line two\nuser_named: false\n'
        self.assertEqual(retitle._yaml_name(block.split('\n'))[2], 'line one\n\nline two')
        out = retitle.set_yaml_name(block, 'chat(misc): "Quoted" title')
        self.assertIn('name: "chat(misc): \\"Quoted\\" title"', out)
        self.assertIn('user_named: false', out)
        self.assertNotIn('line one', out)
        self.assertFalse([l for l in retitle.remove_yaml_name(out).split('\n') if l.startswith('name:')])
        added = retitle.set_yaml_name('id: x\nclient_name: zed\nuser_named: false\n', 'T')
        self.assertEqual(added.split('\n')[2], 'name: "T"')


class ClaudeTest(Fixture):
    def titles(self, path):
        return retitle.claude_titles(path)

    def test_dry_run_changes_nothing(self):
        self.build_claude()
        before = {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(self.run_rename('--dry-run', '--store', 'claude'), 0)
        self.assertEqual(before, {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
        self.assertFalse(self.backup.exists())

    def test_rename_backup_idempotence_and_undo(self):
        self.build_claude()
        originals = {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(self.run_rename('--store', 'claude'), 0)
        # chat session: purpose from "why", secret removed, fields from the transcript
        title = self.titles(self.chat)['custom']
        parsed = naming.parse(title)
        self.assertEqual(naming.problems(title), [])
        self.assertEqual((parsed['purpose'], parsed['client'], parsed['model'], parsed['type'], parsed['date']),
                         ('forensics', 'claude-cli', 'anthropic/opus-5-5', 'interactive', '2026-10-12'))
        self.assertEqual(parsed['project'], 'app')
        self.assertNotIn('sk-abc', title)
        # same two lines as Claude itself writes
        lines = self.chat.read_text().splitlines()[-2:]
        self.assertEqual([json.loads(l)['type'] for l in lines], ['custom-title', 'agent-name'])
        self.assertEqual(json.loads(lines[1])['agentName'], title)
        # old title kept as description, valid prefix kept
        self.assertEqual(naming.parse(self.titles(self.fixed)['custom'])['what'], 'feat(repo): Add login #12')
        # loop worker, subagent, no trailing newline, account
        loop = naming.parse(self.titles(self.loop)['custom'])
        self.assertEqual((loop['who'], loop['type'], loop['client'], loop['purpose'], loop['ref']), ('loop#228', 'loop', 'claude-sdk', 'feat', '#228'))
        side = naming.parse(self.titles(self.side)['custom'])
        self.assertEqual((side['type'], side['purpose']), ('subagent', 'review'))
        self.assertEqual(naming.problems(self.titles(self.nonl)['custom']), [])
        self.assertEqual(naming.parse(self.titles(self.nonl)['custom'])['purpose'], 'docs')
        air = naming.parse(self.titles(self.acme)['custom'])
        self.assertEqual((air['client'], air['model']), ('claude-desktop:acme', 'anthropic/haiku-5-5'))
        # live and conforming sessions stay as they were
        self.assertEqual(self.live.read_bytes(), originals[self.live])
        self.assertEqual(self.ok.read_bytes(), originals[self.ok])
        # index title follows
        index = json.loads((self.home / '.claude/projects/-home-u-dev-app/sessions-index.json').read_text())
        self.assertEqual(index['entries'][0]['customTitle'], self.titles(self.fixed)['custom'])
        # backup keeps relative paths and holds the original bytes
        manifest = self.manifests()[0]
        backed = manifest.parent / '.claude/projects/-home-u-dev-app/chat.jsonl'
        self.assertEqual(backed.read_bytes(), originals[self.chat])
        self.assertFalse((manifest.parent / '.claude/projects/-home-u-dev-app/live.jsonl').exists())
        data = json.loads(manifest.read_text())
        entry = next(e for e in data['entries'] if e['session_id'] == 'chat')
        self.assertEqual((entry['old_title'], entry['new_title'], entry['applied']), (None, title, True))
        # second run changes nothing
        after = {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(self.run_rename('--store', 'claude'), 0)
        self.assertEqual(after, {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
        self.assertEqual(len(self.manifests()), 1)
        # undo restores every byte
        self.assertEqual(self.undo(manifest), 0)
        self.assertEqual(originals, {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()})

    def test_undo_after_new_lines_appends_old_title(self):
        self.build_claude()
        self.run_rename('--store', 'claude')
        with open(self.fixed, 'a') as handle:
            handle.write(jl({'type': 'user', 'message': {'content': 'later'}}))
        self.assertEqual(self.undo(self.manifests()[0]), 0)
        self.assertEqual(self.titles(self.fixed)['custom'], 'feat(repo): Add login #12')

    def test_counts(self):
        self.build_claude()
        plans = retitle.scan(['claude'], retitle.Context(self.home, host='h'))
        counts = {}
        for plan in plans:
            counts[plan.status] = counts.get(plan.status, 0) + 1
        self.assertEqual(counts, {'rename': 6, 'ok': 1, 'live': 1})


class ModelPassTest(Fixture):
    def setUp(self):
        super().setUp()
        proj = '.claude/projects/-home-u-dev-app/'
        self.a = self.write(proj + 'a.jsonl', jl(user('Talk through the tenant onboarding steps', gitBranch='main'), assistant()))
        self.b = self.write(proj + 'b.jsonl', jl(user('Fix the login redirect', gitBranch='fix/login-redirect'), assistant()))
        self.cache = self.tmp / 'cache' / 'llm-cache.json'
        self.asked = []

    def runner(self, prompt):
        items = json.loads(prompt.split('ITEMS:\n', 1)[1])
        self.asked.append(items)
        return 'Sure:\n' + json.dumps([{'id': i['id'], 'purpose': 'plan', 'area': 'Tenant Onboarding', 'description': 'Plan tenant onboarding'}
                                       for i in items] + [{'id': 99, 'purpose': 'bogus', 'area': 'x', 'description': 'y'}])

    def scan(self, **kw):
        return [p for p in retitle.scan(['claude'], retitle.Context(self.home, host='h', **kw))]

    def test_confident_sessions_are_not_sent(self):
        plans = {p.sid: p for p in self.scan()}
        self.assertFalse(plans['b'].low)
        self.assertTrue(plans['a'].low)
        stats = retitle.classify(list(plans.values()), self.cache, runner=self.runner)
        self.assertEqual((stats['low'], stats['asked'], stats['answered']), (1, 1, 1))
        self.assertEqual(len(self.asked[0]), 1)
        self.assertEqual(self.asked[0][0]['messages'], ['Talk through the tenant onboarding steps'])
        parsed = naming.parse(plans['a'].new)
        self.assertEqual((parsed['purpose'], parsed['area']), ('plan', 'tenant-onboarding'))
        self.assertFalse(plans['a'].low)
        self.assertEqual(naming.parse(plans['b'].new)['purpose'], 'fix')
        self.assertEqual(naming.parse(plans['b'].new)['area'], 'login-redirect')

    def test_cache_makes_reruns_free_and_failures_keep_the_guess(self):
        retitle.classify(self.scan(), self.cache, runner=self.runner)
        plans = self.scan()
        stats = retitle.classify(plans, self.cache, runner=lambda prompt: 1 / 0)
        self.assertEqual((stats['cached'], stats['asked'], stats['failed_batches']), (1, 0, 0))
        self.assertEqual(naming.parse(next(p for p in plans if p.sid == 'a').new)['purpose'], 'plan')
        self.cache.unlink()

        def broken(prompt):
            raise RuntimeError('offline')
        plans = self.scan()
        stats = retitle.classify(plans, self.cache, runner=broken)
        self.assertEqual(stats['failed_batches'], 1)
        self.assertEqual(naming.problems(next(p for p in plans if p.sid == 'a').new), [])

    def test_redo_generic_improves_placeholder_titles_only(self):
        generic = '[h/app] chat(misc): Talk through the tenant onboarding steps · owner · claude-cli · anthropic/opus-5-5 · interactive · 2026-10-12'
        self.write('.claude/projects/-home-u-dev-app/c.jsonl', jl(user('x'), assistant(), {'type': 'custom-title', 'customTitle': generic, 'sessionId': 'c'}))
        self.assertEqual({p.sid: p.status for p in self.scan()}['c'], 'ok')
        plans = {p.sid: p for p in self.scan(redo_generic=True)}
        self.assertEqual(plans['c'].status, 'rename')
        retitle.classify(list(plans.values()), self.cache, runner=self.runner)
        self.assertEqual(naming.parse(plans['c'].new)['what'][:5], 'plan(')
        self.assertEqual(plans['c'].old, generic)
        self.assertEqual(plans['c'].new.count('chat(misc)'), 0)
        self.assertEqual(plans['c'].new.count('['), 1)

    def test_distribution(self):
        plans = self.scan()
        self.assertEqual(retitle.distribution(plans), {'chat': 1, 'fix': 1})


class CodexTest(Fixture):
    def build(self):
        db = self.home / '.codex/state_5.sqlite'
        db.parent.mkdir(parents=True)
        conn = sqlite3.connect(db)
        conn.execute(SCHEMA)
        conn.executemany('INSERT INTO threads (id,created_at,updated_at,source,model_provider,cwd,title,git_branch,agent_nickname,model,name,originator,first_user_message) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', [
            ('t1', 1760000000, int(OLD), 'vscode', 'openai', '/home/u/dev/app', 'Deep dive into email', 'main', None, 'gpt-5.6-terra', 'Improve email styling', 'Codex Desktop', 'Deep dive'),
            ('t2', 1760000100, int(OLD), '{"subagent":{"thread_spawn":{"parent_thread_id":"t1","depth":1,"agent_path":"/root/ui_audit","agent_nickname":"Gibbs","agent_role":null}}}',
             'openai', '/home/u/dev/app', '', None, 'Gibbs', 'gpt-5.6-terra', None, 'Codex Desktop', 'Audit the settings page'),
            ('t4', 1760000150, int(OLD), 'cli', 'openai', '/home/u/dev/app', 'Second', None, None, 'gpt-5', 'Second named', 'codex_cli', 'Second'),
            ('t3', 1760000200, int(time.time()), 'exec', 'openai', '/home/u/dev/app', 'Fresh run', None, None, 'gpt-6', None, 'codex_exec', 'Fresh run'),
        ])
        conn.commit()
        conn.close()
        self.write('.codex/session_index.jsonl', jl({'id': 't1', 'thread_name': 'Improve email styling', 'updated_at': '2026-10-05T17:15:06.7Z'}, {'id': 't4', 'thread_name': 'Second named', 'updated_at': '2026-10-05T17:15:07.7Z'}))
        return db

    def rows(self, db):
        conn = sqlite3.connect(db)
        try:
            return {r[0]: r[1:] for r in conn.execute('SELECT id,name,title,updated_at FROM threads ORDER BY id')}
        finally:
            conn.close()

    def test_rename_and_undo(self):
        db = self.build()
        before_rows, before_index = self.rows(db), (self.home / '.codex/session_index.jsonl').read_bytes()
        self.assertEqual(self.run_rename('--store', 'codex'), 0)
        rows = self.rows(db)
        t1, t2 = naming.parse(rows['t1'][0]), naming.parse(rows['t2'][0])
        self.assertEqual((t1['client'], t1['model'], t1['type'], t1['what']), ('codex-app', 'openai/gpt-5.6-terra', 'interactive', 'feat(email): Improve email styling'))
        self.assertEqual((t2['who'], t2['type'], t2['purpose']), ('Gibbs', 'subagent', 'review'))
        self.assertEqual(rows['t1'][0], rows['t1'][1])
        self.assertEqual({k: v[2] for k, v in rows.items()}, {k: v[2] for k, v in before_rows.items()})
        self.assertEqual(rows['t3'], before_rows['t3'])  # live
        index = [json.loads(l) for l in (self.home / '.codex/session_index.jsonl').read_text().splitlines()]
        self.assertEqual([i['id'] for i in index], ['t1', 't4', 't1', 't2', 't4'])
        self.assertEqual(index[3]['thread_name'], rows['t2'][0])
        backed = sqlite3.connect(self.manifests()[0].parent / '.codex/state_5.sqlite')
        self.assertEqual(backed.execute("SELECT name FROM threads WHERE id='t1'").fetchone()[0], 'Improve email styling')
        backed.close()
        self.assertEqual(self.run_rename('--store', 'codex'), 0)
        self.assertEqual(len(self.manifests()), 1)
        self.assertEqual(self.undo(self.manifests()[0]), 0)
        self.assertEqual(self.rows(db), before_rows)
        self.assertEqual((self.home / '.codex/session_index.jsonl').read_bytes(), before_index)

    def test_app_server_is_preferred(self):
        db = self.build()

        class Fake:
            def __init__(self):
                self.calls = []

            def set_name(self, thread, name):
                self.calls.append((thread, name))
                return thread == 't1'

        plans = [p for p in retitle.scan(['codex'], retitle.Context(self.home, host='h')) if p.status == 'rename']
        fake = Fake()
        retitle.apply_codex(plans, retitle.Context(self.home), fake)
        self.assertEqual([c[0] for c in fake.calls], ['t1', 't2', 't4'])
        rows = self.rows(db)
        self.assertEqual(rows['t1'][0], 'Improve email styling')  # app-server owns this write
        self.assertTrue(rows['t2'][0].startswith('['))  # fallback for the one it refused


class PiCopilotTest(Fixture):
    def test_pi(self):
        self.write('.pi/agent/settings.json', json.dumps({'defaultProvider': 'openrouter', 'defaultModel': 'moonshotai/kimi-k2.6'}))
        path = self.write('.pi/agent/sessions/--home-u-writing--/2026-10-14T20-17-41-556Z_abc.jsonl', jl(
            {'type': 'session', 'version': 3, 'id': 'abc', 'timestamp': '2026-10-14T20:17:41.556Z', 'cwd': '/home/u/writing'},
            {'type': 'model_change', 'id': 'aa000001', 'parentId': None, 'timestamp': 'x', 'provider': 'openrouter', 'modelId': 'moonshotai/kimi-k2.6'},
            {'type': 'message', 'id': 'aa000002', 'parentId': 'aa000001', 'timestamp': 'x', 'message': {'role': 'user', 'content': [{'type': 'text', 'text': 'hi'}]}},
            {'type': 'session_info', 'id': 'aa000003', 'parentId': 'aa000002', 'timestamp': 'x', 'name': 'writing'}))
        original = path.read_bytes()
        self.assertEqual(self.run_rename('--store', 'pi'), 0)
        last = json.loads(path.read_text().splitlines()[-1])
        self.assertEqual((last['type'], last['parentId']), ('session_info', 'aa000003'))
        self.assertEqual(list(last), ['type', 'id', 'parentId', 'timestamp', 'name'])
        parsed = naming.parse(last['name'])
        self.assertEqual((parsed['client'], parsed['model'], parsed['what']), ('pi', 'openrouter/kimi-k2.6', 'write(writing): Writing'))
        self.assertEqual(naming.problems(last['name']), [])
        self.assertEqual(self.undo(self.manifests()[0]), 0)
        self.assertEqual(path.read_bytes(), original)

    def test_copilot(self):
        path = self.write('.copilot/session-state/c1/workspace.yaml',
                          'id: c1\ncwd: /home/u/dev/app\nbranch: develop\nclient_name: zed\nname: include caller ID\nuser_named: false\ncreated_at: 2026-10-13T13:41:59.303Z\n')
        original = path.read_text()
        self.assertEqual(self.run_rename('--store', 'copilot'), 0)
        text = path.read_text()
        name = json.loads(next(l for l in text.splitlines() if l.startswith('name:'))[5:])
        self.assertEqual(naming.problems(name), [])
        self.assertEqual(naming.parse(name)['client'], 'zed')
        self.assertIn('user_named: false', text)
        self.assertEqual(self.undo(self.manifests()[0]), 0)
        self.assertEqual(path.read_text(), original)


class CliTest(Fixture):
    def test_ai_title_entry_point(self):
        self.write('.claude/projects/-home-u-dev-app/a.jsonl', jl(user('Plan the trip'), assistant()))
        run = subprocess.run([str(ROOT / 'bin/ai-title'), 'rename', '--dry-run', '--home', str(self.home), '--store', 'claude'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('-> [', run.stdout)
        self.assertIn('would rename', run.stdout)


if __name__ == '__main__':
    unittest.main()
