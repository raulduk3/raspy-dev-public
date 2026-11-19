import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from ai_ecosystem.environments import mapped_path, runtimes, sources
from ai_ecosystem.sessions import scan, resume_plan
from ai_ecosystem.store import Store

class Environments(unittest.TestCase):
    def test_native_stores_mapped_without_host_resume_or_transcript_changes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();envs=root/'envs';envs.mkdir()
            claude=envs/'anthropic-alpha/home/.claude/projects/project';claude.mkdir(parents=True)
            transcript=claude/'one.jsonl';transcript.write_text('private transcript\n')
            (claude/'sessions-index.json').write_text(json.dumps({'entries':[{'sessionId':'one','projectPath':'/workspace/project','fullPath':'/home/node/.claude/projects/project/one.jsonl'}]}))
            codex=envs/'openai-alpha/home/.codex';codex.mkdir(parents=True)
            db=codex/'state_5.sqlite'
            with sqlite3.connect(db) as conn:
                conn.execute('CREATE TABLE threads(id,cwd,updated_at,rollout_path)')
                conn.execute('INSERT INTO threads VALUES(?,?,?,?)',('two','/workspace/other',1,'/home/node/.codex/sessions/two.jsonl'))
            before={p:p.read_bytes() for p in (transcript,db)}
            store=Store(root/'index');report=scan(store,sources(envs),100)
            rows={r['runtime']:r for r in store.all()}
            self.assertEqual(rows['claude']['cwd'],str(envs/'anthropic-alpha/workspace/project'))
            self.assertFalse(rows['claude']['missing'])
            self.assertEqual(rows['codex']['native']['container_cwd'],'/workspace/other')
            self.assertEqual(rows['codex']['native']['rollout_path'],str(codex/'sessions/two.jsonl'))
            for row in rows.values():
                self.assertEqual(row['owner'],'openrig')
                self.assertFalse(resume_plan(row)['supported'])
                self.assertEqual(row['native']['account_identity'],'unverified')
            self.assertEqual(report['claude:environment:anthropic-bravo']['state'],'unavailable')
            self.assertEqual(before,{p:p.read_bytes() for p in before})
            with self.assertRaises(ValueError):mapped_path(envs,'/workspace/../../etc/passwd')
            with self.assertRaises(ValueError):mapped_path(envs,'/etc/passwd')

    def test_accounts_come_from_the_registry(self):
        data={'accounts':[
            {'id':'anthropic-work','provider':'anthropic','kind':'subscription','clients':['claude','pi']},
            {'id':'openai-bravo','provider':'openai','kind':'subscription','clients':['codex','pi']},
            {'id':'openrouter','provider':'openrouter','kind':'api-key','clients':['pi']},
            {'id':'github','provider':'github','kind':'oauth','clients':['gh']}]}
        self.assertEqual(runtimes(data),{'anthropic-work':'claude','openai-bravo':'codex'})
