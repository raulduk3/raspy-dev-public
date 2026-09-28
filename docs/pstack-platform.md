# pstack on this platform

pstack is Lauren Tan's (poteto's) set of engineering skills for Cursor, MIT licensed. This
platform uses it as its engineering method: `/dev-plat` is the front door for any engineering
task that needs rigor, and its playbooks, principles and routed skills are the shared contract
between every tool, agent and seat that writes code here. Her text is kept as she wrote it. This
page says what her Cursor-specific names mean on this machine. Where her text and this page
disagree about a tool name, this page wins. Where they disagree about method, hers wins.

## Where it lives

| Path | What |
| --- | --- |
| `vendor/pstack/` | Her tree, unmodified, at the commit in `vendor/pstack/UPSTREAM`. Never edit it. |
| `skills/<name>/` | The installed copies, built by `bin/pstack-port`. The list is `integrations/pstack/ported.txt`. |
| `integrations/pstack/overlays/<name>/` | Whole-file adaptations that replace the vendored file. Today only `setup-pstack`. |
| `~/.config/dev-platform/pstack-models.md` | The per-role model file `/setup-pstack` writes (her `pstack-models.mdc`). |

A port changes little. Her front door, `poteto-mode`, is named `/dev-plat` here, in its folder,
frontmatter, description and every mention in her Markdown (her TypeScript keeps its internal
names). In every skill the frontmatter `name` becomes the folder name, and one line after the
frontmatter points here. `bin/pstack-port --check` (run by `bin/check`) fails when
`skills/` drifts from a fresh port.

To take a newer pstack: replace `vendor/pstack/` with the new upstream path, update `UPSTREAM`,
run `bin/pstack-port`, read `git diff skills/`, and fix any overlay the upstream change touched.

Not ported: `make-bot-ui` (it drives Cursor Automations webhooks) and the `automations/benny`
skills (Cursor Automations triage and reproduce bots). They stay in `vendor/` for reference.

## Reaching a skill her text names

Her skills set `disable-model-invocation: true`: a person starts one with `/<name>`, and
`/dev-plat` reaches the rest by reading them. "The **how** skill" means read
`skills/how/SKILL.md` in full, next to the skill you are in (installed:
`~/.agents/skills/how/SKILL.md`, or `~/.local/share/dev-platform/current/skills/how/SKILL.md`).

## Cursor names and what they are here

| Her text says | On this platform |
| --- | --- |
| A `Task` subagent, `Task` tool | Claude Code's `Agent` tool (`run_in_background: true`, `subagent_type: general-purpose`). Codex: its own subagents, or `codex exec` started in the background. |
| `subagent_type: "dev-plat-agent"` | `general-purpose`, with the brief's first line: read `skills/dev-plat/SKILL.md` in full, including its Principles index. |
| A model slug in `model:` | The first word of the role's line in `pstack-models.md`. Claude `Agent` takes `fable`, `opus`, `sonnet`, `haiku`; the effort token applies only where a process is started (`claude --effort`). A `codex:<model>` entry runs as `codex exec --model <model>`. |
| `environment: "cloud"`, cloud VM, `cloud_base_branch` | There is no cloud. A worker runs on this machine in its own git worktree: `Agent` with `isolation: "worktree"`, a loop worker, or an OpenRig worker seat (`dev-workspace add-worker`). A base branch means the worktree is cut from that local branch. |
| `~/.cursor/rules/pstack-models.mdc` | `~/.config/dev-platform/pstack-models.md`, written by `/setup-pstack`. Missing file or line: her skill default, read through this table. |
| `.cursor/skills/` (project), `~/.cursor/skills/` (user) | `.claude/skills/` and `.agents/skills/` in the repository; `~/.claude/skills/` and `~/.agents/skills/` for the user. A skill for every repository belongs in this platform's `skills/`. |
| Cursor's built-in `create-skill` | The Authoring playbook with the `skill-creator` skill where the client has it. Validate with `tests/test_skill_frontmatter.py`'s rules: strict YAML, `name` equal to the folder, a whole description. |
| `AskQuestion` | `AskUserQuestion` in Claude Code. Elsewhere, a question with numbered options. |
| `agent-transcripts/` for the active workspace | Claude Code: `~/.claude/projects/<workspace path with / as ->/*.jsonl`. Codex: `~/.codex/sessions/<yyyy>/<mm>/<dd>/*.jsonl`, filtered by `cwd`. Her rule stands: only the active workspace's records. |
| Cursor's `/loop`, wake chain, heartbeat | Claude Code's `/loop` and a background `Monitor` or shell watcher. The development loop's `dev-loop tick` is the owner's to schedule, never an agent's. |
| `cursor-team-kit` `/deslop` | The `simplify` skill on the diff. |
| `control-ui` | The built-in browser pane or Claude in Chrome, or the `run` skill. |
| `control-cli` | The real terminal, or the `run` skill. |
| Cursor's built-in babysit skill | Not present. Her Babysit playbook is the only one. |
| Bugbot, agentic security review | GitHub review comments when a repository has them; `/code-review` and `/security-review` otherwise. Same skeptical triage. |
| MCPs "the Cursor environment" exposes | The session's MCP servers; `ToolSearch` lists deferred ones. |
| The Cursor dashboard (cloud agent status) | `rig ps` and `rig_rig_nodes` for seats; `dev-loop status` for loop workers. |
| `origin pr` (Origin forge) | Not installed. `gh` is the forge. |
| `gt` (Graphite) | Not installed. Her Opening a PR playbook already says never require it. `orch frontier set` needs it; until a gh-based frontier exists, compute the frontier from `gh pr list` and `git`. |
| `bun scripts/...` (orch, watch-pr) | Run with `~/.bun/bin/bun` from `skills/dev-plat/scripts` after `bun install`. |

