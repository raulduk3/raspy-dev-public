# Pi ecosystem transition

Status: OpenClaw is retired (owner, 2026-09-24): it is no longer used, and Assistant, Engineer and Ops run in Pi. Its records stay preserved read-only. The acceptance list below is kept as the migration record.

Priority correction: session ownership, scope and filesystem continuity come first. Follow [Shared session contract](session-context-contract.md) before expanding agent launches. Assistant is personal and project-independent; Engineer requires a project or formation workspace; Ops starts with explicit system or project scope. Authentication alone is not readiness to migrate.

## Required acceptance

- Full original personal and agent records preserved; hashes and representative restoration verified. Live preliminary copies are not final quiescent archives.
- Assistant, Engineer and Ops retain source-linked historical access and role boundaries.
- Shared skills/tools no longer depend on paths that retirement will remove.
- Pinned Pi runtime passes startup and real authenticated session checks; native sign-in stays native and credentials are not copied into project files.
- Engineer starts in an explicit project or project-formation workspace, with the shared development workflow.
- Rig opens in that engineering context; focused native code windows operate on the same tasks/worktrees.
- All four account profiles independently verified, with native account isolation. Existing sessions unaffected by new-launch selection.
- Account/session service connects to Rig and a human TUI: eligible accounts, usage observation age, assignments, concurrency, drain and checkpointed transitions.
- Rig owns team coordination; dev-platform retains engineering gates and primitives. Existing loops transfer ownership explicitly; no duplicate dispatch.
- One complete engineering task demonstrates account attribution, steering, takeover, verification, review and restoration.
- Personal integrations and explicitly authorized schedules tested individually.
- Reversible OpenClaw shutdown trial succeeds before removal; protected historical archive remains.

## Implemented in this branch

`integrations/pi/package.json` and lockfile pin Pi 1.5.0 (0.87.1 until 2026-10-05, 1.0.4 until 2026-11-03) and the `/goal` extension pi-goal-x 0.34.1 (which needs Pi 1.4 or later); install with `npm ci --ignore-scripts`. Dependencies remain local to the integration directory. No global installation or default login is changed.

`bin/ai-history --archive <preservation-directory> --agent engineer find <text>` searches preserved conversation labels. `windows <conversation-key>` lists saved windows and their predecessor links. Both return top-level `has_more` and `next_offset`; pass `--offset <next_offset>` after the subcommand to continue until exhausted. `read <session-id> --after <event-sequence>` pages original user/assistant text. `--limit` precedes the subcommand and bounds scanned events, including non-message events. The read cursor advances even if a page contains only tool events. Pi's history tool exposes `offset` for find/windows and `after` for read. This is an initial title locator and transcript reader, not full-text or semantic retrieval.

The archive contract is `sqlite-consistent/{main,hermes,ops}.sqlite`. SQLite is opened read-only and query-only. Histories are reference data, never current instructions. Output can contain private original conversation content; keep it local and retrieve only relevant passages.

## Outstanding integration constraints

The observed installed Rig provider switch implementation returns `switch_execution_not_yet_wired`. A profile label or TUI menu cannot establish successful account binding. The account service must verify runtime identity and report actual results.

The current target is host-native Pi through the shared account service, with
OpenAI alpha as the initial preference and independent supported Pi authentication.
The earlier mandatory-container direction is superseded. Native profile isolation
must preserve host cwd/HOME; do not copy tokens or silently substitute API billing.
See [the unified specification](AI-ECOSYSTEM-SPEC.md) for current evidence and gates.
A real ephemeral Pi inference has been reported by the implementation task; full
role launch, account attribution and durable authenticated resume remain open.

The host account service now has native launch support. Both providers’ complete Rig profile propagation remains acceptance work.

## Role resource loading

`integrations/pi/role-resources.mjs` is the reusable resource-loading component for the future account-bound launcher. It consumes an already validated conversation, absolute conversation/platform/auth/identity paths, and returns explicit cwd, Pi resources, in-memory settings and the conversation's native session directory.

