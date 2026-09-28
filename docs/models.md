# Model routing

Which class of model does which class of work. Every fleet or workflow run carries a token ceiling and an agent-count ceiling and stops on a quota error. Cost is a tie-breaker, never the first criterion.

| Tier | Work | Models |
| --- | --- | --- |
| Judgment | Specification, decisions, review, the root loop | Fable or Opus, low to medium effort |
| Implementation | A bounded issue with a deterministic check behind it | `LOOP_WORKER_MODEL` (Sonnet by default), Codex default |
| Mechanical | Triage, formatting, summaries | Haiku, local |

Rules:

1. A cheaper model only where a check catches its mistakes. If no check would catch a wrong answer, the work is judgment work.
2. Escalate one tier on failure without asking. A second failure at the judgment tier stops and reports.
3. Every dispatched run states its ceiling: tokens per worker, agents per cycle, wall-clock per cycle. A run with no ceiling is not dispatched.
4. On a quota error, stop the lane, name the account, and do not retry on another account until the routing table below says so.

Implementation tier: the loop's default worker model is `LOOP_WORKER_MODEL`, set in `brief.conf` (Sonnet when unset). On a subscription with full availability of the judgment model, set it to `fable` at high effort and keep Sonnet and Codex as explicit choices. Fable at high effort on a simple task does not spend much more than at low, so tiering is a cost lever, not a quality one. The rules above still hold.

pstack's roles: the pstack skills name no model. Each role names a tier slug, `<tier>[.<n>]-<effort>` (`implementation-xhigh`, `judgment-max`, `judgment.2-max` for a panel's second family), so a skill keeps its own choice of how strong and how deliberate each role is. `/setup-pstack` writes `~/.config/dev-platform/pstack-models.md`: `tier` lines that fill the tiers above with this machine's families, in order, and one line per role. `bin/pstack-model resolve '<role>' [--all] [--runtime claude|codex]` turns a role into a model and effort; without the file it uses the defaults `bin/pstack-model defaults` prints. The loop takes its implementation workers from `feature, refactoring`, its judgment-tier workers from `judgment and prose` and its documentation workers from the `mechanical` tier (`LOOP_MODEL` overrides all three; `LOOP_WORKER_MODEL` stands in for a missing `feature, refactoring` line). See `docs/pstack-platform.md`.

Routing table (fallback order on a quota error; edit here, never improvise):

| Lane | First | Then | Then |
| --- | --- | --- | --- |
| Judgment | primary account, Fable | primary account, Opus | stop and report |
| Implementation | primary account, Sonnet | Codex default | stop and report |
| Mechanical | Haiku | local model | stop and report |

Which account is primary for which surface is a separate decision (spec B2.1, D-13) and is recorded here once made.
