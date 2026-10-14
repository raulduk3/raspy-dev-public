#!/usr/bin/env bash
# setup/macos.sh: make this Mac an AI-ready development server. Safe to re-run.
# Uses Homebrew (installed if missing) and sudo for system settings.
#   AGENTS="claude codex pi" TEAMS=1 GIT_NAME=.. GIT_EMAIL=.. NTFY_TOPIC=.. setup/macos.sh
set -euo pipefail
. "$(dirname "$(readlink -f "$0")")/common.sh"

step "packages"
if ! command -v brew >/dev/null; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi
brew install -q git jq tmux ripgrep node gh
[ -d /Applications/Tailscale.app ] || command -v tailscale >/dev/null || brew install -q --cask tailscale-app

install_agents
configure_git

step "ssh and sleep"
# Remote Login is SSH. If macOS refuses (it may want Full Disk Access for the terminal), turn it
# on in System Settings > General > Sharing > Remote Login.
$SUDO systemsetup -setremotelogin on 2>/dev/null || echo "setup: turn on Remote Login in System Settings" >&2
$SUDO pmset -c sleep 0 disksleep 0   # on power, the machine never sleeps; the display still may

configure_notify   # macOS has no OnFailure=; agent hooks and your own scripts call notify
finish
