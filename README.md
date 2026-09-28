<h1 align="center">raspy-dev</h1>

<p align="center"><em>Say the goal. Watch a team of coding agents build it on one branch. Land it yourself.</em></p>

<p align="center">
  <a href="https://github.com/raulduk3/raspy-dev-public/actions/workflows/check.yml"><img alt="check" src="https://github.com/raulduk3/raspy-dev-public/actions/workflows/check.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-3fb950"></a>
  <img alt="Python 3" src="https://img.shields.io/badge/python-3-3776ab?logo=python&logoColor=white">
  <img alt="Bash" src="https://img.shields.io/badge/bash-scripts-4eaa25?logo=gnubash&logoColor=white">
  <img alt="Runs locally" src="https://img.shields.io/badge/runs-locally-8250df">
</p>

<p align="center">
  <a href="#start"><img alt="Start" src="https://img.shields.io/badge/%E2%96%B6%20Start-111?style=for-the-badge"></a>
  <a href="skills/loop/SKILL.md"><img alt="The loop" src="https://img.shields.io/badge/The%20loop-d97757?style=for-the-badge&logo=anthropic&logoColor=white"></a>
  <a href="skills"><img alt="Skills" src="https://img.shields.io/badge/Skills-0969da?style=for-the-badge"></a>
  <a href="docs"><img alt="Docs" src="https://img.shields.io/badge/Docs-6e7781?style=for-the-badge"></a>
</p>

A small local platform that keeps AI-assisted software work bounded and reviewable. Claude Code, Codex and [OpenRig](https://www.openrig.dev) seats share one set of hooks, skills and templates. Git is the record, and a human is the only one who merges.

## Start

```bash
git clone https://github.com/raulduk3/raspy-dev-public.git && cd raspy-dev-public
./bin/check                               # offline test suite: bash, git, python3, jq, PyYAML
./bin/new-repo ~/Dev/tetris --register    # a new repository to the standard
```

Then, in that repository, ask your agent to use the `intake` skill to spec the goal and the `loop` skill to build it: one branch per goal, one child branch per task, children merge up once their check passes, and you land the goal.

## Inside

| | |
| --- | --- |
| [`skills/`](skills) | intake, loop, tdd, architect, spec-lint and the engineering principles |
| [`hooks/`](hooks) | guard, format, stop and session-length hooks for Claude Code and Codex |
| [`templates/`](templates) | what `new-repo` copies into every project |
| [`integrations/`](integrations) | OpenRig seats and shapes, pstack, VS Code |
| [`docs/`](docs) | model routing, rules, runbooks and the rest |

## License

[MIT](LICENSE). `vendor/pstack` is MIT, © its upstream author; see [`vendor/pstack/UPSTREAM`](vendor/pstack/UPSTREAM).
