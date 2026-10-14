# Contexts

The same rules (`AGENTS.md`) and skills (`skills/`) are used from different places. Each folder
here is a thin adapter: it says only what differs in that place. A skill never changes per
context; when behavior must differ, the difference goes in the adapter.

| Context | Who uses it |
| --- | --- |
| `cli-session/` | An agent started in a project folder |
| `editor/` | An agent panel inside an editor |
| `desktop-app/` | A chat app on another device, reaching this machine through MCP or SSH |
| `team-seat/` | A seat in a team (`teams/`) |
| `persona/` | A named, long-lived assistant (`roles/`) |

Agent-specific wiring lives only here, in `cli-session/<agent>/`: an `install.sh` that
`setup/link.sh` runs when that agent is installed. It links this repository's instructions,
skills, hooks and MCP servers into the agent's own configuration.

## Add a context

Add `contexts/<name>/README.md` saying what differs there, and name it in the list in
`AGENTS.md`. To support another agent, add `contexts/cli-session/<agent>/install.sh` (copy one
of the others; it receives `ROOT`, the repository path) and, if the agent has its own
instruction file name, add that name to `contexts/cli-session/instruction-files`.
