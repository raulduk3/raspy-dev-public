<p align="center">
  <img src="docs/images/raspy-dev.jpg" alt="A terracotta bowl with animals carved in relief around its rim" width="360">
</p>

<h1 align="center">raspy-dev</h1>

<p align="center"><em>One small cockpit for many AI tools. Say what you want; watch a team build it on one branch; land it yourself.</em></p>

A small local platform for keeping AI-assisted software work organized, bounded and reviewable.

Not a framework or a product. It is the glue around an editor, a terminal and a few coding agents: templates, hooks, checks, skills and a loop. Every tool can help, git holds the truth, and a human is the only one who merges.

## Try it

```text
./bin/check                               the offline test suite
./bin/new-repo ~/Dev/tetris --register    a new repository to the standard
```

Then ask your agent for the `intake` skill to spec the goal, and the `loop` skill to build it.

```text
goal
  -> decision, spec and task files
  -> a goal branch, and a child branch per task
  -> workers in their own worktrees
  -> checks and guardrails
  -> merged up, then landed by you
```

## Where things are

```text
bin/           commands
skills/        intake, loop and the rest
hooks/         guardrails for Claude Code and Codex
templates/     what every new repository starts with
integrations/  OpenRig, pstack, VS Code
docs/          everything else
```

MIT. `vendor/pstack` keeps its own license.
