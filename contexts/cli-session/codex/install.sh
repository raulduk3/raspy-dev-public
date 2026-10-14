#!/usr/bin/env bash
# Wire Codex to this repository: instructions, hooks, command rules, MCP servers. Idempotent.
# Skills come from ~/.agents/skills (setup/link.sh). Codex asks you to trust new hooks once:
# run /hooks in a Codex session after this.
set -euo pipefail
command -v codex >/dev/null || exit 0
: "${ROOT:?}"
dir="${CODEX_HOME:-$HOME/.codex}"; mkdir -p "$dir/rules"
if [ ! -e "$dir/AGENTS.md" ]; then ln -s "$ROOT/AGENTS.md" "$dir/AGENTS.md"
elif [ "$(readlink "$dir/AGENTS.md")" != "$ROOT/AGENTS.md" ]; then
  echo "codex: $dir/AGENTS.md is your own; add the rules from $ROOT/AGENTS.md to it" >&2
fi
ln -sfn "$ROOT/contexts/cli-session/codex/guard.rules" "$dir/rules/guard.rules"
hooks="$dir/hooks.json"; [ -s "$hooks" ] || echo '{}' > "$hooks"
jq --arg root "$ROOT/hooks/" '
  def ours: .hooks |= map(select(.command | startswith($root) | not));
  def hook($cmd): {hooks: [{type: "command", command: $cmd, timeout: 600}]};
  .hooks |= ((. // {}) | with_entries(.value |= (map(ours) | map(select(.hooks | length > 0)))))
  | .hooks.PreToolUse += [hook($root + "guard")]
  | .hooks.Stop += [hook($root + "check-before-stop")]
  | .hooks.PermissionRequest += [hook($root + "notify")]
' "$hooks" > "$hooks.new" && mv "$hooks.new" "$hooks"
jq -r '.mcpServers // {} | to_entries[] | [.key, (.value | @json)] | @tsv' "$ROOT/mcp.json" |
while IFS=$'\t' read -r name server; do
  codex mcp remove "$name" >/dev/null 2>&1 || true
  url="$(jq -r '.url // empty' <<<"$server")"
  if [ -n "$url" ]; then codex mcp add "$name" --url "$url" >/dev/null; continue; fi
  env=(); while read -r kv; do [ -n "$kv" ] && env+=(--env "$kv"); done < <(jq -r '.env // {} | to_entries[] | "\(.key)=\(.value)"' <<<"$server")
  args=(); while IFS= read -r a; do args+=("$a"); done < <(jq -r '.args // [] | .[]' <<<"$server")
  codex mcp add "$name" ${env[@]+"${env[@]}"} -- "$(jq -r .command <<<"$server")" ${args[@]+"${args[@]}"} >/dev/null
done
echo "codex: instructions, hooks, rules, MCP linked; run /hooks once in Codex to trust the hooks"
