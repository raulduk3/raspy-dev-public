"""The offline checks of the Pi role code in integrations/pi that no other test runs.

Each check makes its own temporary folders; none reads a live home, a credential or the network.
One check stays out: check-session-mount.mjs needs a bind mount from its caller.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PI = ROOT / 'integrations/pi'
RUNTIME = PI / 'node_modules/@earendil-works/pi-coding-agent'   # the pinned Pi runtime, linked by the release

# (script, a line of its output that says it passed, it needs the Pi runtime)
CHECKS = (
    ('check-journal-tool.mjs', 'journal tool: ok', False),
    ('check-session-title.mjs', 'session-title: ok', False),
    ('check-perplexity.mjs', '"passed": true', True),
    ('check-role-context.mjs', '"passed": true', True),
    ('check-role-history.mjs', '"passed": true', True),
    ('check-role-session.mjs', '"passed": true', True),    # a resume leaves the session file unchanged (SE-49)
    ('check-role-skills.mjs', '"passed": true', True),
    ('check-role-terminal.py', '"passed": true', True),   # runs check-role-terminal.mjs in a PTY
)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class OfflinePiChecks(unittest.TestCase):
    def test_each_check_passes(self):
        for script, passed, runtime in CHECKS:
            with self.subTest(script=script):
                if runtime and not RUNTIME.is_dir():
                    self.skipTest('the Pi runtime is not linked into integrations/pi/node_modules')
                command = [sys.executable, '-I'] if script.endswith('.py') else ['node']
                result = subprocess.run([*command, str(PI / script)], cwd=PI, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(passed, result.stdout)


# The part of check-role-session.mjs that proves SDD-RO-17, on the real Pi runtime with no model call.
# The full check, with the transcript bytes after a resume, is in CHECKS.
ROLE_SWITCH = r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import { createRoleSession } from './role-session.mjs';
import { createRoleRuntime } from './role-runtime.mjs';
const root = process.env.FIXTURE_ROOT, platformRoot = path.resolve('../..');
const agentDir = path.join(root, 'auth'); fs.mkdirSync(agentDir);
const modelRuntime = await ModelRuntime.create({authPath: path.join(agentDir, 'auth.json'), modelsPath: null,
  refreshOnCreate: false, allowModelNetwork: false});
const model = modelRuntime.getModels('openai-codex')[0]; assert(model);
const identityFile = path.join(root, 'identity.md'); fs.writeFileSync(identityFile, 'FIXTURE');
const options = {conversation: {id: 'fixture-conversation', agent: 'assistant', scope: {kind: 'personal'}},
  conversationHome: path.join(root, 'conversation'), platformRoot, agentDir, identityFile, modelRuntime, model,
  accountRef: 'fixture-account'};
const first = await createRoleSession(options);
const manager = first.session.sessionManager;
manager.appendMessage({role: 'user', content: 'fixture request', timestamp: 1});
manager.appendMessage({role: 'assistant', content: [{type: 'text', text: 'fixture reply'}], api: model.api,
  provider: model.provider, model: model.id, timestamp: 2, stopReason: 'stop',
  usage: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
          cost: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0}}});
const file = manager.getSessionFile(); first.session.dispose();
const outside = path.join(root, 'outside.jsonl'); fs.copyFileSync(file, outside);
const runtime = await createRoleRuntime({...options, resumeFile: file});
const result = {};
try {
  runtime.setRebindSession(session => session.bindExtensions({}));
  await runtime.session.bindExtensions({});
  const folder = () => runtime.session.sessionManager.getSessionDir() === path.dirname(file);
  result.newSession = !(await runtime.newSession()).cancelled && folder();
  result.resume = !(await runtime.switchSession(file)).cancelled && folder();
  const id = runtime.session.sessionId;
  result.outsideResumeCancelled = (await runtime.switchSession(outside)).cancelled;
  result.outsideImportCancelled = (await runtime.importFromJsonl(outside)).cancelled;
  result.sessionStays = runtime.session.sessionId === id;
  const user = runtime.session.sessionManager.getEntries().find(e => e.type === 'message' && e.message.role === 'user');
  result.fork = !(await runtime.fork(user.id, {position: 'at'})).cancelled && folder();
  result.bindings = runtime.session.sessionManager.getEntries()
    .filter(e => e.type === 'custom' && e.customType === 'dev-platform-binding').length;
} finally { await runtime.dispose(); }
console.log(JSON.stringify(result));
'''


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
@unittest.skipUnless(RUNTIME.is_dir(), 'the Pi runtime is not linked into integrations/pi/node_modules')
class RoleSessionSwitch(unittest.TestCase):
    def test_new_resume_and_fork_stay_and_an_outside_file_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='pi-role-switch-') as root:
            env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG')}
            env.update(HOME=root, TMPDIR=root, FIXTURE_ROOT=root)
            done = subprocess.run(['node', '--input-type=module', '-e', ROLE_SWITCH], cwd=PI, env=env,
                                  capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1]),
                         {'newSession': True, 'resume': True, 'outsideResumeCancelled': True,
                          'outsideImportCancelled': True, 'sessionStays': True, 'fork': True, 'bindings': 1})


if __name__ == '__main__':
    unittest.main()
