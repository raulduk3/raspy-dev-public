# Tasks

Work is planned here, one file per task, on `develop`. A task file is the whole request: the
person or tool that takes it reads this file, the specification sections it cites, and nothing
else.

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

- `Status:` is `ready` when the task may be started, `draft` while it is still being written.
- `Labels:` is optional. `enhancement` or `spec` makes the branch a `feat/` branch.
- `Scope:` lists the path prefixes the change may touch, comma separated. Tasks that run at the
  same time must have scopes that do not overlap.
- `Depends on:` is `none` or a list such as `#1, #2`. A task starts only after those are done.

## Done

When a task's change is merged into `develop`, its file moves to `docs/tasks/done/`. The
history of a task is the file and the merge that closed it.
