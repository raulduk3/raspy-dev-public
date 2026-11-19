---
name: loop
description: >-
  Work toward a goal on one branch with a team of workers: cut the goal's branch, give each
  ready task a worker in a detached slot, fold each finished task into the goal branch as one
  squash commit, and land the goal as the repository's tier says. Also lists and writes local
  task files. Use for "run the loop", "start the team", "dispatch workers", "fold", "land it".
---

# loop

One goal is one branch and one logical change. The repository's tier in `repos.conf`
(`dev-loop tier <path>`) sets how the goal lands. See `docs/source-control.md`.

1. **The goal gets a branch.** `dev-loop start <owner/repo> <type/slug>` cuts an ordinary branch
   from the base, for example `feat/snake-game`. This is the rig branch. Its worktree is
   `.claude/worktrees/rig-<type>-<slug>` in the checkout.
2. **Each task gets a slot, not a branch.** `dev-loop go` gives every ready task a worker (headless,
   or an OpenRig seat) in a free slot: `.claude/worktrees/slot-1` to `slot-S`, detached at the rig
   branch. S is `slots=` in `repos.conf` (default 2). A slot stays on disk and the next task reuses
   it. A large repository (`large=1`) gets a sparse cone from the task scope.
3. **Finished tasks fold as one commit.** `dev-loop fold <owner/repo> N` squashes the worker's
   commits into one commit on the rig branch and moves the task file to `docs/tasks/done/` in that
   commit. It releases the worker's seat and the slot. It refuses a running or blocked worker, a
   dirty slot, files outside the task scope, a change to the specification by a task without the
   `spec` label, `.worker-*` files, OpenRig's managed context, and a conflict. It does not run the
   full check: the worker ran it, and `close` or `land` runs it once. `fold N --from <branch>`
   takes a cloud agent's branch (tier 2 or 3 GitHub repositories) and then deletes that branch.
4. **The goal lands once.** `dev-loop land <owner/repo>` follows the tier:
   - tier 1: the assistant fast-forwards the base and pushes it;
   - tier 2: the owner, in a terminal; a fast-forward when it can be one, then a push;
   - tier 3: the owner; one draft pull request (GitHub) or one push of the goal branch (bare repository);
   - tier 4: the owner; one push of the goal branch to `origin`, never to `upstream`.
   `close` still writes `pr.md` with one `Closes #N` per folded task; `close --merge` and
   `close --push` stay for the owner.

When every worker is folded, the control seat tells the owner once: which tasks folded into
the rig branch, where to read the diff (`git diff <base>...<rig branch>`), and the one command.

## Who runs what

| Verb | Who |
| --- | --- |
| `status`, `state` (the same facts as JSON), `plan`, `tasks` | anyone |
| `start`, `go`, `resume`, `pause`, `collect`, `fold` | a session or control seat on the owner's word |
| `land` at tier 1 | the assistant |
| `land` at tiers 2 to 4, `close --merge`, `close --push` (professional), `finish`, `tidy --apply` | the owner, in a terminal; an agent is refused (the daily tidy timer runs `tidy --apply`) |
| `close --push` without `--ready` in a personal repository | the assistant may run it |

The header of `dev-loop` (the script) is the full verb table; this table follows it. Every lever
is also in the `ai` menu under a project's Development loop: the goal branch, each worker
branch under it (diff, report, open or release its seat, resume, merge up), dispatch, landing,
tasks and tidy. The menu is the owner's terminal, so it runs the owner verbs after asking.

## Setup, once per machine

`~/.config/dev-platform/repos.conf`: one line per repository, `owner/repo checkout-path
local|owner|bot [base-branch]`, separated by spaces or tabs. `new-repo --register` writes it.
`local` never touches GitHub. `owner` makes the two GitHub writes (`pr create` at close, `issue
close` at finish) with the owner's own `gh` login; `bot` uses the machine user's token.
`~/.config/dev-platform/brief.conf` sets `LOOP_STATE_DIR` (default
`~/.local/state/dev-platform/loop`). A project is named the same everywhere: `dev-loop` takes
`owner/repo`; `ai-work loop` takes `owner/repo`, the project id, or the checkout path.

## Local and GitHub, one motion

The steps above are the same for both. The differences:

- Tasks: `docs/tasks/<N>-<slug>.md` files on the base (local), or GitHub issues labeled
  `sprint-ready` (GitHub). `dev-loop tasks <repo> [list|next|new|check]` writes and checks local
  task files; the `intake` skill decides what they are.
- `start` fetches the base first only for GitHub.
- Landing: `close --merge` merges locally and moves the folded task files to `docs/tasks/done/`;
  `close --push` opens the pull request, and after the owner merges it on GitHub,
  `finish <owner/repo> <pr>` closes the folded issues and removes the rig branch.
- A professional repository gets the ghost check before anything reaches GitHub.

## Task conventions

A repository with `tasks=json` on its `repos.conf` line keeps each task as `docs/tasks/<N>.json`,
checked against the platform schema `schemas/task/v1.schema.json` (decision 0002). The loop reads
both formats in one shape. A JSON task has no done field: fold ends its squash commit with the
trailers `Task: #<N>` and `Closes: #<N>`; `Closes` closes it, and the file stays. Only a ready code or spec task whose
assignee is not a person goes to a worker. `dev-loop tasks <repo> view` prints the open tasks as
an HTML table with no styles.

Every task carries `Scope: <comma-separated path prefixes>` and `Depends on: #N, #M` or `Depends
on: none`. Only ready tasks with both lines are selected. Scopes must be pairwise prefix-disjoint
within one dispatch; dependencies must be done, or already folded into the rig branch.

