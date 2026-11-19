#!/usr/bin/env bash
# tidy-all: run `loop.sh tidy <repo> --apply` for every repository in repos.conf (SDD-SC-13).
# The daily user timer runs it (integrations/systemd/dev-loop-tidy.timer). tidy bundles each ref
# before it deletes it, and keeps the rig worktree, the worker slots and every dirty worktree.
set -u
here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
CONF="${DEV_PLATFORM_REPOS:-$HOME/.config/dev-platform/repos.conf}"
[ -f "$CONF" ] || { echo "tidy-all: no $CONF"; exit 0; }
status=0
while read -r repo _; do
  case "$repo" in ''|'#'*) continue ;; esac
  echo "== $repo"
  OL_PORTAL=unit DEV_LOOP_TIDY_UNIT=1 bash "$here/loop.sh" tidy "$repo" --apply </dev/null || status=1
done < "$CONF"
exit "$status"
