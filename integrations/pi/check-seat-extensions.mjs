// Offline check of the Pi seat extensions: the guard refuses what the platform
// guard refuses and allows the rest; the advice tool resolves its model from the model file
// and builds an OpenRouter request without a network call. Run: node integrations/pi/check-seat-extensions.mjs
import assert from "node:assert/strict";
import seatGuard, { check } from "./seat-guard.mjs";
import adviceTool, { adviceModel, request } from "./advice-tool.mjs";
import workerLimits from "./worker-limits.mjs";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

let handler;
seatGuard({ on: (name, fn) => { assert.equal(name, "tool_call"); handler = fn; } });
const cwd = process.cwd();
for (const command of ["git push origin main", "git push --force origin feat/x", "git reset --hard HEAD~1",
  "git rebase main", "gh pr merge 3", "sudo systemctl restart nginx"]) {
  const verdict = await handler({ toolName: "bash", input: { command } }, { cwd });
  assert.equal(verdict?.block, true, `${command} must be refused`);
}
for (const command of ["git status", "bun run check", "git commit -m 'fix: x'", "ls -la"]) {
  assert.equal(await handler({ toolName: "bash", input: { command } }, { cwd }), undefined, `${command} must pass`);
}
assert.equal(await handler({ toolName: "read", input: { path: "x" } }, { cwd }), undefined);
assert.equal(check("ls", cwd, "/nonexistent/guard.sh")?.block, true, "a guard that cannot run refuses");

let tool;
adviceTool({ registerTool: (t) => { tool = t; } });
assert.equal(tool.name, "ask_advice");
const choice = adviceModel();
assert.match(choice.model, /^[a-z0-9-]+\/[a-z0-9.-]+$/);
const body = request("Which approach?", "diff here", choice);
assert.equal(body.model, choice.model);
assert.equal(body.messages.length, 2);
const saved = process.env.OPENROUTER_API_KEY;
delete process.env.OPENROUTER_API_KEY;
await assert.rejects(tool.execute("1", { question: "q" }), /no OpenRouter key/);
if (saved !== undefined) process.env.OPENROUTER_API_KEY = saved;
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "worker-limits-"));
const run = (env, changed = () => false) => {
  const handlers = {};
  workerLimits({ on: (name, fn) => { handlers[name] = fn; } }, env, changed);
  return handlers;
};
// The dollar cap, from the provider's own cost; a ctx whose abort throws (a finished turn) does not crash the stop.
let dir = tmp(), h = run({ LOOP_WORKER_COST_LIMIT: "1.00" }), aborted = 0, ended = 0;
let ctx = { cwd: dir, abort: () => { aborted += 1; throw new Error("stale ctx"); }, shutdown: () => { ended += 1; } };
await h.message_end({ message: { role: "assistant", usage: { totalTokens: 900000, cost: { total: 0.6 } } } }, ctx);
assert.equal(await h.tool_call({}, ctx), undefined, "under the dollar cap, tools run");
await h.message_end({ message: { role: "assistant", usage: { totalTokens: 900000, cost: { total: 0.5 } } } }, ctx);
assert.equal(aborted + ended, 2, "the cap aborts and ends Pi, even when abort throws");
assert.match(fs.readFileSync(path.join(dir, ".worker-blocked.md"), "utf8"), /\$1\.10 spent, cap \$1\.00/);
assert.equal((await h.tool_call({}, ctx))?.block, true, "a stopped worker runs no more tools");
fs.rmSync(dir, { recursive: true, force: true });
// No change by the first-change turn stops the run early; a change lets it go on.
dir = tmp(); h = run({ LOOP_WORKER_FIRST_CHANGE: "3", LOOP_WORKER_MAX_TURNS: "50" });
for (let i = 0; i < 3; i++) await h.turn_end({}, { cwd: dir, abort() {}, shutdown() {} });
assert.match(fs.readFileSync(path.join(dir, ".worker-blocked.md"), "utf8"), /no change in the worktree after 3 turns/);
fs.rmSync(dir, { recursive: true, force: true });
dir = tmp(); h = run({ LOOP_WORKER_FIRST_CHANGE: "3", LOOP_WORKER_MAX_TURNS: "5" }, () => true);
for (let i = 0; i < 4; i++) await h.turn_end({}, { cwd: dir, abort() {}, shutdown() {} });
assert.equal(fs.existsSync(path.join(dir, ".worker-blocked.md")), false, "a worker with a change goes on");
await h.turn_end({}, { cwd: dir, abort() {}, shutdown() {} });
assert.match(fs.readFileSync(path.join(dir, ".worker-blocked.md"), "utf8"), /5 turns, cap 5/);
fs.rmSync(dir, { recursive: true, force: true });
console.log(`seat extensions ok (advice model ${choice.model}${choice.effort ? `, effort ${choice.effort}` : ""})`);
