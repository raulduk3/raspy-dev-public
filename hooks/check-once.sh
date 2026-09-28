#!/usr/bin/env bash
# One successful repository check per exact HEAD/index/worktree and environment config.
# Untracked .worker-* notes are not source. Tracked worker files remain in the fingerprint.
# Usage: check-once.sh [--status] (--status never executes the check).
set -euo pipefail
case "${1:-}" in ''|--status) ;; *) echo 'check-once: expected --status or no arguments' >&2; exit 2 ;; esac
root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo 'check-once: not inside a repository' >&2; exit 2; }
cd "$root"
common="$(git rev-parse --path-format=absolute --git-common-dir)"
repo_name="$(basename "$(dirname "$common")")"
env_file="${DEV_PLATFORM_ENV_DIR:-$HOME/.config/dev-platform/env.d}/$repo_name.sh"
# Source before resolving the runner: PATH and BUN_PATH may select a pinned toolchain.
[ ! -f "$env_file" ] || . "$env_file"
if [ -x "$root/bin/check" ]; then
  check_cmd=("$root/bin/check")
elif [ -f "$root/package.json" ] && python3 -c 'import json; import sys; sys.exit(not isinstance(json.load(open("package.json")).get("scripts", {}).get("check"), str))'; then
  bun="${BUN_PATH:-$HOME/.bun/bin/bun}"; [ -x "$bun" ] || bun="$(command -v bun || true)"
  [ -n "$bun" ] || { echo 'check-once: bun not found' >&2; exit 2; }
  check_cmd=("$bun" run check)
else
  echo 'check-once: no executable bin/check or package.json scripts.check; refusing to record a pass' >&2
  exit 2
fi
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
if [ -f "$mark/check-pass" ] && [ "$(cat "$mark/check-pass")" = "$h" ]; then
  echo "check-once: check already passed on this tree ($h); log $mark/check.log"
  exit 0
fi
if [ "${1:-}" = --status ]; then echo 'check-once: no recorded pass for this tree'; exit 1; fi
# Do not let two runners publish competing markers/logs. Never guess that a lock is stale.
mkdir "$mark/check-lock" 2>/dev/null || { echo "check-once: another check holds $mark/check-lock; retry after it exits" >&2; exit 3; }
trap 'rmdir "$mark/check-lock"' EXIT
rm -f "$mark/check-pass"
h="$(tree_hash)"
if "${check_cmd[@]}" > "$mark/check.log" 2>&1; then
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
