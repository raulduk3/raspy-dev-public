# Shared session contract

Status: target contract for the Pi migration, incorporating the owner's 2026-09-24 correction. Existing runtime storage has not been moved and these launch rules are not yet enforced. Session coherence precedes fleet expansion. OpenClaw has since been retired and is no longer used.

## Three durable concepts

1. **Agent identity:** Assistant, Engineer or Ops. Stable instructions, relevant memory and available capabilities. An identity can participate in many conversations; it is not a terminal, account or project.
2. **Conversation:** one continuing interaction with an explicit scope and a stable ID. It has one filesystem home, a short checkpoint, and references to its native sessions. Changing windows, accounts or runtimes does not by itself change that scope.
3. **Native session:** the runtime-owned history and resume identity in Pi, Claude, Codex or a retained historical tool. A conversation may contain successive native sessions and linked worker sessions. Their branches, compactions, tool results and native IDs remain intact.

A task or issue is linked existing work, not another session. A Rig seat is a stable execution address whose occupant may change. A tmux pane is a terminal endpoint. An account is a verified execution attribute. None is interchangeable with the conversation ID.

Use the existing session index for native records and the existing project catalog for projects. Add conversation associations to that index rather than introducing another database, task queue or dispatcher. GitHub and the active engineering coordinator retain their existing work ownership.

## Scope by agent

| Agent | Conversation scope | Execution directory | Automatic context |
| --- | --- | --- | --- |
| Assistant | Personal, with optional references to projects | A neutral, controlled runtime directory; never the invoking shell's directory by default | Assistant identity, current conversation checkpoint, selected personal tools; relevant records retrieved on demand |
| Engineer | Exactly one primary project or project-formation workspace | An explicitly resolved project directory or selected worktree | Engineer identity, repository instructions, current handoff and development-workspace entry point |
| Ops | An explicit operational scope, initially this machine/system; alternatively one project | Neutral runtime directory for system work; resolved project/worktree for project work | Ops identity, scope-specific tools and current checkpoint |

Assistant is project-independent, not storage-free. Its process necessarily has a cwd, but that directory must not define its identity, conversation scope or implicitly loaded repository instructions. Explicitly configure Pi's resource loader; changing session storage alone does not prevent cwd-based context discovery.

Engineer can work anywhere on the filesystem, including before a Git repository exists. A formation workspace has an explicit catalog identity and real directory. Creating a repository later updates its binding rather than discarding its earlier conversations. Linked worktrees share project identity; each execution records its own actual cwd. Missing or ambiguous context prevents worker launch, with an actionable explanation.

Ops's initial experiment has two modes: system operations and project work. Reading a file outside its scope does not reclassify the session or grant write authority. A change of primary scope starts a linked conversation and leaves a handoff. System sessions can reference several affected projects without being filed under a randomly selected one.

## Filesystem layout

Retain the current root and add one conversation namespace:

```text
~/.local/state/dev-platform/sessions/
  conversations/<conversation-id>/
    session.json                 # identity, scope, native record references, lineage
    handoff.md                   # goal, verified progress, running work, next action
    native/pi/                   # new Pi native sessions via explicit session directory
  manifests/<native-record-id>.json  # existing index, extended with associations
  handoffs/<native-record-id>.md     # existing per-native handoffs retained
  events/                          # existing index events
  sources.json                     # source observations, including scan failures
```

One canonical home per conversation. Project and agent screens are filtered views of these records, not extra transcript copies. A project path may move; a conversation ID must not change. Personal transcripts stay outside repositories, especially professional repositories.

Agent identity files live separately under `~/.local/share/dev-platform/agents/<agent>/`. Account credentials live in their protected native profile stores, separately from conversation folders. Workspace and repository files remain in their actual locations. The vault remains the journal/document store, not a second transcript database.

New Pi conversations explicitly select `native/pi/` as the session directory. Native Claude/Codex histories remain where their supported runtime APIs require them; the shared index records exact locators and native IDs. Do not relocate a live database or pretend a central index physically centralizes every tool's internal storage. Preservation exports are immutable evidence, not alternate live histories.

The current native index ID includes a hash of the native store path. Migration therefore needs explicit original-to-current locator aliases; it must not silently rescan a relocated archive as unrelated new history. Keep existing index IDs and original provenance, and add stable source identity before generalizing relocation support.

## Minimal shared metadata

Conversation manifest: schema version, stable conversation ID, agent, title, scope, creation time, related conversation IDs with relation type, and indexed native-session references. The manifest is authored association data and must be backed up; native transcript scans alone cannot reconstruct it.

Scope: `personal`, `system` with a resource identity, or `project` with a catalog project ID. Actual cwd belongs to execution, not to the durable identity. Assistant's project links are references rather than a primary scope.

