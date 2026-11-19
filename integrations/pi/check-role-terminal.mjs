/** Offline PTY fixture. Run through check-role-terminal.py, never with live homes. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import { runRoleTerminal } from './role-terminal.mjs';
const root=process.argv[2];
if (!root || process.env.PI_OFFLINE!=='1') throw new Error('Offline fixture directory required');
const agentDir=path.join(root,'auth');fs.mkdirSync(agentDir,{recursive:true});
const identityFile=path.join(root,'identity.md');fs.writeFileSync(identityFile,'Offline Assistant terminal fixture');
const modelRuntime=await ModelRuntime.create({authPath:path.join(agentDir,'auth.json'),modelsPath:null,refreshOnCreate:false,allowModelNetwork:false});
const model=modelRuntime.getModels('openai-codex')[0];
await runRoleTerminal({conversation:{id:'terminal-fixture',agent:'assistant',scope:{kind:'personal'}},
  conversationHome:root,platformRoot:path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),
  agentDir,identityFile,modelRuntime,model,accountRef:'offline-fixture'});
