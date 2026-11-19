# Owner words

`skills/develop/owner-words.md` gives each of the owner's short words one meaning, and holds the ask-first rule. It is the one source file. The owner decides each meaning. A word with status `PROPOSED` waits for his decision.

## How each agent loads it

| Machine | Claude Code | Codex | Pi |
| --- | --- | --- | --- |
| dev-server (platform release) | `ai-guardrails install` puts `@/opt/dev-platform/current/skills/develop/owner-words.md` in the block of `~/.claude/CLAUDE.md` and of each `~/.claude-accounts/*/CLAUDE.md`. An activation updates it. | `ai-guardrails install` puts the text in the block of `~/.codex/AGENTS.md`. | `ai-guardrails install` puts the text in the block of `~/.pi/agent/APPEND_SYSTEM.md`. |
| A machine without the platform (laptop, git-host) | `naming-install.py` (from `bin/ai-title-bundle`) puts the text in its block of `~/.claude/CLAUDE.md`. | The same, in `~/.codex/AGENTS.md`. | The same, in `~/.pi/agent/APPEND_SYSTEM.md`, when `~/.pi/agent` exists. |

Codex and Pi have no include, so they get a copy of the text. `ai-guardrails status` and `naming-install.py status` report a copy that is out of date. After a change to the word list, do these steps:

1. On dev-server, activate the release, then run `ai-guardrails install` for each home.
2. Write the installer again: `bin/ai-title-bundle > ~/.local/share/dev-platform/naming-install.py`.
3. On each other machine, run the installer (`docs/session-naming.md`, "Machines without the platform").

To prove it, open a new session of each agent and ask "what does push mean?".

## Count the vague verbs again

`ai-prompt-verbs --project <part of the path>` reads the local Claude, Codex and Pi transcripts and prints the shares. `--since` and `--until` set a time window. `--save rows.jsonl` keeps the rows, and `--rows rows.jsonl` counts them again. The extraction rules are in `lib/ai_ecosystem/prompt_verbs.py`.

The 2026-11-08 count of Acme prompts on dev-server, and the same count with this command on the same day:

| Measure | 2026-11-08 count | `ai-prompt-verbs --project acme --until 2026-11-08T19:05` |
| --- | ---: | ---: |
| Prompts (Claude, Codex) | 1,403 (1,313, 90) | 1,364 (1,322, 42) |
| Contain a vague verb | 32% | 32.3% |
| Contain only vague verbs | 20% | 20.5% |
| 3 words or less | 18% | 17.7% |

The 2026-11-08 count kept 48 Codex rows that a subagent thread copies from its parent thread. The command counts the parent row only.

## Proposal: a prompt hint hook (not installed)

Status: waits for the owner's approval.

- **Claude Code:** a `UserPromptSubmit` command in `hooks/claude-settings.hooks.json`, `hooks/prompt-hint.py`.
- **Codex:** the same script as a `UserPromptSubmit` hook in `hooks/codex-hooks.json`. Codex runs a hook only after the owner trusts it once in the hook review.
- **Pi:** an extension on the `input` event, as `integrations/pi/session-title.mjs` does.

The hook does these steps:

1. Skip a slash command, and a prompt of 3 words or less (an answer to the last question).
2. Skip a prompt when the session already has an earlier prompt from the owner. Only the first prompt of a task gets the check.
3. Match the prompt with `prompt_verbs.VAGUE` and `prompt_verbs.SPECIFIC_RE`.
4. If the prompt has only vague verbs, add one context line: "The prompt has only vague verbs (make, fix). If the object or the end state is not clear, ask one question first (owner-words.md)."

It never blocks a prompt. It uses no model. The cost is one Python start and a regex match: about 35 ms on dev-server, and no tokens when it is silent. When it warns, it adds about 40 tokens to that prompt. On the 2026-11-08 data it warns on about 20% of first prompts.
