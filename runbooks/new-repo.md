# Runbook: a new repository

One command initializes a repository to the standard. A repository is local unless `--github` is
given; only a GitHub-backed one needs section 2.

## 1. Initialize

```
new-repo <directory> --register [--personal] [--owner <login>] [--github <owner>/<name>] [--private|--public]
```

- Copies `templates/` into the directory: `AGENTS.md`, `CONTRIBUTING.md`, `CLAUDE.md`, the pull request template, `CODEOWNERS` (with your login), Dependabot, the `checks` and `release` workflows, language-neutral `scripts/check`, `scripts/checks/hygiene.py`, `scripts/version.py`, `docs/VERSIONING.md`, `docs/decisions/0000-template.md`, the empty specification under `docs/spec/` and `docs/tasks/`.
- Writes a `.gitignore`, a `README.md` stub and a tiny hygiene test. Project-specific build/test commands belong in executable `scripts/check-local`, not in the skeleton.
- Creates the repository on `main` and tags `v0.1.0` on the first commit so the version derives. At tier 3 it also creates `develop`; tiers 1, 2 and 4 use `main` and release tags only.
- With `--github`, creates the GitHub repository with `gh`, pushes its branches and applies the rulesets (`github/rulesets/main.json`, and `develop.json` at tier 3).

- `--register` adds the repository to `~/.config/dev-platform/repos.conf` (`local`, or `owner` with `--github`); `--tier N` writes its source control tier on that line (default 2 with `--personal`, else 3).

Next, the `intake` skill turns the goal into the first decisions, requirements and task files, and the `loop` skill builds them.

## 2. GitHub, by hand (GitHub-backed repositories only)

1. Settings, General: default branch `main` (`develop` at tier 3); allow merge commits only; delete head branches on merge.
2. Settings, Code security: enable Dependabot alerts and security updates.
3. If the plan allows automatic code review, turn it on for every pull request.
4. Create the milestone for the first minor version.

## 3. First change

Make the first change on the base (`main`, or a `docs/readme` branch from `develop` at tier 3): write the README (what the repository contains, how to use it, where the contracts are) and run `scripts/check`. If the project already has a concrete language or runtime, add its commands to executable `scripts/check-local` in that first change. In a GitHub-backed repository open the pull request with the template and merge it, which proves the rulesets on a real change; in a local one land it with `dev-loop land`, or commit it on `main` at tier 1.
