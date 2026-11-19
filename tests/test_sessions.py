"""ai-session against temp native stores: real subprocesses, SQLite and files, no network."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import select
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/ai-session'
sys.path.insert(0, str(PLATFORM / 'lib'))
from ai_ecosystem import sessions, store  # noqa: E402

UUID = '0b6f1c2e-1111-4222-8333-444455556666'


def tree_digest(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file():
            h.update(str(p).encode() + p.read_bytes())
    return h.hexdigest()


class SessionIndex(unittest.TestCase):
    def setUp(self):
        # Resume plans refuse inherited provider overrides; the desktop apps set some.
        clean = {k: v for k, v in os.environ.items() if not k.startswith(('ANTHROPIC_', 'CLAUDE_CODE_USE_'))}
        patcher = mock.patch.dict(os.environ, clean, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        tmp = tempfile.TemporaryDirectory(prefix='ai-session-')
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.home = self.base / 'home'
        self.state = self.base / 'state'
        self.work = self.base / 'work'
        self.work.mkdir()
        self.env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.home), 'PYTHONDONTWRITEBYTECODE': '1', **{k: os.environ[k] for k in ('DEV_PLATFORM_ACCOUNTS_TEMPLATE', 'OL_ACCOUNTS_STATE') if k in os.environ}}
        self.codex_db(self.home / '.codex', [(UUID, str(self.work), 'fix login', 'main')])
        self.codex_db(self.home / '.openclaw/agents/main/agent/codex-home', [(UUID, str(self.work), 'owned', 'main')])
        project = self.home / '.claude/projects/-work'
        project.mkdir(parents=True)
        self.claude_line(project, 'aaaaaaaa-0000-4000-8000-000000000001', str(self.work))
        ws = self.home / '.config/Code/User/workspaceStorage/abc'
        (ws / 'chatSessions').mkdir(parents=True)
        (ws / 'workspace.json').write_text(json.dumps({'folder': 'file:///work'}))
        (ws / 'chatSessions/s1.json').write_text(json.dumps({'sessionId': 's1', 'requests': [{'message': 'SECRET BODY'}]}))
        (ws / 'chatSessions/s2.json').write_text('[1, 2]')

    def codex_db(self, home, rows):
        home.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(home / 'state_5.sqlite')
        conn.execute('CREATE TABLE IF NOT EXISTS threads (id TEXT, rollout_path TEXT, cwd TEXT, title TEXT, git_branch TEXT, archived INT, updated_at INT, body TEXT)')
        conn.executemany('INSERT INTO threads VALUES (?, "r", ?, ?, ?, 0, 1, "PRIVATE")', rows)
        conn.commit()
        conn.close()

    def claude_line(self, project, sid, cwd):
        lines = [{'type': 'user', 'sessionId': sid, 'cwd': cwd, 'gitBranch': 'dev', 'timestamp': 't',
                  'message': {'content': 'SECRET BODY'}}]
        (project / f'{sid}.jsonl').write_text('\n'.join(json.dumps(x) for x in lines) + '\n')

    def run_cli(self, *args, stdin=None, check=True):
        run = subprocess.run([str(CLI), '--state-root', str(self.state), *args],
                             capture_output=True, text=True, env=self.env, input=stdin)
        if check and run.returncode:
            self.fail(f'{args}: {run.returncode} {run.stderr}')
        return run

    def listed(self):
        return {m['id']: m for m in json.loads(self.run_cli('list', '--json').stdout)['sessions']}

    def by(self, runtime, **kw):
        return [m for m in self.listed().values() if m['runtime'] == runtime and all(m.get(k) == v for k, v in kw.items())]

    def test_scan_indexes_every_runtime_without_touching_native_bytes_or_bodies(self):
        before = tree_digest(self.home)
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        self.assertEqual(tree_digest(self.home), before)
        codex = self.by('codex')
        self.assertEqual(len(codex), 2, 'two Codex homes with one native id stay distinct')
        self.assertEqual({m['owner'] for m in codex}, {'user', 'openclaw'})
        self.assertEqual(len(self.by('claude', branch='dev')), 1)
        self.assertEqual({m['status'] for m in self.by('copilot')}, {'unknown', 'unsupported'})
        dump = ''.join(p.read_text() for p in self.state.rglob('*.json'))
        self.assertNotIn('SECRET BODY', dump)
        self.assertNotIn('PRIVATE', dump)
        rec = sessions.adapters._rec('nested', title={'body': 'SECRET BODY'},
                                     extra={'key': {'message': 'SECRET BODY'}})
        self.assertIsNone(rec['title'])
        self.assertIsNone(rec['native']['key'])

    def test_isolated_account_histories_are_discovered_without_reading_auth(self):
        codex = self.home / 'profiles/codex-alpha'
        claude = self.home / 'profiles/claude-alpha'
        self.codex_db(codex, [(UUID, str(self.work), 'isolated', 'main')])
        project = claude / 'projects/example'
        project.mkdir(parents=True)
        self.claude_line(project, UUID, str(self.work))
        # Invalid credential JSON deliberately proves these are not parsed.
        (codex / 'auth.json').write_text('DO NOT READ CREDENTIALS')
        registry = self.home / '.config/dev-platform/accounts.json'
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps({'version': 1, 'bindings': {
            'openai-alpha': {'home': str(codex)},
            'anthropic-alpha': {'home': str(claude)},
            'openai-bravo': {'home': str(self.home / '.codex'), 'native_default': True}}}))
        before = tree_digest(self.home)
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        self.assertEqual(before, tree_digest(self.home))
        self.assertEqual(len(self.by('codex')), 3)
        record = self.by('claude', store=str(claude))[0]
        plan = json.loads(self.run_cli('resume', record['id']).stdout)
        self.assertEqual(plan['env']['CLAUDE_CONFIG_DIR'], str(claude))
        self.assertNotIn('DO NOT READ CREDENTIALS', self.run_cli('list', '--json').stdout)
        claude.rename(self.home / 'moved-profile')
        report = json.loads(self.run_cli('scan', '--home', str(self.home), '--no-openclaw').stdout)
        self.assertEqual(report['claude:account:anthropic-alpha']['state'], 'unavailable')
        self.assertEqual(self.by('claude', store=str(claude))[0], record)

    def test_titles_and_handoffs_survive_rescan_and_revision_conflict_fails(self):
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        sid = self.by('claude')[0]['id']
        rev = json.loads(self.run_cli('show', '--json', sid).stdout)['revision']
        native_before = tree_digest(self.home)
        before = json.loads(self.run_cli('show', '--json', sid).stdout)
        self.run_cli('title', sid, 'my title', '--expect-revision', str(rev))
        indexed = json.loads(self.run_cli('show', '--json', sid).stdout)
        self.assertEqual(indexed['native_id'], before['native_id'])
        self.assertEqual(indexed['title'], before['title'])
        self.assertEqual(tree_digest(self.home), native_before, 'an index title is not a native rename')
        self.run_cli('handoff', sid, '--import', '-', '--expect-revision', str(rev + 1), stdin='# Next\nfinish it\n')
        stale = self.run_cli('handoff', sid, '--import', '-', '--expect-revision', str(rev), stdin='x', check=False)
        self.assertEqual(stale.returncode, 3)
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        shown = json.loads(self.run_cli('show', '--json', sid).stdout)
        self.assertEqual(shown['title_override'], 'my title')
        self.assertEqual(shown['handoff'], '# Next\nfinish it\n')
        self.assertTrue((self.state / 'handoffs' / f'{sid}.md').stat().st_mode & 0o027 == 0)  # the owner's group may read (an ACL grant needs it); others never

    def test_invalid_ids_and_oversize_handoffs_are_refused(self):
        for bad in ('../../etc/passwd', 'claude-XYZ'):
            self.assertEqual(self.run_cli('show', bad, check=False).returncode, 1)
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        sid = self.by('claude')[0]['id']
        big = self.run_cli('handoff', sid, '--import', '-', '--expect-revision', '1', stdin='x' * 70000, check=False)
        self.assertEqual(big.returncode, 1)

    def test_concurrent_writers_do_not_clobber(self):
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        sid = self.by('claude')[0]['id']
        code = ('import sys; sys.path.insert(0, sys.argv[1]); from ai_ecosystem.store import Store\n'
                's = Store(sys.argv[2])\nfor i in range(25):\n'
                '    with s.lock(sys.argv[3]):\n        s.put(s.get(sys.argv[3]))\n    s.event(sys.argv[3], "t")\n')
        procs = [subprocess.Popen([sys.executable, '-c', code, str(PLATFORM / 'lib'), str(self.state), sid]) for _ in range(4)]
        self.assertEqual([p.wait() for p in procs], [0] * 4)
        m = store.Store(self.state).get(sid)
        self.assertEqual(m['revision'], 1 + 100)
        self.assertGreaterEqual(len(store.Store(self.state).events(sid)), 100)

    def test_partial_files_ignored_and_index_rebuildable(self):
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        (self.state / 'manifests/.claude-0000.json.tmp').write_text('{"trunc')
        (self.state / 'manifests/claude-00000000000000000000.json').write_text('{"trunc')
        count = len(self.listed())
        for p in (self.state / 'manifests').glob('*'):
            p.unlink()
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        self.assertEqual(len(self.listed()), count)

    def test_missing_source_goes_stale_but_failed_or_truncated_scan_does_not(self):
        s = store.Store(self.state)
        good = lambda recs: sessions.adapters.Source('k', 'claude', 'st', 'user', lambda: iter(recs))
        rec = lambda i: sessions.adapters._rec(f'id{i}', str(self.work))
        other = sessions.adapters.Source('o', 'claude', 'o', 'user', lambda: iter([rec(9)]))
        sessions.scan(s, [good([rec(1), rec(2)]), other], 10)

        def boom():
            raise OSError('gone')
            yield
        report = sessions.scan(s, [sessions.adapters.Source('k', 'claude', 'st', 'user', boom)], 10)
        self.assertEqual(report['k']['state'], 'error')
        self.assertEqual({m['status'] for m in s.all()}, {'unknown'})
        report = sessions.scan(s, [good([rec(1), rec(3)])], 1)
        self.assertEqual(report['k']['state'], 'truncated')
        self.assertEqual({m['status'] for m in s.all()}, {'unknown'})
        sessions.scan(s, [good([rec(1)])], 10)
        stat = {m['native_id']: m['status'] for m in s.all()}
        self.assertEqual(stat, {'id1': 'unknown', 'id2': 'stale', 'id9': 'unknown'})

    def test_interrupted_event_publication_leaves_no_partial_final_event(self):
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        sid = self.by('claude')[0]['id']
        s = store.Store(self.state)
        before = s.events(sid)
        code = ("import sys, os, signal; sys.path.insert(0, sys.argv[1]); "
                "from ai_ecosystem.store import Store\n"
                "def pause_before_rename(src, dst):\n"
                "    print('ready', flush=True)\n    signal.pause()\n"
                "os.replace = pause_before_rename\n"
                "Store(sys.argv[2]).event(sys.argv[3], 'interrupted')\n")
        proc = subprocess.Popen([sys.executable, '-c', code, str(PLATFORM / 'lib'), str(self.state), sid],
                                stdout=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([proc.stdout], [], [], 5)[0], 'writer must reach atomic publication')
            self.assertEqual(proc.stdout.readline().strip(), 'ready')
            self.assertEqual(s.events(sid), before)
        finally:
            proc.kill()
            proc.communicate(timeout=5)
        self.assertTrue(list((self.state / 'events' / sid).glob('.*.tmp')))
        self.assertEqual(s.events(sid), before)
        s.event(sid, 'after')
        self.assertEqual(len(s.events(sid)), len(before) + 1)
        self.run_cli('show', '--json', sid)

    def test_stale_scan_preserves_edits_made_after_manifest_snapshot(self):
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        sid = self.by('claude')[0]['id']
        original = store.Store(self.state).get(sid)
        owner = self

        class InterleavedStore(store.Store):
            def all(self):
                snapshot = super().all()
                rev = self.get(sid)['revision']
                owner.run_cli('title', sid, 'concurrent title', '--expect-revision', str(rev))
                owner.run_cli('handoff', sid, '--import', '-', '--expect-revision', str(rev + 1),
                              stdin='concurrent handoff')
                return snapshot

        s = InterleavedStore(self.state)
        src = sessions.adapters.Source(original['source'], 'claude', original['store'], 'user', lambda: [])
        sessions.scan(s, [src], 100)
        after = s.get(sid)
        self.assertEqual(after['title_override'], 'concurrent title')
        self.assertTrue(after['has_handoff'])
        self.assertEqual(s.read_handoff(sid), 'concurrent handoff')
        self.assertEqual(after['status'], 'stale')
        self.assertEqual([e['kind'] for e in s.events(sid)], ['scan', 'title', 'handoff', 'missing'])

    def test_claude_index_and_headers_keep_locators_and_missing_transcript_is_explicit(self):
        project = self.home / '.claude/projects/-work'
        existing = next(project.glob('*.jsonl'))
        missing = project / 'missing.jsonl'
        (project / 'sessions-index.json').write_text(json.dumps({'entries': [
            {'sessionId': 'missing', 'fullPath': str(missing), 'projectPath': str(self.work),
             'firstPrompt': 'SECRET FIRST PROMPT'}]}))
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        by_id = {m['native_id']: m for m in self.by('claude')}
        self.assertEqual(by_id[existing.stem]['native']['transcript_path'], str(existing))
        m = by_id['missing']
        self.assertEqual(m['native']['transcript_path'], str(missing))
        self.assertEqual(m['native']['index_path'], str(project / 'sessions-index.json'))
        self.assertTrue(m['native']['transcript_missing'])
        self.assertEqual(m['status'], 'stale')
        self.assertFalse(sessions.resume_plan(m)['supported'])
        self.assertNotIn('SECRET FIRST PROMPT', ''.join(p.read_text() for p in self.state.rglob('*.json')))

    def test_disappeared_source_is_unavailable_without_staling_records(self):
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        before = self.by('claude')
        (self.home / '.claude').rename(self.home / 'moved-claude')
        report = json.loads(self.run_cli('scan', '--home', str(self.home), '--no-openclaw').stdout)
        self.assertEqual(report['claude:default']['state'], 'unavailable')
        self.assertEqual(self.by('claude'), before)

    def test_openclaw_cli_contract_distinguishes_agents_and_truncation(self):
        bin_dir = self.base / 'bin'
        bin_dir.mkdir()
        fixture = self.base / 'openclaw.json'
        data = {'path': None, 'allAgents': True, 'count': 2, 'totalCount': 2,
                'limitApplied': None, 'hasMore': False, 'activeMinutes': None,
                'stores': [{'agentId': a, 'path': f'/native/{a}/sessions.sqlite'} for a in ('a', 'b')],
                'sessions': [{'sessionId': UUID, 'agentId': a, 'key': f'agent:{a}:main',
                              'updatedAt': 100, 'message': 'SECRET OPENCLAW BODY'} for a in ('a', 'b')]}
        fixture.write_text(json.dumps(data))
        binary = bin_dir / 'openclaw'
        binary.write_text(f'#!{sys.executable}\nimport sys\nfrom pathlib import Path\n'
                          "assert sys.argv[1:] == ['sessions', '--all-agents', '--limit', 'all', '--json']\n"
                          f'print(Path({str(fixture)!r}).read_text())\n')
        binary.chmod(0o755)
        self.env['PATH'] = str(bin_dir) + ':/usr/bin:/bin'
        self.run_cli('scan', '--home', str(self.home))
        records = self.by('openclaw')
        self.assertEqual(len(records), 2)
        self.assertEqual(len({m['id'] for m in records}), 2)
        self.assertEqual(len({m['store'] for m in records}), 2)
        for m in records:
            self.assertEqual(self.run_cli('resume', m['id'], check=False).returncode, 2)
        data['sessions'] = data['sessions'][:1]
        data['hasMore'] = True
        fixture.write_text(json.dumps(data))
        report = json.loads(self.run_cli('scan', '--home', str(self.home)).stdout)
        self.assertEqual(report['openclaw:all-agents']['state'], 'truncated')
        self.assertEqual({m['status'] for m in self.by('openclaw')}, {'unknown'})
        self.assertNotIn('SECRET OPENCLAW BODY', ''.join(p.read_text() for p in self.state.rglob('*.json')))

    def test_list_is_bounded_and_searches_only_metadata(self):
        self.codex_db(self.home / '.codex', [(f'extra-{i}', str(self.work), f'Example {i}', 'main') for i in range(30)])
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        listed = json.loads(self.run_cli('list', '--json').stdout)
        self.assertEqual(len(listed['sessions']), 20)
        self.assertEqual(listed['total'], 35)
        self.assertTrue(listed['has_more'])
        all_rows = json.loads(self.run_cli('list', '--json', '--limit', '0').stdout)
        self.assertEqual(len(all_rows['sessions']), 35)
        self.assertFalse(all_rows['has_more'])
        found = json.loads(self.run_cli('list', '--json', '--search', 'EXAMPLE 2', '--limit', '3').stdout)
        self.assertEqual(found['total'], 11)
        self.assertEqual(len(found['sessions']), 3)
        self.assertTrue(found['has_more'])
        absent = json.loads(self.run_cli('list', '--json', '--search', 'SECRET BODY').stdout)
        self.assertEqual(absent['total'], 0)
        self.assertNotEqual(self.run_cli('list', '--limit', '-1', check=False).returncode, 0)

    def test_pi_resume_executes_without_a_recorded_working_directory(self):
        class TTY:
            def isatty(self):
                return True

            def write(self, text):
                return len(text)

            def flush(self):
                pass

        plan = {'supported': True, 'runtime': 'pi', 'argv': ['ai-role', 'launch', 'ops'],
                'cwd': None, 'env': {}, 'unset_env': []}
        with (mock.patch.object(sessions, 'Store'),
              mock.patch.object(sessions, 'load', return_value={'id': 'pi-session'}),
              mock.patch.object(sessions, 'resume_plan', return_value=plan),
              mock.patch.object(sessions.shutil, 'which', return_value='/usr/bin/ai-role'),
              mock.patch.object(sessions.sys, 'stdin', TTY()),
              mock.patch.object(sessions.sys, 'stdout', TTY()),
              mock.patch.object(sessions.subprocess, 'run', return_value=mock.Mock(returncode=0)) as run):
            self.assertEqual(sessions.main(['resume', 'pi-session', '--execute']), 0)
        self.assertIsNone(run.call_args.kwargs['cwd'])

    def test_resume_prints_quoted_command_and_never_fakes_unsupported(self):
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        user = self.by('codex', owner='user')[0]
        plan = json.loads(self.run_cli('resume', user['id']).stdout)
        self.assertEqual(plan['argv'], ['codex', 'resume', UUID])
        self.assertEqual(plan['env']['CODEX_HOME'], str(self.home / '.codex'))
        self.assertEqual(plan['unset_env'], ['CODEX_HOME', 'CLAUDE_CONFIG_DIR'])
        for m in self.by('codex', owner='openclaw') + self.by('copilot'):
            run = self.run_cli('resume', m['id'], '--execute', check=False)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(json.loads(run.stdout)['supported'])

    def test_crafted_metadata_cannot_inject_shell(self):
        evil = sessions.resume_plan({'runtime': 'claude', 'owner': 'user', 'status': 'unknown',
                                     'native_id': 'x; rm -rf ~', 'cwd': '/tmp', 'store': 's'})
        self.assertFalse(evil['supported'])
        plan = sessions.resume_plan({'runtime': 'claude', 'owner': 'user', 'status': 'unknown',
                                     'native_id': UUID, 'cwd': "/tmp/a'; touch /tmp/pwn; '", 'store': 's'})
        self.assertEqual(subprocess.run(['sh', '-n', '-c', plan['command']]).returncode, 0)
        self.assertIn("'\"'\"'", plan['command'])
        run = self.run_cli('resume', 'claude-' + '0' * 20, check=False)
        self.assertEqual(run.returncode, 1)

    def test_resume_shell_clears_inherited_profile_and_rejects_provider_override(self):
        self.run_cli('scan', '--home', str(self.home), '--no-openclaw')
        sid = self.by('claude')[0]['id']
        self.env.update(CLAUDE_CONFIG_DIR='/wrong/claude', CODEX_HOME='/wrong/codex')
        plan = json.loads(self.run_cli('resume', sid).stdout)
        bindir = self.base / 'probe-bin'
        bindir.mkdir()
        probe = bindir / 'claude'
        probe.write_text(f'#!{sys.executable}\nimport os,json\n'
                         'print(json.dumps({k:os.environ.get(k) for k in '
                         '["CLAUDE_CONFIG_DIR","CODEX_HOME"]}))\n')
        probe.chmod(0o755)
        env = dict(self.env, PATH=str(bindir) + ':/usr/bin:/bin')
        result = subprocess.run(['sh', '-c', plan['command']], env=env,
                                text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), {'CLAUDE_CONFIG_DIR': None, 'CODEX_HOME': None})
        self.env['OPENAI_API_KEY'] = 'PRIVATE-OVERRIDE'
        refused = self.run_cli('resume', sid, check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertFalse(json.loads(refused.stdout)['supported'])
        self.assertNotIn('PRIVATE-OVERRIDE', refused.stdout + refused.stderr)


if __name__ == '__main__':
    unittest.main()
