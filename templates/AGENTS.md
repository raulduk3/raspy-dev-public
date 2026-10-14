# Instructions

These apply to every contributor, person or agent. `CONTRIBUTING.md` is the policy they
summarize; where the two differ, `CONTRIBUTING.md` wins. Other agents' instruction files in this
repository are links to this one.

## Check

`scripts/check` is the one check: commit and source hygiene, then `scripts/check-local` once the
project has one. Run it before you stop; it must pass on the head of every pull request.

## Work

- One task, one branch, one worktree, one pull request to `main`. Branch name `type/short-name`.
- Read the task file in `docs/tasks/`, the specification sections it cites, the code you change
  and its tests. Touch only the paths in the task's `Scope:`.
- Make the smallest change that completes the task; code, tests and the documents it affects ship
  together.
- Stage only your change. Leave other worktrees and unrelated work alone.

## Commits

`type(scope): summary`, imperative, under 72 characters; the body says why. Types: `feat`, `fix`,
`docs`, `test`, `refactor`, `perf`, `chore`, `ci`. No attribution trailer, no generated-with line,
no tool or model names (`scripts/checks/words.txt`).

## Never

- Push to `main`, merge a pull request, or approve your own work.
- Amend, rebase, reset or force-push anything pushed for review.
- Deploy, publish, rotate a credential or restart a service without the owner's word in this
  session.
- Put a credential in source, documents, prompts, commands, fixtures, logs or commits.

## Contracts

- `docs/spec/` says what the software does; `docs/decisions/` records accepted decisions;
  `docs/tasks/` holds planned work.
- If code and contract disagree, say so with evidence and fix the one that is wrong.