Personal Assistant and system Ops use a neutral workspace within the conversation home and load no repository context. Project/formation Engineer and project Ops use the bound workspace and Pi's repository-context discovery. All roles load shared `/develop` guidance and their explicitly supplied identity file. Each role's skills come from one table, `agents/skills.json`, which the Claude Code and Codex homes read too (`ai-guardrails --role`): Assistant and Ops have none, Engineer its engineering skill and the platform skills for project work. Engineer in a project also loads the project's own skills from `.agents/skills`, `.claude/skills` and `.pi/skills`; a name the platform already gave it stays the platform's. Automatic extensions, skills, prompt templates and themes are disabled. The Perplexity extension is explicitly loaded. So is pi-goal-x, which gives every role `/goal`: a persistent objective it keeps working toward until done, paused or out of budget. `ai-role launch` sets `PI_GOAL_ROOT` to the conversation's `goals/` folder, so goals stay with the conversation and never land in a project checkout. `ai-role launch` reads its key from the `dev-platform-perplexity` secret the launcher hands in (stored once with `ol-login perplexity`) and passes it only in the Pi process environment; live search remains unverified until that item exists. Every role also loads `web_fetch` (`integrations/pi/web-fetch-tool.mjs`): a keyless reader for one public page, which refuses local and private addresses at each redirect hop.

Pass `historyArchive` as an absolute preservation-directory path to expose the
`agent_history` tool. The embedded tool binds the role from the conversation,
ignoring inherited `AI_AGENT_ROLE` and `AI_HISTORY_ARCHIVE` values. Without an
archive argument, history is unavailable rather than silently discovered. The
standalone `history.ts` extension continues to require both explicit environment
variables. Neither path reads a live OpenClaw database or needs its process.

`node integrations/pi/check-role-history.mjs` exercises the actual registered
tools and CLI against three real SQLite fixture stores: correct original text,
conflicting inherited values, rejection of another role's session ID, and
unchanged archive bytes. A separate read-only check against the actual preserved
main/hermes/ops databases also completed find/windows/read for each role with
unchanged SHA-256 hashes and no private content printed. This is tool routing,
not OS isolation: same-user shell access can still read accessible files. It also
does not prove an authenticated model selects relevant memories correctly.

`node integrations/pi/check-role-context.mjs` verifies all five role/scope combinations from two unrelated invoking directories using the installed Pi loader. It demonstrates context selection and paths, not authenticated execution, native resume, account selection, process ownership or OpenRig integration. Host-native account-service integration is the current target; container experiments are optional backend evidence.

## Persistent role sessions

`integrations/pi/role-session.mjs` constructs a real Pi `AgentSession` using the
explicit role resources. Its caller supplies the already selected `modelRuntime`,
model and account reference; it does not choose credentials, infer login identity,
or create a second account service. The reference is an association, not proof of
authenticated account identity.

New native transcripts use `conversationHome/native/pi`. A native custom entry
records the conversation ID, role and account reference. Resume requires an exact
existing file in that directory, matching stored association and workspace.
Unbound historical Pi transcripts need a deliberate adoption procedure; this
component does not silently relabel them. An account change needs an explicit
handover rather than changing the stored reference behind an active session.

`node integrations/pi/check-role-session.mjs` runs the real SDK offline, writes
a native fixture transcript using Pi's APIs, resumes its original message, checks
account/conversation/outside-path rejection, and confirms existing bytes remain
unchanged. Fixture assistant text is not an inference result. Pi delays creating
the transcript file until an assistant message exists; an empty session object
does not establish persisted history.

This component is not yet the terminal launcher. The launcher must hold exclusive
writer ownership while resuming a file, connect the verified account selection,
and handle native TUI new/resume/fork/import transitions without losing the role
and conversation bounds. Authenticated inference, terminal interaction and
concurrent-writer/recovery acceptance remain open. Do not expose an unrestricted
native TUI around this factory and assume those transitions are already governed.

`lib/ai_ecosystem/pi_launch.py::exec_conversation` provides the POSIX writer
boundary for that launcher. A dedicated launch process acquires a nonblocking
`flock` on the conversation's persistent `.pi-writer.lock`, then replaces itself
with the selected absolute runtime executable. The descriptor survives exec;
there is no supervisor daemon or PID ledger. Never delete the lock file to
recover: process termination releases the OS lock. `DEV_PLATFORM_PI_LOCK_FD`
identifies the descriptor for the launched runtime; keep it open for its lifetime.

`tests/test_pi_launch.py` checks real Python-to-Node exec, competing launch
rejection, normal exit, forced-crash recovery and failed-exec cleanup. This
primitive is not yet wired into a public terminal command. Direct SDK callers
can still bypass it, so the session factory alone does not guarantee exclusive
ownership. The lock is cooperative and local to a filesystem that supports POSIX
flock; it is not a distributed coordination protocol for future remote swarms.

`integrations/pi/role-runtime.mjs` connects the session component to Pi's native
`AgentSessionRuntime`, the host expected by its native terminal UI. `/new`,
`/resume` and `/fork` reconstruct the same explicit role resources. Resume
reapplies the conversation's native session directory instead of retaining Pi's
default-directory fallback; an unpersisted fork retains its native ID, branch
and association. The native before-switch event rejects outside or unbound
resume/import targets before the current session is replaced.

