#!/usr/bin/env bash
# Daily loop, steps 1 to 3 (dev-platform skill `loop`, procedure): sense, plan, gate.
#
# Read-only. Reads open issues, open pull requests and their checks. Parses the two plain lines
# every implementable issue carries (`Scope: <path prefixes>` and `Depends on: #N, #M | none`),
# builds the dependency graph, selects `sprint-ready` issues whose dependencies are closed (or
# already folded into the open rig branch) and whose scopes are pairwise prefix-disjoint, up to
# the cap, and prints the plan in the fixed format. Nothing here posts anywhere; the plan is
# written to --out. The gate is the steer file that loop.sh keeps: `go` dispatches, anything
# else, including no file at all, is pause.
#
# Usage: loop-sense.sh --repo owner/name [--local-cap 3] [--exclude-file f] [--out plan.md]
#   --exclude-file: lines of `<issue> <reason>` from the local ledger (folded issues waiting for
#   the rig branch's pull request, issues with a local worker branch). A reason starting with `folded`
#   also satisfies a dependency, because that code is already on the rig branch.
#   --tasks <checkout> <ref>: a local repository. Tasks come from docs/tasks/ on that ref
#   (loop-tasks.py) instead of GitHub issues, and GitHub is never called.
set -u
REPO=""
LOCAL_CAP=3
OUT=""
EXCLUDE_FILE=""
TASKS_DIR=""; TASKS_REF=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --local-cap) LOCAL_CAP="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --exclude-file) EXCLUDE_FILE="$2"; shift 2 ;;
    --tasks) TASKS_DIR="$2"; TASKS_REF="$3"; shift 3 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
[ -n "$REPO" ] || { echo "--repo owner/name is required" >&2; exit 2; }
today="$(date +%Y-%m-%d)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

if [ -n "$TASKS_DIR" ]; then
  tasks="$(dirname "$0")/loop-tasks.py"
  python3 "$tasks" "$TASKS_DIR" "$TASKS_REF" issues > "$tmp/issues.json" || exit 1
  python3 "$tasks" "$TASKS_DIR" "$TASKS_REF" closed > "$tmp/closed.json" || exit 1
  echo '[]' > "$tmp/prs.json"
else
  gh issue list --repo "$REPO" --state open --limit 200 --json number,title,labels,body,milestone \
    > "$tmp/issues.json" || { echo "gh issue list failed" >&2; exit 1; }
  gh issue list --repo "$REPO" --state closed --limit 300 --json number > "$tmp/closed.json" || exit 1
  gh pr list --repo "$REPO" --state open --limit 60 --json number,title,isDraft,headRefName,statusCheckRollup,body \
    > "$tmp/prs.json" || exit 1
fi

