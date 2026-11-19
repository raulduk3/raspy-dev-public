#!/usr/bin/env bash
# Claude Code Stop hook: when the session ends inside a repository with an executable bin/check
# or a package.json with a `check` script, and the tree has changes, run the repository's check
# through check-once.sh and report the result. A tree that already passed (the agent ran
# check-once.sh itself, or an earlier stop did) costs nothing. It blocks the stop (exit 2) only
# when the check fails, so the agent reports the failure instead of stopping over a red tree. It
# never edits anything.
set -uo pipefail
# Claude Code's loop guard: a stop that follows this hook's own block arrives with
# "stop_hook_active": true. It is let through, or a failing check would block every stop.
input=
# macOS has no `timeout`; perl is on every Mac and gives the same two-second limit.
read_input() { if command -v timeout >/dev/null 2>&1; then timeout 2 cat; else perl -e 'alarm 2; print while <STDIN>'; fi; }
[ -t 0 ] || input="$(read_input 2>/dev/null || true)"
if [ -n "$input" ] && { printf '%s' "$input" | jq -e '.stop_hook_active == true' >/dev/null 2>&1 ||
     printf '%s' "$input" | grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; }; then
  exit 0
fi
here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
# The hook may be started from the project folder while the session works in a linked worktree:
# the session's own tree is the one to check, and the hook input names it as "cwd".
if [ -n "$input" ]; then
  session_dir="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null || true)"
  [ -n "$session_dir" ] && [ -d "$session_dir" ] && cd "$session_dir"
fi
root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$root" ] || exit 0
# An orchestrated tree: one orchestrator and its workers share the tree, and the orchestrator
# runs the full check once for each batch before it pushes. A stop of any session there runs no
# check. The orchestrator writes the marker; an agent can still run check-once.sh directly.
common="$(cd "$root" && git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
if [ -n "$common" ] && [ -e "$common/dev-platform/orchestrated" ]; then
  echo 'dev-platform: orchestrated tree; the orchestrator runs the check'
  exit 0
fi
# Where the project record turns the full check off, a stop runs no check (SDD-PJ-04).
if [ -f "$here/../lib/ai_ecosystem/tiers.py" ]; then
  off="$(python3 -I "$here/../lib/ai_ecosystem/tiers.py" --field off "$root" 2>/dev/null || true)"
  case ",$off," in *,check,*) echo 'dev-platform: the full check is off for this project'; exit 0 ;; esac
fi
# A repository with no check has nothing to run. The project record can state the check (check-once.sh).
env_file="${DEV_PLATFORM_ENV_DIR:-$HOME/.config/dev-platform/env.d}/$(basename "$(dirname "${common:-/}")").sh"
if [ ! -x "$root/bin/check" ] && ! grep -qs '^export DEV_PLATFORM_CHECK=' "$env_file"; then
  [ -f "$root/package.json" ] && grep -q '"check"' "$root/package.json" || exit 0
fi
if [ -z "$(cd "$root" && git status --porcelain --untracked-files=no)" ] && [ -z "$(cd "$root" && git log --oneline @{upstream}..HEAD 2>/dev/null)" ]; then
  exit 0
fi
status=0
out="$(cd "$root" && bash "$here/check-once.sh" 2>&1)" || status=$?
if [ "$status" -eq 0 ]; then
  printf 'dev-platform: %s\n' "$(printf '%s\n' "$out" | tail -n 1)"
  exit 0
fi
# Another check is running on this tree right now (exit 3): its result is that run's to report,
# and a stop is not a red tree. Nothing is blocked.
if [ "$status" -eq 3 ]; then
  printf 'dev-platform: %s\n' "$(printf '%s\n' "$out" | tail -n 1)"
  exit 0
fi
printf 'dev-platform: check FAILED in %s; last lines:\n' "$root" >&2
printf '%s\n' "$out" | tail -n 30 >&2
exit 2
