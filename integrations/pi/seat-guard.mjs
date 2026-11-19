/** seat_guard: the platform's guard for a Pi seat or worker.
 *
 *  Claude Code runs hooks/pre-tool-use-guard.sh before every shell command; Pi has no hooks, so
 *  without this an API-rig seat could push to a protected branch, rewrite history, merge into the
 *  base or restart a service. Every `bash` tool call is shown to the same script with the same
 *  input shape, and refused when it refuses. If the script cannot run, the command is refused:
 *  a guard that fails open is no guard. Loaded from the seat's own Pi agent folder
 *  (extensions/), which `api-rig` and `dev-workspace add-worker pi` write before the seat starts. */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const GUARD = fileURLToPath(new URL("../../hooks/pre-tool-use-guard.sh", import.meta.url));

/** {block, reason} for a refused command, null for an allowed one. */
export function check(command, cwd, guard = GUARD) {
  const input = JSON.stringify({ tool_name: "Bash", tool_input: { command }, cwd });
  const result = spawnSync("bash", [guard], { input, encoding: "utf8", timeout: 20000 });
  if (result.status === 0) return null;
  if (result.status === 2) {
    return { block: true, reason: (result.stderr || "refused by the platform guard").trim() };
  }
  return { block: true, reason: "the platform guard could not run, so this command is refused" };
}

export default function seatGuard(pi) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return undefined;
    return check(String(event.input?.command ?? ""), ctx?.cwd ?? process.cwd()) ?? undefined;
  });
}
