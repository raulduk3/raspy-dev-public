#!/usr/bin/env bash
# Claude Code Stop hook: when the session ends inside a repository with an executable bin/check
# or a package.json with a `check` script, and the tree has changes, run the repository's check
# through check-once.sh and report the result. A tree that already passed (the agent ran
# check-once.sh itself, or an earlier stop did) costs nothing. It blocks the stop (exit 2) only
# when the check fails, so the agent reports the failure instead of stopping over a red tree. It
# never edits anything.
set -uo pipefail
here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$root" ] || exit 0
if [ ! -x "$root/bin/check" ]; then
  [ -f "$root/package.json" ] && grep -q '"check"' "$root/package.json" || exit 0
fi
if [ -z "$(cd "$root" && git status --porcelain --untracked-files=no)" ] && [ -z "$(cd "$root" && git log --oneline @{upstream}..HEAD 2>/dev/null)" ]; then
  exit 0
fi
if out="$(cd "$root" && bash "$here/check-once.sh" 2>&1)"; then
  printf 'dev-platform: %s\n' "$(printf '%s\n' "$out" | tail -n 1)"
  exit 0
fi
printf 'dev-platform: check FAILED in %s; last lines:\n' "$root" >&2
printf '%s\n' "$out" | tail -n 30 >&2
exit 2
