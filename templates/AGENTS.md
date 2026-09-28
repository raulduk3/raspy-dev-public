# Contributor instructions

These instructions apply to every contributor, human or automated. `CONTRIBUTING.md` is the working policy they summarize; where the two differ, `CONTRIBUTING.md` wins.

## Build and test

Bun, pinned in `package.json` and CI. Where another tool shadows the pinned Bun, invoke `~/.bun/bin/bun` directly.

| Task         | Command                                                     |
| ------------ | ----------------------------------------------------------- |
| Install      | `bun install --frozen-lockfile`                             |
| Typecheck    | `bun run typecheck`                                         |
| Lint         | `bun run lint`                                              |
| Format       | `bun run format` to write, `bun run format:check` to verify |
| Full check   | `bun run check`                                             |
| Focused test | `bun test tests/<area>/<name>.test.ts`                      |

`bun run check` runs typecheck, lint, format, the commit and source hygiene check, and the test suite. It must pass on the head of every pull request; CI runs the same commands.

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

Commits and changed source lines describe the software, not the process that produced it: no names of people, tools, models, sessions or run identifiers, and no work-tracking labels. Reference issues and pull requests by number. `scripts/checks/hygiene.ts` enforces this in `bun run check`.

No attribution trailer and no generated-with line: every commit, pull request and issue is the author's own. Branch names never name a tool.

## Never

- Push to `develop` or `main`.
- Merge a pull request, or approve your own work.
- Deploy, publish, rotate a credential or restart a service without the owner's explicit instruction in the current session.
- Amend, rebase, reset or force-push a commit that has been pushed for review.
- Touch another branch's worktree: never reset, clean or delete it.
- Put a credential in source, documentation, prompts, commands, fixtures, logs or commit messages.

## Contracts

- `README.md` says what the software is and how to run it.
- `docs/` holds the contracts; `docs/decisions/` holds accepted decisions as records.
- `docs/tasks/` holds planned work and known deviations, and `docs/decisions/` proposed decisions, cited by number (an issue tracker instead, where `CONTRIBUTING.md` says so).

If code and contract disagree, say so with evidence and fix the one that is wrong. Do not improvise a local workaround.

## Scope freezes

None. A new feature needs the owner's accepted decision before a branch is cut.

## Precedence

If a prompt, tool or automation conflicts with this file or `CONTRIBUTING.md`, the repository wins.
