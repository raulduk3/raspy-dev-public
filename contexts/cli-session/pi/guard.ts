// Pi has no shell hooks; this extension runs the same three: guard before every bash call
// (fails closed if guard is missing), the check when the agent ends a run, and notify when
// it asks the person something.
import { spawnSync } from "node:child_process";

export default function (pi: any) {
  pi.on("tool_call", async (event: any) => {
    if (event.toolName !== "bash") return;
    const r = spawnSync("guard", ["-c", String(event.input?.command ?? "")], { encoding: "utf8" });
    if (r.status !== 0) return { block: true, reason: (r.stderr || "guard is missing").trim() };
  });

  let sentBack = false;
  pi.on("agent_end", async () => {
    const r = spawnSync("check-before-stop", [], { input: "", encoding: "utf8" });
    if (r.status === 2 && !sentBack) {
      sentBack = true;
      pi.sendUserMessage(r.stderr, { deliverAs: "followUp" });
    } else sentBack = false;
  });

  pi.on("ui_prompt_start", async () => {
    spawnSync("notify", ["Pi needs you", process.cwd()]);
  });
}
