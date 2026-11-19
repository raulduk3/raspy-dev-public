# Tasks

Work is planned here, one file per task, on `develop`. The repository's `repos.conf` line says
the format: `tasks=json` (a typed item, below) or `tasks=md` (the default, a Markdown file). A task file is the whole request: the
person or tool that takes it reads this file, the specification sections it cites, and nothing
else.

## A JSON task (`tasks=json`)

`docs/tasks/<N>.json`, checked against `task.schema.json` in this folder by `scripts/check`.
`dev-loop tasks <repo> new "<title>" --scope <prefixes> --goal G-1` writes a draft. Write the
brief and the checks in place of each `TO WRITE:` line; `check` refuses a ready task that still
has one.

```json
{
  "$schema": "task.schema.json",
  "schema": "dev-platform/task@1",
  "id": 12,
  "title": "Group the price lines by visit",
  "kind": "code",
  "goal": "G-2",
  "state": "ready",
  "brief": "Price lines are one flat list today, so a job with two visits mixes their lines. Group the lines by visit and show each visit's date, so the customer sees what each visit cost.",
  "depends_on": [11],
  "refs": [{"type": "spec", "id": "SDD-P10.337"}, {"type": "decision", "id": "0008"}],
  "work": {"scope": ["src/pricing/"], "changes": ["Group the lines by visit.", "Show the visit date on each group."]},
  "acceptance": [
    {"by": "test", "statement": "A job with two visits shows two groups.", "path": "tests/pricing.test.ts"},
    {"by": "command", "statement": "The full check passes.", "run": "scripts/check"}
  ],
  "created": "2026-11-12"
}
```

- `kind` is code, spec, research, ops, decision, writing or data. Each kind has its own `work`
  fields; the schema names them. Only a ready code or spec task with no person as `assignee`
  goes to an agent worker; the loop marks any other ready task `not-for-workers`.
- `brief` is the task in prose, in this repository's language for tasks: what is true now, the
  change and why. The worker reads it whole. The other fields index the task for the loop and the
  checks; they do not replace the brief. The title keeps this repository's form for titles.
- `goal` names the goal the task serves. `acceptance` has one to eight checks; each says how it
  is verified (`test`, `command`, `eval`, `review`, `artifact` or `host`).
- `state` is draft, ready, blocked (with a `blocked` object) or cancelled (with a `cancelled`
  object). There is no done state: a commit on the base with the trailer `Closes: #<N>`
  closes the task, and the file stays where it is. `Task: #<N>` marks work on the task and closes
  nothing.
- Repository fields go under `ext`, with keys that start with `x-`.

## A Markdown task (`tasks=md`)

`docs/tasks/<N>-<short-name>.md`, where `<N>` is a number no other task uses:

```markdown
# Canvas renderer

Status: ready
Labels: enhancement
Scope: src/ui/
Depends on: none

What to build, the acceptance criteria, and the specification sections that govern it.
```

- `Status:` is `ready` when the task may be started, `draft` while it is still being written.
- `Labels:` is optional. `enhancement` or `spec` makes the branch a `feat/` branch.
- `Scope:` lists the path prefixes the change may touch, comma separated. Tasks that run at the
  same time must have scopes that do not overlap.
- `Depends on:` is `none` or a list such as `#1, #2`. A task starts only after those are done.

## Done

A Markdown task's file moves to `docs/tasks/done/` when its change is merged into `develop`. A
JSON task stays; the `Closes: #<N>` trailer on the merged commit closes it. The history of a task
is the file and the commit that closed it.