# Parse Scope / Depends on lines. An issue with neither line is not implementable by the loop.
jq -c '
  .[] | {
    number, title,
    labels: [.labels[].name],
    milestone: (.milestone.title // null),
    scope: ((.body // "") | capture("(?m)^Scope: *(?<s>[^\n]+)")? .s // null),
    depends: ((.body // "") | capture("(?m)^Depends on: *(?<d>[^\n]+)")? .d // null)
  }' "$tmp/issues.json" > "$tmp/parsed.jsonl"

closed_set="$(jq -r '.[].number' "$tmp/closed.json" | tr '\n' ' ')"
is_closed() { case " $closed_set " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

# Issues already in review on GitHub: an open pull request cites them (`Closes #N`) or its
# branch ends in `-N`. The rig branch's pull request cites every folded issue once it is open.
in_review_lines="$(jq -r '.[] | .number as $pr
  | ( ((.body // "") | scan("(?i)(?:closes|fixes|resolves) #([0-9]+)") | .[0]),
      ((.headRefName // "") | capture("-(?<n>[0-9]+)$")? | .n) )
  | "\(.) \($pr)"' "$tmp/prs.json" 2>/dev/null)"
in_review() { awk -v n="$1" '$1==n {print "pr#" $2; found=1; exit} END {exit !found}' <<<"$in_review_lines"; }

# Issues the local ledger excludes: folded into the rig branch, or holding a worker branch.
excluded() {  # <issue> -> prints the reason, exit 1 when not excluded
  [ -n "$EXCLUDE_FILE" ] && [ -f "$EXCLUDE_FILE" ] || return 1
  awk -v n="$1" '$1==n {sub(/^[0-9]+ /,""); print; found=1; exit} END {exit !found}' "$EXCLUDE_FILE"
}
is_folded() { local r; r="$(excluded "$1")" && case "$r" in folded*) return 0 ;; esac; return 1; }

# Candidates: sprint-ready with both lines present.
selected=(); selected_scopes=(); skipped=()
while IFS= read -r row; do
  n="$(jq -r .number <<<"$row")"
  labels="$(jq -r '.labels | join(",")' <<<"$row")"
  case ",$labels," in *",sprint-ready,"*) ;; *) continue ;; esac
  if pr="$(in_review "$n")"; then skipped+=("#$n in review $pr"); continue; fi
  if why="$(excluded "$n")"; then skipped+=("#$n $why"); continue; fi
  scope="$(jq -r '.scope // ""' <<<"$row")"
  deps="$(jq -r '.depends // ""' <<<"$row")"
  if [ -z "$scope" ] || [ -z "$deps" ]; then skipped+=("#$n missing Scope/Depends line"); continue; fi
  # Dependencies satisfied: every #N closed or folded, or the literal `none`.
  unmet=""
  if [ "$deps" != "none" ]; then
    for d in $(grep -oE '#[0-9]+' <<<"$deps" | tr -d '#'); do is_closed "$d" || is_folded "$d" || unmet="$unmet #$d"; done
  fi
  if [ -n "$unmet" ]; then skipped+=("#$n waits on$unmet"); continue; fi
  # Scope disjointness against already selected issues (pairwise prefix check).
  conflict=""
  for p in $(tr ',' ' ' <<<"$scope"); do
    for q in "${selected_scopes[@]:-}"; do
      [ -z "$q" ] && continue
      case "$p" in "$q"*) conflict="$q" ;; esac
      case "$q" in "$p"*) conflict="$q" ;; esac
    done
  done
  if [ -n "$conflict" ]; then skipped+=("#$n scope overlaps $conflict"); continue; fi
  if [ "${#selected[@]}" -ge "$LOCAL_CAP" ]; then skipped+=("#$n over local cap $LOCAL_CAP"); continue; fi
  selected+=("$n")
  for p in $(tr ',' ' ' <<<"$scope"); do selected_scopes+=("$p"); done
done < "$tmp/parsed.jsonl"

# Open pull requests and their check state (the owner's review queue on GitHub).
pr_lines="$(jq -r '
  def checks:
    (.statusCheckRollup // []) as $c
    | if ($c | length) == 0 then "nochecks"
      elif ($c | map(select((.conclusion // "") | test("FAILURE|ERROR|TIMED_OUT|CANCELLED"))) | length) > 0 then "failing"
      elif ($c | map(select(.status != "COMPLETED")) | length) > 0 then "pending"
      else "green" end;
  .[] | "#\(.number) \(if .isDraft then "draft" else "ready" end) \(checks) \(.headRefName)"' "$tmp/prs.json")"

plan="PLAN $today
repo: $REPO
select:"
if [ "${#selected[@]}" -eq 0 ]; then
  plan="$plan
  none (no sprint-ready issue with Scope and Depends lines whose dependencies are closed)"
else
  for n in "${selected[@]}"; do
    row="$(grep "\"number\":$n," "$tmp/parsed.jsonl" | head -1)"
    t="$(jq -r .title <<<"$row")"; s="$(jq -r .scope <<<"$row")"
    slug="$(tr '[:upper:]' '[:lower:]' <<<"$t" | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g' | cut -c1-40)"
    plan="$plan
  #$n lane=fleet tier=implementation branch=fix/$slug scope=$s"
  done
fi
plan="$plan
skipped:"
if [ "${#skipped[@]}" -eq 0 ]; then plan="$plan
  none"; else for s in "${skipped[@]}"; do plan="$plan
  $s"; done; fi
plan="$plan
review queue (owner, on GitHub):
$( [ -n "$pr_lines" ] && sed 's/^/  /' <<<"$pr_lines" || echo '  none')
caps: local $LOCAL_CAP workers, one ops session, stop on quota error
gate: the steer file. \`loop.sh go\` writes go and dispatches; \`loop.sh pause\` or no file is pause."

printf '%s\n' "$plan"
[ -n "$OUT" ] && printf '%s\n' "$plan" > "$OUT"
exit 0
