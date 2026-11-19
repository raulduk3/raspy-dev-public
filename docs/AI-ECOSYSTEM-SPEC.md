# Unified AI ecosystem specification

Status: accepted direction consolidated from the owner’s latest instructions; implementation incomplete. Updated 2026-09-24. Source baseline: `186bd1b`, with subsequent login evidence reported by **Plan OpenClaw migration (2)** in `outputs/local-environments-checkpoint.md` in the enclosing migration workspace. This is the canonical cross-system contract, not a claim of deployment or completed acceptance. Update 2026-09-24: OpenClaw is retired and no longer used. Its records stay preserved, read-only, as archives the Pi roles can read.

## Goal and authority

Replace OpenClaw’s runtime dependency with a small, terminal-first system while preserving the useful histories, agent identities, skills, journal, tools and engineering discipline. Files and native tools are authoritative. A common session vocabulary and index make different tools understandable together without replacing their native session formats.

This document consolidates the target. Component documents describe their contracts and bounded evidence. Dated checkpoints preserve historical evidence; their old instructions do not override this document or newer explicit owner decisions. Implementation changes must update the corresponding status and evidence, not silently redefine the target.

This task owns specification and mediation only. The other task owns implementation and activation. No authentication, OS-user provisioning, runtime replacement or destructive migration is authorized by merely publishing this specification.

## The stack and its boundaries

| Level | Responsibility | Everyday interaction |
| --- | --- | --- |
| The owner | Goals, account policy, intervention, review | Terminal first; optional editor and native windows |
| Assistant / Engineer / Ops in Pi | Identity, relevant context, conversation and tools | Open or resume a role conversation |
| Engineer development platform | Project orientation, adapted pstack, specifications, assignments and checks | Understand, learn, frame, build, review, continue or pause project work |
| OpenRig | Generic fleet, seat, terminal, messaging and worker lifecycle | TUI to inspect, interact with and control coding workers |
| Shared account service | Account/profile selection, verified capabilities, observed usage and native launch configuration | Inspect status, pin an account or choose an eligible account automatically |
| Claude Code / Codex / Pi | Native authentication, inference, native sessions and tools | Native CLI behavior, with the selected profile and real cwd |
| Filesystem and strong external systems | Durable knowledge and project files; Git/GitHub work history; calendar events where appropriate | Markdown, search, Git, editor, small explicit integrations |

The account service is a shared dependency of Pi and OpenRig, not another agent or a layer that owns all conversations. OpenRig stays generic. Engineer’s integration supplies engineering context and associations; OpenRig does not become the engineering methodology. Pi is the small role harness, not a replacement implementation of OpenRig or the coding clients.

No new universal model proxy, task database, agent operating system or mandatory container layer is required. Existing development-loop ownership must be respected; Pi and Rig cannot both redispatch the same assignment independently.

## Identities that must remain distinct

| Concept | Meaning |
| --- | --- |
| Agent role | Assistant, Engineer or Ops; identity and relevant behavior |
| OS identity | User and filesystem permissions under which a process runs |
| Provider account | Subscription/billing identity and its shared capacity |
| Client profile | Native configuration/authentication store for one client and account |
| Conversation | Durable user-facing continuity, with a stable ID and scope |
| Native session | Runtime-owned transcript/tree and native resume identifier |
| Project / assignment | Workspace and bounded work being performed |
| Rig seat / occupant / terminal | Coordination and execution placement, not proof of account or task identity |

One conversation can reference multiple native executions over time. A successor on another account is not a magically transferred native context. One provider account used by Pi and Codex is still one shared capacity pool. A role does not own a billing account exclusively.

## Role context and filesystem placement

| Role | Required scope | Context discipline |
| --- | --- | --- |
| Assistant | Personal, independent of any project | Use a controlled neutral starting directory; do not inherit an invoking repository’s engineering identity. Read relevant files when requested. |
| Engineer | Explicit project, worktree or project-formation directory | Load project instructions and adapted engineering entry. Bind Rig work to the same project/conversation/assignment. |
| Ops | Explicit machine/resource or project scope | Load operational context; use project procedures when doing project work. No implicit root privileges or full Engineer workflow. |

