#!/usr/bin/env bash
# Wire Pi to this repository: instructions, the guard extension, MCP servers. Idempotent.
# Skills come from ~/.agents/skills (setup/link.sh).
set -euo pipefail
command -v pi >/dev/null || exit 0
: "${ROOT:?}"
dir="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"; mkdir -p "$dir/extensions"
for pair in "AGENTS.md:$ROOT/AGENTS.md" "mcp.json:$ROOT/mcp.json"; do
  name="${pair%%:*}" target="${pair#*:}"
  if [ ! -e "$dir/$name" ]; then ln -s "$target" "$dir/$name"
  elif [ "$(readlink "$dir/$name")" != "$target" ]; then echo "pi: $dir/$name is your own; merge $target into it" >&2; fi
done
ln -sfn "$ROOT/contexts/cli-session/pi/guard.ts" "$dir/extensions/guard.ts"
echo "pi: instructions, guard extension, MCP linked"
