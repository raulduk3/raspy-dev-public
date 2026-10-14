---
name: loop
description: >-
  Work toward a goal on one branch with workers: cut the goal branch, give each ready task its own
  branch and worktree, merge each finished task up once its check passes, and hand a person one
  pull request (or one merge) to land. Also lists and writes task files. Use for "run the loop",
  "start the goal", "dispatch the tasks", "merge it up", "land it".
---

# loop

A branch is the unit of work; a worktree is where it happens. The `loop` command does the git
work; this skill says when to run each step and what to check.

## The motion

1. **The goal gets a branch.** `loop start feat/snake-game` cuts it from `main` into
   `worktrees/feat-snake-game`. One goal is open per repository.
2. **Each ready task gets a branch.** `loop go` takes every task in `docs/tasks/` that is
   `Status: ready`, whose dependencies are merged up or done, and gives it a branch cut from the
   goal branch, in `worktrees/task-N`. Scopes of tasks that run together must not overlap; check
   with `loop tasks check` and fix the task files first.
3. **A worker does one task.** It reads `AGENTS.md`, its task file and the specification sections
   it cites, changes only its `Scope:`, commits, runs the check, and writes `.worker-done.md`
   (or `.worker-blocked.md` with the reason). It never pushes or merges. With `LOOP_AGENT` set,
   `loop go` starts a headless worker; otherwise each worktree has `.worker-task.md` for a person,
   an editor or a team seat to pick up.
4. **Review, then merge up.** Read the worker's diff (`git -C worktrees/task-N diff <goal>...`)
   and `.worker-done.md`. Use `interrogate` or `blast-radius` when the change is risky.
   `loop fold N` runs the repository's check on the branch and merges it into the goal branch; it
   refuses a running, blocked or dirty worker and a conflict.
5. **A person lands it.** `loop land` marks the merged tasks done, then pushes the goal branch and
   opens one pull request (GitHub) or prints the one merge command (local). The person reviews
   and merges. After that, `loop finish` removes the goal's worktree.

`loop status` shows the goal, each worker (running, working, done, blocked) and what is merged up.

## Tasks

`loop tasks list | next | check` and
`loop tasks new "<title>" --scope src/a/,src/b/ [--depends "#1, #2"] [--label spec]`.
The `intake` skill decides what the tasks are; `docs/tasks/README.md` in the repository is the
format. A build task changes nothing under `docs/spec/` or `docs/decisions/` beyond the status of
the items it cites. A worker that finds the specification wrong writes `.worker-blocked.md`, and
the fix becomes a task labeled `spec`.

## Rules

- Never merge into `main`, push `main`, approve, or rewrite history; the guard and the git hooks
  refuse it anyway.
- A blocked worker is never merged up. Read its reason, fix the task or the specification, and
  start it again with `loop go N` after removing its worktree.
- Pick each worker's model by tier from `models.md`: tasks are usually `implementation`; review
  is `judgment`.
