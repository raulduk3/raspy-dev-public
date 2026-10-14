# Source playbook

The why skill spawns one investigator per available evidence category. An agent reaches every category except source control through an MCP server configured in the shared `mcp.json`. Read the server's instructions and tool schema before searching; tool names differ between servers. If a server needs authentication and it fails, stop and report the category as a gap. Never invent findings.

Every investigator returns exact quotes (not paraphrases), with an identifier or link, the author or owner, and dates, and marks each item as direct (it addresses the question) or circumstantial.

## Source control history

Always available through git and `gh`. Full playbook: [`code-archaeology.md`](./sources/code-archaeology.md).

## An issue tracker

**Holds:** issues for features and bugs with their motivation, comments, parent and sub-issue links, labels, milestones, attached specs, and linked pull requests. This is where the product or business reason usually lives.

**Search:**
1. Fetch the ticket IDs the seed commits and pull requests cite first, with all comments.
2. Search by feature name, key symbol and business term; try several phrasings.
3. Walk up from a sub-issue to its parent. Parents often carry the why.
4. Read project-level documents and check labels (`incident-followup`, `compliance`, `customer-request`) and milestones.

**Pitfalls:** scope changed after the ticket was written; boilerplate "why" sections; stale tickets (compare dates with the ship date); closed-as-duplicate chains (follow them to the canonical ticket); pages you cannot open (a gap, not a null).

## A wiki or document store

**Holds:** design documents, specs, RFCs, decision records and postmortems written before or alongside the code.

**Search:** search for the feature name, key symbols, the file path and the ticket IDs; open linked pages; prefer the finalized or most recently updated draft.

**Pitfalls:** specs written before implementation and never updated; doc and code disagree (flag the divergence for the synthesizer); boilerplate templates; the most relevant page is linked from nowhere; restricted pages (a gap).

## Chat history

**Holds:** real-time deliberation that never reached a document: design threads, incident channels, reviewer questions answered by the author.

**Search:**
1. Messages from the pull request's author around its merge date.
2. The feature name and key symbols, including casual phrasings.
3. The pull request URL or `/pull/<number>`.
4. Error strings the target code handles.
5. Likely channels: engineering, project, incident, the owning team's channel.
6. Fetch the whole thread for every hit; the decision is often in the replies.

**Pitfalls:** retention limits (name the date before which nothing exists); private messages are not searchable; casual jokes are not decisions; a single message out of its thread misleads.

## Infrastructure observability (metrics, logs, traces)

**Holds:** metrics, monitors and alerts, dashboards, traces, logs and formal incident records. A metric or monitor's existence shows someone cared about that number.

**Search:** monitors and dashboards that name the service or feature; metrics and logs around the target's ship date; incident records in that window. Narrow by service, tag and time, and aggregate rather than dump raw logs.

**Pitfalls:** correlation is not causation (check neighboring changes in the same window); a chart reflects its author's framing; renamed or expired telemetry is a gap, not a null; instrumented is not caused.

## An error tracker

**Holds:** grouped errors with counts, first and last seen times, affected releases, stack traces and comments.

**Search:** errors whose stack traces pass through the target file or symbol; errors whose first-seen or last-seen time lines up with the target's merge date; release records around that date.

**Pitfalls:** grouping changes after renames (the "same" error under a new ID); a release holds many commits, so release correlation is noisy; errors stop for reasons other than the fix; "resolved" is a human marker, not proof; sampling hides volume; generated explanations from the tracker are not evidence.

## A product analytics warehouse

**Holds:** product events, usage and billing events, experiment and feature-flag exposure, and query history.

**Search:** confirm table names first (`SHOW TABLES`, `DESCRIBE TABLE`); then query event volume for the feature or error condition before and after the target's ship date, and flag exposure for flag-gated code.

**Pitfalls:** instrumented is not caused; a step change in volume may be new instrumentation; schemas drift; derived tables refresh on a schedule; retention cliffs are gaps, not nulls; notebooks are often not queryable.

## Cross-cutting

- [`incident-postmortem.md`](./sources/incident-postmortem.md). Add this if the target code looks defensive (null checks, retry, timeout, rate limit, feature flag, egress guard, OOM handler).
