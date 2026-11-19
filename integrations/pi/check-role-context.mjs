import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadRoleResources, ROLE_SKILLS } from './role-resources.mjs';
const GOAL_TOOLS=['get_goal','create_goal','update_goal','set_goal_tasks','update_goal_task','goal_question','goal_questionnaire','propose_goal_draft'];
const platformRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'pi-role-context-'));
const original=process.cwd();
try {
  const project=path.join(root,'project'); fs.mkdirSync(project);
  fs.writeFileSync(path.join(project,'AGENTS.md'),'BOUND_PROJECT_CONTEXT');
  const other=path.join(root,'other'); fs.mkdirSync(other);
  fs.writeFileSync(path.join(other,'AGENTS.md'),'UNRELATED_PROJECT_CONTEXT');
  const identityFile=path.join(root,'identity.md');fs.writeFileSync(identityFile,'ROLE_IDENTITY');
  const checked=[];
  for(const [agent,kind] of [['assistant','personal'],['engineer','project'],['engineer','formation'],['ops','system'],['ops','project']]) {
    const conversationHome=path.join(root,agent+'-'+kind);fs.mkdirSync(conversationHome);
    for(const invoking of [project,other]) {
      process.chdir(invoking);
      const selected=['project','formation'].includes(kind);
      const result=await loadRoleResources({conversation:{agent,scope:{kind},binding:selected?{workspace:project}:{}},conversationHome,platformRoot,agentDir:path.join(root,'auth'),identityFile});
      assert.equal(result.cwd,selected?fs.realpathSync(project):path.join(conversationHome,'workspace'));
      const contents=result.loader.getAgentsFiles().agentsFiles.map(f=>f.content).join('\n');
      const entryPath=path.join(platformRoot,'skills/develop/SKILL.md');
      const entries=result.loader.getAgentsFiles().agentsFiles.filter(f=>f.path===entryPath);
      assert.equal(entries.length,1);
      assert.equal(entries[0].content,fs.readFileSync(entryPath,'utf8'));
      const extensions=result.loader.getExtensions();
      assert.deepEqual(extensions.errors,[]);
      // Search, /goal and page reading for every role.
      assert.deepEqual(extensions.extensions.flatMap(e=>[...e.tools.keys()]),
        ['perplexity_search',...GOAL_TOOLS,'web_fetch','session_title']);
      assert(extensions.extensions.some(e=>e.commands.has('goal')));
      assert(contents.includes('ROLE_IDENTITY'));
      assert.equal(contents.includes('BOUND_PROJECT_CONTEXT'),selected);
      assert(!contents.includes('UNRELATED_PROJECT_CONTEXT'));
      assert.deepEqual(result.loader.getSkills().skills.map(s=>s.name).sort(),ROLE_SKILLS[agent].map(p=>path.basename(p)).sort());
      assert.equal(result.sessionDirectory,path.join(conversationHome,'native/pi'));
    }
    checked.push({agent,kind});
  }
  console.log(JSON.stringify({passed:true,invocations:10,checked,scope:'Reusable role resource loader; no authenticated session or production process launched'},null,2));
} finally {process.chdir(original);fs.rmSync(root,{recursive:true,force:true});}
