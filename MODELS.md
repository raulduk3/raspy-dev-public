# Model routing

Which class of model does which class of work. Every fleet or workflow run carries a token ceiling and an agent-count ceiling and stops on a quota error. Cost is a tie-breaker, never the first criterion.

| Tier | Work | Models |
| --- | --- | --- |
| Judgment | Specification, decisions, review, the root loop | Claude Opus 5.5, low to medium effort |
| Implementation | A bounded issue with a deterministic check behind it | GPT-6.1 Sol medium for Codex workers; Claude Opus 5.5 medium for Claude-only loop workers |
| Mechanical | Triage, formatting, summaries | Haiku, local |

Rules:

1. A cheaper model only where a check catches its mistakes. If no check would catch a wrong answer, the work is judgment work.
2. Escalate one tier on failure without asking. A second failure at the judgment tier stops and reports.
3. Every dispatched run states its ceiling: tokens per worker, agents per cycle, wall-clock per cycle. A run with no ceiling is not dispatched.
4. On a quota error, stop the lane, name the account, and do not retry on another account until the routing table below says so.

Implementation tier: Codex-capable workers use `codex:gpt-6.1-sol` at medium effort by default. The current headless loop adapter starts Claude workers, so its implementation fallback is `claude-opus-5-5` at medium effort unless `LOOP_MODEL` or `LOOP_WORKER_MODEL` overrides it. The rules above still hold.

OpenRouter is the centre of the ecosystem (owner, 2026-10-12). Every tier in the model file lists its OpenRouter families first (`openrouter:<maker>/<model>`: DeepSeek for implementation and mechanical work, Claude Fable 5.1 then GPT-6 Astra Pro for judgment and the overseers) and the Claude and Codex subscriptions last, as the fallbacks for the clients that run only those. The API rig (`docs/api-rig.md`) runs on OpenRouter alone, under daily and monthly dollar caps; its seats ask the `advice` model (Fable) for second opinions.

pstack's roles: the pstack skills name no model. Each role names a tier slug, `<tier>[.<n>]-<effort>` (`implementation-xhigh`, `judgment-max`, `judgment.2-max` for a panel's second family), so a skill keeps its own choice of how strong and how deliberate each role is. `/setup-pstack` writes the machine's model file, `/etc/dev-platform/pstack-models.md` (its source is `~/dev/dev-server/etc/pstack-models.md`; a user's `~/.config/dev-platform/pstack-models.md` overrides single lines): `tier` lines that fill the tiers above with this machine's families, in order, and one line per role. `bin/pstack-model resolve '<role>' [--all] [--runtime claude|codex|pi|openrouter]` turns a role into a model and effort; without the file it uses the defaults `bin/pstack-model defaults` prints. The loop takes its implementation workers from `feature, refactoring`, its judgment-tier workers from `judgment and prose` and its documentation workers from the `mechanical` tier (`LOOP_MODEL` overrides all three; `LOOP_WORKER_MODEL` stands in for a missing `feature, refactoring` line). See `docs/pstack-platform.md`.

Routing table (fallback order on a quota error; edit here, never improvise):

| Lane | First | Then | Then |
| --- | --- | --- | --- |
| Judgment | primary account, Claude Opus 5.5 | primary account, Opus alias | stop and report |
| Implementation | primary account, GPT-6.1 Sol where Codex workers are available | Claude Opus 5.5 for Claude-only workers | stop and report |
| Mechanical | Haiku | local model | stop and report |

Which account is primary for which surface is a separate decision (spec B2.1, D-13) and is recorded here once made.
