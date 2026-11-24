# Surface roles

Which surface does which class of work, what it refuses, and where it hands off. The repository's `AGENTS.md` and `CONTRIBUTING.md` win inside a repository. This file decides only which surface holds the work. `MODELS.md` decides which class of model does it.

The one rule: Git is the one record of the work, and only the owner lands. Agents make commits in their own worktree or slot, and they write diffs, reports and read-only findings. The owner lands goals, merges, tags, deploys and posts. The tier of each repository sets the refs and the landing (`docs/source-control.md`). The state of the loop is a folder on this machine (`LOOP_STATE_DIR`, skill `loop`). The loop posts nothing on issues.

| Surface | Does | Refuses, and hands off to |
| --- | --- | --- |
| Owner | Decides, reviews, lands goals, merges pull requests, tags, approves each deploy, posts | |
| Editor with chat (VS Code, Copilot, Claude Code and Codex extensions) | Surgical work with the owner present: read the diff, edit, run the checks, write the commit message, review a pull request, act on review findings | Unattended runs (loop worker). Changes on a host (Ops, with the owner's go). Push to a protected branch, merge, mark ready, approve (owner) |
| Loop worker (headless Claude Code, Codex, Pi, or an OpenRig worker seat) | One task in one slot, from its `.worker-brief.md`: the change, the check or the short proof of the brief, `.worker-pr.md`, then stop. The orchestrator or the owner folds it with `dev-loop fold` | Choosing its own task. Touching another worktree. Pushing, opening a pull request or commenting. Anything outside the scope of its brief: it stops and writes `.worker-blocked.md` |
| Desktop agent session (Claude desktop, Cowork) | The owner's second editor: work on a `wip/*` branch, phased work from a written prompt, intake from notes with the `intake` skill, pull request walkthroughs. The same hooks and skills as the terminal, so the same commands are refused | Unrequested loop dispatch or a second ledger. A push of a `wip/*` branch. Merging, marking ready, tagging, deploying (owner) |
| Codex (ChatGPT desktop app or CLI) | A bounded change with a deterministic check behind it, in its own worktree; `codex review` as evidence, never as approval. Runs under the Codex rules and the workspace-write sandbox | Judgment work: specification, review verdicts. A change that no check can catch when it is wrong. Unrequested loop dispatch or a second ledger |
| Engineer (engineering role of `owner`, Claude Code or Pi) | Specification, intake, small verified changes, review, and the loop's verbs on the owner's word in that session. The development platform. In a personal repository it may push a `type/slug` branch and run the loop's `close --push` without `--ready` | Landing, finishing, marking ready. Pushing in a professional repository. Scheduling worker launches (the tick is the owner's). Push, merge, deploy, public posts or credential changes without the owner's go |
| Ops (systems and security role of `owner`, Claude Code or Pi) | Examines a machine, a network, a service or a project for weaknesses, failures and wrong permissions. Reads at system level | Each change to a system without the owner's approval. Work outside the authorized scope |
| Assistant (personal, Pi) | Personal coordination, the journal, time tracking, finances. Reads all of the owner's files and projects, read-only; reads Engineer's sessions, memory and work entries; exchanges messages with Engineer | Engineering, review, gates, approvals, deploys. No engineering step passes through Assistant |
| Chat for thinking (ChatGPT desktop, Claude web) | Research, options, second opinions, draft text | Code and terminals. Text that must be kept goes to `distill` or `intake` |
| GitHub | The forge of a repository that has one: pull requests, checks, releases | State that Git does not hold |

## Roles of the owner's account

Engineer and Ops are roles of the user `owner`. Each is one agent definition: `agents/engineer/role.md` and `agents/ops/role.md`, installed as `~/.claude/agents/engineer.md` and `~/.claude/agents/ops.md`. Start a main session in a role with `claude --agent engineer` or `claude --agent ops`. A role has the access of `owner`. It has no login and no project grant of its own. Its memory is in `/home/engineer/memory` or `/home/ops/memory`. `agents/<role>/identity.md` is the identity of the Pi sessions of a role.

Assistant is a Unix user. His data is personal (mail, money, journal), so his separation is real.

## Shared development control

OpenRig, Pi, Claude Code and Codex control the same loop through `dev-loop` and the `ai-work` adapter (skill `development-workspace`). The loop keeps its checks and permissions on each surface. An OpenRig seat is a conversation, not a second dispatcher. To open the TUI or a control seat does not approve a task, a worker launch or a schedule. Schedules are opt-in, and no surface turns one on when it opens a workspace.

Folding, finishing, pushes to protected branches, merges, tags, deploys, professional posts and permission changes still need the owner's approval and the installed controls. No surface goes around a refused command.

## Personal and professional repositories

A personal repository is one of the owner's own projects: its `repos.conf` line has tier 1 or 2. Each other repository (tier 3 or 4, or not in `repos.conf`) is professional. Pushes to protected branches, merges, ready and approve actions and history rewrites are refused in each repository. In a professional repository nothing that reaches the forge names a tool or a model: no attribution trailer, no generated-with line, no tool name in a branch, an issue or a pull request body. The Git hooks and the guard hook refuse it.

## Desktop apps

The owner can work in Claude desktop and the ChatGPT app as much as the task needs. These rules keep that safe:

1. Code work happens in a worktree, on a `wip/*` branch in a desktop session. Rename the branch to `type/slug` before a push.
2. The Claude Code hooks, the platform skills and the Codex rules load in the desktop apps as in the terminal. A refused command is refused everywhere.
3. The loop has one ledger. On the owner's direction, each surface can examine and control that loop through `ai-work`. No surface makes a second queue.
4. Temporary scripts, probes and generated files stay in the project worktree, the slot of the worker, or the ledger folder of the project. Do not write or run engineering scripts from `~/Desktop`, `~/Downloads` or another personal folder. If the project is not clear, stop and propose a destination.
5. Text from a chat that must be kept goes into the specification or a task, through `distill` or `intake`.

## Session titles

Each agent can name its own session when the task is known, and update its own generated title when the scope changes. An agent writes only the part `purpose(area): Description #ref`; hooks and launchers add the other fields. Do not rename the live session of another agent. [Session naming](docs/session-naming.md) gives the format, the purposes and the controls of each client. The title never goes into a repository: commits, pull request bodies and specifications name no session.

## Hand-off protocol

When a request needs a capability or an authority that the surface does not have, say the boundary in one line and stop. Do not do a smaller version of the work. Examples:

- Editor chat, asked to restart a container: "A restart is host work for Ops, and it needs the owner's go."
- A loop worker that needs a file outside its scope: it writes `.worker-blocked.md` and stops.
- Each surface, asked to push to a protected branch, merge, mark ready or approve: refuse. The guard hook and the Codex rules enforce this.

## Signs that you are on the wrong surface

- You are about to change a host, a container, a phone binding or a credential.
- You are about to write process narrative into a repository: names of people, tools, models, sessions, run identifiers.
- You hold state that is only in this conversation. Put it in Git or stop.
- You are about to make or run a helper script from `~/Desktop`, `~/Downloads` or another personal folder.
