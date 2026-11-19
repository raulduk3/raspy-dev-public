# Skills layer

The skills layer is not a bag of project-specific prompts. It is the routing layer that lets every surface in the local AI ecosystem ask the same questions before it acts:

1. What project, repository, worktree or engagement owns this work?
2. What state is already live: sessions, rig seats, loop workers, PRs, artifacts, account bindings?
3. Which surface should hold the next step?
4. What context must be hydrated before editing, dispatching, reviewing or stopping?
5. What evidence will prove the work is safe to hand back?

A skill is good when it is reusable across surfaces. A skill is bad when it only remembers one old project, one provider, one customer, or one incident.

## Where skills run

raspy-dev expects the same skill contracts to be reachable from several places:

| Surface | How skills should behave |
| --- | --- |
| Pi roles | Use skills to orient the role, find the owning project, read durable context, and hand off to the right surface. A personal role can read engineering context for billing or coordination, but does not become an engineering gate. |
| Claude Code and Codex desktop sessions | Use skills as modes and playbooks. The desktop app may be flexible, but it still writes code in a worktree, uses the same hooks, and leaves durable work on the ledger. |
| CLI/headless workers | Use narrow skills from a written brief: one issue, one branch, one worktree, one check, one report, then stop. |
| OpenRig seats | Use skills to hydrate a seat with project identity, current loop state, nearby seats, allowed actions, and handoff rules. A rig seat is a conversation with a role, not a second scheduler. |
| Herdr/team spaces | Use skills to show the current project, rig seats, loop state, and active checks in one place. Herdr is a view, not a source of truth. |
| VS Code/editor chat | Use skills for surgical edits, PR walkthroughs, and review finding disposal while the owner is present. |

## Deterministic verb resolution

Skill prose should name the deterministic surface for a verb when the object is owned by the ecosystem. Do not make the model infer how to "read", "check", "open", "list", "run" or "write" an owned object from context alone. Resolve the object first, then use the narrowest platform or project tool that preserves its IDs, format and authority. Fall back to direct files only when no configured tool exists, and say that the fallback happened.

| Verb + object | Deterministic path |
| --- | --- |
| Find or open a project/worktree | `ai-work projects`, `repos.conf`, then Git evidence from the resolved checkout |
| Read a specification | The project's configured spec reader first; otherwise `docs/spec/SDD.md`, `docs/spec/TDD.md` and referenced docs/code, preserving native item IDs |
| Read decisions or tasks | `dev-loop tasks <repo>` for local repositories; `ghx`/GitHub for owner or bot repositories; direct task files only as a fallback or for editing the assigned file |
| Read sessions, handoffs or conversation ownership | `ai-session` and the recorded conversation/handoff, not transcript search by guess |
| Read loop state or dispatch loop work | `dev-loop`/`ai-work loop`; never a parallel task ledger |
| Read rig, seat or team state | `rig`, `herdr` and the engagement folder's `rig.yaml`; do not infer from window titles |
| Check a specification | `spec-lint` plus any project-specific spec check |
| Check local task format | `dev-loop tasks <repo> check` |
| Check a branch or implementation | The repository's declared check command on the candidate head; report exact output |
| Create or update repo records | The owning command or template (`new-repo`, `dev-loop tasks`, `ghx`, decision template) rather than freehand prose |

This is a writing rule for skills, not a requirement to automate every action. If the surface lacks a tool, the skill should say which direct files are the fallback and what evidence proves the result.

## Skill families

The target shape is a small set of ecosystem skills, plus project-local verification skills when a repository needs them.

### 1. Entry and routing

Purpose: get the session into the right lane.

Good skills:

- identify whether the request is personal, operations, repository work, review, loop control, or exploratory planning;
- find the current project and worktree using `ai-work`, `ai-session`, repo config and live process evidence;
- refuse to infer authority from a directory name, chat title, or old transcript;
- name the next surface if the current one is wrong.

### 2. Context hydration

Purpose: make a seat useful without dumping the whole machine into context.

