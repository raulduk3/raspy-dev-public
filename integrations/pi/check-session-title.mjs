// Offline check of the Pi session-title extension: a new session gets a conforming name, a
// conforming name is kept, the first prompt names an untitled session, resumed sessions keep
// their title. Run: node integrations/pi/check-session-title.mjs
import assert from "node:assert/strict";
import sessionTitle, { conforms, formatTitle } from "./session-title.mjs";

function fake({ name, who } = {}) {
  const handlers = {}; const calls = { names: [], titles: [] }; let tool; let current = name;
  const pi = {
    on: (event, fn) => { handlers[event] = fn; },
    registerTool: (t) => { tool = t; },
    getSessionName: () => current,
    setSessionName: (n) => { current = n; calls.names.push(n); },
  };
  sessionTitle(pi, { who });
  const ctx = { cwd: process.cwd(), model: { provider: "openrouter", id: "moonshotai/kimi-k2.6" }, ui: { setTitle: (t) => calls.titles.push(t) } };
  return { handlers, calls, ctx, tool: () => tool, name: () => current };
}

delete process.env.DEV_SESSION_WHO; delete process.env.DEV_SESSION_PROVIDER; delete process.env.DEV_SESSION_MODEL;

let s = fake({ who: "ops" });
await s.handlers.session_start({ reason: "startup" }, s.ctx);
assert.match(s.name(), /^\[[^\]]+\] chat\(misc\): Untitled session · ops/);
assert.match(s.name(), / · ops · pi · openrouter\/kimi-k2\.6 · interactive · \d{4}-\d{2}-\d{2}$/);
assert.equal(s.calls.titles.at(-1), s.name(), "terminal title follows");
await s.handlers.input({ text: "Align the photo captions\nmore", source: "interactive" }, s.ctx);
assert.match(s.name(), /^\[[^\]]+\] [a-z]+\([a-z0-9-]+\): Align the photo captions · ops/);

s = fake({ name: formatTitle("fix(ui): Keep me #4", { cwd: process.cwd() }, "owner") });
const kept = s.name();
await s.handlers.session_start({ reason: "startup" }, s.ctx);
await s.handlers.input({ text: "something else", source: "interactive" }, s.ctx);
assert.equal(s.name(), kept, "a conforming title is never replaced");

s = fake({ name: "old plain title" });
await s.handlers.session_start({ reason: "resume" }, s.ctx);
assert.equal(s.name(), "old plain title", "a resumed session keeps its title");
await s.handlers.session_start({ reason: "startup" }, s.ctx);
assert.match(s.name(), /[a-z]+\([a-z0-9-]+\): Old plain title/);

process.env.DEV_SESSION_WHO = "loop#12"; process.env.DEV_SESSION_TYPE = "headless";
s = fake({ who: "assistant" });
await s.handlers.session_start({ reason: "new" }, s.ctx);
assert.match(s.name(), / · loop#12 · pi · .* · headless · /, "launcher variables win");
delete process.env.DEV_SESSION_WHO; delete process.env.DEV_SESSION_TYPE;

s = fake();
const out = await s.tool().execute("1", { what: "feat(pi): Name sessions #9" }, undefined, undefined, s.ctx);
assert.match(out.content[0].text, /feat\(pi\): Name sessions #9/);
assert.ok(conforms(s.name()));
console.log("session-title: ok");
