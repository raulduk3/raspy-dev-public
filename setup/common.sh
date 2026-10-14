# shellcheck shell=bash
# Shared by setup/linux.sh and setup/macos.sh (sourced, not run). Each step is safe to repeat.
# AGENTS: which agent CLIs to install, any of "claude codex pi"; asked when unset.
# TEAMS=1 also installs OpenRig. GIT_NAME, GIT_EMAIL, NTFY_TOPIC: asked or made when unset.

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
SUDO=""; [ "$(id -u)" = 0 ] || SUDO=sudo
step() { printf '\n== %s\n' "$*"; }
ask() {   # ask VAR "question" default: keeps VAR when set; asks only at a terminal
  local name=$1 question=$2 default=${3:-} answer
  [ -n "${!name:-}" ] && return
  if [ -t 0 ]; then read -r -p "$question [$default] " answer; fi
  printf -v "$name" '%s' "${answer:-$default}"
}

install_agents() {
  step "agent CLIs"
  ask AGENTS "Which agents? (any of: claude codex pi)" "claude"
  export PATH="$HOME/.local/bin:$PATH"
  for agent in $AGENTS; do
    case "$agent" in
      claude) command -v claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash ;;
      codex) npm install -g @openai/codex@latest >/dev/null ;;
      pi) npm install -g --ignore-scripts @earendil-works/pi-coding-agent@latest >/dev/null ;;
      *) echo "setup: unknown agent $agent (claude, codex, pi)" >&2 ;;
    esac
  done
  [ "${TEAMS:-0}" != 1 ] || npm install -g @openrig/cli@latest >/dev/null
}

configure_git() {
  step "git"
  ask GIT_NAME "Your name for commits" "$(git config --global user.name || true)"
  ask GIT_EMAIL "Your email for commits" "$(git config --global user.email || true)"
  [ -z "$GIT_NAME" ] || git config --global user.name "$GIT_NAME"
  [ -z "$GIT_EMAIL" ] || git config --global user.email "$GIT_EMAIL"
  git config --global init.defaultBranch main
  git config --global push.autoSetupRemote true
}

configure_notify() {   # the topic is a secret: it lives only in these two files
  step "ntfy"
  local file="$HOME/.config/notify/topic"
  [ -n "${NTFY_TOPIC:-}" ] || NTFY_TOPIC="$(head -n 1 "$file" 2>/dev/null || true)"
  [ -n "$NTFY_TOPIC" ] || NTFY_TOPIC="dev-$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')"
  mkdir -p "$(dirname "$file")" && (umask 077 && printf '%s\n' "$NTFY_TOPIC" > "$file")
  $SUDO mkdir -p /etc/notify && printf '%s\n' "$NTFY_TOPIC" | $SUDO tee /etc/notify/topic >/dev/null
  $SUDO chmod 600 /etc/notify/topic
  $SUDO mkdir -p /usr/local/bin && $SUDO ln -sfn "$ROOT/hooks/notify" /usr/local/bin/notify
  echo "ntfy: subscribe to topic $NTFY_TOPIC in the ntfy app (server https://ntfy.sh)"
}

finish() {
  step "link"
  bash "$ROOT/setup/link.sh"
  cat <<EOF

Ready. Next, by hand:
  1. Sign in to each agent with its own login: run it once (claude, codex, pi) and follow it.
  2. sudo tailscale up --ssh      (then reach this machine from your devices by its name)
  3. In the ntfy app, subscribe to: $NTFY_TOPIC
  4. If you use Codex: run /hooks once in a session to trust the hooks.
EOF
}
