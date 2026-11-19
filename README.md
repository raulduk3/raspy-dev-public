<p align="center">
  <img src="docs/images/raspy-dev.jpg" alt="A terracotta bowl with animals carved in relief around its rim" width="360">
</p>

<h1 align="center">raspy-dev</h1>

<p align="center"><em>One small cockpit for many AI tools. Say what you want; watch a team build it on one branch; land it yourself.</em></p>

A small personal development platform for keeping AI-assisted software work organized, bounded, and reviewable.

raspy-dev is not a framework, a product, or a replacement for GitHub. It is the local glue around my editor, terminal, coding agents, repository templates, checks, native-account selection, sessions, rig seats, and project workflow. Every tool can help, git holds the truth, and a human remains the release authority. Everything runs locally; GitHub is opt-in per repository.

## What it connects

raspy-dev instruments the whole local developer stack:

- **Git and GitHub**: issues, pull requests, branch protections, rulesets, release lanes.
- **Herdr**: a cockpit view for spaces, projects, tabs, rig panes and active work.
- **OpenRig**: native project/control surface, rig seats, team spaces and seat handoff.
- **VS Code, Claude Code, Codex**: editor and agent hooks, stop checks, formatting, refusals.
- **Pi roles** (Assistant, Ops, Engineer): role-specific assistants under the same platform contracts.
- **Native account/profile controls**: explicit account selection and quota snapshots.
- **Bun, Node, Python, uv, gh, git, jq, prettier**: the ordinary local toolchain. On dev-server (Arch Linux ARM) `~/dev/dev-server/bootstrap.sh` installs it in its "dev-platform toolchain" step.
- **Laya**: optional local decision/probe service diagnostics through `ai-env doctor`.
- **Jev**: optional bounded classifier adapter through `ai-jev` and `schemas/jev/`, used only for closed routing, ranking, verification and escalation decisions.

Each tool keeps its native UX. raspy-dev supplies the common rules, scripts, templates, adapters and handoff language.

## The shape of the system

```text
owner goal
  -> decision, spec and task files (or GitHub issues, where a repository opts in)
  -> a goal branch, and a child branch per task in its own worktree
  -> Herdr / OpenRig / VS Code / Claude Code / Codex / Pi
  -> skills pick the lane and hydrate the surface
  -> checks and guardrails
  -> pull request, artifact, review finding, decision record or handoff
  -> human review, merge, tag, deploy
```

The important rule is that there is one ledger. Chats, agents, desktop apps, rig seats and terminals are work surfaces. Git is the durable record: branches, commits, task files and decision records, with GitHub issues and pull requests where a repository uses them.

## Filesystem layout

The repo expects a normal local layout but does not require secrets in the repository.
On dev-server one install serves the owner and every agent user (`lib/ai_ecosystem/paths.py`):

```text
~/dev/dev-platform             the owner's working checkout (DEV_PLATFORM_CHECKOUT)

/opt/dev-platform/             root-owned, world-readable (DEV_PLATFORM_SHARE)
  repo.git                     mirror of the checkout that releases are built from
  releases/<commit>/           `ai-release activate` output: git archive of one commit
  current -> releases/<commit> what everyone runs (DEV_PLATFORM_HOME)
  pi-runtime/<version>/        the pinned Pi package and /goal, from integrations/pi's lockfile
  openrig-runtime/             the pinned OpenRig runtime and its Node

/usr/local/bin/<command>       links into /opt/dev-platform/current/bin (and dev-loop, ghx)

A release (and the checkout) holds:
  bin/                         CLI entrypoints
  docs/                        platform contracts
  github/rulesets/             branch ruleset JSON
  hooks/                       Claude Code, Codex, check and formatting hooks
  integrations/openrig/        OpenRig seat configuration
  lib/ai_ecosystem/            session, account, workspace and environment adapters
  runbooks/                    manual procedures
  skills/                      reusable agent/operator procedures
  templates/                   files copied into new repositories
  tests/                       offline tests for the platform itself
  vscode/                      VS Code instructions and settings snippets

~/.config/dev-platform/
  repos.conf                   repository map: owner/repo, checkout, identity, base
  personal.conf                local-only list of personal repositories
  account-selection.json       local-only choice of account for each runtime
  env.d/                       local-only environment settings
  ste100                       the writing standard that the global instruction files include

~/.local/state/dev-platform/
  loop/                        local development-loop ledger
  sessions/                    reconstructed session index
  workspace/                   generated OpenRig project catalog
```

Scratch files and helper scripts belong in a project worktree or project artifact directory, not on the Desktop. The hooks enforce that for common cases.

## What is in this repository

