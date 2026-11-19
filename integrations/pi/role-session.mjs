/** Persistent Pi session construction. The caller owns account selection and TUI. */
import fs from 'node:fs';
import path from 'node:path';
import { createAgentSession, SessionManager } from '@earendil-works/pi-coding-agent';
import { loadRoleResources } from './role-resources.mjs';

export async function createRoleSession(options, suppliedManager) {
  const { conversation, modelRuntime, model, accountRef, resumeFile } = options;
  if (!conversation?.id || !modelRuntime || !model || !accountRef) {
    throw new Error('Explicit conversation, model runtime, model and account reference required');
  }
  const resources = await loadRoleResources(options);
  const directory = resources.sessionDirectory;
  // A conversation's native directory must not escape through a symlink.
  for (const candidate of [options.conversationHome, path.dirname(directory), directory]) {
    if (fs.existsSync(candidate) && fs.lstatSync(candidate).isSymbolicLink()) {
      throw new Error('Conversation storage cannot be a symlink');
    }
  }
  fs.mkdirSync(directory, {recursive:true, mode:0o700});
  const expected = {conversation:conversation.id, agent:conversation.agent, accountRef};
  let manager;
  if (resumeFile || suppliedManager) {
    const candidate = resumeFile || suppliedManager.getSessionFile();
    // /new and a user-message fork can stay in memory until the first reply.
    if (suppliedManager && candidate && !fs.existsSync(candidate)) {
      if (path.dirname(candidate) !== directory || fs.realpathSync(suppliedManager.getCwd()) !== fs.realpathSync(resources.cwd)) {
        throw new Error('New native session differs from conversation binding');
      }
      manager = suppliedManager;
      if (manager.getEntries().length === 0) manager.appendCustomEntry('dev-platform-binding', expected);
      assertManagerBinding(manager,resources.cwd,expected);
    } else {
      manager = openBoundSession(candidate, directory, resources.cwd, expected);
    }
  } else {
    manager = SessionManager.create(resources.cwd, directory);
    manager.appendCustomEntry('dev-platform-binding', expected);
  }
  const result = await createAgentSession({
    cwd:resources.cwd, agentDir:options.agentDir,
    modelRuntime, model, sessionManager:manager,
    sessionStartEvent:options.sessionStartEvent,
    resourceLoader:resources.loader, settingsManager:resources.settingsManager,
  });
  return {...result, resources};
}

export function openBoundSession(candidate, directory, cwd, expected) {
    if (!candidate || !path.isAbsolute(candidate) || !fs.existsSync(candidate) ||
        fs.lstatSync(candidate).isSymbolicLink() ||
        path.dirname(fs.realpathSync(candidate)) !== fs.realpathSync(directory)) {
      throw new Error('Resume requires an existing native file in this conversation');
    }
    const manager = SessionManager.open(candidate, directory);
    assertManagerBinding(manager,cwd,expected);
    return manager;
}

function assertManagerBinding(manager,cwd,expected) {
    if (fs.realpathSync(manager.getCwd()) !== fs.realpathSync(cwd)) {
      throw new Error('Native session workspace differs from conversation binding');
    }
    const bindings = manager.getEntries().filter(e=>e.type==='custom' && e.customType==='dev-platform-binding');
    if (bindings.length !== 1 || Object.entries(expected).some(([k,v])=>bindings[0].data?.[k]!==v)) {
      throw new Error('Native session conversation, role or account binding differs');
    }
}
