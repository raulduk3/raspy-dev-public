/** worker_limits: a loop worker on Pi stops at its caps, in money, turns and progress.
 *
 *  On an API key every request is paid for. The loop sets, in the worker's environment:
 *    LOOP_WORKER_COST_LIMIT      dollars this run may spend (the provider's own cost per request)
 *    LOOP_WORKER_MAX_TURNS       turns
 *    LOOP_WORKER_FIRST_CHANGE    turns by which the worktree must show a change (a commit or an
 *                                edited file); a worker still only reading by then stops, so a run
 *                                that is not converging ends early and cheaply, and the loop's retry
 *                                takes it on a stronger model
 *    LOOP_WORKER_BASE            the branch the worker's branch was cut from
 *    LOOP_WORKER_TOKEN_LIMIT     a backstop in billed tokens, only when a provider reports no cost
 *  Over any cap the worker writes .worker-blocked.md (fold refuses a blocked worker; the control
 *  seat reads why), refuses further tool calls and ends Pi. */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const number = (value, fallback) => {
  const n = Number.parseFloat(value ?? "");
  return Number.isFinite(n) && n > 0 ? n : fallback;
};

export function limits(env = process.env) {
  return {
    dollars: number(env.LOOP_WORKER_COST_LIMIT, 2),
    turns: Math.round(number(env.LOOP_WORKER_MAX_TURNS, 60)),
    firstChange: Math.round(number(env.LOOP_WORKER_FIRST_CHANGE, 20)),
    tokens: Math.round(number(env.LOOP_WORKER_TOKEN_LIMIT, 20000000)),
    base: env.LOOP_WORKER_BASE || "",
  };
}

/** True when the worktree has a commit beyond the base or a changed file (worker notes aside). */
export function changed(cwd, base, run = spawnSync) {
  if (base) {
    const ahead = run("git", ["-C", cwd, "rev-list", "--count", `${base}..HEAD`], { encoding: "utf8" });
    if (ahead.status === 0 && Number.parseInt(ahead.stdout, 10) > 0) return true;
  }
  const status = run("git", ["-C", cwd, "status", "--porcelain"], { encoding: "utf8" });
  return status.status === 0 && status.stdout.split("\n").some((line) => line.trim() && !line.includes(".worker-"));
}

export default function workerLimits(pi, env = process.env, isChanged = changed) {
  const cap = limits(env);
  let turns = 0, tokens = 0, dollars = 0, priced = false, stopped = null;
  const stop = (ctx, why) => {
    if (stopped) return;
    stopped = why;
    const cwd = ctx?.cwd ?? process.cwd();
    try {
      fs.writeFileSync(path.join(cwd, ".worker-blocked.md"), `# Stopped by its limits\n\nThis worker stopped: ${why}. ` +
        `The work so far is on this branch, uncommitted changes included. The control seat decides: resume (the loop's ` +
        `retry runs on a stronger model when the branch has no commit), split the task, widen its scope, or drop it.\n`);
    } catch { /* the note is best effort; the stop is not */ }
    try { ctx?.abort?.(); } catch { /* a finished turn has nothing to abort */ }
    try { ctx?.shutdown?.(); } catch { /* Pi may already be ending */ }
  };
  pi.on("message_end", async (event, ctx) => {
    const usage = event.message?.role === "assistant" ? event.message.usage : undefined;
    if (!usage) return;
    if (Number.isFinite(usage.totalTokens)) tokens += usage.totalTokens;
    const cost = usage.cost?.total;
    if (Number.isFinite(cost)) { dollars += cost; priced = true; }
    if (priced && dollars >= cap.dollars) stop(ctx, `$${dollars.toFixed(2)} spent, cap $${cap.dollars.toFixed(2)}`);
    else if (!priced && tokens >= cap.tokens) stop(ctx, `${tokens} billed tokens, cap ${cap.tokens}`);
  });
  pi.on("turn_end", async (_event, ctx) => {
    turns += 1;
    if (turns >= cap.turns) return stop(ctx, `${turns} turns, cap ${cap.turns}`);
    if (turns === cap.firstChange && !isChanged(ctx?.cwd ?? process.cwd(), cap.base)) {
      stop(ctx, `no change in the worktree after ${turns} turns (the brief asks for a first change by then)`);
    }
  });
  pi.on("tool_call", async () => (stopped ? { block: true, reason: `worker stopped: ${stopped}` } : undefined));
  return { state: () => ({ turns, tokens, dollars, stopped }) };
}
