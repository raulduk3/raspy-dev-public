# raspy-dev

Turn a Linux or macOS machine into an AI-ready development server: your coding agents installed
and signed in with your own accounts, reachable from your other devices, sharing one set of rules
and skills, working one task per git worktree, never merging or pushing `main`, and pinging your
phone when they need you. Git holds the truth; a person is the only one who merges.

No daemon, database or broker of its own: the agents' own hooks, skills and MCP support, plus git,
Tailscale, ntfy and (optionally) OpenRig.

## Setup (about 20 minutes)

1. Fork this repository (your skills, models and MCP servers will live in your fork), then clone
   it on the machine: `git clone https://github.com/<you>/raspy-dev ~/raspy-dev`.
2. Run the setup for your OS. It asks which agents to install and your git name and email.
   <!-- agents:begin -->
   ```sh
   AGENTS="claude codex pi" ~/raspy-dev/setup/linux.sh   # or setup/macos.sh; pick any of the three
   ```
   It installs git, gh, jq, ripgrep, tmux, Node 22+, Tailscale and the agents you chose
   (Claude Code, Codex, Pi), turns on SSH, keeps the machine awake, and links everything below.
   Add `TEAMS=1` to install OpenRig.
3. Sign in to each agent with its own login: run `claude`, `codex` or `pi` once and follow it.
   One account per provider; never rotate accounts to dodge limits.
4. Codex only: run `/hooks` once in a Codex session to trust the hooks.
   <!-- agents:end -->
5. Join your tailnet: `sudo tailscale up --ssh`. Install Tailscale on your laptop and phone too.
6. From your laptop: `ssh <machine-name>` (its tailnet name). Use `tmux` so sessions survive.
7. Install the ntfy app on your phone and subscribe to the topic setup printed (also in
   `~/.config/notify/topic`). Test: `notify "hello" "from the server"`.
8. Fill in `models.md`: your models, by tier.
9. Remote features: start agents with their own remote mode to drive them from a phone or the web
   <!-- agents:begin -->
   (Claude Code: `claude remote-control` inside tmux, or `/remote-control` in a session)
   <!-- agents:end -->.
10. Start a project: `new-repo ~/code/hello`, `cd` in, open your agent, and ask it to use the
    `intake` skill on your goal, then `loop` to build it.

Run `setup/link.sh` again whenever you change skills, `mcp.json`, contexts or hooks.

## What you get

| Piece | Where |
| --- | --- |
| One instruction file for every agent | `AGENTS.md` (other names link to it) |
| Skills: intake, loop, interrogate, architect, tdd, how, why, recall, ... | `skills/` |
| Guard: no push to `main`, no merge into it, no history rewrite, no secrets | `hooks/guard`, `hooks/git/` |
| The repository's check before an agent stops | `hooks/check-before-stop` |
| Phone alerts for agents that need you and failed services | `hooks/notify`, ntfy |
| Goal branch → task worktrees → check → merge up → a person lands | `bin/loop`, `skills/loop` |
| New repositories with the same rules | `bin/new-repo`, `templates/` |
| Teams of agents | `teams/*.yaml` (OpenRig), `roles/` |
| Differences per place (terminal, editor, desktop app, team seat, persona) | `contexts/` |

## Extend it

Every extension is one file or one line. Then run `setup/link.sh`.

**A skill**: a folder with a `SKILL.md` (Agent Skills format).
```markdown
---
name: changelog
description: Write the changelog entry for the current branch. Use before opening a pull request.
---
```

**A tool**: one entry in `mcp.json`, shared by every agent.
```json
{ "mcpServers": {
  "github": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"] }
} }
```

**A model or account**: one line under its tier in `models.md`; sign in with the agent's own login.
```markdown
## implementation
- provider/model-name    reasoning: high
```

**A role or persona**: one markdown file in `roles/`.
```markdown
# Release manager
## You own
Release notes and tags, after a person approves.
```

**A team**: one OpenRig file in `teams/`; start it with `rig up teams/<name>.yaml --cwd <project>`.
<!-- agents:begin -->
```yaml
pods:
  - id: review
    members: [{ id: reviewer, agent_ref: local:seat, profile: default, runtime: codex, cwd: ".", startup: { files: [{ path: roles/reviewer.md, delivery_hint: guidance_merge }] } }]
```
<!-- agents:end -->

**A context**: one folder in `contexts/` with a `README.md` saying what differs there.
```markdown
# Context: a scheduled job
No person is watching: never ask, write what you need into the task file and stop.
```

## Check

`./check` tests this repository: scripts parse, skills are valid, JSON parses, the tests pass, no
file outside `contexts/` and `setup/` names a model, vendor or agent, nothing private is in the
tree (patterns, gitleaks when installed, and your own deny-list in
`~/.config/raspy-public/denylist.txt`), and scripts stay under 1,500 lines.

## Advanced

<!-- agents:begin -->
- A local model: run llama.cpp's server or Ollama yourself, on demand, listening on localhost; add
  it to `models.md` under `mechanical`.
<!-- agents:end -->
- Separate Unix users per persona keep files and logins apart. Optional; not set up here.

MIT. See `LICENSE` and `NOTICE`.
