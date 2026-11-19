/** Two-process offline fixture; caller supplies only a temporary bind mount. */
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import { createRoleSession } from './role-session.mjs';

const [phase, home] = process.argv.slice(2);
assert(['create', 'resume'].includes(phase));
assert.equal(process.env.PI_OFFLINE, '1');
assert(path.isAbsolute(home));
const marker = path.join(home, '.offline-fixture.json');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'pi-session-mount-'));
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
try {
  const identityFile = path.join(temporary, 'identity.md');
  fs.writeFileSync(identityFile, 'OFFLINE_MOUNT_FIXTURE');
  const modelRuntime = await ModelRuntime.create({authPath:path.join(temporary,'auth.json'),
    modelsPath:null,refreshOnCreate:false,allowModelNetwork:false});
  const model = modelRuntime.getModels('openai-codex')[0];
  assert(model);
  const options = {conversation:{id:'mount-fixture',agent:'assistant',scope:{kind:'personal'}},
    conversationHome:home,platformRoot:path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),
    agentDir:temporary,identityFile,modelRuntime,model,accountRef:'offline-account'};
  if (phase === 'create') {
    assert(!fs.existsSync(marker), 'Use an empty temporary conversation');
    const created = await createRoleSession(options);
    try {
      const manager = created.session.sessionManager;
      manager.appendMessage({role:'user',content:'Preserve this fixture request.',timestamp:1});
      manager.appendMessage({role:'assistant',content:[{type:'text',text:'Preserved fixture response.'}],
        api:model.api,provider:model.provider,model:model.id,timestamp:2,stopReason:'stop',
        usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,
          cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}});
      const file = manager.getSessionFile();
      fs.writeFileSync(marker, JSON.stringify({file,id:created.session.sessionId,
        hash:digest(file),hostname:os.hostname()}));
    } finally {created.session.dispose();}
  } else {
    const original = JSON.parse(fs.readFileSync(marker,'utf8'));
    assert.notEqual(os.hostname(), original.hostname, 'Must run in a replacement container');
    const resumed = await createRoleSession({...options,resumeFile:original.file});
    try {
      assert.equal(resumed.session.sessionId, original.id);
      assert.equal(resumed.session.sessionFile, original.file);
      assert.deepEqual(resumed.session.messages.filter(m=>m.role==='user').map(m=>m.content),
        ['Preserve this fixture request.']);
      assert.deepEqual(resumed.session.messages.filter(m=>m.role==='assistant').map(m=>m.content),
        [[{type:'text',text:'Preserved fixture response.'}]]);
    } finally {resumed.session.dispose();}
    assert.equal(digest(original.file), original.hash);
    await assert.rejects(()=>createRoleSession({...options,resumeFile:original.file,
      accountRef:'different-account'}), /binding differs/);
    assert.equal(digest(original.file), original.hash);
  }
  console.log(JSON.stringify({passed:true,phase,scope:'Offline native fixture on explicit conversation mount'}));
} finally {fs.rmSync(temporary,{recursive:true,force:true});}