The specification changes only through a spec task (`Labels: spec`). A build task may move the
status marker of the items it cites and any lock line, and nothing else under `docs/spec/`,
`docs/decisions/` or `docs/tasks/`; fold refuses the branch and shows the lines otherwise. A
worker that finds the spec wrong writes `.worker-blocked.md`, and the fix becomes a spec task.

### Spec-direct mode

A `repos.conf` line can carry `spec=domains` and `decisions=frozen` (`dev-loop tier <path>`
prints both). Then the fold runs `scripts/spec-guard.py` on each branch:

- `decisions=frozen`: every task is refused, a spec task too, when it adds, changes or deletes a
  file under `docs/decisions/` or adds a `SPEC-AMENDMENTS.md`. The global git pre-commit hook
  (`hooks/git/pre-commit`) refuses the same commit for every agent and every terminal.
- `spec=domains`: a `kind: spec` task may edit `docs/spec/<domain>/` freely. A code task may change
  only the `status:`, `tests:` and `code:` lines of the items it cites (`SDD-…` or `TDD-…` IDs in
  its refs or brief), and the regenerated `docs/spec/index.json`. Any other line under
  `docs/spec/` is refused.
- A decision that a task cites gates nothing: it is history. A task with a label in
  `LOOP_GOVERNED_LABELS` waits until the owner removes the label or gives it to a person.
- The worker brief tells the worker the same rules and points to the repository's `AGENTS.md`.

## Goal forge

For a goal with many tasks, run the loop through `dev-forge` (`docs/forge.md`). A rig folder holds one
profile, `forge.json`. `dev-forge loop -- <dev-loop arguments>` is the door: it gives the loop the
worker limit and the short proof of the profile. Then:

- a worker runs only the short proof and posts `READY #N` (`dev-forge post orchestrator <name>`);
- `dev-forge ready` lists the tasks that no running task holds by a shared scope path;
- `dev-forge batch N ...` stacks the results, runs the full check one time and folds the good tasks;
  a failed batch folds the tasks before the first bad task and posts the failure.

A profile with no full check folds nothing. Heavy commands go through `dev-forge run heavy`.

## Workers

A worker has one task and one slot, and no branch. It commits, runs `hooks/check-once.sh` (which
records the passing tree), writes `.worker-pr.md` with the four template sections and `Closes
#N`, and stops. It never pushes, opens a pull request or comments. A worker that finds the fix
outside its scope, or the task already done, writes `.worker-blocked.md` and stops.

With `LOOP_SEAT_RIG=<running rig>`, dispatch gives each task an interactive seat in that rig's
`workers` pod (`dev-workspace add-worker`; `LOOP_SEAT_RUNTIME` claude, codex or pi; a Codex seat takes
`LOOP_SEAT_ACCOUNT` or its native home) and records the rig, so fold can release the seat.

With `LOOP_RUNTIME=pi`, a headless worker is one Pi run on the OpenRouter key instead of Claude
Code: the key comes from the environment by name (the API rig's unit holds it; dispatch refuses
without it), the model is the model file's line for the task resolved for openrouter, and the
platform guard, the advice tool and the turn and billed-token caps (`LOOP_WORKER_TOKEN_LIMIT`)
load as Pi extensions. `api-rig` sets this; see `docs/api-rig.md`. A
blocked worker is never folded, so its seat stays until the owner or control seat releases it with
`dev-workspace remove-worker --rig <rig> --cwd <worktree>`. See `docs/rig-working-branches.md`.

## Other verbs

- `dev-loop status <owner/repo>`: steer, the rig branch, running workers, worker branches and their
  state, folded tasks, the pull request; with none open, the last rig branch that landed.
- `dev-loop collect <owner/repo>`: the CYCLE report, with seat workers counted.
- `dev-loop tick <owner/repo>` does what `go` does from a schedule, only when the steer says `go`.
  The steer is the gate: first word `go` or `pause`; a missing file means pause. Landing writes
  `pause`.
- `dev-loop tidy <owner/repo>`: read-only list of merged branches and clean, unused worktrees;
  `--apply` bundles every ref first, then deletes. It never lists the base or a trunk in the
  `keep=a,b` field of the `repos.conf` line. Put each trunk that the host protects or checks there.
  A local repository with `forge=bare` has a real origin: tidy also lists the origin branches that
  are merged into the base, and `--apply` bundles them, then deletes them on origin.

Writes to GitHub go through `scripts/ghx <owner/repo> <gh args>`, which picks the identity from
`repos.conf` and refuses merge, ready and review on every repository.

## Base and limits

The fourth `repos.conf` column pins the base. Without it, a personal repository uses its remote
default branch; a professional repository uses `develop`. An open rig branch keeps its recorded
base. One rig branch is open per repository at a time. `LOOP_WORKER_MAX_TURNS`,
`LOOP_WORKER_MAX_SECONDS` and `LOOP_WORKER_TOKEN_CEILING` bound workers; the token ceiling is a
prompt budget, not a spending cap. A quota failure stops the lane rather than switching accounts.
`LOOP_MODEL` may name a model, a tier slug (`implementation-high`) or a role. Worker models come from `bin/pstack-model`, which reads `/etc/dev-platform/pstack-models.md` (a user's `~/.config/dev-platform/pstack-models.md` overrides single lines)
when `/setup-pstack` wrote it and its own tier defaults otherwise (see `MODELS.md`).
