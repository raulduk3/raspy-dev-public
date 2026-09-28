#!/usr/bin/env bash
# Daily loop, steps 5 and 6 (dev-platform skill `loop`, procedure): collect and report.
#
# Read-only. Reads the local ledger and the worker worktrees: which worker branches carry
# commits and a `.worker-pr.md` (ready for the owner's local review), which workers still run,
# which are blocked, what was folded into the rig branch, and its pull request's state on
# GitHub once it exists. Prints the CYCLE report in the fixed format with its one metrics line
# and writes it to --out. Transcripts and logs are never read here.
#
# Usage: loop-collect.sh --repo owner/name --dir <checkout> --rig <branch|""> --state <ledger rig dir>
#                        --hooks <platform hooks dir> [--planned N] [--dispatched N] [--out cycle.md]
#                        [--base <ref>] [--local]
#   --base: the ref the rig branch is measured against (default origin/develop). --local: a local
#   repository; GitHub is never called.
set -u
REPO=""; DIR=""; RIG=""; STATE=""; HOOKS=""
PLANNED=0; DISPATCHED=0; OUT=""; BASE="origin/develop"; LOCAL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --dir) DIR="$2"; shift 2 ;;
    --rig) RIG="$2"; shift 2 ;;
    --state) STATE="$2"; shift 2 ;;
    --hooks) HOOKS="$2"; shift 2 ;;
    --planned) PLANNED="$2"; shift 2 ;;
    --dispatched) DISPATCHED="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --base) BASE="$2"; shift 2 ;;
    --local) LOCAL=1; shift ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
[ -n "$REPO" ] && [ -n "$DIR" ] && [ -n "$STATE" ] || { echo "--repo, --dir and --state are required" >&2; exit 2; }
today="$(date +%Y-%m-%d)"

running_pid() {  # <issue> -> pid when a worker for it is alive
  local pf pid
  for pf in "$STATE/workers/$1.pid" "$(dirname "$STATE")"/../*/worker-"$1".pid; do
    [ -f "$pf" ] || continue
    pid="$(cat "$pf")"; ps -p "$pid" >/dev/null 2>&1 && { echo "$pid"; return 0; }
  done
  return 1
}

rig_line="none open"
if [ -n "$RIG" ]; then
  ahead="$(git -C "$DIR" rev-list --count "$BASE".."$RIG" 2>/dev/null || echo '?')"
  rig_line="$RIG, $ahead commit(s) ahead of $BASE"
fi

ready_lines=""; waiting_lines=""; blocked_lines=""
nready=0; nblocked=0; nrunning=0
for wt in "$DIR"/.claude/worktrees/loop-*; do
  [ -d "$wt" ] || continue
  i="$(basename "$wt" | sed -nE 's/^loop-([0-9]+)-.*/\1/p')"; [ -n "$i" ] || continue
  b="$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  ahead="$(git -C "$DIR" rev-list --count "${RIG:-$BASE}".."$b" 2>/dev/null || echo 0)"
  if [ -f "$wt/.worker-blocked.md" ]; then
    nblocked=$((nblocked+1)); blocked_lines="$blocked_lines
  issue #$i $b blocked: $(head -1 "$wt/.worker-blocked.md")"
  elif pid="$(running_pid "$i")"; then
    nrunning=$((nrunning+1)); waiting_lines="$waiting_lines
  issue #$i $b running pid $pid, $ahead commit(s) so far"
  elif [ "$ahead" = 0 ] && [ -f "$STATE/workers/$i.seat" ]; then
    nrunning=$((nrunning+1)); waiting_lines="$waiting_lines
  issue #$i $b working in its seat in $(cat "$STATE/workers/$i.seat"), no commits yet"
  elif [ "$ahead" = 0 ]; then
    nblocked=$((nblocked+1)); blocked_lines="$blocked_lines
  issue #$i $b exited with no commits (see $STATE/workers/$i.log)"
  else
    chk="not yet checked"
    if [ -n "$HOOKS" ] && (cd "$wt" && bash "$HOOKS/check-once.sh" --status >/dev/null 2>&1); then chk="check passed"; fi
    body="no body"; [ -f "$wt/.worker-pr.md" ] && body="body written"
    nready=$((nready+1)); ready_lines="$ready_lines
  issue #$i $b ahead $ahead, $chk, $body"
  fi
done

folded_lines=""; nfolded=0
if [ -s "$STATE/folded.tsv" ]; then
  folded_lines="$(awk -F'\t' '{print "  issue #" $1 " " $2 " " $3}' "$STATE/folded.tsv")"
  nfolded="$(cut -f1 "$STATE/folded.tsv" | sort -u | wc -l | tr -d ' ')"
fi

pr_line="not opened"
if [ -f "$STATE/merged" ]; then
  pr_line="merged locally into $(cat "$STATE/merged")"
elif [ -f "$STATE/pr-url" ]; then
  url="$(cat "$STATE/pr-url")"
  st="$(gh pr view "$url" --json number,state,isDraft,statusCheckRollup 2>/dev/null | jq -r '
    def checks:
      (.statusCheckRollup // []) as $c
      | if ($c | length) == 0 then "nochecks"
        elif ($c | map(select((.conclusion // "") | test("FAILURE|ERROR|TIMED_OUT|CANCELLED"))) | length) > 0 then "failing"
        elif ($c | map(select(.status != "COMPLETED")) | length) > 0 then "pending"
        else "green" end;
    "#\(.number) \(.state | ascii_downcase) \(if .isDraft then "draft" else "ready" end) checks \(checks)"' 2>/dev/null || echo 'unreadable')"
  pr_line="$url $st"
fi

merged_today=""; decisions=""
[ "$LOCAL" = 1 ] || merged_today="$(gh pr list --repo "$REPO" --state merged --limit 40 --json number,headRefName,mergedAt 2>/dev/null \
  | jq -r --arg d "$today" '.[] | select((.mergedAt // "") | startswith($d)) | "  #\(.number) \(.headRefName)"')"
[ "$LOCAL" = 1 ] || decisions="$(gh issue list --repo "$REPO" --label decision --state open --limit 40 --json number,title,createdAt 2>/dev/null \
  | jq -r --arg d "$today" '.[] | select(.createdAt | startswith($d)) | "  #\(.number) \(.title)"')"
ndec="$(grep -c '#' <<<"$decisions" || true)"

cycle="CYCLE $today
plan: $PLANNED issue(s) selected, $DISPATCHED dispatched
rig branch: $rig_line
ready (review locally, then loop.sh fold):${ready_lines:-
  none}
waiting:${waiting_lines:-
  none}
blocked:${blocked_lines:-
  none}
folded:${folded_lines:+
$folded_lines}${folded_lines:-
  none}
pull request: $pr_line
merged today:${merged_today:+
$merged_today}${merged_today:-
  none}
decisions:${decisions:+
$decisions}${decisions:-
  none new today}
lessons: 0 appended
metrics: planned $PLANNED dispatched $DISPATCHED running $nrunning ready $nready folded $nfolded blocked $nblocked decisions $ndec"

printf '%s\n' "$cycle"
[ -n "$OUT" ] && printf '%s\n' "$cycle" > "$OUT"
exit 0
