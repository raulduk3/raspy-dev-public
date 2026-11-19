# Jev bounded-decision adapter

`ai-jev` is the platform's thin Jev integration. It is intentionally small: schemas live in
`schemas/jev/`, callers send state, Jev returns closed typed answers, and platform code decides
what to do next.

Jev is not a reasoner here. It does not plan, write, summarize, resolve truth, or authorize work.
It classifies bounded questions so code can route, rank, verify or escalate.

## Commands

```bash
ai-jev list
ai-jev status
ai-jev install-research
ai-jev import-key-from-env
ai-jev show rank-context
ai-jev request rank-context --state '{"task":"...","candidate":"..."}'
ai-jev decide rank-context --provider http --state @state.json
```

Providers:

- `openrouter` (default, owner 2026-10-14): Jev through OpenRouter's `typesafe/jev-router`, on the
  one OpenRouter key; there is no Jev account. The request asks the schema's closed questions with
  a JSON schema for the answer, and OpenRouter's reported charge is what the monthly cap counts.
  On dev-server it goes to the local `jev-proxy` (`127.0.0.1:8741`), which alone holds the key, so
  every identity can ask without seeing it. Elsewhere set `JEV_OPENROUTER_URL` to OpenRouter's
  `https://openrouter.ai/api/v1/chat/completions` and pass `OPENROUTER_API_KEY`.
- `ai-jev mcp` serves the schemas as MCP tools (`jev_rank_context`, ...) over stdio, for Claude
  desktop and Cowork on the Mac: `ssh dev-server /opt/dev-platform/current/bin/ai-jev mcp`.
- `command` (when `JEV_COMMAND` is set): runs `$JEV_COMMAND`, sends request JSON on stdin, reads JSON on stdout.
- `http`: POSTs to the configured endpoint, or `$JEV_API_URL` when set. The key comes from `JEV_API_KEY` or the `dev-platform-jev` secret: stored once with `ol-login jev`, kept by root, and read by `ai-jev` through root's helper when the owner runs it (each use noted in the journal).
- `--response` bypasses providers and validates a fixture, useful for tests and dry runs.

`ai-jev install-research` writes the same non-secret provider shape used by the research platform to `~/.config/dev-platform/jev.json`: ngrok AI Gateway at `https://gateway.ngrok.ai/v1/systemone`, model `typesafeai/jev-latest`, and `JEV_API_KEY` as the credential name. `ai-jev import-key-from-env` stores the current `JEV_API_KEY` in Keychain. The CLI never prints the key.

Live calls are capped at `$10/month` by default. Usage is tracked in `~/.local/state/dev-platform/jev/usage.json`; once the monthly spend reaches the configured limit, or the next estimated request would exceed it, live calls are disabled. Fixture validation with `--response` remains available because it is not paid.

## Schemas

Current automatic/advisory integrations:

- `ai-env doctor` reports Jev config, credential and capped monthly usage.
- `ai` shows Jev status/spend and can classify a request from Accounts and setup.
- `ai-session list --search TEXT --jev-rank` reranks candidate sessions with `rank-context`.
- `hooks/pre-tool-use-guard.sh` can use `classify-tool-risk` as an escalation-only advisory after deterministic guard rules. Set `DEV_PLATFORM_JEV_GUARD=1` for a session to enable paid hook classification; it is off by default so test suites and bulk command loops do not spend silently.
- Direct callers use `ai-jev decide <schema> --provider http --state ...`.

Initial schemas:

| Schema | Use |
| --- | --- |
| `rank-context` | Rerank search, docs, memory, session or issue candidates before loading context. |
| `verify-claim` | Classify whether one source supports, contradicts or does not state one claim. |
| `classify-tool-risk` | Raise risk or require confirmation for proposed commands and tool calls. |
| `route-task` | Suggest a declared surface or lane for an incoming request. |
| `check-completion` | Second-pass classification of whether bounded task evidence appears complete. |
| `detect-instruction-injection` | Flag untrusted text that targets an agent, policy or credential flow. |

A schema may use only:

- `choice`: pick one declared option.
- `score`: pick one declared ordered level.
- `noul`: probability that one bounded yes/no statement is true.

Provider responses must include every declared question, no extra answer IDs, declared choices only,
and numeric confidence/probabilities from 0 to 1.

## Integration rule

Use Jev at decision edges:

```text
search/tool/platform state
  -> ai-jev schema request
  -> typed JSON answer
  -> ordinary code routes, filters, escalates or asks a human
```

Do not put Jev in the core reasoning path:

```text
agent asks Jev what to do next   # wrong
```

For safety decisions, Jev may raise risk. It must not lower a deterministic guard, policy rule or
human requirement.
