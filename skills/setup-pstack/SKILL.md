---
name: setup-pstack
description: Configure which models pstack uses per role and at what reasoning budget. Detects your available models, sorts them into tiers, and writes the platform's model file that overrides the skill defaults. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices.
---

> **On this platform.** This is pstack's `setup-pstack` skill (MIT, Lauren Tan; the unmodified source is in `vendor/pstack`). This copy is adapted; `integrations/pstack/overlays/setup-pstack/` holds every change. Read [the platform map](../../docs/pstack-platform.md) (installed: `/opt/dev-platform/current/docs/pstack-platform.md`) once per session: it says what the Cursor tools named here are on this machine, and which steps the guard hook leaves to the owner.

# Setup pstack

Write the platform's model file, the one file that sets pstack's model per role for the owner and every agent (assistant, ops, engineer), under Claude Code, Codex and Pi. Its source is `~/dev/dev-server/etc/pstack-models.md` in the dev-server repository; bootstrap installs it as `/etc/dev-platform/pstack-models.md`, which every user reads. Every pstack skill reads it through `bin/pstack-model`, and the loop reads it for its workers. It replaces Cursor's `~/.cursor/rules/pstack-models.mdc`. A user's own `~/.config/dev-platform/pstack-models.md` is a personal override, line by line; write it only when the owner asks for a change that is his alone.

The skills never name a model. Each role names a **tier slug**, `<tier>[.<n>]-<effort>`: `judgment-max`, `judgment.2-max`, `implementation-xhigh`, `mechanical`. The file's `tier` lines say which model families fill each tier, in order; `.n` picks the nth family, which is how a panel gets a second family. So a skill keeps its own logic about how strong and how deliberate each role should be, and this file alone decides what that means on this machine. A role may still name a concrete slug (`fable-max`, `codex:gpt-5.6-sol-high`, `openrouter:deepseek/deepseek-v4-pro-0813-high`) to pin it.

OpenRouter is the centre of this ecosystem (owner, 2026-10-12): every tier lists its OpenRouter families first, and the Claude and Codex subscriptions last, as the fallbacks for the clients that can only run those. Claude Code and Codex skip the families they cannot run, so a subscription client still resolves to its own family; Pi and the API rig (`docs/api-rig.md`) take the OpenRouter ones.

## Steps

### 1. Detect available models

A family is what a runtime accepts as a model: for Claude Code the `Agent` tool's `model` (`fable`, `opus`, `sonnet`, `haiku`) or a full id `claude --model` accepts; for Codex, `codex:<model>` as `codex --model` accepts it. Confirm a family by running it once (`claude -p --model <model> --effort low 'reply ok'`, `codex exec --model <model> 'reply ok'`) or from the account's documented entitlements; `ai-account status` names the verified accounts. If you cannot detect any, ask the user to paste the models they have. An OpenRouter family is `openrouter:<maker>/<model>` (`openrouter:deepseek/deepseek-v4-pro-0813`, `openrouter:anthropic/claude-fable-5.1`): Pi runs it with the OpenRouter key. Confirm one from OpenRouter's public model list (`curl -s https://openrouter.ai/api/v1/models`, no key needed) and from Pi's catalog, which is what Pi will accept (`OPENROUTER_API_KEY=placeholder pi --list-models deepseek`; the placeholder only lets Pi list, it reaches nothing). The key itself is the registry's `openrouter` account, typed once on dev-server with `ol-login openrouter`; never ask for it in chat or put it in a file. `ol-login status` shows it verified and its credit.

Never write a family you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid.

### 2. Load current state

`bin/pstack-model defaults` prints the default file, the shape in step 5. `bin/pstack-model show` prints every line in force and the file it came from. Read `~/dev/dev-server/etc/pstack-models.md`, and a personal override if there is one: its `# budget` line, its `tier` lines and its role values are the current choices, and a line it lacks takes the default. A role line whose role is not in the defaults, such as `how critics`, is from a retired role. Drop it. A file from before tiers has concrete role values and no `tier` lines; it still works, and step 3 offers to move it to tier slugs.

### 3. Tiers, budget, and confirm

**(a) Fill the tiers.** From the detected families, order each tier strongest first:

