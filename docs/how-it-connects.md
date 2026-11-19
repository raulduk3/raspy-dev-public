# How everything connects

A map of the AI setup on this machine. Read the first two sections and you can use the
whole thing. The rest is reference.

## The model

Everything on this machine is one of these things, each owned by one other thing or by
nothing, each with one tool that manages it.

| Thing | What it is | Where it lives |
| --- | --- | --- |
| **Account** | One subscription or key you have signed in to. | `/var/lib/dev-server/accounts/registry.json`, made from the platform's `config/accounts.json` |
| **Home** | An account's own folder: login, settings, past transcripts. | `~/.claude`, `~/.codex`, or `accounts/<account>` |
| **Project** | One Git repository. | its checkout, in `~/dev/<project>` or `~/dev/<group>/<project>`; the platform itself is `~/dev/dev-platform` |
| **Worktree** | One branch of a project, checked out in its own folder. | `<checkout>/.claude/worktrees/` |
| **Session** | One conversation with one agent, in one folder, as one account. | a transcript inside that account's home |
| **Role** | Assistant, Ops or Engineer: a persona and what it may touch. | `agents/<role>/identity.md` |
| **Conversation** | A role's durable thread, which spans many Pi sessions. | `sessions/conversations/<id>/` |
| **Rig**, or team | Agents working together on one project. | OpenRig's database, or Claude Code sessions, plus a team folder `~/dev/teams/<team>` |
| **Pod** | A group of seats in a rig: control, review, workers. | the rig's spec |
| **Seat** | One agent slot: a runtime, a home, a folder and a tmux session. | tmux session `<pod>-<member>@<rig>` |
| **Space** | herdr's view of one rig. | herdr, labeled with the rig's name |
| **Tile** | A viewer of one seat, beside `rig tui`. | a herdr pane |

The rules that follow from it:

- **A project owns its code.** Only a worker seat writes inside it, in its own worktree, on its own branch.
- **A rig belongs to one project.** The menu names it `engineer-<project>`; control and overseer work from the team folder `~/dev/teams/<team>`, outside the repository. One running rig per project.
- **A seat belongs to one rig.** OpenRig enforces this. Any seat in any rig can run as any account, and a session's history outlives its seat.
- **A session is one conversation.** One runtime, one account, one folder. A plain Claude session in a project has no rig and no seat, and that is normal.
- **A space is only a view.** Closing a tile or a whole space stops nothing.
- **Accounts sit above everything.** They belong to no project or rig; `ai-usage` reads them all at once.

| Tool | Manages |
| --- | --- |
| `ai` | Everything. The menu, and the only command you need day to day. |
| `ai-work`, `dev-loop` | Projects, worktrees and the development loop. |
| `ai-session` | Sessions and conversations. |
| `ai-role` | Opening a role's conversation. |
| `ai-account`, `ai-environment`, `ai-usage` | Accounts: one resolver and one usage record. The sign-in helper (`ol-login`) is not in this copy. |
| `ai-usage` | How much each account has left. |
| `api-rig` | A project's team on the OpenRouter key alone, running the lifecycle unattended under spend caps ([api-rig.md](api-rig.md)). |
| `ai-jev` | Optional bounded Jev classifier adapter for closed routing, ranking, verification and escalation schemas. |
| `dev-workspace` | Starting rigs, and adding or removing worker seats. |
| `rig` | OpenRig itself: rigs, pods and seats. |
| `tmux` | The terminal each seat runs in. |
| `herdr` | Spaces and tiles. |

On disk:

```
~/dev/<project>/  ~/dev/<group>/<project>/  a project's checkout
  .claude/worktrees/<name>/               every worktree of the project, from any tool; no other place
~/dev/teams/<team>/                       a team's control folder: rig.yaml or RIG.md, guidance, prompts; its own Git history; notes/ untracked
  .claude/worktrees/rig-<type>-<slug>/     a goal's rig branch
  .claude/worktrees/loop-<N>-<slug>/      one issue's branch; its worker seat works here
~/.claude  ~/.codex                       the two default homes
~/.config/dev-platform/                   repos.conf, personal.conf, account-selection.json
/var/lib/dev-server/accounts/               the account register (registry.json) and one file for each sign-in
~/.claude-accounts/<account>/             an isolated Claude home for a second account
/opt/dev-platform/
  current -> releases/<commit>/           the platform: bin, lib, agents, integrations
                                          built and activated by `ai-release activate <commit>`, never copied from a checkout
~/.local/state/dev-platform/
  sessions/                               the session index and role conversations
    conversations/<id>/                   canonical conversation homes: manifest, handoff, native refs, artifacts
    work/conversations/<name>/            named filesystem views over canonical conversation homes
    work/agents/<agent>/<name>/           role views of the same conversations
    work/projects/<project>/<name>/       project views of the same conversations
  openrig/                                rig specs and worker fragments the launcher writes
  loop/<owner__repo>/                     the loop ledger, unless brief.conf's LOOP_STATE_DIR moves it
~/.openrig/                               OpenRig's daemon database
~/.config/herdr/                          herdr's server socket and saved layout
```

