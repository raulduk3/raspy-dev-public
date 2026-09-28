# Software Design Description

What the software must do, stated as requirements a reader can verify.

## Document control

| Field               | Value                                                                                                                                |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Product             | Name of the software.                                                                                                                |
| Target version      | The release this document describes.                                                                                                 |
| Scope               | What the software covers and what it does not.                                                                                       |
| Authority           | This document decides what the software does. Where code and this document disagree, one is wrong; say which, with evidence.         |
| Companion documents | [TDD.md](TDD.md) states how each requirement is met. [SPEC-AMENDMENTS.md](SPEC-AMENDMENTS.md) records each change to either.         |
| Change control      | A pull request cites an accepted decision under `docs/decisions/`, edits the exact lines, and appends a row to the amendment ledger. |

## Normative language

- "must" states a requirement.
- "must not" states a prohibition.
- No other word makes a requirement. A proposal that is not decided is a decision record with `Status: proposed` under `docs/decisions/` (or a `decision` issue where the repository uses an issue tracker) and does not appear here.

## Conventions

- Each requirement is one sentence on a `**XX-nn.**` line: a two-letter area code and a two-digit number.
- A trace comment follows it: `<!-- id: SDD-XX-nn | tdd: TDD-x.y.z | status: ... -->`.
- Bullets follow the trace comment: `Trigger`, `Behavior`, `Observable`, `On failure`, `Verified by`, and `Limits` where numbers apply.
- Status is one of `implemented`, `pending:#N` (decided, not yet implemented) or `deviation:#N` (the code does not yet meet it), where `#N` is the task in `docs/tasks/` (or the issue) that carries the work.

Example, not part of the specification:

```text
**XX-01.** The service must reject a request that carries no credential.
<!-- id: SDD-XX-01 | tdd: TDD-1.1.1 | status: pending:#12 -->

- Trigger: a request arrives without a credential.
- Behavior: the service rejects it before any work is done.
- Observable: the response status is 401 and the body names the missing credential.
- On failure: the rejection is logged once with the request id.
- Verified by: a test that sends a request with no credential and checks the response.
- Limits: the rejection is returned within 100 ms.
```

## 1. First area

No requirements yet. The first accepted decisions add them here.