The offline session check exercises those native lifecycle operations and verifies
the original transcript stays unchanged. It does not render the terminal, supply
a verified account environment, restrict native model/login menus or connect the
OS writer lock. Those remain launcher acceptance requirements. No replacement
TUI or custom branching/transcript format has been introduced.

## Native terminal boundary

`integrations/pi/role-terminal.mjs::runRoleTerminal` opens Pi's own
`InteractiveMode` using the bound runtime. It requires a real terminal and the
inherited launch-lock descriptor matching this conversation's lock file. The
descriptor check confirms wiring, not an unforgeable same-user security boundary;
the Python exec launcher must acquire the actual OS lock first.

`python3 -B integrations/pi/check-role-terminal.py` performs that real exec/PTY
chain with a temporary home, empty auth store, explicit offline mode and no
prompts. It observes native rendering of the `/develop` context, role workspace
and Perplexity extension, exits with native Ctrl+D, then reacquires the same lock.
The check invokes the actual terminal implementation rather than a fake terminal.

This connects terminal rendering and writer ownership in the tested path. A
user-facing command still needs to resolve a real conversation, identity and
verified account through the account service. Authenticated inference, protected
search credentials, real account attribution and management of model/login menu
choices remain open; the offline fixture's account reference is explicitly fake.

## Role launcher

`bin/ai-role` is the account-bound consumer of the components above. `ai-role plan
<conversation-id>` prints what a launch would do; `ai-role launch <conversation-id>`
performs it in an interactive terminal. The conversation comes from `ai-session
conversation create`; the account is `--account` or the registry's selected account;
the Pi profile is the host account service's `accounts/pi/<account>` directory and
must report `configured` through the existing read-only native check. The role
identity is `~/.local/share/dev-platform/agents/<agent>/identity.md`, falling back to
the platform's `agents/<agent>/identity.md`. The model is `--model` or the profile's
saved default for that provider.

The launcher refuses inherited provider overrides, missing identities, unconfigured
profiles, and resume files outside the conversation's `native/pi` directory. It
prints one session header (agent, scope, cwd, model, account, rig binding), acquires
the conversation writer lock with `pi_launch.exec_conversation`, and execs Node on
`integrations/pi/role-launch.mjs`, which builds Pi's model runtime exactly as Pi's own
entry does and starts `role-terminal.mjs`. The plan carries no credentials; the Node
entry reads only the profile directory Pi itself would read.

Attribution stays honest: the plan records the account and the Pi profile state with
`identity: unverified`. A Pi sign-in is a separate native login from that account's
Codex or Claude binding; the launcher does not claim they are the same identity or
share quota. `tests/test_role_launch.py` covers the plan rules and a real offline PTY
launch through the lock boundary with a synthetic profile. An authenticated Engineer
launch with inference is a user-run acceptance step, not something these tests claim.

## On dev-server

The roles run in Pi again (owner's decision 2026-10-05), each as its own Linux user
inside its memory cap, through the machine's one launcher:

```text
OL_MODEL=pi agent assistant                  # or the ai menu: Assistant > In Pi > Which Pi account?
OL_MODEL=pi:gpt-6 OL_ACCOUNT=openai agent ops
OL_MODEL=pi agent engineer ~/dev/x -- --conversation REF [--resume FILE]
```

- `agent-run` (root) resolves the account with the one resolver (`ai-account
  resolve --client pi`), hands the session a private copy of the Pi login (taken
  back, refreshed, when it ends) or, for OpenRouter and z.ai, the API key as the
  `pi-key` credential, plus the tools' secrets (web search).
- `ol-pi` (as the role) picks the conversation, resumes its latest native session
  on this account, and says so when a rotation starts a new one: a native Pi session
  belongs to the account it started on.
- `ai-role` then runs as before, with `--account --provider --agent-dir` instead of
  a registry and profile of its own, the identity and memory under `/home`, the
  journal read-only and additions in `/home/owner/inbox`. `ai-role turn` takes one
  message on stdin and prints the answer (the shared chat, when
  `/etc/dev-server/chat-model` says `pi`).
- Each role starts on its model in the one model file: the `<role> start` lines that `pstack-model resolve "<role> start" --runtime pi` reads (`/etc/dev-platform/pstack-models.md`, edited in dev-server's `etc/pstack-models.md`). Any provider Pi knows can
  drive a role by naming its account.
- Conversations live in the role's `~/.local/state/dev-platform/sessions`, where
  ai-session indexes them; several can run at once, one writer each.
