#!/usr/bin/env bash
# One successful repository check per exact HEAD/index/worktree and environment config.
# Untracked .worker-* notes are not source. Tracked worker files remain in the fingerprint.
# The check is the command of the project record (work.check), else bin/check, else package.json
# scripts.check, else scripts/check (new-repo).
# Usage: check-once.sh [--status|--source|--hash]. Only a call with no option runs the check:
# --status compares the tree with the pass record; --source prints the check (bin/check, bun run
# check, scripts/check or the command of the record) and exits 2 when the repository has none (the
# stop check asks it); --hash prints the hash of the present tree (the batch of a forge writes it
# as the pass record of the goal worktree when its check passed on the same tree).
set -euo pipefail
case "${1:-}" in ''|--status|--source|--hash) ;; *) echo 'check-once: expected --status, --source, --hash or no arguments' >&2; exit 2 ;; esac
root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo 'check-once: not inside a repository' >&2; exit 2; }
cd "$root"
common="$(git rev-parse --path-format=absolute --git-common-dir)"
repo_name="$(basename "$(dirname "$common")")"
env_file="${DEV_PLATFORM_ENV_DIR:-$HOME/.config/dev-platform/env.d}/$repo_name.sh"
# Source before resolving the runner: PATH and BUN_PATH may select a pinned toolchain.
# Only the environment file can state the check command: a variable of the session does not.
unset DEV_PLATFORM_CHECK
[ ! -f "$env_file" ] || . "$env_file"
if [ -n "${DEV_PLATFORM_CHECK:-}" ]; then
  # The project record states the check command (work.check; dev-project sync writes this file).
  check_cmd=(bash -c "$DEV_PLATFORM_CHECK"); check_name="$DEV_PLATFORM_CHECK"
elif [ -x "$root/bin/check" ]; then
  check_cmd=("$root/bin/check"); check_name=bin/check
elif [ -f "$root/package.json" ] && python3 -c 'import json; import sys; sys.exit(not isinstance(json.load(open("package.json")).get("scripts", {}).get("check"), str))'; then
  bun="${BUN_PATH:-$HOME/.bun/bin/bun}"; [ -x "$bun" ] || bun="$(command -v bun || true)"
  [ -n "$bun" ] || [ "${1:-}" = --source ] || { echo 'check-once: bun not found' >&2; exit 2; }
  check_cmd=("${bun:-bun}" run check); check_name='bun run check'
elif [ -x "$root/scripts/check" ]; then
  check_cmd=("$root/scripts/check"); check_name=scripts/check
else
  echo 'check-once: no executable bin/check, package.json scripts.check or executable scripts/check; refusing to record a pass' >&2
  exit 2
fi
if [ "${1:-}" = --source ]; then printf '%s\n' "$check_name"; exit 0; fi
mark="$(git rev-parse --path-format=absolute --git-path dev-platform)"
mkdir -p "$mark"
tree_hash() {
  python3 - "$env_file" "${check_cmd[@]}" <<'PY'
import hashlib, os, pathlib, stat, subprocess, sys
h = hashlib.sha256()
def add(data):
    h.update(len(data).to_bytes(8, 'big')); h.update(data)
def git(*args):
    return subprocess.check_output(['git', *args])
add(b'check-once-v2')
add(git('rev-parse', 'HEAD'))
# Index matters even if the working file is reverted to HEAD after staging.
add(git('ls-files', '--stage', '-z'))
tracked = set(git('ls-files', '-z').split(b'\0')) - {b''}
untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0')) - {b''}
# A linked worktree of this repository inside the checkout (.claude/worktrees/<name>) is the tree of a different
# session, with its own check. It is no content of this tree: its commits and its uncommitted work do not change
# this result (2026-11-17: one dirty worktree of a second session failed the stop check of each session here).
top = os.path.realpath(git('rev-parse', '--show-toplevel').decode().strip())
linked = set()
for line in git('worktree', 'list', '--porcelain').decode().splitlines():
    if line.startswith('worktree '):
        other = os.path.realpath(line[9:])
        if other != top and other.startswith(top + os.sep):
            linked.add(os.fsencode(os.path.relpath(other, top)))
untracked = {p for p in untracked if p.rstrip(b'/') not in linked}
paths = tracked | {p for p in untracked if not pathlib.PurePath(os.fsdecode(p)).name.startswith('.worker-')}
for path in sorted(paths):
    add(path)
    try:
        st = os.lstat(path)
        add(str(stat.S_IMODE(st.st_mode)).encode())
        if stat.S_ISLNK(st.st_mode): add(os.readlink(path))
        elif stat.S_ISREG(st.st_mode): add(pathlib.Path(os.fsdecode(path)).read_bytes())
        elif stat.S_ISDIR(st.st_mode):
            # Submodule checkout state cannot be reduced to its index gitlink alone.
            add(subprocess.check_output(['git', '-C', os.fsdecode(path), 'rev-parse', 'HEAD']))
            status = subprocess.check_output(['git', '-C', os.fsdecode(path), 'status', '--porcelain', '-z'])
            if status:
                raise SystemExit('check-once: dirty submodule cannot be cached; commit or clean its changes first')
            add(status)
        else: raise RuntimeError('unsupported file type')
    except FileNotFoundError: add(b'missing')
env = pathlib.Path(sys.argv[1]); add(str(env).encode()); add(env.read_bytes() if env.exists() else b'')
for arg in sys.argv[2:]: add(os.fsencode(arg))
add(os.fsencode(os.environ.get('PATH', '')))
print(h.hexdigest())
PY
}
h="$(tree_hash)"
if [ "${1:-}" = --hash ]; then printf '%s\n' "$h"; exit 0; fi
if [ -f "$mark/check-pass" ] && [ "$(cat "$mark/check-pass")" = "$h" ]; then
  echo "check-once: check already passed on this tree ($h); log $mark/check.log"
  exit 0
