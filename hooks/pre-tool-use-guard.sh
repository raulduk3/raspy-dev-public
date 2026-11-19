#!/usr/bin/env bash
# Claude Code PreToolUse hook for the Bash tool: refuse the commands an agent must never run.
#
# Reads the hook input on stdin (JSON with tool_name and tool_input.command), exits 2 with the
# reason on stderr to block, exits 0 to allow. Blocked, regardless of repository:
#   - git push to develop, main or master, in any spelling (`git push origin develop`, refspecs
#     such as HEAD:refs/heads/main, x:main, +ref, `git -C dir push`), except at tier 1, where a
#     non-force push of main or master is allowed (the git pre-push hook checks fast-forward);
#   - a push of a wip/ branch, at every tier;
#   - force pushes, and history rewrites of anything shared: push --force*, rebase, reset --hard,
#     commit --amend, filter-branch;
#   - git merge while main, master or develop is the current branch, and gh pr merge, ready and
#     approve, and a gh api call that merges;
#   - --no-verify on commit or push, and a change of core.hooksPath;
#   - git branch -D, git worktree remove and git clean aimed at another worktree than the own one;
#   - checkout, switch, merge, reset, pull, cherry-pick, revert and stash pop/apply in a worktree
#     where another live Claude Code or Codex process has its working directory (a shared bench);
#   - docker compose up/restart/down/stop, docker restart/stop/kill, systemctl restart/stop;
#   - ssh as root, and any ssh command that restarts, deploys or stops something;
#   - writing, chmodding or executing project scripts from ~/Desktop;
#   - a git worktree or clone in /tmp, /dev/shm or /run/user: memory on dev-server, and swept.
# The git and gh rules live in hooks/guard_git.py. It matches command words, not text in quotes.
# Tier 3 repositories (and a path with no tier) also refuse tool or model attribution and
# claude/, codex/ and copilot/ branch pushes. The tier comes from lib/ai_ecosystem/tiers.py.
# An operator who needs one of these runs it in a terminal, not through the agent. Set
# DEV_PLATFORM_ALLOW_MUTATIONS=1 in the agent's environment to lift the ssh and docker rules for a
# session the owner is driving; the push and merge rules stay.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))' 2>/dev/null || true)"
[ -n "$command" ] || exit 0

cwd="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cwd",""))' 2>/dev/null || true)"

# The tier of the repository. Tier 3 gets the professional rules. A path with no tier, and a
# lookup that fails, count as tier 3.
guard_dir="$(dirname "$(readlink -f "$0")")"
tiers_py="$guard_dir/../lib/ai_ecosystem/tiers.py"
tier=3
if [ -f "$tiers_py" ]; then
  found_tier="$(python3 -I "$tiers_py" --field tier "${cwd:-$PWD}" 2>/dev/null || true)"
  case "$found_tier" in 1|2|3|4) tier="$found_tier" ;; esac
  found_off="$(python3 -I "$tiers_py" --field off "${cwd:-$PWD}" 2>/dev/null || true)"
fi
professional=0
personal=0
[ "$tier" = 3 ] && professional=1
# Where the project record turns the Git rules off, the rules of a professional repository do not apply (SDD-PJ-04).
case ",${found_off:-}," in *,git,*) professional=0 ;; esac
if [ "$tier" = 1 ] || [ "$tier" = 2 ]; then personal=1; fi

refuse() {
  printf 'dev-platform guard: %s\n' "$1" >&2
  exit 2
}

# Normalize whitespace for matching; keep the original for messages.
flat="$(printf '%s' "$command" | tr '\n' ' ' | tr -s ' ')"

# Match git's common global options too.
flat="$(printf '%s' "$flat" | python3 -c '
import re,sys
s=sys.stdin.read()
arg=r"(?:\"[^\"]*\"|\x27[^\x27]*\x27|[^ ;&|]+)"
s=re.sub(r"\bgit\s+(?:(?:-C|-c|--git-dir|--work-tree)\s+"+arg+r"\s+)+", "git ", s)
print(s)
')"

# Git and gh rules. The helper reads shell words, so text in quotes and search patterns never
# matches. It runs with the tier lookup of the repository that the command names.
guard_status=0
guard_reason="$(printf '%s' "$command" | python3 -I "$guard_dir/guard_git.py" --cwd "${cwd:-$PWD}" 2>/dev/null)" || guard_status=$?
case "$guard_status" in
  0) ;;
  2) refuse "$guard_reason" ;;
  *) refuse "the git rule helper could not run, so this command is refused" ;;
esac

# A controlled specification: no shell write to a file of the system requirements, the SDD or the TDD (SDD-SW-12).
# The helper is not in the bundle for a client machine; there this rule does not run.
if [ -f "$guard_dir/spec_guard.py" ]; then
  spec_status=0
  spec_reason="$(printf '%s' "$input" | python3 -I "$guard_dir/spec_guard.py" 2>/dev/null)" || spec_status=$?
  [ "$spec_status" -eq 2 ] && refuse "${spec_reason#dev-platform guard: }"
fi

desktop_pattern=""
if [ -n "${HOME:-}" ]; then
  home_escaped="$(printf '%s/Desktop' "$HOME" | sed 's/[.[\\*^$()+?{}|]/\\&/g')"
  # ~/Desktop, the literal text $HOME/Desktop, and the expanded path.
  desktop_pattern="(~|\\\$HOME)/Desktop|$home_escaped"