- `bin/ai`: the menu over everything here: projects, sessions, roles, teams and accounts. It hands off to the commands below and keeps no state of its own.
- `bin/new-repo`: initializes a repository with the standard templates and branch rules.
- `bin/ai-session`: indexes native AI sessions without copying message bodies.
- `bin/ai-account`: verifies native account/profile selection and quota snapshots for new CLI launches.
- `bin/ai-work`: lists projects/sessions and forwards loop commands to the existing ledger.
- `bin/dev-workspace`: starts or plans native OpenRig control seats safely.
- `bin/rig-shape` and `skills/setup-rig`: shape a project's team (`build`, `review`, `solo`), validated by OpenRig and recorded in the team folder's history (`~/dev/teams/<team>`).
- `bin/ai-env`: read-only diagnostics for local tools, skills and optional services.
- `bin/ai-release`: builds a commit into `/opt/dev-platform/releases/<commit>` with `git archive`, activates it, and verifies that the activated release still matches its commit.
- `bin/ai-jev`: thin adapter for Jev-style bounded classification schemas; it validates typed JSON, keeps planning/writing/authority in the platform/agents/human, and disables live calls at the configured monthly spend cap.
- `hooks/`: command guards, stop checks, one-shot check caching, post-edit formatting.
- `skills/loop`: work toward a goal on one branch: dispatch workers, merge each finished child up, land the goal once.
- `skills/dev-plat` and the other pstack skills: the engineering method, ported from [pstack](https://github.com/cursor/plugins/tree/main/pstack) (MIT, Lauren Tan).
- `skills/intake` and `skills/distill`: turn a goal or external notes into decisions, spec and task files, without copying private source into repos.
- `templates/`: the repository standard: AGENTS, CONTRIBUTING, pull request template, hygiene checks, specs, release/check workflows.
- `docs/how-it-connects.md`: the map of the whole setup for the person using it. Start there.
- `docs/rig-working-branches.md`: the control rig, one worker seat per loop worktree and a Codex overseer.
- `docs/session-index.md`, `docs/session-naming.md`, `docs/development-workspace.md`, `docs/skills-layer.md` and `docs/pstack-platform.md`: the contracts for the local ecosystem.
- `ROLES.md`: which surface should do which kind of work.
- `MODELS.md`: which model tier should do which kind of work.

## Skills are the routing layer

The skills are not meant to be a pile of project-specific prompts. They are small reusable moves that let every surface ask the same questions:

- What project, worktree, loop or team owns this?
- What live context should be hydrated before acting?
- Should this be a rig seat, editor chat, loop worker, Pi role, desktop session or plain human note?
- What evidence proves the step is done?

Some tasks should enter an active loop. Some should become a rig seat with a hydration packet. Some should stay a chat, a note, or a read-only investigation. That flexibility is the point.

See [`docs/skills-layer.md`](docs/skills-layer.md) for the target shape and [`docs/pstack-platform.md`](docs/pstack-platform.md) for the engineering method.

## Agents and surfaces

The platform distinguishes roles instead of pretending every AI tool is the same:

- **Owner**: decides, reviews, merges, tags, deploys.
- **Herdr**: cockpit view over projects, tabs, rig seats and current work.
- **OpenRig seats**: bounded conversations with project identity, peers, context and stop conditions.
- **Editor chat**: surgical edits with the owner present.
- **Headless coding agents**: one issue, one branch, one worktree, stop after check and PR body.
- **Desktop agent sessions**: flexible planning, intake, review, phased work, but no competing ledger.
- **Engineering / personal assistants**: loop control, diagnostics, drafted text and coordination, or personal time/journal context, neither with release authority.

The same repository policy should be visible from every surface.

## Privacy stance

This repo is meant to be public-safe. It should contain procedures, templates, tests and generic examples, not private records.

- No API keys, tokens, private prompts, transcripts or customer records.
- No raw meeting notes or emails.
- Local configuration stays in `~/.config/dev-platform`.
- Credentials are read at runtime from the user's own credential store when needed.
- Session indexing stores metadata only, not message bodies.

If a private source produces engineering work, it becomes a redacted decision, issue, spec change or pull request. The private source itself stays outside the repository.

## Status

Personal infrastructure. Useful, tested, and evolving. Not packaged as a general-purpose product yet.

This is the public copy of a private repository. The names of people, machines and clients are replaced with generic words (`the owner`, `dev-server`, `Engineer`, `Ops`, `Assistant`, `Acme`). The machine setup that the documents call `~/dev/dev-server` (users, units, `bootstrap.sh`) is a different repository and is not public. The root login helper (`ol-login`) and its document are also not public.
