import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { historyExtension } from "./history-tool.mjs";

// Standalone native Pi extension. Embedded role sessions pass explicit bindings.
export default function history(pi: ExtensionAPI) {
  return historyExtension({
    archive: process.env.AI_HISTORY_ARCHIVE,
    agent: process.env.AI_AGENT_ROLE,
  })(pi);
}
