/** The role session guard refuses input past the limit and leaves extension input alone. */
import assert from 'node:assert/strict';
import { sessionLengthExtension } from './session-length.mjs';

let handler;
sessionLengthExtension()({ on: (event, h) => { if (event === 'input') handler = h; } });
const send = (prior, source = 'interactive') => {
  const notes = [];
  const entries = Array.from({ length: prior }, () => ({ type: 'message', message: { role: 'user' } }));
  entries.push({ type: 'message', message: { role: 'assistant' } });
  const result = handler({ source, text: 'q' }, { sessionManager: { getEntries: () => entries }, ui: { notify: (_m, level) => notes.push(level) } });
  return [result.action, notes.join(',')];
};
assert.deepEqual(send(5), ['continue', '']);
assert.deepEqual(send(19), ['continue', 'warning']);
assert.deepEqual(send(29), ['continue', 'warning']);
assert.deepEqual(send(30), ['handled', 'error']);
assert.deepEqual(send(30, 'extension'), ['continue', '']);
console.log('session-length: ok');