Good skills:

- resolve each owned object through its deterministic reader first: project docs/spec readers, `ghx` or `dev-loop tasks`, loop ledger commands, `ai-session` titles and handoffs, and recent artifacts;
- summarize only what the seat needs to act;
- include live ownership: running workers, active rig seats, current branch, account/profile binding;
- avoid private transcripts and raw notes unless the surface is explicitly allowed to read them.

### 3. Project and filesystem boundaries

Purpose: stop the Desktop-script problem and similar drift.

Good skills:

- decide where helper scripts, screenshots, traces, notes and generated files belong;
- keep source code in repositories, artifacts in engagement/project artifact folders, and private notes outside public repos;
- stop and propose a destination map when ownership is unclear.

### 4. Loop and worker operation

Purpose: coordinate rigorous parallel work without making a second ledger.

Good skills:

- inspect loop status, plan work, dispatch only authorized issues, collect results and close a reviewed day through `dev-loop` or `ai-work loop`;
- hydrate workers with exact scope, account/profile, branch, stop condition and check command;
- prevent stale sessions or rig seats from steering work they do not own.

### 5. Review and verification

Purpose: prove the work, not just narrate it.

Good skills:

- read diffs from the candidate head, run the repository's declared check, reproduce bugs on the real surface, inspect runtime artifacts with their owning command, and write reviewable findings;
- separate evidence from opinion;
- never approve or merge on behalf of the owner.

### 6. Intake, distillation and decisions

Purpose: turn private or messy input into public-safe engineering work.

Good skills:

- keep raw notes, calls and messages outside public repositories;
- distill candidate requirements into generic, redacted records;
- promote accepted decisions into spec diffs and implementable issues.

### 7. Operations and deploy verification

Purpose: diagnose and verify systems without accidental mutation.

Good skills:

- read health, logs, deploy records and status through the service's documented operational commands;
- require explicit current-session authorization for restarts, deployments, credential changes or provider mutations;
- leave a concise verification record.

## What to retire or rewrite

A skill should be rewritten when it:

- names a single old project, customer, provider incident or host as its normal path;
- stores policy that belongs in `ROLES.md`, `MODELS.md`, repository `AGENTS.md`, or a docs contract;
- dispatches work instead of selecting the correct dispatcher;
- requires hidden context from one chat to make sense;
- makes a rig seat, desktop chat, Pi role or CLI worker behave differently for the same repository boundary.

Project-specific knowledge should live in the project repository, project artifact folder, engagement state, or private notes. raspy-dev skills should describe reusable moves.

## Current bundled skills

| Skill | Keep? | Direction |
| --- | --- | --- |
| `loop` | Yes | Core ecosystem skill. It owns local worker dispatch and should become the common rig/agent/desktop path for active loop work. |
| `intake` | Yes | Keep generic. It should remain the public-safe bridge from private notes to decisions/spec issues. |
| `distill` | Yes, but narrow | Keep as a candidate extractor, not a hidden project planner. |
| `spec-lint` | Yes | Repository-standard verification. |
| `new-repo` | Yes | Project bootstrap. |
| `morning-brief` | Retired | The skill and its job were removed; no release holds it. |

## Desired frontier-developer experience

The ideal flow feels like this:

1. Open a project in Herdr/OpenRig/VS Code/Claude/Codex/Pi.
2. The session knows the project identity, current branch, active loop, account profile, and nearby seats.
3. A mode skill decides whether this is investigation, implementation, review, ops, intake, cleanup or pause/resume.
4. If active loop work is appropriate, the session joins the existing loop instead of creating another one.
5. If a rig seat is spawned, it receives a small hydration packet: mission, repo, branch/worktree, current evidence, allowed actions, peers and stop condition.
6. Work ends with a check, artifact, PR body, review finding, decision record or explicit handoff. No orphan scripts, mystery sessions or private-only state.

The point is not to force every task through automation. The point is that when automation is useful, every tool joins the same map.