Extend native records only with the necessary binding: conversation ID, relation (`primary`, `worker`, `successor`), predecessor where applicable, and execution observations. Existing native runtime/store/ID/source fields remain authoritative for native identity. Execution observations include cwd, runtime owner, account verification status/time, and, when managed, host/Rig/seat/occupant identifiers. Account secrets never enter metadata.

Unknown means unknown. An inferred match by title, cwd or timestamp is a candidate association, not an authoritative one. New launches write associations directly; older records remain unassigned until supported by evidence. Scans must preserve authored associations and handoffs.

## Engineer and OpenRig

The Engineer integration resolves conversation -> project -> working directory -> Rig binding. OpenRig receives ordinary project/runtime configuration and opaque correlation identifiers. Its core does not need hard-coded knowledge of Engineer, personal agents or this four-account pool.

A project Rig can outlive an Engineer chat and serve later conversations. A conversation binds to the relevant Rig and work, but does not necessarily create a new Rig. Pausing or closing the chat leaves worker lifecycle explicit; it must not silently stop work or permit a second coordinator to start it again.

Before worker dispatch, the integration resolves the current Rig seat/occupant, available account profile, actual worktree, and current coordination owner. The account service provides verified native profile selection for new execution; Rig owns supported seat and messaging operations. The TUI is the human control surface. Account transitions checkpoint and record predecessor/successor execution; no repeated chat prompting is required.

Messages use the live seat/occupant binding. Record delivery separately from acknowledgement; a pane write is not proof the intended agent acted. A restarted tmux pane is not proof the former native session resumed. OpenRig's continuity outcome and seat-binding outcome remain separate, as its installed handover contract requires.

Focused native windows join the same conversation/project through explicit binding. Discovery alone does not adopt a Desktop session into tmux or transfer control. One runtime owns each execution; one coordinator owns each delegated task.

## Shared reading and lightweight discipline

Provide a common reader envelope: source/native session ID, event ID or sequence, timestamp when available, role, event kind, content and lineage. Preserve runtime-specific payloads and source locators. Order within a native session by its native sequence/tree; across sessions use an explicitly approximate timestamp view plus causal links. Do not flatten Pi's branch tree into a falsely linear conversation.

Context loaded at boot is small: identity, selected scope, current checkpoint, and a tool/skill index. Retrieve history and skill bodies only when relevant. A brief session header shows agent, scope, cwd, runtime, verified/unknown account and Rig binding. Launchers and adapters enforce these bindings; prose reminders are not the enforcement mechanism.

Reconcile on launch/resume and before state-changing control; record lifecycle events as they happen. A read-only scan discovers native sessions opened outside the launcher. Surface drift and orphaned records instead of inventing ownership. Do not build a new polling daemon merely for presentation.

## Lifecycle checks

- Launch Assistant from two unrelated repositories: both produce personal scope, neutral cwd and no inherited repository context; explicit new conversations remain distinct.
- Resume Engineer from another shell folder: recover the bound project and native session; do not reclassify by the new shell cwd.
- Select another worktree: preserve project/conversation association and record the actual execution cwd; never create a second writer through an implicit resume.
- Change project: create a linked conversation, preserve the previous home and leave a handoff.
- Change account/runtime: retain conversation, record real native continuity and new execution attribution; never claim cross-runtime context identity.
- Recreate a terminal: preserve the conversation and stable seat; verify the new occupant separately.
- Restart the machine or later migrate to Omarchy: restore IDs, native sources and bindings; rebind host paths explicitly and reverify live execution.
- Lose access to a source: show unavailable/stale, not deleted/completed; preserved histories remain readable.

## Implementation order

1. Land scope/association schema and preserve it through existing index scans. Add Pi discovery and source-locator continuity without renaming native histories.
2. Build the thin role launcher with explicit storage and resource loading. Prove Assistant context isolation, Engineer project enforcement, and Ops's two modes using real Pi sessions.
3. Link Engineer to existing Rig/project/seat identities and account-service observations; verify tmux/native sessions and message acknowledgement. Finish unsupported adapter behavior before claiming account rotation.
4. Backfill evidenced historical relationships; expose unassigned records for review. Verify every retained source through the common reader and restore procedure.
5. Run the lifecycle checks across real Claude/Codex/Pi execution.

## Evidence inspected

- Local `lib/ai_ecosystem/{store,sessions,workspace}.py`: existing filesystem index, native IDs, resumption and cwd-based project grouping.
- Pinned Pi 1.5.0 (was 1.0.4 and 0.87.1; session format version 3 in those two) `docs/{sessions,sdk}.md`: explicit session storage, cwd/resource discovery, native tree and runtime replacement behavior.
- Installed OpenRig 0.5.14 `rig context get skills/seat-continuity-and-handover`: stable seat identity, occupant lineage and separate binding/continuity outcomes.
- Owner's current session-scope requirements take precedence over the retired OpenClaw routing conventions.
