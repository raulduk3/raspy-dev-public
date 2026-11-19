#!/usr/bin/env bash
# loop: work toward one goal on one branch. The goal gets an ordinary type/slug branch, the rig
# branch, cut from the base. Each task gets a worker and a child branch cut from the rig branch.
# A child whose check passes merges up into the rig branch; the rig branch reaches the base once.
# repos.conf: owner/repo checkout local|owner|bot [base], separated by spaces or tabs.
# local, the default posture: tasks are files in docs/tasks/ on the base branch, the rig branch
# is cut from the local base, and close --merge merges it back locally. GitHub is never called.
# owner|bot: tasks are GitHub issues and the rig branch lands as one pull request (the identity
# that makes the two GitHub writes).
# Without an explicit base: personal uses local origin/HEAD, professional uses develop.
# The open rig branch pins its base; worker limits are LOOP_CAP, LOOP_WORKER_MAX_TURNS and
# LOOP_WORKER_MAX_SECONDS. LOOP_WORKER_TOKEN_CEILING is an instruction, not a CLI limit.
#
# The repository sees only what its policy asks for: one branch cut from the base, one pull
# request to the base with the template body and the check output, merged by the owner. Child
# branches stay on this machine and never push. One rig branch is open per repository at a time,
# so there is one dispatcher. No comment is ever posted on an issue, and CI runs once, on the
# rig branch's pull request.
#
# Ledger: LOOP_STATE_DIR/<owner__repo>/   (LOOP_STATE_DIR from brief.conf; default
#                                          ~/.local/state/dev-platform/loop)
#   steer                     first word go|pause, the rest are steer args (only N, skip N).
#                             A MISSING FILE MEANS PAUSE.
#   rig-branch, rig-base      the open rig branch and its base; absent when none is open
#   <rig>/plan.md             PLAN (loop-sense.sh); <rig> is the branch name with / as __
#   <rig>/cycle.md            CYCLE (loop-collect.sh)
#   <rig>/folded.tsv          issue <tab> branch <tab> merge sha <tab> folded-at
#   <rig>/folded-<issue>.md   the worker's pull request body, kept at fold
#   <rig>/pr.md, pr-url, pushed-as, pr-merged   the rig branch's pull request
#   <rig>/workers/<issue>.{pid,log}
#   _next/plan.md             a plan written while no rig branch is open
#
# Personal repositories are listed in ~/.config/dev-platform/personal.conf (the guard hook's
# rule); every other repository is professional. Workers use an explicit allow list everywhere.
# In a personal repository the assistant may run close --push; in a professional one close
# refuses a body that names a tool or a model (the ghost check).
#
# Verbs. assistant = on the owner's word in that session, including a control seat; owner = the
# owner in a terminal (refused without one); automation = the scheduled tick.
#   status <repo>                        read-only summary                              anyone
#   state <repo>                         the status facts as JSON (the ai menu reads it) anyone
#   plan <repo>                          write and print the PLAN                       anyone
#   start <repo> <type/slug>             cut the rig branch for this goal from the base
#                                        into its worktree, record it, write the plan    assistant
#   go <repo> [only N ..|skip N ..]      write steer go, plan, dispatch now              assistant
#   resume <repo> N ...                 resume an unfinished local worker, within the cap
#   pause <repo>                         write steer pause                              assistant
#   tick <repo>                          dispatch when steer says go, up to CAP running automation
#   collect <repo>                       write and print the CYCLE                      assistant
#   fold <repo> <issue|branch> ..        merge a finished child branch up into the rig
#                                        branch once its check passes; release its seat,
#                                        keep its body, remove branch+worktree          assistant
#   close <repo> [--as type/slug] [--title t] [--push [--ready] | --merge]
#                                        check the rig branch head, write pr.md and print
#                                        the commands; --push pushes the rig branch under
#                                        its own name (or --as) and opens the one pull
#                                        request; the ghost check runs first in a
#                                        professional repository                        owner for --push*
#                                        (local: --merge merges the rig branch into the
#                                        base and marks its tasks done)                 owner for --merge
#   finish <repo> <pr>                   after the owner merged it: close the folded
#                                        issues, delete the pushed branch, remove the
#                                        rig worktree and branch, steer pause           owner
#   drop <repo> N ..                     throw a worker away, work and all: its working
#                                        copy and branch (refused while it runs)        assistant
#   tidy <repo> [--apply]                classify merged and stale branches and
#                                        worktrees; --apply bundles, then deletes       owner for --apply
#   tasks <repo> [list|next|check]       local: list the tasks on the base, print the next
#   tasks <repo> new <title> --scope ..  number, check or write task files in the checkout
#                                        the command runs in (or the mapped one)        anyone
#   * one exemption: in a personal repository the assistant may run close --push without --ready.
#
# Who a local worker runs as: the owner (default) in a git worktree of the checkout, or engineer
# (LOOP_WORKER_AS=engineer, what dev-server's `goal` sets). engineer is let into one folder and nothing
# above it, so its working copy is a full clone under .claude/worktrees: the grant never reaches
# the project's .git. Its branch comes back by fetch; fold and drop treat both kinds alike.
#
# Nothing here pushes to develop or main, merges into them, marks ready, approves or deploys.
#
# Source control tiers (decision 0001, docs/spec/SDD.md area SC). repos.conf lines may end with
# key=value fields: tier=0..4 forge=github|bare|none tracker=files|github slots=N large=0|1
# keep=a,b (trunks that tidy never lists or deletes: the ones the host protects or checks)
# spec=single|domains decisions=open|frozen (spec-direct mode: skills/loop/scripts/spec-guard.py).
#   tier <path|owner/repo>               print the tier record (lib/ai_ecosystem/tiers.py)  anyone
#   land <repo>                          land the goal as its tier says: tier 1 fast-forward
#                                        and push (assistant); tier 2 the owner's local land
#                                        and push; tier 3 one push (bare) or one draft pull
#                                        request (github); tier 4 one push to origin       see tier
#   fold <repo> N --from <remote branch> fold a cloud agent's branch by its commit, then
#                                        delete that branch (tier 2 and 3 GitHub only)     assistant
# Workers run in slots: .claude/worktrees/slot-1..slot-S, detached at the rig branch, reused
# from task to task. A slot holds .worker-issue while it has a worker. A fold adds one squash
# commit for each task (and moves a task file to docs/tasks/done/ in that commit); the full
# check runs in the worker and once at close or land, not at the fold.
set -eu
# $0 may be a symlink (the assistant workspace and ~/.claude/skills link here): resolve it.
here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
HOOKS="$(cd "$here/../../../hooks" && pwd)"
TIERS="$here/../../../lib/ai_ecosystem/tiers.py"
CONF="${DEV_PLATFORM_REPOS:-$HOME/.config/dev-platform/repos.conf}"
if [ "${1:-}" = tier ]; then
  exec python3 -I "$TIERS" --conf "$CONF" "${2:?loop: tier <path|owner/repo>}"
fi
BRIEF_CONF="${DEV_PLATFORM_BRIEF:-$HOME/.config/dev-platform/brief.conf}"
[ -f "$BRIEF_CONF" ] && . "$BRIEF_CONF"
state="${LOOP_STATE_DIR:-$HOME/.local/state/dev-platform/loop}"
verb="${1:?status|state|plan|start|go|pause|resume|tick|collect|fold|drop|close|land|finish|tidy|tasks|tier}"; repo="${2:?owner/repo}"; shift 2
CAP="${LOOP_CAP:-3}"
WORKER_AS="${LOOP_WORKER_AS:-}"
case "$WORKER_AS" in ""|engineer) ;; *) echo "loop: LOOP_WORKER_AS is empty (the owner) or engineer" >&2; exit 2 ;; esac
MAX_TURNS="${LOOP_WORKER_MAX_TURNS:-60}"
MAX_SECONDS="${LOOP_WORKER_MAX_SECONDS:-1800}"
TOKEN_CEILING="${LOOP_WORKER_TOKEN_CEILING:-35000}"
for limit in "$CAP" "$MAX_TURNS" "$MAX_SECONDS" "$TOKEN_CEILING"; do
  case "$limit" in ''|*[!0-9]*|0) echo "loop: worker limits must be positive integers" >&2; exit 2 ;; esac
done
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo "loop: invalid owner/repo" >&2; exit 2; }
today="$(TZ=Etc/UTC date +%Y-%m-%d)"
# The repository's tier record (SDD-SC-01): one reader for the loop, the guard and ghx.
t_tier=3; t_forge=none; t_tracker=github; t_tasks=md; t_slots=2; t_large=0; t_base=""; t_keep=""; t_spec=single; t_decisions=open
t_off=""; t_side=""
tier_rec="$(python3 -I "$TIERS" --conf "$CONF" "$repo")" || { echo "loop: $CONF is malformed" >&2; exit 2; }
while IFS='=' read -r key value; do
  case "$key" in
    tier) t_tier="$value" ;; forge) t_forge="$value" ;; tracker) t_tracker="$value" ;; tasks) t_tasks="$value" ;;
    slots) t_slots="$value" ;; large) t_large="$value" ;; base) t_base="$value" ;; keep) t_keep="$value" ;;
    spec) t_spec="$value" ;; decisions) t_decisions="$value" ;; off) t_off="$value" ;; side) t_side="$value" ;;
  esac
done <<<"$tier_rec"
# Where the project record turns the loop off, only the read verbs work (SDD-PJ-04).
case ",$t_off," in *,loop,*)
  case "$verb" in status|state|plan|tasks|tier) ;; *) echo "loop: the loop is off for $repo (the parts of its project record)" >&2; exit 2 ;; esac ;;
esac
export LOOP_DECISIONS="$t_decisions"   # loop-tasks.py: with frozen, a cited decision does not gate a task
SLOTS="${LOOP_SLOTS:-$t_slots}"
case "$SLOTS" in ''|*[!0-9]*|0) echo "loop: slots must be a positive integer" >&2; exit 2 ;; esac
ctl="$state/${repo//\//__}"; mkdir -p "$ctl"
GHX="$here/ghx"
ACCOUNT_CLI="$here/../../../bin/ai-account"
TITLE_CLI="${LOOP_TITLE_CLI:-$here/../../../bin/ai-title}"

verify_loop_account() {
  # One resolver for every launch: an account named for this loop
  # (LOOP_ACCOUNT_ID) or saved by the owner (ai-account select) is used or refused, never
  # substituted; otherwise the eligible Claude account with the most remaining quota.
  # A refusal stops here: no worker is allocated and steer is not changed. Workers never
  # run unbound. A switch from the last account is said in the chat and recorded.
  # Pi workers and seats (the API rig, LOOP_RUNTIME=pi or LOOP_SEAT_RUNTIME=pi) run on the
  # OpenRouter key the rig holds: that account is named and its metered billing confirmed by the rig itself
  # (docs/api-rig.md), and it must be signed in and verified like any other.
  local result
  [ "${LOOP_RUNTIME:-}" != hand ] || return 0   # the caller's own session is the account
  if [ "${LOOP_SEAT_RUNTIME:-}" = pi ] || [ "${LOOP_RUNTIME:-}" = pi ]; then
    if [ -z "${LOOP_SEAT_RIG:-}" ] && [ -z "${OPENROUTER_API_KEY:-}" ]; then
      echo "loop: no OpenRouter key in this environment (the api-rig unit holds it); no worker allocated or steer changed" >&2; return 2
    fi
    result="$(cd "$(repo_dir)" && "$ACCOUNT_CLI" resolve --provider openrouter --client pi \
      --account "${LOOP_ACCOUNT_ID:-openrouter}" --metered-ok --who loop --json)" || {
      echo "loop: the OpenRouter account cannot take a worker; no worker allocated or steer changed" >&2; return 2; }
    LOOP_ACCOUNT_ID="$(jq -r '.account // empty' <<<"$result")" || return 2
    [ -n "$LOOP_ACCOUNT_ID" ] || return 2
    return 0
  fi
  result="$(cd "$(repo_dir)" && "$ACCOUNT_CLI" resolve --provider anthropic --client claude \
    ${LOOP_ACCOUNT_ID:+--account "$LOOP_ACCOUNT_ID"} --who loop --json)" || {
    echo "loop: no Claude account can take a worker; no worker allocated or steer changed" >&2; return 2; }
  LOOP_ACCOUNT_ID="$(jq -r '.account // empty' <<<"$result")" || return 2
  [ -n "$LOOP_ACCOUNT_ID" ] || return 2
}

