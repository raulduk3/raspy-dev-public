# Contributing

This is the working policy for the repository. It applies to people and to automated contributors alike. It is short on purpose: one branch, one pull request, one reviewer, one deploy owner.

## How work happens

1. **One change, one branch, one PR.** Cut a branch from `develop` named `type/short-description`, make the change, open a pull request to `develop`. No cumulative integration branches and no stacked pull requests. Change branches are deleted on merge.
2. **Small and complete.** A PR does one thing end to end: the code, its tests, and the documentation it changes.
3. **The PR is the record.** The description follows the template: what changed and why, verification, deploy impact, review notes.
4. **Human review merges.** The owner reviews and merges with a merge commit. An automated contributor never merges, never approves its own work, and never pushes to `develop` or `main`.

Commit messages use `type(scope): summary`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`. Commits and changed source lines carry no process words, people, tools, models, sessions or run identifiers; `scripts/check` enforces it.

## Tasks

Planned work lives in `docs/tasks/`, one file per task, as that folder's README describes. A task file carries the request, its `Scope:` and its `Depends on:`, and moves to `docs/tasks/done/` when its change is merged. A repository that also uses an issue tracker says so here.

## What gates a merge

- `scripts/check` on the exact PR head: commit/source hygiene, version derivation and any project-specific executable `scripts/check-local`. CI runs the same command.
- Human review by the owner. Automated review findings are evidence to reproduce and disposition, not approval.
- New commits invalidate earlier checks and approvals.

## Versioning and tags

Semantic versioning, one product version, derived from the git graph at build time by `python3 scripts/version.py` and never typed by hand. See `docs/VERSIONING.md`. Every branch, pull request and commit gets a version shaped like `<next patch>-<branch>.<distance>+<sha8>` until it is exactly on a release or candidate tag.

- `vX.Y.Z` tags live on `main` only, annotated, created and pushed by the owner after the release pull request merges. The tag push is the release and, where a deploy exists, its authorization.
- `vX.Y.Z-rc.N` tags live on `develop` only, annotated, created by the owner to name a candidate.
- No other version tags. The changelog is generated and never hand-edited.

## Deploys and external effects

Deploys, restarts, credential rotation and destructive history operations require the owner's explicit authorization each time. Keep credentials out of source, documentation, prompts, commands, fixtures and logs. Preserve unrelated dirty work. Do not force-push, reset or clean away uncommitted changes.

## Decisions

The owner accepts a change of behavior before it is built. The change edits the exact lines of the specification under `docs/spec/`, and the commit message gives the reason. The repository keeps no decision record and no amendment ledger.