## How an agent is told what to do

An agent's instructions come from layers. Each layer is a file or a message, and each has one owner.

| Layer | Where it comes from | Reaches |
| --- | --- | --- |
| Account instructions | `CLAUDE.md`/`AGENTS.md` in the account's home | Every session and seat as that account |
| Project instructions | The repository's own `AGENTS.md`/`CLAUDE.md` | That checkout or its worktrees |
| Seat guidance | `integrations/openrig/agents/<agent>/guidance/role.md`, merged into the seat's `CLAUDE.md`/`AGENTS.md` | That seat only |
| OpenRig culture | OpenRig's default culture file, merged the same way | Every seat |
| Identity message | OpenRig types a short "which seat you are" message | Every seat, at start |
| A task | A worker's `.worker-brief.md`, written by the loop | That worker, when told to start |
| Role resources | Shared session entry, the role's identity and memory; Engineer also gets the project's instructions and its engineering skill | Assistant, Ops, Engineer Pi sessions |

The platform's control, overseer and worker seats get standing guidance only, and they wait for you.

Source control follows one tier for each repository. See [source-control.md](source-control.md).

## Skills: where they live and who sees them

A skill is a folder with a `SKILL.md`. An agent sees a skill only if it sits in the skills folder of the home it runs as: `<home>/skills`, for Claude and Codex alike. `~/.agents/skills` is the shared folder the default homes link through.

| Where skills come from | What |
| --- | --- |
| The platform release, `skills/` | `bounded-decisions`, `development-workspace`, `distill`, `intake`, `loop`, `new-repo`, `/develop`, `spec-lint` |
| pstack (`vendor/pstack`, ported by `bin/pstack-port`) | `/dev-plat`, its routed skills and the 23 `principle-*` skills; see `docs/pstack-platform.md` |
| Engineer's own resources | `engineering`, loaded only into Engineer's Pi sessions |
| OpenRig | `openrig-skills`, vendored into the default Claude home and the shared folder |
| The clients themselves | Claude desktop's synced skills; Codex's own |

| Runs as | Platform skills it sees |
| --- | --- |
| `anthropic-bravo` (`~/.claude`) | All of them |
| `openai` (`~/.codex`) | All of them |
| `anthropic` (isolated) | None. Only Claude desktop's synced skills. |
| `openai-bravo` (isolated) | None |
| An OpenRig seat | Whatever its account's home has, plus any `skill_install` in its agent. The platform's agents install none. |
| Assistant, Ops, Engineer (Pi) | Skill discovery is off. `/develop` arrives as instructions; Engineer also gets `engineering`, `new-repo`, `intake` and `distill`. |

An isolated account's seats and sessions do not have `loop`, `development-workspace` or the others as skills, though session entry still reaches them through the default home's copy. Each platform skill is linked to `~/.local/share/dev-platform/current/skills/<name>` so it follows activation; `ai-env doctor` reports a link into any other release as `stale`.

## What OpenRig writes into your project folder, and why

When a seat starts in a folder, OpenRig places three small files there: a status-line config, its script, and a `CLAUDE.md`/`AGENTS.md` guidance block naming the seat. Harmless in a scratch folder or your own project, but it's why the launcher refuses to start a seat directly inside a professional repository checkout: those files would show up in someone else's git status.

The rule for project work is one seat per working branch, removed before its branch is folded, which puts the guidance files back. `docs/rig-working-branches.md` has the commands.

## Day to day

**Start with the menu.** One command covers everything below: projects, sessions, Assistant, Ops, Engineer, teams and accounts. Arrow keys move, typing filters, Enter opens, Esc goes back. Anything you open hands over the terminal and comes back to the menu when you leave it.

```bash
ai
```