## Repositories without a forge

`repos.conf` marks each repository `local`, `owner` or `bot`. A `local` repository has no pull
requests. Every step that opens, edits or watches a pull request becomes: the branch is ready,
its briefing-style body (her Opening a PR sections) is in the worker's `.worker-pr.md`, and the
owner merges it into the base with `git merge --no-ff` in a terminal. Tasks are `docs/tasks/`
files (see the `intake` and `loop` skills); a task number is the issue number her text cites.

## What the guard hook leaves to the owner

`hooks/pre-tool-use-guard.sh` refuses these for every agent in every repository. Her playbooks
run them; here the agent stops at the step and hands it to the owner, with the exact command.

| Her step | Refused | What happens here |
| --- | --- | --- |
| Opening a PR: rebase into small ordered commits; amend a just-made commit | `git rebase`, `git commit --amend`, `git reset --hard` | Commit in the intended order as you go. A fix to an earlier commit is a new commit. |
| Stacks: a child rebases onto its parent's tip; Shipping rebases the bottom PR onto trunk | `git rebase`, force push | Merge the parent into the child (`git merge <parent>`), or ask the owner to restack. |
| Shipping, Autopilot-full: merge the verified bottom PR | `gh pr merge`, merges into `develop` or `main` | Stop at merge-ready with the per-PR verdict. The owner merges. |
| Babysit: mark ready | `gh pr ready` | Opening ready (`gh pr create` without `--draft`) is allowed and is her default. |
| Pushing | Push to `develop` or `main`, force push, a bare `git push` | Push only the named `type/slug` branch. |
| Deploys, restarts | docker, systemctl, ssh mutations | The owner, every time. |

In a professional repository (not in `personal.conf`) nothing that reaches GitHub names a tool or
model, and the platform's publication rules decide whether an agent pushes at all.

## Seats and the development loop

In her Orchestrate playbook one coordinator owns the program and writes briefs; workers own units;
a verifier on a different model family checks each unit. On OpenRig that is: the `control.lead`
seat runs `/dev-plat` and follows Orchestrate; each `workers.*` seat runs `/dev-plat` with
the playbook its brief names (Feature, Bug fix, Refactoring); the `review.overseer` seat runs
`/interrogate` on a finished unit. Every brief carries her fields: GOAL, SCOPE, CONTEXT,
ACCEPTANCE, VERIFY, TIMEBOX, FORBIDDEN, REPORT, STANDING. The seat definitions under
`integrations/openrig/agents/` do not yet install these skills; that is the next change.

### Branches, not days

A branch is the only unit of work. A goal gets one ordinary `type/slug` branch cut from the base,
the rig branch (`dev-loop start <repo> feat/snake-game`). Each task gets a child branch cut from
it. A child whose check passes merges up into the rig branch; the control seat does that with
`dev-loop fold`, which also releases the worker's seat. The rig branch reaches the base once, by
the owner: a local merge, or one pull request. That is her stack with one level, landed by merge
instead of rebase, which the guard hook refuses. The loop is a way to repeat this until the goal is
done, not a daily clock.