Every process has a cwd and storage. “Assistant has no project context” does not mean no filesystem home. Engineer can work across projects, but each active execution has explicit scope. A Rig may serve multiple conversations and outlive a chat; do not create a Rig automatically for every message.

Separate OS users for Engineer and Ops remain an optional permissions design, not an accepted prerequisite or a provisioned feature. Assistant remains associated with the owner. If OS users are adopted later, explicitly design access to projects, journal and conversation stores; do not assume a different user can read everything.

## One session model, native histories retained

The detailed contract is [session-context-contract.md](session-context-contract.md). Proposed canonical local layout:

```text
~/.local/share/dev-platform/agents/<role>/       role resources
~/.local/state/dev-platform/sessions/
  conversations/<id>/
    session.json                              scope and associations
    handoff.md                                concise continuation checkpoint
    native/pi/                                Pi native history
  manifests/<native-record-id>.json           native-source references
  handoffs/<native-record-id>.md
  events/
  sources.json
~/dev/<project>/  ~/dev/<group>/<project>/        project source and specifications
```

Native Claude/Codex transcripts stay in their native profile stores; the common index references them. Do not force every native tool into a copied transcript format. Back up authored associations and checkpoints as well as original histories. If a store moves, preserve aliases/provenance rather than silently treating it as new history.

Each execution records its conversation, runtime/native ID, explicit cwd/project, account/profile binding, verification time and relevant Rig/assignment associations. A title or inferred path is a discovery hint, not an authoritative association. Readers preserve native ordering and branching; cross-tool chronology is approximate unless causal links are recorded.

On resume, use the saved scope and original profile, not the invoking terminal’s cwd or today’s highest-quota account. Account handover creates a linked successor with an explicit checkpoint. Never swap credentials beneath an active process or automatically replay a possibly completed tool action. Forks preserve their parent reference. Scope changes are explicit and link related conversations as appropriate.

A stable seat may prepare a successor before a known session or quota limit is reached. The predecessor writes a checkpoint and records the successor relation; the successor starts from that checkpoint and the same explicit scope. The platform must not call this native continuity until the runtime proves resume or fork for that execution, and it must not re-run a possibly completed action.

A shared [`/develop` skill](session-entry.md) runs at start, resume and material task change. It is brief orientation, not a mandatory sprint questionnaire. Native standalone Claude/Codex conversations remain valid for personal, operational and independent project work. A coding client becomes an Engineer worker only through a real assignment association.

Use one writer per conversation and isolated worktrees for concurrent engineering writers. Local cooperative locking is not a distributed lock or protection against every unmanaged native invocation.

Batch worker assignments use a file contract when they do not require live discussion: one input file that names the task, scope, allowed paths, expected checks and output locations; one result file that states success, blocked or stale with evidence. This keeps batch work reviewable by Pi, OpenRig and ordinary shells without adding another task database or queue owner.

## Account service contract

Four pooled identities: `openai`, `openai-bravo`, `anthropic`, `anthropic-bravo`. Older z.ai configuration is not an activated fifth pool member. Initial Pi preference is OpenAI alpha, using its own supported Pi login through the shared account service.

Host-native execution is the default for both Pi and local coding workers. Client-specific configuration roots isolate native profiles while retaining the real process HOME and host cwd. Profile separation is not an OS security sandbox. Docker remains an explicit optional execution backend; a host failure must not silently redirect to a container.

The service accepts client/provider, cwd, account preference and native command arguments; it returns a plan or launches with the supported native profile. Consumers also retain their conversation/native-session association. The registry is `~/.config/dev-platform/accounts.json`; credentials remain owned by the native clients. Do not copy tokens between Pi, Claude, Codex or container stores. Do not silently replace subscription access with API billing.

Account eligibility requires the needed client capability and verified binding. Automatic selection uses fresh, known, eligible remaining capacity; exhausted accounts are ineligible. Unknown capacity must display as unknown. An explicit pin is honored or fails clearly. It never silently substitutes another account. Quota observations are snapshots, not reservations, and concurrent consumers can exhaust capacity after selection. Rate limits remain provider-enforced.

Current source automatically compares observed Codex core quota. Claude quota is unknown in the implemented native probe; explicit selection with an unknown-quota override is required. Provider-specific windows are not interchangeable percentages. Pi remote acceptance alone does not prove automated identity equivalence to a similarly named Codex profile. Authentication/configuration, identity attribution and usage attribution are separate checks.