- `judgment`: the strongest reasoning families. Put a family from a different vendor second, so `.2` gives panels a second opinion. The `advice` role (the API rig's "ask Fable for advice" tool) and `judgment and prose` read this tier, so `claude-fable-5-1` through OpenRouter (`openrouter:anthropic/claude-fable-5.1`) goes first.
- `implementation`: capable, cheaper families for bounded work with a check behind it. On OpenRouter: the strongest DeepSeek coding model first, a cheaper DeepSeek second.
- `mechanical`: the cheapest family, for triage, formatting and summaries. On OpenRouter: a cheap DeepSeek flash model.
- `overseer`: the API rig's two overseers (`rig overseer` is `overseer-max`, `rig second overseer` is `overseer.2-max`). The strongest model OpenRouter serves first and the strongest from a different maker second: `rig-shape` refuses a `review` team whose two overseers resolve to one maker.

Put the OpenRouter families first in every tier and the Claude and Codex families after them, in their own order. `.n` counts only the families the asking runtime can run, so a Claude Code panel still gets a second family when the OpenRouter ones lead.

Drop any default family that was not detected. A tier left empty needs a choice. Show the tiers and ask whether to accept them. Prefer AskUserQuestion over free text.

**(b) Ask for a budget.** Offer these four options with these exact labels, and name the current budget when the file records one.

- `unlimited — keep max`
- `large — xhigh reasoning`
- `medium — high reasoning`
- `small — medium reasoning`

**(c) Apply it.** Build the working table from the defaults, and on a re-run keep any role you changed by tier, family, list, or alias. `unlimited` leaves every effort as in that table. `large`, `medium`, and `small` set the effort token of every slug, panel entries included, to `xhigh`, `high`, or `medium`. The effort token is the last hyphen token, on the ladder `max` > `xhigh` > `high` > `medium` > `low`; a slug without one, like `mechanical`, keeps none. So `small` turns `judgment-max` into `judgment-medium` and `implementation-xhigh` into `implementation-medium`. A concrete slug whose result is not detected takes the same family's detected slug with the highest effort at or below the target, else needs a choice. `inherit-parent` and `auto` do not change.

**(d) Show the roles and confirm.** Show every role with its slug and what it resolves to (`bin/pstack-model resolve '<role>' --all`), and list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the tier slugs, the detected families, and `inherit-parent` and `auto` (both mean: this role runs on the parent chat model). For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena selects one value from it whose model family differs from the parent's when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

### 4. Validate

Every family on a `tier` line and every concrete slug must be detected. `inherit-parent` and `auto` always pass. After writing, `bin/pstack-model resolve '<role>' --all` must print a model for every role. For the API rig, every `rig ...` role and `advice` must also resolve with `--runtime openrouter` (that runtime takes only OpenRouter families, never a subscription), and every role with `--runtime pi`. If anything fails, stop and ask again.

### 5. Write the file

Write `~/dev/dev-server/etc/pstack-models.md` (or, for a personal override, `~/.config/dev-platform/pstack-models.md`): the `# budget` line with the chosen label and its target effort, the `tier` lines, and one line per role, using the same labels dev-plat uses. Overwrite the whole file so re-runs stay idempotent. The defaults, which `bin/pstack-model defaults` prints:

```
# pstack model configuration. Tier lines map each tier to its model families, in order;
# role lines name a tier slug `<tier>[.<n>]-<effort>` or a concrete model. Delete a line to fall
# back to the default. `inherit-parent` or `auto`: the role runs on the parent chat model.
# OpenRouter first in every tier; the Claude and Codex subscriptions last (owner, 2026-10-12).
# budget: unlimited (max)
tier judgment: openrouter:anthropic/claude-fable-5.1, openrouter:openai/gpt-6-astra-pro, claude-opus-5-5, codex:gpt-6.1-sol, claude-fable-5-1
tier implementation: openrouter:deepseek/deepseek-v4-pro-0813, openrouter:deepseek/deepseek-v4.1-flash, codex:gpt-6.1-sol, claude-opus-5-5
tier mechanical: openrouter:deepseek/deepseek-v4.1-flash, openrouter:deepseek/deepseek-v4-flash, claude-haiku-4-5, codex:gpt-6-luna
tier overseer: openrouter:anthropic/claude-fable-5.1, openrouter:openai/gpt-6-astra-pro, codex:gpt-6.1-sol, claude-fable-5-1
feature, refactoring: implementation-xhigh
bug-fix: implementation-xhigh
perf-issue: implementation-xhigh
hillclimb: implementation-xhigh
judgment and prose: judgment-max
hardest tasks: judgment-max
how explorer: implementation-xhigh
how explainer: judgment-max
why investigators: implementation-xhigh
why synthesizer: judgment-max
reflect tooling: judgment.2-max
reflect judgment, divergent, synthesizer: judgment-max
arena runners: judgment-max, judgment.2-max, implementation-xhigh
arena cross-judge pool: judgment-max, judgment.2-max, implementation-xhigh
swarm workers: implementation-xhigh
architect runners: judgment-max, judgment.2-max, implementation-xhigh
interrogate reviewers: judgment-max, judgment.2-max, implementation-xhigh
advice: judgment-max
rig control: implementation-high
rig overseer: overseer-max
rig second overseer: overseer.2-max
rig worker: implementation-high
rig worker retry: openrouter:anthropic/claude-opus-5.5-high
assistant start: codex:gpt-6.1-sol
ops start: codex:gpt-6-luna
engineer start: codex:gpt-6-sol
```

The `rig control`, `rig overseer`, `rig second overseer` and `rig worker` lines are the API rig's seats and workers; `rig-shape write <project> review --all pi` and the loop's Pi workers resolve them with `--runtime openrouter`. The `<role> start` lines are the Pi roles' start models; under `--runtime pi` a `codex:` family runs on the OpenAI subscription and a Claude family is never picked, because Pi on Anthropic is metered and only chosen by hand. The loop reads two of these lines for its workers, through `bin/pstack-model --runtime claude`: `feature, refactoring` for implementation tasks and `judgment and prose` for tasks labeled `spec`, `decision`, `privacy` or `security`; `documentation` tasks take the `mechanical` tier. `MODELS.md` states what the tiers are for.

### 6. Confirm

Tell the user the file was written. A change to the repository's file is a change to the machine: commit it in `~/dev/dev-server`, and it applies to everyone at the owner's next `sudo ./bootstrap.sh` (bootstrap installs it; nothing else writes `/etc`). A personal override applies at once. Either way it reaches new sessions and workers the loop starts after this. Re-running this skill updates it.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill`. On no, move on without pushing.
