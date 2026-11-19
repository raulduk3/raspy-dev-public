/** Native Pi lifecycle with a fixed role/conversation/account boundary. */
import path from 'node:path';
import { AgentSessionRuntime } from '@earendil-works/pi-coding-agent';
import { createRoleSession, openBoundSession } from './role-session.mjs';

export async function createRoleRuntime(options) {
  let boundCwd;
  const directory = path.join(options.conversationHome,'native/pi');
  const expected = {conversation:options.conversation.id,agent:options.conversation.agent,accountRef:options.accountRef};
  const guard = pi => {
    pi.on('session_before_switch', (event, ctx) => {
      if (event.reason === 'new') return;
      try { openBoundSession(event.targetSessionFile, directory, boundCwd, expected); }
      catch {
        ctx.ui.notify('Choose a native session already bound to this conversation and account. Start another conversation separately.','warning');
        return {cancel:true};
      }
    });
  };
  const construct = async (manager, event, resumeFile) => {
    const result = await createRoleSession({...options, resumeFile, sessionStartEvent:event,
      extensionFactories:[...(options.extensionFactories ?? []), guard]},manager);
    boundCwd = result.resources.cwd;
    const services = {cwd:boundCwd,agentDir:options.agentDir,modelRuntime:options.modelRuntime,
      settingsManager:result.resources.settingsManager,resourceLoader:result.resources.loader,diagnostics:[]};
    return {...result,services,diagnostics:[]};
  };
  const first = await construct(undefined,undefined,options.resumeFile);
  return new AgentSessionRuntime(first.session,first.services,
    ({sessionManager,sessionStartEvent})=>construct(sessionManager,sessionStartEvent),[],first.modelFallbackMessage);
}
