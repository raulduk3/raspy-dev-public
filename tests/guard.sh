#!/usr/bin/env bash
# Cases for hooks/guard: "allow" or "refuse", then the command.
set -u
guard="$(cd "$(dirname "$0")/../hooks" && pwd)/guard"
fail=0
repo="$(mktemp -d)"; trap 'rm -rf "$repo"' EXIT; git init -q -b main "$repo"
feature="$repo/feature"; git init -q -b feat/t "$feature"   # the cases run on a task branch
while IFS='|' read -r want cmd; do
  [ -n "$want" ] || continue
  (cd "$feature" && "$guard" -c "$cmd" 2>/dev/null) && got=allow || got=refuse
  [ "$got" = "$want" ] || { echo "guard: expected $want: $cmd"; fail=1; }
done <<'CASES'
allow|git status
allow|git push -u origin feat/x
allow|git push origin feat/x
allow|git push origin maintenance
allow|git push origin feat/main-thing
allow|git commit -m 'ok'
allow|git reset HEAD file
allow|gh pr create --draft
allow|git worktree add ../x
allow|git merge feat/x
refuse|git push origin main
refuse|git push origin master
refuse|git push
refuse|git push origin
refuse|git -C /x push origin HEAD:main
refuse|git push origin HEAD:refs/heads/main
refuse|git push --force origin feat/x
refuse|git push --force-with-lease origin feat/x
refuse|git push origin +feat/x
refuse|git push origin --delete feat/x
refuse|git rebase -i HEAD~2
refuse|git reset --hard
refuse|git commit --amend -m x
refuse|git commit -n -m x
refuse|git commit --no-verify -m x
refuse|git -c core.hooksPath=/dev/null commit -m x
refuse|ALLOW_PROTECTED=1 git push origin main
refuse|gh pr merge 3
refuse|gh pr review 3 --approve
refuse|git checkout main && git merge feat/x
refuse|cd x; git filter-branch --all
refuse|git worktree add /tmp/x
CASES
printf '%s' '{"tool_input":{"command":"git push origin main"}}' | "$guard" 2>/dev/null && { echo "guard: JSON input not refused"; fail=1; }
printf '%s' '{"tool_input":{"command":"ls"}}' | "$guard" 2>/dev/null || { echo "guard: JSON ls refused"; fail=1; }
printf 'garbage' | "$guard" 2>/dev/null && { echo "guard: bad input allowed"; fail=1; }
printf '{"cwd":"%s","tool_input":{"command":"git merge feat/x"}}' "$repo" | "$guard" 2>/dev/null && { echo "guard: merge on main allowed"; fail=1; }
"$guard" -c "git -C $repo merge feat/x" 2>/dev/null && { echo "guard: git -C merge on main allowed"; fail=1; }
exit $fail
