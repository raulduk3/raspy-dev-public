---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
---

# Reflect

Mine the current conversation for durable learnings, then route them into skill edits.

## When to invoke

Invoke when the user says "reflect" or "/reflect". Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## Process

### 1. Locate the active transcript

The parent finds its own transcript before fanning out. Use the session history your agent keeps natively (its resume or history feature, or the transcript file it names for the current session). Stay inside the current project's history. Do not search across other projects' transcripts: that reads private chats from unrelated work.

If several candidates exist, open each and check that its first user message is this conversation's opening prompt. Take the matching path. If no path resolves, write a tight digest of the session and pass that instead.

### 2. Spawn three reviewers in parallel

Spawn three subagents at once, in parallel, with full tool access rather than a read-only mode. Reviewers need MCP access for context lookups (tickets, chat threads, observability traces referenced in the transcript), and a read-only mode may strip MCPs.

Each reviewer and the synthesizer names a tier. Run it on the model that `models.md` (the tier map at the root of this skills repository) assigns to that tier. If the file or the tier is missing, use the model you are running on and say so.

| Lens | Tier | Prompt template |
|---|---|---|
| Judgment | judgment | `references/judgment-reviewer.md` |
| Tooling | judgment, on a different model from the other two when `models.md` lists one | `references/tooling-reviewer.md` |
| Divergent | judgment | `references/divergent-reviewer.md` |

Pass each template verbatim, substituting the transcript path or digest where marked. Reviewers return findings in their final response.

### 3. Synthesize

One subagent on the **judgment** tier, with full tool access. The synthesizer's quality check includes spot-verifying citations, which can require MCP access, and a read-only mode may strip MCPs. Use `references/synthesizer.md` verbatim, with each reviewer's full output inlined where marked. The synthesizer returns a structured Accepted / Rejected / Backlog list.

### 4. Structural enforcement check

Sanity-check the synthesizer's Accepted list. For any item that would be enforced more reliably by a lint rule, script, metadata flag, or runtime check, move it from Accepted to Backlog. See the **encode-lessons-in-structure** principle skill.

### 5. Apply

Before applying any Accepted edit, present the synthesizer's full Accepted/Rejected/Backlog output to the user and wait for explicit approval. The user picks which subset to apply and may redirect routings. Skill changes affect every future agent in the org. Do not auto-apply.

Backlog items file to whatever devex / backlog tracker your team uses automatically. Only the Accepted list waits for approval.

For each approved Accepted item, follow the Routing field exactly:

- Trivial existing-skill edit (a one-line bullet, a tightened sentence, a stale fact corrected): parent does directly.
- Substantive existing-skill edit (a new section, a new pattern table, more than ~10 lines): run a draft / test / iterate loop, using your environment's skill-authoring workflow if it has one.
- `tune description: <skill path>` (the skill exists but didn't trigger when it should have): rewrite the description, then test that it triggers on the transcript's request and not on unrelated ones.
- `new skill: <kebab-name>`: create it in the Agent Skills format (`<name>/SKILL.md` with `name` and `description` frontmatter), through your environment's skill-authoring workflow if it has one. Do not invent the shape ad hoc.

If your environment ships a SKILL.md validator, run it on every touched skill before declaring done. Skip this step if it doesn't.

### 6. Summarize for the user

Short list, no preamble:

- Edits applied: `<skill path>`. What changed, one line each.
- New skills created: `<skill path>`. One line each (rare).
- Backlog filed to the devex tracker: `<issue title>` (`<tags>`). One line each.
- Dropped: one line per rejected finding + reason from the synthesizer.
