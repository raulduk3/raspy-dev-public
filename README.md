<p align="center">
  <img src="docs/images/raspy-dev.jpg" alt="A terracotta bowl with animals carved in relief around its rim" width="360">
</p>

<h1 align="center">raspy-dev</h1>

<p align="center"><em>Paste this into your agent to figure out what you might want from this system.</em></p>

```text
Read the repository at <the address of this page>. Start at README.md and do what
the section "Prompt for the agent" tells you. Then tell me what I might want from
this system.
```

The rest of this page is for the agent.

## Prompt for the agent

You are an AI agent. A person asked you to read this repository and to say what the person can use from it. Read this prompt fully before you open other files.

### What this repository is

raspy-dev is the platform that one person uses for software work with AI agents on one Linux machine. It is the layer around an editor, a terminal and the coding agents Claude Code, Codex and Pi. It holds commands, hooks, skills, templates, checks and documents. It is not a framework and it is not a product.

Three rules apply in all parts:

- Git is the one record. Chats, agents and terminals are places of work. They are not records.
- Each agent works in a bounded place: one task, one worktree, one check.
- A person decides, reviews and releases. In a shared repository, only the person puts a finished goal on the base branch.

### What this copy is

- This is the public copy of a private repository. Generic words replace the names of people, machines and clients: `the owner`, `dev-server`, `laptop`, `git-host`, `Acme`, `Globex`. The three agent roles have the names `Engineer`, `Ops` and `Assistant`.
- Some parts are not in this copy: the machine setup (the documents call it `~/dev/dev-server`, with its users, units and `bootstrap.sh`), the sign-in helper `ol-login`, the decision records and the task files of the platform. Text that points to these parts has no target here.
- This copy has no installer. The documents describe one machine (Arch Linux ARM) with a shared release in `/opt/dev-platform`. Read each path, user name and host name as an example.
- `vendor/pstack` is a copy of a third-party project (MIT, Lauren Tan). It has its own license.

### How to read it

1. Read `docs/how-it-connects.md`. It is the map of the full system.
2. Read `ROLES.md` and `MODELS.md`. They say which surface and which model tier does which work.
3. Read `docs/source-control.md`. It gives the tiers, the branches and the rules for landing.
4. Then open only the parts that fit the person. Use the table below.

Read the files. Do not run a command from this repository, do not install anything and do not change the machine of the person, unless the person tells you to. The test command `bin/check` needs `jq` 1.8 and a pinned Pi runtime. On a machine without them, some tests fail.

### The parts

| If the person wants | Read |
| --- | --- |
| One menu for projects, sessions, roles, teams and accounts | `bin/ai` |
| A standard for each new repository: agent instructions, contribution rules, hygiene checks, specification files and task files | `bin/new-repo`, `templates/`, `runbooks/new-repo.md`, `skills/new-repo/SKILL.md` |
| Guards that refuse a risky command or a wrong push before it runs | `hooks/pre-tool-use-guard.sh`, `hooks/guard_git.py`, `hooks/git/`, `hooks/codex.rules`, `hooks/claude-settings.hooks.json`, `hooks/codex-hooks.json` |
| A check that runs before an agent stops, with one result for each state of the code | `hooks/stop-check.sh`, `hooks/check-once.sh` |
| One goal that many workers build on one branch, with a check before each result is joined | `skills/loop/SKILL.md`, `skills/loop/scripts/`, `docs/forge.md`, `bin/dev-forge` |
| A goal, notes or a transcript made into decisions, specification changes and tasks | `skills/intake/SKILL.md`, `skills/distill/SKILL.md`, `skills/spec-lint/SKILL.md`, `bin/dev-spec`, `docs/spec/`, `templates/docs/spec/` |
| An engineering method that agents load as skills | `skills/dev-plat/SKILL.md`, `docs/pstack-platform.md`, `docs/skills-layer.md`, the `skills/principle-*` folders |
| Rules for the start of each session, and a plain writing standard | `skills/develop/SKILL.md`, `skills/develop/ste100.md`, `skills/develop/owner-words.md`, `docs/session-entry.md` |
| Session titles in one format, and an index of sessions | `docs/session-naming.md`, `bin/ai-title`, `hooks/session-title.py`, `docs/session-index.md`, `bin/ai-session` |
| A catalog of projects and a workspace for each project | `docs/development-workspace.md`, `bin/ai-work`, `bin/dev-workspace`, `skills/development-workspace/SKILL.md` |
| Named roles with their own scope and memory | `agents/`, `ROLES.md`, `bin/ai-role`, `integrations/pi/`, `docs/pi-transition.md`, `docs/agent-memory.md`, `bin/ai-memory` |
| Teams of agents with OpenRig | `integrations/openrig/README.md`, `bin/rig`, `bin/rig-shape`, `skills/setup-rig/SKILL.md`, `docs/rig-working-branches.md`, `docs/api-rig.md` |
| Models by tier, and accounts with their usage | `MODELS.md`, `bin/pstack-model`, `skills/setup-pstack/SKILL.md`, `bin/ai-account`, `bin/ai-usage`, `docs/usage.md`, `docs/host-account-service.md` |
| A small classifier for closed questions: route, rank, verify | `docs/jev.md`, `bin/ai-jev`, `schemas/jev/` |
| Diagnostics, releases and incident steps | `bin/ai-env`, `bin/ai-release`, `runbooks/release.md`, `runbooks/incident.md` |
| A journal in plain text files | `docs/filesystem-journal.md`, `lib/journal.py` |
| Editor setup | `vscode/README.md`, `docs/zed.md` |

### What to tell the person

If you do not know these three things, ask first:

1. Which agents and editors does the person use?
2. Does the person work alone or in a team, and where is the code hosted?
3. What goes wrong today? Examples: an agent pushes to the wrong branch, sessions get lost, nobody reviews the work, there is no specification.

Then answer in this sequence:

1. One paragraph that says what this system is, in plain words.
2. Three to five parts that fit this person. For each part, give what it does, the files to read, what the person must have (tools, accounts), and how much work it is to use that part alone.
3. The parts that do not fit this person, one line for each, with the reason.
4. What is not in this copy, and what the person must supply.
5. One first step that takes less than one hour.

Rules for your answer:

- Say only what the files show. Give a path for each statement.
- If you did not read a file, say so.
- Do not tell the person to adopt the full system. Most parts are useful alone, and some parts depend on the machine setup that is not here.
- Do not copy a file into a project of the person before the person agrees. The license is MIT (`LICENSE`).
