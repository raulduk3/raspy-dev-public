# Rigs on working branches

The rig setup this builds on is in `integrations/openrig/README.md`.

Every worker seat works in its own Git worktree, on the branch the loop cut for its
issue. Seats join from a control rig that the owner starts once per engagement. This
reuses the loop skill's branch contract; it does not add a second one.

## The shape

| Seat | Runtime and account | Working directory | Branch |
| --- | --- | --- | --- |
| Control (`control.lead`) | Claude Code, native default home | an engagement folder outside the repository | none |
| Overseer (`review.overseer`) | Codex, native default home | the same engagement folder | none; reads with `git -C` |
| Worker (`workers.issue-N`) | Claude Code or Codex, any verified account | the loop's worktree for issue N | `type/slug-N`, cut from the goal's rig branch |

Control and overseer stay out of the repository on purpose. OpenRig writes guidance
blocks into the folder's `CLAUDE.md` or `AGENTS.md`. Repositories track those files, so
a seat in the rig worktree would keep it modified, and the loop folds only into a clean
rig worktree. Workers do sit in worktrees, one seat each; fold releases the seat.

The control seat directs the loop on the owner's word, using the pstack-informed
practice in its guidance. The overseer reads worker diffs, each `.worker-pr.md` and the
recorded check, and reports. It never edits, folds, pushes or answers a worker's prompt.
Putting it on the other provider gives an independent reading and keeps one provider's
quota from gating both writing and review.

## Using it

The easy way is the `ai` menu: pick a project, then "This project's team". It names the
team `helm-<project>` and makes its engagement folder for you, so every project gets its
own team. The commands below are what it runs. Without `--rig`, `start helm` makes a
single rig called `development-helm`.

Start the control rig from an empty engagement folder. `start` refuses a folder inside a
Git checkout.

```bash
mkdir -p ~/Dev/engagements/<repo> && dev-workspace start helm --cwd ~/Dev/engagements/<repo>
```

Let the loop give each dispatched issue a seat instead of a headless worker. The loop
still cuts the worktree and writes `.worker-brief.md`. `LOOP_SEAT_RUNTIME` picks `claude`
(the default) or `codex`. A Claude seat uses the loop's selected account. A Codex seat uses
`LOOP_SEAT_ACCOUNT`, or its native home when that is unset, because the loop's own account
selection accepts only Claude accounts.

```bash
LOOP_SEAT_RIG=development-helm dev-loop go <owner/repo>
```

A worktree the loop already cut can take a seat directly:

```bash
dev-workspace add-worker claude --rig development-helm --cwd <worktree> --account anthropic-apple
```

The worker waits until told to start, then follows its brief and stops after writing
`.worker-pr.md`. To fold it, remove its seat first; this restores the worktree's tracked
guidance files. Fold refuses while a seat's block is still there, and refuses a branch
that commits OpenRig's blocks or `.openrig/`.

```bash
dev-workspace remove-worker --rig development-helm --cwd <worktree>
```

## What the pieces are

- `integrations/openrig/helm.yaml`: the template. Pods `control`, `review` and an empty
  `workers` pod that seats join.
- `integrations/openrig/agents/overseer` and `agents/worker`: their guidance, beside the
  existing silent `control` agent.
- `bin/dev-workspace add-worker` and `remove-worker`. Add resolves the account through the
  account service, writes a member fragment to `~/.local/state/dev-platform/openrig/`,
  excludes `.openrig/` in the repository, and calls `rig add`. The client gives up after
  five seconds while the daemon finishes, so the result is read back from the rig, never
  retried blind. Remove calls `rig remove`, then strips the blocks with the same rule as
  OpenRig's own teardown, which `rig remove` does not run.
- `skills/loop/scripts/loop.sh`: the `LOOP_SEAT_RIG` branch in worker launch and the two
  fold refusals.

## Limits

- Professional repositories stay refused, for workers as for any seat. OpenRig's blocks in
  a tracked `CLAUDE.md` or `AGENTS.md` would be one careless `git add` from a commit.
- Control and overseer run on the native default homes. Pinning them per account needs a
  two-member renderer that does not exist yet; workers are already pinnable.
- The loop does not see seats as running workers. `status` and `collect` count only
  headless workers, so a CYCLE report undercounts, and the cap ignores seats. The plan's
  local cap still bounds how many issues one `go` dispatches. Fold's only sign of a live
  seat is its guidance block in the worktree.
- Every seat starts by asking permission to run `rig whoami`, from OpenRig's boot hint.
  That prompt is the owner's to answer.

Proven 2026-09-24 on a scratch personal repository: the rig started with its three pods,
a worker seat joined on the Apple Anthropic home, and after `remove-worker` the worktree's
status was empty. The loop's seat dispatch is covered by tests through `resume`, not yet by
a live `dev-loop go` against real issues.
