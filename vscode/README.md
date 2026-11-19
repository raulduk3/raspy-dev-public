# Editor surface (VS Code), not in use

The owner edits with Zed over SSH, not VS Code or Cursor (2026-10-05). Nothing here is
installed on the Mac. The working setup, including Zed's Claude Agent and Codex external
agents running on dev-server, is `docs/remote-clients.md` in the dev-server repository. This
folder is kept for a VS Code user.

The editor is where the owner reads diffs and decides. Copilot Chat is a VS Code built-in and
never appears in the extensions list; the Claude Code and Codex extensions sit beside it. All
three read the same rules:

The editor runs on the owner's Mac and works on dev-server over Remote-SSH (`ssh-remote+dev-server`):
the Mac holds no project state, and the Claude Code, Codex and Copilot extensions run in the
remote extension host on dev-server, so the hooks are dev-server's. Copilot does not run in Cursor.
The per-client setup (VS Code, Cursor, Claude Desktop, Codex, ChatGPT) is
`docs/remote-clients.md` in the dev-server repository.

- `dev-platform.instructions.md`: user-level chat instructions, installed by copying into the
  Mac's VS Code profile `prompts/` folder (`~/Library/Application Support/Code/User/prompts/`);
  it is editor configuration, so it lives on the Mac although projects do not. `applyTo: "**"` makes it apply
  to every chat and agent request in every workspace. Inside a repository, `AGENTS.md` still
  wins; Copilot reads it natively.
- `settings.snippet.jsonc`: the terminal auto-approve list, merged into the user `settings.json`.
  It is the same allow and deny set as `hooks/codex.rules` and `hooks/pre-tool-use-guard.sh`.
  `false` entries prompt the owner every time; the Claude Code guard refuses the same commands
  outright.
- The Claude Code hooks from `hooks/` apply inside the extension the same as in the terminal.

Workspace layout for a project: one `<project>.code-workspace` file on dev-server, outside any repository,
with the main checkout and the platform repository as folders. Live worktrees are added as
folders while they are active and removed when their pull request merges. Worktree directories
under the checkout are excluded from search so the same file never appears twice.

Copilot code review and the Copilot coding agent are enabled only on repositories under this
account. On repositories where the owner is the only identity, review comes from `codex review`
and local review, and coding agents run locally.