# Paid workers start only on the owner's word: loop.sh go/resume typed at a terminal, or from
# a session the owner is in (agent-run gives it OL_PORTAL term, desk or phone). Workers then
# launch as the owner's own run (portal desk). The tick alone never starts a paid worker.
owner_present() {
  # unit: the API rig's service (api-rig@<project>), which the owner installed and enabled with
  # his password; its daily and monthly caps stop dispatch (docs/api-rig.md).
  [ -t 0 ] && return 0
  case "${OL_PORTAL:-}" in term|desk|phone|unit) return 0 ;; esac
  return 1
}

repo_dir() {
  local d; d="$(awk -v r="$repo" '$1==r {print $2}' "$CONF" 2>/dev/null | head -1)"
  [ -n "$d" ] && git -C "$d" rev-parse --show-toplevel >/dev/null 2>&1 || { echo "loop: $repo is not mapped to a checkout in $CONF" >&2; exit 2; }
  echo "$d"
}
steer_word() { if [ -f "$ctl/steer" ]; then head -1 "$ctl/steer" | awk '{print $1}'; else echo pause; fi; }
steer_args() { if [ -f "$ctl/steer" ]; then head -1 "$ctl/steer" | cut -s -d' ' -f2-; fi; }
rig_branch() { if [ -f "$ctl/rig-branch" ]; then head -1 "$ctl/rig-branch"; fi; }
need_rig() {
  local d; d="$(rig_branch)"
  [ -n "$d" ] || { echo "loop: no rig branch is open for $repo; run: loop.sh start $repo <type/slug>" >&2; exit 3; }
  echo "$d"
}
rig_wt() { echo "$(repo_dir)/.claude/worktrees/rig-${1//\//-}"; }
repository_identity() {
  local common
  common="$(git -C "$1" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 1
  [ -n "$common" ] && (cd "$common" && pwd -P)
}
is_personal() {  # 1 at tiers 1 and 2 (the owner's own repositories); else 0
  case "$t_tier" in 1|2) echo 1 ;; *) echo 0 ;; esac
}
personal="$(is_personal)"
mode="$(awk -v r="$repo" '$1==r {print $3; exit}' "$CONF" 2>/dev/null)"
# Tasks are files (and the base is the local one) when the tracker is files or side; GitHub issues otherwise.
# tracker=side is a ghost project (SDD-PJ-10): the task files are in docs/tasks/ of the side folder (the registry
# field side=), on its HEAD, and the repository holds no task file.
side_mode() { [ "$t_tracker" = side ]; }
local_mode() { [ "$t_tracker" = files ] || side_mode; }
if side_mode && { [ -z "$t_side" ] || ! git -C "$t_side" rev-parse --git-dir >/dev/null 2>&1; }; then
  echo "loop: tracker=side needs the registry field side=<folder>, a Git repository; this one is '${t_side:-not set}'" >&2; exit 2
fi
tasks_dir() { if side_mode; then echo "$t_side"; else repo_dir; fi; }
tasks_ref() { if side_mode; then echo HEAD; else echo "$base_ref"; fi; }
side_done() {  # <issue>: move its task file to done/ in the side folder, and commit only that move there
  local f; f="$(python3 "$here/loop-tasks.py" "$t_side" HEAD to-move "$1" 2>/dev/null)" || return 0
  [ -n "$f" ] || return 0
  mkdir -p "$t_side/docs/tasks/done"
  git -C "$t_side" mv "$f" "docs/tasks/done/$(basename "$f")" &&
    git -C "$t_side" commit -q -m "chore(tasks): mark #$1 done" -- "$f" "docs/tasks/done/$(basename "$f")"
}
owner_terminal() {  # one exemption: close --push without --ready in a personal repository
  [ -t 0 ] && [ -t 1 ] && return 0
  [ "$verb" = close ] && [ "${push:-0}" = 1 ] && [ "${ready:-0}" = 0 ] && [ "$personal" = 1 ] && return 0
  # The daily tidy timer (integrations/systemd), which the owner installed: tidy --apply only.
  [ "$verb" = tidy ] && [ "${OL_PORTAL:-}" = unit ] && [ "${DEV_LOOP_TIDY_UNIT:-}" = 1 ] && return 0
  echo "loop: '$verb' is the owner's own act and runs in a terminal, never from an agent" >&2; exit 4
}
base_branch() {
  local b
  if [ -n "$(rig_branch)" ] && [ -s "$ctl/rig-base" ]; then
    b="$(cat "$ctl/rig-base")"
  else
    b="$t_base"
    if [ -z "$b" ] && [ "$personal" = 1 ]; then
      b="$(git -C "$(repo_dir)" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
      b="${b#origin/}"
    fi
    b="${b:-develop}"
  fi
  git check-ref-format "refs/heads/$b" >/dev/null 2>&1 && [[ "$b" != -* ]] || { echo "loop: invalid configured base" >&2; exit 2; }
  printf '%s\n' "$b"
}
base_ref="$(base_branch)"
# The ref a rig branch is cut from and measured against: the remote base, or the local one.
base_tip() { if local_mode; then echo "$base_ref"; else echo "origin/$base_ref"; fi; }
issue_json() {  # <issue> -> {title, body, labels}, from the task file or the GitHub issue
  if local_mode; then python3 "$here/loop-tasks.py" "$(tasks_dir)" "$(tasks_ref)" view "$1"
  else gh issue view "$1" --repo "$repo" --json title,body,labels; fi
}
# The ghost check's markers, the guard hook's: a tool-named Co-authored-by trailer or a generated-with line.
ATTRIBUTION='co-authored-by:.*(anthropic|openai|claude|codex|copilot|noreply@)|(^|[^a-z])generated with'
# The open rig branch names the ledger directory (/ as __); with none open, plans go to _next.
rig="$(rig_branch)"; rigd="${rig//\//__}"; [ -n "$rig" ] || rigd="_next"
out="$ctl/$rigd"; mkdir -p "$out/workers"

