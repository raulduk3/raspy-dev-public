#!/usr/bin/env bash
# Pages the owner's phone when a Claude Code session needs a person or stops on an error:
# Notification (permission, input, elicitation) and StopFailure (rate limit, billing, login, ...).
# Delivery is the machine's `notify` command (dev-server: ntfy). Without one, or with
# DEV_PLATFORM_NOTIFY=off, it does nothing. The same session and reason page once per 10 minutes.
[ "${DEV_PLATFORM_NOTIFY:-on}" = off ] && exit 0
command -v notify >/dev/null 2>&1 || exit 0
input=$(cat)
read -r event kind session cwd message < <(python3 -c '
import json, sys
d = json.loads(sys.argv[1] or "{}")
kind = d.get("notification_type") or d.get("error_type") or d.get("error") or d.get("matcher") or ""
if isinstance(kind, dict): kind = kind.get("type", "")
msg = d.get("message") or d.get("error_message") or ""
print(d.get("hook_event_name", ""), kind or "-", d.get("session_id", "-")[:8], d.get("cwd", "-"),
      " ".join(str(msg).split())[:300])
' "$input" 2>/dev/null) || exit 0
case "$event:$kind" in
  Notification:idle_prompt|Notification:auth_success|Notification:elicitation_complete|Notification:elicitation_response) exit 0 ;;
esac
stamp="${XDG_RUNTIME_DIR:-/tmp}/claude-notify-$(id -u)-$session-$event-$kind"
[ -n "$(find "$stamp" -mmin -10 2>/dev/null)" ] && exit 0
touch "$stamp" 2>/dev/null
priority=default; [ "$event" = StopFailure ] && priority=high
printf '%s\n%s\n' "${message:-$event $kind}" "$(id -un)@$(hostname -s) in ${cwd/#$HOME/\~} (session $session)" \
  | timeout 15 notify "Claude: ${kind/-/$event}" - "$priority" >/dev/null 2>&1
exit 0
