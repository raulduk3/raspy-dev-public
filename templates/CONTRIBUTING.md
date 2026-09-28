# Contributing

This is the working policy for the repository. It applies to people and to automated contributors alike. It is short on purpose: one branch, one pull request, one reviewer, one deploy owner.

## How work happens

1. **One change, one branch, one PR.** Cut a branch from `develop` named `type/short-description`, make the change, open a pull request to `develop`. No cumulative integration branches and no stacked pull requests. Change branches are deleted on merge.
2. **Small and complete.** A PR does one thing end to end: the code, its tests, and the documentation it changes.
3. **The PR is the record.** The description follows the template: what changed and why, verification, deploy impact, review notes.
4. **Human review merges.** The owner reviews and merges with a merge commit. An automated contributor never merges, never approves its own work, and never pushes to `develop` or `main`.

Commit messages use `type(scope): summary`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`. Commits and changed source lines carry no process words, people, tools, models, sessions or run identifiers; `bun run check` enforces it.

## Tasks

Planned work lives in `docs/tasks/`, one file per task, as that folder's README describes. A task file carries the request, its `Scope:` and its `Depends on:`, and moves to `docs/tasks/done/` when its change is merged. A repository that also uses an issue tracker says so here.

## What gates a merge

- `bun run check` on the exact PR head: typecheck, lint, format, hygiene and the test suite. CI runs the same commands.
- Human review by the owner. Automated review findings are evidence to reproduce and disposition, not approval.
- New commits invalidate earlier checks and approvals.

## Versioning and tags

Semantic versioning, one product version, derived from the git graph at build time by `scripts/version.ts` and never typed by hand: `X.Y.Z` on a release tag, `X.Y.Z-rc.N` on a candidate tag, otherwise `<next patch>-<branch>.<distance>+<sha8>`.

- `vX.Y.Z` tags live on `main` only, annotated, created and pushed by the owner after the release pull request merges. The tag push is the release and, where a deploy exists, its authorization.
- `vX.Y.Z-rc.N` tags live on `develop` only, annotated, created by the owner to name a candidate.
- No other tags. `package.json` is set by the release pull request and read by nothing. The changelog is generated and never hand-edited.

## Deploys and external effects

Deploys, restarts, credential rotation and destructive history operations require the owner's explicit authorization each time. Keep credentials out of source, documentation, prompts, commands, fixtures and logs. Preserve unrelated dirty work. Do not force-push, reset or clean away uncommitted changes.

## Decisions

An accepted decision that changes behavior gets a record under `docs/decisions/`, from `0000-template.md`, citing its task or issue and the changes that carried it.
