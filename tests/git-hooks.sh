#!/usr/bin/env bash
# The global git hooks in a throwaway repository and bare remote.
set -u
hooks="$(cd "$(dirname "$0")/../hooks/git" && pwd)"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
fail=0; expect() { [ "$1" = "$2" ] || { echo "git hooks: $3: expected $1, got $2"; fail=1; }; }
g() { git -C "$work/r" -c core.hooksPath="$hooks" -c user.name=t -c user.email=t@example.invalid "$@" >/dev/null 2>&1 && echo ok || echo refused; }
git init -q --bare "$work/remote.git" && git init -q -b main "$work/r" && git -C "$work/r" remote add origin "$work/remote.git"
echo a > "$work/r/a" && git -C "$work/r" add a
expect ok "$(g commit -m one)" "clean commit"
printf 'api_key = "%s"\n' "$(printf 'A%.0s' {1..20})" > "$work/r/conf" && git -C "$work/r" add conf
expect refused "$(g commit -m secret)" "secret commit"
git -C "$work/r" rm -q --cached conf
expect refused "$(g push origin main)" "push main"
expect ok "$(ALLOW_PROTECTED=1 g push origin main)" "person pushes main"
expect ok "$(g push origin main:feat/x)" "push task branch"
echo b > "$work/r/a" && g commit -qam two >/dev/null
expect ok "$(g push origin main:feat/x)" "fast-forward"
git -C "$work/r" reset -q --hard HEAD~1 && echo c > "$work/r/a" && g commit -qam three >/dev/null
expect refused "$(g push --force origin main:feat/x)" "force push"
git -C "$work/r" checkout -q -b feat/y && echo d > "$work/r/d" && git -C "$work/r" add d && g commit -qm four >/dev/null
git -C "$work/r" checkout -q main
expect refused "$(g merge --no-ff -m m feat/y)" "merge onto main"
git -C "$work/r" merge --abort 2>/dev/null
expect ok "$(ALLOW_PROTECTED=1 g merge --no-ff -m m feat/y)" "person merges onto main"
exit $fail
