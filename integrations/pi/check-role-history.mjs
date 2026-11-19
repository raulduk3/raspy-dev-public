import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { loadRoleResources } from './role-resources.mjs';

const platformRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'pi-history-'));
const savedRole=process.env.AI_AGENT_ROLE;
const savedArchive=process.env.AI_HISTORY_ARCHIVE;
try {
  const archive=path.join(root,'archive');
  execFileSync('python3',['-c',`
import sqlite3, pathlib, json, sys
root=pathlib.Path(sys.argv[1])/'sqlite-consistent'
root.mkdir(parents=True)
for agent, store in [('assistant','main'),('engineer','hermes'),('ops','ops')]:
    with sqlite3.connect(root/(store+'.sqlite')) as c:
        c.executescript('''CREATE TABLE session_nodes(session_key,current_session_id,label,display_name,updated_at);
        CREATE TABLE session_windows(session_id,session_key,previous_session_id,reason,created_at,updated_at);
        CREATE TABLE transcript_events(session_id,seq,event_json,created_at);''')
        c.execute('INSERT INTO session_nodes VALUES(?,?,?,?,?)',(agent,agent+'-session','History '+agent,agent,1))
        c.execute('INSERT INTO session_windows VALUES(?,?,?,?,?,?)',(agent+'-session',agent,None,'start',1,1))
        c.execute('INSERT INTO transcript_events VALUES(?,?,?,?)',(agent+'-session',0,json.dumps({'message':{'role':'user','content':agent+' original text'}}),1))
        for n in range(2,16):
            c.execute('INSERT INTO session_windows VALUES(?,?,?,?,?,?)',(agent+'-window-'+str(n),agent,None,'reset',n,n))
`,archive]);
  const fingerprint=()=>fs.readdirSync(path.join(archive,'sqlite-consistent')).sort().map(name=>
    createHash('sha256').update(fs.readFileSync(path.join(archive,'sqlite-consistent',name))).digest('hex'));
  const before=fingerprint();
  const identityFile=path.join(root,'identity.md');fs.writeFileSync(identityFile,'Test identity');
  // Conflicting inherited values must not control embedded roles.
  process.env.AI_AGENT_ROLE='incorrect';process.env.AI_HISTORY_ARCHIVE='/nonexistent';
  for(const [agent,kind] of [['assistant','personal'],['engineer','formation'],['ops','system']]) {
    const result=await loadRoleResources({conversation:{agent,scope:{kind},binding:{workspace:root}},
      conversationHome:path.join(root,agent),platformRoot,agentDir:path.join(root,'auth'),identityFile,historyArchive:archive});
    const tool=result.loader.getExtensions().extensions.flatMap(e=>[...e.tools.values()])
      .find(t=>t.definition.name==='agent_history').definition;
    const call=async params=>JSON.parse((await tool.execute('history',params)).content[0].text);
    const found=await call({action:'find',value:'History'});
    assert.equal(found.agent,agent);
    assert.deepEqual(found.result.map(r=>r.label),['History '+agent]);
    const read=await call({action:'read',value:agent+'-session'});
    assert.equal(read.result.messages[0].text,agent+' original text');
    const firstPage=await call({action:'windows',value:agent});
    assert.equal(firstPage.result.length,10);
    assert.equal(firstPage.next_offset,10);
    assert.equal(firstPage.has_more,true);
    const lastPage=await call({action:'windows',value:agent,offset:firstPage.next_offset});
    assert.equal(lastPage.result.length,5);
    assert.equal(lastPage.next_offset,null);
    assert.equal(lastPage.has_more,false);
    assert.deepEqual([...firstPage.result,...lastPage.result].map(row=>row.session_id),
      [agent+'-session',...Array.from({length:14},(_,i)=>agent+'-window-'+(i+2))]);
    const exhausted=await call({action:'find',value:'History',offset:1});
    assert.deepEqual(exhausted.result,[]);
    assert.equal(exhausted.next_offset,null);
    const other=agent==='assistant'?'engineer':'assistant';
    await assert.rejects(()=>call({action:'read',value:other+'-session'}),
      {message:'Historical lookup failed or exceeded its output bound; narrow the request or inspect the archive locally.'});
  }
  assert.deepEqual(fingerprint(),before);
  console.log(JSON.stringify({passed:true,roles:3,checks:['explicit role wins over inherited environment','original messages retrieved','15 saved windows paged without loss or duplication','exhausted search page','cross-role session rejected','archive bytes unchanged'],scope:'Actual Pi registered tools and real SQLite/CLI; no model invocation'},null,2));
} finally {
  for(const [name,value] of [['AI_AGENT_ROLE',savedRole],['AI_HISTORY_ARCHIVE',savedArchive]]) {
    if(value===undefined) delete process.env[name];else process.env[name]=value;
  }
  fs.rmSync(root,{recursive:true,force:true});
}
