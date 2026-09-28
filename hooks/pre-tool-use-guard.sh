#!/usr/bin/env bash
# Claude Code PreToolUse hook for the Bash tool: refuse the commands an agent must never run.
#
# Reads the hook input on stdin (JSON with tool_name and tool_input.command), exits 2 with the
# reason on stderr to block, exits 0 to allow. Blocked, regardless of repository:
#   - git push to develop or main (any spelling: `git push origin develop`, `git push -f origin
#     HEAD:main`, refspecs, `--force` to any protected ref);
#   - force pushes, and history rewrites of anything shared: push --force*, rebase, reset --hard,
#     commit --amend, filter-branch;
#   - merges into develop or main and gh pr merge;
#   - docker compose up/restart/down/stop, docker restart/stop/kill, systemctl restart/stop;
#   - ssh as root, and any ssh command that restarts, deploys or stops something;
#   - writing, chmodding or executing project scripts from ~/Desktop.
# An operator who needs one of these runs it in a terminal, not through the agent. Set
# DEV_PLATFORM_ALLOW_MUTATIONS=1 in the agent's environment to lift the ssh and docker rules for a
# session the owner is driving; the push and merge rules stay.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))' 2>/dev/null || true)"
[ -n "$command" ] || exit 0

cwd="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cwd",""))' 2>/dev/null || true)"

# The owner's own repositories; every other repository is professional.
repository_identity() {
  local common
  common="$(git -C "$1" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 1
  [ -n "$common" ] && (cd "$common" && pwd -P)
}
personal=0
personal_conf="${DEV_PLATFORM_PERSONAL:-$HOME/.config/dev-platform/personal.conf}"
if [ -n "$cwd" ] && [ -f "$personal_conf" ] && repo_identity="$(repository_identity "$cwd")"; then
  while IFS= read -r line; do
    case "$line" in ''|'#'*) continue ;; esac
    entry="$(repository_identity "${line/#\~/$HOME}")" || continue
    if [ "$repo_identity" = "$entry" ]; then personal=1; break; fi
  done < "$personal_conf"
fi

refuse() {
  printf 'dev-platform guard: %s\n' "$1" >&2
  exit 2
}

# Normalize whitespace for matching; keep the original for messages.
flat="$(printf '%s' "$command" | tr '\n' ' ' | tr -s ' ')"

# Match git's common global options too; do not weaken rules for personal repositories.
flat="$(printf '%s' "$flat" | python3 -c '
import re,sys
s=sys.stdin.read()
arg=r"(?:\"[^\"]*\"|\x27[^\x27]*\x27|[^ ;&|]+)"
s=re.sub(r"\bgit\s+(?:(?:-C|-c|--git-dir|--work-tree)\s+"+arg+r"\s+)+", "git ", s)
print(s)
')"

# git push to a protected branch, in any form.
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +push\b'; then
  if printf '%s' "$flat" | grep -Eq 'git +push[^;&|]*(\b(develop|main)\b|:refs/heads/(develop|main)\b|:(develop|main)\b)'; then
    refuse "git push to develop or main is refused; open a pull request from a type/short-description branch"
  fi
  if printf '%s' "$flat" | grep -Eq 'git +push[^;&|]*(--force|-f\b|--force-with-lease|\+[a-zA-Z0-9_./-]+:)'; then
    refuse "force push is refused; nothing pushed for review is rewritten"
  fi
  if ! printf '%s' "$flat" | grep -Eq 'git +push[^;&|]*(-u |--set-upstream|origin +[a-zA-Z]+/|origin +HEAD|origin +refs/heads/[a-z]+/|refs/heads/[a-z]+/)'; then
    # A bare `git push` follows the branch's upstream, which may be develop or main.
    refuse "bare git push is refused; name the branch: git push -u origin <type/short-description>"
  fi
fi

desktop_pattern=""
if [ -n "${HOME:-}" ]; then
  home_escaped="$(printf '%s/Desktop' "$HOME" | sed 's/[.[\\*^$()+?{}|]/\\&/g')"
  desktop_pattern="(~|\\$HOME)/Desktop|$home_escaped"
fi
if [ -n "$desktop_pattern" ] && printf '%s' "$flat" | grep -Eq "$desktop_pattern"; then
  desktop_write_re="(^|[;&|] *)((mkdir|touch|chmod|cp|mv|install|rsync)\b[^;&|]*($desktop_pattern)|(curl|wget)\b[^;&|]*(-o|--output-document=)[^;&|]*($desktop_pattern)|tee\b[^;&|]*($desktop_pattern)|[^;&|>]+>+[^;&|]*($desktop_pattern))"
  desktop_exec_re="(^|[;&|] *)(bash|sh|zsh|python3?|node|bun|npm|npx|pwsh|osascript) +[^;&|]*($desktop_pattern)[^;&|]*\.(sh|py|js|ts|mjs|cjs|ps1|command|applescript|scpt)\b"
  if printf '%s' "$flat" | grep -Eq "$desktop_write_re|$desktop_exec_re"; then
    refuse "engineering scripts do not live on Desktop; use the project worktree or ledger/artifacts directory"
  fi
fi

# Professional repositories: no tool or model attribution reaches the ledger.
if [ "$personal" != "1" ]; then
  ghost="professional repository: no tool or model attribution reaches the ledger"
  attribution='co-authored-by:.*(anthropic|openai|claude|codex|copilot|noreply@)|(^|[^a-z])generated with'
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(-C +[^ ]+ +)?commit\b' && printf '%s' "$flat" | grep -Eiq "$attribution"; then
    refuse "$ghost (commit trailer or generated-with line)"
  fi
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)gh +(pr +(create|edit|comment)|issue +(create|comment|edit))\b' && printf '%s' "$flat" | grep -Eiq "$attribution"; then
    refuse "$ghost (pull request or issue text)"
  fi
  if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(-C +[^ ]+ +)?push[^;&|]*[ :](refs/heads/)?(claude|codex|copilot)/'; then
    refuse "$ghost (tool-named branch)"
  fi
fi

# History rewrites of shared commits.
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(rebase|filter-branch|reset +--hard|commit +--amend|commit +[^;&|]*--amend)\b'; then
  refuse "history rewrite is refused (rebase, reset --hard, commit --amend, filter-branch)"
fi

# Merges into protected branches and merging pull requests.
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)git +(checkout|switch) +(develop|main)\b *[;&|]+ *git +merge\b'; then
  refuse "merging into develop or main is refused; the owner merges"
fi
if printf '%s' "$flat" | grep -Eq '(^|[;&|] *)gh +pr +(merge|ready|review +[^;&|]*--approve)\b'; then
  refuse "gh pr merge, ready and approve are refused; the owner reviews, marks ready and merges"
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

exit 0
