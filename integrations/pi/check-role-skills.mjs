import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DefaultResourceLoader, SettingsManager } from '@earendil-works/pi-coding-agent';
import { ROLE_SKILLS, roleSkillPaths } from './role-resources.mjs';

const repository = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const skill = path.join(repository, 'agents/engineer/skills/engineering');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pi-role-skills-'));
const results = [];
try {
  // Fixtures deliberately contain an unrelated discoverable skill and repository context.
  const inherited = path.join(root, '.pi/skills/unwanted');
  fs.mkdirSync(inherited, {recursive:true});
  fs.writeFileSync(path.join(inherited,'SKILL.md'), '---\nname: unwanted\ndescription: Unrelated fixture\n---\nDo not inherit.\n');
  fs.writeFileSync(path.join(root,'AGENTS.md'),'UNRELATED_REPOSITORY_CONTEXT');
  // A project's own skills: one new, one named like a platform skill (the platform's must win).
  const write = (dir, name, body) => { fs.mkdirSync(dir,{recursive:true});
    fs.writeFileSync(path.join(dir,'SKILL.md'), `---\nname: ${name}\ndescription: Project fixture\n---\n${body}\n`); };
  const bound = path.join(root,'bound');
  write(path.join(bound,'.agents/skills/project-own'), 'project-own', 'PROJECT_OWN');
  write(path.join(bound,'.claude/skills/intake'), 'intake', 'PROJECT_INTAKE');
  const expected = {assistant:[], ops:[],
    engineer:['dev-plat','development-workspace','distill','intake','engineering','loop','new-repo','setup-rig','spec-lint']};
  for (const [agent, project] of [['assistant',false],['ops',false],['ops',true],['engineer',false],['engineer',true]]) {
    const loader = new DefaultResourceLoader({cwd:root, agentDir:path.join(root,'config'),
      settingsManager:SettingsManager.inMemory(), noExtensions:true, noSkills:true,
      noContextFiles:true, noPromptTemplates:true, noThemes:true,
      additionalSkillPaths:roleSkillPaths(agent, repository, project?bound:root, project)});
    await loader.reload();
    const loaded = loader.getSkills();
    const local = agent==='engineer' && project;
    assert.equal(ROLE_SKILLS[agent].length, expected[agent].length);
    assert.deepEqual(loaded.diagnostics.filter(d=>d.type!=='collision'), []);
    assert.deepEqual(loaded.diagnostics.map(d=>d.collision?.name ?? d.message), local?['intake']:[]);
    assert.deepEqual(loaded.skills.map(s=>s.name).sort(), [...expected[agent], ...(local?['project-own']:[])].sort());
    if (local) assert(loaded.skills.find(s=>s.name==='intake').filePath.startsWith(repository));
    assert.deepEqual(loader.getAgentsFiles().agentsFiles,[]);
    results.push({agent,project,skills:loaded.skills.map(s=>s.name)});
  }
  const body = fs.readFileSync(path.join(skill,'SKILL.md'),'utf8');
  const links = [...body.matchAll(/\]\(((?:references\/|\.\.\/\.\.\/\.\.\/\.\.\/skills\/principle-)[^)]+)\)/g)].map(m=>m[1]);
  assert.equal(links.filter(p=>p.includes('/skills/principle-')).length,23);
  for (const relative of links) assert(fs.statSync(path.join(skill,relative)).isFile(),relative);
  console.log(JSON.stringify({passed:true,results,referenceFiles:links.length,
    scope:'Actual Pi resource loader with isolated fixtures; no inference, authentication, or production launcher tested.'},null,2));
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
