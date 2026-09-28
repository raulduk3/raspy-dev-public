# Runbook: a new repository

One command initializes a repository to the standard. A repository is local unless `--github` is
given; only a GitHub-backed one needs section 2.

## 1. Initialize

```
new-repo <directory> --register [--personal] [--owner <login>] [--github <owner>/<name>] [--private|--public]
```

- Copies `templates/` into the directory: `AGENTS.md`, `CONTRIBUTING.md`, `CLAUDE.md`, the pull request template, `CODEOWNERS` (with your login), Dependabot, the `checks` and `release` workflows, `scripts/checks/hygiene.ts`, `scripts/version.ts`, `docs/decisions/0000-template.md`, the empty specification under `docs/spec/` and `docs/tasks/`.
- Writes a minimal `package.json` with the check scripts, a `.gitignore`, a `README.md` stub, `tsconfig.json`, `.prettierrc.json` and `eslint.config.js`.
- Creates the repository on `main`, tags `v0.1.0` on the first commit so the version derives, and creates `develop`.
- With `--github`, creates the GitHub repository with `gh`, pushes both branches and applies `github/rulesets/develop.json` and `github/rulesets/main.json`.

- `--register` adds the repository to `~/.config/dev-platform/repos.conf` (`local`, or `owner` with `--github`); `--personal` lists it in `personal.conf` as the owner's own.

Next, the `intake` skill turns the goal into the first decisions, requirements and task files, and the `loop` skill builds them.

## 2. GitHub, by hand (GitHub-backed repositories only)

1. Settings, General: default branch `develop`; allow merge commits only; delete head branches on merge.
2. Settings, Code security: enable Dependabot alerts and security updates.
3. If the plan allows automatic code review, turn it on for every pull request.
4. Create the milestone for the first minor version.

## 3. First change

Cut `docs/readme` from `develop`, write the README (what the software is, how to run it, where the contracts are) and run `bun run check`. In a GitHub-backed repository open the pull request with the template and merge it, which proves the rulesets on a real change; in a local one merge it with `git merge --no-ff docs/readme` on `develop`.
