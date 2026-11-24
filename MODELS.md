# Model routing

Which class of model does which class of work. Cost is a tie-breaker, never the first criterion.

`bin/pstack-model` is the one resolver. The model file `/etc/dev-platform/pstack-models.md` fills each tier with model families, in order. Its source is `~/dev/dev-server/etc/pstack-models.md`, and `/setup-pstack` writes it. A user's `~/.config/dev-platform/pstack-models.md` overrides single lines. Without a file or a line, the resolver uses the defaults that `bin/pstack-model defaults` prints.

| Tier | Work |
| --- | --- |
| `judgment` | Specification, decisions, review, the root loop |
| `implementation` | A bounded task with a deterministic check behind it |
| `mechanical` | Triage, formatting, summaries, documentation tasks |
| `overseer` | The review seats of a team |

Each tier line names its OpenRouter families first (`openrouter:<maker>/<model>`) and the Claude and Codex subscriptions last, as the fallbacks for the clients that run only those. `bin/pstack-model resolve '<role>' [--all] [--runtime claude|codex|pi|openrouter]` prints the first family of the tier that the runtime can run, and the effort. A Pi seat of a team runs on OpenRouter only.

Rules:

1. Use a cheaper model only where a check catches its mistakes. If no check would catch a wrong answer, the work is judgment work.
2. On a failure, go one tier up. The loop does this for a Pi worker: a task whose Pi run made no commit gets the `rig worker retry` line and the dollar cap `LOOP_WORKER_RETRY_COST_LIMIT` (default 6). A second failure at the judgment tier stops and reports.
3. Each dispatched run has limits. The loop sets them for each worker: `LOOP_WORKER_MAX_TURNS`, `LOOP_WORKER_MAX_SECONDS`, `LOOP_WORKER_TOKEN_LIMIT` and `LOOP_WORKER_COST_LIMIT` (default 2 dollars).
4. On a quota error, stop the lane and name the account. Do not retry on another account.

pstack's roles: the pstack skills name no model. Each role names a tier slug, `<tier>[.<n>]-<effort>` (`implementation-xhigh`, `judgment-max`, `judgment.2-max` for a panel's second family), so a skill keeps its own choice of how strong and how deliberate each role is. The model file has one line for each role.

The loop takes its implementation workers from the line `feature, refactoring`, the workers of tasks labeled `spec`, `decision`, `privacy` or `security` from `judgment and prose`, and its documentation workers from the `mechanical` tier. `LOOP_MODEL` overrides all three. `LOOP_WORKER_MODEL` stands in for a missing `feature, refactoring` line. See `docs/pstack-platform.md`.
