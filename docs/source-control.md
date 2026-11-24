# Source control

Each repository has one tier in `~/.config/dev-platform/repos.conf`. The tier sets the refs, the checkouts, the landing and the forge use for every agent and every interface.

Find the tier: `dev-loop tier <path>`. An unregistered repository follows tier 3.

## Tiers

| Tier | Kind | Refs | Landing |
| --- | --- | --- | --- |
| 0 | No git | None | None |
| 1 | Solo trunk | None. Work on `main`. | An agent can fast-forward and push `main`. |
| 2 | Personal shared | One goal branch | The owner lands it with `dev-loop land`. |
| 3 | Protected company | One goal branch | One push, then one draft PR, or one push to a bare repository. The owner merges. |
| 4 | Fork | One `local/*` patch branch | Never push upstream. |

Tiers 1 and 2 use `main` and release tags. They have no `develop` branch. Acme remotes are bare repositories on git-host: `ssh://git-host/srv/git/<repo>.git`.

## One goal

1. `dev-loop start <repo> <type/slug>` makes the goal branch (none at tier 1). The spec change is the first commit.
2. `dev-loop go <repo>` gives each ready task to a worker in a detached slot. A slot has no branch.
3. Each worker commits small and often, runs the full check once, and reports.
4. `dev-loop fold <repo> <N>` adds one squash commit for the task to the goal branch.
5. `dev-loop land <repo>` lands the goal. The owner runs it. The full check runs once at the land.
6. `dev-loop tidy <repo>` removes merged refs and old worktrees. A daily timer also runs it. Tidy never removes the base or a trunk in the `keep=` field of the `repos.conf` line. Put each trunk that the host protects or checks in `keep=`, for example `keep=feat/example`.

A goal can run as a forge: workers run a short proof, and one orchestrator runs the full check one time for each batch of results, then folds the batch (`dev-forge`, `docs/forge.md`).

Readers (reviewer, overseer, control seat) get no checkout. They read with `git show`, `git diff` and `git grep`.

## Rules for every agent

The develop skill lists rules R1 to R11. In short: find the tier first, make the fewest refs, never amend, rebase or force-push, write commit, PR and issue text in ASD-STE100, and use the forge only when the tier requires it.

A desktop session uses a `wip/*` branch. Never push it. Rename it to `type/slug` before a push.

## Decision records and spec-direct mode

Two fields on a `repos.conf` line set how agents change the specification:

- `spec=domains`: the specification is `docs/spec/<domain>/sdd.md` and `tdd.md`, found through `docs/spec/index.json`. The default `spec=single` is `docs/spec/SDD.md` and `TDD.md`.
- `decisions=none` (the default of a registered line): the repository keeps no decision record and no amendment ledger. The specification is the one record of a requirement. Intake asks the owner each open question in the conversation and changes the specification after the owner accepts the change. Git records the change, and the commit message gives the reason. The git pre-commit hook and `dev-loop fold` refuse a new or changed file under `docs/decisions/` and a new `SPEC-AMENDMENTS.md`. Files that are there are history; a commit can delete them.
- `decisions=frozen`: as `none`, but no commit deletes a decision file, and intake changes no specification. Distill still writes candidates. The owner takes a candidate in by hand, or an agent uses the `dev-spec` write commands where the project has a specification tree.
- `decisions=open`: the repository keeps decision records, and intake drafts them. Set it only for a repository whose own rules need the records.
- A path that no line names has `decisions=open`: the platform sets no rule for the decision files of a repository that it does not know.

The `intake`, `distill`, `spec-lint` and `loop` skills read both fields. The repository's `AGENTS.md` gives its own steps and checks; the platform does not copy them.

## Incoming candidates

Distill writes candidates to one HTML file for each repository. Git never tracks it, so it makes no commit and no branch. The `incoming=` field of the `repos.conf` line sets the place, and `dev-loop tier <path>` prints it as `incoming_file`:

- `incoming=state` (the default): `~/.local/state/dev-platform/incoming/<repo>.html`.
- `incoming=project`: `docs/incoming.html` in the main checkout. Distill adds it to the `info/exclude` file of git when the repository does not ignore it.

Intake reads a candidate by its ID from that file and removes it when it promotes or rejects it.

## Interfaces

| Interface | Role |
| --- | --- |
| OpenRig | Runs the team: workers in slots, readers with no checkout. |
| Claude Code (desktop and CLI) | Full guard. Reads and writes. |
| Codex | Partial guard. Reads and writes. |
| Pi | Partial guard. Reads and writes. |
| Zed | Remote editor. Writes go through Claude Code or Codex over ACP. The built-in agent reads only. See `docs/zed.md`. |
| ChatGPT chat | Text only. Use it for `distill` and `intake` text. It has no checkout. |
| Codex cloud, Claude Code web | Workers on tier 2 and tier 3 GitHub repositories only. Fold takes the result by commit ID. |

## Three layers of enforcement

1. **Global git hooks.** They refuse a push of a protected ref, a force push, a push of a `wip/*` ref, and a commit with an AI attribution trailer. In a repository with `decisions=none` or `decisions=frozen` they also refuse a commit that touches `docs/decisions/` or adds a `SPEC-AMENDMENTS.md`. They work for every local interface.
2. **Server rules.** Branch rules on the forge or the bare repository refuse the same pushes for cloud agents and for Zed.
3. **Harness guards.** The Claude, Codex and Pi guards refuse a merge into a protected ref, a `gh api` merge, and the deletion of the branch or worktree of another session. In a worktree where another live Claude Code or Codex process works (a shared bench), they also refuse a command that moves HEAD or the index: `checkout`, `switch`, `merge`, `reset`, `pull`, `cherry-pick`, `revert`, `stash pop` and `stash apply`. Commit on the bench where it is, under the lock. Read other refs with `git show` and `git diff`.

## The full check at a stop

The Claude Code Stop hook (`hooks/stop-check.sh`) runs the full check through `hooks/check-once.sh` when a session stops in a tree with changes or commits that are not pushed. A tree that passed before costs nothing.

An orchestrated tree is different. One orchestrator and its workers share the tree, and the orchestrator runs the full check once for each batch before it pushes. Mark the tree so that a stop runs no check:

```bash
dir="$(git rev-parse --path-format=absolute --git-common-dir)/dev-platform"
mkdir -p "$dir" && touch "$dir/orchestrated"
```

- The orchestrator writes the marker. Remove the file to get the check at each stop again.
- The marker applies to all worktrees of the repository.
- An agent can still run `hooks/check-once.sh` directly. Its lock and its result file do not change.
- `check-once.sh` exits 3 ("another check runs") when a `next build` already runs in the same tree. It does not start a second build.
