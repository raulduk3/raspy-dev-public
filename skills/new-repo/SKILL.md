---
name: new-repo
description: >-
  Start a new project from zero: create a repository from the standard templates with
  `new-repo`, local by default or on GitHub on request, then hand the goal to `intake`.
---

# new-repo

`new-repo <directory>` creates a repository from the templates: `AGENTS.md` (and a link to it
for every agent's instruction file name), `CONTRIBUTING.md`, the empty specification under
`docs/spec/`, the decision template, `docs/tasks/`, `scripts/check` with its hygiene rules, the
pull request template and CI. It commits on `main` and runs the check.

## Procedure

1. **Ask only what changes the command:** the directory, and whether it needs GitHub now. Local
   is the default and needs no network; GitHub can be added later.
2. **Run** `new-repo <directory>`, or `new-repo <directory> --github <owner>/<name> [--public]`.
   The GitHub form creates the repository, pushes `main` and protects it with
   `github/ruleset-main.json`. That leaves the machine: confirm with the person first.
3. **Verify** in the new checkout: `git branch --show-current` is `main` and `scripts/check`
   passes.
4. **Hand over** to `intake` with the person's goal. It writes the first decisions, requirements
   and tasks; `loop` then builds them.

The templates are language-neutral. The project's first task adds its language, its build and
`scripts/check-local`, which `scripts/check` runs.
