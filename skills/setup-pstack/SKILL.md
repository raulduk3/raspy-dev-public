---
name: setup-pstack
description: Configure which models pstack uses per role and at what reasoning budget. Detects your available models and writes the platform's model file that overrides the skill defaults. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices.
---

> **On this platform.** This is pstack's `setup-pstack` skill (MIT, Lauren Tan; the unmodified source is in `vendor/pstack`). This copy is adapted; `integrations/pstack/overlays/setup-pstack/` holds every change. Read [the platform map](../../docs/pstack-platform.md) (installed: `~/.local/share/dev-platform/current/docs/pstack-platform.md`) once per session: it says what the Cursor tools named here are on this machine, and which steps the guard hook leaves to the owner.

# Setup pstack

Write `~/.config/dev-platform/pstack-models.md`, the file that sets pstack's model per role on this platform. Every pstack skill reads it through the platform map, and the loop reads it for its workers. It replaces Cursor's `~/.cursor/rules/pstack-models.mdc`; the lines have the same shape.

## Steps

### 1. Detect available models

A slug here is `<model>-<effort>`. `<model>` is what the runtime accepts: for Claude Code the `Agent` tool's `model` (`fable`, `opus`, `sonnet`, `haiku`) or a full id that `claude --model` accepts (`claude-opus-5-5`); for Codex, `codex:<model>` as `codex --model` accepts it. `<effort>` is one of `max`, `xhigh`, `high`, `medium`, `low`, which `claude --effort` accepts. Confirm a model by running it once (`claude -p --model <model> --effort low 'reply ok'`, `codex exec --model <model> 'reply ok'`) or from the account's documented entitlements; `ai-account status` names the verified accounts. If you cannot detect any, ask the user to paste the models they have. Never write a real slug you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected slugs.

### 2. Load current state

The default role-to-model mapping is the file shape shown in step 5 below. If `~/.config/dev-platform/pstack-models.md` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer AskUserQuestion over free text. Offer these four options with these exact labels, and name the current budget when the file records one.

- `unlimited — keep max`
- `large — xhigh reasoning`
- `medium — high reasoning`
- `small — medium reasoning`

**(b) Apply it.** Build the working table from the skill defaults, and on a re-run keep any role you changed by family, list, or alias (`inherit-parent`, `auto`). `unlimited` leaves every effort as in that table. `large`, `medium`, and `small` set the effort token of every real slug, panel entries included, to `xhigh`, `high`, or `medium`. The effort token is the last token, on the ladder `max` > `xhigh` > `high` > `medium` > `low`. If the result is not a detected slug, use the same family's detected slug with the highest effort at or below the target, else mark the role as needing a choice. `inherit-parent` and `auto` do not change. So `small` turns `fable-max` into `fable-medium`, and `codex:gpt-5.6-sol-xhigh` into `codex:gpt-5.6-sol-medium`.

**(c) Show the roles and confirm.** Show every role with its model, marking any real slug not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models plus `inherit-parent` and `auto` (both mean: this role runs on the parent chat model) as the options. Prefer AskUserQuestion over free text. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena selects one value from it whose model family differs from the parent's when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

### 4. Validate

Every real slug written must be in the detected set. `inherit-parent` and `auto` always pass. If a chosen real slug is not available, stop and ask again.

### 5. Write the file

Write `~/.config/dev-platform/pstack-models.md` with a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels dev-plat uses. Overwrite the whole file so re-runs stay idempotent. Shape:

```
# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit the Agent `model`). Alias entries in a panel list still count toward its fan-out.
# budget: unlimited (max)
feature, refactoring: sonnet-high
bug-fix: sonnet-high
perf-issue: sonnet-high
hillclimb: sonnet-high
judgment and prose: fable-max
hardest tasks: fable-max
how explorer: sonnet-high
how explainer: fable-max
why investigators: sonnet-high
why synthesizer: fable-max
reflect tooling: codex:gpt-5.6-sol-max
reflect judgment, divergent, synthesizer: fable-max
arena runners: fable-max, codex:gpt-5.6-sol-max, sonnet-high
arena cross-judge pool: fable-max, codex:gpt-5.6-sol-max, sonnet-high
swarm workers: sonnet-high
architect runners: fable-max, codex:gpt-5.6-sol-max, sonnet-high
interrogate reviewers: fable-max, codex:gpt-5.6-sol-max, sonnet-high
```

The loop reads two of these lines for its workers: `feature, refactoring` for implementation tasks and `judgment and prose` for tasks labeled `spec`, `decision`, `privacy` or `security`. `MODELS.md` states the tiers these defaults follow.

### 6. Confirm

Tell the user the file was written and that it applies to new sessions and to workers the loop starts after this. Re-running this skill updates it.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill`. On no, move on without pushing.
