# Technical Design Description

How the software is built to meet each requirement, item by item, with the code and tests that carry it.

## Document control

| Field               | Value                                                                                                                                |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Product             | Name of the software.                                                                                                                |
| Target version      | The release this document describes.                                                                                                 |
| Scope               | The design of what [SDD.md](SDD.md) requires, and nothing it does not.                                                               |
| Authority           | This document decides how the software is built. Where code and this document disagree, one is wrong; say which, with evidence.      |
| Companion documents | [SDD.md](SDD.md) states what the software must do. [SPEC-AMENDMENTS.md](SPEC-AMENDMENTS.md) records each change to either.           |
| Change control      | A pull request cites an accepted decision under `docs/decisions/`, edits the exact lines, and appends a row to the amendment ledger. |

## Normative language

- "must" states a requirement.
- "must not" states a prohibition.
- No other word makes a requirement. A proposal that is not decided is a decision record with `Status: proposed` under `docs/decisions/` (or a `decision` issue where the repository uses an issue tracker) and does not appear here.

## Conventions

- Each item is a `#### TDD-<section>.<n> Title` heading.
- A trace comment follows it: `<!-- id: TDD-x.y.z | implements: XX-nn | code: path#Symbol | tests: path or none | status: ... -->`.
- Items are numbered in reading order. A cited item is never renumbered; new items are appended.
- Status is one of `implemented`, `pending:#N` (decided, not yet implemented) or `deviation:#N` (the code does not yet meet it), where `#N` is the task in `docs/tasks/` (or the issue) that carries the work.

Example, not part of the specification:

```text
#### TDD-1.1.1 Reject a request without a credential

<!-- id: TDD-1.1.1 | implements: XX-01 | code: src/http/auth.ts#requireCredential | tests: tests/http/auth.test.ts | status: pending:#12 -->

The request handler calls `requireCredential` before routing. It returns the rejection response and logs the request id once.
```

## 1. First chapter

### 1.1 First section

No items yet. The first accepted decisions add them here.
