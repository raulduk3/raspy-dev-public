#!/usr/bin/env bash
# setup/linux.sh: make this Linux machine an AI-ready development server. Safe to re-run.
# Debian/Ubuntu (apt), Fedora (dnf) or Arch (pacman). Uses sudo for packages and system settings.
#   AGENTS="claude codex pi" TEAMS=1 GIT_NAME=.. GIT_EMAIL=.. NTFY_TOPIC=.. setup/linux.sh
set -euo pipefail
. "$(dirname "$(readlink -f "$0")")/common.sh"
systemd=0; [ -d /run/systemd/system ] && systemd=1

step "packages"
packages="git curl jq tmux ripgrep python3 nodejs npm ca-certificates"
if command -v apt-get >/dev/null; then
  $SUDO apt-get update -qq
  # Debian and Ubuntu ship an old Node; the step below installs a current one instead.
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq ${packages/nodejs npm/xz-utils} gh openssh-server >/dev/null
elif command -v dnf >/dev/null; then
  $SUDO dnf install -y -q $packages gh openssh-server
elif command -v pacman >/dev/null; then
  $SUDO pacman -Sy --needed --noconfirm ${packages/python3/python} github-cli openssh >/dev/null
else
  echo "setup: no apt, dnf or pacman; install these yourself: $packages gh openssh" >&2; exit 1
fi

export PATH="$HOME/.local/bin:$PATH"
# Agent CLIs from npm need Node 22 or later; older distributions get it in ~/.local.
if [ "$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -lt 22 ]; then
  step "node 22 in ~/.local"
  arch="$(uname -m | sed 's/x86_64/x64/;s/aarch64/arm64/')"
  base=https://nodejs.org/dist/latest-v22.x
  tarball="$(curl -fsSL "$base/SHASUMS256.txt" | grep -o "node-v[0-9.]*-linux-$arch.tar.xz" | head -n 1)"
  curl -fsSLo "/tmp/$tarball" "$base/$tarball"
  (cd /tmp && curl -fsSL "$base/SHASUMS256.txt" | grep " $tarball\$" | sha256sum -c - >/dev/null)
  mkdir -p "$HOME/.local" && tar -xJf "/tmp/$tarball" -C "$HOME/.local" --strip-components=1 && rm "/tmp/$tarball"
fi
npm config set prefix "$HOME/.local"   # global installs without sudo

install_agents
configure_git

step "ssh and tailscale"
command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh
if [ $systemd = 1 ]; then
  $SUDO systemctl enable -q --now tailscaled
  $SUDO systemctl enable -q --now ssh 2>/dev/null || $SUDO systemctl enable -q --now sshd
  # A server that sleeps is unreachable: no suspend, and closing a laptop lid does nothing.
  $SUDO systemctl mask -q sleep.target suspend.target hibernate.target hybrid-sleep.target
  $SUDO mkdir -p /etc/systemd/logind.conf.d
  printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\n' |
    $SUDO tee /etc/systemd/logind.conf.d/no-sleep.conf >/dev/null
fi

configure_notify
if [ $systemd = 1 ]; then
  # Any system service that fails pages your phone (OnFailure= on every service, except this one).
  printf '[Unit]\nDescription=Notify that %%i failed\n\n[Service]\nType=oneshot\nExecStart=/usr/local/bin/notify "%%i failed" "on %%H; journalctl -u %%i" high\n' |
    $SUDO tee /etc/systemd/system/notify-failure@.service >/dev/null
  $SUDO mkdir -p /etc/systemd/system/service.d /etc/systemd/system/notify-failure@.service.d
  printf '[Unit]\nOnFailure=notify-failure@%%n.service\n' | $SUDO tee /etc/systemd/system/service.d/notify-failure.conf >/dev/null
  printf '[Unit]\nOnFailure=\n' | $SUDO tee /etc/systemd/system/notify-failure@.service.d/no-loop.conf >/dev/null
  $SUDO systemctl daemon-reload
fi

finish