`ai research` jumps straight to the project whose name matches.

**See how much you have left.** Nothing changes.

```bash
ai-usage
```

Codex numbers are live. Claude numbers are a recent reading with an age, captured by a status line as it renders. An unused account reads as unknown, never zero.

**Open the dashboard.** Nothing changes. Press `?` inside it for every command.

```bash
dev-workspace
```

**Check the machine contract.** Nothing changes. This is the shared health gate the `ai` menu uses before team launch and panel layout.

```bash
ai-env doctor
```

**Start one seat on a chosen account.** Always plan first; it refuses an account that is
out of quota or not verified, and it launches nothing.

```bash
dev-workspace plan claude --account anthropic --cwd /path/to/folder
dev-workspace start claude --account anthropic --cwd /path/to/folder
```

Each account gets its own rig name, so two accounts never collide. Reusing a rig resumes its original session in its original folder.

**Give a project its own team.** Use a shape: `/setup-rig` in Claude, Codex or Engineer, or **This project's team → Shape this team** in the `ai` menu, or `rig-shape write <project> build|review|solo [--runtime lead=codex]`. It writes the spec to `~/dev/teams/<team>/rig.yaml`, checks it with `rig spec validate`, and commits it to that folder's Git history. `dev-workspace start engineer` then starts that spec instead of the standard control and overseer. Before the menu starts or reshapes a team, it runs the machine contract from `ai-env doctor`: OpenRig version/runtime/config/workspace, the local Codex `exec` patch, instruction surfaces and tmux provider overrides must be healthy. Before it opens herdr panels, herdr's command, server, config and socket must be healthy.

**Attach to a seat, detach, stop a team.**

```bash
tmux attach -t <seat-name>        # Ctrl-b then d to detach
rig down <rig-name>               # stops every seat, keeps a snapshot
rig archive <rig-id>              # hides a stopped team; takes the ID from rig ps --json, not the name
```

A rig's name is part of every seat's identity, so nothing renames one. To rename a team, stop it, archive it if you like, and start a fresh one under the new name.

**Give Assistant, Ops and Engineer web search.** Their search tool uses Perplexity. Store the key once, from the Mac or on dev-server; it is typed into a hidden prompt and kept by root:

```bash
ol-login perplexity
```

Claude and Codex sessions use their own built-in web search, not Perplexity. The roles also have `web_fetch`, which reads one public page by its address and refuses local and private network addresses.

**Use Jev as a classifier only.** `ai-jev` loads closed schemas from `schemas/jev/` and returns typed JSON for routes, rankings, verification and escalation. It does not plan, write, summarize, settle truth or authorize work; ordinary platform code and the human owner decide what happens with the classification.

## Known limits

- **Open a team from the menu once before using `rig tui` to open agents.** Until the menu builds the space for a rig, OpenRig makes a new one for each open.
- **Ending an agent from inside its tile leaves a bare shell in its seat.** Leave with Ctrl+b then q instead.
- **Claude usage is a snapshot.** Only a running session reports it, so expect an age on every Claude number.
- **The dashboard shows Codex seats as "needs attention".** OpenRig checks the foreground process, and `codex` here is a Node wrapper. Claude seats verify correctly. Reported upstream.
- **A stopped rig cannot be restored with `rig up --existing`.** Stock OpenRig behavior. Start a fresh rig instead.
- **A seat's usage comes from OpenRig's own status line.** `ai-usage` folds it into the record under the account the seat was launched on (`usage/seats/SEAT`).

## When something looks wrong

| Symptom | Cause | Fix |
| --- | --- | --- |
| Daemon stops at start with `ERR_DLOPEN_FAILED` | Wrong Node on PATH | Start it through `dev-workspace` or `bin/rig`, which use the pinned Node 24 |
| A new seat sits on "Connection refused, retrying" | Inherited stale proxy URL | `ai-env doctor` shows it; `dev-workspace start` removes it; or `tmux set-environment -g -u ANTHROPIC_BASE_URL` |
| A seat times out after 30 seconds, never interactive | Claude's first-run Chrome dialog in a fresh home | `bootstrap.sh` records the answer in each agent's `~/.claude.json`; rerun it |
| `ai-account status` says every account is unverified | Run from inside a Claude desktop session, which sets a provider variable | Run it from a plain terminal |
| A Codex seat shows "needs attention" but works | The foreground-process check, see Known limits | Ignore, or report upstream |
