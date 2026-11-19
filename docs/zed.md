# Zed on the Mac

Zed on the Mac (laptop) edits files on dev-server with Zed remote development. Claude Code and Codex write code. The Zed built-in agent only reads. This setup implements SDD-SC-16.

Zed has no platform guard. Git hooks and server rules still apply (see `docs/source-control.md`).

## Remote development

The Zed remote server 1.26.2 is installed on dev-server. The Zed app on the Mac must run the same version.

1. Open Zed on the Mac.
2. Run the action `projects: open remote` (command palette).
3. Choose `ssh://dev-server`, or add the host to `ssh_connections` in `settings.json`.
4. Open `~/dev/<project>` or `~/dev/<group>/<project>` on dev-server.

```json
{
  "ssh_connections": [
    { "host": "dev-server", "projects": [{ "paths": ["/home/owner/dev"] }] }
  ]
}
```

Do not open a project from a copy on the Mac. The work stays on dev-server, where the guards run.

## Writes: Claude Code or Codex over ACP

Use an external agent for every write. Zed starts it on dev-server and talks to it over the Agent Client Protocol (ACP). The guards of that agent apply.

1. Open the agent panel.
2. Choose New Claude Code thread or New Codex thread from the plus menu.
3. Ask for the change. The agent follows the tier of the repository (`dev-loop tier <path>`).

If the thread entry is missing, add the agent in `agent_servers`. Check in Zed settings: the key and the fields differ between Zed versions.

```json
{
  "agent_servers": {
    "claude": { "default_mode": "default" }
  }
}
```

## The Zed built-in agent reads only

Use the built-in agent to read and explain code. Do not use it to write. Set these values in `settings.json`. Names marked "check in Zed settings" can differ in your Zed version.

```json
{
  "agent": {
    "default_profile": "ask",
    "always_allow_tool_actions": false,
    "tool_permissions": { "default": "confirm" }
  }
}
```

- `agent.default_profile: "ask"` selects the read-only profile. Check in Zed settings.
- `agent.always_allow_tool_actions: false` makes the agent ask before each tool. Check in Zed settings.
- `agent.tool_permissions` with `default: "confirm"` (or `"deny"` for the edit and terminal tools). Check in Zed settings.
- Do not select the `write` profile. Do not approve an edit from the built-in agent.

## Check

1. Open a project on dev-server in Zed.
2. Start a Claude Code thread. Ask it to print `dev-loop tier .`.
3. Start a built-in agent thread. Confirm that it cannot edit a file without a prompt.
