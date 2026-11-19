/** Session-length guard for role sessions: warn from turn 20, refuse input after turn 30. */
export function sessionLengthExtension({ warn = 20, stop = 30 } = {}) {
  return (pi) => pi.on('input', (event, ctx) => {
    if (event.source === 'extension') return { action: 'continue' };
    const entries = ctx.sessionManager?.getEntries?.() ?? [];
    const turn = entries.filter(e => e.type === 'message' && e.message?.role === 'user').length + 1;
    if (turn > stop) {
      ctx.ui?.notify?.(`Stop. Session passed ${stop} turns. Start a new session with a 5-line summary.`, 'error');
      return { action: 'handled' };
    }
    if (turn >= warn) ctx.ui?.notify?.(`Session long: turn ${turn} of ${stop}. Start fresh for judgments.`, 'warning');
    return { action: 'continue' };
  });
}
