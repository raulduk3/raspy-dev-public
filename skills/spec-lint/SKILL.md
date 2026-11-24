---
name: spec-lint
description: >-
  Check a repository's specification (`docs/spec/`) against its conventions before a
  specification change merges: trace comments, status markers that cite an existing task,
  decision or issue, lock markers where used, no people or tools named. Reports findings;
  edits nothing.
---

# spec-lint

Read-only. Report each finding as `file:line: problem`; fix nothing unless asked.

Read the mode with `dev-loop tier <path>`: `spec=single|domains`, `decisions=none|frozen|open`
(default `none`).

With `decisions=none` or `decisions=frozen`, in each layout: compare the branch with its base.
`git diff --name-status <base>... -- docs/decisions` must print nothing, and the branch adds no
`SPEC-AMENDMENTS.md`. With `decisions=none`, a line with the status `D` (a deletion) is not a finding. A status marker that cites a decision is not a finding when the file is
there; a new citation of a decision is a finding.

## With `spec=domains` or `decisions=frozen`

The repository's own checks are the conventions. Do not look for conventions at the top of a
single `SDD.md`; there is none.

1. Run each check that the repository's `AGENTS.md` names, in its order. For example:
   `bun run spec:index` must leave `docs/spec/index.json` unchanged (`git diff --exit-code
   docs/spec/index.json`), then `bun run spec:check`
   (`python3 scripts/checks/spec-workflow.py check`), then `bun run spec:audit`. Report each line
   that a check prints as a finding. A check that is missing is a finding.
2. With `decisions=frozen`, no `SPEC-AMENDMENTS.md` exists under `docs/spec/`.
3. Each changed task cites current IDs that the index holds. With `decisions=frozen`, a
   `kind: decision` task is a finding.
4. Rules 4 and 6 below apply. Rules 1, 2, 3 and 5 do not apply.

## With `spec=single` and `decisions=none` or `decisions=open`

1. Every SDD requirement is a `**XX-nn.**` line followed by its
   `<!-- id: SDD-XX-nn | tdd: ... | status: ... -->` comment, and every TDD item is a
   `#### TDD-x.y.z` heading followed by its `<!-- id: ... | implements: ... -->` comment, as the
   conventions at the top of `SDD.md` and `TDD.md` state. `tdd:` and `implements:` cite items that
   exist.
2. Every status is `implemented`, `pending:#N` or `deviation:#N`, and `#N` resolves: in a local
   repository (`repos.conf` posture `local`) to a file in `docs/tasks/` or `docs/tasks/done/`; in a
   GitHub-backed one to an issue (`gh issue view N`). A `pending` item whose task is done, or whose
   issue is closed, is a finding.
3. Where the specification already uses spec-lock markers, every subsection carries one. A
   specification with none is not a finding.
4. No section names a person, agent, model, session or process history.
5. Every `Describes release:` header matches the current tag or candidate.
6. In a local repository, `dev-loop tasks <repo> check` reports ok.
