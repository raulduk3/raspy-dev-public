### Opening a PR

Invoked at the end of every other playbook. On this platform the tier of the repository decides what "open" means. Run `dev-loop tier <path>` first.

**Commits.** Commit small and often in your own worktree. Never rebase, amend or force-push. Fold and land join the commits.

**Text.** Write every commit, PR title and PR description in ASD-STE100. Use `type(scope): subject` for the title. Use the types `feat`, `fix`, `docs`, `refactor`, `test`, `chore` and `perf`. Run `/no-comments` before review.

**Tier 1.** Make no PR and no branch. Commit on `main`.

**Tier 2.** Make no PR. Write the briefing in `.worker-pr.md`. The owner lands the goal branch with `dev-loop land`.

**Tier 3.** Push the goal branch once. Open one draft PR, or push once to the bare repository. Never open a ready PR. The owner marks it ready and merges it.

**Tier 4.** Never push upstream. Keep the work on the `local/*` patch branch.

**Briefing.** The description is a briefing, not a lab notebook. Use these sections in order and drop a section that has nothing to say: `## Why`, `## Scope`, `## Tradeoffs`, `## Blast Radius`, `## Verification`. Report one primary number with its unit for a performance change.

**Forge.** Use `gh` only when the tier requires it. Make one call for each fact, with `--json` and `-q`. Do not poll CI. Do not post status comments. Edit the PR description.

**Stacks.** Do not make a stack. One goal makes one branch.
