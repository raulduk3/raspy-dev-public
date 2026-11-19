# Development workspace: one loop, several surfaces

`ai-work` is a thin interface over the existing repository configuration, Git
identity, session manifests, and development loop. OpenRig, Claude Code, Codex,
and the Pi roles can invoke the same interface. It does not introduce a task database,
queue, scheduler, account switcher, or new execution authority.

## The organization

**Display group → project → existing loop → task → native session/worktree.**

Configured projects come from `~/.config/dev-platform/repos.conf` (or
`DEV_PLATFORM_REPOS` / `--config`). Their owner/repository identities and checkout
paths are exactly the identities the existing loop uses. Configuration retains its
existing whitespace-delimited format; paths containing whitespace are not supported
by that loop format. Groups default to the repository owner; with an explicit
`--dev-root`, configured and discovered projects inside that root share its first
grouping directory (or `local` for direct children). They are not
professional/personal classifications and confer no permissions.

An explicit `--dev-root ~/Dev` also finds Git repositories directly below Dev or
one grouping directory below it. Those entries are visible but cannot launch loops
until separately configured through the platform's existing process. Discovery never
recursively imports `.claude/worktrees`, transcripts, or arbitrary nested folders.
Existing repositories and session stores are neither moved nor pruned.

Projects are deduplicated by canonical `git rev-parse --git-common-dir`, not encoded
Claude directory names, remote URL guesses, or basename matching. Linked worktrees
and symlink aliases associate with the real repository; two unrelated repositories
named `project` remain distinct. If a session's working directory has disappeared,
its project is **unassigned**, not inferred from its old name.

## Read and find work

```sh
ai-work projects
ai-work --dev-root "$HOME/Dev" projects
ai-work sessions --project owner/repository --limit 20
ai-work sessions --project unassigned --limit 20
```

The interface emits JSON. Project selectors accept the exact owner/repository,
generated stable ID, or canonical checkout path shown by `projects`.
Session listings default to 20 entries (maximum 200) and return total/has_more.
They read the existing `ai-session` index; they do not rescan, copy transcripts,
start native harnesses, or claim that an indexed session is currently running.
Use `ai-session`'s supported scan/resume/handoff operations for native continuity.
The session list reads a whitelist of summary fields only and does not create an
index when none exists.

## Control the existing loop

```sh
ai-work loop owner/repository status
ai-work loop owner/repository plan
ai-work loop owner/repository start
ai-work loop owner/repository go only 12 19
ai-work loop owner/repository pause
ai-work loop owner/repository collect
ai-work loop owner/repository go only 12 --dry-run
```

These pass the exact verb and configured repository identity to the existing
`skills/loop/scripts/loop.sh`. Its repository configuration, ledger, dispatch lock,
worker cap, checks, and authorization rules remain authoritative. `--dry-run`
prints the exact argument vector and configuration without executing it. There is
no shell-string execution or arbitrary command argument.

- `status` reads the existing loop view (the underlying loop may create its ledger
  directories); `plan` and `collect` retain their existing behavior and dependencies.
- `start <type/slug>` may fetch the configured base and create the goal's rig branch and worktree.
- `go` is explicit worker dispatch and requires prior task authorization. Its only
  optional arguments are `only` or `skip` followed by positive issue numbers.
- **`pause` stops future dispatch. It does not terminate, interrupt, or acknowledge
  steering by already running workers.**
- No bridge command merges, folds, deploys, pushes, cleans worktrees, reenables a
  timer, or overrides an owner-only operation.

Use the same environment/configuration when invoking the loop directly and through
this interface. The bridge supplies `DEV_PLATFORM_REPOS` from its resolved config;
it otherwise leaves the existing loop environment intact, including brief and ledger
configuration. It never claims a message was received by a worker. Worker status requires a repository-owned supervisor command and live process identity;
PID existence alone is not evidence of a running worker. Conflicting live identity
receipts block dispatch for inspection. Interactive
steering requires that worker's native supported interface; historical transcripts
are not live controls.

