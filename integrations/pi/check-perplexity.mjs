import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DefaultResourceLoader, SettingsManager } from '@earendil-works/pi-coding-agent';

const root=fs.mkdtempSync(path.join(os.tmpdir(),'pi-perplexity-'));
const savedKey=process.env.PERPLEXITY_API_KEY;
try {
  const loader=new DefaultResourceLoader({cwd:root,agentDir:path.join(root,'agent'),
    settingsManager:SettingsManager.inMemory(),noExtensions:true,noSkills:true,
    noContextFiles:true,noPromptTemplates:true,noThemes:true,
    additionalExtensionPaths:[fileURLToPath(new URL('./perplexity.ts',import.meta.url))]});
  await loader.reload();
  const loaded=loader.getExtensions();
  assert.deepEqual(loaded.errors,[]);
  const tool=loaded.extensions[0].tools.get('perplexity_search').definition;
  delete process.env.PERPLEXITY_API_KEY;
  await assert.rejects(()=>tool.execute('missing',{query:'public documentation'}),
    {message:'Perplexity search is unavailable: configure PERPLEXITY_API_KEY through the protected launch environment, not chat.'});
  process.env.PERPLEXITY_API_KEY='synthetic-never-sent';
  const controller=new AbortController();
  controller.abort();
  await assert.rejects(()=>tool.execute('cancelled',{query:'public documentation'},controller.signal),
    {message:'Perplexity search failed or was cancelled. Check protected credentials, service status and filters; no provider error body is included.'});
  console.log(JSON.stringify({passed:true,checks:['native extension loading','missing credentials','pre-aborted execution'],
    scope:'Actual registered tool; no live query, credential migration or success-path acceptance.'},null,2));
} finally {
  if(savedKey===undefined) delete process.env.PERPLEXITY_API_KEY;
  else process.env.PERPLEXITY_API_KEY=savedKey;
  fs.rmSync(root,{recursive:true,force:true});
}
