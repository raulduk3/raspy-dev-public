# Editor surface (VS Code)

The editor is where the owner reads diffs and decides. Copilot Chat is a VS Code built-in and
never appears in the extensions list; the Claude Code and Codex extensions sit beside it. All
three read the same rules:

- `settings.snippet.jsonc`: the terminal auto-approve list, merged into the user `settings.json`.
  It is the same allow and deny set as `hooks/codex.rules` and `hooks/pre-tool-use-guard.sh`.
  `false` entries prompt the owner every time; the Claude Code guard refuses the same commands
  outright.
- The Claude Code hooks from `hooks/` apply inside the extension the same as in the terminal.

Workspace layout for a project: one `<project>.code-workspace` file outside any repository,
with the main checkout and the platform repository as folders. Live worktrees are added as
folders while they are active and removed when their pull request merges. Worktree directories
under the checkout are excluded from search so the same file never appears twice.

Copilot code review and the Copilot coding agent are enabled only on repositories under this
account. On repositories where the owner is the only identity, review comes from `codex review`
and local review, and coding agents run locally.