# Models come from pstack-model: the system file (/etc/dev-platform), the user's override, defaults.
PSTACK_MODEL="$here/../../../bin/pstack-model"
tier_role() {  # issue labels -> the model file's role for its worker
  case ",$1," in
    *",spec,"*|*",decision,"*|*",privacy,"*|*",security,"*) echo "judgment and prose" ;;
    *",documentation,"*) echo "mechanical" ;;
    *) echo "feature, refactoring" ;;
  esac
}
tier_model() {  # issue labels -> Claude Code model, optionally <model>-<effort> (MODELS.md tiers)
  # LOOP_MODEL may name a model, a tier slug (implementation-xhigh, judgment.2-max) or a role.
  if [ -n "${LOOP_MODEL:-}" ]; then
    "$PSTACK_MODEL" resolve "$LOOP_MODEL" --runtime claude --no-inherit 2>/dev/null \
      | awk -F'\t' 'NR == 1 { print $1 ($2 == "" ? "" : "-" $2) }' | grep . || echo "$LOOP_MODEL"
    return 0
  fi
  local role
  role="$(tier_role "$1")"
  case "$role" in
    "feature, refactoring")
       if [ -n "${LOOP_WORKER_MODEL:-}" ] && [ "$("$PSTACK_MODEL" source "$role" 2>/dev/null)" = default ]; then
         echo "$LOOP_WORKER_MODEL"; return 0
       fi ;;
  esac
  # A worker has no parent chat to inherit, and this loop starts Claude workers only.
  "$PSTACK_MODEL" resolve "$role" --runtime claude --no-inherit \
    | awk -F'\t' 'NR == 1 { print $1 ($2 == "" ? "" : "-" $2) }'
}
running_workers() {  # "pid issue" only for verified supervisors owned by this repository
  python3 "$here/worker-run.py" --running "$ctl" "$(repo_dir)"
}
worker_running() { running_workers | grep -qE " $1\$"; }
live_worktrees() {  # cwd of every running claude process
  local pid
  for pid in $(pgrep -x claude 2>/dev/null); do lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p'; done
  return 0
}
is_slot() { case "$(basename "$1")" in slot-[0-9]*) return 0 ;; esac; return 1; }
slot_issue() { cat "$1/.worker-issue" 2>/dev/null || true; }
worker_dirs() {  # every working copy that holds a worker: occupied slots, then old loop-* worktrees
  local p
  for p in "$(repo_dir)"/.claude/worktrees/slot-*; do [ -f "$p/.worker-issue" ] && echo "$p"; done
  for p in "$(repo_dir)"/.claude/worktrees/loop-*; do [ -d "$p" ] && echo "$p"; done
  return 0
}
issue_of_dir() { if is_slot "$1"; then slot_issue "$1"; else basename "$1" | sed -nE 's/^loop-([0-9]+)-.*/\1/p'; fi; }
worker_wt_of() {  # issue -> its working copy: the slot that holds it, or an old loop-<issue>-* worktree
  local p
  for p in $(worker_dirs); do [ "$(issue_of_dir "$p")" = "$1" ] && { echo "$p"; return 0; }; done
  return 0
}
worker_branch_of() {  # issue -> local type/slug-<issue> branch (old loop-* workers only; slots have none)
  git -C "$(repo_dir)" for-each-ref --format='%(refname:short)' 'refs/heads/*/*' | grep -E -- "-$1\$" | head -1; return 0
}
is_clone() { [ -d "$1/.git" ]; }  # engineer's clone; a worktree has a .git file
slot_head() {  # <slot> -> the commit its worker made (a clone's objects are fetched in first)
  local h
  h="$(git -c safe.directory="$1" -C "$1" rev-parse --verify -q HEAD)" || return 1
  if is_clone "$1"; then git -c safe.directory="$1" -C "$(repo_dir)" fetch -q "$1" HEAD 2>/dev/null || return 1; fi
  echo "$h"
}
free_slot() {  # -> a slot without a worker; a missing slot up to SLOTS counts as free; empty when all are busy
  local k p
  for k in $(seq 1 "$SLOTS"); do
    p="$(repo_dir)/.claude/worktrees/slot-$k"
    if [ ! -e "$p" ] || [ ! -f "$p/.worker-issue" ]; then echo "$p"; return 0; fi
  done
  return 0
}
scope_dirs() {  # task Scope: prefixes -> folders for a sparse cone (a file prefix gives its folder)
  local s
  tr ',' '\n' <<<"$1" | sed 's/^ *//; s/ *$//' | while IFS= read -r s; do
    [ -n "$s" ] && [ "$s" != unspecified ] || continue
    case "$s" in */) echo "${s%/}" ;; */*) dirname "$s" ;; *.*) ;; *) echo "$s" ;; esac
  done | sort -u
}
prepare_slot() {  # <slot> <scope>: the slot detached at the rig branch, clean, with a sparse cone if large
  local p="$1" scope="$2" dir; dir="$(repo_dir)"
  if [ "$WORKER_AS" = engineer ]; then
    # engineer is let into this folder only: a shared clone reads the checkout's objects in place
    # (objects/info/alternates) and writes its own. No full copy (SDD-SC-06).
    if [ -e "$p" ]; then if is_clone "$p"; then rm -rf -- "$p"; else git -C "$dir" worktree remove --force "$p"; fi; fi
    git clone -q --shared --no-checkout "$dir" "$p"
    git -C "$p" remote remove origin
    git -C "$p" checkout -q --detach "$(git -C "$dir" rev-parse "$rig")"
    git -C "$p" config user.name engineer; git -C "$p" config user.email engineer@dev-server
    echo '.worker-*' >> "$p/.git/info/exclude"
  else
    if [ -e "$p" ] && is_clone "$p"; then rm -rf -- "$p"; fi
    if [ ! -e "$p" ]; then
      git -C "$dir" worktree add -q --detach "$p" "$rig"
    else
      git -C "$p" checkout -q -f --detach "$rig"
      git -C "$p" clean -q -fdx
    fi
  fi
  if [ "$t_large" = 1 ] && [ -n "$(scope_dirs "$scope")" ]; then
    # shellcheck disable=SC2046
    git -C "$p" sparse-checkout set --cone $(scope_dirs "$scope")
  elif git -C "$p" config --bool core.sparseCheckout 2>/dev/null | grep -qx true; then
    git -C "$p" sparse-checkout disable
  fi
}
release_slot() {  # <working copy>: free a slot for the next task, or remove an old loop-* worktree
  if is_slot "$1"; then
    if is_clone "$1"; then rm -rf -- "$1"; else rm -f "$1"/.worker-*; fi
  else
    remove_wt "$1"
  fi
}
sync_clone() {  # <working copy> <branch>: a clone's branch, brought back as the checkout's branch
  is_clone "$1" || return 0
  git -c safe.directory="$1" -C "$(repo_dir)" fetch -q "$1" "+refs/heads/$2:refs/heads/$2" 2>/dev/null || true
}
remove_wt() {  # <working copy>: a clone is a folder; a worktree is the checkout's to remove
  if is_clone "$1"; then rm -rf -- "$1"; else git -C "$(repo_dir)" worktree remove --force "$1"; fi
}
worker_rows() {  # issue <tab> branch <tab> worktree <tab> ahead <tab> state <tab> seat rig, one per worker
  local dir wt i b ahead st seat c
  dir="$(repo_dir)"
  for wt in $(worker_dirs); do
    i="$(issue_of_dir "$wt")"
    if is_slot "$wt"; then
      b="$(basename "$wt")"; c="$(slot_head "$wt" || echo '?')"
    else
      b="$(git -c safe.directory="$wt" -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
      sync_clone "$wt" "$b"; c="$b"
    fi
    ahead="$(git -C "$dir" rev-list --count "${rig:-$(base_tip)}".."$c" 2>/dev/null || echo '?')"
    seat=""; grep -qsF 'OpenRig MANAGED BLOCK' "$wt/CLAUDE.md" "$wt/AGENTS.md" && seat="$(cat "$out/workers/$i.seat" 2>/dev/null || echo '?')"
    st=working
    if [ -f "$wt/.worker-blocked.md" ]; then st=blocked
    elif worker_running "$i"; then st=running
    elif [ -f "$wt/.worker-pr.md" ]; then st="ready for review"
    elif [ "$ahead" = 0 ]; then st="no commits"
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$i" "$b" "$wt" "$ahead" "$st" "$seat"
  done
}
folded_issues() { if [ -f "$out/folded.tsv" ]; then cut -f1 "$out/folded.tsv" | sort -un; fi; }
exclusions() {  # "N reason" lines for loop-sense: folded issues and issues with a local worker
  local i wt
  for i in $(folded_issues); do echo "$i folded, waits for the rig branch to land"; done
  for wt in $(worker_dirs); do
    i="$(issue_of_dir "$wt")"
    [ -n "$i" ] && echo "$i has a local worker"
  done
  return 0
}
sense() {  # write and print the PLAN
  local ex tasks=(); ex="$(mktemp)"; exclusions > "$ex"
  if local_mode; then tasks=(--tasks "$(tasks_dir)" "$(tasks_ref)"); fi
  "$here/loop-sense.sh" --repo "$repo" --local-cap "$CAP" --exclude-file "$ex" --out "$out/plan.md" \
    ${tasks[@]+"${tasks[@]}"}
  rm -f "$ex"
}
select_from_plan() {  # [only N ..|skip N ..] -> selected issue numbers, one per line
  local sel only="" skip="" mode="" a s
  sel="$(grep -oE '^  #[0-9]+ lane=' "$out/plan.md" 2>/dev/null | grep -oE '[0-9]+' || true)"
  for a in "$@"; do
    case "$a" in only) mode=only ;; skip) mode=skip ;; [0-9]*) [ "$mode" = only ] && only="$only $a"; [ "$mode" = skip ] && skip="$skip $a" ;; esac
  done
  if [ -n "$only" ]; then
    local kept=""
    for s in $sel; do case " $only " in *" $s "*) kept="$kept $s" ;; esac; done
    sel="$(tr ' ' '\n' <<<"$kept" | sed '/^$/d')"
  fi
  for s in $skip; do sel="$(grep -vx "$s" <<<"$sel" || true)"; done
  printf '%s\n' "$sel"
}
section() {  # <file> <header text> -> the section body, without its header
  awk -v h="## $2" '$0==h {f=1; next} /^## / {f=0} f' "$1" | sed '/^Closes #[0-9]*$/d'
}
dispatch() {  # <issue>...
  local dir base i j title labels scope slug kind branch wt model exclude
  dir="$(repo_dir)"
  base="$(git -C "$dir" rev-parse --short=8 "$rig")"
  # The worker's untracked files are excluded repository-wide (local only, never committed).
  exclude="$(git -C "$dir" rev-parse --path-format=absolute --git-path info/exclude)"; mkdir -p "$(dirname "$exclude")"
  grep -qxF '.worker-*' "$exclude" 2>/dev/null || echo '.worker-*' >> "$exclude"
  for i in "$@"; do
    [ "$(running_workers | wc -l | tr -d ' ')" -lt "$CAP" ] || { echo "loop: worker cap reached"; break; }
    j="$(issue_json "$i")"
    title="$(jq -r .title <<<"$j")"; labels="$(jq -r '[.labels[].name]|join(",")' <<<"$j")"
    scope="$(jq -r '(.body // "") | capture("(?m)^Scope: *(?<s>[^\n]+)")? .s // "unspecified"' <<<"$j")"
    slug="$(tr '[:upper:]' '[:lower:]' <<<"$title" | sed -E 's/^[a-z]+-[a-z]+[-:]? *//; s/[^a-z0-9]+/-/g; s/^-|-$//g' | cut -c1-36 | sed -E 's/-$//')"
    kind=fix; case ",$labels," in *",enhancement,"*|*",spec,"*) kind=feat ;; *",documentation,"*) kind=docs ;; esac
    # branch is a label for the session name only: a worker commits in a detached slot, no branch.
    branch="$kind/$slug-$i"; model="$(tier_model "$labels")"
    if [ -n "$(worker_wt_of "$i")" ]; then echo "#$i: a worker already holds it, not relaunched"; continue; fi
    wt="$(free_slot)"
    [ -n "$wt" ] || { echo "loop: all $SLOTS slots are busy"; break; }
    if local_mode; then
      task_path="$(jq -r .path <<<"$j")"; where_task="in this worktree"
      if side_mode; then task_path="$t_side/$task_path"; where_task="outside this worktree; do not change it"; fi
      read_task="Read the task file \`$task_path\` $where_task: it is the request, and a
   later section in it wins over an earlier one. Read the spec sections the task cites; read
   the code and its tests before editing."
    else
      read_task="Read the issue with its comments (\`gh issue view $i --repo $repo --comments\`): the owner refines
   the request in comments, and a comment posted after the body wins. Read the spec sections the
   issue cites; read the code and its tests before editing."
    fi
    prepare_slot "$wt" "$scope"
    echo "$i" > "$wt/.worker-issue"
    if [ "${LOOP_RUNTIME:-claude}" = pi ]; then
      budget_line="Budget, enforced: \$${LOOP_WORKER_COST_LIMIT:-2} for this run (a retry on a stronger model gets more), $MAX_TURNS turns, and a first change in this worktree (a failing test or the first edit) by turn ${LOOP_WORKER_FIRST_CHANGE:-20}: a run with no change by then stops. Read the files the task and its spec items name first, not the whole repository; use ask_advice when stuck."
    else
      budget_line="Token budget: $TOKEN_CEILING (worker instruction; the CLI has no total-token flag)."
    fi
    frozen_line=""
    if [ "$t_decisions" = frozen ]; then
      frozen_line="
