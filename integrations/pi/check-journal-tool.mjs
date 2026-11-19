/** Offline checks for the journal tool: every role reads the journal, none writes in it,
 *  and what a role adds lands in the inbox (or, for Assistant's own log, in his memory). */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { journalExtension } from './journal-tool.mjs';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'journal-tool-'));
const journal = path.join(tmp, 'journal'), inbox = path.join(tmp, 'inbox'), memory = path.join(tmp, 'memory');
const today = new Date().toLocaleDateString('sv-SE');
const [y, m, d] = today.split('-');
fs.mkdirSync(path.join(journal, 'tasks/open/2026'), {recursive:true});
fs.mkdirSync(path.join(journal, 'log', y, m), {recursive:true});
fs.mkdirSync(inbox); fs.mkdirSync(memory);
fs.writeFileSync(path.join(journal, 'tasks/open/2026/pay-rent.txt'), 'pay the rent\ndetail\n');
fs.writeFileSync(path.join(journal, 'tasks/open/2026/call-bank.txt'), 'call the bank\ndue: 2026-10-09\npriority: high\ntags: money home\n');
fs.writeFileSync(path.join(journal, 'log', y, m, `${d}.txt`), 'a quiet day\n');
const snapshot = () => JSON.stringify(fs.readdirSync(journal, {recursive:true}).sort().map(f => {
  const p = path.join(journal, f); return [f, fs.statSync(p).isFile() ? fs.readFileSync(p, 'utf8') : ''];
}));
const before = snapshot();

function tool(agent) {
  let registered;
  journalExtension({root:journal, agent, inbox, memory})({registerTool: t => { registered = t; }});
  return params => registered.execute('id', params);
}
const text = r => r.content[0].text;

for (const agent of ['assistant', 'engineer', 'ops']) {
  const run = tool(agent);
  assert.match(text(await run({action:'tasks'})), /pay the rent/);
  { const t = JSON.parse(text(await run({action:'tasks'}))).find(x => x.task === 'call the bank');
    assert.equal(t.due, '2026-10-09'); assert.equal(t.priority, 'high'); assert.equal(t.tags, 'money home'); }
  assert.match(text(await run({action:'day'})), /a quiet day/);
  assert.match(text(await run({action:'work', summary:'fixed it', project:'globex', minutes:30})), /inbox/);
}
const entries = JSON.parse(text(await tool('assistant')({action:'entries'})));
assert.equal(entries.length, 3);
assert.ok(entries.every(e => e.project === 'globex' && e.billable));
assert.deepEqual(entries.map(e => e.role).sort(), ['Assistant', 'Engineer', 'Ops']);

// Only Assistant proposes tasks and journal lines; both go to the inbox.
await assert.rejects(tool('engineer')({action:'task', text:'x'}), /not available to Engineer/);
await assert.rejects(tool('ops')({action:'journal-line', body:'x'}), /not available to Ops/);
await tool('assistant')({action:'task', text:'call the bank'});
await tool('assistant')({action:'journal-line', body:'a good session'});
assert.equal(fs.readdirSync(inbox).filter(f => /-assistant-(task|journal-line)-/.test(f)).length, 2);

// Assistant's own log is in his memory.
await tool('assistant')({action:'log-append', title:'morning', body:'notes'});
assert.match(fs.readFileSync(path.join(memory, 'days', `${today}.md`), 'utf8'), /## morning/);

// Bad dates are refused; the journal itself never changed.
await assert.rejects(tool('ops')({action:'day', date:'yesterday'}), /YYYY-MM-DD/);
assert.equal(snapshot(), before);
fs.rmSync(tmp, {recursive:true, force:true});
console.log('journal tool: ok');
