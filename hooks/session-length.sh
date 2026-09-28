#!/usr/bin/env bash
# Session-length guard: warn from turn 20, block after turn 30.
# Counts typed turns in a Claude Code or Codex transcript; injected context, tool results
# and task or shell notices are excluded. SESSION_TURN_STOP and SESSION_TURN_WARN override.
set -u
WARN=${SESSION_TURN_WARN:-20}; STOP=${SESSION_TURN_STOP:-30}
input=$(cat)
t=$(jq -r '.transcript_path // empty' <<<"$input" 2>/dev/null)
[ -n "$t" ] && [ -f "$t" ] || exit 0
if jq -e 'select(.type=="session_meta" or .type=="response_item")' "$t" >/dev/null 2>&1; then
  host=codex
  n=$(jq -s '[.[]|select(.type=="response_item" and .payload.type=="message" and .payload.role=="user")
    |(.payload.content|map(.text? // "")|join(" "))
    |select(test("^\\s*(# AGENTS\\.md instructions|<environment_context|<user_instructions)|OpenRig session identity")|not)]|length' "$t" 2>/dev/null) || exit 0
else
  host=claude
  n=$(jq -s '[.[]|select(.type=="user" and (.isMeta|not))
    |(.message.content|if type=="string" then . elif type=="array" and ([.[]|select(.type=="tool_result")]|length)==0 then (map(.text? // "")|join(" ")) else empty end)
    |select(test("^\\s*<(task-notification|bash-|local-command|command-)")|not)]|length' "$t" 2>/dev/null) || exit 0
fi
n=$((n + 1))
if [ "$n" -gt "$STOP" ]; then
  reason="Stop. Session passed $STOP turns. Start a new session with a 5-line summary."
  if [ "$host" = codex ]; then jq -n --arg r "$reason" '{decision:"block", reason:$r}'; exit 0; fi
  echo "$reason" >&2; exit 2
fi
if [ "$n" -ge "$WARN" ]; then
  msg="Session long: turn $n of $STOP. Start fresh for judgments."
  jq -n --arg m "$msg" '{systemMessage:$m, hookSpecificOutput:{hookEventName:"UserPromptSubmit", additionalContext:$m}}'
fi
exit 0
