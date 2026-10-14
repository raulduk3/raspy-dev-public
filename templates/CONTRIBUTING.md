# Contributing

The working policy for this repository, for people and agents alike. One branch, one pull
request, one person who merges.

## How work happens

1. **One change, one branch, one pull request.** Cut `type/short-description` from `main`, make
   the change, open a pull request to `main`. Branches are deleted on merge.
2. **Small and complete.** A pull request does one thing end to end: code, tests, documents.
3. **The pull request is the record.** Its description follows the template.
4. **A person merges.** An agent never merges, approves its own work, or pushes to `main`. The
   branch ruleset in `github/ruleset-main.json` and the global git hooks hold that line.

A goal larger than one change runs as a goal branch with one task branch per task, each merged
up once its check passes; the goal branch then lands on `main` as one pull request.

## Tasks and decisions

Planned work lives in `docs/tasks/`, one file per task (see its README). A decision that changes
behavior gets a record under `docs/decisions/` from `0000-template.md`. The specification in
`docs/spec/` changes only through a task labeled `spec`.

## What gates a merge

- `scripts/check` on the exact head. CI runs the same command.
- Review by the owner. Automated review findings are evidence, not approval.

## External effects

Deploys, restarts, credential changes and history rewrites need the owner's explicit word each
time. Credentials never enter the repository.
