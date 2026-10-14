---
name: recall
description: "Reconstruct your recent working context from the repository's own record (git history, branches, worktrees, task files, decision records), your agent's native session history, and the shared record (user reports, prior fixes, incidents), then hand back a tight current-state brief. Use for 'recall my work on X', 'catch me up', 'what have I been working on', 'where did I leave off', before starting or resuming work."
---

# Recall

**Before you start or resume work, you rebuild the user's recent working context and hand back a tight capsule of where things stand now and what to do next.**

Keep it tight and on-topic. Read only what the in-scope threads need, then stop.

Your context lives in three records. The repository holds what was actually done: commits, branches, worktrees, task files and decision records. Your agent's native session history (its resume or history feature) holds what was discussed and decided but never committed. The shared record holds everything that happened around the same code under other names: the symptoms users keep reporting, the fixes that shipped and got reverted, the errors still firing in prod. That third record is what the **why** skill searches, across source control, the issue tracker, chat history, long-form docs, and error tracking. A feature with a long bug tail keeps most of its story there, so don't reconstruct it from your own history alone.

1. Classify, then route. Resuming one specific prior chat is your agent's native resume feature, not this. A human-readable summary of your work is a different task. Recall loads working context across recent work before you act. If the user already gave you a full state capsule (paths, branch, the change), use it and skip the mining.
2. Lock the scope before searching. Pin the window ("recent" is a real range, default the last 7 days), the topic if named, and the repository (default the current one. Never read another project's history without being asked). State the scope back. Never quietly turn "all" into "recent N".
3. Read the repository's record.
   - `git log --since=<window> --all --oneline --decorate` (add `--author=<you>` when several people commit, and `-- <path>` when the topic names an area). Read the full message of each commit that bears on the topic.
   - `git reflog --date=iso -n 50` for what was checked out, rebased, reset or amended, including work that never reached a branch.
   - `git branch -a --sort=-committerdate` and `git worktree list` for work in flight. For each in-scope branch, `git log <base>..<branch> --oneline` and `git status` in its worktree, to see what is committed, what is not, and whether it was merged.
   - `docs/tasks/` for task files changed in the window (`git log --since=<window> --name-only -- docs/tasks/`): their `Scope:` and `Depends on:` lines, and which moved to `docs/tasks/done/`.
   - `docs/decisions/` for decision records proposed or accepted in the window, and their `Status:`.
   - In a GitHub-backed repository, `gh pr list --state all --search "updated:>=<date>"` and `gh issue list --state all --search "updated:>=<date>"`.
4. Read your own session history. Use your agent's native resume or history feature to list sessions in this repository within the window, newest first by real modification time, never by id or name. Search for the topic first, then read only the matching sessions and only their relevant parts. Skip the current session and obvious noise (subagent, eval and test sessions). From each, take: topic, the user's goal, decisions, open threads, struggles and corrections, and artifacts (PRs, tasks, branches), citing the session. With more than a few matching sessions, fan out to parallel subagents on the **mechanical** tier from `models.md`, each taking a slice and returning that same schema; the raw history stays in the subagents and the main thread gets only their findings. If your agent keeps no history you can read, say so and rely on the repository's record.
5. Sweep the shared record whenever the topic names a feature, file, subsystem, area, or bug. This is the default, not a judgment call, and "my work on X" does not exempt it. Hand it to the **why** skill's source investigators, but steer their question from "why was this built this way" to "what's the current state, what's been tried and didn't hold, and what are users still reporting". Reuse its source playbook, run the investigators in parallel with steps 3 and 4, and inherit its posture: one investigator per source, null results are findings, skip an unavailable MCP and say so. Fold what comes back into the brief. Skip this step only for pure activity recall with no named target ("what did I do this week"), where the repository and your own history are the entire answer.
6. Verify against live state. Check every PR, branch, task and issue that steps 3 to 5 surfaced against its current state with `git` and `gh`. When the answer hinges on what an agent actually did (the commands it ran, files it read, errors it hit), read the full session or the commits, not a summary.
7. Write the brief to the contract below. Group by thread. Stay on the named topic.

## Output contract

Lead with the capsule, then the thread status, then the problems, then the next move. Deeper detail goes below or gets cut.

- **Capsule.** At most 5 bullets. What this work is and where it stands overall.
- **Threads.** One line each, prefixed with exactly one status tag: `[merged #N]`, `[open PR #N]`, `[in flight <branch>]`, `[verified, uncommitted]`, `[reverted #N]`, or `[planned, not started]`. A thread with no tag is not done yet, so tag it.
- **Problems.** At most 5, the recurring ones. Include the symptoms users keep reporting and any fix that shipped and was reverted, so the next attempt starts where the last one failed.
- **Next move.** The single most useful next action, concrete.

An adjacent feature or task stays out unless it blocks this one. When the capsule and thread lines outgrow a screen, cut detail before you cut threads. Write the brief through the **unslop** skill, cite repository findings by commit, branch, task or decision file, session findings by session, and shared-record findings by their source (PR #, ticket ID, chat permalink, error-tracker issue), and sanitize private context before any public output.

**Reply:** the brief, to the contract above.
