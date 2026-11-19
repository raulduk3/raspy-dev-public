/** Explicit role resources for Pi; no auth, dispatch or model calls. */
import fs from 'node:fs';
import path from 'node:path';
import { DefaultResourceLoader, SettingsManager } from '@earendil-works/pi-coding-agent';
import { historyExtension } from './history-tool.mjs';
import { memoryExtension } from './memory-tool.mjs';
import { journalExtension } from './journal-tool.mjs';
import { webFetchExtension } from './web-fetch-tool.mjs';
import { sessionLengthExtension } from './session-length.mjs';
import sessionTitle from './session-title.mjs';

// Each role's skills, by path from the platform root: one table (agents/skills.json) that the
// Claude Code and Codex homes read too (guardrails.py). Discovery stays off; these load explicitly.
export const ROLE_SKILLS = JSON.parse(fs.readFileSync(new URL('../../agents/skills.json', import.meta.url), 'utf8'));
// Where a project keeps its own skills. Engineer, working in the project, loads those that exist;
// a name the platform already gave it stays the platform's (Pi keeps the first and notes the collision).
export const PROJECT_SKILL_DIRS = ['.agents/skills', '.claude/skills', '.pi/skills'];

// /goal (pi-goal-x): a persistent objective the role keeps working toward. Pinned in package.json
// and loaded by the entry its own package declares, since automatic discovery is off.
export function goalExtensionPath(platformRoot) {
  const root = path.join(platformRoot, 'integrations/pi/node_modules/pi-goal-x');
  const [entry] = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8')).pi.extensions;
  return path.join(root, entry);
}

export function roleSkillPaths(agent, platformRoot, cwd, project) {
  const own = ROLE_SKILLS[agent].map(p => path.join(platformRoot, p));
  const local = agent === 'engineer' && project
    ? PROJECT_SKILL_DIRS.map(p => path.join(cwd, p)).filter(p => fs.existsSync(p) && fs.statSync(p).isDirectory())
    : [];
  return [...own, ...local];
}

export async function loadRoleResources({ conversation, conversationHome, platformRoot, agentDir, identityFile, historyArchive, memoryState, journalRoot, inboxRoot, extensionFactories = [] }) {
  const { agent, scope, binding } = conversation;
  if (!['assistant','engineer','ops'].includes(agent)) throw new Error('Unknown agent role');
  const project = ['project','formation'].includes(scope?.kind);
  if (agent === 'assistant' && scope?.kind !== 'personal') throw new Error('Assistant requires personal scope');
  if (agent === 'engineer' && !project) throw new Error('Engineer requires project scope');
  if (agent === 'ops' && !project && scope?.kind !== 'system') throw new Error('Ops requires system or project scope');
  if (!path.isAbsolute(conversationHome) || !path.isAbsolute(platformRoot) || !path.isAbsolute(agentDir) || !path.isAbsolute(identityFile)) {
    throw new Error('Role resource paths must be absolute');
  }
  if (memoryState !== undefined && !path.isAbsolute(memoryState)) throw new Error('Memory state root must be absolute');
  if (journalRoot !== undefined && !path.isAbsolute(journalRoot)) throw new Error('Journal root must be absolute');
  if (journalRoot !== undefined && (!inboxRoot || !path.isAbsolute(inboxRoot))) throw new Error('The journal needs the owner\'s inbox for what a role adds');
  // Every role reads the journal and none writes it; additions go to the owner's inbox (the tool decides).
  // Personal/system sessions execute in their neutral conversation workspace.
  // Invocation cwd never participates in resource selection.
  let cwd;
  if (project) {
    if (!binding?.workspace || !path.isAbsolute(binding.workspace)) throw new Error('Missing explicit workspace');
    cwd = fs.realpathSync(binding.workspace);
    if (!fs.statSync(cwd).isDirectory()) throw new Error('Workspace is not a directory');
  } else {
    cwd = path.join(conversationHome, 'workspace');
    if (fs.existsSync(cwd) && fs.lstatSync(cwd).isSymbolicLink()) throw new Error('Neutral workspace cannot be a symlink');
    fs.mkdirSync(cwd,{recursive:true,mode:0o700});
  }
  const identity = {path:identityFile,content:fs.readFileSync(identityFile,'utf8')};
  // Startup guidance must be in context, not merely available for skill discovery.
  const entryPath = path.join(platformRoot,'skills/develop/SKILL.md');
  const entry = {path:entryPath,content:fs.readFileSync(entryPath,'utf8')};
  // The role's own memory index rides in context so it starts oriented; the daily
  // corpus and the inherited records stay behind the agent_memory tool.
  let memory = null;
  if (memoryState) {
    const indexPath = path.join(memoryState, agent, 'memory', 'MEMORY.md');
    if (fs.existsSync(indexPath) && !fs.lstatSync(indexPath).isSymbolicLink()) {
      memory = {path:indexPath, content:fs.readFileSync(indexPath,'utf8')};
    }
  }
  const settingsManager = SettingsManager.inMemory();
  const loader = new DefaultResourceLoader({
    cwd, agentDir, settingsManager,
    noExtensions:true, noSkills:true, noPromptTemplates:true, noThemes:true,
    additionalExtensionPaths:[path.join(platformRoot,'integrations/pi/perplexity.ts'), goalExtensionPath(platformRoot)],
    // Every role can read a public page it has the address for; search finds the address.
    extensionFactories:[webFetchExtension(), sessionLengthExtension(), pi => sessionTitle(pi, {who:agent}), ...((Array.isArray(historyArchive) ? historyArchive.length : historyArchive) ? [historyExtension({archive:historyArchive,agent})] : []),
      ...(memoryState ? [memoryExtension({agent, state:memoryState})] : []),
      ...(journalRoot ? [journalExtension({root:journalRoot, agent, inbox:inboxRoot, memory:memoryState ? path.join(memoryState, agent, 'memory') : undefined})] : []),
      ...extensionFactories],
    noContextFiles:!project,
    additionalSkillPaths:roleSkillPaths(agent, platformRoot, cwd, project),
    agentsFilesOverride:base=>({agentsFiles:[entry,identity,...(memory?[memory]:[]),...(project?base.agentsFiles:[])]}),
  });
  await loader.reload();
  if (loader.getExtensions().errors.length) throw new Error('Role extension loading failed');
  const errors = loader.getSkills().diagnostics.filter(d=>d.type==='error');
  if (errors.length) throw new Error('Role skill loading failed');
  return {cwd,loader,settingsManager,memoryIndex:memory?.path ?? null,sessionDirectory:path.join(conversationHome,'native/pi')};
}
