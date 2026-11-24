---
name: new-repo
description: >-
  Start a new project from zero: create a repository to the platform standard with
  `new-repo`, local by default or GitHub-backed on request, register it for the loop,
  then hand the goal to `intake`.
---

# new-repo

`new-repo` (on `PATH`; `bin/new-repo` in the platform) creates a repository from the platform's
templates. The files are language-neutral: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, the empty
specification (`docs/spec/SDD.md`, `TDD.md`), `docs/tasks/`, and the hygiene and version scripts (`scripts/check`, `scripts/version.py`). It
writes no language skeleton. The project adds its own build and checks in `scripts/check-local`.
It commits on `main`, tags `v0.1.0`, and writes the source control tier in `AGENTS.md`.

## Tiers

- Tier 1 (solo trunk) and tier 2 (personal shared): `main` and release tags only. No `develop` branch.
- Tier 3 (protected company): `main` and `develop`. The checkout stays on `develop`.
- `--tier N` sets the tier. The default is 2 with `--personal`, and 3 without it.

## Procedure

1. **Ask only what changes the command:** the directory, whether it is
   the owner's own project (`--personal`) or professional work, and whether it needs GitHub now.
   Local is the default and needs no network; GitHub can be added later.
2. **Run** `new-repo <directory> --register [--personal] [--tier N] [--owner <login>]`.
   - `--owner` is required when `gh` is not logged in; locally it only names the repository in
     `repos.conf` (`<owner>/<name>`).
   - With `--github <owner>/<name> [--private|--public]` it also creates the GitHub repository,
     pushes the branches and applies the rulesets. That leaves the machine: confirm first, and
     never for a professional repository without the owner's word.
   - `--register` appends `<owner>/<name> <path> local|owner <base> tier=N tracker=files|github`
     to `~/.config/dev-platform/repos.conf`. The base is `main`, or `develop` at tier 3.
     The tracker is `files` for a local repository and `github` for a GitHub-backed one.
3. **Verify** from the new checkout: `git branch --show-current` is the base,
   `dev-loop tier .` prints the tier, `dev-loop status <owner>/<name>` resolves the repository,
   and `scripts/check` passes.
4. **Hand over** to `intake` with the owner's goal as the source. It asks the owner each open
   question, writes the first requirements in the empty specification after the owner accepts
   them, and writes the first tasks; `loop` then builds them. A new repository keeps no decision
   record (`decisions=none`, the default of a registered line).

A project that needs a language skeleton adds it in its first change. `runbooks/new-repo.md` has
the GitHub settings that are done by hand.
