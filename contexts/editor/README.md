# Context: an editor panel

You are an agent panel inside an editor, with a person watching the diff.

- The same rules as a CLI session. Edits happen in the folder the editor has open; if that is
  `main`, ask the person to open a worktree (or open one for them) before you change files.
- No long-running jobs, servers or watchers from the panel; leave those to a terminal, `loop`
  or a team.
- Report the check's output as it is. Draft the commit message; the person commits.

Editors that reach this machine over SSH (for example a remote-development mode) run the agent
here, so this machine's instructions, skills and hooks apply unchanged. Editors that read their
own instruction file name use the link `new-repo` makes to `AGENTS.md`.
