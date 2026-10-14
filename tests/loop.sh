#!/usr/bin/env bash
# new-repo and the loop end to end, in a throwaway home: a repository from the templates, two
# tasks, a goal, a stand-in worker for each, merge up, land locally, finish.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
export HOME="$work" GIT_CONFIG_GLOBAL="$work/gitconfig" GH_TOKEN="" PATH="$root/bin:$PATH"
git config --global user.name tester && git config --global user.email tester@example.invalid
git config --global core.hooksPath "$root/hooks/git"
fail() { echo "loop test: $*" >&2; exit 1; }
settle() { for _ in $(seq 50); do loop status | grep -q running || return 0; sleep 0.2; done; fail "worker hung"; }

new-repo "$work/app" >/dev/null
cd "$work/app"
for f in $(grep -hv "^#" "$root"/contexts/*/instruction-files); do [ -L "$f" ] || fail "no link $f"; done
scripts/check >/dev/null || fail "template check fails"
loop tasks new "Add greeting" --scope src/greet/ >/dev/null
loop tasks new "Add farewell" --scope src/bye/ --depends "#1" >/dev/null
loop tasks check || fail "task files invalid"
git add docs && git commit -qm "docs(tasks): plan greeting and farewell"

cat > "$work/worker" <<'EOF'
#!/usr/bin/env bash
n="$(sed -n 's/.*worker for task \([0-9]*\).*/\1/p' <<<"$1" | head -n 1)"
dir="$(sed -n 's/^Scope: *//p' docs/tasks/"$n"-*.md)"
mkdir -p "$dir" && echo "task $n" > "$dir/file.txt"
git add "$dir" && git commit -qm "feat(app): task $n"
printf 'Done.\nCloses #%s\n' "$n" > .worker-done.md
EOF
chmod +x "$work/worker"
export LOOP_AGENT="$work/worker"

loop start feat/hello >/dev/null
loop go >/dev/null; settle
[ -d worktrees/task-1 ] && [ ! -d worktrees/task-2 ] || fail "task 2 started before its dependency"
loop status | grep -q 'task 1 *done' || fail "task 1 not done"
loop fold 1 >/dev/null || fail "fold 1"
loop go >/dev/null; settle
loop fold 2 >/dev/null || fail "fold 2"
loop land | grep -q 'merge --no-ff feat/hello' || fail "land did not print the merge"
ALLOW_PROTECTED=1 git merge -q --no-ff -m "merge: hello" feat/hello
[ -f src/greet/file.txt ] && [ -f src/bye/file.txt ] && [ -f docs/tasks/done/1-add-greeting.md ] || fail "goal content missing"
loop finish >/dev/null || fail "finish"