Decision records are frozen here: never add, change or delete a file under \`docs/decisions/\` and
never add a \`SPEC-AMENDMENTS.md\`. The commit hook and the fold refuse both. Follow AGENTS.md."
    fi
    if [ "$t_spec" = domains ]; then
      frozen_line="$frozen_line
The specification is \`docs/spec/<domain>/sdd.md\` and \`tdd.md\`; find an item with \`docs/spec/index.json\`.
A build task may change only the \`status:\`, \`tests:\` and \`code:\` lines of the items it cites,
and the regenerated \`docs/spec/index.json\`."
    fi
    # A goal forge (dev-forge loop sets LOOP_PROOF): the worker runs the short proof of the profile, and the
    # orchestrator runs the full check one time on the batch (SDD-SC-08, SDD-SC-22).
    if [ -n "${LOOP_PROOF:-}" ]; then
      proof_text="Run this short proof on the final head: $LOOP_PROOF."
      [ "$LOOP_PROOF" != none ] || proof_text="The profile of this forge names no proof: run no check."
      check_step="Keep this brief for recovery. $proof_text
   Do NOT run the full check (\`check-once.sh\`, \`bin/check\`, \`bun run check\`) and do not run a build: the
   orchestrator runs the full check one time on the batch. Keep the final lines of the proof for the next step."
    else
      check_step="Keep this brief for recovery, then run the full check on the final head with
   \`bash $HOOKS/check-once.sh\` (it runs the repository's check, \`bin/check\` or \`bun run check\`, and records the passing tree so the
   check is not repeated at exit). Keep its final lines for the next step."
    fi
    cat > "$wt/.worker-brief.md" <<EOF
# Worker brief: issue #$i
Repository $repo. This directory is a work slot, detached at \`$rig\` ($base). Commit here, on
the detached HEAD. Do not make a branch: the fold takes your commits by their commit ID.
Read AGENTS.md and CONTRIBUTING.md here first; the repository's rules win over this brief.
Write commit messages in ASD-STE100 (short sentences, active voice), in the form \`type(scope): summary\`.
Issue #$i: $title
Scope (only these path prefixes may change): $scope
The status marker that cites this task, and any lock digest that guards it, are always in scope
as well.$frozen_line The specification text itself is not: it changes only through a spec task. If the work
needs a requirement or design item to say something different, write that in
\`.worker-blocked.md\` and stop; merging refuses a build branch that edits it.
1. $read_task
2. If the fix needs code or test files outside the scope, write what you found (the paths you
   would need and why) to \`.worker-blocked.md\` in this directory and stop. Do not comment on the
   issue. If the code already matches the contract on this base and only the specification's
   status marker is stale, the change is that marker and its lock digest: make it and continue.
   Work in the foreground. Do not spawn background agents; let the check finish.
   Ceiling: one worker, $MAX_TURNS turns, $MAX_SECONDS seconds (enforced by runner).
   $budget_line Stop on quota errors.
3. Otherwise: smallest coherent change with tests and affected spec lines; commits
   \`type(scope): summary\`, body says why; no names of people, tools, models or sessions in
   commits or code. Stage only the files of the change. Never stage a \`.worker-*\` file.
   No \`Co-authored-by\` trailer and no generated-with line: the commit is the owner's.
4. $check_step
5. Write \`.worker-pr.md\` in this directory with the four sections of the repository's pull
   request template as \`## \` headings: What changed and why, Verification (the check's final
   lines), Deploy and provider impact, Review notes. End it with the line \`Closes #$i\`. Then stop.
Never push, open a pull request, comment on GitHub, merge, mark ready, approve, deploy, restart,
rebase or amend, make a branch, or touch another worktree. When you have written .worker-pr.md,
stop; the control seat or the owner folds your commits into the rig branch on this machine.
EOF
    launch_worker "$i" "$wt" "$model" "$branch" "$title" "$labels" "$scope"
  done
}

session_area() {  # <scope> <labels>: commit scope for the session title; `repo` only when nothing fits
  local first seg area="" label
  first="${1%%,*}"; first="${first#"${first%%[![:space:]]*}"}"
  case "$first" in unspecified|""|.|./) first="" ;; esac
  local IFS=/
  for seg in $first; do
    seg="${seg%.*}"
    case "$seg" in ""|.|..|lib|src|app|apps|packages|skills|integrations|tests|test|docs) continue ;; esac
    area="$seg"; break
  done
  unset IFS
  if [ -z "$area" ]; then  # an `area:x` or `scope:x` label
    for label in ${2//,/ }; do
      case "$label" in area:*|scope:*) area="${label#*:}"; break ;; esac
    done
  fi
  area="$(tr '[:upper:]_' '[:lower:]-' <<<"$area" | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' | cut -c1-24 | sed -E 's/-+$//')"
  [ -n "$area" ] || area=repo
  printf '%s' "$area"
}

session_purpose() {  # <branch>: the branch kind on the purpose list in lib/ai_ecosystem/naming.py
  case "${1%%/*}" in feat|fix|refactor|docs|test|chore) printf '%s' "${1%%/*}" ;; *) printf loop ;; esac
}

session_title_for() {  # client provider model account i worktree branch title labels scope: the unified session title
  local client="$1" provider="$2" model="$3" account="$4" i="$5" wt="$6" branch="$7" title="$8" labels="$9" scope="${10}"
  local description area purpose title_text
  local -a title_argv
  # Display metadata only: no native ID changes or historical session edits.
  description="$(jq -nr --arg title "$title" '$title | gsub("[[:space:][:cntrl:]]+"; " ") | sub("^ +"; "") | sub("[ .]+$"; "") | .[0:60]')"
  [ -n "$description" ] || description="Implement issue"
  area="$(session_area "$scope" "$labels")"; purpose="$(session_purpose "$branch")"
  title_text="$purpose($area): $description #$i"
  # One argv through ai-title (no shell parsing of the issue title).
  title_argv=("$TITLE_CLI" format --client "$client" --who "loop#$i" --type loop --purpose "$purpose"
    --provider "$provider" --model "$model" --cwd "$wt" --branch "$branch")
  [ -z "$account" ] || title_argv+=(--account "$account")
  "${title_argv[@]}" -- "$title_text" || { echo "loop: could not format the session title" >&2; printf '%s' "$title_text"; }
}

launch_pi_worker() {  # issue worktree model branch title: one headless Pi run on the OpenRouter key
  # The API rig's worker (docs/api-rig.md): a new Pi session per task, its model the model file's
  # line for the task resolved for openrouter (never a subscription), the platform guard, the
  # advice tool and worker-limits.mjs (turn and billed-token caps) loaded from its own agent
  # folder, the wall-time cap from worker-run. The key reaches Pi by name from the rig's
  # environment (worker-run passes OPENROUTER_API_KEY for LOOP_RUNTIME=pi), never as an argument.
  local i="$1" wt="$2" branch="$4" title="$5" labels="${6:-}" scope="${7:-}" role pimodel agent session_title piseat="$here/../../../lib/ai_ecosystem/piseat.py"
  [ -n "${OPENROUTER_API_KEY:-}" ] || { echo "#$i: no OpenRouter key in this environment (the api-rig unit holds it); not started" >&2; return 2; }
  role="${LOOP_MODEL:-$(tier_role "$(jq -r '[.labels[].name]|join(",")' <<<"$(issue_json "$i")")")}"
  [ "$role" != "feature, refactoring" ] || role="rig worker"
  # The retry: a task that already had a Pi run and has no commit on its branch goes to the
  # stronger model (MODELS.md rule 2, escalate one tier on failure), with its own dollar cap.
  local tries ahead limit="${LOOP_WORKER_COST_LIMIT:-2}"
  tries="$(grep -c '"runtime":"pi"' "$out/workers/$i.account.jsonl" 2>/dev/null || true)"
  ahead="$(git -C "$wt" rev-list --count "$rig..HEAD" 2>/dev/null || echo 0)"
  if [ -z "${LOOP_MODEL:-}" ] && [ "${tries:-0}" -ge 1 ] && [ "$ahead" = 0 ]; then
    role="rig worker retry"; limit="${LOOP_WORKER_RETRY_COST_LIMIT:-6}"
  fi
  pimodel="$(python3 "$piseat" model "$role")" || { echo "#$i: no OpenRouter model for $role; not started" >&2; return 2; }
  agent="$(python3 "$piseat" prepare-dir "$out/workers/$i.pi-agent" worker-limits.mjs)" || return 2
  mkdir -p "$out/workers/$i.pi-sessions"
  session_title="$(session_title_for pi openrouter "$pimodel" "" "$i" "$wt" "$branch" "$title" "$labels" "$scope")"
    jq -cn --arg id "$selected_account" --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg model "$pimodel" --arg cap "$limit" \
    '{account_id:$id, runtime:"pi", model:$model, dollar_cap:$cap, attempted_at:$at, scope:"new worker attempt"}' >> "$out/workers/$i.account.jsonl"
  rm -f "$out/workers/$i.exit"
  ( cd "$wt" || exit 2
    export LOOP_RUNTIME=pi LOOP_WORKER_MAX_TURNS="$MAX_TURNS" LOOP_WORKER_TOKEN_LIMIT="${LOOP_WORKER_TOKEN_LIMIT:-20000000}"
    export LOOP_WORKER_COST_LIMIT="$limit" LOOP_WORKER_FIRST_CHANGE="${LOOP_WORKER_FIRST_CHANGE:-20}" LOOP_WORKER_BASE="$rig"
    export OL_PORTAL="${OL_PORTAL:-desk}"
    export DEV_SESSION_WHO="loop#$i" DEV_SESSION_TYPE=loop DEV_SESSION_PROVIDER=openrouter DEV_SESSION_MODEL="$pimodel"
    unset DEV_SESSION_ACCOUNT
    python3 - "$out/workers/$i.pid" "$out/workers/$i.log" \
      "$here/worker-run.py" "$MAX_SECONDS" "$out/workers/$i.exit" -- \
      env "PI_CODING_AGENT_DIR=$agent" "PI_CODING_AGENT_SESSION_DIR=$out/workers/$i.pi-sessions" \
      pi --mode json --no-approve --model "$pimodel" --name "$session_title" \
      "$(cat .worker-brief.md)" <<'PYEOF'
from pathlib import Path
import subprocess
import sys

pid_path, log_path, *command = sys.argv[1:]
with open(log_path, 'w') as log:
    supervisor = subprocess.Popen([sys.executable, *command], stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
target = Path(pid_path)
tmp = target.with_suffix('.pid.tmp')
tmp.write_text(str(supervisor.pid) + '\n')
tmp.replace(target)
PYEOF
  )
  echo "#$i -> $branch (pi $pimodel) pid $(cat "$out/workers/$i.pid")"
}
launch_worker() {  # issue worktree model branch title [labels scope]: start a new native conversation
  local i="$1" wt="$2" model="$3" branch="$4" title="$5" labels="${6:-}" scope="${7:-}"
  local envf common v session_title effort=""
  case "${model##*-}" in max|xhigh|high|medium|low) effort="${model##*-}"; model="${model%-*}" ;; esac
  local selected_account="${LOOP_ACCOUNT_ID:-}"
  local -a worker_command issue_tools=()
  local_mode || issue_tools=("Bash(gh issue view *)")
  # LOOP_RUNTIME=hand: the slot and the brief are ready and the loop starts nothing. The caller starts the one-task
  # worker itself: an in-session agent of a Claude Code orchestrator, or one `codex exec` run in the slot.
  if [ "${LOOP_RUNTIME:-claude}" = hand ]; then
    echo "#$i -> $wt (hand: start one worker in that folder with .worker-brief.md)"; return 0
  fi
  if [ -n "${LOOP_SEAT_RIG:-}" ]; then  # an interactive seat in the owner's running rig instead
    # The loop's selected account is a Claude one; a Codex seat takes LOOP_SEAT_ACCOUNT or its native home.
    # A Pi seat runs on the OpenRouter key of its rig's daemon; its model is LOOP_MODEL (a tier
    # slug or role) or the model file's line for the task's labels, resolved for openrouter.
    local seat_account="${LOOP_SEAT_ACCOUNT:-}" pi_role=""
    [ -n "$seat_account" ] || [ "${LOOP_SEAT_RUNTIME:-claude}" != claude ] || seat_account="$selected_account"
    if [ "${LOOP_SEAT_RUNTIME:-claude}" = pi ]; then
      seat_account=""
      pi_role="${LOOP_MODEL:-$(tier_role "$(jq -r '[.labels[].name]|join(",")' <<<"$(issue_json "$i")")")}"
      [ "$pi_role" != "feature, refactoring" ] || pi_role="rig worker"
    fi
    DEV_WORKSPACE_PI_MODEL="$pi_role" "${DEV_WORKSPACE:-$here/../../../bin/dev-workspace}" add-worker "${LOOP_SEAT_RUNTIME:-claude}" \
      --rig "$LOOP_SEAT_RIG" --cwd "$wt" ${seat_account:+--account "$seat_account"} \
      --purpose "$(session_purpose "$branch")" --area "$(session_area "$scope" "$labels")" \
      || { echo "#$i: no seat confirmed in $LOOP_SEAT_RIG; the worktree stays at $wt"; return 0; }
    echo "$LOOP_SEAT_RIG" > "$out/workers/$i.seat"  # fold releases the seat from this rig
    # A seat opens idle at its prompt. Tell its worker to begin once it is ready; if that fails,
    # the brief is still in the worktree and a person can say the same thing.
    local seat="workers-issue-$i@$LOOP_SEAT_RIG"
    if "${LOOP_RIG:-rig}" send "$seat" "Start task #$i now: read .worker-brief.md in this folder and follow it to the end." \
        --wait-for-idle "${LOOP_SEAT_START_WAIT:-120}" >/dev/null 2>&1; then
      echo "#$i -> $branch (seat in $LOOP_SEAT_RIG, told to start)"
    else
      echo "#$i -> $branch (seat in $LOOP_SEAT_RIG; it did not confirm the start message: rig send $seat \"Start task #$i\")"
    fi
    return 0
  fi
  [ -n "$selected_account" ] || { echo "#$i: no account resolved; not started" >&2; return 2; }
  if [ "${LOOP_RUNTIME:-claude}" = pi ]; then launch_pi_worker "$@"; return; fi
  local -a model_args=(--model "$model")
  worker_command=("$ACCOUNT_CLI" run --client claude --account "$selected_account" --)
  if is_clone "$wt"; then  # engineer's clone: engineer runs it, let into this one folder by its launcher
    case "$model" in
      claude-*) ;; opus) model=claude-opus-5-5 ;; sonnet) model=claude-sonnet-5-5 ;; haiku) model=claude-haiku-4-5-20251001 ;;
      *) echo "#$i: $model is not a Claude model the launcher knows; not started" >&2; return 2 ;;
    esac
    model_args=()  # the launcher passes OL_MODEL to the harness itself
    worker_command=(env "OL_ACCOUNT=$selected_account" "OL_MODEL=$model" "${LOOP_AGENT:-agent}" engineer "$wt" --)
  fi
  jq -cn --arg id "$selected_account" --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{account_id:$id, runtime:"claude", attempted_at:$at, scope:"new worker attempt"}' >> "$out/workers/$i.account.jsonl"
  session_title="$(session_title_for claude-cli anthropic "$model" "$selected_account" "$i" "$wt" "$branch" "$title" "$labels" "$scope")"
  common="$(git -C "$wt" rev-parse --path-format=absolute --git-common-dir)"
  envf="${DEV_PLATFORM_ENV_DIR:-$HOME/.config/dev-platform/env.d}/$(basename "$(dirname "$common")").sh"
  rm -f "$out/workers/$i.exit"
  ( cd "$wt" || exit 2
    [ ! -f "$envf" ] || . "$envf"
    for v in ${DEV_PLATFORM_ENV_PASS:-}; do
      [[ "$v" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "loop: invalid environment variable name" >&2; exit 2; }
      case "$v" in HOME|PATH|USER|LANG|TERM|BASH_ENV|ENV|SHELLOPTS|*TOKEN*|*SECRET*|*PASSWORD*|*CREDENTIAL*|*_KEY) echo "loop: reserved or credential variable in DEV_PLATFORM_ENV_PASS" >&2; exit 2 ;; esac
      export "$v"
    done
    export DEV_PLATFORM_ENV_PASS
    export DEV_SESSION_WHO="loop#$i" DEV_SESSION_TYPE=loop DEV_SESSION_PROVIDER=anthropic DEV_SESSION_MODEL="$model"
    export DEV_SESSION_ACCOUNT="$selected_account"
    export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="${LOOP_BG_WAIT_CEILING_MS:-900000}"
    export OL_PORTAL=desk  # the owner's own run: dispatch got here only on his word (owner_present)
    # Detach the supervisor too: tool cleanup may terminate the launcher's process group.
    # nohup only ignores SIGHUP; losing the supervisor leaves its detached child unbounded.
    python3 - "$out/workers/$i.pid" "$out/workers/$i.log" \
      "$here/worker-run.py" "$MAX_SECONDS" "$out/workers/$i.exit" -- \
      "${worker_command[@]}" --name "$session_title" ${model_args[@]+"${model_args[@]}"} ${effort:+--effort "$effort"} --max-turns "$MAX_TURNS" -p "$(cat .worker-brief.md)" --permission-mode acceptEdits \
      --allowedTools "Bash(git status *)" "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)" \
        "Bash(git add *)" "Bash(git commit *)" ${issue_tools[@]+"${issue_tools[@]}"} \
        "Bash(uv *)" "Bash(bin/check*)" "Bash(bin/spec-check*)" "Bash(python3 *)" "Bash(pytest *)" \
        "Bash(ls *)" "Bash(find *)" "Bash(cat *)" "Bash(head *)" "Bash(tail *)" "Bash(wc *)" "Bash(grep *)" "Bash(rg *)" \
        "Bash(pwd)" "Bash(which *)" "Bash(mkdir *)" "Bash(rm .worker-blocked.md)" \
        "Bash(bun install --frozen-lockfile)" "Bash(bun run check)" "Bash(bun run *)" "Bash(bun test *)" "Bash(bun install*)" \
        "Bash(~/.bun/bin/bun run *)" "Bash(~/.bun/bin/bun test *)" "Bash(~/.bun/bin/bun install*)" \
        "Bash($HOME/.bun/bin/bun *)" "Bash(npx vitest *)" "Bash(npm *)" "Bash(node *)" "Bash(npx *)" "Bash(rm .worker-brief.md)" \
        "Bash(bash $HOOKS/check-once.sh*)" \
      <<'PY'
from pathlib import Path
import subprocess
import sys

pid_path, log_path, *command = sys.argv[1:]
with open(log_path, 'w') as log:
    supervisor = subprocess.Popen([sys.executable, *command], stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
target = Path(pid_path)
tmp = target.with_suffix('.pid.tmp')
tmp.write_text(str(supervisor.pid) + '\n')
tmp.replace(target)
PY
  )
  echo "#$i -> $branch ($model) pid $(cat "$out/workers/$i.pid")"
}

end_rig() {  # remove the rig worktree and branch, record the rig closed, steer pause
  local dir; dir="$(repo_dir)"
  [ -d "$(rig_wt "$rig")" ] && git -C "$dir" worktree remove --force "$(rig_wt "$rig")"
  # The check folder and the marker of a goal forge end with the goal (dev-forge batch, dev-forge loop).
  [ ! -d "$dir/.claude/worktrees/forge-check" ] || git -C "$dir" worktree remove --force "$dir/.claude/worktrees/forge-check" || true
  rm -f "$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir)/dev-platform/orchestrated"
  git -C "$dir" branch -D "$rig" >/dev/null 2>&1 || true
  mv "$ctl/rig-branch" "$out/rig-branch.closed"; echo "$rig" > "$ctl/last-rig"; echo pause > "$ctl/steer"
}

# Serialize dispatch decisions. A missing/leftover lock fails closed; never auto-launch twice.
case "$verb" in
  go|tick|resume)
    mkdir "$ctl/dispatch-lock" 2>/dev/null || { echo "loop: another dispatch holds $ctl/dispatch-lock" >&2; exit 3; }
    trap 'rmdir "$ctl/dispatch-lock"' EXIT
    # Validate ownership outside a pipeline: set -e must stop on ambiguous identity.
    running_workers >/dev/null
    ;;
esac

case "$verb" in
  status)
    dir="$(repo_dir)"
    echo "STATUS $(TZ=Etc/UTC date '+%Y-%m-%d %H:%M') $repo"
    if [ -f "$ctl/steer" ]; then echo "steer: $(head -1 "$ctl/steer")"; else echo "steer: pause (no steer file)"; fi
    if [ -n "$rig" ]; then
      echo "rig branch: $rig, $(git -C "$dir" rev-list --count "$(base_tip)".."$rig" 2>/dev/null || echo '?') commits ahead of $(base_tip), worktree $(rig_wt "$rig")"
    else
      echo "rig branch: none open (loop.sh start $repo <type/slug>)"
      if [ -s "$ctl/last-rig" ]; then  # what landed last, from its own ledger
        last="$(cat "$ctl/last-rig")"; out="$ctl/${last//\//__}"
        echo "last rig branch: $last"
      fi
    fi
    echo "running:"; r="$(running_workers)"; if [ -n "$r" ]; then sed 's/^\([0-9]*\) \(.*\)$/  issue #\2 pid \1/' <<<"$r"; else echo "  none"; fi
    echo "worker branches:"; rows="$(worker_rows)"
    if [ -n "$rows" ]; then
      awk -F'\t' '{print "  #" $1 " " $2 " ahead " $4 ": " $5 ($6 != "" ? ", seat in " $6 : "")}' <<<"$rows"
    else echo "  none"; fi
    echo "folded:"; if [ -s "$out/folded.tsv" ]; then awk -F'\t' '{print "  #" $1 " " $2 " " $3 " " $4}' "$out/folded.tsv"; else echo "  none"; fi
    if [ -f "$out/merged" ]; then echo "rig branch: merged locally into $(cat "$out/merged")"
    elif local_mode; then echo "pull request: none (local; loop.sh close --merge)"
    elif [ -f "$out/pr-url" ]; then echo "pull request: $(cat "$out/pr-url") as $(cat "$out/pushed-as" 2>/dev/null)"; else echo "pull request: not opened (loop.sh close)"; fi
    ;;
  state)  # the status facts as JSON, for the ai menu; read-only
    dir="$(repo_dir)"; rows="$(worker_rows)"; last=""; [ -n "$rig" ] || last="$(cat "$ctl/last-rig" 2>/dev/null || true)"
    jq -n --arg repo "$repo" --arg mode "${mode:-}" --arg steer "$(steer_word)" --arg rig "$rig" --arg base "$base_ref" \
      --arg tip "$(base_tip)" --arg worktree "$( [ -z "$rig" ] || rig_wt "$rig")" --arg last "$last" \
      --arg ahead "$( [ -z "$rig" ] || git -C "$dir" rev-list --count "$(base_tip)".."$rig" 2>/dev/null || echo '?')" \
      --arg folded "$(folded_issues | paste -sd' ' -)" --arg rows "$rows" '
      def opt: if . == "" then null else . end;
      {repo: $repo, mode: $mode, steer: $steer, rig: ($rig | opt), base: $base, base_tip: $tip,
       worktree: ($worktree | opt), ahead: ($ahead | opt), last_rig: ($last | opt),
       folded: ($folded | split(" ") | map(select(. != "") | tonumber)),
       workers: ($rows | split("\n") | map(select(. != "") | split("\t")
         | {issue: (.[0] | tonumber), branch: .[1], worktree: .[2], ahead: .[3], state: .[4], seat: (.[5] // "" | opt)}))}'
    ;;
  plan)
    sense
    ;;
  start)
    [ -z "$rig" ] || { echo "loop: a rig branch is already open ($rig)" >&2; exit 3; }
    rig="${1:-}"
    [ -n "$rig" ] || { echo "loop: name the rig branch for this goal: loop.sh start $repo <type/slug>, for example feat/snake-game" >&2; exit 2; }
    [[ "$rig" =~ ^(feat|fix|docs|refactor|test|chore|perf)/[a-z0-9][a-z0-9._-]*$ ]] && git check-ref-format "refs/heads/$rig" ||
      { echo "loop: the rig branch is an ordinary type/slug branch, for example feat/snake-game" >&2; exit 2; }
    rigd="${rig//\//__}"; out="$ctl/$rigd"; mkdir -p "$out/workers"
    if [ -f "$out/pr-merged" ] || [ -f "$out/merged" ]; then
      n=1; while [ -e "$out.$n" ]; do n=$((n+1)); done
      mv "$out" "$out.$n"; mkdir -p "$out/workers"
      echo "ledger for $rig already closed; the earlier one is kept as $(basename "$out").$n"
    fi
    dir="$(repo_dir)"; local_mode || git -C "$dir" fetch -q origin "$base_ref"
    wt="$(rig_wt "$rig")"
    if git -C "$dir" show-ref -q --verify "refs/heads/$rig"; then echo "loop: local branch $rig already exists; delete or rename it first" >&2; exit 3; fi
    git -C "$dir" worktree add -q -b "$rig" "$wt" "$(base_tip)"
    echo "$rig" > "$ctl/rig-branch"; echo "$base_ref" > "$ctl/rig-base"
    [ -f "$ctl/steer" ] || echo pause > "$ctl/steer"
    echo "rig branch $rig cut from $(base_tip) $(git -C "$dir" rev-parse --short=8 "$(base_tip)") at $wt"; echo
    sense
    echo; echo "steer: $(steer_word). Dispatch with: loop.sh go $repo [only N|skip N]"
    ;;
  go)
    [ -n "$rig" ] || need_rig >/dev/null
    verify_loop_account
    owner_present || { echo "loop: paid workers start only on the owner's word (a terminal, or a session he is in); nothing dispatched" >&2; exit 2; }
    printf 'go%s\n' "${*:+ $*}" > "$ctl/steer"
    sense >/dev/null
    sel="$(select_from_plan "$@")"
    dir="$(repo_dir)"; keep=""
    for i in $sel; do [ -z "$(worker_wt_of "$i")" ] || continue; keep="$keep $i"; done
    [ -n "${keep// /}" ] || { echo "steer: go written; nothing to dispatch (see $out/plan.md)"; exit 0; }
    echo "GO $(TZ=Etc/UTC date '+%Y-%m-%d %H:%M') $repo on $rig"
    # shellcheck disable=SC2086
    dispatch $keep
    ;;
  resume)
    [ -n "$rig" ] || need_rig >/dev/null
    verify_loop_account
    owner_present || { echo "loop: paid workers start only on the owner's word (a terminal, or a session he is in); nothing dispatched" >&2; exit 2; }
    [ $# -gt 0 ] || { echo "loop: resume needs issue numbers" >&2; exit 2; }
    dir="$(repo_dir)"
    for i in "$@"; do
      [[ "$i" =~ ^[0-9]+$ ]] || { echo "loop: invalid issue number" >&2; exit 2; }
      [ "$(running_workers | wc -l | tr -d ' ')" -lt "$CAP" ] || { echo "loop: worker cap reached"; break; }
      wt="$(worker_wt_of "$i")"
      [ -n "$wt" ] || { echo "#$i: no worker worktree"; continue; }
      worker_running "$i" && { echo "#$i: still running"; continue; }
      [ ! -f "$wt/.worker-pr.md" ] || { echo "#$i: ready for review, not relaunched"; continue; }
      [ -f "$wt/.worker-brief.md" ] || { echo "#$i: brief gone, worker finished; review or fold instead"; continue; }
      [ -f "$wt/.worker-blocked.md" ] && { echo "#$i: blocked, widen the scope first"; continue; }
      branch="$(git -C "$wt" rev-parse --abbrev-ref HEAD)"
      j="$(issue_json "$i")"
      title="$(jq -r '.title // ""' <<<"$j")"
      labels="$(jq -r '[.labels[].name]|join(",")' <<<"$j")"; model="$(tier_model "$labels")"
      # The owner may have widened Scope: in the issue body since dispatch; the brief carries the current line.
      scope="$(jq -r '(.body // "") | capture("(?m)^Scope: *(?<s>[^\n]+)")? .s // "unspecified"' <<<"$j")"
      python3 - "$wt/.worker-brief.md" "$scope" <<'PY'
import re,sys
p,scope=sys.argv[1],sys.argv[2]; s=open(p).read()
s=re.sub(r'^Scope \(only these path prefixes may change\): .*$', lambda m: 'Scope (only these path prefixes may change): '+scope, s, count=1, flags=re.M)
open(p,'w').write(s)
PY
      [ -f "$out/workers/$i.log" ] && mv "$out/workers/$i.log" "$out/workers/$i.log.$(date +%H%M%S)"
      launch_worker "$i" "$wt" "$model" "$branch" "$title" "$labels" "$scope"
    done
    ;;
  pause)
    echo pause > "$ctl/steer"; echo "steer: pause written for $repo; the tick dispatches nothing until loop.sh go"
    ;;
  tick)
    [ "$(steer_word)" = go ] || { echo NO_REPLY; exit 0; }
    [ -n "$rig" ] || { echo NO_REPLY; exit 0; }
    verify_loop_account
    owner_present || { echo NO_REPLY; exit 0; }  # unattended: paid workers wait for the owner's go
    running="$(running_workers | wc -l | tr -d ' ')"
    cap=$((CAP - running)); [ "$cap" -gt 0 ] || { echo NO_REPLY; exit 0; }
    sense >/dev/null
    # shellcheck disable=SC2046
    cand="$(select_from_plan $(steer_args))"
    dir="$(repo_dir)"; sel=""
    for i in $cand; do
      [ "$cap" -gt 0 ] || break
      [ -z "$(worker_wt_of "$i")" ] || continue
      sel="$sel $i"; cap=$((cap-1))
    done
    [ -n "${sel// /}" ] || { echo NO_REPLY; exit 0; }
    echo "TICK $(TZ=Etc/UTC date '+%Y-%m-%d %H:%M') $repo on $rig"
    # shellcheck disable=SC2086
    dispatch $sel
    ;;
  collect)
    planned="$(grep -cE '^  #[0-9]+ lane=' "$out/plan.md" 2>/dev/null || echo 0)"
    dispatched="$(ls "$out"/workers/*.pid "$out"/workers/*.seat 2>/dev/null | wc -l | tr -d ' ')"
    "$here/loop-collect.sh" --repo "$repo" --dir "$(repo_dir)" --rig "$rig" --state "$out" --hooks "$HOOKS" \
      --planned "$planned" --dispatched "$dispatched" --out "$out/cycle.md" --base "$(base_tip)" \
      $(local_mode && echo --local)
    ;;
  fold)
    # Not the owner's act: folding a finished worker into the rig branch never touches the base.
    # One squash commit for each task (SDD-SC-07). The full check ran in the worker and runs once
    # more at close or land; the fold checks conflicts, scope and the specification only (SDD-SC-08).
    need_rig >/dev/null; dir="$(repo_dir)"; rwt="$(rig_wt "$rig")"
    [ -d "$rwt" ] || { echo "loop: rig worktree $rwt is missing" >&2; exit 3; }
    [ -z "$(git -C "$rwt" status --porcelain --untracked-files=no)" ] || { echo "loop: the rig worktree has uncommitted changes; commit or stash in $rwt first" >&2; exit 3; }
    from=""; items=()
    while [ $# -gt 0 ]; do
      case "$1" in --from) from="${2:?loop: --from <remote branch>}"; shift 2 ;; *) items+=("$1"); shift ;; esac
    done
    [ ${#items[@]} -gt 0 ] || { echo "loop: fold needs issue numbers or branch names" >&2; exit 2; }
    if [ -n "$from" ]; then
      # A cloud agent's branch (Codex cloud, Claude Code on the web): tier 2 and 3 GitHub repositories only.
      [ ${#items[@]} = 1 ] && [[ "${items[0]}" =~ ^[0-9]+$ ]] || { echo "loop: fold N --from <branch> takes one issue number" >&2; exit 2; }
      case "$t_tier:$t_forge" in 2:github|3:github) ;; *) echo "loop: cloud branches fold only into tier 2 or 3 GitHub repositories" >&2; exit 2 ;; esac
      git check-ref-format "refs/heads/$from" >/dev/null 2>&1 && [[ "$from" != -* ]] || { echo "loop: invalid branch name" >&2; exit 2; }
      git -C "$dir" fetch -q origin "refs/heads/$from" || { echo "loop: origin has no branch $from" >&2; exit 3; }
      from_sha="$(git -C "$dir" rev-parse FETCH_HEAD)"
    fi
    for a in "${items[@]}"; do
      wt=""; b=""; c=""
      case "$a" in
        [0-9]*) i="$a"
                if [ -n "$from" ]; then b="origin/$from"; c="$from_sha"
                else
                  wt="$(worker_wt_of "$i")"
                  if [ -n "$wt" ] && is_slot "$wt"; then b="$(basename "$wt")"; c="$(slot_head "$wt" || true)"
                  else b="$(worker_branch_of "$i")"; c="$b"; [ -z "$wt" ] || [ -z "$b" ] || sync_clone "$wt" "$b"; fi
                fi ;;
        *) b="$a"; c="$a"; i="${b##*-}" ;;
      esac
      if [ -z "$c" ] || ! git -C "$dir" rev-parse -q --verify "$c^{commit}" >/dev/null; then echo "  #$i: no worker commits to fold"; continue; fi
      c="$(git -C "$dir" rev-parse "$c^{commit}")"
      if worker_running "$i"; then echo "  #$i: worker still running; wait for it or stop it first"; continue; fi
      if [ -n "$wt" ] && [ -f "$wt/.worker-blocked.md" ]; then echo "  #$i: blocked, not folded:"; sed 's/^/    /' "$wt/.worker-blocked.md"; continue; fi
      if [ -n "$wt" ] && grep -qsF 'OpenRig MANAGED BLOCK' "$wt/CLAUDE.md" "$wt/AGENTS.md"; then
        seat_rig="$(cat "$out/workers/$i.seat" 2>/dev/null || true)"
        if [ -z "$seat_rig" ]; then echo "  #$i: a seat is still attached to $wt; dev-workspace remove-worker --rig <rig> --cwd $wt first"; continue; fi
        "${DEV_WORKSPACE:-$here/../../../bin/dev-workspace}" remove-worker --rig "$seat_rig" --cwd "$wt" >/dev/null ||
          { echo "  #$i: could not release its seat in $seat_rig; dev-workspace remove-worker --rig $seat_rig --cwd $wt"; continue; }
        echo "  #$i: released its seat in $seat_rig"
      fi
      if git -C "$dir" diff "$rig"..."$c" | grep -qE '^\+.*OpenRig MANAGED BLOCK|^\+\+\+ b/\.openrig/'; then echo "  #$i: $b commits OpenRig's managed context; fix the branch first"; continue; fi
      if [ -n "$wt" ] && [ -n "$(git -c safe.directory="$wt" -C "$wt" status --porcelain --untracked-files=no)" ]; then echo "  #$i: $wt has uncommitted changes; commit or discard them first"; continue; fi
      ahead="$(git -C "$dir" rev-list --count "$rig".."$c")"
      [ "$ahead" -gt 0 ] || { echo "  #$i: $b has no commits beyond $rig"; continue; }
      if git -C "$dir" diff --name-only --diff-filter=A "$rig"..."$c" | grep -qE '(^|/)\.worker-'; then echo "  #$i: $b commits a .worker-* file; fix the branch first"; continue; fi
      j="$(issue_json "$i" 2>/dev/null || echo '{}')"
      spec_task=0; jq -e 'any(.labels[]?; .name == "spec")' >/dev/null <<<"$j" && spec_task=1
      # Spec-direct mode (spec=domains, decisions=frozen on the repos.conf line): no task touches the
      # decision records or adds an amendment ledger; a build task moves only the markers it cites.
      if [ "$t_spec" = domains ] || [ "$t_decisions" = frozen ]; then
        if ! guard="$(jq -r '.body // ""' <<<"$j" | python3 -I "$here/spec-guard.py" "$dir" "$rig" "$c" "$t_spec" "$t_decisions" "$spec_task")"; then
          echo "  #$i: $b fails the specification guard:"; printf '%s\n' "$guard" | head -10 | sed 's/^/    /'; continue
        fi
      fi
      # The specification changes only through a spec task. A build branch may move the status
      # markers (trace comments) and lock lines it cites, and nothing else under these paths.
      if [ "$spec_task" = 0 ]; then
        spec_paths="docs/spec docs/decisions"; [ "$t_spec" = domains ] && spec_paths="docs/decisions"   # spec-guard.py checked docs/spec
        drift="$(git -C "$dir" diff -U0 "$rig"..."$c" -- $spec_paths docs/tasks | grep -E '^[+-]' | grep -vE '^(\+\+\+|---) ' |
          grep -vE '^[+-][[:space:]]*<!-- (id:|spec-lock).*-->[[:space:]]*$' || true)"
        if [ -n "$drift" ]; then
          echo "  #$i: $b changes the specification; only a spec task may, and this one is not labeled spec:"
          printf '%s\n' "$drift" | head -5 | sed 's/^/    /'; continue
        fi
      fi
      # Only the task's Scope: prefixes may change (SDD-SC-07); the spec paths are checked above.
      scope="$(jq -r '(.body // "") | capture("(?m)^Scope: *(?<s>[^\n]+)")? .s // ""' <<<"$j")"
      if [ -n "$scope" ]; then
        outside="$(git -C "$dir" diff --name-only "$rig"..."$c" | python3 -c '
import sys
prefixes = [p.strip() for p in sys.argv[1].split(",") if p.strip()]
for path in sys.stdin.read().split():
    if path.startswith(("docs/spec/", "docs/decisions/", "docs/tasks/")):
        continue
    if not any(path == p.rstrip("/") or path.startswith(p.rstrip("/") + "/") or path.startswith(p) for p in prefixes):
        print(path)' "$scope")"
        if [ -n "$outside" ]; then
          echo "  #$i: $b changes files outside its scope ($scope):"; printf '%s\n' "$outside" | head -10 | sed 's/^/    /'; continue
        fi
      fi
      if [ -n "$wt" ] && [ -f "$wt/.worker-pr.md" ]; then
        cp "$wt/.worker-pr.md" "$out/folded-$i.md"
      else
        echo "  #$i: no .worker-pr.md; the commit messages become its body"
        { echo "## What changed and why"; echo; git -C "$dir" log --format='%B' "$rig".."$c"; echo; echo "Closes #$i"; } > "$out/folded-$i.md"
      fi
      if ! git -C "$rwt" merge --squash -q "$c" >/dev/null 2>&1; then
        git -C "$rwt" reset -q --hard HEAD; rm -f "$out/folded-$i.md"
        echo "  #$i: $b conflicts with $rig; bring $rig into the worker's commits, or fold it by hand in $rwt (git merge --squash $c), then rerun fold $i"
        continue
      fi
      # A Markdown task file moves to docs/tasks/done/ in the same commit; a JSON task stays, and the
      # commit's `Closes: #N` trailer closes it (SDD-TK-05).
      if local_mode && ! side_mode && f="$(python3 "$here/loop-tasks.py" "$rwt" HEAD to-move "$i" 2>/dev/null)" && [ -n "$f" ]; then
        mkdir -p "$rwt/docs/tasks/done"; git -C "$rwt" mv "$f" "docs/tasks/done/$(basename "$f")"
      fi
      title="$(jq -r '.title // ""' <<<"$j")"; labels="$(jq -r '[.labels[]?.name]|join(",")' <<<"$j")"
      kind=fix; case ",$labels," in *",enhancement,"*|*",spec,"*) kind=feat ;; *",documentation,"*) kind=docs ;; esac
      msg="$(mktemp)"
      { printf '%s: %s (#%s)\n\n' "$kind" "${title:-task $i}" "$i"
        section "$out/folded-$i.md" "What changed and why" | sed '/./,$!d'
        printf '\nTask #%s: %s commit(s) from %s, folded as one.\n\nTask: #%s\nCloses: #%s\n' "$i" "$ahead" "$b" "$i" "$i"; } > "$msg"
      if ! git -C "$rwt" commit -q -F "$msg"; then
        git -C "$rwt" reset -q --hard HEAD; rm -f "$msg" "$out/folded-$i.md"
        echo "  #$i: $b adds nothing to $rig; not folded"; continue
      fi
      rm -f "$msg"
      sha="$(git -C "$rwt" rev-parse --short=10 HEAD)"
      printf '%s\t%s\t%s\t%s\n' "$i" "$b" "$sha" "$(date -u +%FT%TZ)" >> "$out/folded.tsv"
      if side_mode; then side_done "$i" || echo "  #$i: the task file in $t_side is not marked done; move it by hand"; fi
      if [ -n "$from" ]; then
        git -C "$dir" push -q origin --delete "$from" 2>/dev/null && echo "  #$i: deleted origin/$from" || echo "  #$i: origin/$from not deleted; delete it by hand"
      elif [ -n "$wt" ]; then
        release_slot "$wt"
        [ -z "$b" ] || is_slot "$wt" || git -C "$dir" branch -D "$b" >/dev/null 2>&1 || true
      elif git -C "$dir" show-ref -q --verify "refs/heads/$b"; then
        git -C "$dir" branch -D "$b" >/dev/null
      fi
      echo "  #$i: folded $b into $rig at $sha ($ahead commit(s) as one)"
    done
    ;;
  drop)
    [ $# -gt 0 ] || { echo "loop: drop needs issue numbers" >&2; exit 2; }
    dir="$(repo_dir)"
    for i in "$@"; do
      [[ "$i" =~ ^[0-9]+$ ]] || { echo "loop: invalid issue number" >&2; exit 2; }
      if worker_running "$i"; then echo "  #$i: worker still running; not dropped"; continue; fi
      if [ -f "$out/workers/$i.seat" ]; then echo "  #$i: a seat in $(cat "$out/workers/$i.seat") holds it; release the seat first"; continue; fi
      wt="$(worker_wt_of "$i")"; b=""
      [ -n "$wt" ] && is_slot "$wt" || b="$(worker_branch_of "$i")"
      [ -n "$wt$b" ] || { echo "  #$i: no worker"; continue; }
      [ -z "$wt" ] || release_slot "$wt"
      [ -z "$b" ] || git -C "$dir" branch -D "$b" >/dev/null
      echo "  #$i: dropped${b:+ $b} and its work${wt:+ in $(basename "$wt")}"
    done
    ;;
  close)
    need_rig >/dev/null; dir="$(repo_dir)"; rwt="$(rig_wt "$rig")"
    as="$rig"; title=""; push=0; ready=0; merge=0
    while [ $# -gt 0 ]; do
      case "$1" in
        --as) as="$2"; shift 2 ;; --title) title="$2"; shift 2 ;; --push) push=1; shift ;; --ready) ready=1; shift ;;
        --merge) merge=1; shift ;;
        *) echo "loop: unknown close option $1" >&2; exit 2 ;;
      esac
    done
    if local_mode && [ "$push$ready" != 00 ]; then echo "loop: $repo is local; close --merge merges $rig into $base_ref" >&2; exit 2; fi
    if ! local_mode && [ "$merge" = 1 ]; then echo "loop: $repo closes as a pull request; --merge is for local repositories" >&2; exit 2; fi
    [ "$ready" = 0 ] || owner_terminal
    [ "$push" = 0 ] || owner_terminal
    [ "$merge" = 0 ] || owner_terminal
    [ -f "$out/pushed-as" ] && as="$(cat "$out/pushed-as")"
    [[ "$as" =~ ^(feat|fix|refactor|docs|test|chore|build|ci|perf|revert)/[a-z0-9][a-z0-9._/-]*$ ]] && git check-ref-format "refs/heads/$as" >/dev/null || { echo "loop: --as must be a type/slug branch" >&2; exit 2; }
    [ -s "$out/folded.tsv" ] || { echo "loop: nothing folded into $rig yet" >&2; exit 3; }
    [ -d "$rwt" ] || { echo "loop: rig worktree $rwt is missing" >&2; exit 3; }
    [ -z "$(git -C "$rwt" status --porcelain --untracked-files=no)" ] || { echo "loop: the rig worktree has uncommitted changes" >&2; exit 3; }
    issues="$(folded_issues)"; n="$(wc -l <<<"$issues" | tr -d ' ')"
    list="$(sed 's/^/#/' <<<"$issues" | paste -sd, - | sed 's/,/, /g')"
    # The title comes from the rig branch: feat/snake-game becomes "feat: snake game (#1, #2)".
    [ -n "$title" ] || { subject="${rig#*/}"; title="${rig%%/*}: ${subject//-/ } ($list)"; }
    head_sha="$(git -C "$rwt" rev-parse --short=10 HEAD)"
    echo "checking $rig at $head_sha (repository check, once per tree) ..."
    if ! chk="$(cd "$rwt" && bash "$HOOKS/check-once.sh" 2>&1)"; then
      printf '%s\n' "$chk" | tail -30 >&2; echo "loop: the check failed on $rig; fix it in $rwt, then rerun close" >&2; exit 1
    fi
    draft="$(mktemp)"
    {
      echo "## What changed and why"; echo
      for i in $issues; do echo "### #$i"; echo; section "$out/folded-$i.md" "What changed and why"; echo; done
      echo "## Verification"; echo
      echo "Repository check on the pull request head $head_sha:"; echo; echo '```'; printf '%s\n' "$chk" | tail -12; echo '```'; echo
      echo "The integrated head passed the repository check shown above."; echo
      echo "## Deploy and provider impact"; echo
      dep=0
      for i in $issues; do
        s="$(section "$out/folded-$i.md" "Deploy and provider impact" | sed '/^[[:space:]]*$/d')"
        if [ -n "$s" ] && ! grep -qiE '^(none|no |n/a)' <<<"$s"; then dep=1; echo "- #$i: $(head -1 <<<"$s")"; sed '1d; s/^/  /' <<<"$s"; fi
      done
      [ "$dep" = 1 ] || echo "No additional deploy or provider impact declared; repository release rules still apply."
      echo; echo "## Review notes"; echo
      for i in $issues; do
        s="$(section "$out/folded-$i.md" "Review notes" | sed '/^[[:space:]]*$/d')"
        [ -n "$s" ] && { echo "- #$i: $(head -1 <<<"$s")"; sed '1d; s/^/  /' <<<"$s"; }
      done
      echo
      for i in $issues; do echo "Closes #$i"; done
    } > "$draft"
    # Ghost check: in a professional repository nothing on the ledger names a tool or a model.
    if [ "$personal" = 1 ]; then
      ghost="not applied (personal repository)"
    else
      hits="$( { for i in $issues; do grep -HniE "$ATTRIBUTION" "$out/folded-$i.md" || true; done
                 grep -niE "$ATTRIBUTION" "$draft" | sed "s#^#$out/pr.md:#" || true; } )"
      if [ -n "$hits" ]; then
        rm -f "$draft"
        echo "loop: ghost check failed: a professional repository's pull request names no tool or model. Remove these lines, then rerun close:" >&2
        sed 's/^/  /' <<<"$hits" >&2
        exit 1
      fi
      ghost="clean (no tool or model attribution in the folded bodies or pr.md)"
    fi
    mv "$draft" "$out/pr.md"
    echo "wrote $out/pr.md ($n issue(s): $list)"; echo "title: $title"; echo "ghost check: $ghost"
    if local_mode; then
      if [ "$merge" = 0 ]; then
        printf '\nNext, the owner in a terminal:\n  loop.sh close %s --merge\nwhich merges %s into %s in %s with pr.md as the merge message,\nmoves the folded task files to docs/tasks/done/, and removes the rig worktree and branch.\n' \
          "$repo" "$rig" "$base_ref" "$dir"
        exit 0
      fi
      [ "$(git -C "$dir" branch --show-current)" = "$base_ref" ] || { echo "loop: $dir must have $base_ref checked out to merge $rig into it" >&2; exit 3; }
      [ -z "$(git -C "$dir" status --porcelain --untracked-files=no)" ] || { echo "loop: $dir has uncommitted changes; commit or stash them first" >&2; exit 3; }
      if ! git -C "$dir" merge --no-ff -q -m "$title" -m "$(cat "$out/pr.md")" "$rig"; then
        git -C "$dir" merge --abort 2>/dev/null || true
        echo "loop: $rig does not merge cleanly into $base_ref; nothing changed" >&2; exit 3
      fi
      moved=""
      for i in $issues; do
        if side_mode; then side_done "$i" && moved="$moved #$i"; continue; fi
        f="$(python3 "$here/loop-tasks.py" "$dir" "$base_ref" to-move "$i" 2>/dev/null)" || continue
        [ -n "$f" ] || continue
        mkdir -p "$dir/docs/tasks/done"; git -C "$dir" mv "$f" "docs/tasks/done/$(basename "$f")"; moved="$moved #$i"
      done
      [ -z "$moved" ] || git -C "$dir" commit -q -m "chore(tasks): mark$moved done"
      echo "$base_ref at $(git -C "$dir" rev-parse --short=10 HEAD)" > "$out/merged"
      end_rig
      echo "merged $rig into $base_ref ($(cat "$out/merged")); tasks done:${moved:- none}; rig worktree and branch removed, steer pause"
      exit 0
    fi
    if [ "$push" = 0 ]; then
      cat <<EOF

