/** session_title: every Pi session gets a title in the platform format (docs/session-naming.md).
 *
 *  On session_start and on the first input, a name that does not pass `ai-title check` is replaced.
 *  `bin/ai-title` is the only formatter; this file adds the Pi context (client, provider/model,
 *  who). A name that already conforms, such as one the owner set, is never changed. The agent also
 *  gets a `session_title` tool, so it can set `purpose(area): Description #ref` when the task is clear. */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CANDIDATES = [path.resolve(HERE, "../../bin/ai-title"), "/opt/dev-platform/current/bin/ai-title",
  path.join(os.homedir(), ".local/share/dev-platform-naming/bin/ai-title")];

export function aiTitle() {
  if (process.env.AI_TITLE_BIN) return process.env.AI_TITLE_BIN;
  return CANDIDATES.find((file) => fs.existsSync(file)) ?? "ai-title";
}

function run(args, bin = aiTitle()) {
  const r = spawnSync(bin, args, { encoding: "utf8", timeout: 5000 });
  return { ok: r.status === 0, out: (r.stdout ?? "").trim() };
}

export function conforms(name, bin) {
  return typeof name === "string" && name !== "" && run(["check", name], bin).ok;
}

/** Pi provider and model id to the title's provider/model: openrouter + moonshotai/kimi-k2.6. */
export function providerModel(ctx) {
  return {
    provider: process.env.DEV_SESSION_PROVIDER || ctx?.model?.provider,
    model: process.env.DEV_SESSION_MODEL || ctx?.model?.id,
  };
}

export function formatTitle(what, ctx, who, bin) {
  const { provider, model } = providerModel(ctx);
  const args = ["format", "--client", "pi", "--cwd", ctx?.cwd ?? process.cwd()];
  if (provider) args.push("--provider", provider);
  if (model) args.push("--model", model);
  if (process.env.DEV_SESSION_WHO || who) args.push("--who", process.env.DEV_SESSION_WHO || who);
  const branch = spawnSync("git", ["-C", ctx?.cwd ?? process.cwd(), "branch", "--show-current"], { encoding: "utf8", timeout: 3000 });
  if (branch.status === 0 && branch.stdout.trim()) args.push("--branch", branch.stdout.trim());
  args.push("--", what || "");
  const r = run(args, bin);
  return r.ok && r.out ? r.out : null;
}

const PLACEHOLDER = /Untitled session/;
const terminal = (ctx, title) => { try { ctx.ui?.setTitle?.(title); } catch { /* no terminal */ } };

/** `who` is the role (assistant, ops, engineer) when the launcher gave none. */
export default function sessionTitle(pi, { who } = {}) {
  const apply = (ctx, what) => {
    const title = formatTitle(what, ctx, who);
    if (title) { pi.setSessionName(title); terminal(ctx, title); }
    return title;
  };
  let first = true;
  pi.on("session_start", (event, ctx) => {
    const current = pi.getSessionName();
    if (conforms(current)) return terminal(ctx, current);
    // Only a new session is named here; a resumed or forked one keeps its title (bulk rename owns history).
    if (event?.reason === "startup" || event?.reason === "new") apply(ctx, current || "");
  });
  pi.on("input", (event, ctx) => {
    if (first && event.source !== "extension") {
      first = false;
      const current = pi.getSessionName();
      const line = String(event.text ?? "").split("\n")[0].trim().slice(0, 70);
      if (line && (!current || PLACEHOLDER.test(current))) apply(ctx, line);
    }
    return { action: "continue" };
  });
  pi.registerTool?.({
    name: "session_title",
    label: "Session title",
    description: "Name this session once the task is clear: purpose(area): Description #ref, for example fix(ui): Align photo captions #12. Omit #ref when there is none. Host, who, client, model, type and date are added for you.",
    parameters: { type: "object", properties: { what: { type: "string", minLength: 3, maxLength: 80 } }, required: ["what"], additionalProperties: false },
    async execute(_id, params, _signal, _update, ctx) {
      const title = apply(ctx, String(params.what));
      return { content: [{ type: "text", text: title ? `Session title: ${title}` : "Session title unchanged: ai-title is unavailable." }], details: {} };
    },
  });
}
