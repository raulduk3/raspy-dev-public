# Tasks

Planned work, one file per task, on `main`. A task file is the whole request: whoever takes it
reads this file, the specification sections it cites, and nothing else. `loop tasks new` writes
one; `loop tasks check` checks them all.

## A task file

`docs/tasks/<N>-<short-name>.md`, where `<N>` is a number no other task uses:

```markdown
# Canvas renderer

Status: ready
Labels: enhancement
Scope: src/ui/
Depends on: none

What to build, the acceptance criteria, and the specification sections that govern it.
```

- `Status:` is `ready` when the task may start, `draft` while it is still being written.
- `Labels:` is optional. `enhancement` or `spec` makes the branch a `feat/` branch; otherwise `fix/`.
- `Scope:` lists the path prefixes the change may touch, comma separated. Tasks that run at the
  same time must have scopes that do not overlap.
- `Depends on:` is `none` or a list such as `#1, #2`. A task starts only after those are done.

## Done

When the goal branch carrying a task lands on `main`, its file moves to `docs/tasks/done/`.