fi
if [ "${1:-}" = --status ]; then echo 'check-once: no recorded pass for this tree'; exit 1; fi
# A `next build` that already runs in this tree (another session's check, or a build by hand)
# shares .next with this check, and the two collide. Do not start a second one.
for pid in $(pgrep -f 'next build' 2>/dev/null || true); do
  if [ "$(readlink "/proc/$pid/cwd" 2>/dev/null || true)" = "$(pwd -P)" ]; then
    echo "check-once: another check runs: next build (pid $pid) in $root; retry after it exits" >&2
    exit 3
  fi
done
# Do not let two runners publish competing markers/logs. The lock names its holder, and only a
# holder that is provably gone (its pid no longer runs) is cleared; a lock with no holder note, or
# with a live one, is never guessed stale.
lock="$mark/check-lock"
refuse_lock() { echo "check-once: another check holds $lock; retry after it exits" >&2; exit 3; }
if ! mkdir "$lock" 2>/dev/null; then
  holder="$(cat "$lock/pid" 2>/dev/null || true)"
  { [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; } || refuse_lock
  echo "check-once: clearing the lock left by pid $holder, which no longer runs" >&2
  rm -f "$lock/pid"
  rmdir "$lock" 2>/dev/null && mkdir "$lock" 2>/dev/null || refuse_lock
fi
printf '%s\n' "$$" > "$lock/pid"
release_lock() { rm -f "$lock/pid"; rmdir "$lock" 2>/dev/null || true; }
trap release_lock EXIT
rm -f "$mark/check-pass"
h="$(tree_hash)"
# The check runs as a child so that a signal to this script (a hook timeout sends TERM) stops the
# check and releases the lock instead of leaving it behind for every later run to refuse.
"${check_cmd[@]}" > "$mark/check.log" 2>&1 < /dev/null &
child=$!
# The check is a tree of processes (a runner, its shell, the tests): every one of them is told.
kill_tree() { local p; for p in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$p"; done; kill -TERM "$1" 2>/dev/null || true; }
trap 'kill_tree "$child"; wait "$child" 2>/dev/null; release_lock; trap - EXIT; exit 143' TERM INT HUP
status=0
wait "$child" || status=$?
if [ "$status" -eq 0 ]; then
  after="$(tree_hash)"
  if [ "$after" != "$h" ]; then
    echo 'check-once: tree or environment changed during check; no pass recorded; rerun on the final tree' >&2
    exit 1
  fi
  printf '%s\n' "$h" > "$mark/check-pass.tmp"
  mv "$mark/check-pass.tmp" "$mark/check-pass"
  tail -n 5 "$mark/check.log"
  echo "check-once: check passed on $h; log $mark/check.log"
else
  tail -n 30 "$mark/check.log" >&2
  echo "check-once: check FAILED; log $mark/check.log" >&2
  exit 1
fi