A stale worker is one with no fresh live occupant acknowledgement and no fresh file
artifact proving progress. Stale work can be reassigned or closed only by writing an
evidence record in the repository's existing loop ledger or worker worktree; a missing
PID, closed pane or old transcript is insufficient by itself. Reassignment preserves the
single-owner boundary and never creates an OpenRig mission for the same task.

Batch workers that do not need a live conversation use a file contract in their worktree:
`assignment.json` for the intended task and boundaries, `result.json` for success or
blocked state, and an `evidence/` directory for logs or generated artifacts. These files
are a portable worker interface, not a new queue; the loop or human coordinator remains
the owner that decides dispatch, reassignment and fold.

## Project visibility in native OpenRig

```sh
ai-work --dev-root "$HOME/Dev" sync-openrig --workspace "$HOME/.local/state/dev-platform/workspace"
```

This is an explicit, repeatable projection into OpenRig's documented project
workspace contract:

```text
~/.local/state/dev-platform/workspace/
  workspace.yaml                  # native projects: [{id, root}]
  projects/<id>/
    SPEC.md                       # code checkout pointer and loop boundary
    project.yaml                  # openrig.project/v0alpha1
    missions/                     # no invented tasks or automatic queue entries
    exhaust/
  .ai-work-projection.json         # content ownership, not task state
```

The project-world roots are outside code repositories. Selecting a project never
places `.openrig` policy or context files in a professional repository. JSON is used
for generated `.yaml` documents; it is valid YAML accepted by the native catalog
parser. Project manifests follow the upstream schema and leave skill/context
selectors empty until a deliberate native installation configures them.

Scratch files follow the selected project boundary. Engineering scripts, probes and generated
artifacts belong in the current project worktree, the loop worker worktree, or that project's
ledger or artifacts directory. Desktop apps must not use `~/Desktop`, `~/Downloads` or personal
notes as a convenience workspace for runnable project files. When the right destination is
unclear, the session stops and proposes a destination map instead of creating the script in a
personal holding area.

The sync command does not configure or start OpenRig. Configure its
`workspace.root` / `workspace.catalog_path` with the native `rig` commands for the
installed release, and use its native `files.allowlist` for any necessary source
reads. The catalog grants neither file access nor permission to execute work.
Point it at the generated catalog; don't initialize a conflicting catalog over it.

**The native Projects panel provides organization; it does not magically convert
existing loop tasks into OpenRig missions or wire native mission execution buttons
to the loop.** In a coding/control seat, the shared interface above controls the
existing loop. Do not separately dispatch the same task into OpenRig's queue.
A future native event/control integration must preserve that single-owner boundary.

Projection reconciliation is intentionally conservative:

- Use a workspace outside Git repositories.
- Unrelated files are preserved.
- Existing unowned files or locally edited generated bytes cause a collision error;
  there is no `--force` and no silent overwrite.
- Symlinked generated paths are rejected.
- All path/content collisions are checked before generated files are changed.
- A filesystem lock serializes syncs; individual files are replaced atomically.
- Removed projects leave their external project-world files intact. No pruning is
  performed, even when they disappear from the newly projected catalog.

If a projection has been edited intentionally, retain it and select another output
workspace or resolve that exact collision manually. The receipt is evidence of
owned bytes, not authority to remove user data.

## Verification and limits

`tests/test_workspace.py` uses real temporary Git repositories and linked worktrees,
real session manifests, and the actual loop status/pause/dispatch-lock paths. It
checks bounded output, ambiguous identities, safe projection, preservation, exact
argument forwarding, and lock enforcement without launching workers or reaching a
remote. These are boundary tests, not claims of a live OpenRig interaction test.

Nothing here unifies provider quotas, grants release authority, claims full native
conversation migration, or turns headless processes into interactive terminals.
Those boundaries remain explicit so a fresh checkout is repeatable and controllable.
