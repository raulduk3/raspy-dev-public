# platform_secret NAME   Print the secret the launcher handed to this process (systemd
# credential at $CREDENTIALS_DIRECTORY/NAME), or fail quietly. The shell twin of
# lib/ai_ecosystem/secret.py: capture it in a variable, never echo it to a terminal or log.
platform_secret() {
  [[ "$1" =~ ^[a-z0-9][a-z0-9._-]{0,63}$ ]] || return 2
  local value=
  if [ -n "${CREDENTIALS_DIRECTORY:-}" ] && [ -r "$CREDENTIALS_DIRECTORY/$1" ]; then
    value="$(cat "$CREDENTIALS_DIRECTORY/$1")"
  fi
  # Outside a launch the owner's own tools ask root's helper through a pipe (keys marked
  # owner_read; each use noted in the journal). Only a member of wheel asks.
  if [ -z "$value" ] && [ -z "${OL_SECRET_LAUNCH_ONLY:-}" ] && id -Gn 2>/dev/null | tr ' ' '\n' | grep -qx wheel && [ -x /usr/local/bin/ol-login-root ]; then
    value="$(sudo -n /usr/local/bin/ol-login-root secret "$1" 2>/dev/null </dev/null)" || value=
  fi
  [ -n "$value" ] || return 1
  printf '%s' "$value"
}
