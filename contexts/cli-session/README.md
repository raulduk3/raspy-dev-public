# Context: a CLI session

You were started in a terminal, in a project folder.

- Read the repository's `AGENTS.md` (your agent may already have) and its specification
  (`docs/spec/`) before changing anything. A folder being a repository is not an assignment:
  work on what you were asked.
- One task per worktree. If you are on `main`, cut a branch into `worktrees/<type-slug>` first
  (`git worktree add -b <type/slug> worktrees/<type-slug> main`) and work there.
- Run the repository's check before you stop. The stop hook runs it too, and sends you back to
  work if it fails.
- Long jobs belong to `loop` workers or a team, not to this session.
- When you need the person and they may be away, the notify hook tells their phone; say plainly
  what you need.
