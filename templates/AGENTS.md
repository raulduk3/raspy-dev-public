# Contributor instructions

These instructions apply to every contributor, human or automated. `CONTRIBUTING.md` is the working policy they summarize; where the two differ, `CONTRIBUTING.md` wins.

## Source control

Source control tier: @TIER@ (see repos.conf). Find the tier with `dev-loop tier <path>` before you change a file.

| Command | Use |
| --- | --- |
| `dev-loop tier <path>` | Print the tier of a repository. |
| `dev-loop start <repo> <type/slug>` | Start the goal branch (tiers 2 and 3). |
| `dev-loop go <repo>` | Give each ready task to a worker slot. |
| `dev-loop fold <repo> <N>` | Join a finished task into the goal branch. |
| `dev-loop land <repo>` | Land the goal. The owner runs this command. |
| `dev-loop tidy <repo>` | List merged refs and old worktrees to remove. |

## Build and test

The repository skeleton is language-neutral. `scripts/check` is the required platform check and `scripts/version.py` derives the SemVer string from git. Add project-specific checks in `scripts/check-local` when this repository gains a concrete runtime, language or build system.

| Task                  | Command                         |
| --------------------- | ------------------------------- |
| Full platform check   | `scripts/check`                 |
| Derived version       | `python3 scripts/version.py`    |
| Version metadata      | `python3 scripts/version.py --json` |
| Project-specific test | `scripts/check-local`, if present |

`scripts/check` runs commit/source hygiene, proves the version derives, then runs executable `scripts/check-local` if the project has one. It must pass on the head of every pull request; CI runs the same command.

## Change rules

- One change, one branch cut from `develop`, one pull request to `develop`. Branch name `type/short-description`. No stacked pull requests: a change that depends on another waits for it to merge, then cuts from `develop`.
- Make the smallest coherent change that completes the request.
- Code, tests, and the documentation the change affects ship in the same pull request.
- Read the code you are changing and its tests before editing.
- Prefer editing an existing owner over adding a parallel one. No speculative abstractions.
- Tests detect a concrete prohibited alternative. Do not mock away the owner under test.
- Stage only the files that belong to the change. Preserve unrelated uncommitted work.
- The pull request description follows `.github/pull_request_template.md` and is the record of the change.

## Commit format

`type(scope): summary`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`. Subject under 72 characters, imperative, no trailing period. The body explains why. `Closes #N` links the issue. `!` after the type, or a `BREAKING CHANGE:` footer, marks a major change.

Commits and changed source lines describe the software, not the process that produced it: no names of people, tools, models, sessions or run identifiers, and no work-tracking labels. Reference issues and pull requests by number. `scripts/checks/hygiene.py` enforces this in `scripts/check`.

No attribution trailer and no generated-with line: every commit, pull request and issue is the author's own. Branch names never name a tool.

## Never

- Push to `develop` or `main`.
- Merge a pull request, or approve your own work.
- Deploy, publish, rotate a credential or restart a service without the owner's explicit instruction in the current session.
- Amend, rebase, reset or force-push a commit that has been pushed for review.
- Touch another branch's worktree: never reset, clean or delete it.
- Put a credential in source, documentation, prompts, commands, fixtures, logs or commit messages.

## Contracts

- `README.md` says what the repository contains and how to use it.
- `docs/VERSIONING.md` defines the SemVer/git graph contract.
- `docs/` holds the contracts; `docs/decisions/` holds accepted decisions as records.
- `docs/tasks/` holds planned work and known deviations, and `docs/decisions/` proposed decisions, cited by number (an issue tracker instead, where `CONTRIBUTING.md` says so).

If code and contract disagree, say so with evidence and fix the one that is wrong. Do not improvise a local workaround.

## Scope freezes

None. A new feature needs the owner's accepted decision before a branch is cut.

## Precedence

If a prompt, tool or automation conflicts with this file or `CONTRIBUTING.md`, the repository wins.
