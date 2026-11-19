#!/usr/bin/env bash
# Claude Code PostToolUse hook for Edit and Write: format the file that changed, when the
# repository has prettier. Reads the hook input on stdin, never fails the tool call.
set -uo pipefail
input="$(cat)"
file="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)"
[ -n "$file" ] && [ -f "$file" ] || exit 0
case "$file" in
  *.ts|*.tsx|*.js|*.mjs|*.cjs|*.json|*.yml|*.yaml|*.md|*.css|*.html) ;;
  *) exit 0 ;;
esac
dir="$(dirname "$file")"
root="$(cd "$dir" && git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$root" ] && [ -x "$root/node_modules/.bin/prettier" ] || exit 0
# Respect the repository's ignore file; prettier exits non-zero for ignored files, which is fine.
(cd "$root" && ./node_modules/.bin/prettier --write --ignore-unknown "$file" >/dev/null 2>&1) || true
exit 0