fi
if [ -n "$desktop_pattern" ] && printf '%s' "$flat" | grep -Eq "$desktop_pattern"; then
  desktop_write_re="(^|[;&|] *)((mkdir|touch|chmod|cp|mv|install|rsync)\b[^;&|]*($desktop_pattern)|(curl|wget)\b[^;&|]*(-o|--output-document=)[^;&|]*($desktop_pattern)|tee\b[^;&|]*($desktop_pattern)|[^;&|>]+>+[^;&|]*($desktop_pattern))"
  desktop_exec_re="(^|[;&|] *)(bash|sh|zsh|python3?|node|bun|npm|npx|pwsh|osascript) +[^;&|]*($desktop_pattern)[^;&|]*\.(sh|py|js|ts|mjs|cjs|ps1|command|applescript|scpt)\b"
  if printf '%s' "$flat" | grep -Eq "$desktop_write_re|$desktop_exec_re"; then
    refuse "engineering scripts do not live on Desktop; use the project worktree or ledger/artifacts directory"
  fi
fi

# A checkout in memory: /tmp, /dev/shm and /run/user are RAM (tmpfs), and /tmp is swept, so a
# worktree there starves the machine and can lose uncommitted work (2026-10-06: 7.6 GB of
# worktrees in /tmp left the local model killed for memory).
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(worktree +add|clone)\b[^;&|]*[ =]["\x27]?(/tmp|/dev/shm|/run/user)(/|["\x27 ]|$)'; then
  refuse "no worktree or clone in /tmp, /dev/shm or /run/user (memory, and swept); put a worktree in its repository's .claude/worktrees/<name>"
fi

# One place for worktrees: the repository's own .claude/worktrees. ~/dev/wt was the place
# before 2026-11-02 (commit 20147ba); a worktree there is outside every project folder.
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +([^;&|]* +)?worktree +add\b[^;&|]*[ =]["\x27]?(~|\$HOME|/home/[^/ ]+|/Users/[^/ ]+)/[Dd]ev/wt(/|["\x27 ]|$)'; then
  refuse "no worktree in ~/dev/wt; put it in its repository's .claude/worktrees/<name>"
fi

# Tier 3 repositories: no tool or model attribution reaches the ledger.
if [ "$professional" = "1" ]; then
  ghost="professional repository: no tool or model attribution reaches the ledger"
  attribution='co-authored-by:.*(anthropic|openai|claude|codex|copilot|noreply@)|(^|[^a-z])generated with'
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(-C +[^ ]+ +)?commit\b' && printf '%s' "$flat" | grep -Eiq "$attribution"; then
    refuse "$ghost (commit trailer or generated-with line)"
  fi
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)gh +(pr +(create|edit|comment)|issue +(create|comment|edit))\b' && printf '%s' "$flat" | grep -Eiq "$attribution"; then
    refuse "$ghost (pull request or issue text)"
  fi
fi

if [ "${DEV_PLATFORM_ALLOW_MUTATIONS:-0}" != "1" ]; then
  # Container and service mutations.
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)(docker +compose|docker-compose)[^;&|]*\b(up|restart|down|stop|kill|rm)\b'; then
    refuse "docker compose up/restart/down/stop is refused; deploys and restarts are the owner's, in a terminal"
  fi
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)docker +(restart|stop|kill|rm|run +[^;&|]*--restart)\b'; then
    refuse "docker restart/stop/kill/rm is refused"
  fi
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)(sudo +)?systemctl +(restart|stop|start|reload|disable|enable)\b'; then
    refuse "systemctl mutations are refused"
  fi
  # Remote mutations.
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)ssh +[^;&|]*\broot@'; then
    refuse "ssh as root is refused"
  fi
  # The remote command is what follows the host (`user@host cmd …`); a user named deploy is fine.
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)ssh +[^;&|]*@[^ ]+ +[^;&|]*\b(docker|systemctl|restart|deploy|reboot|shutdown|rm +-rf|compose)\b'; then
    refuse "an ssh command that restarts, deploys or removes something is refused; read-only diagnostics only"
  fi
fi

# Jev advisory escalation. This never lowers the deterministic rules above. It may only
# raise a still-allowed command to a confirmation-required refusal. If Jev is unavailable,
# over budget, uncredentialed or malformed, the ordinary guard result stands.
if [ "${DEV_PLATFORM_JEV_GUARD:-0}" = "1" ] && command -v ai-jev >/dev/null 2>&1; then
  jev_state="$(COMMAND="$command" CWD="$cwd" PERSONAL="$personal" python3 - <<'PY'
import json, os
print(json.dumps({
    "command": os.environ.get("COMMAND", "")[:4000],
    "cwd": os.environ.get("CWD", ""),
    "personal_repository": os.environ.get("PERSONAL") == "1",
}))
PY
)"
  jev_answer="$(JEV_TIMEOUT="${DEV_PLATFORM_JEV_TIMEOUT:-5}" ai-jev decide classify-tool-risk --provider openrouter --state "$jev_state" 2>/dev/null || true)"
  jev_refusal="$(JEV_ANSWER="$jev_answer" python3 - <<'PY' 2>/dev/null || true
import json, os
try:
    data = json.loads(os.environ.get("JEV_ANSWER", ""))
    answers = data.get("answers", {})
    risk = answers.get("risk_level", {}).get("choice")
    probability = answers.get("requires_confirmation", {}).get("probability", 0)
    if risk == "credential_privacy_billing" or (risk == "destructive_or_external" and probability >= 0.75):
        print(f"Jev classified this command as {risk} with confirmation probability {probability:.2f}")
except Exception:
    pass
PY
)"
  if [ -n "$jev_refusal" ]; then
    refuse "$jev_refusal"
  fi
fi

exit 0
