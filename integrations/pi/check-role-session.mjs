import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import { createRoleSession } from './role-session.mjs';
import { createRoleRuntime } from './role-runtime.mjs';
const platformRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'pi-role-session-'));
try {
  const agentDir=path.join(root,'auth');fs.mkdirSync(agentDir);
  const modelRuntime=await ModelRuntime.create({authPath:path.join(agentDir,'auth.json'),modelsPath:null,refreshOnCreate:false,allowModelNetwork:false});
  const model=modelRuntime.getModels('openai-codex')[0];assert(model);
  const identityFile=path.join(root,'identity.md');fs.writeFileSync(identityFile,'ASSISTANT_SESSION_FIXTURE');
  const options={conversation:{id:'fixture-conversation',agent:'assistant',scope:{kind:'personal'}},
    conversationHome:path.join(root,'conversation'),platformRoot,agentDir,identityFile,
    modelRuntime,model,accountRef:'fixture-account'};
  const first=await createRoleSession(options);
  let file;
  try {
    assert(first.session.systemPrompt.includes('ASSISTANT_SESSION_FIXTURE'));
    assert(first.session.getActiveToolNames().includes('perplexity_search'));
    const manager=first.session.sessionManager;
    // Native fixture messages, not an inference result. Pi persists on first assistant entry.
    manager.appendMessage({role:'user',content:'fixture request',timestamp:1});
    manager.appendMessage({role:'assistant',content:[{type:'text',text:'fixture reply'}],
      api:model.api,provider:model.provider,model:model.id,timestamp:2,stopReason:'stop',
      usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}});
    file=manager.getSessionFile();
    assert.equal(path.dirname(file),path.join(options.conversationHome,'native/pi'));
    assert(fs.existsSync(file));
  } finally {first.session.dispose();}
  const bytes=fs.readFileSync(file);
  const resumed=await createRoleSession({...options,resumeFile:file});
  try {
    assert.equal(resumed.session.sessionFile,file);
    assert(resumed.session.messages.some(m=>m.role==='user' && m.content==='fixture request'));
  } finally {resumed.session.dispose();}
  assert.deepEqual(fs.readFileSync(file),bytes);
  await assert.rejects(()=>createRoleSession({...options,resumeFile:file,accountRef:'other-account'}),/binding differs/);
  await assert.rejects(()=>createRoleSession({...options,resumeFile:file,conversation:{...options.conversation,id:'other'}}),/binding differs/);
  const outside=path.join(root,'outside.jsonl');fs.copyFileSync(file,outside);
  await assert.rejects(()=>createRoleSession({...options,resumeFile:outside}),/in this conversation/);
  assert.deepEqual(fs.readFileSync(file),bytes);
  const runtime=await createRoleRuntime({...options,resumeFile:file});
  try {
    runtime.setRebindSession(session=>session.bindExtensions({}));
    await runtime.session.bindExtensions({});
    assert.equal((await runtime.newSession()).cancelled,false);
    assert.equal(runtime.session.sessionManager.getSessionDir(),path.dirname(file));
    assert.equal((await runtime.switchSession(file)).cancelled,false);
    assert.equal(runtime.session.sessionManager.getSessionDir(),path.dirname(file));
    const sessionId=runtime.session.sessionId;
    assert.equal((await runtime.switchSession(outside)).cancelled,true);
    assert.equal((await runtime.importFromJsonl(outside)).cancelled,true);
    assert.equal(runtime.session.sessionId,sessionId);
    const userEntry=runtime.session.sessionManager.getEntries().find(e=>e.type==='message' && e.message.role==='user');
    assert.equal((await runtime.fork(userEntry.id,{position:'at'})).cancelled,false);
    assert.equal(runtime.session.sessionManager.getSessionDir(),path.dirname(file));
    assert.equal(runtime.session.sessionManager.getEntries().filter(e=>e.type==='custom' && e.customType==='dev-platform-binding').length,1);
  } finally {await runtime.dispose();}
  assert.deepEqual(fs.readFileSync(file),bytes);
  console.log(JSON.stringify({passed:true,checks:['real Pi session construction','conversation-local persistence','native new/resume/fork','account and conversation mismatch rejection','outside resume/import cancelled','existing transcript unchanged'],scope:'Offline native lifecycle and fixture transcript; no inference, terminal rendering, account verification or concurrent-writer acceptance'},null,2));
} finally {fs.rmSync(root,{recursive:true,force:true});}