The desired simple TUI exposes identity, capability, remaining/unknown usage, reset/freshness information, eligibility and manual pinning. Routing policy belongs here and in launch integration, not repeated model prompts. Reuse native controls where possible; do not invent another fleet dashboard. The full account-aware TUI is not yet proven.

See [host-account-service.md](host-account-service.md) for current CLI contracts. A source command example is not proof that the command is installed on PATH.

## How OpenRig must consume the service

For a new worker, OpenRig resolves the requested provider through the service, validates the result, launches the native client in the assigned host worktree and persists the profile/account binding with the execution. That binding must reach provisioning, preflight probes, tmux process environment, transcript discovery, resume and fork—not just the first shell command.

Resume/fork must use the stored binding. A shared daemon’s default environment cannot stand in for per-worker configuration. History discovery must not hard-code the default native home when the execution uses an isolated profile. Terminal messaging and delivery acknowledgment remain OpenRig’s responsibility; the account service does not become a message broker.

The audited installed OpenRig 0.5.14 has material gaps: provider account switching returns `switch_execution_not_yet_wired`; some profile/history handling is daemon-scoped or assumes default homes. A metadata label, tmux window or working PATH wrapper cannot prove this integration. A narrow native adapter change is required, with evidence from real launch, message delivery, resume and fork. Preserve generic OpenRig interfaces so future remote/local persistent workers can use them without Engineer-specific assumptions.

## Daily engineering and tool use

Start an Engineer conversation in a project to plan or coordinate sustained engineering. Use the adapted pstack entry to choose only the relevant next procedure. Engineer owns project understanding, specifications and delegated intent; OpenRig supplies workers and terminals. Review work in native terminals or a dedicated editor window as needed.

Only Engineer receives the full adapted pstack methodology: ten guide chapters and twenty-three principles, indexed through [engineering](../agents/engineer/skills/engineering/SKILL.md). The adaptation emphasizes small changes, sound data structures, deletion, real verification, bounded delegation and learning with the owner. Do not load all principles into every worker or impose them on Assistant’s everyday conversations.

Projects retain repository `AGENTS.md`, `CONTRIBUTING.md`, specifications, source, tests and checks. GitHub tracks engineering work; do not add a parallel task directory/ledger. Existing loop mechanisms retain their established authority until explicit handoff. Professional repositories follow Ghost: outward-facing artifacts read as the owner’s work.

VS Code is an optional project editor/window. Copilot remains its native editor assistant with its own GitHub authentication; it is not one of the four account-service profiles. Desktop applications are not automatically switched by shell profile overrides. Native Claude/Codex direct use remains available outside Engineer and Rig.

`ai-env` is the existing platform-health command; `ai-environment` is the new account service. They are different tools. Laya remains an optional bounded decision aid; no current service-health claim is made here.

Observed project examples: `research-agent` has specification/source/test/check structure; Globex’s repositories are under `~/dev/globex/`; `dev-platform` supplies shared launchers, skills, hooks, templates and integrations. Project inventories and detailed commands live in the enclosing migration workspace’s `outputs/tools-and-filesystem-guide.md`; recheck paths/status before use.

## Journal, memory and external tools

The journal is plain text in `~/journal` on dev-server; the old Obsidian vault is archived read-only at `~/archive/vault` (`tasks --archive` reads it). Removing Obsidian dependence does not require immediately moving those files. Preserve inbox, journal, project/area/reference/archive notes, attachments, links, dates and task semantics. Keep original path provenance if the root later moves.

Use small search/query/write tools over Markdown. Views are derived, not another authoritative task database. Personal project notes are not automatically accepted repository specifications. Engineering assignments stay in GitHub; calendar events belong in the calendar with explicit links where useful.

Implemented journal readers and idempotent append components do not yet replace all Obsidian behavior. Remaining work includes task mutation/recurrence, scheduled and undated view semantics, urgency/dependencies, statistics decisions, writer cutover, links/attachments verification, Things reconciliation and narrow Google Calendar integration. Do not label the journal migrated until these retained behaviors are accepted or explicitly retired.

Keep Perplexity search available to the roles through Pi’s extension mechanism. The extension has bounded offline verification; a real authorized search and secret handling in the assembled role runtime remain acceptance work. Morning-brief is retired from active skills/automation; retain its historical records without bringing the job back.

