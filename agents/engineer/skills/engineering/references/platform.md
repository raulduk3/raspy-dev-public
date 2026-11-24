# Operating the platform

The owner runs his engineering through this platform and wants to talk to you about it rather
than to a fresh session. Know where its truth lives, read that before acting, and keep
observation, reversible local changes and outward or costly actions apart.

## Where the truth lives

Everything below is relative to the activated release, `/opt/dev-platform/current`.

| Question | Read |
| --- | --- |
| What is an account, home, project, worktree, session, role, rig, pod, seat, space, tile; which tool owns each; known limits and fixes | `docs/how-it-connects.md`, first, every time the question is about the platform |
| How a project's team and loop workers share branches | `docs/rig-working-branches.md` |
| Which surface holds which work, and what each refuses | `ROLES.md` |
| Which model class runs which work | `MODELS.md` |
| OpenRig install, the local fork, the launcher and its boundaries | `integrations/openrig/README.md` |
| Accounts and usage | `docs/spec/SDD.md`, section AC |
| Sessions, the index and naming | `docs/session-index.md`, `docs/session-naming.md` |
| OpenRig's own contracts (RigSpec, AgentSpec, edges) | `rig --help`, and `~/.local/share/dev-platform/openrig-runtime/app/node_modules/@openrig/cli/daemon/docs/reference/` |

The release is a copy of one commit. `readlink /opt/dev-platform/current` names it,
and it may be cut from a branch other than `develop`. Before reasoning from a checkout, find
which branch that commit is on. A platform change reaches you and every seat only after a new
release is cut and activated, which is the owner's go.

## Look before you act

These change nothing; run them whenever the state matters:

- `rig ps`, `rig ps --include-archived`, `rig ps --nodes --rig <name>`, `rig ps --json` for IDs.
- `tmux ls`; `herdr workspace list`; `herdr status`.
- `ai-usage`; `ai-env doctor` (a `stale` skill folder means its links point into an older release; relink them to `current/skills/<name>`); `ai-account status` (from a plain terminal: inside a Claude
  desktop session every account reads as unverified).
- `ai-session` and the transcripts themselves: `~/.claude/projects/<cwd-slug>/<id>.jsonl`,
  `~/.codex/sessions/`. A session outlives its seat, its rig and its herdr tile.
- `dev-loop status <owner/repo>` for a loop; `git worktree list` for a project.

## Operations and their traps

| Goal | Do | Trap |
| --- | --- | --- |
| Start a project's standard team | The `ai` menu, or `dev-workspace start engineer --cwd <team folder> --rig engineer-<project>` | The menu ties a team to a repository through `engagements/<slug>/project`, which holds `owner/repo` |
| Give a project its own team | `~/dev/teams/<team>/rig.yaml` named `engineer-<project>`, `path:` agents beside it; `rig spec validate`, `rig agent validate`, `rig up <spec> --plan`; then start it from the menu or `dev-workspace start engineer --cwd <team folder> --rig engineer-<project>` | The launcher starts that spec with no `--cwd`, since `--cwd` overrides every member's folder, and refuses a spec whose `name` differs from the team's |
| Rename a team | Stop it, then start fresh under the new name | A rig name is its identity (`pod-member@rig`); nothing renames it, and `rig up --existing` cannot restore a stopped rig |
| Hide an old team | `rig archive <rig ID>` | Takes the ID from `rig ps --json`, not the name. Reversible with `rig unarchive` |
| Tidy herdr | `herdr workspace close <id>` | A space or tile is only a view; closing it stops nothing. Open a team from the menu once before using `rig tui` to open agents |
| Give a loop worktree a seat | `dev-workspace add-worker`, and `remove-worker` before its fold | The loop still owns the work; the seat is only its terminal |
| Recover a conversation | `claude --resume <id>` from the session's original folder, or the menu's sessions | Stopping or archiving a rig deletes no transcript |

## Designing a team

Start from the smallest team that does the job. Each seat gets one folder that is its alone
(`separate-before-serializing-shared-state`): a writer seat in its own worktree, a
coordinating or operating seat in the team folder outside the repository. Give each
seat short standing guidance that names its folder, what it may change, what waits for
the owner's word, and the few principles that fit its job, pointing at the full rules rather than
copying them. Silent seats, no startup prompts, unless the owner asks otherwise. A seat on an
isolated account does not see the platform skills; the default homes do. A Codex seat cannot
reach local ports from its sandbox, so every `rig`, `docker` or `curl` it runs needs escalation.

## Authority

Observation is always fine. Reversible local work on the owner's request needs no extra question:
a team folder, a spec, a worktree, closing a view. Starting or stopping seats spends
the owner's quota and changes what he sees, so do it when he asks for it. Activating a release,
changing accounts or credentials, restarting the OpenRig daemon, changing OpenRig or herdr
configuration, enabling any schedule, and anything leaving the machine need his explicit word
in the current session.

When the platform itself is wrong, fix it at its source in `~/Dev/dev-platform` through the
repository's branch and pull request rules, record the lesson in `docs/how-it-connects.md`
when it is general, and keep dated facts about one day's state in your memory instead.
