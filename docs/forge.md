# Goal forge

One goal is one forge. Many workers commit, each in its own slot. One orchestrator checks a batch of results with one full check and folds it. The command is `dev-forge` (`lib/ai_ecosystem/forge.py`). The requirements are SDD-SC-08, SDD-SC-22 to SDD-SC-27 and SDD-LP-25 to SDD-LP-44.

## Why it is fast

| Mechanism | Tool |
| --- | --- |
| A worker writes code and tests and runs only a short proof. It runs no build and no full check. | `dev-forge brief`, `dev-forge loop` |
| A worker has a new context for each task. The slot keeps the warm build. | The loop's slots |
| Reports go up as small files. A background wait wakes the reader. | `dev-forge post`, `wait`, `stale` |
| One full check for a batch of tasks, in one warm check folder. | `dev-forge batch` |
| A task starts only when no running task shares a scope path with it. | `dev-forge ready` |
| Heavy checks and short proofs take places of the machine, in one fair line. | `dev-forge run light|heavy` |

For 24 tasks in batches of 6, the full check runs 4 times and not 25 times. One failed batch adds about 3 runs.

## The rig folder and the profile

A rig folder (`~/dev/rigs/<rig>`) holds `forge.json`, `culture.md`, `rig.yaml`, the inbox, the failure logs and the batch ledger. It is a Git repository of its own. The repository of the project gets no file of the forge.

`dev-forge init <repo>` proposes the profile from the files of the checkout. Read each value. Then `dev-forge init <repo> --rig <folder> --write` makes the rig folder.

```json
{
  "schema": "dev-platform.forge@1",
  "kind": "forge",
  "project": "name-of-the-project-record",
  "commands": {
    "install": "bun install --frozen-lockfile",
    "cheap": "bun run typecheck",
    "proof": "bun test {tests}",
    "affected": "scripts/affected-tests",
    "full": "bun run check"
  },
  "places": {"light": 3, "heavy": 1, "mem_min_mb": 3000, "load_max": null},
  "batch": {"max_tasks": 6},
  "wide": ["packages/contracts/src"],
  "workers": {"limit": null, "runtime": "claude", "rig": null, "seat_runtime": "claude", "model": null, "rules": ["..."]}
}
```

- `forge.json` is the one profile of a rig. `rig.yaml` is only the file that OpenRig reads.
- `project` names the project record (`dev-project show <name>`). The record gives the repository, the worker slots and the check command. `workers.limit: null` takes the slots of the record, and `commands.full: null` takes its check command. A value that the profile states wins. Where a project has more than one repository, `repository` names one. `repo: "owner/name"` is the older way, for a repository with no record.
- `kind` says how a worker starts: `forge` (a headless run), `openrig` (a seat), `harness` (an agent in a session) or `api` (Pi on the OpenRouter key). It gives `workers.runtime` where the profile states none.
- `commands.affected` can be an existing tool: `vitest --changed`, `jest --findRelatedTests`, pytest-testmon, `nx affected`.
- `wide` lists the registry files that many tasks touch. They do not hold a task.
- `places` are for the whole machine (`~/.local/state/dev-platform/forge/places`), so two rigs stand in one line.
- The profile has no build command, no batch wait time and no review kinds. A profile that holds `commands.build`, `batch.max_wait_s` or `review_kinds` is refused with the name of the field: delete that field.

## One goal

1. `dev-forge loop -- start <type/slug>` makes the goal branch.
2. `dev-forge ready` lists the ready tasks: FREE, IN WORK, or held by a running task.
3. `dev-forge loop -- go only <N> ...` gives each task a slot and a brief. The brief names the short proof and forbids the full check.
4. A worker commits in its slot and posts `READY #<N>` to the orchestrator. The orchestrator waits with `dev-forge wait orchestrator` as a background command.
5. `dev-forge batch <N> ...` stacks the results on the goal tip in the check folder (`.claude/worktrees/forge-check`), runs the install command and the full check one time, and folds the tasks.
6. When the check fails, the batch searches the first bad task in halves. It folds the tasks before it, posts the failure with the log to the orchestrator, and leaves the later tasks for the next batch.
7. `dev-loop land` lands the goal as the tier says. The check folder and the stop hook marker go away with the goal.

## Runtimes

The rig is files, git and shell commands. A runtime gives only the start of a one-task worker.

| `workers.runtime` | The worker | Use |
| --- | --- | --- |
| `claude` | One headless Claude Code run for each task | Claude Code CLI |
| `seat` | One seat in the OpenRig rig `workers.rig`, of the runtime `workers.seat_runtime` (claude, codex or pi) | OpenRig |
| `hand` | The loop makes the slot and the brief and starts nothing | An in-session agent of a Claude Code orchestrator, or `codex exec "$(cat .worker-brief.md)"` in the slot |
| `pi` | One headless Pi run on the OpenRouter key | A caller that has the key in its environment |

A worker context lives for one task. The seat and the slot live for the goal. The orchestrator is the one long context: it writes its state to files and hands over when its context is over half (OpenRig: the seat handover; Claude Code: a clear and one message).

## What the forge does with a repository that has less

| The repository has | The forge does |
| --- | --- |
| No full check | It stacks the batch and folds nothing. No check, no automatic fold. |
| No command for affected tests | A worker runs the tests that its task names. Use a smaller batch. |
| A task with no scope | The task runs alone. |
| A GitHub tracker | Not supported: `ready`, `brief` and `batch` read task files only. |

## Limits

- A slot stays with its task until the batch folds. Give the repository more slots than the worker limit (`slots=` in `repos.conf`).
- One open goal for each repository. One goal across two repositories is two forges.