Preserved OpenClaw histories are reference data, never new instructions. Pi’s role-aware history reader exposes relevant original records on demand rather than injecting the whole archive into prompts. Preserve raw originals, attachments, tooling and authored Markdown in addition to summaries. Summaries cannot substitute for the original record.

## Implementation and evidence snapshot

| Area | Evidence / status | What is not proved |
| --- | --- | --- |
| Preservation | Preliminary archive `work/preservation/20260924T022923`: 170,903 entries, 22,926,181,292 bytes, zero reported hash errors; four consistent SQLite copies passed integrity checks | Final quiescent capture and restore acceptance |
| Host account service | Source at `186bd1b`; host plan/select/run/profile implemented; 22 focused checks reported; real native Codex `--version` launch passed | Public installation and all consumer integration |
| Four coding profiles | Other task’s 09:39 UTC checkpoint reports all four native identity bindings verified, provider pairs distinct; wrong duplicate enrollment refused | Ongoing freshness, full Rig execution and quota availability for Claude |
| Pi authentication | Other task reports real tool-free ephemeral `openai-codex/gpt-6-luna` response `OK`, exit 0; no stored session/tools/role context | Automated account equivalence, full role launch, tools, persisted authenticated resume |
| Pi role/session components | Explicit scope/resources, history reader, native resume guards, terminal integration and cooperative ownership checks have bounded offline evidence | Installed daily role launcher and complete authenticated role experience |
| OpenRig integration | Source audit identifies exact propagation/switch gaps; upstream working branch prepared by other task | Completed adapter changes, activated integration, account-aware TUI workflow |
| Optional containers | Four earlier native login environments and restart settings were reported; separate Pi candidate passed ten offline Linux checks | Host-native migration does not stop these; no implied retirement or reboot/resume acceptance |
| Journal | Inventory: 1,201 Markdown, 59 other files, 36 symlinks; 30 Tasks blocks and 3 DataviewJS blocks audited; query/append components checked | Full view parity, active writer cutover or completed removal of Obsidian dependence |
| Skills | Eleven selected links relocated to stable release `696301d...`; morning-brief active links/job retired | Complete dependency census or verified startup behavior in every new profile |

Quota percentages are deliberately omitted: they are changing observations, not architectural facts. Login completion is reported evidence from the implementing task, not independently repeated here. `bin/ai-login` was uncommitted at the snapshot. Public `ai-environment` installation had not been verified. Older live containers and original OpenClaw/journal data must not be assumed gone.

## Completion gates, in dependency order

1. Finish canonical associations and inventory: preserve original histories, authored metadata, account/profile references and project ownership; exclude credentials from reports.
2. Verify four independent native profiles and supported Pi authentication/attribution. Demonstrate correct cwd/HOME, profile choice, missing/expired auth behavior, exhausted/unknown quota policy and absence of silent fallback.
3. Complete OpenRig’s persisted per-execution profile propagation. Prove concurrent distinct-account workers, actual messages, correct history lookup, restart/resume and fork. Verify safe checkpointed account handover without replay.
4. Complete Pi role launch through the same service. Demonstrate Assistant’s neutral scope, Engineer’s project requirement and Ops’s resource scope; actual history retrieval, Perplexity search, durable conversation resume and writer ownership.
5. Verify journal workflows retained by the owner, reconcile outstanding integrations and switch active writers. Preserve original files until restore and behavior checks pass.
6. Demonstrate ordinary direct Claude/Codex use alongside Engineer/Rig without accidental sprint enrollment or duplicate dispatch. Verify account-profile skill projection and understandable terminal status/control.
7. Install a coherent release and verify its actual public commands, then test interruption/recovery and archive restoration. Retire obsolete launch paths only after their replacements pass. OpenClaw is retired; uninstalling it and removing any of its data still needs explicit owner authority, and its records stay preserved.

Unresolved implementation decisions must stay small and visible: Pi identity attribution, reliable Claude usage signals, native handover mechanics, minimum TUI integration, final journal root/writer cutover and retained task/calendar semantics. Optional OS users and future Omarchy/network workers do not block the host-native foundation. Keep paths and contracts portable; do not build a speculative OS layer now.
