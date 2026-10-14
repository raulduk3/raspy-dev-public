#!/usr/bin/env bash
# Wire Claude Code to this repository: instructions, skills, hooks, MCP servers. Idempotent.
set -euo pipefail
command -v claude >/dev/null || exit 0
: "${ROOT:?}"
dir="$HOME/.claude"; mkdir -p "$dir"
# Instructions: one import line, so the user's own CLAUDE.md stays theirs.
grep -qxF "@$ROOT/AGENTS.md" "$dir/CLAUDE.md" 2>/dev/null || printf '@%s\n' "$ROOT/AGENTS.md" >> "$dir/CLAUDE.md"
link_skills "$dir/skills"   # from setup/link.sh
# Hooks: drop this repository's old entries, add the current ones.
settings="$dir/settings.json"; [ -s "$settings" ] || echo '{}' > "$settings"
jq --arg root "$ROOT/hooks/" '
  def ours: .hooks |= map(select(.command | startswith($root) | not));
  def hook($cmd; $matcher): {hooks: [{type: "command", command: $cmd, timeout: 600}]} + (if $matcher then {matcher: $matcher} else {} end);
  .hooks |= ((. // {}) | with_entries(.value |= (map(ours) | map(select(.hooks | length > 0)))))
  | .hooks.PreToolUse += [hook($root + "guard"; "Bash")]
  | .hooks.Stop += [hook($root + "check-before-stop"; null)]
  | .hooks.Notification += [hook($root + "notify"; "permission_prompt|elicitation_dialog")]
  | .hooks.StopFailure += [hook($root + "notify"; null)]
' "$settings" > "$settings.new" && mv "$settings.new" "$settings"
# MCP servers from the one shared mcp.json, at user scope.
jq -r '.mcpServers // {} | keys[]' "$ROOT/mcp.json" | while read -r name; do
  claude mcp remove -s user "$name" >/dev/null 2>&1 || true
  claude mcp add-json -s user "$name" "$(jq -c --arg n "$name" '.mcpServers[$n]' "$ROOT/mcp.json")" >/dev/null
done
echo "claude-code: instructions, $(ls "$ROOT/skills" | wc -l | tr -d ' ') skills, hooks, MCP linked"
