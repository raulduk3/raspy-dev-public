# Runbook: an incident

Read-only first. Every mutation is a decision the owner makes in the session, then performs or authorizes explicitly.

## 1. Observe

1. `/health` and `status` on the affected deployment: version, build reference, capability readiness, execution gates, worker health.
2. The last deploy record and the deploy log: what changed last, when, by whom.
3. Container state and the last 200 log lines. Provider dashboards, read-only.
4. Open issues and pull requests that touch the area.

Write down the timeline as observed, with timestamps and sources, before touching anything.

## 2. Decide

State the hypothesis, the smallest action that tests it, its blast radius and its rollback. File it as a `decision` issue or say it in the session. The owner decides.

## 3. Act, once authorized

- Rollback is a tag flip to the previous release; never a rebuild, never a hand edit on the host.
- A restart is a restart of one service, after an active-interaction check.
- A configuration change goes through the repository (pull request, deploy), not the host, unless the owner authorizes a hand change and it is recorded in the deploy log with its reversal.

## 4. Record

One deploy-log row per action. An issue for the root cause with the timeline. A decision record if the fix changed behavior. Nothing in memory files or chat only.
