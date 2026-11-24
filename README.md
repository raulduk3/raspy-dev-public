<p align="center">
  <img src="docs/images/raspy-dev.jpg" alt="A terracotta bowl with animals carved in relief around its rim" width="360">
</p>

<h1 align="center">raspy-dev</h1>

<p align="center"><em>Paste this into your agent to figure out what you might want from this system.</em></p>

```text
Read the repository at https://raw.githubusercontent.com/raulduk3/raspy-dev-public/main/README.md. Do what
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
- Some parts are not in this copy: the machine layer of the server (its bootstrap, users and units, the server launcher `agent`, the journal commands and the chat; some documents call it `~/dev/dev-server`), the sign-in helper `ol-login`, the mail, money and time commands, the decision records and the task files of the platform. Text in the code and the documents that points to these parts has no target here.
- The menu `bin/ai` has entries for the commands of the machine layer. An entry shows only where its command is on the path, so on a machine without that layer the menu shows only the platform.
- This copy has no installer. The documents describe one machine (Arch Linux ARM) with a shared release in `/opt/dev-platform`. Read each path, user name and host name as an example.
- `vendor/pstack` is a copy of a third-party project (MIT, Lauren Tan). It has its own license.

### How to read it

1. Read `docs/how-it-connects.md`. It is the map of the full system.
2. Read `ROLES.md` and `MODELS.md`. They say which surface and which model tier does which work.
3. Read `docs/source-control.md`. It gives the tiers, the branches and the rules for landing.
4. Use `docs/spec/SDD.md` to find what a part must do, and `docs/spec/TDD.md` to find the code and the tests of that part.
5. Then open only the parts that fit the person. Use the table below.

Read the files. Do not run a command from this repository, do not install anything and do not change the machine of the person, unless the person tells you to. The test command `bin/check` needs `jq` 1.8 and PyYAML. The checks of the Pi code need Node and the pinned Pi runtime; without them, these checks are skipped or fail.

### The specification

The specification covers the full copy. `docs/spec/SDD.md` holds the system requirements in the chapter SY, then one section of requirements for each area. `docs/spec/TDD.md` holds one design item for each part of the design. Each design item names the requirements that it meets, its code files and its test files. Each code file and each test file of this copy has a design item; the files below `docs/`, `templates/`, `vendor/` and `tests/support/` are not counted.

To compile it, when the person agrees, run `bin/dev-spec check --layout single` in the root of this copy. It only reads. The last line gives the faults and the gaps; for this copy it is `0 faults, 0 gaps`. `bin/dev-spec compile --layout single` also writes the page `tree.html`, with each requirement, its design and its tests, into `.git/dev-platform/`.

### Connect a repository with no file added to it

`bin/dev-project connect <folder> --ghost` connects a repository to the platform and adds no file to it. It proposes the tier, the base branch, the check and the layout, and asks to confirm each value. It writes the settings to one record outside the repository, `~/.config/dev-platform/projects/<name>.json`. With `--ghost`, the specification and the task files go to a side folder outside the repository. `bin/dev-project brief <folder>` prints the text that each Claude Code session in that folder gets.

### The parts

| If the person wants | Read |
| --- | --- |
| One menu for projects, sessions, roles, teams and accounts | `bin/ai` |
| Settings for each project in one record outside its repository | `bin/dev-project`, `lib/ai_ecosystem/projectrecord.py` |
| A standard for each new repository: agent instructions, contribution rules, hygiene checks, specification files and task files | `bin/new-repo`, `templates/`, `runbooks/new-repo.md`, `skills/new-repo/SKILL.md` |
| Guards that refuse a risky command or a wrong push before it runs | `hooks/pre-tool-use-guard.sh`, `hooks/guard_git.py`, `hooks/git/`, `hooks/codex.rules`, `hooks/claude-settings.hooks.json`, `hooks/codex-hooks.json` |
| A check that runs before an agent stops, with one result for each state of the code | `hooks/stop-check.sh`, `hooks/check-once.sh` |
| One goal that many workers build on one branch, with a check before each result is joined | `skills/loop/SKILL.md`, `skills/loop/scripts/`, `docs/forge.md`, `bin/dev-forge` |
| A goal, notes or a transcript made into specification changes and tasks | `skills/intake/SKILL.md`, `skills/distill/SKILL.md`, `skills/spec-lint/SKILL.md`, `templates/docs/spec/` |
| A specification that shows the design, the code and the tests of each requirement | `bin/dev-spec`, `lib/ai_ecosystem/spectree.py`, `lib/ai_ecosystem/specwrite.py`, `docs/spec/` |
| An engineering method that agents load as skills | `skills/dev-plat/SKILL.md`, `docs/pstack-platform.md`, the `skills/principle-*` folders |
| Rules for the start of each session, and a plain writing standard | `skills/develop/SKILL.md`, `skills/develop/ste100.md`, `skills/develop/owner-words.md` |
| Session titles in one format, and an index of sessions | `docs/session-naming.md`, `bin/ai-title`, `hooks/session-title.py`, `docs/session-index.md`, `bin/ai-session` |
| A catalog of projects and a workspace for each project | `bin/ai-work`, `bin/dev-workspace`, `skills/development-workspace/SKILL.md` |
| Named roles with their own scope and memory | `agents/`, `ROLES.md`, `bin/ai-role`, `integrations/pi/`, `bin/ai-memory` |
| Teams of agents with OpenRig | `integrations/openrig/README.md`, `bin/rig`, `bin/rig-shape`, `skills/setup-rig/SKILL.md`, `docs/rig-working-branches.md` |
| Models by tier, and accounts with their usage | `MODELS.md`, `bin/pstack-model`, `skills/setup-pstack/SKILL.md`, `bin/ai-account`, `bin/ai-usage`, `config/accounts.json`, the section AC of `docs/spec/SDD.md` |
| A small classifier for closed questions: route, rank, verify | `bin/ai-jev`, `lib/ai_ecosystem/jev.py`, `schemas/jev/` |
| Diagnostics, releases and incident steps | `bin/ai-env`, `bin/ai-release`, `runbooks/release.md`, `runbooks/incident.md` |
| A read-only reader of the task lines in a folder of Markdown notes | `lib/journal.py`; `docs/filesystem-journal.md` describes the journal, whose commands are not in this copy |
| Editor setup | `docs/zed.md` |

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