Next, the owner in a terminal$( [ "$personal" = 1 ] && [ "$ready" = 0 ] && echo ', or the assistant (personal repository)'):
  loop.sh close $repo --as $as --push$( [ "$ready" = 1 ] && echo ' --ready')
which runs exactly:
  git -C $rwt push -u origin $rig:$as
  gh pr create --repo $repo --base "$base_ref" --head $as$( [ "$ready" = 1 ] || echo ' --draft') --title "$title" --body-file $out/pr.md
Running close --push again after more folds pushes the update to the same pull request and
rewrites its title and body from pr.md.
EOF
      exit 0
    fi
    owner_terminal
    git -C "$rwt" push -u origin "$rig:$as"
    if [ -f "$out/pr-url" ]; then
      # The pull request is the record: after more folds its title and body must name every issue.
      "$GHX" "$repo" pr edit "$(cat "$out/pr-url")" --title "$title" --body-file "$out/pr.md" >/dev/null
      echo "pushed $as; pull request $(cat "$out/pr-url") updated: title, body and head (CI runs once more)"
    else
      url="$(cd "$rwt" && "$GHX" "$repo" pr create --base "$base_ref" --head "$as" $( [ "$ready" = 1 ] || echo --draft ) --title "$title" --body-file "$out/pr.md")"
      echo "$url" > "$out/pr-url"; echo "$as" > "$out/pushed-as"
      echo "opened $url from $as"
    fi
    ;;
  land)
    # Land the goal as its tier says (SDD-SC-09). close writes pr.md and runs the check once.
    need_rig >/dev/null; dir="$(repo_dir)"; rwt="$(rig_wt "$rig")"
    case "$t_tier" in
      0) echo "loop: $repo is tier 0 (no git); nothing lands" >&2; exit 2 ;;
      1) ;;                       # solo trunk: the assistant lands it (decision 0001, point 1)
      *) owner_terminal ;;        # tiers 2 to 4: the owner, in a terminal
    esac
    if [ "$t_tier" = 3 ] && [ "$t_forge" = github ]; then
      exec bash "$here/loop.sh" close "$repo" --push "$@"   # one push and one draft pull request
    fi
    bash "$here/loop.sh" close "$repo" "$@" >/dev/null || exit $?
    subject="${rig#*/}"; issues="$(folded_issues)"
    list="$(sed 's/^/#/' <<<"$issues" | paste -sd, - | sed 's/,/, /g')"
    title="${rig%%/*}: ${subject//-/ } ($list)"
    if [ "$t_tier" = 3 ] || [ "$t_tier" = 4 ]; then
      # A bare company repository or a fork: one push of the goal branch; the merge is the owner's
      # (on the host for a bare repository). Never to upstream.
      git -C "$dir" remote get-url origin >/dev/null 2>&1 || { echo "loop: $repo has no origin to push to" >&2; exit 3; }
      git -C "$rwt" push -u origin "$rig:$rig"
      echo "$rig" > "$out/pushed-as"
      echo "pushed $rig to origin. Merge it into $base_ref on the server, then: git -C $dir fetch origin $base_ref:$base_ref && loop.sh finish $repo"
      exit 0
    fi
    # Tiers 1 and 2: land on the local base, a fast-forward when it can be one, then push it.
    where="$(git -C "$dir" worktree list --porcelain | awk -v b="refs/heads/$base_ref" '/^worktree /{p=substr($0,10)} $0=="branch " b {print p; exit}')"
    if [ -n "$where" ]; then
      [ -z "$(git -C "$where" status --porcelain --untracked-files=no)" ] || { echo "loop: $where has uncommitted changes; commit or stash them first" >&2; exit 3; }
      if git -C "$dir" merge-base --is-ancestor "$base_ref" "$rig"; then
        git -C "$where" merge -q --ff-only "$rig"
      elif ! git -C "$where" merge --no-ff -q -m "$title" -m "$(cat "$out/pr.md")" "$rig"; then
        git -C "$where" merge --abort 2>/dev/null || true
        echo "loop: $rig does not merge cleanly into $base_ref; nothing changed" >&2; exit 3
      fi
    elif git -C "$dir" merge-base --is-ancestor "$base_ref" "$rig"; then
      git -C "$dir" update-ref "refs/heads/$base_ref" "$(git -C "$dir" rev-parse "$rig")" "$(git -C "$dir" rev-parse "$base_ref")"
    else
      echo "loop: $base_ref moved since $rig was cut, and no worktree has $base_ref checked out; check out $base_ref, then rerun land" >&2; exit 3
    fi
    echo "$base_ref at $(git -C "$dir" rev-parse --short=10 "$base_ref")" > "$out/merged"
    pushed="no origin; local only"
    if git -C "$dir" remote get-url origin >/dev/null 2>&1; then
      # DEV_LOOP_LAND tells the pre-push hook that this is the land: a fast-forward of the base is permitted.
      if DEV_LOOP_LAND=1 git -C "$dir" push -q origin "$base_ref" 2>"$out/push.err"; then pushed="pushed to origin"
      else pushed="push FAILED ($(tail -1 "$out/push.err")); $base_ref is landed locally"; fi
    fi
    end_rig
    echo "landed $rig on $base_ref ($(cat "$out/merged")); $pushed; rig worktree and branch removed, steer pause"
    ;;
  finish)
    owner_terminal; need_rig >/dev/null; dir="$(repo_dir)"; rwt="$(rig_wt "$rig")"
    if local_mode; then  # the owner merged the rig branch by hand; close --merge already finishes
      git -C "$dir" merge-base --is-ancestor "$rig" "$base_ref" || { echo "loop: $rig is not merged into $base_ref; run loop.sh close $repo --merge" >&2; exit 3; }
      echo "$base_ref at $(git -C "$dir" rev-parse --short=10 "$base_ref")" > "$out/merged"
      end_rig; echo "rig branch $rig closed: already in $base_ref; its worktree and branch removed, steer pause"; exit 0
    fi
    pr="${1:?pull request number}"
    st="$(gh pr view "$pr" --repo "$repo" --json state,headRefName,baseRefName)"
    [ "$(jq -r .state <<<"$st")" = MERGED ] || { echo "loop: #$pr is not merged (state $(jq -r .state <<<"$st"))" >&2; exit 3; }
    [ "$(jq -r .baseRefName <<<"$st")" = "$base_ref" ] || { echo "loop: #$pr targets a different base" >&2; exit 3; }
    head_ref="$(jq -r .headRefName <<<"$st")"
    closed=0
    for i in $(folded_issues); do
      s="$(gh issue view "$i" --repo "$repo" --json state --jq .state 2>/dev/null || echo '?')"
      if [ "$s" = OPEN ]; then "$GHX" "$repo" issue close "$i" --comment "Merged in #$pr." >/dev/null && { echo "  closed #$i"; closed=$((closed+1)); }
      else echo "  #$i already $s"; fi
    done
    if git -C "$dir" push origin --delete "$head_ref" >/dev/null 2>&1; then echo "  deleted origin/$head_ref"; else echo "  origin/$head_ref already gone"; fi
    [ -d "$rwt" ] && git -C "$dir" worktree remove --force "$rwt"
    git -C "$dir" branch -D "$rig" >/dev/null 2>&1 || true
    git -C "$dir" fetch -q --prune origin
    mv "$ctl/rig-branch" "$out/rig-branch.closed"; echo "$pr" > "$out/pr-merged"; echo "$rig" > "$ctl/last-rig"; echo pause > "$ctl/steer"
    echo "rig branch $rig closed: #$pr merged, $closed issue(s) closed, $head_ref and the rig worktree removed, steer pause"
    ;;
  tidy)
    apply=0; [ "${1:-}" = --apply ] && apply=1
    [ "$apply" = 0 ] || owner_terminal
    dir="$(repo_dir)"
    # origin is read when the tasks are GitHub issues, and in local mode when origin is a real bare
    # repository (forge=bare, the Acme repositories on git-host): its merged branches go too.
    with_origin=0
    if ! local_mode; then with_origin=1
    elif [ "$t_forge" = bare ] && git -C "$dir" remote get-url origin >/dev/null 2>&1; then with_origin=1; fi
    [ "$with_origin" = 0 ] || git -C "$dir" fetch -q --prune origin
    live="$(live_worktrees)"
    open_heads=""
    local_mode || open_heads="$(gh pr list --repo "$repo" --state open --limit 100 --json headRefName --jq '.[].headRefName')"
    main_sha="$(git -C "$dir" rev-parse "$(base_tip)")"
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    # Never listed: the base, the open rig branch, open pull request heads, and the keep= trunks
    # (the host's pre-receive hook protects or checks them, so a delete is refused or harmful).
    protected() {
      case "$1" in develop|main|HEAD|"$rig"|"$base_ref") return 0 ;; esac
      case ",$t_keep," in *",$1,"*) return 0 ;; esac
      grep -qx "$1" <<<"$open_heads"
    }
    merged_or_pointer() { git -C "$dir" merge-base --is-ancestor "$1" "$(base_tip)" 2>/dev/null || [ "$(git -C "$dir" rev-parse "$1" 2>/dev/null)" = "$main_sha" ]; }
    echo "TIDY $today $repo"
    echo "remote branches merged into origin/$base_ref:"
    if [ "$with_origin" = 1 ] && ! git -C "$dir" rev-parse -q --verify "refs/remotes/origin/$base_ref" >/dev/null; then
      echo "  (origin has no $base_ref; remote branches not read)"; with_origin=0
    fi
    # lstrip gives the branch name itself; origin/HEAD would abbreviate to plain "origin".
    [ "$with_origin" = 0 ] || for b in $(git -C "$dir" for-each-ref --format='%(refname:lstrip=3)' refs/remotes/origin); do
      protected "$b" && continue
      git -C "$dir" merge-base --is-ancestor "origin/$b" "origin/$base_ref" && { echo "  $b"; echo "$b" >> "$tmp/remote"; }
    done; [ -f "$tmp/remote" ] || echo "  none"
    echo "worktrees that are clean, have no live session, and whose branch is merged or a pointer to main:"
    git -C "$dir" worktree list --porcelain | awk '/^worktree /{p=$2} /^branch /{sub("refs/heads/","",$2); print p, $2} /^detached$/{print p, "(detached)"}' > "$tmp/wts"
    while read -r p b; do
      [ "$p" = "$dir" ] && continue
      case "$p" in */rig-*|*/slot-[0-9]*|*/forge-check) continue ;; esac  # the rig worktree, the worker slots and the check folder of a forge stay
      grep -qx "$p" <<<"$live" && continue
      [ -z "$(git -C "$p" status --porcelain 2>/dev/null)" ] || continue
      if [ "$b" = "(detached)" ] || merged_or_pointer "$b"; then echo "  $p ($b)"; echo "$p" >> "$tmp/wt"; fi
    done < "$tmp/wts"; [ -f "$tmp/wt" ] || echo "  none"
    echo "local branches merged into origin/$base_ref or pointing at main (not checked out elsewhere):"
    for b in $(git -C "$dir" for-each-ref --format='%(refname:short)' refs/heads); do
      protected "$b" && continue
      p="$(awk -v b="$b" '$2==b {print $1}' "$tmp/wts")"
      if [ -n "$p" ] && ! grep -qx "$p" "$tmp/wt" 2>/dev/null; then continue; fi
      merged_or_pointer "$b" && { echo "  $b"; echo "$b" >> "$tmp/local"; }
    done; [ -f "$tmp/local" ] || echo "  none"
    [ "$apply" = 1 ] || { echo; echo "read-only. Apply in a terminal with: loop.sh tidy $repo --apply (bundles first)"; exit 0; }
    arch="$ctl/tidy-$today"; mkdir -p "$arch"
    refs="$( { cat "$tmp/local" 2>/dev/null || true; sed 's#^#origin/#' "$tmp/remote" 2>/dev/null || true; } | tr '\n' ' ')"
    if [ -n "${refs// /}" ]; then
      # shellcheck disable=SC2086
      git -C "$dir" bundle create "$arch/deleted-branches.bundle" $refs >/dev/null 2>&1
      git -C "$dir" bundle verify "$arch/deleted-branches.bundle" >/dev/null 2>&1 || { echo "loop: bundle verification failed; nothing deleted" >&2; exit 1; }
      { cat "$tmp/local" 2>/dev/null || true; sed 's#^#origin/#' "$tmp/remote" 2>/dev/null || true; } > "$arch/deleted-branches.txt"
      echo "bundled $(wc -l < "$arch/deleted-branches.txt" | tr -d ' ') ref(s) to $arch/deleted-branches.bundle (restore: git fetch <bundle> <branch>:<branch>)"
    fi
    for b in $(cat "$tmp/remote" 2>/dev/null); do git -C "$dir" push origin --delete "$b" >/dev/null 2>&1 && echo "  deleted origin/$b" || echo "  FAILED origin/$b"; done
    for p in $(cat "$tmp/wt" 2>/dev/null); do git -C "$dir" worktree remove "$p" >/dev/null 2>&1 && echo "  removed $p" || echo "  FAILED $p"; done
    git -C "$dir" worktree prune
    for b in $(cat "$tmp/local" 2>/dev/null); do git -C "$dir" branch -D "$b" >/dev/null 2>&1 && echo "  deleted $b" || echo "  FAILED $b"; done
    [ "$with_origin" = 0 ] || git -C "$dir" fetch -q --prune origin
    echo "result: local $(git -C "$dir" for-each-ref refs/heads | wc -l | tr -d ' '), remote $(git -C "$dir" for-each-ref refs/remotes/origin | grep -vc 'origin/HEAD'), worktrees $(git -C "$dir" worktree list | wc -l | tr -d ' ')"
    ;;
  tasks)
    local_mode || { echo "loop: $repo keeps its tasks as GitHub issues; tasks is for local repositories" >&2; exit 2; }
    # Write where the command runs when that is a worktree of this repository (an intake branch).
    dir="$(repo_dir)"; here_top="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -n "$here_top" ] && [ "$(repository_identity "$here_top")" = "$(repository_identity "$dir")" ]; then dir="$here_top"; fi
    tref="$base_ref"
    if side_mode; then dir="$t_side"; tref=HEAD; fi   # a ghost project: the task files of the side folder
    sub="${1:-list}"; [ $# -eq 0 ] || shift
    case "$sub" in
      list) listed="$(python3 "$here/loop-tasks.py" "$dir" "$tref" issues)"
            jq -r '.[] | "#\(.number) \(if any(.labels[]; .name == "sprint-ready") then "ready" elif .waits then "waits (\(.waits))" elif any(.labels[]; .name == "not-for-workers") then "person" else "draft" end) \(.title)"' <<<"$listed" ;;
      next|check) python3 "$here/loop-tasks.py" "$dir" "$tref" "$sub" "$@" ;;
      new) LOOP_TASKS="$t_tasks" python3 "$here/loop-tasks.py" "$dir" "$tref" new "$@" ;;   # tasks=json writes <N>.json
      view) python3 "$here/loop-tasks.py" "$dir" "$tref" html ;;   # plain HTML on stdout (SDD-TK-08)
      *) echo "loop: tasks list|next|new|check|view" >&2; exit 2 ;;
    esac
    ;;
  *) echo "unknown verb $verb" >&2; exit 2 ;;
esac
