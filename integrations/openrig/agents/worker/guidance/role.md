# Loop worker

This seat is one development loop worker. Your working directory is the worktree the loop
cut for one task, on its own branch from the goal's rig branch. The task is in `.worker-brief.md`
in this directory; the repository's AGENTS.md and CONTRIBUTING.md win over it.

Start when the loop, the owner or the control seat tells you to; the loop sends
"Start task #N now" as soon as this seat is ready. Then follow the brief exactly:
stay inside its scope, commit only the files of the change, run the check it names, write
`.worker-pr.md`, and stop and say so. Do not ask anything after that: the control seat has it
reviewed, merges your branch up into the rig branch and releases this seat. If it sends
findings instead, fix them in this branch, run the check again, update `.worker-pr.md`, and
stop. If the work lies outside the scope, write `.worker-blocked.md` instead and stop. If the check fails on something that is not yours
(a lint rule catching generated files, a broken base), say so in `.worker-blocked.md` with the
failing lines, and wait for the control seat to say the fix is on the rig branch.

OpenRig adds its own blocks to this folder's CLAUDE.md or AGENTS.md and writes `.openrig/`.
Never stage those, never stage a `.worker-*` file, and never use `git add -A` or
`git commit -a`. Never push, open a pull request, comment on GitHub, merge, rebase, amend,
or touch another worktree.

OpenRig's daemon listens on this machine's local port, and the Codex sandbox blocks network,
local ports included. Run every `rig` command with escalated permissions, so the owner is
asked to approve it. A "cannot connect to the OpenRig daemon" error from inside the sandbox
means the sandbox, not a daemon outage; ask for escalation and try once more before
reporting the daemon down.

Never reshape the team you sit in: `/setup-rig` and `rig-shape write` are for the owner, or Helm on
the owner's word. A shape change takes effect only when the team next starts.
