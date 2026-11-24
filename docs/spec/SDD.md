# Software Design Description

What the dev platform must do, stated as requirements a reader can verify.

## Document control

| Field               | Value                                                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Product             | dev-platform                                                                                                                |
| Scope               | The full platform. The chapter SY holds the system requirements. Each other section holds the requirements of one area and names one system requirement as its owner. |
| Authority           | This document decides what the platform does in its areas. Where code and this document disagree, one is wrong; say which. |
| Companion documents | [TDD.md](TDD.md) states how each requirement of area ST is met; `tdd: none` marks an item with no TDD item yet. [SPEC-AMENDMENTS.md](SPEC-AMENDMENTS.md) holds the changes up to 2026-11-12. |
| Change control      | Only the owner's word changes a sentence. A change edits the exact lines. Git records the change. No decision record is written (SC-19). |

## Normative language

- "must" states a requirement.
- "must not" states a prohibition.

## Conventions

- Each requirement is one sentence on a `**XX-nn.**` line.
- A trace comment follows it: `<!-- id: SDD-XX-nn | tdd: TDD-x.y or none | status: ... -->`.
- Status is `implemented`, `pending:#N` or `deviation:#N`, where `#N` is a file in `docs/tasks/`. The field `gap: #N` cites a task in the same way. The task files are not in this copy.

## SY. System requirements

dev-platform is the layer around the editor, the terminal and the coding agents of one person on one machine. It keeps software work with AI agents organized, bounded and open to review. Each requirement of this chapter says one thing that the platform is for. Each section below names one of them as its owner.

**PL-01.** The platform MUST keep Git as the one record of the work of each project.
<!-- id: SYS-PL-01 -->

**PL-02.** The platform MUST give each agent one bounded place of work: one task, one worktree and one check.
<!-- id: SYS-PL-02 -->

**PL-03.** The platform MUST let only the owner land a goal on the base branch of a shared repository.
<!-- id: SYS-PL-03 -->

**PL-04.** The platform MUST refuse an agent command that changes a protected ref or the work of a different session.
<!-- id: SYS-PL-04 -->

**PL-05.** The platform MUST start each agent session with one account that the owner permits.
<!-- id: SYS-PL-05 -->

**PL-06.** The platform MUST make each session of each client findable through one index and one title format.
<!-- id: SYS-PL-06 -->

**PL-07.** The platform MUST give each role its identity, its memory and its history in each conversation.
<!-- id: SYS-PL-07 -->

**PL-08.** The platform MUST let the owner run a team of agents on one goal of one project.
<!-- id: SYS-PL-08 -->

**PL-09.** The platform MUST show the design, the code and the tests that prove each requirement of a project.
<!-- id: SYS-PL-09 -->

**PL-10.** The platform MUST keep the settings of each project in one record outside its repository.
<!-- id: SYS-PL-10 -->

**PL-11.** The platform MUST give each agent the same working method in each client.
<!-- id: SYS-PL-11 -->

**PL-12.** The platform MUST run each command from one release that the owner activated.
<!-- id: SYS-PL-12 -->

**PL-13.** The platform MUST NOT replace the native session format or the native sign-in of a client.
<!-- id: SYS-PL-13 -->

## SC. Source control
<!-- section: SDD-SC | sys: SYS-PL-01 -->

This area gives each repository one source control tier and one line of settings in the registry of the machine. The tier sets the refs, the checkouts, the land and the forge use for each agent and each interface, because an inventory of 2026-11-06 found six kinds of repository, seven worktree and branch schemes and four paths from an idea to code on one machine. The loop then moves one goal on one branch: workers commit in a fixed pool of detached slots, a fold adds one squash commit for each task, and the land follows the tier. Few refs and few checkouts make agent work faster, and they keep Git as the one record of the work. The area also holds the commands around the loop: the tidy, the command that makes a new repository from the templates, the project catalog and the workspace command. The owner uses these commands in a terminal, and agents and the team use them on the word of the owner.

The reasons:

- SC-37: Two repositories with one folder name stay distinct, and a linked worktree belongs to its real repository.
- SC-38: The identity is selected for one repository only, and two identities never share a shell.
- SC-41: Tiers 1 and 2 use `main` and release tags; a tier 3 repository keeps its own rules.
- SC-44: One goal is one branch and one logical change.
- SC-45: One open goal for each repository gives one dispatcher.
- SC-48: Tasks that run at the same time have scopes that do not overlap, so two workers do not change one file.
- SC-50: The steer is the gate of the dispatch, and a missing steer means pause.
- SC-51: A worker costs money, so a worker starts only on the word of the owner.
- SC-52: A worker never runs with no account bound to it.
- SC-53: A lock that was left fails closed, so the loop never starts one worker two times.
- SC-59: A process number can belong to a different process; a number alone is no evidence of a worker that runs.
- SC-60: The cleanup of a tool can end the process group of the starter, and a lost supervisor leaves a worker with no limit.
- SC-66: The specification changes only through a spec task; a worker that finds the specification wrong writes a blocker.
- SC-67: A tier 2 goal lands only through the owner; the loop itself never merges into a base, marks ready, approves or deploys for an agent.
- SC-68: At tier 1, a solo trunk, an agent can fast-forward and push `main` with no act of the owner.
- SC-69: No server rule protects a personal repository now, so tier 2 lands only through the owner.
- SC-70: The company repository sees only what its policy asks for: one branch and one pull request, merged by the owner.
- SC-72: A fork never pushes to its upstream repository.
- SC-74: A pull request of a company repository names no tool and no model.
- SC-79: A branch that the tidy deleted can be restored from the bundle.
- SC-80: A delete of a trunk that the host protects is refused or does harm; on 2026-11-06 the tidy listed such a trunk.
- SC-82: On 2026-11-06 four merged branches on a bare remote had to be deleted by hand.
- SC-83: One command makes a repository to the standard, and a repository is local unless the owner asks for GitHub.
- SC-85: Tiers 1 and 2 use `main` and release tags and no `develop` branch; a tier 3 repository keeps its own rules.
- SC-89: Each branch and each commit has one derived version, and the release tags are the only versions that a person writes.
- SC-91: The catalog adds no task database and no second source: its projects are the repositories that the loop uses.
- SC-94: The project of a session is not guessed from an old folder name.
- SC-95: The bridge runs no shell text and no free argument, and no bridge command merges, folds, pushes or cleans.
- SC-96: The projection gives the team tool a view of the projects; it puts no file of the team tool into a company repository, and the receipt is no permission to remove data of the user.
- SC-97: The start writes managed context into the folder, and a company checkout never gets such a file.
- SC-01: The tier sets the refs, the checkouts, the landing and the forge use for each agent and each interface; an inventory found six kinds of repository on one machine.
- SC-29: Tier 3 is the safe default for the push rules and the forge rules.
- SC-02: The tier sets the refs, the checkouts, the landing and the forge use, so an agent that does not know the tier can make a wrong ref or a wrong push.
- SC-03: An inventory found that one goal with N tasks made up to 3 + N branch refs; few refs make agent work faster.
- SC-30: Tier 1 is a solo trunk: the work is on `main`, with no ref.
- SC-04: A slot has no branch, so a task makes no ref; the fold takes the commits by their commit ID.
- SC-31: Before the tiers, one goal with N tasks made N + 2 new worktrees; few checkouts make agent work faster.
- SC-05: Few checkouts make agent work faster, and a reader does not change a file.
- SC-07: One goal is one branch and one logical change, and each task is one commit that a person can read and revert.
- SC-09: The kind of the repository decides who can move its base: an agent on a solo trunk, the owner on a shared repository, the host on a company repository.
- SC-13: Merged refs and old worktrees collect on the machine when no person removes them.
- SC-15: A cloud agent has no checkout on the machine; its result comes through GitHub, where server rules apply.

**SC-01.** Each registered repository MUST have one tier from 0 to 4.
<!-- id: SDD-SC-01 | tdd: TDD-4.1 -->

- Behavior: The tier names the kind of the repository: 0 no Git, 1 solo trunk, 2 personal shared, 3 protected company, 4 fork. The registry line states it in the setting `tier`.
- Observable: `dev-loop tier` with a path or a repository name prints the tier and each other setting with its value.
- Verified by: A loop test that reads the tier of a registered line, and the tests of the loop, the hooks and the wrapper at each tier.
- Limits: A registered line with no tier gets tier 3.

**SC-02.** Each agent MUST read the tier of the repository before its first change to a file.
<!-- id: SDD-SC-02 | tdd: TDD-4.2 -->

- Behavior: The session entry skill states the rule and the table of the tiers. The agent instructions of a repository from the templates hold the tier of that repository.
- Observable: `dev-loop tier` prints the tier for the agent.
- Verified by: A test that finds the tier line in the agent instructions of a new repository, and a read of the session entry skill for the rule.

**SC-03.** A goal MUST make at most one branch ref.
<!-- id: SDD-SC-03 | tdd: TDD-4.5 | gap: #13 -->

- Behavior: The goal branch holds the specification commits, each fold and the land. A worker commits on a detached head and makes no branch.
- Observable: `git for-each-ref` shows one new ref for each open goal.
- Verified by: A loop test that starts a goal, runs workers in slots and finds no branch of a worker.

**SC-04.** A worker MUST run in a detached slot from a fixed pool of the repository.
<!-- id: SDD-SC-04 | tdd: TDD-4.6 -->

- Behavior: The slots are numbered worktrees of the home repository. Before a task, the loop sets the slot to the tip of the goal branch and removes each file that Git does not track.
- Observable: A slot has no current branch. The loop prints that all slots are busy when each slot holds a task.
- Verified by: A loop test that gives three tasks to two slots.
- Limits: The setting `slots` of the registry line gives the size of the pool; the default is 2. A task with no free slot waits for the next dispatch.

**SC-05.** A reader MUST NOT get a checkout.
<!-- id: SDD-SC-05 | tdd: TDD-4.25, TDD-8.6 | gap: #11 -->

- Behavior: A reader is a reviewer, an overseer, a control seat or a planner. A reader reads the home repository with `git show`, `git diff` and `git grep`.
- Observable: The start of a team makes no worktree for a reader seat.
- Verified by: A launcher test that starts the control team in a folder outside the repository and is refused inside a repository.

<!-- retired: SDD-SC-06 -->

**SC-07.** A fold MUST add one squash commit for each task.
<!-- id: SDD-SC-07 | tdd: TDD-4.12 -->

- Behavior: The fold joins each commit of the worker into one commit on the goal branch. The message has the type, the title and the number of the task, the text of the worker and the trailers of the task.
- Observable: The log of the goal branch has one commit for each folded task.
- On failure: A goal worktree with uncommitted changes stops the fold.
- Verified by: A loop test that folds a task with two commits and reads one commit on the goal branch.

**SC-09.** The land MUST follow the tier of the repository.
<!-- id: SDD-SC-09 | tdd: TDD-4.16 | sys: SYS-PL-03 -->

- Behavior: The land first closes the goal: it writes the description and runs the check of the repository one time on the head of the goal branch. Then it acts as the tier says.
- On failure: A failed check, a goal with no folded task, and tier 0 stop the land with no change of the base.
- Verified by: A loop test of the land for each tier. Tests exist for tier 1 and tier 2 today.

**SC-10.** The distill skill MUST write its candidates to an incoming file that no repository tracks.
<!-- id: SDD-SC-10 | tdd: TDD-6.9, TDD-6.10 -->

- Behavior: The skill adds each batch of candidates to one HTML file for each repository. Where the file is in the project folder, the skill makes sure that Git ignores it and stops when Git tracks it.
- Observable: `dev-loop tier` prints the place of the file.
- Verified by: The test of the tier record for the place of the file; the text of the distill skill for the write.

**SC-13.** A daily timer MUST remove each merged ref of each registered repository.
<!-- id: SDD-SC-13 | tdd: TDD-4.18 | gap: #14 -->

- Behavior: A user timer of the machine runs the tidy with the apply option for each line of the registry, one time each day. The tidy writes each ref to a bundle first.
- Observable: `systemctl --user list-timers` shows the timer.
- Verified by: A read of the list of the user timers on the machine, and a test that runs the timer script with no terminal for each line of the registry.
- Limits: The owner installs the timer one time. The timer run needs no terminal.

**SC-15.** A cloud agent MUST work only on a tier 2 or tier 3 repository with a GitHub forge.
<!-- id: SDD-SC-15 | tdd: TDD-4.13 | gap: #22 -->

- Behavior: The fold of a cloud branch is the gate: it refuses each other tier and each other forge.
- On failure: The fold stops with one line and exit code 2.
- Verified by: A loop test that folds a cloud branch into a repository with file tasks and is refused.

<!-- retired: SDD-SC-18 -->

**SC-19.** Where a repository has `decisions=none` or `decisions=frozen`, an agent or a terminal MUST NOT change a decision record.
<!-- id: SDD-SC-19 | tdd: TDD-5.14, TDD-6.7, TDD-6.8 -->

- Behavior: A change of a decision record is each addition, edit or rename of a file in the decisions folder of the repository. With `decisions=frozen`, a deletion is a change also. With `decisions=none`, a deletion is allowed: the owner can remove the old records.
- Behavior: The commit hook of the platform refuses such a commit for each local interface. The fold refuses a task that holds such a change, a spec task also.
- Observable: The refusal names each path and the value of the setting.
- Verified by: The commit hook tests of the two values, with the deletion of a record for each value, and the loop tests of the two values.
- Limits: Where the Git rules are off for the project, the commit hook does not apply this rule. A repository with `decisions=open` keeps its decision records.

**SC-20.** Where a repository has `decisions=frozen`, intake MUST NOT change the specification.
<!-- id: SDD-SC-20 | tdd: TDD-6.11 -->

- Behavior: Intake stops and names the way that applies: distill for a raw record, or a change by the owner, by hand or through an agent that uses the write commands of the specification.
- Behavior: Distill still writes candidates. Intake can still make tasks for the gaps between the code and the present specification.
- Verified by: A test reads the rule in the text of the intake skill. An agent follows this rule, and no command enforces it for intake.
- Limits: This is the one difference from `decisions=none`: the commit hook and the fold apply the same rules for the two values.

**SC-21.** When intake promotes or rejects a candidate, intake MUST remove that candidate from the incoming file.
<!-- id: SDD-SC-21 | tdd: TDD-6.11 -->

- Behavior: Intake reads a candidate by its identifier from the incoming file, so the owner does not copy the block.
- Behavior: The message of the commit that changes the specification keeps the identifier. With `decisions=open` the decision record keeps it, and with `decisions=frozen` the commit message of the tasks keeps it.
- Verified by: The text of the intake skill.

**SC-28.** Where a repository has `decisions=none` or `decisions=frozen`, an agent or a terminal MUST NOT add an amendment log.
<!-- id: SDD-SC-28 | tdd: TDD-6.7, TDD-6.8 -->

- Behavior: An amendment log is a file that lists the changes of the specification.
- Behavior: The commit hook and the fold refuse a new log in each folder of the repository. A log that exists stays open to a change.
- Verified by: The commit hook tests of a new log with each value and of a log that exists, and the loop tests of the two values.

**SC-29.** If a Git repository has no registry line, then the platform MUST apply the push rules and the forge rules of tier 3.
<!-- id: SDD-SC-29 | tdd: TDD-4.1 -->

- Behavior: The tier record of such a path has tier 3, no forge, file tasks and 2 slots, and it says that the path is not registered.
- Verified by: A hook test and a guard test with an empty registry, and a launcher test with a new repository.

**SC-30.** Where a repository has tier 1, a goal MUST NOT make a branch ref.
<!-- id: SDD-SC-30 | tdd: TDD-4.5 -->

- Behavior: The work of a tier 1 goal is on the base branch.
- Verified by: A loop test that counts the refs of a tier 1 goal from the start to the land. No test does this today.

**SC-31.** The loop MUST NOT make or remove a worktree for each task.
<!-- id: SDD-SC-31 | tdd: TDD-4.6 -->

- Behavior: The loop makes a slot the first time that it needs the slot. A fold or a drop frees the slot, and the next task uses it again.
- Observable: The count of worktrees is the same before and after the second task of a slot.
- Verified by: A loop test that folds one task and gives the freed slot to the next task.

**SC-32.** If a worker result changes a file outside the task scope, then the fold MUST refuse the result.
<!-- id: SDD-SC-32 | tdd: TDD-4.12 -->

- Behavior: The scope is the list of path prefixes of the task. A file of the specification, the decision records and the tasks is examined by the specification rule and not by the scope.
- On failure: The fold names each file outside the scope and continues with the next task.
- Verified by: A loop test with a result that changes one file outside its scope and then a result inside its scope.
- Limits: A task with no scope line is not examined.

**SC-33.** A daily timer MUST remove each clean worktree that the tidy rule permits.
<!-- id: SDD-SC-33 | tdd: TDD-4.18 -->

- Behavior: The timer run removes a worktree through the tidy, and the rule of the tidy decides. A clean worktree with no unmerged branch and no live session leaves at the next run. A worktree with an unmerged branch stays at each age.
- Verified by: The tidy tests of the timer script with no terminal: a clean merged worktree leaves, and a repository whose tidy fails does not stop the others.
- Limits: The tidy has no rule for the age of a worktree.

**SC-34.** The fold MUST take the result of a cloud agent by its commit ID.
<!-- id: SDD-SC-34 | tdd: TDD-4.13 -->

- Behavior: The fold fetches the named branch of the remote, folds its commit as one squash commit, and then deletes the branch on the remote.
- On failure: A remote with no such branch stops the fold. A branch that the remote does not delete is named for the owner.
- Verified by: A loop test with a remote branch in a fixture. No test does this today.

**SC-35.** If a folder is no Git checkout, then the platform MUST report tier 0 for the folder.
<!-- id: SDD-SC-35 | tdd: TDD-4.1 -->

- Behavior: Tier 0 is the kind with no Git: it has no ref, no fold and no land. The land refuses a repository of tier 0.
- Observable: `dev-loop tier` prints tier 0 for the folder.
- Verified by: A loop test that reads the tier of a folder outside each repository.

**SC-36.** If a registry line breaks its form, then each reader of the registry MUST stop and name the file and the line.
<!-- id: SDD-SC-36 | tdd: TDD-4.1 -->

- Behavior: A line has the repository name, the checkout folder, the mode, an optional base, and then the settings as pairs of key and value. An unknown key, and a value outside the list of its key, break the form.
- Observable: `dev-loop tier` and each other loop verb exit with code 2.
- Verified by: A test with a wrong value of one setting, and a tidy test with a wrong list of kept branches.
- Limits: The project catalog reads the registry with the same reader, so a line that breaks its form also stops the catalog.

**SC-37.** The platform MUST treat each linked worktree and each symbolic link of a checkout as the same repository.
<!-- id: SDD-SC-37 | tdd: TDD-4.1, TDD-4.21 -->

- Behavior: The identity of a repository is its common Git folder, with each link resolved. A folder name and a remote address do not identify a repository.
- Observable: The tier record, the loop and the catalog give the same repository for each such path.
- Verified by: Tests with a linked worktree and a symbolic link in the registry line, and a catalog test with two repositories of one folder name.

**SC-38.** The GitHub wrapper MUST run each command under the identity that the mode of the repository names.
<!-- id: SDD-SC-38 | tdd: TDD-4.3 -->

- Behavior: The mode is the third column of the registry line. With `owner` the wrapper uses the login of the owner, with `bot` the token of the machine user, and with `local` it refuses each command.
- Observable: The wrapper is the command ghx: it takes the repository name and the arguments of one GitHub command.
- On failure: A repository with no registry line is refused. An argument that names a second repository or a second host is refused.
- Verified by: A wrapper test for each mode with a recorded GitHub command. No test runs the local mode today.

**SC-39.** Where the mode is `bot`, the GitHub wrapper MUST use the token of the machine user only at tier 0, 1 or 2.
<!-- id: SDD-SC-39 | tdd: TDD-4.3 -->

- Behavior: At tier 3 and tier 4 the wrapper refuses before it reads a credential. A tier that the wrapper cannot read counts as tier 3.
- On failure: With no token in the secret store the wrapper exits with code 4. It does not use the login of the owner in its place.
- Verified by: A wrapper test at each tier from 1 to 4 with no token in the fixture.

**SC-40.** The GitHub wrapper MUST refuse each GitHub act that belongs to the owner.
<!-- id: SDD-SC-40 | tdd: TDD-4.3 -->

- Behavior: The acts are: merge a pull request, mark it ready, review it, create a release, delete a repository, and a direct call of the API.
- On failure: The wrapper exits with code 3 and makes no call.
- Verified by: A wrapper test of the acts for the modes `owner` and `bot`.

**SC-41.** The loop MUST cut each goal branch from the base of the repository.
<!-- id: SDD-SC-41 | tdd: TDD-4.4 -->

- Behavior: The base is the fourth column or the setting `base` of the registry line. With no stated base, a tier 1 or tier 2 repository uses the default branch of its remote, and each other repository uses `develop`.
- On failure: A base that is no valid branch name stops each loop verb with exit code 2.
- Verified by: Loop tests for a stated base, for the default of a personal repository and for the default of a company repository.
- Limits: A tier 1 or tier 2 repository whose remote gives no default branch uses `develop`. Where the tasks are GitHub issues, the loop fetches the base and cuts from the base of the remote.

**SC-42.** While a goal is open, the loop MUST keep the base that the goal started from.
<!-- id: SDD-SC-42 | tdd: TDD-4.4 -->

- Behavior: The loop records the base at the start of the goal. A later change of the registry line changes the base of the next goal only.
- Observable: The status measures the goal against the recorded base.
- Verified by: A loop test that changes the base in the registry while a goal is open.

**SC-43.** Where a registry line states no forge, the platform MUST derive the forge from the mode and the remote.
<!-- id: SDD-SC-43 | tdd: TDD-4.1 -->

- Behavior: The forge is the kind of the remote host: `github`, `bare` or `none`. The modes `owner` and `bot` give `github`; the mode `local` gives `bare` where the checkout has the remote `origin`, else `none`.
- Observable: `dev-loop tier` prints the forge.
- Verified by: A test that reads the forge of a line of each mode, with a remote and with no remote. No test does this today.

**SC-44.** When a user starts a goal, the loop MUST cut one goal branch with a type and slug name from the base.
<!-- id: SDD-SC-44 | tdd: TDD-4.5 -->

- Behavior: The name has a commit type, a slash and a slug in small letters, for example feat/snake-game. The goal branch gets its own worktree in the worktree folder of the repository.
- Observable: The loop prints the goal branch, the commit of the base and the plan.
- On failure: A name of a different form, and a local branch that has the name, stop the start with no change.
- Verified by: A loop test that starts a goal and compares the goal branch with the base, and a workspace test with a name of a wrong form.

**SC-45.** While a goal is open in a repository, the loop MUST refuse the start of a second goal.
<!-- id: SDD-SC-45 | tdd: TDD-4.5 -->

- Behavior: One repository has one open goal, and so one dispatcher.
- On failure: The start exits with code 3 and names the open goal.
- Verified by: A loop test that starts a goal two times.

**SC-46.** Where a repository is large, the loop MUST limit the files of a slot to the folders of the task scope.
<!-- id: SDD-SC-46 | tdd: TDD-4.6 -->

- Behavior: The setting `large` of the registry line turns this on. The slot gets a sparse checkout: the folders of the scope and the files of the top folder.
- Verified by: A loop test that reads a slot of a large repository for a file inside and a file outside the scope.
- Limits: A task with no folder in its scope gets the full tree. A slot of a repository that is not large gets the full tree again.

**SC-47.** The loop MUST select a task only when each task that it depends on is closed or folded.
<!-- id: SDD-SC-47 | tdd: TDD-4.7 -->

- Behavior: A task states its dependencies in one line, or the word none. A dependency that is folded into the open goal branch counts, because its code is on that branch.
- Observable: The plan lists the task as skipped, with the open dependencies.
- Verified by: A loop test with a task that depends on an open task.

**SC-48.** The loop MUST NOT select two tasks with overlapping scope paths in one plan.
<!-- id: SDD-SC-48 | tdd: TDD-4.7 -->

- Behavior: Two scopes overlap when a path of one is a prefix of a path of the other. The first task in the order of the list is selected.
- Observable: The plan lists the later task as skipped, with the path that overlaps.
- Verified by: A plan test with two ready tasks that share a path prefix. No test does this today.

**SC-49.** When a user asks for a plan, the loop MUST list each selected task and each skipped task with its reason.
<!-- id: SDD-SC-49 | tdd: TDD-4.7 -->

- Behavior: The loop selects a ready task that has a scope line and a dependency line, up to the worker limit. The reasons to skip are: in review, folded, held by a worker, a missing line, an open dependency, an overlap, over the limit.
- Observable: The loop prints the plan and keeps it in the ledger of the goal; it posts nothing.
- Verified by: A loop test that reads the plan of a repository with a ready task, a task that waits and a draft task.

**SC-50.** While the steer of a repository is not `go`, the scheduled tick MUST NOT start a worker.
<!-- id: SDD-SC-50 | tdd: TDD-4.8 -->

- Behavior: The steer is one word of the ledger: go or pause. A missing steer means pause, the pause verb writes pause, and the end of a goal writes pause.
- Observable: The tick prints one fixed word and starts nothing. The status prints the steer.
- Verified by: A test that pauses a repository and reads the steer. No test runs the tick with the steer pause today.
- Limits: A pause stops the next dispatch only; it does not stop a worker that runs.

**SC-51.** If the owner is not present, then the loop MUST NOT start a worker.
<!-- id: SDD-SC-51 | tdd: TDD-4.8 -->

- Behavior: The owner is present in a terminal, or in a session that the owner started through one of the portals term, desk and phone. A worker then runs as a run of the owner, and a service unit is no sign of the owner.
- On failure: The go verb exits with code 2 and leaves the steer unchanged; the tick starts nothing.
- Verified by: A loop test that runs the go verb and the tick with no sign of the owner.

**SC-52.** If no account can take a worker, then the loop MUST stop before it changes the steer or a slot.
<!-- id: SDD-SC-52 | tdd: TDD-4.8 -->

- Behavior: The loop asks the account service for one account before each dispatch. A named account is used or refused; no second account takes its place.
- On failure: The go verb exits with code 2.
- Verified by: A loop test with an account that is not signed in, and a loop test with an account registry that cannot be read.

**SC-53.** While one dispatch runs for a repository, the loop MUST refuse a second dispatch.
<!-- id: SDD-SC-53 | tdd: TDD-4.8 -->

- Behavior: The go verb, the resume verb and the tick hold one lock of the repository.
- On failure: The second dispatch exits with code 3 and changes nothing. A lock that a stopped dispatch left stays until a person removes it.
- Verified by: A workspace test that holds the lock and runs the go verb.

**SC-54.** The loop MUST run at most the configured number of workers of one repository at one time.
<!-- id: SDD-SC-54 | tdd: TDD-4.8 -->

- Behavior: The limit is a variable of the loop; the default is 3. The dispatch and the resume count the live workers before each start.
- Observable: The loop prints that the worker limit is reached.
- On failure: A limit that is no positive number stops each loop verb with exit code 2.
- Verified by: A loop test that resumes a task while one worker runs and the limit is 1.

**SC-55.** When the loop gives a task to a slot, the loop MUST write a brief with the task, the scope and the worker rules.
<!-- id: SDD-SC-55 | tdd: TDD-4.8 -->

- Behavior: The brief tells the worker to commit on the detached head, to stay in the scope, to run the check or the short proof one time, and to write its report or its blocker and stop. It names the task file or the issue as the request.
- Observable: The brief is a file of the slot that Git does not track.
- Verified by: A loop test that reads the brief of a file task for the task file and for the rules.

**SC-56.** If a worker passes its time limit, then the loop MUST stop the worker and each process that the worker started.
<!-- id: SDD-SC-56 | tdd: TDD-4.9 -->

- Behavior: A supervisor process starts the worker in its own process group. At the limit it ends the group, and after 5 seconds it ends each process that is left.
- Observable: The exit record has the code 124 and the time limit as the reason.
- Verified by: A supervisor test with a process that sleeps past a limit of 1 second.
- Limits: The default limit is 1800 seconds. A turn limit of the worker command also applies; its default is 60 turns.

**SC-57.** The loop MUST give a worker only the environment variables on the allow list.
<!-- id: SDD-SC-57 | tdd: TDD-4.9 -->

- Behavior: The list holds the home folder, the path, the user, the language, the session naming variables and the names that the owner lists for the repository. The loop refuses the name of a credential in the list of the owner.
- Verified by: A supervisor test with one listed variable and one variable that is not listed.
- Limits: A Pi worker also gets the metered key of the model gateway and its limits by name.

**SC-58.** When a worker run ends, the loop MUST record the exit code, the reason and the run time.
<!-- id: SDD-SC-58 | tdd: TDD-4.9 -->

- Behavior: The reasons are: exited, time limit, interrupted, failed to start. The output of the worker goes to a log in the ledger.
- Observable: The record is one JSON file for each task in the ledger of the goal.
- Verified by: A loop test that reads the record of a worker that exits with code 7.

**SC-59.** The loop MUST count a worker as running only while a live supervisor of the same repository holds its record.
<!-- id: SDD-SC-59 | tdd: TDD-4.9 -->

- Behavior: The loop compares the process, its start time, its folder and its command with the record that the supervisor wrote. A process number alone is no evidence.
- On failure: A live supervisor whose identity differs from its record stops the dispatch for inspection.
- Verified by: A loop test that counts one live supervisor against a limit of 1.

**SC-60.** A worker MUST continue to run when the session that started it ends.
<!-- id: SDD-SC-60 | tdd: TDD-4.9 -->

- Behavior: The supervisor runs in its own session, apart from the process group of the starter.
- Observable: The supervisor and the worker are alive after the group of the starter gets the end signal.
- Verified by: A loop test that ends the process group of the starter and then reads the exit record of the worker.

**SC-61.** When a user resumes a task, the loop MUST start a new worker run in the slot that holds the task.
<!-- id: SDD-SC-61 | tdd: TDD-4.10 -->

- Behavior: The new run gets the brief with the present scope line of the task. It is a new conversation, not a continued one.
- On failure: The loop skips a task that still runs, that is ready for review, that is blocked, or that has no brief or no slot.
- Verified by: A loop test that resumes a task in its worktree and reads the command of the new run.

**SC-62.** When a user drops a task, the loop MUST free the slot of the task and discard its work.
<!-- id: SDD-SC-62 | tdd: TDD-4.10 -->

- Behavior: The slot loses its task mark, and the next task sets the slot to the goal branch again.
- On failure: The loop refuses a task whose worker still runs or whose seat is not released.
- Verified by: A loop test that drops a task and then drops it a second time.

**SC-63.** When a user asks for the state of a repository, the loop MUST report the goal, each worker and each folded task.
<!-- id: SDD-SC-63 | tdd: TDD-4.11 -->

- Behavior: The report has the steer, the goal branch with its commits ahead of the base, the live workers, the state of each slot, the folded tasks and the pull request or the local merge. One verb prints text, and one verb prints the same facts as JSON.
- Observable: A worker state is one of: working, running, blocked, ready for review, no commits.
- Verified by: A loop test that reads the text and the JSON for a goal with one worker in a slot.
- Limits: With no open goal the report names the last goal that landed.

**SC-64.** When a user collects a cycle, the loop MUST write one report with the count of each task state.
<!-- id: SDD-SC-64 | tdd: TDD-4.11 -->

- Behavior: The report lists the tasks that are ready for review, that wait, that are blocked and that are folded, and the pull request of the goal. Its last line has the counts: planned, dispatched, running, ready, folded, blocked, decisions.
- Observable: The loop prints the report and keeps it in the ledger of the goal.
- Verified by: A loop test that collects a cycle of a repository with file tasks.
- Limits: The collect reads no transcript and no log. For a repository with file tasks it calls no forge.

**SC-65.** If a worker result is not ready, then the fold MUST refuse the result and leave the goal branch unchanged.
<!-- id: SDD-SC-65 | tdd: TDD-4.12 -->

- Behavior: A result is not ready when the worker still runs, is blocked, has uncommitted changes or no commit, commits a worker file or the managed context of a team seat, or conflicts with the goal branch.
- Observable: One line for each task says that it is folded, or gives the reason.
- Verified by: A loop test with a seat that is still attached and with a commit of the managed context. No test has a live worker, a blocked worker or a conflict today.

**SC-66.** If a task has no `spec` label and its result changes specification text, then the fold MUST refuse the result.
<!-- id: SDD-SC-66 | tdd: TDD-4.12 -->

- Behavior: A build task can change only the trace comment and the lock line of an item. The rule covers the specification, the decision records and the task files.
- On failure: The fold prints the first changed lines.
- Verified by: A loop test where a build task changes a requirement sentence and then only a trace comment.
- Limits: Where the registry line sets the domains layout or frozen decisions, the specification guard of the loop examines the result first (SC-19).

**SC-67.** If an owner act runs with no terminal of the owner, then the loop MUST refuse the act.
<!-- id: SDD-SC-67 | tdd: TDD-4.14 -->

- Behavior: The owner acts are: the land at tier 2, 3 and 4, a push or a local merge of the close, the ready option, the finish, and the tidy with the apply option.
- On failure: The loop exits with code 4 and calls no forge.
- Verified by: A loop test of the finish, of the tidy with the apply option, and of the close with a push, with no terminal.
- Limits: Two cases need no terminal: a draft push of the close at tier 1 or tier 2, and the tidy of the daily timer.

**SC-68.** Where a repository has tier 1, the loop MUST permit an agent to land the goal on the base and push the base.
<!-- id: SDD-SC-68 | tdd: TDD-4.16 -->

- Behavior: The land moves the local base to the goal branch, as a fast-forward when it can be one, and pushes the base to the remote where one exists.
- Observable: The base and the base of the remote are the same commit, and the log has no merge commit.
- Verified by: A loop test that lands a tier 1 goal with no terminal.
- Limits: With no remote the land is on the machine only.

**SC-69.** Where a repository has tier 2, the land MUST move the local base to the goal and push the base.
<!-- id: SDD-SC-69 | tdd: TDD-4.16 | sys: SYS-PL-03 -->

- Actor: The owner, in a terminal.
- Behavior: The move is a fast-forward when it can be one, else one merge commit with the description of the goal. The push tells the push hook that it is the land.
- On failure: A base worktree with uncommitted changes, a conflict, and a moved base that no worktree holds stop the land with no change. A failed push is reported, and the base stays landed on the machine.
- Verified by: A loop test that is refused with no terminal and lands in a terminal.

**SC-70.** Where a repository has tier 3 and a GitHub forge, the land MUST make one push and one draft pull request.
<!-- id: SDD-SC-70 | tdd: TDD-4.16 -->

- Actor: The owner, in a terminal.
- Behavior: The land pushes the goal branch under its own name and opens the pull request against the base, with the description of the goal. A second land after more folds pushes to the same pull request and writes its title and body again.
- Observable: The ledger keeps the address of the pull request. The owner merges it.
- Verified by: A loop test of a tier 3 land with a recorded GitHub command. No test does this today.

**SC-71.** Where a repository has tier 3 and no GitHub forge, the land MUST push only the goal branch to the remote.
<!-- id: SDD-SC-71 | tdd: TDD-4.16 -->

- Actor: The owner, in a terminal.
- Behavior: The merge into the base is the act of the owner on the host. The finish closes the goal when the local base holds it.
- On failure: A repository with no remote stops the land.
- Verified by: A loop test of a tier 3 land to a bare remote. No test does this today.

**SC-72.** Where a repository has tier 4, the land MUST push only the goal branch to the remote `origin`.
<!-- id: SDD-SC-72 | tdd: TDD-4.16 -->

- Actor: The owner, in a terminal.
- Behavior: Tier 4 is a fork. The land never pushes to the upstream repository, and it changes no base.
- Verified by: A loop test of a tier 4 land with two remotes. No test does this today.

**SC-73.** When the loop closes a goal, the loop MUST write one description with one closing line for each folded task.
<!-- id: SDD-SC-73 | tdd: TDD-4.15 -->

- Behavior: The description has the four sections of the pull request template: what changed and why for each task, the last lines of the check, the deploy impact and the review notes. The title comes from the name of the goal branch and the task numbers.
- Observable: The loop prints the place of the description, the title and the next command.
- On failure: A goal with no folded task, and a goal worktree with uncommitted changes, stop the close.
- Verified by: A loop test that closes a goal with one folded task and reads the description.

**SC-74.** Where a repository is not tier 1 or tier 2, the loop MUST refuse a goal description that gives a tool as an author.
<!-- id: SDD-SC-74 | tdd: TDD-4.15 -->

- Behavior: The loop looks in the text of each folded task and in the description for a co-author trailer that names a tool and for a generated-with line.
- On failure: The close prints each such line, exits with code 1 and writes no description.
- Verified by: A loop test that closes a goal whose folded text has a generated-with line.

**SC-75.** Where the tasks of a repository are files, the close MUST merge the goal branch into the local base with one merge commit.
<!-- id: SDD-SC-75 | tdd: TDD-4.15 -->

- Actor: The owner, in a terminal, with the merge option.
- Behavior: The merge message is the title and the description of the goal. The close then moves the files of the folded tasks to the done folder and ends the goal.
- On failure: A checkout that is not on the base, uncommitted changes and a conflict stop the merge with no change. The push option is refused for such a repository.
- Verified by: A loop test that runs a goal from task files to the local merge.
- Limits: The close calls no forge.

**SC-76.** When a goal lands on the machine, the loop MUST remove the goal branch and the goal worktree.
<!-- id: SDD-SC-76 | tdd: TDD-4.15 -->

- Behavior: The loop also removes the check folder and the stop marker of a goal forge, records the goal as the last goal, and writes the steer pause.
- Observable: The status shows no open goal and names the last goal.
- Verified by: A loop test that reads the ledger and the branches after a land and after a local merge.

**SC-77.** If the pull request of a goal is not merged into the base, then the finish MUST refuse to close the goal.
<!-- id: SDD-SC-77 | tdd: TDD-4.15 -->

- Actor: The owner, in a terminal.
- Behavior: For a merged pull request the finish closes each folded issue, deletes the pushed branch on the remote, removes the goal branch and the goal worktree, and writes the steer pause. For a repository with file tasks the finish needs the goal branch in the local base.
- Verified by: A loop test of the finish with a recorded GitHub command for an open and for a merged pull request. No test does this today.

**SC-78.** Where the user does not apply the tidy, the tidy MUST only list the refs and the worktrees that it can remove.
<!-- id: SDD-SC-78 | tdd: TDD-4.17 -->

- Behavior: The list has three groups: merged branches of the remote, worktrees, and local branches.
- Observable: The last line says that the run is read-only and gives the command that applies it.
- Verified by: A loop test that runs the tidy with no option and finds each branch in place.

**SC-79.** The tidy MUST write each ref to a bundle before it deletes the ref.
<!-- id: SDD-SC-79 | tdd: TDD-4.17 -->

- Behavior: The bundle and a list of the refs are in a dated folder of the ledger. The tidy verifies the bundle.
- Observable: The tidy prints the command that restores a branch from the bundle.
- On failure: A bundle that fails its verification stops the tidy, and nothing is deleted.
- Verified by: A tidy test that applies the tidy and lists the heads of the bundle.

**SC-80.** The tidy MUST NOT list or delete the base, a kept trunk, the open goal branch or the head of an open pull request.
<!-- id: SDD-SC-80 | tdd: TDD-4.17 -->

- Behavior: A kept trunk is a branch in the setting `keep` of the registry line: a branch that the host protects or checks. The names `main` and `develop` are kept in each repository.
- Verified by: A tidy test with two kept trunks and one old branch, on the machine and on the remote.

**SC-81.** The tidy MUST remove a worktree only when it is clean, has no live session and has no unmerged branch.
<!-- id: SDD-SC-81 | tdd: TDD-4.17 -->

- Behavior: A worktree with a detached head counts as merged. The tidy never removes the main checkout, the goal worktree, a worker slot or the check folder of a goal forge.
- Verified by: A tidy test with a clean merged worktree, a worktree with changes and a worker slot. No test does this today.
- Limits: A live session is a Claude Code process with the worktree as its folder. The tidy does not see a session of a different runtime.

**SC-82.** Where the forge of a repository is `bare`, the tidy MUST also remove the merged branches of the remote.
<!-- id: SDD-SC-82 | tdd: TDD-4.17 -->

- Behavior: The tidy fetches the remote, lists each branch that is merged into the base of the remote, and deletes it on the remote after the bundle. For a repository with GitHub issues the tidy reads the remote also, and it keeps the head of each open pull request.
- Verified by: A tidy test with a bare remote that holds a merged branch, a kept trunk and an open branch.

**SC-83.** The new repository command MUST make each repository from the templates of the platform release.
<!-- id: SDD-SC-83 | tdd: TDD-4.19 -->

- Behavior: The templates give the agent instructions, the contribution policy, the pull request template, the code owners file, the workflows, the check scripts, the version script, the empty specification and the task folder. The command adds an ignore file, a first README and one hygiene test, and it writes no language skeleton.
- On failure: A target folder that is not empty, and a tier outside 1 to 4, stop the command with exit code 2.
- Verified by: A test that runs the command through a link, as the installed command, and finds the template files.
- Limits: With no GitHub name the command makes no remote and pushes nothing.

**SC-84.** A new repository MUST start with one commit on `main` and the tag `v0.1.0`.
<!-- id: SDD-SC-84 | tdd: TDD-4.19 -->

- Behavior: The tag makes the version derivable from the first commit.
- Observable: The version script prints 0.1.0 in the new repository.
- Verified by: A test that reads the version of a new repository.

**SC-85.** A new repository MUST have a `develop` branch only at tier 3.
<!-- id: SDD-SC-85 | tdd: TDD-4.19 -->

- Behavior: At tier 3 the checkout stays on `develop`, and that branch is the base. At tiers 1, 2 and 4 the command takes the name `develop` out of the instructions, the workflows and the hygiene check, and the base is `main`.
- Verified by: A test that lists the branches of a new tier 1, tier 2 and tier 3 repository.

**SC-86.** The new repository command MUST write the tier into the agent instructions of the new repository.
<!-- id: SDD-SC-86 | tdd: TDD-4.2, TDD-4.19 -->

- Behavior: The tier is an option of the command; the default is 2 for a personal repository and 3 for each other repository. The instructions tell the agent to find the tier before it changes a file.
- Verified by: A test that reads the tier line of a new tier 1, tier 2 and tier 3 repository.

**SC-87.** Where the user asks for registration, the new repository command MUST add one registry line with the tier, the base and the tracker.
<!-- id: SDD-SC-87 | tdd: TDD-4.19 -->

- Behavior: The line has the mode `local` and file tasks, or the mode `owner` and GitHub issues where the user names a GitHub repository. The task form of the line follows TK-10.
- On failure: A repository that the registry holds stays unchanged. With no registration the command prints the line for the owner.
- Verified by: A test that compares the registry line of a new personal repository and of a new company repository.

**SC-88.** Where the user names a GitHub repository, the new repository command MUST create it, push each branch and apply the branch rules.
<!-- id: SDD-SC-88 | tdd: TDD-4.19 -->

- Behavior: The rules protect `main`, and `develop` at tier 3: no deletion, no forced push, a pull request with one approval of a code owner, and two status checks. The command sets the base as the default branch and permits merge commits only.
- On failure: Where GitHub refuses a rule set, the command says so and prints the command that applies it later.
- Verified by: A test that runs the command with a recorded GitHub command. No test does this today.

**SC-89.** A new repository MUST derive its version from its Git tags and its branch.
<!-- id: SDD-SC-89 | tdd: TDD-4.20 -->

- Behavior: On a release tag the version is the tag. After a tag it is the next patch number with the branch slug, the distance to the tag and the short commit ID.
- Observable: No file of the project holds the version.
- Verified by: A test that reads the version on the tag and after one commit on a branch.

**SC-90.** The check of a new repository MUST refuse a commit message that gives a tool as an author.
<!-- id: SDD-SC-90 | tdd: TDD-4.20 -->

- Behavior: The hygiene check reads each commit after the base. It refuses a co-author trailer that names a tool, a generated-with line, a subject that is not in the form of type, scope and summary, and an added line of source or documents that names a tool.
- On failure: The check prints each finding with its commit or its file and line, and exits with code 1.
- Verified by: A test of the template check on a history with a tool trailer, a generated-with line and a plain message.

**SC-91.** The catalog MUST list each repository of the registry as one project with a stable identifier.
<!-- id: SDD-SC-91 | tdd: TDD-4.21 -->

- Behavior: A project has the identifier, the repository name, the checkout, a display group, the mode and a mark that the loop can run for it. The identifier comes from the repository name and is the same in each run.
- Observable: `ai-work projects` prints the catalog as JSON.
- On failure: Two lines for one repository stop the catalog with one line of text. A checkout that is gone is listed as not available, with a caution.
- Verified by: Catalog tests with a local repository, with two lines for one repository and with a long name.
- Limits: The group is for display only and gives no permission.

**SC-92.** Where the user names a development root, the catalog MUST also list each Git repository at most one folder below the root.
<!-- id: SDD-SC-92 | tdd: TDD-4.21 -->

- Behavior: Such a project is shown, and the loop cannot run for it until the registry has a line for it. The catalog does not look inside a worktree folder or a deeper folder.
- Verified by: A catalog test with a repository below the root, one in a group folder and one in a worktree folder.

**SC-93.** If the checkout of a registry line is gone, then the catalog MUST look for the moved checkout below the development root.
<!-- id: SDD-SC-93 | tdd: TDD-4.21 -->

- Behavior: The catalog takes the one repository whose folder name is the old folder name or the repository name. More than one match is no match.
- Observable: The catalog gives the new folder and a caution that the checkout moved.
- Verified by: A catalog test that moves a checkout into a group folder.

**SC-94.** The catalog MUST list the indexed sessions of a project by the repository of their working folder.
<!-- id: SDD-SC-94 | tdd: TDD-4.22 -->

- Behavior: The list reads the session index only: it starts no scan and makes no index. A session whose folder is gone is listed as not assigned, not as a project of its old name.
- Verified by: Tests with sessions in a checkout, in a linked worktree, in a second repository and in a folder that is gone.
- Limits: The list has 20 rows by default and 200 at most, newest first, with the total count.

**SC-95.** The workspace command MUST pass only a listed verb and validated arguments to the loop.
<!-- id: SDD-SC-95 | tdd: TDD-4.23 -->

- Behavior: The verbs are status, plan, start, go, pause and collect. The start takes one goal branch name, and only the go verb takes the words only or skip with task numbers.
- Observable: With the dry run option the command prints the loop command and the registry, and it starts nothing.
- On failure: A different verb, a different argument and a project with no registry line are refused with exit code 2.
- Verified by: A workspace test with a fold verb, with an argument that holds a shell command, and with a dry run.

**SC-96.** When the user asks for a projection, the workspace command MUST write one project catalog for the team tool outside each Git repository.
<!-- id: SDD-SC-96 | tdd: TDD-4.24 -->

- Behavior: The projection has one catalog file and one folder for each project, with a manifest and a pointer to the checkout. A receipt records the hash of each file that the command wrote.
- On failure: A target inside a Git repository, a symbolic link, and a file that the receipt does not own or that a person changed stop the command before it writes a file.
- Verified by: Tests that run the projection two times, with a file of the user, with a changed file and with a symbolic link.
- Limits: The command removes no file, also not for a project that left the catalog. It does not configure or start the team tool.

**SC-97.** If a checkout is tier 3, tier 4 or not registered, then the seat launcher MUST refuse to start a new seat in it.
<!-- id: SDD-SC-97 | tdd: TDD-4.25 -->

- Behavior: The start of a seat writes managed context of the team tool into the folder of the seat. A plan of a seat writes nothing and is permitted.
- On failure: The launcher exits with code 2 and starts no seat.
- Verified by: A launcher test that starts and plans a seat in a repository with no registry line.
- Limits: A team folder with its own team file is no product checkout, and the rule does not apply to it.

## GD. Guards and checks
<!-- section: SDD-GD | sys: SYS-PL-04 -->

This part of the platform refuses a command or a Git operation that changes a protected ref or the work of a different session, and it runs the full check of a tree one time for one state of that tree. The agents in Claude Code, Codex and Pi meet the command guard before each shell command, and each person and each tool that runs Git on the machine meets the Git hooks. The harness guards reach Claude Code fully, Codex and Pi in part and Zed not at all, so the Git hooks carry the push rules and the commit rules to each local interface. The stop check keeps a session from a stop on a tree whose check fails, and the pass record keeps the cost to one run. The format hook and the notify hook are two small helpers of a Claude Code session: one formats a file after an edit, and one calls the owner when a session waits or fails.

The reasons:

- GD-08: Pi has no hooks of its own, and a guard that fails open is no guard.
- GD-09: A read-only search for a refused phrase is no refused command.
- GD-10: Nothing that was pushed for review is written again.
- GD-11: A branch of a desktop session is work in progress and is never pushed.
- GD-13: No tool or model attribution reaches the record of a professional repository.
- GD-14: Only the land verb sets the variable, so that an agent cannot pass the push rule of the Git hooks.
- GD-15: An agent commits small and often and does not amend or rebase; the fold and the land join the commits.
- GD-16: The hooks path carries the Git hooks of the platform.
- GD-17: A checkout or a merge in a shared worktree makes the check of a different session there fail.
- GD-18: A memory folder takes memory from the machine and the system sweeps it, so a checkout there can stop other programs and lose work that is not committed.
- GD-19: Engineering scripts belong in the worktree of the project.
- GD-20: A deploy and a restart are the owner's, in a terminal.
- GD-21: An agent does read-only diagnostics on a remote host; a change there is the owner's.
- GD-22: The classifier can raise the risk of a command and cannot lower a rule; it is off by default so that test runs and command loops do not spend money.
- GD-23: The rules are the second layer for Codex, which cannot state a rule for one repository; the hook entry covers the forms that a prefix cannot match.
- GD-24: No tool or model attribution reaches the record of a professional repository.
- GD-25: Tier 2 lands only through the owner, and the Git hooks cover each local push.
- GD-26: A global hooks path does not turn the hooks of a repository off.
- GD-27: A tree that passed before costs nothing.
- GD-28: One dirty worktree of a second session would make the stop check of each session in the checkout fail.
- GD-31: Two checks in one tree share the build output and the log, and they collide.
- GD-32: The time limit of the stop hook sends the signal; a lock that stays behind would refuse each later run.
- GD-33: A tree that passed before costs nothing, and a session does not stop on changes that no check saw.
- GD-34: The agent reports the failure and does not stop on a tree whose check fails.
- GD-35: Without this rule a check that fails would block each stop of the session.
- GD-36: One orchestrator and its workers share the tree, and the orchestrator runs the full check one time for each batch.
- SC-11: The harness guards reach Claude Code fully, Codex and Pi in part and Zed not at all, so Git hooks carry the rules to each local interface.
- GD-01: Nothing that was pushed for review is written again.
- GD-02: A branch of a desktop session is work in progress and is never pushed.
- GD-03: No tool or model attribution reaches the record of a professional repository.
- SC-12: The owner merges into a protected ref; an agent does not.
- GD-04: At tiers 2 to 4 a protected ref changes only through the land of the owner or a pull request.
- GD-05: The owner reviews, marks ready and merges.
- GD-06: A branch that a different worktree holds is the work of a different session.
- GD-07: A different worktree and its untracked files are the work of a different session.
- SC-14: A branch of a desktop session is work in progress and is never pushed.
- SC-16: Zed has no platform guard, so a write of its built-in agent would pass each harness guard.

**SC-11.** If a push changes a protected ref, then the Git hooks MUST refuse the push for each local interface.
<!-- id: SDD-SC-11 | tdd: TDD-5.12 -->

- Actor: A person or an agent that runs Git on the machine: Claude Code, Codex, Pi, Zed or a terminal.
- Behavior: The protected refs are the branches main, master and develop. A push to one of them and a delete of one of them are refused, and an unregistered repository gets the rules of tier 3.
- Observable: Git stops the push with one line that starts with `dev-platform pre-push:` and names the ref and the tier. The remote ref does not change.
- Verified by: The pre-push tests push to a local bare remote with plain Git and no agent tool, at each tier and from a linked worktree. The installer tests prove the global hooks path.
- Limits: At tier 1 a fast-forward push of main or master passes, and at tier 0 the hooks apply no push rule. The land verb has its own rule in this section.

**GD-01.** If a push is a force update of a ref, then the Git hooks MUST refuse the push at each tier.
<!-- id: SDD-GD-01 | tdd: TDD-5.12 -->

- Behavior: A force update is a push where the old commit of the remote ref is not an ancestor of the new commit. An old commit that the local repository does not hold also counts, and the reason tells the user to fetch first.
- Observable: The remote ref keeps its old commit.
- Verified by: The pre-push tests of a rewritten branch at tiers 1 to 4, with the force option and with a plus refspec, and with the land variable set.
- Limits: The land verb does not lift this rule.

**GD-02.** If a push sends a branch whose name starts with wip/, then the Git hooks MUST refuse the push at each tier.
<!-- id: SDD-GD-02 | tdd: TDD-5.12 -->

- Behavior: The reason tells the user to rename the branch to a type and a short description first.
- Observable: The remote gets no ref with that name.
- Verified by: The pre-push test of a wip branch at tiers 1 to 4.

**GD-03.** Where a repository has tier 3, the Git hooks MUST refuse a commit whose message holds a tool attribution.
<!-- id: SDD-GD-03 | tdd: TDD-5.13 -->

- Behavior: A tool attribution is a co-author line that names an AI vendor, an AI tool or a no-reply address, or a line with the words generated with. A co-author line of a person passes.
- Observable: Git makes no commit and prints two lines that start with `dev-platform commit-msg:`.
- Verified by: The commit message tests with six attribution lines at tier 3, with a human co-author, at the other tiers and in an unregistered repository.
- Limits: An unregistered repository gets the rule of tier 3. At tiers 1, 2 and 4 the message passes.

**SC-12.** If an agent command merges into a protected ref, then the command guard MUST refuse the command.
<!-- id: SDD-SC-12 | tdd: TDD-5.4 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The rule applies while main, master or develop is the current branch of the repository that the command names. A change of branch earlier in the same command line counts.
- Verified by: The guard tests of a merge on a protected branch, through a folder option, after a change of branch, and of the fast-forward at tier 1 and tier 2.
- Limits: At tier 1 a merge that permits only a fast-forward passes for main and master. The options that end a merge in progress pass.

**GD-04.** If an agent command pushes to a protected ref, then the command guard MUST refuse the command.
<!-- id: SDD-GD-04 | tdd: TDD-5.3 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: Each spelling counts: a branch name, a refspec with a protected target, a full ref name, a delete, and the word `HEAD` while a protected branch is current.
- Verified by: The guard tests of twelve spellings at tiers 2 to 4, of the word `HEAD` on two branches, and of tier 1.
- Limits: At tier 1 a push of main or master with no force passes, and develop stays refused.

**GD-05.** If an agent command does an owner action on a pull request, then the command guard MUST refuse the command.
<!-- id: SDD-GD-05 | tdd: TDD-5.4 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The owner actions are merge, mark ready and approve. They count as `gh pr merge`, `gh pr ready` and `gh pr review --approve`, and as a `gh api` call that merges.
- Verified by: The guard test of eight merge forms and four permitted forge commands.
- Limits: A read of a pull request and the creation of a draft pull request pass.

**GD-06.** If an agent command force-deletes a branch that a different worktree has checked out, then the command guard MUST refuse the command.
<!-- id: SDD-GD-06 | tdd: TDD-5.5 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The reason names the worktree that holds the branch.
- Verified by: The guard test of five delete forms and four permitted forms.
- Limits: A branch that no worktree holds, the branch of the own worktree and a delete with no force pass.

**GD-07.** If an agent command removes or cleans a worktree that is not the worktree of its session, then the command guard MUST refuse the command.
<!-- id: SDD-GD-07 | tdd: TDD-5.5 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The worktree of a session is the worktree of the folder where the session works. A clean counts when its folder or one of its path arguments is in a different worktree.
- Verified by: The guard test of seven remove and clean forms and five permitted forms.
- Limits: A clean of the own worktree, a dry run of a clean and the addition of a worktree pass.

**SC-14.** Each desktop session MUST work on a branch whose name starts with wip/.
<!-- id: SDD-SC-14 | tdd: TDD-5.20 -->

- Behavior: The session entry gives the rule to each agent. The agent renames the branch to a type and a short description before a push.
- Verified by: The session entry holds the rule. No test proves the name of the branch.
- Limits: No part of the platform makes or checks the name of the branch. The Git hooks and the command guard refuse the push of such a branch.

**SC-16.** The Zed agent MUST NOT write code in a registered repository.
<!-- id: SDD-SC-16 | tdd: TDD-5.20 | gap: #23 -->

- Behavior: A write in Zed goes through Claude Code or Codex over the agent client protocol, so the guards of that agent apply. The built-in agent of Zed uses a read profile and asks before each tool.
- Verified by: The check steps of the Zed setup document, which the owner does by hand on the Mac. No test in the repository proves the rule.
- Limits: Zed has no command guard. The Git hooks and the server rules still apply to a push from Zed.

**SC-17.** Each agent MUST write commit text, pull request text and issue text in ASD-STE100.
<!-- id: SDD-SC-17 | tdd: TDD-5.20 -->

- Behavior: The session entry, the guidance of the worker seat and of the control seat and the brief of a loop worker give the rule. The type prefix of a title stays.
- Verified by: A test reads the rule in the session entry, in the guidance of the worker seat and of the control seat, and in the brief of a loop worker.
- Limits: No hook and no check reads the text of a commit, a pull request or an issue for this rule.

**GD-08.** The command guard MUST examine each shell command of an agent before the command runs.
<!-- id: SDD-GD-08 | tdd: TDD-5.1, TDD-5.2, TDD-5.10, TDD-5.11 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The harness gives the guard the command and the folder of the session. The guard applies the tier and the current branch of the repository that the command names, through a folder option or a change of folder.
- Observable: A refused command does not run, and the agent gets one line that starts with `dev-platform guard:` and gives the reason. A permitted command runs with no change.
- On failure: Where the guard cannot read its Git rules, it refuses the command. Where the guard cannot run in a Pi seat, the seat refuses the command.
- Verified by: The guard rule tests run the guard on real repositories with a main checkout and two linked worktrees. The check of the Pi seat extensions proves six refusals, four permitted commands and the refusal when the guard is absent.
- Limits: The guard reads shell commands only, not the edit tools. Codex runs the guard only where the owner merged the hook entry into the Codex hooks file by hand.

**GD-09.** The command guard MUST apply a Git rule or a forge rule only to a command word of the command line.
<!-- id: SDD-GD-09 | tdd: TDD-5.2 -->

- Behavior: A command word is the first word of a simple command, also inside a shell wrapper, an evaluated string or a command substitution. Quoted text, a comment, a search pattern and the body of a here-document are no command words.
- Observable: A search for the text of a refused command passes. The same refused command inside `bash -c`, `eval`, `sudo` or a substitution is refused.
- Verified by: The guard tests of seven read commands that quote a refused command, and of eight wrapped forms of a refused command.
- Limits: The text rules for services, remote hosts, the Desktop folder and the checkout folders do not read quotes: quoted text after a command separator can match them.

**GD-10.** If an agent command forces a push, then the command guard MUST refuse the command at each tier.
<!-- id: SDD-GD-10 | tdd: TDD-5.3 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: Each force option of the push command counts, and so does a refspec that starts with a plus sign.
- Verified by: The guard test of four force forms at tiers 1 to 4.

**GD-11.** If an agent command pushes a branch whose name starts with wip/, then the command guard MUST refuse the command at each tier.
<!-- id: SDD-GD-11 | tdd: TDD-5.3 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The target of each refspec counts. The reason tells the agent to rename the branch to a type and a short description first.
- Verified by: The guard test of three wip forms at tiers 1 to 4.

**GD-12.** If an agent command pushes with no branch name, then the command guard MUST refuse the command.
<!-- id: SDD-GD-12 | tdd: TDD-5.3 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: A push with no refspec is refused. A push of all branches and a mirror push are refused at each tier.
- Observable: The reason tells the agent to name the branch.
- Verified by: The guard tests of a push with no refspec at tier 2 and at tier 1, and of the all and mirror options at tier 1.
- Limits: At tier 1 a push with no refspec passes.

**GD-13.** Where a repository has tier 3, the command guard MUST refuse a command that adds a tool attribution to the repository or its forge.
<!-- id: SDD-GD-13 | tdd: TDD-5.3, TDD-5.8 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: A tool attribution is a pushed branch whose name starts with a tool name, or a co-author line or a generated-with line in the text of a command. The commands are a commit, and a forge command that creates, edits or comments on a pull request or an issue.
- Verified by: The guard tests of three tool-named branches at each tier and of a commit command with an attribution. No test proves the rule for a forge command.
- Limits: An unregistered repository gets the rule of tier 3. At tiers 1, 2 and 4 such a command passes.

**GD-14.** If an agent command sets the land variable, then the command guard MUST refuse the command.
<!-- id: SDD-GD-14 | tdd: TDD-5.2 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The land variable is `DEV_LOOP_LAND`. An assignment before a command, an export, and an assignment inside a wrapper or an evaluated string count.
- Verified by: The guard test of four forms that set the variable and two read commands, at tier 1 and tier 2.
- Limits: The name of the variable as the text of a read command passes.

**GD-15.** If an agent command rewrites history, then the command guard MUST refuse the command.
<!-- id: SDD-GD-15 | tdd: TDD-5.6 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: A history rewrite is a rebase, a hard reset, an amend of a commit and a filter of a branch.
- Verified by: The guard tests of the four forms.

**GD-16.** If an agent command turns the Git hooks off, then the command guard MUST refuse the command.
<!-- id: SDD-GD-16 | tdd: TDD-5.6 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The option that skips the hooks of a commit or a push counts, in its long and its short form. A change of the hooks path of Git counts, as a config command or as a one-command option.
- Verified by: The guard test of six forms and three permitted forms, and the test of the Git rules that are off.
- Limits: A read of the hooks path and the option as the text of a commit message pass. The rule for the hooks path stays where the record of a project turns the Git rules off.

**GD-17.** While a second live agent works in a worktree, the command guard MUST refuse a command that moves HEAD or the index there.
<!-- id: SDD-GD-17 | tdd: TDD-5.7 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The commands are checkout, switch, merge, reset, pull, cherry-pick and revert, and the pop and the apply of a stash. A read, a commit and an option that aborts an operation pass.
- Observable: The reason names the second agent, its process and its folder. It tells the agent to commit where it is and to read a different ref with `git show`.
- Verified by: The guard tests with a live process named as an agent: ten refused commands, eight permitted commands, a nested worktree, and the agent that runs the guard.
- Limits: A second live agent is a Claude Code or Codex process whose working folder is in the worktree; the guard does not see a Pi process. A worktree inside the worktree is a different worktree, and the agent that runs the guard does not count.

**GD-18.** If an agent command makes a checkout in a refused folder, then the command guard MUST refuse the command.
<!-- id: SDD-GD-18 | tdd: TDD-5.8 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: A worktree and a clone are refused in the memory folders of the machine: /tmp, /dev/shm and /run/user. A worktree is also refused in the retired folder dev/wt of a home.
- Observable: The reason names the right place: the worktrees folder inside the repository.
- Verified by: The guard tests of five forms in a memory folder and three forms in the retired folder, with the permitted forms of each.

**GD-19.** If an agent command uses the Desktop folder as a place for scripts, then the command guard MUST refuse the command.
<!-- id: SDD-GD-19 | tdd: TDD-5.8 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: A command that writes, copies, moves or changes the mode of a file in the Desktop folder of the home counts. An interpreter that runs a script from that folder also counts.
- Verified by: The guard test of five forms and of a listing of the folder.
- Limits: A read of the folder passes.

**GD-20.** If an agent command changes the run state of a container or a system service, then the command guard MUST refuse the command.
<!-- id: SDD-GD-20 | tdd: TDD-5.8 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: The rule covers the compose commands and the container commands that start, stop, restart or remove a container. It also covers the service manager commands that start, stop, restart, reload, enable or disable a unit.
- Verified by: The guard tests of two compose commands, and the check of the Pi seat extensions for a service restart.
- Limits: The owner can lift this rule for one session with the variable `DEV_PLATFORM_ALLOW_MUTATIONS`; the push rules and the merge rules stay. No test proves the variable.

**GD-21.** If an agent command changes a remote host through a remote shell, then the command guard MUST refuse the command.
<!-- id: SDD-GD-21 | tdd: TDD-5.8 -->

- Actor: An agent in Claude Code, in Codex or in a Pi seat.
- Behavior: A remote shell as root always counts. For a different user, a remote command counts when it holds a word of restart, deploy, shutdown or removal, or the name of a container tool or a service tool.
- Verified by: The guard tests of a remote shell as root. No test proves the rule for a different user.
- Limits: A read-only remote command passes. The owner can lift this rule for one session with the variable `DEV_PLATFORM_ALLOW_MUTATIONS`.

**GD-22.** Where the owner turns the Jev classifier on, the command guard MUST refuse a permitted command that the classifier rates as high risk.
<!-- id: SDD-GD-22 | tdd: TDD-5.9 -->

- Behavior: The classifier gets the command only when each rule permitted it. High risk is the class of credentials, privacy and billing, or the destructive or external class with a confirmation probability of 0.75 or more.
- Verified by: The Jev tests prove the question schema and the decide command. A guard test runs the guard with a fake classifier on.
- Limits: The switch is the Jev guard variable and it is off by default. An absent classifier, a reached cap, a late answer or a malformed answer leaves the result of the rules.

**GD-23.** The Codex rules MUST forbid each listed literal form of a command that the command guard refuses.
<!-- id: SDD-GD-23 | tdd: TDD-5.11 -->

- Actor: An agent in Codex.
- Behavior: The list holds forms of a push to a protected ref, a force push, a hook skip, a history rewrite, a pull request merge, a branch delete, a worktree removal, a clean, a service change and a root shell. The rules also permit a short list of read commands and build commands with no prompt.
- Verified by: The Codex rule tests ask the installed Codex for its decision on fifteen forbidden forms and three ordinary forms. The tests skip where Codex is not installed.
- Limits: A rule matches literal words from the start of a command, so a folder option and an unlisted refspec do not match. The rules are the same in each repository, so Codex cannot push main at tier 1.

**GD-24.** Where a repository has tier 3, the Git hooks MUST refuse the push of a branch whose name starts with a tool name.
<!-- id: SDD-GD-24 | tdd: TDD-5.12 -->

- Behavior: The tool names are those of the three coding agents, each with a slash after it.
- Verified by: The pre-push tests of three tool-named branches at tier 3 and of one at tier 2.
- Limits: An unregistered repository gets the rule of tier 3. At tiers 1, 2 and 4 such a branch passes.

**GD-25.** When the land verb pushes, the Git hooks MUST allow a fast-forward of a protected ref at tier 1 and tier 2.
<!-- id: SDD-GD-25 | tdd: TDD-5.12 -->

- Actor: A person or an agent that runs `dev-loop land`.
- Behavior: The land verb sets the land variable for its own push. At tier 3 and tier 4 the variable changes nothing.
- Verified by: The pre-push tests of the land variable at tiers 1 and 2, with a force update and at tier 3.
- Limits: A force update stays refused with the variable set. The command guard refuses an agent command that sets the variable.

**GD-26.** The Git hooks MUST run the hook of the repository that has the same name, with the same input.
<!-- id: SDD-GD-26 | tdd: TDD-5.12, TDD-5.13, TDD-5.14 -->

- Behavior: A global hooks path turns the hooks of a repository off in Git. Each platform hook starts the hook of the repository when its own rules pass, and the result of that hook decides.
- Observable: A hook of the repository that exits with a fault still stops the commit or the push.
- Verified by: The tests of a repository hook for the push, for the commit message and for the commit.

**GD-27.** If the full check passed on the present state of a tree, then the check-once command MUST NOT run the full check again.
<!-- id: SDD-GD-27 | tdd: TDD-5.16 -->

- Actor: An agent, the stop check, the loop or a forge.
- Observable: The command prints that the check already passed on this tree, with the hash of the state and the place of the log, and exits with 0.
- Verified by: The check tests count the runs of a check script: one run for two calls on the same state, and no run for the status option.
- Limits: With the status option the command runs no check: it exits with 0 for a recorded pass and with 1 for none. The record is for one worktree.

**GD-28.** When the commit, the index or a source file of a tree changes, the check-once command MUST treat the recorded pass as void.
<!-- id: SDD-GD-28 | tdd: TDD-5.16 -->

- Behavior: A source file is each tracked file and each untracked file that Git does not ignore, without the untracked notes of a worker. The environment file of the repository, the check command and the search path of commands also belong to the state.
- On failure: A submodule with uncommitted changes cannot be part of a state: the command stops and records no pass.
- Verified by: The check tests of an edited file, a new untracked file, a staged change that the file no longer shows, a tracked worker file, a changed environment file, a dirty submodule and a dirty linked worktree.
- Limits: A linked worktree inside the checkout is the tree of a different session and is no content of this tree.

**GD-29.** The check-once command MUST take the full check from the project record first and from the repository second.
<!-- id: SDD-GD-29 | tdd: TDD-5.15 -->

- Behavior: In the repository the order is the check file of the bin folder, the check script of the package file, then the check file of the scripts folder. A variable of the session cannot state the check.
- On failure: With no full check in any place, the command names the places, exits with 2 and records no pass.
- Verified by: The check tests of each source and of each pair of sources, the test of no source, and the project record test of the check of the record.

**GD-30.** The check-once command MUST record a pass only when the full check passed and the state of the tree did not change.
<!-- id: SDD-GD-30 | tdd: TDD-5.16 -->

- Observable: For a failed check the command prints the last 30 lines of the log and exits with 1. For a change during the run it says that the tree or the environment changed, and exits with 1.
- Verified by: The check tests of a check that fails, of a check that passes after a failure, and of a check that changes a source file during its run.
- Limits: The command removes the earlier record before it starts a run.

**GD-31.** While a check runs on a tree, the check-once command MUST NOT start a second check on that tree.
<!-- id: SDD-GD-31 | tdd: TDD-5.16 -->

- Behavior: A lock in the Git folder of the worktree names the process that holds it. A `next build` process that works in the tree also counts as a check that runs.
- Observable: The command says that another check runs or holds the lock, and exits with 3.
- On failure: A lock whose holder no longer runs is cleared with one line of notice. A lock with no note of its holder is kept.
- Verified by: The check tests of a lock with no holder note, with a live holder and with a holder that is gone, and of a build in the same tree and in a different tree.

**GD-32.** When a stop signal arrives, the check-once command MUST leave no process of the check and no lock.
<!-- id: SDD-GD-32 | tdd: TDD-5.16 -->

- Behavior: The check runs as a child of the command. The command ends each process below that child, waits for it, releases the lock and exits with 143.
- Observable: The next call is not refused for a lock, and the status option reports no pass.
- Verified by: The check test that sends the signal to a check with a child process.

**GD-33.** When a session stops in a tree with changes, the stop check MUST run the check-once command on that tree.
<!-- id: SDD-GD-33 | tdd: TDD-5.17 -->

- Actor: A Claude Code session.
- Behavior: Changes are uncommitted changes of tracked files, or commits that the upstream branch does not hold. The tree is the folder of the session that the harness names, so a session in a linked worktree gets the check of its own worktree.
- Observable: The session gets one line that starts with `dev-platform:` and gives the result.
- Verified by: The stop check tests of a changed tree, a second stop on the same state, a linked worktree, commits ahead of the upstream, a clean tree at its upstream, and a repository whose only check is the check file of the scripts folder.
- Limits: A clean tree at its upstream gets no check, and a project whose record turns the full check off gets none. The stop check and the check-once command find the check by one rule, so a repository with no check gets none.

**GD-34.** If the full check fails at a stop, then the stop check MUST block the stop.
<!-- id: SDD-GD-34 | tdd: TDD-5.17 -->

- Actor: A Claude Code session.
- Observable: The agent gets the folder of the tree and the last 30 lines of the check output.
- Verified by: The stop check tests of a check that fails and of a lock that a live process holds.
- Limits: A check that cannot start because a different check runs on the tree is no failure: the stop passes with one line.

**GD-35.** When a stop follows a block of the stop check, the stop check MUST let the stop through.
<!-- id: SDD-GD-35 | tdd: TDD-5.17 -->

- Behavior: The harness marks such a stop in the hook input. The stop check then runs no check.
- Verified by: The stop check test with the mark set, in spaced and in compact JSON.

**GD-36.** While a tree has the orchestrated marker, the stop check MUST NOT run the full check.
<!-- id: SDD-GD-36 | tdd: TDD-5.17 -->

- Behavior: The orchestrator of a forge writes the marker when it gives work to its workers and removes it at the end of the goal. The marker counts for each worktree of the repository.
- Observable: The session gets one line that says that the orchestrator runs the check.
- Verified by: The stop check test of a marked tree and its linked worktree, and the forge test that sets and removes the marker.
- Limits: An agent can still run the check-once command directly.

**GD-37.** When an edit tool changes a file, the format hook MUST format that file with the formatter of its repository.
<!-- id: SDD-GD-37 | tdd: TDD-5.18 -->

- Actor: A Claude Code session, after its Edit tool or its Write tool.
- Behavior: The formatter is the Prettier program that the repository installed. The hook acts on the script, data, style, page and document files of the web, and Prettier reads the ignore file of the repository.
- On failure: With no formatter, a file of a different kind, a missing file or a fault of the formatter, the hook changes nothing and exits with 0. The tool call does not fail.
- Verified by: The formatter tests with a stand-in formatter, with no formatter, with a file of a different kind and with a missing file.

**GD-38.** When a Claude Code session needs a person or stops on an error, the notify hook MUST send one message to the owner.
<!-- id: SDD-GD-38 | tdd: TDD-5.19 -->

- Behavior: The message goes through the notify command of the machine. It holds the reason, the user, the host, the folder and the first eight characters of the session identifier, and a stop on an error has high priority.
- On failure: The hook always exits with 0, so a fault of the notify command does not fail the session.
- Verified by: A test runs the hook with a fake notify command for each event, reason, limit and switch, and reads the hook settings for the two events.
- Limits: The same session and reason send one message in 10 minutes, and an idle prompt, a successful sign-in and a completed question send none. With no notify command, or with the notify switch variable set to off, the hook sends nothing.

## LP. Loop and forge
<!-- section: SDD-LP | sys: SYS-PL-02 -->

This section says how a goal becomes tasks and how each task reaches one worker. A task is one file or one issue with a state, a scope and its dependencies, so that a worker gets one bounded request and needs no second source. The loop gives each ready task to one worker with one brief, and the goal forge lets many workers commit while one orchestrator runs one full check for a batch of results. The owner, the orchestrator and the workers use these parts through the loop commands, the forge commands and the task files, in a repository of each kind. The incoming file keeps candidate requirements out of each repository until the owner takes one in. A registered repository keeps no decision record by default, so the specification is the one record of a requirement.

The reasons:

- LP-02: Git records that a JSON task is done, so the task needs no done field (decision 0002).
- LP-04: Each repository keeps its tracker as it is: task files, GitHub issues or none (decision 0002).
- LP-06: The history of a task is the file and the merge that closed it (docs/tasks/README.md).
- LP-07: The number joins the task with its slot, its ledger line and its closing trailer (skills/loop/scripts/loop-tasks.py).
- LP-09: Intake writes the tasks on the goal branch, not in the main checkout (skills/intake/SKILL.md).
- LP-12: The acceptance of the owner is the gate: intake drafts a decision as proposed and stops (skills/intake/SKILL.md).
- LP-14: An old decision does not override the present specification (skills/intake/SKILL.md).
- LP-15: No new decision can be written in this mode, so the word of the owner is the gate (skills/loop/scripts/loop-tasks.py).
- LP-19: The steer is the gate of the loop (skills/loop/SKILL.md).
- LP-22: A task is the whole request: the worker reads it and the specification that it cites, and nothing else (docs/tasks/README.md).
- LP-23: The specification is decided before it is built, so a change of it never rides inside a build task (skills/intake/SKILL.md).
- LP-25: One profile holds each value of the project, so that a rig of each runtime uses the same tools (docs/forge.md).
- LP-27: The profile does not state a value of the project record a second time (docs/forge.md; area PJ).
- LP-28: A runtime gives only the start of a one-task worker; each other part of the rig is files, Git and shell commands (docs/forge.md).
- LP-30: The owner reads each value before the rig uses it (docs/forge.md).
- LP-31: The control folder of the first rig had no history when it was lost (lib/ai_ecosystem/forge.py).
- LP-32: Reports go up as small files, and a wait in the background wakes the reader (docs/forge.md).
- LP-34: Heavy checks and short proofs take places of the machine in one fair line (docs/forge.md).
- LP-35: A wait costs less than a stop by the kernel (lib/ai_ecosystem/forge.py).
- LP-37: A task with no scope can change each file, so it runs alone (docs/forge.md).
- LP-41: A worker writes code and tests and runs only a short proof (docs/forge.md).
- LP-42: The orchestrator runs the full check one time on the batch (docs/forge.md).
- LP-44: One warm check folder keeps the dependencies and the build output between batches (docs/forge.md).
- LP-47: The orchestrator gives a failed task to the next free worker (lib/ai_ecosystem/forge.py, the culture text).
- LP-52: One orchestrator and its workers share the tree, and the orchestrator runs the full check for each batch (docs/source-control.md).
- LP-54: People read, discuss and edit the candidates by hand, and the rank shows which candidate is an easy change (skills/distill/SKILL.md).
- LP-57: Raw records are never copied into a repository (skills/distill/SKILL.md).
- LP-58: The specification is decided before it is built (skills/intake/SKILL.md).
- LP-59: A worker can take a task without a question when the task cites the specification (skills/intake/SKILL.md).
- SC-08: One goal made 2N + 1 runs of the full check before; the design brings it to N + 1 (decision 0001).
- LP-01: For 24 tasks in batches of 6, the full check runs 4 times and not 25 times (docs/forge.md).
- SC-10: The candidates make no commit and no branch (decision 0001, point 4; docs/source-control.md).
- SC-19: The specification is the only record of a requirement, and Git records each change of it (skills/intake/SKILL.md; docs/source-control.md).
- SC-28: Git records each change of the specification, so a second ledger is not necessary (docs/source-control.md).
- SC-20: Only the owner changes a requirement: by hand, or through an agent that uses the write commands of the specification (skills/intake/SKILL.md).
- SC-22: One failed batch adds about three runs of the full check and loses no good task (docs/forge.md).
- SC-23: No check, no automatic fold (docs/forge.md).
- SC-24: A new context for each task is one of the mechanisms that make the forge fast (docs/forge.md).
- SC-25: The places are for the whole machine, so that two rigs stand in one line (docs/forge.md).
- SC-27: The rig is files, Git and shell commands, so that each runtime uses the same tools (docs/forge.md).
- TK-01: An audit of 1584 Markdown task files found free prose, acceptance mixed into the prose and stale status lines (decision 0002).
- TK-12: The platform stays able to work with each kind of repository, and the move of a repository is a separate decision (decision 0002).
- TK-02: One strict schema keeps the tasks of each owned repository in the same form (decision 0002).
- TK-04: No task of the old form named a goal (decision 0002).
- TK-15: A task that needs more than eight checks is two tasks (skills/intake/SKILL.md).
- TK-16: Acceptance was mixed into the prose of the old tasks (decision 0002).
- TK-05: One repository already had 891 commits with the work trailer, so three open tasks read as closed; no repository used the closing trailer (decision 0002).
- TK-17: 1068 done task files still had the status ready; Git is the one record of done (decision 0002).
- TK-07: The loop stays one tool for each kind of repository (decision 0002).
- TK-10: The owner asked for typed tasks in each owned repository from now on, with no pilot in a company repository (decision 0002).
- TK-20: A repository does not depend on the platform to validate its tasks (decision 0002; area PJ).
- TK-11: A first conversion compressed the task text to fit the typed fields; the typed fields index the task and do not replace its meaning (decision 0002, point 7).
- TK-21: The system does not lose the meaning and the language of a task (decision 0002, point 7).

**SC-08.** The full check MUST run one time on each worker result where the goal is not a forge.
<!-- id: SDD-SC-08 | tdd: TDD-6.6 | gap: #16 -->

- Behavior: The worker runs the full check on its last commit, and the check records the tree that passed. The fold examines only the conflicts, the scope and the specification.
- Observable: A second run on a tree that passed starts no check.
- Verified by: The loop test that reads the check step of a worker brief, and the tests of a tree that passed before.
- Limits: The close of the goal runs the full check one more time, on the goal branch.

**LP-01.** Where a goal runs as a forge, the forge MUST run the full check one time on each batch of results.
<!-- id: SDD-LP-01 | tdd: TDD-6.18 -->

- Behavior: The batch command stacks the results and runs the full check on the last commit of the stack. A worker runs only the short proof. When the folded goal tip is the tree that passed, the batch records the pass for the goal worktree, so the close of the goal starts no second check on that tree.
- Observable: The batch command prints the count of full checks, and the batch ledger keeps it.
- Verified by: The batch test that folds three tasks with one full check, and the land test that counts one run of the full check for a batch and its land.
- Limits: A batch that fails adds runs to find the first bad task. The close of the goal runs the full check again when the check of the repository is not the full check of the profile, or when the tree or the environment changed after the batch.

**SC-22.** If the full check fails on a batch, then the forge MUST fold only the tasks before the first task that fails.
<!-- id: SDD-SC-22 | tdd: TDD-6.18 -->

- Behavior: The forge searches the first task that fails in halves of the stack. The tasks behind it stay in their slots for the next batch.
- Observable: The batch command names the failed task and exits with 1.
- Verified by: The batch test with a bad task in the middle.

**SC-23.** Where the profile of a forge names no full check, the forge MUST NOT fold a task.
<!-- id: SDD-SC-23 | tdd: TDD-3.9, TDD-6.18 -->

- Behavior: The forge stacks the batch in the check folder and stops for the owner. The full check is the command that the profile states, or the check command of the project record that the profile names.
- Observable: The batch command says that nothing is folded and exits with 3.
- Verified by: The batch test of a profile with no full check, and the test of a profile that names a project record.

**SC-24.** A forge MUST give each task to a worker with a new context.
<!-- id: SDD-SC-24 | tdd: TDD-6.6, TDD-6.17 -->

- Behavior: The slot and the seat live for the goal, and the context lives for one task. All state is in files, so a new context loses nothing.
- Verified by: The brief tests and the test of a start by hand.

**SC-25.** The machine MUST run at most the configured number of heavy commands of all forges at one time.
<!-- id: SDD-SC-25 | tdd: TDD-6.15 -->

- Behavior: A command takes one place of the machine, and the waiters stand in one line where a later waiter does not pass an earlier one. The forge returns the exit code of the command that it runs.
- Observable: The command prints the place that it takes.
- Verified by: The test that starts three commands on one heavy place.

**SC-26.** While a running task shares a scope path with a ready task, the forge MUST NOT list the ready task as free.
<!-- id: SDD-SC-26 | tdd: TDD-6.16 -->

- Behavior: Two scope paths are shared when they are equal or one is a folder above the other. The list names the running task and the path that hold the ready task.
- Verified by: The tests of the ready list.

**SC-27.** When a session posts a report, the forge MUST write the report as one file in the inbox of the reader.
<!-- id: SDD-SC-27 | tdd: TDD-6.14 -->

- Behavior: The file holds the sender, the reader, the time and the text. A reader never sees half of a report, because the file gets its final name in one step.
- On failure: A name with a character that is not a lowercase letter, a digit or a hyphen stops the post, and so does an empty text.
- Verified by: The channel tests.
- Limits: A report is a request of a teammate. It gives no permission and is never the word of the owner.

**LP-02.** When the loop folds a task, the fold commit MUST carry the work trailer and the closing trailer of that task.
<!-- id: SDD-LP-02 | tdd: TDD-6.2 -->

- Behavior: The fold moves a Markdown task file to the done folder in the same commit. A JSON task file stays in its place.
- Verified by: The loop test that reads the trailer text of the fold, and the test that only a Markdown task moves.

**LP-03.** The tier record of each repository MUST give the place of the incoming file as the incoming setting states.
<!-- id: SDD-LP-03 | tdd: TDD-6.9 -->

- Behavior: With the value `state`, the default, the file is in the state folder of the platform and has the name of the repository. With the value `project`, the file is in the docs folder of the main checkout.
- On failure: A different value makes the registry line invalid, and the command exits with a failure.
- Verified by: The test of the tier record with each value and with a wrong value.

**LP-04.** The loop MUST read the tasks of a project from the place that its tracker setting names.
<!-- id: SDD-LP-04 | tdd: TDD-6.1, TDD-6.5 -->

- Behavior: With the value `files`, the tasks are files in the task folder on the base branch; with `github`, they are the open issues of the repository. With `side`, they are files in the side folder of the project.
- Observable: `dev-loop tier` prints the tracker.
- Verified by: The loop tests of a local repository, which calls no GitHub command, and the tests of the side folder.
- Limits: A registry line with no tracker gets files in the local mode and GitHub issues in each other mode.

**LP-05.** If the tracker of a project is GitHub, then the task commands of the loop MUST refuse the project.
<!-- id: SDD-LP-05 | tdd: TDD-6.1 -->

- Behavior: The task commands list, number, write, examine and show task files.
- Observable: The command says that the project keeps its tasks as GitHub issues and exits with 2.
- Verified by: The loop test of the task commands on a GitHub project.

**LP-06.** When a Markdown task file moves to the done folder, the loop MUST read that task as closed.
<!-- id: SDD-LP-06 | tdd: TDD-6.1, TDD-6.2 -->

- Behavior: A Markdown task is one file with the number of the task and a short name. Its first heading is the title, and its lines give the status, the labels, the scope and the dependencies.
- Verified by: The loop test that runs from task files to a local merge.

**LP-07.** If two task files have one number, then the loop MUST refuse to read the tasks.
<!-- id: SDD-LP-07 | tdd: TDD-6.1 -->

- Observable: The command names each such number and exits with a failure.
- Verified by: The loop test where two branches take the same number.

**LP-08.** The loop MUST NOT give a new task a number that a task of the base or of the checkout holds.
<!-- id: SDD-LP-08 | tdd: TDD-6.3 -->

- Behavior: The next number is one more than the highest number of an open task or a done task.
- Verified by: The loop test of the next number with a done task.
- Limits: Two branches that do not see each other can take the same number; the task check and the merge show it.

**LP-09.** When a user makes a new task, the loop MUST write the task file in the worktree where the command runs.
<!-- id: SDD-LP-09 | tdd: TDD-6.3 -->

- Behavior: The new task is a draft unless the user asks for a ready task. The command needs a title of one line and a scope, and it prints the path of the file.
- On failure: A title of more than one line, an empty title and a missing scope stop the command, and no file is written.
- Verified by: The loop test that writes a task in a second worktree.

**LP-10.** Where the task form of a project is JSON, the loop MUST write each new task as a JSON draft.
<!-- id: SDD-LP-10 | tdd: TDD-6.3 -->

- Behavior: The draft holds a marked place for the brief and for the first acceptance check. The command writes only a task of the kind code or spec.
- On failure: A new JSON task with no goal stops the command.
- Verified by: The loop tests of a new task with the JSON form, with no goal and with the default form.

**LP-11.** If an open task file is one that the loop cannot read correctly, then the task check MUST name the file and fail.
<!-- id: SDD-LP-11 | tdd: TDD-6.3 -->

- Behavior: The causes are: no title, a status that is not ready or draft, no scope line, no dependency line, and a dependency on itself or on a number with no task file. A ready JSON task that still holds a marked place of the draft is a cause also.
- Observable: With no problem, the check prints the count of open tasks.
- Verified by: The loop tests of a bad Markdown task and of a ready JSON task with a marked place.

**LP-12.** Where a repository has `decisions=open`, the loop MUST NOT give a worker a ready task that cites a decision record that is not accepted.
<!-- id: SDD-LP-12 | tdd: TDD-6.4 -->

- Behavior: A citation is the path of a decision record or a decision line with its number. The task list shows the task as waiting, with the decision and its status.
- Verified by: The loop test where a task waits for the decision of the owner, in a repository with `decisions=open`.

**LP-13.** Where a repository has `decisions=open`, the loop MUST NOT give a worker a ready task with a governed label that cites no accepted decision record.
<!-- id: SDD-LP-13 | tdd: TDD-6.4 -->

- Behavior: The owner lists the governed labels, for example legal, in the environment of the loop. With no list, a label holds no task.
- Verified by: The loop test where a task with a legal label waits, in a repository with `decisions=open`.

**LP-14.** Where a repository has `decisions=none` or `decisions=frozen`, a decision record that a task cites MUST NOT hold the task.
<!-- id: SDD-LP-14 | tdd: TDD-6.4 -->

- Behavior: A cited decision record is history with these values. The value `none` is the default of a registered repository.
- Verified by: The loop tests of the two values: a task that cites a proposed decision is ready, and a task that cites an absent decision is ready.

**LP-15.** Where a repository has `decisions=none` or `decisions=frozen`, the loop MUST hold each ready task with a governed label for the owner.
<!-- id: SDD-LP-15 | tdd: TDD-6.4 -->

- Behavior: The task waits until the owner removes the label or gives the task to a person. The task list says that the task needs the word of the owner.
- Verified by: The loop test of the default value, where a task with a legal label waits for the word of the owner.

**LP-16.** While a dependency of a ready task is not closed and not folded, the loop MUST NOT select the task.
<!-- id: SDD-LP-16 | tdd: TDD-6.5 -->

- Behavior: The plan lists the task as skipped, with each dependency that it waits for.
- Verified by: The loop test where the second task waits for the first.

**LP-17.** The loop MUST NOT select two tasks with overlapping scope paths for one dispatch.
<!-- id: SDD-LP-17 | tdd: TDD-6.5 -->

- Behavior: Two paths overlap when one starts with the other. The plan lists the later task as skipped, with the path.
- Verified by: A plan test with two overlapping tasks, which is not written.

**LP-18.** While the count of running workers is at the worker limit, the loop MUST NOT start a worker.
<!-- id: SDD-LP-18 | tdd: TDD-6.5, TDD-6.17 -->

- Behavior: The limit is 3 unless the environment of the loop states a different number. A forge gives the worker limit of its profile to the loop.
- Observable: The loop says that the worker cap is reached.
- Verified by: The loop test of a resume at the limit.

**LP-19.** While the steer of a repository is pause, the scheduled dispatch MUST NOT start a worker.
<!-- id: SDD-LP-19 | tdd: TDD-6.5 -->

- Behavior: The steer is go or pause, and a missing steer is pause. The end of a goal writes pause.
- Verified by: The loop tests that read the steer; a test of a scheduled dispatch at pause is not written.

**LP-20.** If the owner is not present, then the loop MUST NOT start a paid worker.
<!-- id: SDD-LP-20 | tdd: TDD-6.5 -->

- Behavior: The owner is present at a terminal, or in a session that the owner started through one of the portals term, desk and phone. A service unit and a scheduled dispatch alone start no paid worker.
- Observable: The loop says that nothing is dispatched, and the steer does not change.
- Verified by: The loop test that paid workers start only on the word of the owner.

**LP-21.** While a worker holds a task, the loop MUST NOT start a second worker for that task.
<!-- id: SDD-LP-21 | tdd: TDD-6.5 -->

- Behavior: One dispatch runs at one time for a repository. A second dispatch is refused while the first holds the lock.
- Verified by: The tests of the dispatch lock.

**LP-22.** When the loop gives a task to a worker, the loop MUST write one brief in the slot of the worker.
<!-- id: SDD-LP-22 | tdd: TDD-6.6 -->

- Behavior: The brief names the task, its scope, the limits of the worker and the check to run, and it says where to read the task. The worker reports with a result file or a blocked file in the same slot and stops.
- Verified by: The loop tests that read the brief of a slot.

**LP-23.** If a task with no spec label changes the text of the specification, then the fold MUST refuse the task.
<!-- id: SDD-LP-23 | tdd: TDD-6.7 -->

- Behavior: Such a task can change only the trace comment and the lock line of an item; in the domains layout, only the status, tests and code lines. The refusal shows the changed lines.
- Verified by: The loop tests of a build task that changes a requirement, one for each layout.

**LP-24.** Where the specification layout is domains, the fold MUST refuse a marker change of an item that the task does not cite.
<!-- id: SDD-LP-24 | tdd: TDD-6.7 -->

- Behavior: The marker lines are the status, tests and code lines of an item. The generated index of the specification is free.
- Verified by: The loop test of the frozen mode with a marker of a second item.

**LP-25.** Each forge command MUST read one profile from the rig folder.
<!-- id: SDD-LP-25 | tdd: TDD-6.12 -->

- Behavior: The rig folder is the folder of the option, else of the environment, else the folder of the command or a folder above it that holds a profile. `dev-forge profile` prints the profile with its defaults and the values of the project record.
- On failure: With no rig folder or no profile, the command says how to make one and exits with 2.
- Verified by: The forge tests, which each read a profile from a rig folder.

**LP-26.** If the profile holds an unknown field or a value outside its range, then the forge MUST refuse the profile.
<!-- id: SDD-LP-26 | tdd: TDD-6.12 -->

- Behavior: The count of places of each kind is from 1 to 16, and the worker limit is from 1 to 99. The schema name of the profile is fixed. A field that an older profile held and that nothing read (the build command, the wait time of a batch and the review kinds) is refused as a removed field.
- Observable: The command names the field and exits with 2.
- Verified by: The forge tests of an unknown field and of each removed field.

**LP-27.** Where the profile names a project record, the forge MUST take each value that the profile leaves empty from that record.
<!-- id: SDD-LP-27 | tdd: TDD-6.12 -->

- Behavior: The values are the repository, the worker limit from the slots of the record, and the full check from the check command of the record. With no project record, the profile names the repository itself, and the worker limit is the slots of its registry line.
- On failure: A project with no such name, a project with more than one fitting repository, and a repository that differs from the record are refused.
- Verified by: The forge test of a profile that names a project record.

**LP-28.** Where the profile states the kind of a rig, the forge MUST start each worker in the way of that kind.
<!-- id: SDD-LP-28 | tdd: TDD-6.12, TDD-6.17 -->

- Behavior: The kinds are: forge, one headless run for each task; openrig, one seat of a running rig; harness, a start by hand; api, one headless run on the metered key. With a start by hand, the loop prepares the slot and the brief and starts no process.
- On failure: An unknown kind, a worker runtime that differs from the kind, and a seat runtime with no rig are refused.
- Verified by: The forge tests of the kind and of a start by hand.

**LP-29.** Where the profile names a worker model, the loop MUST start each worker of the forge with that model.
<!-- id: SDD-LP-29 | tdd: TDD-6.17 -->

- Behavior: The name is a model, a tier of the model file or a role.
- Verified by: The loop test of a model name; a forge test of the profile field is not written.

**LP-30.** When the owner asks for the profile of a repository, the forge MUST print a proposal and write no file.
<!-- id: SDD-LP-30 | tdd: TDD-6.13 -->

- Behavior: The proposal comes from the files of the checkout: the package manager, the scripts, and a check script as the full check. Where a project record holds the checkout, the proposal names the project and repeats no value of the record.
- Observable: The notes say what the forge found and that nothing is written.
- Verified by: The forge tests of the proposal and of each project type.

**LP-31.** When the owner confirms the proposal, the forge MUST make the rig folder as a Git repository of its own.
<!-- id: SDD-LP-31 | tdd: TDD-6.13 -->

- Behavior: The folder gets the profile, the culture text and the rig file of the team tool, and Git ignores the inbox, the failure logs and the two ledgers. The repository of the project gets no tracked file of the forge.
- On failure: A rig folder that already holds a profile is refused, and the owner changes that profile by hand.
- Verified by: A test of the write option, which is not written.

**LP-32.** When a reader waits on its inbox, the forge MUST print each new report and move it to the read folder.
<!-- id: SDD-LP-32 | tdd: TDD-6.14 -->

- Behavior: The read folder is the record of the channel. A wait with no report ends at its time limit with one line, and only the newest wait of an inbox reads it.
- Verified by: The channel test where a post is read one time.
- Limits: With the memory option, the wait also ends when the free memory of the machine stays low.

**LP-33.** When a user asks for the stale reports, the forge MUST list each report that no reader read in the given time.
<!-- id: SDD-LP-33 | tdd: TDD-6.14 -->

- Behavior: The default time is five minutes.
- Verified by: The channel test of a stale report.

**LP-34.** The machine MUST run at most the configured number of light commands of all forges at one time.
<!-- id: SDD-LP-34 | tdd: TDD-6.15 -->

- Behavior: The short proof of a worker takes a light place. The default is three light places and one heavy place.
- Verified by: The place tests use one heavy place; a test that fills the light places is not written.

**LP-35.** While the free memory of the machine is below the minimum of the profile, a forge command MUST NOT start in a place.
<!-- id: SDD-LP-35 | tdd: TDD-6.15 -->

- Behavior: A heavy command needs the full minimum, and a light command needs half of it. The command keeps its place while it waits, and the kernel stops this command first if memory runs out.
- Verified by: A test with a high minimum, which is not written.

**LP-36.** Where the profile states a load limit, a forge command MUST NOT start while the load of the machine is at that limit or above.
<!-- id: SDD-LP-36 | tdd: TDD-6.15 -->

- Behavior: The load is the average of the last minute. The default profile states no load limit.
- Verified by: A test with a load limit, which is not written.

**LP-37.** While a task runs, the forge MUST NOT list a ready task with no scope as free.
<!-- id: SDD-LP-37 | tdd: TDD-6.16 -->

- Behavior: The list shows such a task as alone, with the tasks that it waits for.
- Verified by: The ready list test of a task with no scope.

**LP-38.** The forge MUST NOT hold a ready task for a shared path that the profile lists as wide.
<!-- id: SDD-LP-38 | tdd: TDD-6.16 -->

- Behavior: A wide path is a file or a folder that many tasks change, for example a registry of contracts.
- Verified by: The ready list test of a wide path.

**LP-39.** If the tracker of the project is GitHub, then the forge MUST refuse each command that reads tasks.
<!-- id: SDD-LP-39 | tdd: TDD-6.16 -->

- Behavior: The commands are the ready list, the brief of a task and the batch. This version reads task files only, in the repository or in the side folder.
- Verified by: A forge test with a GitHub tracker, which is not written.

**LP-40.** When a user asks for the ready list, the forge MUST show each ready task as free, in work or held.
<!-- id: SDD-LP-40 | tdd: TDD-6.16 -->

- Behavior: The list holds only a task that the loop can give to a worker and whose dependencies are closed. The last line gives the counts and the worker limit.
- Verified by: The tests of the ready list.

**LP-41.** Where a goal runs as a forge, the worker brief MUST name the short proof of the profile.
<!-- id: SDD-LP-41 | tdd: TDD-6.6, TDD-6.17 -->

- Behavior: The short proof is the cheap command of the profile, then the proof command through a light place. The proof command can hold a mark for the tests: the output of the command for affected tests, or the test files of the change.
- Verified by: The forge test that reads the brief of a slot.
- Limits: With no proof in the profile, the brief tells the worker to run no check.

**LP-42.** Where a goal runs as a forge, the worker brief MUST forbid the full check and the build.
<!-- id: SDD-LP-42 | tdd: TDD-6.6, TDD-6.17 -->

- Verified by: The forge test that reads the brief of a slot, and the test that a worker of a plain loop still runs the full check.

**LP-43.** When a user asks for the brief of a task, the forge MUST print its scope, the worker rules and the report command.
<!-- id: SDD-LP-43 | tdd: TDD-6.17 -->

- Behavior: The default rules tell the worker to write code and tests only, to keep inside the scope, to start no agent and to stop when the acceptance holds. The brief also names the short proof and the trailer of the commit.
- On failure: A number that is no open task is refused.
- Verified by: The forge test of the brief of a task.
- Limits: The brief file that the loop writes in a slot does not hold the worker rules of the profile.

**LP-44.** The forge MUST run the full check of each batch in one check folder that keeps its build output.
<!-- id: SDD-LP-44 | tdd: TDD-6.18 -->

- Behavior: The check folder is a detached worktree of the repository at the goal tip. The forge stacks one commit for each task there, in the order of the batch.
- Verified by: The batch tests, and the test that the tidy does not list the check folder.

**LP-45.** If a result conflicts with the results before it in the batch, then the forge MUST leave that task out.
<!-- id: SDD-LP-45 | tdd: TDD-6.18 -->

- Behavior: A result that adds nothing to the goal branch is left out also. The command names each such task and its reason.
- On failure: A batch with no task left is refused.
- Verified by: A batch test with a conflict, which is not written.

**LP-46.** If a batch names more tasks than the profile permits, then the forge MUST refuse the batch.
<!-- id: SDD-LP-46 | tdd: TDD-6.18 -->

- Behavior: The default is six tasks.
- Verified by: A batch test over the limit, which is not written.

**LP-47.** If the full check fails on a batch, then the forge MUST post the failed task and the end of its log to the orchestrator.
<!-- id: SDD-LP-47 | tdd: TDD-6.18 -->

- Behavior: The rig folder keeps the full log of each check, with the number of the task as its name.
- Verified by: The batch test with a bad task in the middle.

**LP-48.** Where the profile names an install command, the forge MUST run that command in the check folder before each full check.
<!-- id: SDD-LP-48 | tdd: TDD-6.18 -->

- On failure: An install command that fails stops the batch and names its log.
- Verified by: A batch test with an install command, which is not written.

**LP-49.** If the folded goal tip differs from the tree that passed the full check, then the forge MUST report the difference and fail.
<!-- id: SDD-LP-49 | tdd: TDD-6.18 -->

- Behavior: The forge compares the two trees when each good task of the batch folded. The task folder is not compared, because a Markdown task file moves at the fold.
- Verified by: A batch test with a fold that differs, which is not written.
- Limits: With the option for no fold, the batch only runs the check.

**LP-50.** The forge MUST add one line to the batch ledger for each batch that ends with a result of the full check.
<!-- id: SDD-LP-50 | tdd: TDD-6.19 -->

- Behavior: The line holds the time, the count of stacked tasks, of folded tasks and of full checks, the result, the failed task and the seconds.
- Verified by: The batch test that reads the ledger.

**LP-51.** When a user asks for the measure, the forge MUST print the folds, the checks and the checks for each fold of the ledger.
<!-- id: SDD-LP-51 | tdd: TDD-6.19 -->

- Behavior: The output also gives the batches, the failed batches, the hours and the folds for each hour. Each call adds one line to a trend ledger in the rig folder.
- On failure: With no ledger, the command says that no batch ran.
- Verified by: The batch test that reads the checks for each fold.

**LP-52.** While a goal runs as a forge, a session stop in the repository MUST NOT start the full check.
<!-- id: SDD-LP-52 | tdd: TDD-6.17 -->

- Behavior: The forge marks the repository when a start, a dispatch or a resume passes through its door to the loop. An agent can still run the check directly.
- Observable: The stop hook says that the tree is orchestrated.
- Verified by: The forge test of the mark, and the stop hook test of an orchestrated tree.
- Limits: The forge removes the mark when a close command of the loop passes through its door, also where the goal stays open.

**LP-53.** When a goal lands on the local base, the platform MUST remove the check folder and the mark of the forge.
<!-- id: SDD-LP-53 | tdd: TDD-6.17 -->

- Behavior: This is the land at the tiers 1 and 2, the local merge, and the finish of a local project. `dev-forge end` removes only the mark, so that a stop runs the check again.
- Verified by: The forge test of the end command; a test of the check folder at the land is not written.
- Limits: The finish of a pushed goal does not remove the check folder.

**LP-54.** The distill skill MUST rank each candidate for its congruency with the specification and for its complexity.
<!-- id: SDD-LP-54 | tdd: TDD-6.10 -->

- Behavior: The congruency is one of: already satisfied, clarifies, amends, contradicts, brand new, nonsense, with the specification items that the candidate touches. The complexity is S, M, L or XL, with one line of reason.
- Behavior: Where a repository has `decisions=none` or `decisions=frozen`, an old decision record is history, and the skill ranks against the present text of the specification.
- Verified by: The text of the distill skill and its template.

**LP-55.** Each candidate MUST have one identifier that holds its date and a number of that day.
<!-- id: SDD-LP-55 | tdd: TDD-6.10 -->

- Behavior: The number continues through each batch of one day. A person gives the identifier to intake to promote the candidate.
- Verified by: The text of the distill skill.

**LP-56.** The distill skill MUST NOT change a tracked file, an issue or the specification of a repository.
<!-- id: SDD-LP-56 | tdd: TDD-6.10 -->

- Behavior: The skill adds a batch at the top of the incoming file and does not change, move or delete a block that exists, because people edit the blocks by hand. Promotion is the act of a person.
- Verified by: The text of the distill skill.

**LP-57.** A candidate MUST NOT hold a raw quote or the name of a private person.
<!-- id: SDD-LP-57 | tdd: TDD-6.10 -->

- Behavior: The raw record stays in the notes of the owner. The candidate cites its source by date and type only.
- Verified by: The text of the distill skill and of the intake skill.

**LP-58.** Where a repository has `decisions=open`, intake MUST NOT change the specification before the owner accepts the decision record.
<!-- id: SDD-LP-58 | tdd: TDD-6.11 -->

- Behavior: Intake writes each open question as a decision draft with the status proposed, and asks the owner. After the acceptance it records the status accepted and the date, and it commits the decision with the specification change and the tasks.
- Behavior: Each other step is the procedure of `decisions=none`.
- Verified by: A test reads the rule in the text of the intake skill. An agent follows this rule, and no command enforces it.
- Limits: With the GitHub tracker, the draft is a decision issue, on the word of the owner. This value is only for a repository whose own rules need the records.

**LP-59.** Each task that the intake skill makes MUST cite the specification items that govern it.
<!-- id: SDD-LP-59 | tdd: TDD-6.11 -->

- Behavior: Intake makes the tasks with the task command of the tracker, in the order of their dependencies, each small enough for one worker. The specification change is the first commit on the goal branch, and the build tasks follow it.
- Verified by: The text of the intake skill.

**LP-60.** The platform MUST give `decisions=none` to each registered repository that names no value for that field.
<!-- id: SDD-LP-60 | tdd: TDD-6.8, TDD-7.4 -->

- Behavior: With `decisions=none` the repository keeps no decision record and no amendment log. The specification is the one record of a requirement, and Git records each change of it.
- Behavior: A repository that the registry does not name gets `decisions=open`. The platform sets no rule for the decision files of a repository that it does not know.
- Behavior: A new repository from the platform template holds no decision template and no amendment log.
- Observable: `dev-loop tier` prints the value.
- On failure: A value that is not `none`, `frozen` or `open` makes the registry line invalid, and the command exits with a failure.
- Verified by: A test that reads the tier record of a line with no field, of a line with each value and of a path that no line names.

**LP-61.** Where a repository has `decisions=none`, intake MUST change the specification only after the owner accepts the change.
<!-- id: SDD-LP-61 | tdd: TDD-6.11 -->

- Behavior: Intake asks the owner each open question in the conversation and shows the exact sentence that changes. It writes no file for the question.
- Behavior: The message of the commit gives the reason of the change, the date of the acceptance and the identifier of each candidate.
- Behavior: A question that waits for a person who is not in the conversation is a task for that person.
- Verified by: A test reads the rule in the text of the intake skill. An agent follows this rule, and no command enforces it.
- Limits: A goal that the owner stated plainly is the acceptance of that goal. A choice that the goal does not make is still a question.

## TK. Task items
<!-- section: SDD-TK | sys: SYS-PL-02 -->

Decision: 0002.

**TK-01.** Where the task form of a project is JSON, the project MUST keep each task as one JSON file.
<!-- id: SDD-TK-01 | tdd: TDD-7.4 -->

- Behavior: The task form is Markdown or JSON, and Markdown is the default. The file has the number of the task as its name, in the task folder of the repository.
- Observable: `dev-loop tier` prints the task form.
- Verified by: The tests that read the tier record of a personal repository, of a company repository and of a folder with no registry line.

**TK-02.** Each JSON task MUST be valid against the one task schema of the platform.
<!-- id: SDD-TK-02 | tdd: TDD-7.2 -->

- Behavior: The schema is closed: it permits no unknown field, and it requires each necessary field and each type. An existing validator runs it, not platform code.
- Verified by: The schema test with one valid example of each kind.

**TK-03.** Each JSON task MUST have one kind from this list: code, spec, research, ops, decision, writing, data.
<!-- id: SDD-TK-03 | tdd: TDD-7.2 -->

- Verified by: The schema test finds one example of each kind and refuses an unknown kind.

**TK-04.** Each JSON task MUST name one goal.
<!-- id: SDD-TK-04 | tdd: TDD-7.2 -->

- Behavior: The goal is a short identifier of capital letters and a number, for example `G-2`.
- Verified by: The schema test of a task with no goal.
- Limits: No file of goals exists, so no check examines that the goal exists.

**TK-05.** When a commit on the base has the closing trailer of a JSON task, the loop MUST read that task as done.
<!-- id: SDD-TK-05 | tdd: TDD-6.2 -->

- Behavior: The closing trailer is `Closes: #N` with the number of the task. The trailer `Task: #N` means work on the task and closes nothing, and no trailer closes a Markdown task.
- Verified by: The loop tests of the closing trailer, of the work trailer alone and of a Markdown task.

**TK-06.** The loop MUST give a task to a worker only when the state of the task is ready.
<!-- id: SDD-TK-06 | tdd: TDD-7.1, TDD-6.5 -->

- Behavior: A ready task also needs a scope line and a dependency line; the plan lists a task without them as skipped. A draft task stays for its writer.
- Verified by: The loop tests where a draft task is not in the plan and not in the ready list.

**TK-07.** The loop MUST read the Markdown tasks and the JSON tasks of one repository in one shape.
<!-- id: SDD-TK-07 | tdd: TDD-6.1, TDD-7.1 -->

- Behavior: The shape is the one that a list of GitHub issues has: number, title, body and labels. The body of a JSON task has the same scope line and dependency line as a Markdown task, so the plan, the dispatch and the fold read both.
- Verified by: The loop test with one task of each form.

**TK-08.** When a user asks for the task view, the loop MUST write the open tasks as one HTML table with no styles.
<!-- id: SDD-TK-08 | tdd: TDD-7.3 -->

- Behavior: The table has one row for each open task: number, title, kind, goal, state, dependencies, labels, checks and file. The page has no style, no class and no script.
- Observable: `dev-loop tasks` with the verb `view` prints the page.
- Verified by: The loop test that parses the page and finds no style.

**TK-09.** A repository MUST add its own fields of a JSON task only below the extension field, with keys that start with `x-`.
<!-- id: SDD-TK-09 | tdd: TDD-7.2 -->

- Behavior: The schema refuses an unknown field at the top of a task. The extension field has the name `ext`.
- Verified by: The schema tests of an unknown field at the top and of an extension key with no prefix.

**TK-10.** When the owner makes a personal repository, the platform MUST register the repository with the JSON task form.
<!-- id: SDD-TK-10 | tdd: TDD-7.4 -->

- Behavior: `new-repo` with the options `--register` and `--personal` writes the registry line. A repository that is not personal gets the Markdown form.
- Verified by: The `new-repo` tests of the registry line.

**TK-11.** Each JSON task MUST carry a brief that states the task in prose.
<!-- id: SDD-TK-11 | tdd: TDD-7.2 -->

- Behavior: The brief has from 1 to 12000 characters, in the language in which the repository writes tasks. The title is one line of 3 to 140 characters.
- Verified by: The schema tests of a task with no brief, with an empty brief and with a long title.

**TK-12.** The platform MUST NOT change the tracker of a project that does not use JSON tasks.
<!-- id: SDD-TK-12 | tdd: TDD-7.4 -->

- Behavior: Markdown task files, GitHub issues and a repository with no tracker work as before.
- Verified by: The loop tests with Markdown task files, and the tier test of a folder with no registry line.

**TK-13.** If a JSON task breaks the task schema, then the task check MUST name the task and fail.
<!-- id: SDD-TK-13 | tdd: TDD-7.2, TDD-6.3 -->

- Behavior: The check also fails a task whose identifier differs from the number in its file name. The task commands of the loop run it, and so does the check script of a repository from the template.
- On failure: With no validator on the machine, the check stops and names the package to install.
- Verified by: The schema test with each broken shape, and the loop test of an invalid JSON task.

**TK-14.** Each JSON task MUST hold the work fields that its kind requires.
<!-- id: SDD-TK-14 | tdd: TDD-7.2 -->

- Behavior: Code and spec need a scope; research needs questions and a deliverable; ops needs a host, steps and a rollback. Decision needs a question, two options or more and the path of its record; writing needs a destination and a form; data needs a source, a target and a transform.
- Verified by: The schema test with one broken example for each kind.
- Limits: The scope of a spec task is below the docs folder.

**TK-15.** Each JSON task MUST have from one to eight acceptance checks.
<!-- id: SDD-TK-15 | tdd: TDD-7.2 -->

- Verified by: The schema tests of a task with no check and with nine checks.

**TK-16.** Each acceptance check of a JSON task MUST state how it is verified.
<!-- id: SDD-TK-16 | tdd: TDD-7.2 -->

- Behavior: The ways are test, command, eval, review, artifact and host. Each way has its own necessary fields, for example the command of a command check, or the metric, the operator and the value of an eval.
- Verified by: The schema tests of an eval check with no metric and of a command check with a field of a different way.

**TK-17.** A JSON task MUST NOT have a field or a state that marks it as done.
<!-- id: SDD-TK-17 | tdd: TDD-7.2 -->

- Behavior: The states are draft, ready, blocked and cancelled. A blocked task states its reason and what it needs, and a cancelled task states its reason.
- Verified by: The schema test of a task with the state done.

**TK-18.** If the kind of a ready JSON task is not code or spec, then the loop MUST NOT give the task to a worker.
<!-- id: SDD-TK-18 | tdd: TDD-7.1 -->

- Behavior: The task gets the label `not-for-workers` and stays for a person. The task list shows it with the word person.
- Verified by: The loop test with a ready decision task.

**TK-19.** If the assignee of a ready JSON task is a person, then the loop MUST NOT give the task to a worker.
<!-- id: SDD-TK-19 | tdd: TDD-7.1 -->

- Behavior: The task gets the label `not-for-workers` and stays for that person.
- Verified by: The loop test with a ready code task for a person.

**TK-20.** When the owner makes a personal repository, the platform MUST copy the task schema and its check into the repository.
<!-- id: SDD-TK-20 | tdd: TDD-7.4 -->

- Behavior: The copy of the schema is equal to the schema of the platform. The check script of the new repository validates each JSON task file.
- Verified by: The `new-repo` test of the schema and its check, and the test that the template schema is the platform schema.

**TK-21.** The task body that the loop makes from a JSON task MUST end with the full brief.
<!-- id: SDD-TK-21 | tdd: TDD-7.1 -->

- Behavior: The worker reads the task file, and each tool that reads the body gets the same text.
- Verified by: The loop test that the body of a task ends with the brief.

## TM. Teams
<!-- section: SDD-TM | sys: SYS-PL-08 -->

a team, called a rig, is a set of agent seats that work together on one goal of one project. the owner gives a project a team with a named shape, starts it from a team folder outside the repository, and adds or removes worker seats one worktree at a time. the seats run under OpenRig, which the platform pins and starts only through its own launcher, so that a seat starts on the word of the owner, on a permitted account, and writes no file of OpenRig into a shared repository. the area also holds the limits and the identity of a worker process, because they decide how many workers of a team run and when one stops.

The reasons:

- TM-01: The team specification lives outside the repository, so a change of the shape is no change of a product repository.
- TM-02: Each change of a shape can be read and reverted.
- TM-03: A validator that fails to start says nothing about the specification, so only its verdict counts.
- TM-04: The OpenRouter runtime takes only OpenRouter models, so a Pi seat cannot fall back to a subscription.
- TM-05: The two overseers run on two model families on purpose, so that each gives an independent reading.
- TM-06: A seat that opens is not a request to start work: the owner or the loop gives the direction.
- TM-07: The integration is examined against one version; a different version is not used until the owner examines it again.
- TM-08: Only a rig that the owner starts can run paid seats; a daemon that restores a rig on its own cannot give the approval.
- TM-09: The seats of the kernel rig start paid sessions that nobody asked for.
- TM-10: A start of an agent is a separate action that the owner requests.
- TM-11: An unhealthy, stale or ambiguous daemon is reported and not started again.
- TM-13: A live session is not cloned or given a second task without a word of the owner.
- TM-14: OpenRig writes a status line and a guidance block into the folder of a seat; in a shared repository these files show in the Git status of other people.
- TM-15: A seat in the goal worktree keeps the tracked guidance files changed, and a fold goes only into a clean worktree.
- TM-17: The guard still refuses a push, a merge and a restart; it is the one barrier that stays on these seats.
- TM-18: Two accounts on one runtime do not collide on one rig, and an account that is out of quota or not verified starts no seat.
- TM-19: OpenRig refuses the home field, and no authentication material goes into a specification or a project file.
- TM-21: Each new pane takes the environment of the terminal server; one stale proxy address there kept each new seat on a refused connection.
- TM-22: Only a worker seat writes inside a project, in its own worktree.
- TM-23: The client of OpenRig stops after five seconds while the daemon completes the start, so a blind second request can make a second seat.
- TM-24: The removal of one seat by OpenRig leaves its blocks in files that the worktree tracks.
- TM-25: Pi has no hooks, so without the guard a seat can push to a protected branch, rewrite history or restart a service.
- TM-26: Each request on a key is paid for, and a run that does not converge ends early so that the retry takes the task on a stronger model.

**TM-01.** When the owner writes a team shape, the platform MUST write the team specification into the team folder of the project.
<!-- id: SDD-TM-01 | tdd: TDD-8.1 -->

- Actor: The owner, or an agent on the word of the owner, with `rig-shape write`.
- Behavior: The shapes are `build` (a control seat and one overseer), `review` (a control seat and two overseers) and `solo` (a control seat). The team folder is outside each repository: the folder whose project marker names the repository, else a folder named for the checkout.
- Observable: The command prints the team name, the shape, the word recorded or unchanged, and the result of the schema check. `rig-shape show` prints the specification.
- Verified by: A test that writes a shape for a registered project and reads the specification, the team name and the project marker.
- Limits: A write starts no team and changes no running team. The new shape applies at the next start of the team.

**TM-02.** Each change of a team specification MUST be one commit in the Git history of the team folder.
<!-- id: SDD-TM-02 | tdd: TDD-8.1 -->

- Behavior: The team folder is a Git repository of its own that tracks the specification and the project marker. A write that changes nothing makes no commit.
- Observable: `rig-shape history` lists each change with its date, newest first.
- Verified by: A test that writes two shapes and one unchanged shape and reads two lines of history and the tracked files.

**TM-03.** If a shape request is not valid, then the platform MUST write no team specification.
<!-- id: SDD-TM-03 | tdd: TDD-8.1 -->

- Behavior: A request is not valid when it names an unknown shape, a seat that the shape does not have or an unknown runtime, or when the schema check of OpenRig rejects the result. The runtimes are Claude Code, Codex and Pi.
- On failure: The command exits with status 2 and one line that gives the valid names or the errors of the schema check.
- Verified by: Tests with an unknown shape, an unknown seat, an unknown runtime, a rejected specification and a check that cannot start.
- Limits: A schema check that cannot run gives no verdict: the write goes on and the output says that the specification is not validated, with the reason.

**TM-04.** Where a seat of a team runs on Pi, the team specification MUST name the OpenRouter model of the role of that seat.
<!-- id: SDD-TM-04 | tdd: TDD-8.1, TDD-8.2 -->

- Behavior: The roles are the control seat, the overseer, the second overseer and the worker. The model of a role comes from the model file, resolved for OpenRouter only.
- Observable: The command prints one line for each Pi seat with its model. A seat on Claude Code or Codex gets no model line.
- On failure: With no OpenRouter model for a role, the command exits with status 2 and writes no specification.
- Verified by: A test that puts each seat of the review shape on Pi and reads the three models, and a test with a model file that has no OpenRouter model.

**TM-05.** If the two overseers of a team resolve to models of one maker, then the platform MUST refuse the team specification.
<!-- id: SDD-TM-05 | tdd: TDD-8.1, TDD-8.2 -->

- Behavior: The rule applies where the two overseers run on Pi. The maker is the part of the model name that names the company of the model.
- On failure: The command exits with status 2, names the maker and the two models, and writes no specification.
- Verified by: A test with a model file whose overseer tier has two models of one maker.

**TM-06.** Each seat of a team MUST get the standing guidance of its role at its start.
<!-- id: SDD-TM-06 | tdd: TDD-8.10 -->

- Behavior: The roles are control, overseer and worker. The guidance tells the seat what it can do and that it waits for direction; it forces no model, no skill and no hook. The control seat hands over to a successor when its context is full; an overseer and a worker start with a new session.
- Observable: The instruction file in the folder of the seat holds a block with the role text.
- Verified by: A test that each agent reference of a written shape is a folder with an agent specification, and the schema check of OpenRig on each shape where OpenRig is installed.
- Limits: OpenRig writes the block and applies the lifecycle. The platform supplies the agent specifications and the text.

**TM-07.** If the pinned OpenRig runtime is absent or has a different version, then the launcher MUST start no daemon and no seat.
<!-- id: SDD-TM-07 | tdd: TDD-8.4, TDD-8.5 -->

- Behavior: The launcher is the pair of commands rig and dev-workspace. Each runs OpenRig only from the runtime folder of the platform with the pinned Node version.
- On failure: The command exits with one line that names the missing runtime or the expected version.
- Verified by: The launcher tests run against a runtime fixture that reports the pinned version; no test gives a different version.
- Limits: The rig command examines only that the runtime is present. The dev-workspace command also compares the version.

**TM-08.** When a command starts the seats of a rig, the launcher MUST ask the owner at the terminal to approve that rig.
<!-- id: SDD-TM-08 | tdd: TDD-8.4, TDD-8.6 -->

- Actor: The owner at a terminal.
- Behavior: The request goes through the approval helper of the machine, which asks for the password of the owner. A plan, a dry run and a help request ask nothing.
- On failure: With no terminal or no valid rig name, the launcher asks nothing and prints that the seats of the rig get no paid session.
- Verified by: Tests of the rig name, of the start and plan arguments, of a call with no terminal and of the helper call at a terminal.
- Limits: The seat launcher of the machine refuses the paid session of a seat whose rig has no approval. That launcher is not part of this repository.

**TM-09.** The launcher MUST NOT start the built-in kernel rig of OpenRig on its own.
<!-- id: SDD-TM-09 | tdd: TDD-8.4, TDD-8.5 -->

- Behavior: Each daemon that the launcher starts has the kernel turned off. The shared terminal of a kernel is attached only on request and only where one exists.
- Verified by: A test that the two launcher commands set the kernel switch, and a test that an open with a stopped daemon starts the daemon with no kernel.

**TM-10.** The open action of the launcher MUST NOT start a seat or restore a rig.
<!-- id: SDD-TM-10 | tdd: TDD-8.5 -->

- Actor: The owner, with `dev-workspace` and no other argument.
- Behavior: The action opens the dashboard of the rigs. It starts the daemon when the daemon is stopped.
- On failure: An open with a runtime or a folder argument is refused.
- Verified by: Tests that an open calls only the version, the daemon status, the daemon start where necessary, and the dashboard.

**TM-11.** If the state of the daemon is unhealthy or not known, then the launcher MUST NOT start a second daemon.
<!-- id: SDD-TM-11 | tdd: TDD-8.5 -->

- Behavior: The launcher starts the daemon only when the status says that the daemon is stopped. A plan request does not start a stopped daemon.
- On failure: The command exits with status 2 and prints the status text.
- Verified by: Tests with an unhealthy status, an unknown status and a plan with a stopped daemon.

**TM-12.** If the plan of a seat start fails, then the launcher MUST NOT start that seat.
<!-- id: SDD-TM-12 | tdd: TDD-8.6 -->

- Behavior: The plan action of `dev-workspace` runs only the plan of the rig. The start action runs the same plan first and then the start, and it leaves each permission question of the rig to the owner.
- On failure: The command exits with a failure and makes no start call.
- Verified by: A test where the plan fails and no start call follows.

**TM-13.** When a rig of the requested name exists, the launcher MUST start that rig again in place of a new rig.
<!-- id: SDD-TM-13 | tdd: TDD-8.6 -->

- Behavior: The name is fixed by the runtime, by the runtime and the account, or by the project for a control rig. The session of a reused rig keeps its first folder.
- On failure: An archived rig of that name, two rigs of that name and an inventory that is cut short each stop the command with status 2.
- Verified by: Tests with an existing rig, an archived rig and an existing rig for an account.

**TM-14.** The launcher MUST NOT start a new seat in a checkout of tier 3 or higher.
<!-- id: SDD-TM-14 | tdd: TDD-8.6, TDD-8.9 -->

- Behavior: A repository that is not registered counts as tier 3. The rule holds for a control seat and for a worker seat. A plan in such a checkout is permitted.
- On failure: The command exits with status 2 and says that OpenRig writes managed context into the folder.
- Verified by: Tests that a start and a worker seat in an unregistered checkout are refused and that a plan runs.
- Limits: A folder that is no Git checkout is not refused by this rule.

**TM-15.** The launcher MUST NOT start the control rig of a project in a folder inside a Git checkout.
<!-- id: SDD-TM-15 | tdd: TDD-8.6 -->

- Behavior: The control seat and each overseer work from the team folder and read the repository with Git commands.
- On failure: The command exits with status 2 and names the team folder rule.
- Verified by: A test that starts the control rig in a plain folder and is refused in a checkout.
- Limits: A team folder that holds its own team specification is accepted, although it is a Git repository of its own.

**TM-16.** Where the team folder holds a team specification, the launcher MUST start the team from that specification.
<!-- id: SDD-TM-16 | tdd: TDD-8.6 -->

- Actor: The owner, with `dev-workspace start engineer` and the rig name of the project.
- Behavior: The members keep the folders that the specification gives them. With no specification in the folder, the launcher starts the standard control rig under the name of the project.
- On failure: A specification whose name differs from the requested rig name stops the command with status 2.
- Verified by: Tests with a team folder that has a specification, with a different name in it, and with no specification.
- Limits: With no rig name, the launcher starts the standard control rig and does not read the team folder.

**TM-17.** Where a new Claude or Codex seat starts in a personal checkout, the launcher MUST start that seat with permission prompts off.
<!-- id: SDD-TM-17 | tdd: TDD-8.6 -->

- Behavior: A personal checkout has tier 1 or tier 2. The policy applies to that seat only, and the launcher prints one notice.
- Verified by: Tests of both runtimes in a personal checkout, and of each case that keeps its prompts.
- Limits: A folder that is no Git checkout, a professional checkout, a reused rig and a control rig keep their prompts.

**TM-18.** Where the owner names an account for a seat, the launcher MUST start the seat only if the account resolver accepts that account.
<!-- id: SDD-TM-18 | tdd: TDD-8.7 -->

- Behavior: The launcher asks the resolver of the account registry before it reads the rig inventory or writes a file; the resolver uses the named account or refuses it (AC-07). The rig of an account has a name of its own, `development-<runtime>-<account>`.
- On failure: The command exits with status 2 and prints the reason of the resolver, for example that the account is not signed in or is exhausted. A configuration file of the folder that overrides the authentication or the provider also stops the command, with the name of the file (AC-22).
- Verified by: Tests with an account that is not signed in, an exhausted account, a folder whose settings override the provider, a wrong provider, an accepted account and a reused rig of an account.
- Limits: An account of a different provider than the runtime is refused as an argument fault. With no account, the seat uses the default home of its client.

**TM-19.** A team specification that the platform writes MUST NOT name a credential or the home folder of an account.
<!-- id: SDD-TM-19 | tdd: TDD-8.6, TDD-8.7 -->

- Behavior: The account reaches the seat through the seat launcher of the machine at the start of the seat. A generated specification is a private file in the state folder of the platform, outside each repository.
- Verified by: Tests that read each generated specification and each worker fragment and find no home field.

**TM-20.** When a seat starts on a named account, the launcher MUST record the account of that seat for the usage report.
<!-- id: SDD-TM-20 | tdd: TDD-8.7, TDD-8.9 -->

- Behavior: The record is one entry for each seat session. A Pi worker seat is recorded on the OpenRouter key.
- Observable: The usage command adds a newer quota reading of a Claude seat to the reading of that account (AC-61).
- On failure: When the record cannot be written, the launcher prints one line and the seat stays.
- Verified by: Tests that add a worker seat with an account and a Pi worker seat and read the record.
- Limits: The usage command adds no reading of a seat on a different client.

**TM-21.** When the launcher starts a seat, the launcher MUST first remove each provider override from the environment of the terminal server.
<!-- id: SDD-TM-21 | tdd: TDD-8.8 -->

- Behavior: A provider override is a variable of the terminal server that points a client to a different provider or address. The launcher prints the names that it removed.
- Verified by: A test with a terminal server fixture that holds two overrides and two other variables, and a test of a plan.
- Limits: A plan removes nothing. A pane that runs keeps its environment.

**TM-22.** When the owner adds a worker seat, the launcher MUST put one seat for that worktree in the workers pod of the running rig.
<!-- id: SDD-TM-22 | tdd: TDD-8.9 -->

- Actor: The owner or the loop, with `dev-workspace add-worker`.
- Behavior: The seat works in the worktree and takes its name from the task number of the worktree. One worktree has one seat. A worktree on a branch gives the task number in its folder name, and a slot of the loop gives it in its task mark.
- Observable: The command prints the seat, the branch or the slot, the account and the command that attaches the terminal of the seat.
- On failure: A folder that is not a linked worktree on a branch or a slot with a task, a rig that is not one running rig and a second seat for the worktree each stop the command with status 2.
- Verified by: Tests that add a seat from a worktree and from a slot, add it a second time, and try the checkout itself, a free slot, a detached worktree outside the slots and a stopped rig.
- Limits: The launcher accepts a detached worktree only when it is a slot of the repository that holds a task mark of the loop.

**TM-23.** If the rig does not show a new worker seat in the wait time, then the launcher MUST NOT repeat the add request.
<!-- id: SDD-TM-23 | tdd: TDD-8.9 -->

- Behavior: The launcher reads the result of an add request from the rig and not from the exit status of the request.
- On failure: The command exits with status 1 and tells the owner to examine the rig before a new try.
- Verified by: A test where the request fails but the seat shows, and a test where the seat does not show and one request is recorded.

**TM-24.** When the owner removes a worker seat, the launcher MUST remove each managed block of OpenRig from the guidance files of the worktree.
<!-- id: SDD-TM-24 | tdd: TDD-8.9 -->

- Actor: The owner or the loop, with the remove-worker action of the launcher.
- Behavior: The launcher removes the seat from the rig where the seat exists. A guidance file that holds only managed blocks is deleted.
- Observable: The command prints the files that it restored, and the Git status of the tracked files of the worktree is empty.
- Verified by: A test that adds a seat, writes managed blocks into two guidance files, removes the seat and reads the files and the status.

**TM-25.** Each Pi seat and each Pi worker of a team MUST start with the platform guard and the advice tool loaded.
<!-- id: SDD-TM-25 | tdd: TDD-8.2, TDD-8.3, TDD-8.9 -->

- Behavior: The platform writes the two extensions into the settings of the agent folder of the seat before the seat starts, and keeps each other setting. A headless worker also loads its limits. Where the environment of the launcher names a Pi model list, each seat and worker gets a copy.
- Verified by: Tests that read the extension list of a Pi worker seat and of a headless Pi worker of the loop, and the offline check of the extensions.
- Limits: A Pi worker seat takes no account: it runs on the key that the daemon of its rig holds.

**TM-26.** If a Pi worker reaches one of its limits, then the worker MUST stop with a blocked note in its worktree.
<!-- id: SDD-TM-26 | tdd: TDD-8.3 -->

- Behavior: The limits are the cost in dollars, the turns, the turn by which the worktree shows a first change, and the billed tokens. The token limit applies only while the provider reports no cost.
- Observable: The note gives the limit and the value. The worker runs no more tool calls and Pi ends.
- Verified by: The offline check of the extensions, with a cost over the cap, no change by the first-change turn and a turn cap.
- Limits: The defaults are 2 dollars, 60 turns, a first change by turn 20 and 20,000,000 tokens. The loop can set other values.

**TM-27.** The loop MUST count as a running worker only a live supervisor process of the same repository.
<!-- id: SDD-TM-27 | tdd: TDD-8.11 -->

- Behavior: A process record alone is no proof. The process is alive, is the supervisor of that task, and runs in a checkout of the repository. A worker with an exit record is not counted.
- Observable: `dev-loop status` lists each counted worker with its task and its process number, and the worker cap uses the count.
- Verified by: Tests with a live supervisor, a completed one, a process of a different program, a stale record, a different repository and a different checkout.
- Limits: A live supervisor that has no identity receipt is counted.

**TM-28.** If the identity receipt of a live supervisor differs from its process, then the loop MUST NOT dispatch a worker.
<!-- id: SDD-TM-28 | tdd: TDD-8.11 -->

- Behavior: The supervisor writes the receipt before the work starts.
- On failure: The status, the dispatch verbs and the resume verb of the loop exit with a failure and say that the identity changed. No dispatch lock stays.
- Verified by: A test that changes the receipt of a live supervisor and runs each of the four verbs.

**TM-29.** The supervisor MUST mark each worker process as a loop worker in the environment of that process.
<!-- id: SDD-TM-29 | tdd: TDD-8.11 -->

- Behavior: The session length limit of the platform reads the mark and applies to the worker.
- Verified by: A test that starts a command through the supervisor and reads the environment of that command.

<!-- retired: SDD-TM-30 -->

## AC. Accounts
<!-- section: SDD-AC | sys: SYS-PL-05 -->

This area decides which account a new agent session uses, and it keeps the credential of each account away from the agents. The owner signs in an account one time, from the Mac or at the server, and each agent user then gets that credential from the launcher when a session starts. One registry lists the accounts, one resolver makes the choice, one credential store that only root can read holds the credentials, and one usage record holds what each account has left. The area exists because a session is partly untrusted: an agent can change each file that its user can write, so no credential stays in a home folder or a project, and nothing that a session writes goes back to the store. The area also protects the money of the owner: a subscription is not replaced by metered API cost unless the owner names that option and confirms it for one launch. The tools of the owner and of the roles get their service keys by name from the same store.

The reasons:

- AC-01: A new account or a new API key provider is one entry, and no agent signs in for itself.
- AC-02: Each user of the machine can read the registry; the credentials stay in the store that only root reads.
- AC-03: Each later sign-in is compared with the identity that the owner confirmed at the first sign-in.
- AC-04: Work for a client uses only the accounts of that client, and personal work does not use them.
- AC-06: The owner decided that each model account can serve each place when he chooses it by name; code of a client is pushed only with the login of that client.
- AC-07: A named account is a decision of the owner; a silent change of account can spend a different plan.
- AC-08: Quota observations are snapshots of a shared pool, so a new session goes where the most capacity is observed.
- AC-09: A missing reading says nothing about the account, so it does not stop a launch.
- AC-12: What a session costs depends on the account and on the harness that it runs through.
- AC-13: Subscription access is not replaced by API billing without a decision of the owner.
- AC-15: Metered API cost starts only after a yes of the owner for that one launch.
- AC-17: The owner sees a change of account when it occurs.
- AC-18: The resolver of the launcher runs as root and writes to the chat, so a planted file cannot bring a secret there.
- AC-19: A saved name is not a fallback: it holds each later launch of that user until the owner clears it.
- AC-20: A launch with no name could use an account that the owner did not select.
- AC-23: The launcher hands the credential to the session, so no login is kept in a home folder.
- AC-25: No process that runs as the owner can sign an account in or out by itself.
- AC-36: Only the word of the owner says whose credential it is, and the status does not show more than that.
- AC-51: Each process that runs as the owner can ask, so each use is on record.
- AC-52: A service key is for a tool, not for a model session.
- AC-53: An agent gets a key only where its work needs it; the launcher lists the keys by name.
- AC-54: The tools of the owner run outside a launch and have no launcher that hands them the key.
- AC-55: An agent does not use the rights of the owner to get a key.
- AC-57: No reading says nothing about the account.
- AC-58: The percentage of a window that ended says nothing about now.
- AC-59: The agents can write the usage folder, so a reading is not trusted.
- AC-60: Root reads and writes in a folder that the agents can write.
- AC-61: A seat that OpenRig starts runs the status line of OpenRig, so its readings come by a second path.

**AC-01.** The account registry MUST hold one entry for each account with its name, provider, kind and clients.
<!-- id: SDD-AC-01 | tdd: TDD-9.1 -->

- Behavior: An entry can also hold the default mark, the expected identity, the quota source, the billing of a client, the bound folders and a service name. The kinds are subscription, API key, OAuth and local.
- Observable: `ai-account list` prints one line for each entry.
- On failure: A registry with an unknown kind, an unknown client, one name two times, two defaults for one provider or an unsupported version is refused. The command prints the reason and exits with 2.
- Verified by: A test that loads the template, a test that adds one entry and resolves to it, and a test that loads a bound entry with wrong folders.
- Limits: While the machine has no registry of its own, the commands read the template of the repository.

**AC-02.** The account registry MUST NOT hold a credential.
<!-- id: SDD-AC-02 | tdd: TDD-9.1 -->

- Behavior: The load refuses an entry that has a field whose name holds a word such as token, secret, password, refresh or access.
- On failure: The command prints the name of the account and of the field and exits with 2.
- Verified by: A test that loads a registry with a field named as a refresh token.

**AC-03.** When the template is merged into the registry of the machine, the merge MUST keep each identity recorded at sign-in.
<!-- id: SDD-AC-03 | tdd: TDD-9.1 -->

- Behavior: The template decides which accounts exist and how each one is described. An account that had an older name keeps its recorded identity below the new name.
- Verified by: A test that merges the template over a copy with a recorded identity, and a test that merges over a copy with no billing.
- Limits: The installer that starts the merge is not a part of this repository.

**AC-04.** While the work folder is bound to accounts, the resolver MUST choose only among those accounts for a launch that names no account.
<!-- id: SDD-AC-04 | tdd: TDD-9.2 -->

- Behavior: A folder is bound when it is one of the folders of an entry or is inside one, by its real path. A choice by folder is not a rotation.
- On failure: With no eligible bound account the launch is refused. The resolver does not use an account that is not bound.
- Verified by: A test that resolves in a bound folder with and without a verified credential of the bound account.

**AC-05.** The resolver MUST NOT choose an account that is bound to folders for a launch outside those folders that names no account.
<!-- id: SDD-AC-05 | tdd: TDD-9.2 -->

- Behavior: A bound account is not a default account. A registry that marks a bound account as default, or gives it a folder that is not absolute, is refused.
- Verified by: A test that resolves outside the bound folder, and a test that loads the wrong entries.

**AC-06.** Where a launch names a model account, the resolver MUST accept that account in each folder.
<!-- id: SDD-AC-06 | tdd: TDD-9.2 -->

- Behavior: Model accounts are the accounts of the model providers and of the local model. A named GitHub login stays bound: outside its folders, and inside the folders of a different login, the launch is refused.
- Verified by: A test that names a bound model account outside its folder and an unbound one inside it, and a test that names each GitHub login in the folder of the other.

**AC-07.** When a launch names an account, the resolver MUST use that account or refuse the launch with the reason.
<!-- id: SDD-AC-07 | tdd: TDD-9.3, TDD-9.5, TDD-8.7 -->

- Behavior: The name comes from the launch (`--account`) or from the selection of the owner. The resolver does not replace a named account with a different account.
- Observable: `ai-account resolve` prints the account. A refusal goes to the error output with exit 2.
- On failure: An unknown name, an account that does not serve the client, an account with no verified credential and an exhausted account each give a refusal that names the state.
- Verified by: A test that names an account with a credential, with no credential and with no quota left.

**AC-08.** When a launch names no account, the resolver MUST choose the eligible account with the most remaining observed quota.
<!-- id: SDD-AC-08 | tdd: TDD-9.3 -->

- Behavior: With equal remainders the default account of the provider goes first. The choice applies to a new session; a running session keeps its account.
- Observable: The result gives the account, the reason, the usage line and each candidate with its state.
- Verified by: A test with two accounts and two usage readings.

**AC-09.** The resolver MUST rank an account with unknown quota below each eligible account with a known remainder.
<!-- id: SDD-AC-09 | tdd: TDD-9.3, TDD-9.18 -->

- Behavior: Unknown quota is not zero and is not exhausted. Where no eligible account has a known remainder, the default account goes first.
- Verified by: A test with one known and one unknown account, a test with no reading, and a test with a window whose reset time passed.

**AC-10.** The resolver MUST choose only an account that has a verified credential and is not exhausted.
<!-- id: SDD-AC-10 | tdd: TDD-9.3 -->

- Behavior: An account is exhausted when its remaining observed quota is zero. The local model needs no credential.
- Verified by: A test with a credential that is not verified, a test with a full window, and a test of the local model.

**AC-11.** If no account is eligible, then the resolver MUST refuse the launch and name the state of each candidate.
<!-- id: SDD-AC-11 | tdd: TDD-9.3, TDD-9.4 -->

- Behavior: Where the caller names who launches, the same line goes to the chat and to the rotation record.
- Observable: The message holds each account with its state and its usage line.
- Verified by: A test with no credential in the store.

**AC-12.** Each pair of account and client MUST have one billing: subscription, metered, free or none.
<!-- id: SDD-AC-12 | tdd: TDD-9.3 -->

- Behavior: The billing comes from the kind of the account unless the entry names a different billing for that client. A subscription account that runs through a second harness can be metered.
- Observable: `ai-account options` and the status table show the billing of each pair.
- Verified by: A test that reads the billing of each pair, and a test of the status rows of the service keys.

**AC-13.** When a launch names no account, the resolver MUST choose only among accounts with the billing of the default account.
<!-- id: SDD-AC-13 | tdd: TDD-9.3 -->

- Behavior: The resolver does not replace a subscription with an API key.
- Verified by: A test with an exhausted subscription and a ready API key, and a test with two subscriptions.

**AC-14.** The resolver MUST NOT choose a metered option for a launch that names no account.
<!-- id: SDD-AC-14 | tdd: TDD-9.3 -->

- Behavior: Where each option of a provider and client is metered, the launch is refused. The message tells the owner to name the account and to confirm it.
- Verified by: A test with a metered harness on a subscription account, with and without the confirmation.

**AC-15.** If a launch names a metered option with no confirmation for that launch, then the resolver MUST refuse the launch.
<!-- id: SDD-AC-15 | tdd: TDD-9.3 -->

- Behavior: The confirmation is the option `--metered-ok`. It applies to one launch.
- Verified by: A test that names a metered option without and with the confirmation.

**AC-16.** When the chosen account differs from the last account for that provider and client, the resolver MUST write the change to the rotation record.
<!-- id: SDD-AC-16 | tdd: TDD-9.4 -->

- Behavior: The line holds the time, the provider, the client, the two accounts and the reason. A choice of a bound account is not recorded.
- Verified by: A test that exhausts the last account and resolves again, and a test of the place of the two records.
- Limits: Only the resolver that runs as root can write the record and the last choice. A resolve of a user reads them and records nothing.

**AC-17.** Where the caller names who launches, the resolver MUST write each change of account to the chat.
<!-- id: SDD-AC-17 | tdd: TDD-9.4 -->

- Behavior: The chat line names who launches, the provider, the client, the two accounts and the state of the earlier account.
- Verified by: A test that reads the chat after a change of account.

**AC-18.** The resolver MUST repeat from its records only a name that the account registry holds.
<!-- id: SDD-AC-18 | tdd: TDD-9.4 -->

- Behavior: A last choice that is not an account name of the registry is ignored. From a usage reading, only a plain window name is repeated.
- Verified by: A test that plants a link to a secret as the last choice, and a test with a window name and an account name that hold other text.

**AC-19.** When the owner selects an account for a provider, each later launch of that user MUST use that account or fail.
<!-- id: SDD-AC-19 | tdd: TDD-9.5 -->

- Behavior: `ai-account select` saves one name for each provider, and `--clear` removes one name or all names. An account that one launch names wins over the selection.
- Observable: `ai-account selected` prints the account and the reason.
- On failure: A selection of an account with no verified credential is refused and nothing is saved.
- Verified by: Tests that select an account with less quota, exhaust it, name a different account for one launch, clear the selection and select an account with no credential.

**AC-20.** If the selection record is unreadable, then the account command MUST refuse the launch.
<!-- id: SDD-AC-20 | tdd: TDD-9.5 -->

- On failure: The command prints the reason and exits with 2.
- Verified by: A test that writes text that is no JSON into the selection record.

**AC-21.** If the environment of a launch holds a provider setting that overrides the account, then the account command MUST refuse to start the session.
<!-- id: SDD-AC-21 | tdd: TDD-9.6 -->

- Behavior: The settings are the key, token and address variables of the providers. The message names the variables and gives no value.
- Observable: `ai-account run` exits with 2.
- Verified by: A test that sets one such variable and starts the run command.

**AC-22.** If a configuration file of the project or of the client overrides authentication or the provider, then the launch MUST be refused.
<!-- id: SDD-AC-22 | tdd: TDD-9.6, TDD-8.7 -->

- Behavior: The check reads the client settings files of the work folder and of each folder above it. The refusal names the file and gives no value.
- Observable: `ai-account run` and `dev-workspace --account` exit with 2 and print the name of the file.
- Verified by: A test that starts the run command, and a test that starts a seat, each in a folder with a settings file that sets a provider address.

**AC-23.** When the owner starts a session with the account command, the command MUST give the launcher the account and the model as names only.
<!-- id: SDD-AC-23 | tdd: TDD-9.6 -->

- Behavior: `ai-account run` starts Claude Code or Codex through the launcher. With no model named, it takes the model for judgment and prose from the model file.
- On failure: With no model in the model file, or with a client that is not Claude Code or Codex, the command exits with 2.
- Verified by: A test that starts the run command with a stand-in launcher and reads its arguments and environment.

**AC-25.** A change of the credential store MUST require the password of the owner.
<!-- id: SDD-AC-25 | tdd: TDD-9.7 -->

- Behavior: Sign-in and sign-out run only through the entry point that asks for the password. The check and the usage reading need no password.
- On failure: A sign-in or sign-out request to the entry point with no password is refused and the store does not change.
- Verified by: A test that sends both requests to each entry point as root, and a test that reads the commands that the sign-in command starts.

**AC-36.** Where the provider cannot name the identity of a working credential, the status MUST show the credential as not checked.
<!-- id: SDD-AC-36 | tdd: TDD-9.7 -->

- Behavior: The owner types the address that he signed in with. The credential is usable, and the status says that only the owner confirmed it.
- Verified by: A test with a token that works and names no account, and tests of the address prompt.

**AC-37.** The status command MUST show for each account and client the identity, the verified state, the billing and the quota with its age.
<!-- id: SDD-AC-37 | tdd: TDD-9.7 -->

- Behavior: `ai-account status` prints the table, and `--json` gives the rows. The sign-in command `ol-login`, which is not in this copy, prints the same table and signs in the row that the owner chooses.
- Verified by: A test that reads the table for a verified account with a usage reading.

**AC-51.** Each credential that the credential helper gives to a command of the owner MUST have one journal line with no credential in it.
<!-- id: SDD-AC-51 | tdd: TDD-9.17 -->

- Behavior: The line names the account, the user and the command that asked. A password in an address of that command is replaced by a mark.
- Verified by: Tests that read the journal line of a GitHub answer and of a service key, and a test of a command with a password in an address.

**AC-52.** A service key MUST NOT be offered as an account for a harness.
<!-- id: SDD-AC-52 | tdd: TDD-9.17 -->

- Behavior: A service key is an API key entry with no client and a service name. The resolver refuses it and the launch options do not list it.
- Verified by: A test that looks for each service in the launch options and resolves each one.

**AC-53.** When a tool asks for a secret by name, the platform MUST give the value that the launcher handed to that process.
<!-- id: SDD-AC-53 | tdd: TDD-9.17 -->

- Behavior: A Python reader and a shell reader read the credentials folder of the process. A missing secret gives no value, and the caller says which name is missing.
- On failure: A name that is not a plain secret name is refused.
- Verified by: A test that reads a name inside the folder, a name outside it and a name with a path in it.

**AC-54.** Where a service key has the owner read mark, a tool of the owner MUST get the key through a pipe outside a launch.
<!-- id: SDD-AC-54 | tdd: TDD-9.17 -->

- Behavior: The tool asks the credential helper with no password. A key with no mark is refused, and the helper prints no key to a terminal.
- Verified by: A test that asks for a marked key through a pipe, for a key with no mark, and with a terminal as output.

**AC-55.** If the caller is not in the group of the owner, then the secret reader MUST NOT ask the credential helper for a key.
<!-- id: SDD-AC-55 | tdd: TDD-9.17 -->

- Behavior: The reader then returns no value. A switch in the environment turns the owner read off for tests.
- Verified by: A test that reads with no group and with the switch, and looks for a started command.

**AC-57.** The usage view MUST show an account with no reading as unknown, not as zero.
<!-- id: SDD-AC-57 | tdd: TDD-9.18, TDD-9.20 -->

- Observable: The row has the state quota unknown, no remaining percent and the summary unknown.
- Verified by: A test of an account with a credential and no reading.

**AC-58.** The remaining quota of an account MUST be the percent left in its tightest window whose reset time is in the future.
<!-- id: SDD-AC-58 | tdd: TDD-9.18 -->

- Behavior: A window whose reset time passed is dropped. With no window, the credits count as the share of the limit that is left.
- Verified by: A test with a window past its reset, a test with a full and a part-used window, and a test with credits.

**AC-59.** If a usage reading holds a value that is not a plain number in range, then the platform MUST read that part as unknown.
<!-- id: SDD-AC-59 | tdd: TDD-9.18 -->

- Behavior: A window with such a value is dropped, and a capture time in the future is left out. The commands do not stop on such a reading.
- Verified by: A test with readings that hold text, very large numbers, a deep structure and a future time.

**AC-60.** The platform MUST read a usage reading only from an ordinary file with one name and a limited size.
<!-- id: SDD-AC-60 | tdd: TDD-9.18 -->

- Behavior: A link, a pipe, a device, a file with a second name and a large file each read as no reading, and the reader does not wait. A reading that root writes replaces the name and follows no link.
- Verified by: Tests that plant a link, a pipe, a second name and a large file in the usage folder.

**AC-61.** When the usage command runs, a newer reading of an OpenRig Claude seat MUST join the reading of the account of that seat.
<!-- id: SDD-AC-61 | tdd: TDD-9.20 -->

- Behavior: The seat launcher records the account of each seat. A seat reading older than the record changes nothing, and a Codex seat gives no reading.
- Verified by: A test with one Claude seat and one Codex seat, then with a newer record.

**AC-62.** The usage view MUST give each account one state: unverified, quota unknown, exhausted or ready.
<!-- id: SDD-AC-62 | tdd: TDD-9.20 -->

- Behavior: `ai-usage` prints a table with the last five lines of the rotation record, and `--json` gives the rows with the windows, the age and the source of each reading. An account with no quota source is left out unless it is a subscription.
- Verified by: A test with a full and a part-used account, and a test of the table with one line in the rotation record.

## SE. Sessions
<!-- section: SDD-SE | sys: SYS-PL-06 -->

The owner and the agents work in more than one client (Claude Code, Codex, Pi) and in more than one home, and each client keeps its sessions in its own store and its own format. This area gives one index of all those sessions, one title format on each client, a readable text of each transcript, and a plan to resume a session in its native client. The index reads the native stores and does not write them, because the native client stays the authority for its history and its resume identity. A title has fixed fields, so that a person or an agent can find a session by its project, its purpose, who started it, its client, its model and its date; hooks add the fields, and a model writes only the middle part. A conversation joins the native sessions of more than one client under one stable identifier and one scope, so that a change of window, account or client does not change what the work is about. The area also holds the guard that limits the length of an agent session, and the delivery of the shared session entry text.

The reasons:

- SE-01: One index makes the sessions of different clients understandable together and does not replace their native formats.
- SE-02: Files and native tools are the authority for their sessions.
- SE-04: The same native identifier in two homes never collides.
- SE-05: The change time of a file is never proof that a session runs; only native evidence changes the status.
- SE-06: An absent source is not evidence that its records were deleted.
- SE-08: A second tool searches the readable text; the search of the index stays on the facts of a session.
- SE-09: The index is not a native rename interface; only the owning client renames its conversation.
- SE-10: A scan of the native stores cannot make this data again, because the owner or an agent wrote it.
- SE-12: A handoff gives the goal, the progress and the next action to the session that continues the work.
- SE-14: The readable text holds message content, so the folder is for the owner; the group can read so that a read grant of the owner by an access list has an effect.
- SE-15: Only an agent can read its own home, so the agent exports and the owner files the result.
- SE-16: One index holds the sessions of each home, and no user reads the home of a different user.
- SE-17: The launcher records who started a session and how; these facts are in the index and not in a file name.
- SE-20: The owner asked to read sessions as text and to search them.
- SE-23: A resume uses the recorded place and the recorded profile, not the folder or the account of the present terminal.
- SE-25: A resumed session keeps its original profile.
- SE-26: A login route of a terminal that is not related does not change a recovered session with no sign.
- SE-27: The launcher sets the limits of an agent, so a resume does not go around it.
- SE-28: A resume that is not supported is never reported as a success.
- SE-29: A conversation continues across windows, accounts and clients, so its identity is not a terminal, an account or a project path.
- SE-30: The personal agent is independent of projects, the engineering agent works in exactly one project or formation, and the systems agent has an explicit operational scope.
- SE-31: One home for each conversation; the views by project and by agent are references and not copies of transcripts.
- SE-32: A conversation can hold native sessions of more than one client, and their histories stay where the clients keep them.
- SE-34: An association needs evidence; a match by title, folder name or time is only a candidate.
- SE-35: One contract says what a session is called on each client, so that a person and an agent find a session by its fields.
- SE-36: One implementation formats the title for each launcher and each hook.
- SE-37: The launcher knows who started a session and how, so a hook does not guess these fields.
- SE-39: The redaction is a second barrier; a writer of a title does not put a secret, an account identifier or customer data in it.
- SE-40: A guess is only the first evidence; chat and misc are for a session where no evidence points to a different value.
- SE-41: A launcher uses the short title as the name of a terminal window.
- SE-42: Each agent names its own session, and the hooks add the context fields.
- SE-43: A title that the owner or a model set stays.
- SE-44: A model changes only the middle part; it never changes host, project, who, client, model, type or date.
- SE-45: A failure to name a session never stops a turn.
- SE-46: Injected client text never describes the task.
- SE-47: A spawned session names its worker and its parent, and it has no user prompt to take a description from.
- SE-48: The rename call is the supported path that the client itself uses.
- SE-50: The app shows the title that the tool sent, so a title with only the middle part shows no fields.
- SE-51: The hook can only guess from the first prompt, and the model knows the task; the limit prevents a loop when a model cannot rename.
- SE-52: The app keeps its own copy of a title and can write it over a rename.
- SE-61: A machine with no release of the platform gets the same session names.
- SE-62: The command line client, the desktop app and the editor extensions read the same settings of a home.
- SE-65: Local agents on a client machine follow the same rules as on the platform machine.
- SE-68: The limit is for the agents and the loop workers (decision of 2026-10-05), and an agent cannot claim the name of the owner.
- SE-69: The entry text separates the purpose of a session from its client and its account.
- SE-70: The start guidance is in the context of the session, not only available to find.

**SE-01.** The session index MUST hold one record for each session that a scan finds in a native store of a supported client.
<!-- id: SDD-SE-01 | tdd: TDD-10.2, TDD-10.3 -->

- Actor: The owner, with the scan command of the index.
- Behavior: The supported clients are Claude Code, Codex and Pi. A record holds the native identifier, the working directory, the title, the branch, the time of the last change and the locators of the native files.
- Observable: `ai-session list --json` shows the records and the last state of each source.
- Verified by: A scan of temporary native stores of each client, and a second scan after the owner deleted the records.
- Limits: One scan reads at most 100000 records from one source; the limit option changes this number.

**SE-02.** The session index MUST NOT write to a native store of a client.
<!-- id: SDD-SE-02 | tdd: TDD-10.2 | sys: SYS-PL-13 -->

- Behavior: A scan, a title, a handoff and a conversation link change only the state of the index.
- Observable: The bytes of each native store are the same before and after each command of the index.
- Verified by: A digest of the native folders before and after a scan, a title write and a bind.

**SE-03.** Each adapter MUST NOT copy a message body, a prompt or the content of a request into a session record.
<!-- id: SDD-SE-03 | tdd: TDD-10.2 -->

- Behavior: An adapter copies only single values; a nested object in a title field or a path field becomes empty. The same rule applies to a conversation record and to its references.
- Verified by: A search for planted body text in each record file after a scan of Codex and Claude Code stores. No test covers the Pi limit.
- Limits: The record of a Pi session also holds the first 200 characters of its first prompt, with credentials masked; the transcript reader adds them as a derived title.

**SE-04.** A session identifier MUST name the client and a digest of the native store and the native identifier.
<!-- id: SDD-SE-04 | tdd: TDD-10.1 -->

- Observable: One native identifier in two native homes gives two records.
- On failure: A command refuses an identifier that does not have this form, with exit status 1.
- Verified by: A fixture with one native identifier in the default Codex home and in an account home, and a show of a path as an identifier.

**SE-05.** When a complete scan of a source does not find a recorded session, the session index MUST mark that session as stale.
<!-- id: SDD-SE-05 | tdd: TDD-10.3 -->

- Behavior: A Claude Code record whose index names an absent transcript is also stale. The status is `unknown` where no native evidence says more.
- Observable: The status field of the record in `ai-session list`.
- Verified by: Scans with a removed session and with an absent transcript.

**SE-06.** If a scan cannot read a source in full, then the session index MUST NOT mark a session of that source as stale.
<!-- id: SDD-SE-06 | tdd: TDD-10.2, TDD-10.3 -->

- Behavior: The scan report gives each source one state: `ok`, `truncated`, `error` or `unavailable`. A native store that an earlier scan found and that is absent now is `unavailable`.
- On failure: One source with an error does not stop the scan of the other sources.
- Verified by: Scans with a source that raises an error, with a limit of one record and with a moved native home.

**SE-07.** When the caller gives no limit, the session list MUST show at most 20 sessions.
<!-- id: SDD-SE-07 | tdd: TDD-10.4 -->

- Behavior: The newest session is first, and `--runtime` and `--owner` select a part of the list. `--limit 0` asks for all matches.
- Observable: The JSON output gives the total and a flag for more matches; the text output prints one line with the two counts.
- On failure: A negative limit is refused.
- Verified by: A list of 32 sessions with no limit, with limit 0 and with a search. No test covers the rank option.
- Limits: With `--jev-rank` and a search, the classifier orders the first 30 matches; a failure of the classifier leaves the order as it is.

**SE-08.** The session search MUST match only the title, the native identifier, the working directory and the owner of a session.
<!-- id: SDD-SE-08 | tdd: TDD-10.4 -->

- Behavior: The match ignores the case of the letters. The search does not read the text of a transcript.
- Verified by: A search for a planted body text that gives no match.

**SE-09.** A title that the owner sets in the session index MUST NOT change the title in the native client.
<!-- id: SDD-SE-09 | tdd: TDD-10.4 | sys: SYS-PL-13 -->

- Actor: The owner or an agent, with `ai-session title`.
- Behavior: The index keeps a display title of at most 200 characters beside the last native title that a scan found.
- Observable: `ai-session show --json` prints the two titles.
- Verified by: A digest of the native folders before and after a title write.

**SE-10.** When a scan runs again, the session index MUST keep the title, the handoff, the conversation link and the launch facts that a record holds.
<!-- id: SDD-SE-10 | tdd: TDD-10.3, TDD-10.9 -->

- Behavior: The scan also keeps them on a record that it marks as stale. A change that a second process makes during the scan is not lost.
- Verified by: A scan after a title write and a handoff import, and a scan with a title write between its two steps.

**SE-11.** If a write names a revision that is not the current revision of the record, then the session index MUST refuse the write.
<!-- id: SDD-SE-11 | tdd: TDD-10.1, TDD-10.4 -->

- Behavior: Each write adds one to the revision of the record. A handoff import and a conversation bind need `--expect-revision`; a title write can give it.
- Observable: The command prints a conflict line and exits with status 3.
- Verified by: A handoff import with an old revision.

**SE-12.** When the owner imports a handoff text for a session, the session index MUST keep that text and show it with the session.
<!-- id: SDD-SE-12 | tdd: TDD-10.1, TDD-10.4 -->

- Actor: The owner or an agent, with `ai-session handoff`.
- Behavior: The text comes from a file or from standard input. With no import, the command prints the kept text, or exits with status 1 when none exists.
- On failure: A larger text is refused with exit status 1.
- Verified by: An import, a scan and a show; an import of 70000 characters.
- Limits: A handoff text has at most 65536 bytes.

**SE-13.** While two processes write one session record, the session index MUST keep each write.
<!-- id: SDD-SE-13 | tdd: TDD-10.1 -->

- Behavior: A writer holds a lock for the session and replaces the record in one step. A reader does not read a partial file.
- Observable: The revision is equal to the count of the writes, and each change adds one event that no later write changes.
- Verified by: Four processes with 25 writes each, and a writer that stops before it publishes an event.

**SE-14.** The session index MUST NOT give a user outside the group of the owner access to its files.
<!-- id: SDD-SE-14 | tdd: TDD-10.1 -->

- Behavior: The folders and the files have no permission for other users. The group of the owner can read, so that a read grant of the owner has an effect.
- Verified by: The permission bits of a handoff file after an import.

**SE-15.** The session export MUST NOT write to the session index or to a native store.
<!-- id: SDD-SE-15 | tdd: TDD-10.5 -->

- Actor: An agent in its own home, with `ai-session export`.
- Behavior: The command prints one JSON line for each session of one home. It adds the readable text only for a transcript that changed since the time of `--since`.
- Verified by: An export that leaves no state folder.

**SE-16.** When the owner ingests the export of an agent, the session index MUST record those sessions with that agent as the owner.
<!-- id: SDD-SE-16 | tdd: TDD-10.5 -->

- Actor: The owner, with `ai-session ingest --owner`.
- Behavior: A complete export that no longer lists a session marks that session as stale. A scan of the home of the owner does not report a source of an agent as absent.
- On failure: An ingest for a name that is no agent is refused, and an export that is not complete leaves the records as they are.
- Verified by: An ingest of a temporary agent home with a Claude Code session and a Pi session, then a scan of the owner, then a second ingest with a deleted transcript.

**SE-17.** Where an ingest gives launch facts, the session index MUST put them on the sessions that changed since the launch time.
<!-- id: SDD-SE-17 | tdd: TDD-10.5 -->

- Behavior: A launch fact is a key and a value: the kind, the portal, the model, the account or the place. An ingest with a later launch time does not replace the facts of an older session.
- Observable: The record in `ai-session list --json` holds the facts.
- Verified by: Two ingests with different launch times.

**SE-18.** The import of old conversation homes MUST copy each home to a folder of the agent that its record names.
<!-- id: SDD-SE-18 | tdd: TDD-10.26 -->

- Actor: The owner, with `ai-session import-old`.
- Behavior: The command does not copy a home with no known agent, a home that is at the target, or a writer lock file. A scan reads a Pi session below the old conversations folder of a home as archived history.
- Observable: The command prints the count of homes for each agent.
- Verified by: A fixture with two old homes of two agents, an ingest and a show of the archived session.

<!-- retired: SDD-SE-19 -->

**SE-20.** When the owner shows a session, the session index MUST print its title, its facts, its resume command, its handoff and its conversation text.
<!-- id: SDD-SE-20 | tdd: TDD-10.6 -->

- Actor: The owner or an agent, with `ai-session show`.
- Behavior: The facts are the client, the owner, the working directory, the account, the model and the time. With `--json` the command prints the record in the place of the text.
- On failure: An identifier that is not valid or not known gives exit status 1. Where no readable text exists, one line says so.
- Verified by: A show of an ingested Claude Code session and of an ingested Pi session.

**SE-21.** The readable text of a session MUST NOT hold a thinking block or a raw record of the native file.
<!-- id: SDD-SE-21 | tdd: TDD-10.6 -->

- Behavior: A turn has a heading with the role and the time. A tool call is one line with the tool and its main argument, and a tool result is clipped text.
- Verified by: A show of a Pi session with a thinking block, a tool call and a tool result.
- Limits: Claude Code, Codex and Pi sessions have a readable text. An argument shows at most 240 characters and a result at most 600 characters.

**SE-22.** The readable text of a session MUST show a fixed marker in the place of each text that looks like a credential.
<!-- id: SDD-SE-22 | tdd: TDD-10.6 -->

- Behavior: The marker is `[secret hidden]`. The patterns are provider keys, forge and chat tokens, bearer and basic values, signed web tokens, private keys, a password in an address and a value given to a name such as password or secret.
- Observable: The export of an agent and the kept text hold the marker and not the credential.
- Verified by: Planted credentials of each kind, and ordinary text that stays the same.

**SE-23.** When the owner asks to resume a session, the session index MUST print a plan with the command, the working directory and the environment.
<!-- id: SDD-SE-23 | tdd: TDD-10.7 -->

- Actor: The owner, with `ai-session resume`.
- Behavior: For a Claude Code or Codex session of the owner, the command changes to the recorded working directory and starts the native resume. A Pi session has a plan only when it is the session of a role.
- Observable: The plan is JSON, and the command starts no process.
- Verified by: The plan of a Codex session, and a record with shell characters in its working directory.
- Limits: The plan quotes each value of the record that it puts in the shell command.

**SE-24.** Where the owner gives the execute option, the resume command MUST start the native command only from an interactive terminal.
<!-- id: SDD-SE-24 | tdd: TDD-10.7 -->

- Behavior: The command starts an argument list with no shell, in the working directory of the plan.
- On failure: With no terminal, no native command or no working directory, the command exits with status 2.
- Verified by: An execute of the plan of a role Pi session with a stub terminal, and an execute of a plan that is not supported.
- Limits: The command has no pause, no steer and no cancel.

**SE-25.** The resume plan MUST clear the inherited native home settings and set the native home that the session record names.
<!-- id: SDD-SE-25 | tdd: TDD-10.7 -->

- Behavior: The plan removes the home variable of Codex and the home variable of Claude Code from the environment. It then sets the Codex home of the record, or the Claude Code home when the session is in an account home.
- Verified by: A plan that runs with two wrong home variables in the environment and a probe in the place of the client.

**SE-26.** If the environment holds a provider credential or a routing setting, then the resume command MUST refuse the plan.
<!-- id: SDD-SE-26 | tdd: TDD-10.7 -->

- Observable: The plan says that it is not supported, with a reason; the exit status is 2. The output does not hold the value of the setting.
- Verified by: A resume with a planted provider key variable.

**SE-27.** A resume plan for a session of an agent MUST start that session through the launcher of the agent.
<!-- id: SDD-SE-27 | tdd: TDD-10.7 -->

- Behavior: A Claude Code session resumes as `agent WHO -- --resume ID`, with the recorded folder for the engineering agent. A Pi session of a role resumes in its conversation and on the account that it started on; for a metered account the command carries the approval of the owner.
- Verified by: The plans of an agent Claude Code session, of an agent Pi session and of an agent Pi session on a metered account.
- Limits: A Codex session of an agent has no plan.

**SE-28.** If a session cannot resume through a supported native command, then the resume command MUST print the reason and exit with status 2.
<!-- id: SDD-SE-28 | tdd: TDD-10.7, TDD-10.26 -->

- Behavior: This applies to a stale record, archived history, an archived Codex thread, a record with no absolute working directory, a Pi session in the own store of the owner and a Pi session of a role with no conversation. A native identifier that is not a plain identifier is also refused.
- Verified by: A resume of a stale record and of two Pi sessions in the own store of the owner, one of them in a conversation home; a show of an archived record and of a role Pi session with no conversation; a plan for a native identifier with shell text. No test covers an archived Codex thread.
- Limits: A record whose owner is not the owner and no agent is also refused; no adapter makes such a record today.

**SE-29.** When the owner creates a conversation, the session index MUST give it a stable identifier, a name and one scope.
<!-- id: SDD-SE-29 | tdd: TDD-10.8 -->

- Actor: The owner or a launcher, with `ai-session conversation create`.
- Behavior: The scope is personal, system with a resource, project with a project of the catalog, or formation with a real folder. The name is the given lowercase name, or one made from the agent, the date and the title.
- Observable: The command prints the record; `ai-session conversation list` and `ai-session conversation show` read it by identifier or by name.
- Verified by: A create for each scope, and a show by name.
- Limits: The command starts no client. A title has 1 to 200 characters.

**SE-30.** If a conversation request breaks the scope rule of its agent, then the session index MUST refuse it.
<!-- id: SDD-SE-30 | tdd: TDD-10.8 -->

- Behavior: The personal agent takes only the personal scope. The engineering agent needs a project or a formation with a workspace, and the systems agent needs a system resource or a project.
- On failure: A workspace outside the repository of the named project is refused. A project together with a formation or with a resource is also refused.
- Verified by: A refused request for each agent, and a project request with a wrong checkout.

**SE-31.** Each conversation MUST have one home that holds its record, its checkpoint text and references to its native sessions.
<!-- id: SDD-SE-31 | tdd: TDD-10.8 -->

- Behavior: The index also keeps a reference to the home by name, by agent and by scope. A record of the older form gets a name and the absent parts when the owner lists or shows it.
- On failure: A home, a record or a reference that is a symbolic link is refused.
- Verified by: The parts of a new home, the references by name and by agent, and an older record. No test covers a symbolic link.
- Limits: The transcripts stay in the stores of their clients. Only the owner can open the home.

**SE-32.** When the owner binds an indexed session to a conversation, the session index MUST record the conversation in the session record.
<!-- id: SDD-SE-32 | tdd: TDD-10.9 -->

- Actor: The owner or a launcher, with `ai-session conversation bind`.
- Behavior: The bind needs the expected revision of the session record. The home of the conversation gets a small reference to the session, with no message content.
- Observable: `ai-session conversation show` lists the bound sessions, also after a new scan.
- Verified by: A bind, a scan and a show.

**SE-33.** If a session belongs to a different conversation, then the session index MUST refuse to bind it.
<!-- id: SDD-SE-33 | tdd: TDD-10.9 -->

- Verified by: A bind of one session to a second conversation.

**SE-34.** If the working directory of a session is outside the project or the formation of a conversation, then the session index MUST refuse the bind.
<!-- id: SDD-SE-34 | tdd: TDD-10.9 -->

- Behavior: For a project, the two folders are in the same Git repository, linked worktrees included. For a formation, the working directory is the workspace or a folder below it.
- On failure: A session with no recorded working directory is also refused.
- Verified by: A bind of a session from a different folder to a project conversation.

**SE-35.** Each session title MUST hold these fields in one fixed sequence: host, project, purpose, area, description, reference, who, client, model, type and date.
<!-- id: SDD-SE-35 | tdd: TDD-10.10, TDD-10.11 -->

- Behavior: The form is [host/project] purpose(area): Description #ref · who · client · provider/model · type · date. The reference is optional, and the client can have an account after a colon.
- Observable: The parse command of the title tool prints the fields of a title as JSON.
- Verified by: A title that the formatter makes and the parser reads again.

**SE-36.** When a caller gives a text and a client, the title formatter MUST print one full title in the title format.
<!-- id: SDD-SE-36 | tdd: TDD-10.10 -->

- Actor: A launcher, a hook or an agent, with `ai-title format`.
- Behavior: Where the caller gives no value, the host is the machine, the project is the repository of the working directory, who is the user and the date is today. A text that is a full title keeps its middle part, and a middle part of more than 80 characters is cut.
- Verified by: A title with each field given, a full title as the text, and a worktree path that no longer exists.
- Limits: A worktree gives the name of its main repository. A type outside the list becomes interactive.

**SE-37.** Where a launcher sets the session variables, the title formatter MUST use them for who, the account, the provider, the model and the type.
<!-- id: SDD-SE-37 | tdd: TDD-10.10, TDD-10.13, TDD-10.17 -->

- Behavior: The variables are `DEV_SESSION_WHO`, `DEV_SESSION_ACCOUNT`, `DEV_SESSION_PROVIDER`, `DEV_SESSION_MODEL` and `DEV_SESSION_TYPE`. A title hook takes these values before the values that it finds in the data of the session.
- Verified by: A hook run with the variables set, for Claude Code and for Pi.

**SE-38.** When a caller checks a title, the title check MUST list each problem and exit with status 1 if one exists.
<!-- id: SDD-SE-38 | tdd: TDD-10.11 -->

- Actor: A hook, an extension or the owner, with `ai-title check`.
- Behavior: A problem is: a title that is not in the format, a purpose or a type outside the lists, the placeholder text, a text like a credential, a middle part of more than 80 characters, or a date that is not real. The purposes are feat, fix, refactor, docs, test, chore, loop, review, spike, forensics, ops, chat, plan, research, write, admin, learn and personal.
- Verified by: A check of a title from before the format.
- Limits: The types are interactive, headless, subagent, seat, loop, scheduled, web and cloud. The check does not compare the client with a list.

**SE-39.** The title formatter MUST NOT put a text that looks like a credential in a title.
<!-- id: SDD-SE-39 | tdd: TDD-10.10 -->

- Behavior: The formatter writes `[redacted]` in the place of the text.
- Verified by: A format of a text with a planted key.

**SE-40.** When a text has no purpose and no area, the title formatter MUST add a purpose and an area from the text and the branch.
<!-- id: SDD-SE-40 | tdd: TDD-10.11 -->

- Behavior: The kind of the branch name gives the purpose where it is in the list; if not, the first word rule that matches gives it, and the last choice is chat. The area is the first content word of the branch name or of the text, and the last choice is misc.
- Observable: `ai-title guess` prints the purpose and the area for a text and a branch.
- Verified by: Guesses from a branch name, from words and from the two together.

**SE-41.** When a caller asks for a short title, the title formatter MUST print the project, a colon, the purpose and the area.
<!-- id: SDD-SE-41 | tdd: TDD-10.11 -->

- Actor: A launcher of terminal windows, with `ai-title short`.
- Behavior: The command accepts a middle part or a full title.
- Verified by: A short title from a middle part and from plain words.

**SE-42.** When a new session of a supported client has no title that conforms, the title hook of that client MUST set a full title.
<!-- id: SDD-SE-42 | tdd: TDD-10.13, TDD-10.16, TDD-10.17 -->

- Behavior: The hook takes the description from the present title, or from the first prompt, and adds each other field from the data of the session. The supported clients are Claude Code, Codex and Pi.
- Observable: The title that the client shows; in Pi also the title of the terminal.
- Verified by: A first prompt in each of the three clients, and a second prompt in Claude Code.
- Limits: In Claude Code the hook replaces a title with no part from a model one time in each session. A session start with no title and no prompt changes nothing in Claude Code and Codex; the Pi extension sets a placeholder title, which the first input replaces.

**SE-43.** A title hook MUST NOT change a title that conforms.
<!-- id: SDD-SE-43 | tdd: TDD-10.13, TDD-10.16, TDD-10.17 -->

- Verified by: A session with a title that conforms, in each of the three clients.

**SE-44.** When a model or a person sets only the middle part of a title, the title hook MUST add each other field.
<!-- id: SDD-SE-44 | tdd: TDD-10.12, TDD-10.13, TDD-10.16, TDD-10.17 -->

- Behavior: The Claude Code hook does this on the next prompt, the Codex hook on its next event, and the Pi extension in its title tool. A who field after the middle part stays, and a full title with damaged fields is made again.
- Verified by: A bare middle part as the title in Claude Code and in Codex, a damaged title of a worker, and a call of the Pi title tool.

**SE-45.** If a title hook cannot name a session, then the hook MUST NOT stop or fail the session.
<!-- id: SDD-SE-45 | tdd: TDD-10.13, TDD-10.16 -->

- Behavior: The Claude Code hook prints nothing and exits with status 0 on each error. The Codex hook exits with status 0 and writes the error to a log in the Codex home.
- Verified by: Runs of the Claude Code hook with empty input and with input that is no JSON, and a run of the Codex hook with no input.

**SE-46.** A description that the Claude Code or Codex hook takes from a prompt MUST NOT hold injected client text, markup, an address or a credential.
<!-- id: SDD-SE-46 | tdd: TDD-10.12, TDD-10.13 -->

- Behavior: The hook takes the first line that describes the task and cuts it at a word.
- Verified by: Prompts with an injected first line, with a reminder block, with a planted token and with 100 words.
- Limits: The description has at most 60 characters in Claude Code and 70 characters in Codex. The Pi extension takes the first 70 characters of the first line, and only the credential rule of the formatter applies to it.

**SE-47.** A title hook MUST give the type subagent to a session that a second agent starts.
<!-- id: SDD-SE-47 | tdd: TDD-10.13, TDD-10.15, TDD-10.16 -->

- Behavior: In Claude Code an agent identifier, a subagent transcript or a who of the form worker@parent marks such a session; in Codex the source of the thread does. A spawned Codex thread gets its description from its agent path and its who from its nickname and the area of the parent title.
- Verified by: A Claude Code prompt with an agent identifier, and a spawned Codex thread with a parent title.
- Limits: The Pi extension has no rule for a subagent.

**SE-48.** The Codex title hook MUST NOT write to the database or the index file of Codex.
<!-- id: SDD-SE-48 | tdd: TDD-10.15, TDD-10.16 -->

- Behavior: The hook names the thread with the rename call of the Codex app server, over its control socket. It reads the thread table only to find the client, the type and the parent.
- Verified by: A stub app server that records the calls.

**SE-49.** When a Codex or Pi session starts as a resume, the title hook MUST NOT set a title.
<!-- id: SDD-SE-49 | tdd: TDD-10.16, TDD-10.17, TDD-11.8 -->

- Behavior: The Codex hook does nothing at a session start with the source resume or clear. The Pi extension names a session at start only for the reasons startup and new. The role launcher of Pi starts a resumed file with the reason resume.
- Verified by: A resumed Codex thread and a resumed Pi session with a plain old title. A check of a resumed role session whose file stays the same.
- Limits: A later prompt gets a title in a resumed Codex thread whose name does not conform, and in a resumed Pi session with no name. Plain Pi gives the reason startup also to a session that it resumes at launch, so the extension can name such a session when its name does not conform.

**SE-50.** Where the client is the Claude desktop app, the title hook MUST give the model the exact full title to send.
<!-- id: SDD-SE-50 | tdd: TDD-10.14 -->

- Behavior: On the first prompt the hook adds a note with the title, an open place for the middle part, and the standard of the middle part. When the model sends a title with absent fields or a middle part that is not standard, the hook adds a note with the title to send again.
- Verified by: A first prompt in the desktop app, a rename with only the middle part, a rename with a bad middle part and a rename of a different session.
- Limits: The hook examines only a rename of the own session.

**SE-51.** While a Claude desktop session has no standard title from the model, the title hook MUST block the end of a turn.
<!-- id: SDD-SE-51 | tdd: TDD-10.12, TDD-10.14 -->

- Behavior: The standard is: a purpose of the list, an area that names a part of the project, and a description of 2 to 10 words and at most 60 characters, with a capital first letter, a verb first and no full stop. The block message gives the title to send.
- Verified by: A stop with the title of the hook, with a bad middle part, a third stop, and a stop in the command line client.
- Limits: The hook blocks at most two times in one session. It does not block a subagent or a different client.

**SE-52.** If the Claude desktop app puts an old title back, then the title hook MUST set the last rename again on the next prompt.
<!-- id: SDD-SE-52 | tdd: TDD-10.14 -->

- Behavior: The hook reads the last middle part from its own state, or from the last short title record of the transcript.
- Verified by: A transcript with a rename between two copies of an old title.

<!-- retired: SDD-SE-53 -->

<!-- retired: SDD-SE-54 -->

<!-- retired: SDD-SE-55 -->

<!-- retired: SDD-SE-56 -->

<!-- retired: SDD-SE-57 -->

<!-- retired: SDD-SE-58 -->

<!-- retired: SDD-SE-59 -->

<!-- retired: SDD-SE-60 -->

**SE-61.** The bundle command MUST print one installer file that needs only Python on the target machine.
<!-- id: SDD-SE-61 | tdd: TDD-10.22 -->

- Actor: The owner, with `ai-title-bundle`.
- Behavior: The installer holds the title formatter, the Claude Code hook, the Codex hook and the Pi extension as data.
- On failure: An argument that the command does not know gives exit status 2.
- Verified by: An installer that runs in an isolated Python with a temporary home.

**SE-62.** When the installer runs, the installer MUST add the title hooks and the naming rule to each client home that it finds.
<!-- id: SDD-SE-62 | tdd: TDD-10.15, TDD-10.22 -->

- Behavior: It adds the hooks to each Claude Code home and to Codex, the rule and the word list of the owner to each global prompt file, and the extension to Pi. It asks the Codex app server to trust the hook, and prints a note when that is not possible.
- Observable: A second run adds no second copy of a hook or a rule.
- Verified by: Two runs in a home with a Claude Code home and an account home, then a prompt through the installed hook. No test covers the trust step.

**SE-63.** The installer MUST keep each setting and each text that it did not write.
<!-- id: SDD-SE-63 | tdd: TDD-10.22 -->

- Behavior: The installer writes a copy of a file to a backup folder and then replaces the file. Where a prompt file has the rule block of the platform, the installer adds no second rule.
- On failure: A settings file that is no valid JSON stays as it is, and the installer prints a note.
- Verified by: A home with a model setting and a hook of the owner, and a prompt file with the block of the platform.

**SE-64.** When the owner runs the status command of the installer, the installer MUST list each part that is absent.
<!-- id: SDD-SE-64 | tdd: TDD-10.22 -->

- Observable: The exit status is 1 when a part is absent. With each part in place, the command prints ok and a sample title.
- Verified by: A status after an install, and a status with the naming rule removed.

**SE-65.** Where the caller gives the client option, the installer MUST also install the writing standard, the commit rule, the command guard and the Git hooks.
<!-- id: SDD-SE-65 | tdd: TDD-10.22 -->

- Behavior: The installer also adds the rule that engineering on a platform repository runs on the platform machine. It leaves a Git hooks path of the owner and a different text of the writing standard as they are, and prints a note.
- Verified by: Two runs of the client installer, a refused force push and a refused commit message through the installed guards, and a home with a hooks path of the owner.
- Limits: The installer does not change the sandbox settings or the approval settings of Codex, or a credential.

**SE-66.** When a session of an agent or a loop worker reaches turn 20, the session length guard MUST warn the agent.
<!-- id: SDD-SE-66 | tdd: TDD-10.23 -->

- Behavior: The guard counts the typed turns of a Claude Code or Codex transcript; injected context, tool results and notices are no turns. A Pi role session has the same guard.
- Verified by: A transcript with 19 typed turns and extra tool results, and the offline check of the Pi guard.
- Limits: `SESSION_TURN_WARN` changes the number for Claude Code and Codex.

**SE-67.** When a session of an agent or a loop worker passes turn 30, the session length guard MUST refuse the next prompt.
<!-- id: SDD-SE-67 | tdd: TDD-10.23 -->

- Behavior: The message tells the agent to start a new session with a summary of five lines.
- Verified by: Transcripts with 29 and with 30 typed turns, and the offline check of the Pi guard.
- Limits: `SESSION_TURN_STOP` changes the number for Claude Code and Codex.

**SE-68.** The session length guard MUST NOT warn or block a session of the owner that is not a loop worker.
<!-- id: SDD-SE-68 | tdd: TDD-10.23 -->

- Behavior: The guard reads the name of the owner from a file that only root writes, and not from the environment. With no such file, each session has the limit.
- Verified by: Runs as the owner, as a different user, as a loop worker, with no owner file and with a false owner name in the environment.
- Limits: The guard of a Pi role session has no exception.

**SE-69.** Each Claude Code and Codex home that the platform configures MUST load the shared session entry text through its native user instructions.
<!-- id: SDD-SE-69 | tdd: TDD-10.24 -->

- Behavior: The prompt file of Claude Code imports the text. The prompt file of Codex tells the agent to read and apply the text at session start, on resume and when the task changes.
- Verified by: The prompt files of a home after an install of the platform rules.
- Limits: The instructions guide the model; they are no security boundary and no proof that a model followed the text.

**SE-70.** Each Pi role session MUST get the shared session entry text in its start context.
<!-- id: SDD-SE-70 | tdd: TDD-10.24 -->

- Behavior: The role loader puts the text in the context before the role identity and the project instructions. It does not use skill discovery for this.
- Verified by: The offline check of the role loader for ten combinations of role, scope and start folder.

## RO. Roles
<!-- section: SDD-RO | sys: SYS-PL-07 -->

Three roles work for the owner on the Pi client: Assistant for personal work, Engineer for engineering and Ops for systems and security. This part of the platform starts a conversation of a role with one account, one model, one workspace and one writer. At each start it gives the role its identity, its rules, its skills and its memory, because a role that starts with an identity and nothing else can recall no decision and no preference. It keeps the records of the retired agent system and of the old machine as archives that a role can only read, with each secret hidden, because these records are reference data and not instructions. The outer launcher of the server calls `ai-role` with the login folder of one session; the owner and the roles use `ai-memory` and `ai-history`. The outer launcher and the build of the old archive are not in this copy.

The reasons:

- RO-01: Scope comes first: Assistant is personal and independent of a project, Engineer needs a project or a formation workspace, and Ops starts with an explicit scope.
- RO-02: A role does not inherit the engineering identity of the repository where a shell starts it.
- RO-03: The identity states what a role is and what it can touch.
- RO-04: The shared entry skill gives a short orientation at each start, each resume and each change of task.
- RO-05: A role that starts with its index is oriented, and the index has a cost in the context, so the plan shows its size.
- RO-07: Only Engineer gets the full engineering method; the other roles and the workers do not load it.
- RO-09: Credentials stay with the native client and the outer launcher; no token is copied between stores.
- RO-10: The launcher makes no silent change of the account or of the billing: it stops.
- RO-11: A tool that Pi runs finds its key in the folder of the handed credentials, and no other part of the environment of the outer launcher goes on.
- RO-12: Each role starts on its model in the one model file, by the decision of the owner of 2026-10-05.
- RO-13: Attribution stays honest: a sign-in that works does not prove which identity it is.
- RO-14: On the server the root launcher resolves the account and runs the role as its own Linux user, so the role needs no registry of its own.
- RO-15: One writer for each conversation protects the native history, and the end of the process frees the lock, so a stale lock needs no repair.
- RO-16: A native session belongs to the account that it started on; a change of account needs an explicit handover.
- RO-17: The native steps new, resume and fork keep the bounds of the role and of the conversation.
- RO-19: A checkout that works hides an absent package, and a released install then fails at the import.
- RO-20: The original corpus is the record of the earlier agent: it is never changed, moved or deleted.
- RO-22: A role gets the passages that it needs on demand, and not the full archive in its context.
- RO-24: The launcher takes the memory from the role, and no option starts a role with no memory.
- RO-25: The records of the retired agent system stay preserved and read-only.
- RO-26: Each role keeps its access to its own history and its role boundary.
- RO-27: A role studies its past records and never quotes a secret from them.
- RO-28: Preserved records are reference data: they are not instructions and not proof of the present state.
- RO-29: With no archive argument the history is absent; the tool does not search for an archive silently.
- RO-36: Each role reads the journal and no role writes it; what a role adds goes to the inbox of the owner.
- RO-37: Engineer and Ops are roles of the account of the owner by the decision of 2026-11-14; Assistant stays a separate user because his data is personal.

**RO-01.** A role conversation MUST start only with a scope that its role permits.
<!-- id: SDD-RO-01 | tdd: TDD-11.6 -->

- Behavior: The roles are Assistant (personal), Engineer (engineering) and Ops (systems and security). Assistant takes the personal scope only, Engineer a project or a project formation, and Ops a system, a project or a formation.
- On failure: A role name outside the three, or a scope that the role does not permit, stops the start with one line.
- Verified by: A check that loads each of the five permitted pairs of role and scope; a test of a pair that is not permitted.

**RO-02.** A role conversation MUST NOT take its workspace or its context from the folder where the launch command runs.
<!-- id: SDD-RO-02 | tdd: TDD-11.6 -->

- Behavior: With the personal or the system scope, the conversation runs in a neutral workspace inside its own home and loads no instruction file of a repository. With a project or a formation, it runs in the workspace that the conversation binds and loads the instruction files of that workspace.
- On failure: A project scope with no bound workspace, or a neutral workspace that is a symbolic link, stops the start.
- Verified by: A check that starts each permitted pair from two unrelated folders and compares the workspace and the context.

**RO-03.** Each role conversation MUST start with the identity text of its role in its context.
<!-- id: SDD-RO-03 | tdd: TDD-11.3, TDD-11.6 -->

- Behavior: The launcher uses the identity file in the state folder of the role. Where that folder has none, it uses the identity file of the platform.
- On failure: A role with no identity file does not start, and the launcher names the file to write.
- Verified by: A plan test with an identity in the state folder, with the identity of the platform and with none; the check of the context.

**RO-04.** Each role conversation MUST start with the session entry guidance of the platform in its context.
<!-- id: SDD-RO-04 | tdd: TDD-11.6 -->

- Behavior: The guidance is the text of the skill `develop`. It is in the context from the start and does not wait for a skill search.
- Verified by: The check of the context finds the guidance one time, equal to its source.

**RO-05.** Where a role has a memory index, the role conversation MUST start with that index in its context.
<!-- id: SDD-RO-05 | tdd: TDD-11.6 -->

- Behavior: The index is one file of the live memory root of the role. The other entries and the inherited records stay behind the memory tool.
- Observable: The launch plan shows if the index is in the context, and its size.
- Verified by: A check that loads a role with a memory index and reads the context.

**RO-06.** Each role identity of the platform MUST hold the canonical rules of the platform word for word.
<!-- id: SDD-RO-06 | tdd: TDD-11.3 -->

- Behavior: The canonical rules are one file of the platform. Each identity file holds its full text.
- Verified by: A test that looks for the text of the rules in each identity file.

**RO-07.** A role conversation MUST NOT load a skill by automatic discovery.
<!-- id: SDD-RO-07 | tdd: TDD-11.7 -->

- Behavior: A role gets the skills that the skills table of the platform lists for it: none for Assistant and Ops, the engineering skill and the platform skills of project work for Engineer. Engineer in a project also gets the skills that the project keeps, and a platform skill wins where two skills have one name.
- Verified by: A check with a skill that discovery finds, a project skill, and a project skill with the name of a platform skill.
- Limits: The automatic discovery of extensions, prompt templates and themes is off also.

**RO-08.** When the owner asks for a launch plan, the launcher MUST print the plan and start no conversation.
<!-- id: SDD-RO-08 | tdd: TDD-11.1 -->

- Actor: The outer launcher or the owner, with `ai-role plan <conversation>` and a handed login folder.
- Observable: The plan shows the role, the scope, the workspace, the account, the model, the resume file, the memory roots with their entry counts, the journal folder and the command of the launch.
- Verified by: The plan tests of the launcher.

**RO-09.** The launcher MUST NOT print or store a credential.
<!-- id: SDD-RO-09 | tdd: TDD-11.1 -->

- Behavior: The plan holds the names of the environment variables and no value. The key of a provider and the key of the search tool go only into the environment of the one Pi process.
- Observable: The header line of a launch says if the search tool is on, off or offline.
- Verified by: Tests that look for a planted key in the plan, and for the search key in the environment of the launch only.

**RO-10.** If a launch condition fails, then the launcher MUST start no conversation and print one line with the reason.
<!-- id: SDD-RO-10 | tdd: TDD-11.1, TDD-11.5 -->

- Behavior: The conditions are: a Pi login folder that the outer launcher hands in; an account name; an environment with no conflicting provider setting; a conversation with a native session folder; a model; the Pi runtime. An interactive launch also needs a terminal on its input and its output.
- Observable: The line starts with `ai-role:` and the exit status is 2.
- Verified by: A test for each condition.

**RO-11.** The launcher MUST pass to the Pi process only the variables of a fixed list from its own environment.
<!-- id: SDD-RO-11 | tdd: TDD-11.1 -->

- Behavior: The list holds the path, the home, the language, the terminal, the shell, the temporary folder and the folder of the handed credentials. The launcher adds the login folder, the goal folder inside the conversation home, the variables of the session title and the launch plan.
- Verified by: A test that puts a foreign variable in the environment of the launcher and reads the environment of the launch.

**RO-12.** Where no model is named, the launcher MUST start the role on its start model from the model file.
<!-- id: SDD-RO-12 | tdd: TDD-11.2 -->

- Behavior: The start line of a role lists models in order, and the launcher takes the first one that the provider of the session runs. Where the line has none for that provider, the launcher takes the saved default model of the handed login folder.
- On failure: With no model from these sources, or with a model name of a wrong form, the launcher stops and asks for a model.
- Verified by: Tests of a named model and of a start line with two providers; a test of the saved default model.

**RO-13.** The launcher MUST report the account identity of each role conversation as unverified.
<!-- id: SDD-RO-13 | tdd: TDD-11.1 -->

- Behavior: A Pi sign-in is a separate login from the Codex or Claude sign-in of the same account. The launcher does not state that the two are one identity or share one quota.
- Observable: A launch prints one header line with the role, the scope, the workspace, the model, the account and the count of memory entries. The plan and the header show the account with the words `identity unverified`.
- Verified by: The plan test reads the account part of the plan; the launch test reads the header line.

**RO-14.** The launcher MUST start a role conversation only with the Pi login folder that the outer launcher hands in.
<!-- id: SDD-RO-14 | tdd: TDD-11.1 -->

- Behavior: The outer launcher of the server resolves the account and names it with its provider, so the launcher selects no account and keeps no profile of its own. For a provider with an API key, the key comes from the handed credential.
- On failure: With no handed folder, no account name, no login in the folder or no handed key, the launch stops with one line.
- Verified by: Tests with a handed login, with no folder, with no account name, with a login that is absent and with a handed key.

**RO-15.** A role conversation MUST have at most one writer process at one time.
<!-- id: SDD-RO-15 | tdd: TDD-11.4 -->

- Behavior: The launcher takes an exclusive lock of the conversation and then becomes the Pi process, which keeps the lock until it ends. The Pi process starts only with the lock of its own conversation.
- On failure: A second launch of the same conversation stops with one line. When the writer ends, also by a forced stop or a failed start, the next launch works with no cleanup step.
- Verified by: A test with two launches, a writer stopped by force and a failed start; a check of the terminal through the lock.
- Limits: The lock is cooperative and local to one file system.

**RO-16.** A role conversation MUST resume a native session only where its recorded conversation, role, account and workspace are the same.
<!-- id: SDD-RO-16 | tdd: TDD-11.8 -->

- Behavior: Each native session records its conversation, its role and its account reference in one entry at its start, and its file is in the folder of the conversation. The caller names the file to resume, or `latest` for the newest one.
- On failure: A file outside the folder of the conversation, a symbolic link, or a record that differs stops the resume, and the file does not change.
- Verified by: A plan test of the resume file; a check that resumes with a different account, a different conversation and an outside file.

**RO-17.** While a role conversation runs, the client MUST refuse a switch to a native session that the conversation does not own.
<!-- id: SDD-RO-17 | tdd: TDD-11.9 -->

- Behavior: A new session, a resume and a fork inside the client stay in the folder of the conversation and keep the record. A resume or an import of an outside file is cancelled with a notice, and the present session stays.
- Verified by: A check that runs new, resume, fork, an outside resume and an outside import on the real client with no network.

**RO-18.** Where the caller asks for one turn, the launcher MUST read one message from its input, print the answer and end.
<!-- id: SDD-RO-18 | tdd: TDD-11.5 -->

- Actor: A second system, for example the shared chat of the server, with `ai-role turn <conversation>`.
- Behavior: A turn needs no terminal and holds the same writer lock. The message has 64 KiB at most.
- On failure: An empty message stops the turn.
- Verified by: A test of one turn with a message and with no message.

**RO-19.** The launcher MUST run the Pi version that the platform pins.
<!-- id: SDD-RO-19 | tdd: TDD-11.2 -->

- Behavior: A release holds no package folder of the client. The launcher links the installed runtime of the pinned version one time, and it never uses a different installed version.
- On failure: Where the pinned version is not installed, or a package folder exists with no client in it, the launcher stops.
- Verified by: A test with a release folder, two installed versions, a checkout with the package and a broken install.

**RO-20.** The memory command MUST NOT write to an inherited memory root.
<!-- id: SDD-RO-20 | tdd: TDD-11.10, TDD-11.11 -->

- Behavior: Each role has one live root that it can write, and zero or more inherited roots of the agent that it continues. The record of an inherited root holds its path and the mode read-only.
- Observable: Each result names the root that it comes from, and the status marks only the live root as writable.
- Verified by: Tests that read the record of an inherited root, the status of each root and the entries of both roots.

<!-- retired: SDD-RO-21 -->

**RO-22.** Each memory result and each history result MUST be one page with a cursor to the next page.
<!-- id: SDD-RO-22 | tdd: TDD-11.11, TDD-11.12 -->

- Behavior: Each page says if more rows exist. A list and a search give the offset of the next page, and a read gives the last line or the last sequence number of its page.
- Verified by: A memory test that reads two pages; a check that reads 15 saved windows on two pages with no loss.
- Limits: A page of the history command holds 1 to 100 rows.

**RO-23.** If a state path of a role holds a symbolic link, then the platform MUST refuse to use that path.
<!-- id: SDD-RO-23 | tdd: TDD-11.1, TDD-11.3, TDD-11.4, TDD-11.8, TDD-11.10 -->

- Behavior: The state paths are the state folder of the memory, the identity file, the conversation home, the handed login folder and a native session file. The memory command also refuses an entry name that is not of the form `<source>:<file>`.
- Verified by: A memory test with a linked state folder and with wrong entry names; a test of each other path.

**RO-24.** Each role conversation MUST have a tool that lists, searches and reads the memory of its own role.
<!-- id: SDD-RO-24 | tdd: TDD-11.11 -->

- Behavior: The tool calls the memory command with the role of the conversation. A call cannot name a different role.
- Verified by: A check that calls the registered tool for each role.

**RO-25.** The history command MUST NOT write to an archive.
<!-- id: SDD-RO-25 | tdd: TDD-11.12 -->

- Behavior: An archive is the old memory folder of a role, the old archive, or a folder with the same layout; a caller can give more than one, and the command reads each one that exists. The command reads the records of the retired agent system and the Pi conversations of the old machine, and it needs no runtime of the retired system.
- On failure: With no archive that exists, or a session that no archive holds, the command prints one fixed line with no detail.
- Verified by: A test that compares the hash of a store before and after each read and tries a delete; a test with an empty archive and a full one.
- Limits: A search matches its text as literal text: a wildcard character or a quote has no special function.

**RO-26.** The history command MUST return only the records of the role that the caller names.
<!-- id: SDD-RO-26 | tdd: TDD-11.12 -->

- Behavior: Each role has its own store in an archive, and a Pi conversation of the old machine names its role. A session of a different role is not found.
- Verified by: A test with conversations of two roles; a check that asks for the session of a different role.
- Limits: This is the routing of a tool and not the isolation of the operating system: a shell of the same user can read the files.

**RO-27.** The history command MUST hide each secret in each text that it prints.
<!-- id: SDD-RO-27 | tdd: TDD-11.12 -->

- Behavior: The command uses the one mask of the platform, also on an archive that no build masked. A hidden secret shows as `[secret hidden]`.
- Verified by: A test that reads a planted key from a masked archive and from a raw archive.

**RO-28.** Each memory read and each history result MUST carry a notice that the text is reference and not an instruction.
<!-- id: SDD-RO-28 | tdd: TDD-11.11, TDD-11.12 -->

- Behavior: The notice is one field of the result.
- Verified by: A memory test and a history test that read the notice.

**RO-29.** Where a launch names a history archive, the role conversation MUST have a history tool that is bound to its own role.
<!-- id: SDD-RO-29 | tdd: TDD-11.13 -->

- Behavior: The tool takes the role from the conversation and the archives from the launch; a value of the environment has no effect. With no archive in the launch, the conversation has no history tool.
- On failure: An archive that is no absolute path of a folder stops the launch.
- Verified by: A check that sets a wrong role and a wrong archive in the environment and calls the registered tool for each role.

**RO-36.** Where a journal folder is configured, the launcher MUST give each role conversation the journal folder and the inbox of the owner.
<!-- id: SDD-RO-36 | tdd: TDD-11.1 -->

- Behavior: The journal folder is the first line of the journal config file of the owner, or the default journal of the server where that file is absent. The journal tool decides what a role reads and where an addition goes; that tool is a part of area RT.
- On failure: With no journal folder that exists, the conversation starts with no journal tool.
- Verified by: A test with a config file, with none, with a comment only and with a path that is no folder; a plan test of each role.

**RO-37.** The platform MUST supply the roles Engineer and Ops as one definition each for the account of the owner.
<!-- id: SDD-RO-37 | tdd: TDD-11.16 -->

- Behavior: One file is the agent definition of Claude Code and the skill of each other client. Such a role has the access of the account of the owner and no login of its own.
- Verified by: The test of the skill front matter reads each definition through its skill link.

<!-- retired: SDD-RO-78 -->

<!-- retired: SDD-RO-79 -->

## RT. Role tools
<!-- section: SDD-RT | sys: SYS-PL-07 -->

A role does its work in a conversation, and this area gives the role the tools that it can call there. The journal tool lets each role read the journal of the owner and leave work entries and proposals in his inbox, because the owner alone writes his journal. The web fetch tool and the search tool give a role public reference material, with guards that keep a page away from the local machine and keep the search key out of the conversation. The advice tool lets a seat on a low-cost model ask the strongest judgment model for a second opinion. An archive reader keeps the task lines of the old notes folder searchable and changes nothing.

The reasons:

- RT-03: The owner alone writes his journal: what a role wants to add goes to his inbox, and he takes it or drops it.
- RT-04: A work entry says what was done, for which project and for how long, so that the personal role can reconcile the hours.
- RT-05: An entry with no project cannot be billed, and the personal role must see that when it reconciles the hours.
- RT-06: Personal coordination and the journal belong to the personal role; the other roles keep durable reference in their own memory.
- RT-07: The owner takes a proposal or drops it; a task proposal has the form of a task file, so that he takes it with one command.
- RT-08: The dense daily log of the personal role is its own record, so it stays in its memory and not in the journal of the owner.
- RT-09: The tasks of the old notes folder were not imported into the journal, and the reader keeps them searchable.
- RT-10: The old notes folder is an archive that stays unchanged.
- RT-13: A line with a fault is flagged and not dropped, so that no task of the old notes folder is lost from a search.
- RT-16: A role that has the address of a page reads it at no cost; the search tool finds addresses.
- RT-17: A page cannot steer a role into a local service of the machine.
- RT-18: A public page cannot send the tool to a local address through a redirect.
- RT-21: The key is a secret that the launcher hands in; a role does not get it through the chat.
- RT-22: The reply of the provider and a fetch error can hold sensitive data of the request.
- RT-24: A seat on a low-cost model gets a second opinion from the strongest judgment model where a wrong decision is expensive.

**RT-01.** Where a role conversation has a journal, the journal tool MUST return the open tasks of the owner to each role.
<!-- id: SDD-RT-01 | tdd: TDD-12.1 -->

- Actor: A role in a Pi conversation, through the tool `journal`.
- Behavior: The action `tasks` returns at most 50 open tasks in the order of their file names. Each task has its first line, its file and, where present, its due date, scheduled date, priority and tags.
- Verified by: The check script of the journal tool reads two task files as each of the three roles and compares the fields.
- Limits: The tool reads at most 64 KB of one file. It skips hidden files and symbolic links.

**RT-02.** Where a role conversation has a journal, the journal tool MUST return the note of one day to each role.
<!-- id: SDD-RT-02 | tdd: TDD-12.1 -->

- Behavior: The action `day` takes a date in the form YYYY-MM-DD and uses today when the caller gives none. A day with no note gives a short text that says so.
- On failure: The tool refuses a date in a different form and a path that leaves the journal.
- Verified by: The check script reads the note of today as each role and gets a refusal for a date in words.
- Limits: The tool returns at most 64 KB of a note and adds a mark when it cuts the text.

**RT-03.** The journal tool MUST NOT write in the journal of the owner.
<!-- id: SDD-RT-03 | tdd: TDD-12.1 -->

- Behavior: Each thing that a role adds goes to the inbox of the owner or to the memory of the role.
- Observable: The files of the journal are the same before and after each action of the tool.
- Verified by: The check script compares the tree and the content of the journal before and after all actions of the three roles.

**RT-04.** When a role records work, the journal tool MUST put one new work entry in the inbox of the owner.
<!-- id: SDD-RT-04 | tdd: TDD-12.2 -->

- Behavior: The action `work` writes a small text file with the role, the date, a summary of one line and, where given, the project and the minutes. The role name comes from the launch of the conversation, and the file name holds the date, the time, the role, the kind and a random identifier.
- On failure: The tool refuses a call with no summary and a call when the inbox does not exist. It does not replace a file that the inbox holds.
- Verified by: The check script records work as each of the three roles and reads the three entries back with their roles.

**RT-05.** When a role asks for the work entries of a day, the journal tool MUST return each entry with a billable mark.
<!-- id: SDD-RT-05 | tdd: TDD-12.2 -->

- Behavior: The action `entries` reads the work entries in the inbox whose file name starts with the date. An entry with a project is billable, and an entry with no project is not.
- Verified by: The check script reads three entries that have a project. No check has an entry with no project.

**RT-06.** If a role that is not the personal role calls a proposal action or a log action, then the journal tool MUST refuse the call.
<!-- id: SDD-RT-06 | tdd: TDD-12.2 -->

- Behavior: The proposal actions are `task` and `journal-line`, and the log actions are `log-append` and `log-path`. The tool does not list these actions for the other roles.
- Verified by: The check script calls `task` and `journal-line` as the two other roles and gets a refusal that names the role.

**RT-07.** Each proposal of the personal role MUST go to the inbox of the owner as one new file.
<!-- id: SDD-RT-07 | tdd: TDD-12.2 -->

- Behavior: A proposal is a task or one line for the journal, made with the action `task` or `journal-line`. A task proposal holds the task text and, where given, a due date, and each file ends with a line that says that it is a proposal.
- On failure: The tool refuses a proposal with no text.
- Verified by: The check script proposes one task and one journal line and counts two files of these kinds in the inbox.

**RT-08.** When the personal role appends to its daily log, the journal tool MUST write the section in the memory of that role.
<!-- id: SDD-RT-08 | tdd: TDD-12.2 -->

- Behavior: The action `log-append` adds a section with a title and a body to the file of today in the folder `days` of the memory. The action `log-path` returns the path of that file.
- On failure: The tool refuses a call with no title or no body. The launch of a conversation of the personal role that has a journal and no memory folder fails.
- Verified by: The check script appends one section and reads its title in the file of today in the memory folder.

**RT-09.** The archive reader MUST list each task line of a Markdown folder with its file, its line number and its state.
<!-- id: SDD-RT-09 | tdd: TDD-12.3, TDD-12.4 -->

- Behavior: A task line is a list item with a check box, and its state is todo, done, in-progress, cancelled or unknown. Each line also gives its dates, its tags, its priority and a mark for a recurrence.
- Observable: With `--json` the output is one object with the folder and the list of tasks. With no option each line has the path, the line number, the symbol of the check box and the text.
- On failure: With no folder given the reader stops with status 2 and reads nothing. A folder that does not exist gives status 1.
- Verified by: The unit test of the reader runs it on a fixture folder and compares the line numbers and the states. No test runs it with no folder.

**RT-10.** The archive reader MUST NOT change a file of the folder that it reads.
<!-- id: SDD-RT-10 | tdd: TDD-12.3 -->

- Observable: Each file of the folder has the same bytes before and after a run.
- Verified by: The unit test compares the bytes of each fixture file before and after all runs.

**RT-11.** The archive reader MUST NOT list a task line from front matter, a fenced block, a hidden path or a symbolic link.
<!-- id: SDD-RT-11 | tdd: TDD-12.3 -->

- Behavior: Front matter is the block between two lines of three hyphens at the top of a file. A fenced block ends at a fence of the same character that is not shorter than the fence that opened it.
- Verified by: The unit test has a fixture with front matter, a fenced example and a symbolic link. No test has a hidden path.

**RT-12.** Where the caller does not ask for history, the archive reader MUST NOT list a task line of a history folder.
<!-- id: SDD-RT-12 | tdd: TDD-12.3 -->

- Behavior: The history folders are four fixed top folders of the old notes folder: the records of the personal role, the archive, the templates and the data views. The option `--include-history` includes them.
- Verified by: The unit test has a task line in the archive folder: it is absent by default and present with the option.

**RT-13.** If a task line has an invalid date, a repeated date or an unknown state, then the archive reader MUST list it with a warning.
<!-- id: SDD-RT-13 | tdd: TDD-12.3 -->

- Behavior: The reader also warns for a date mark with no date that it can read and for a cancel date on a line that is not cancelled. In the plain output the warnings follow the text of the line.
- Verified by: The unit test has an invalid due date, an unknown state and a cancel date on a done line. No test has a repeated date.

**RT-14.** The archive reader MUST return only the task lines that agree with each filter that the caller gives.
<!-- id: SDD-RT-14 | tdd: TDD-12.4 -->

- Behavior: The filters are the state, a latest due date, a tag, a text in the path, an excluded text in the path and a text in the line. With no state filter the reader returns the lines that are not done and not cancelled.
- On failure: A date that is not a valid date in the form YYYY-MM-DD gives status 2.
- Verified by: The unit test filters by tag and due date, by state and by two excluded paths, and gives an invalid date.

**RT-15.** When the caller gives sort keys and a limit, the archive reader MUST sort the lines first and then apply the limit.
<!-- id: SDD-RT-15 | tdd: TDD-12.4 -->

- Behavior: A sort key is one of the dates, the priority or the path, and the keys apply in the order given. The highest priority comes first, a line with no date comes last, and a limit of zero returns no line.
- On failure: A limit that is negative or is not a number gives status 2.
- Verified by: The unit test sorts by due date and priority with a limit of 4, sorts by priority and due date, and gives two invalid limits.

**RT-16.** Each role conversation MUST have a web fetch tool that returns the readable text of one public web page.
<!-- id: SDD-RT-16 | tdd: TDD-12.6 -->

- Actor: A role in a Pi conversation. The web fetch tool needs no key.
- Behavior: For an HTML page the tool returns the title and the text with no scripts, styles or markup; for other text types it returns the body. The result also gives the final address, the status, the content type and a mark when the text is cut.
- On failure: A page that is not text and a page with an HTTP error status give an error with the reason.
- Verified by: The check script of the tool uses a fake resolver and a fake fetch for a page, a binary reply and a missing page; a unit test runs the script.
- Limits: The text has 12000 characters by default and 40000 at most. The tool reads at most 2 MB and waits 20 seconds for one request.

**RT-17.** The web fetch tool MUST NOT read an address of the local machine, a private network or a link-local network.
<!-- id: SDD-RT-17 | tdd: TDD-12.5 -->

- Behavior: The tool examines each address that the host name resolves to, and one such address refuses the host. It also refuses the local host names, the carrier-grade NAT range and the multicast ranges.
- Verified by: The check script gives eleven refused addresses, three public addresses, a host that resolves to the local machine and a host with one private address.

**RT-18.** When a page redirects, the web fetch tool MUST apply its address rules to each redirect target.
<!-- id: SDD-RT-18 | tdd: TDD-12.5, TDD-12.6 -->

- Verified by: The check script has a redirect to a public page, a redirect to a host of the local machine and a redirect loop.
- Limits: The tool follows at most five redirects and gives an error for more.

**RT-19.** If an address has a scheme other than http or https, or holds credentials, then the web fetch tool MUST refuse it.
<!-- id: SDD-RT-19 | tdd: TDD-12.5 -->

- Behavior: Credentials are a user name or a password in the address. Text that is not an address is refused too.
- Verified by: The check script gives a file address, an address with a user name and a password, and text that is no address.

**RT-20.** Each role conversation MUST have a search tool that returns the title, the address and an excerpt of each web result.
<!-- id: SDD-RT-20 | tdd: TDD-12.7 -->

- Actor: A role in a Pi conversation, through the search tool.
- Behavior: The tool takes a query and optional filters for domains, recency and dates. It returns 5 results by default and 10 at most, with the dates of a result where the provider gives them.
- Verified by: The check script loads the tool through the extension loader of Pi. No test has a search that succeeds.
- Limits: A query has at most 4000 characters and an excerpt at most 6000. The tool reads at most 1 MB and waits 30 seconds.

**RT-21.** If the role conversation has no search key, then the search tool MUST refuse the call and name the protected launch.
<!-- id: SDD-RT-21 | tdd: TDD-12.7 -->

- Behavior: The key comes from the launch of the conversation, in the environment of the process only. The message says that the key is configured through the protected launch and not through the chat.
- Verified by: The check script calls the tool with no key and compares the message. The unit test of the launch shows the key in the environment of the process and its absence when no secret is handed in.

**RT-22.** If a search fails, then the search tool MUST give one fixed error message with no text from the provider.
<!-- id: SDD-RT-22 | tdd: TDD-12.7 -->

- Behavior: A failure is a refusal of the provider, a timeout, a cancelled call, a reply that is too large or a result that is not valid. A result whose address is not http or https makes the full search fail.
- Verified by: The check script calls the tool with a cancelled signal and compares the message.

**RT-23.** The search tool MUST NOT return the search key in a result.
<!-- id: SDD-RT-23 | tdd: TDD-12.7 -->

- Behavior: The tool replaces each copy of the key in the result text with a mark.
- Verified by: A fake provider that returns the key in an excerpt, with a result that holds the mark and not the key. This test does not exist today.

**RT-24.** When a seat asks for advice, the advice tool MUST send the question to the model that the model file names for advice.
<!-- id: SDD-RT-24 | tdd: TDD-12.8 -->

- Actor: A Pi seat or a headless worker that runs on the metered key of the model gateway, through the advice tool.
- Behavior: The tool reads the model file at each call, so a change applies to the next call. The answer ends with the name of the model and, when the provider reports it, the cost.
- Verified by: The check script of the seat extensions resolves the model and builds the request with no network call. The tests of the seat settings show that each seat and each headless worker loads the tool.
- Limits: A question has at most 4000 characters and its context at most 60000. The tool waits 180 seconds at most.

**RT-25.** If the seat has no gateway key or the model file names no advice model, then the advice tool MUST refuse the call.
<!-- id: SDD-RT-25 | tdd: TDD-12.8 -->

- Behavior: The error says which of the two is absent.
- Verified by: The check script calls the tool with no key. No test has a model file with no advice model.

**RT-26.** The advice tool MUST NOT use a subscription account.
<!-- id: SDD-RT-26 | tdd: TDD-12.8 -->

- Behavior: The call uses the same metered key that the seat runs on, so its cost is on that key. The model lookup asks for a gateway model and takes no model of the parent session.
- Verified by: The check script runs with no model file of the system or the user and gets a model of the gateway.

## SK. Skills and method
<!-- section: SDD-SK | sys: SYS-PL-11 -->

This part gives each agent the same working method in each client. A skill is one folder with one instruction file; the platform keeps each skill in the activated release and links it into the home of each user, so that one activation updates Claude Code, Codex and Pi together. The engineering method is a third-party skill set that the platform ports from an unchanged vendor copy with a small set of declared changes, so that the owner can take a newer vendor copy with one new port. A skill names a tier of model and not a product; one resolver turns a role into a model for the runtime at hand, so that one model file serves the owner and each agent. A bounded classifier answers closed questions at a low cost under one month limit, and a count of the owner's prompt verbs shows how frequently a prompt gives no object and no end state. The owner and each role use these parts; no part decides in place of the owner or of the agent.

The reasons:

- SK-01: One copy in the activated release keeps each client on the same skills after each activation.
- SK-02: One table gives a role the same skills in Claude Code, in Codex and in Pi.
- SK-04: Each agent starts each session with the same orientation: its purpose, its scope and its present assignment.
- SK-05: Each short word of the owner has one meaning for each agent on each machine.
- SK-08: The hooks of Claude Code come from the managed settings of the machine; each other client loads its guards from the home.
- SK-11: Some clients refuse a front matter that other clients accept, and the description is the only text that a client reads when it decides to load a skill.
- SK-12: The text of the vendor stays as written, so the owner takes a newer vendor copy with one new port and one read of the difference.
- SK-14: The vendor copy is never edited, and some vendor playbooks conflict with the source control tiers.
- SK-16: A skill keeps its own choice of strength and effort for each role, and the model file of the machine names the products.
- SK-18: One model file serves the owner and each agent in each client, so a caller names a role and not a product.
- SK-21: One file serves each user and each client of the machine, and a user changes one line with no copy of the file.
- SK-23: A panel and the two overseers of a rig get a second opinion from a second model family.
- SK-25: OpenRouter is the centre of the platform, and the subscriptions are the fallback for a client that runs only those.
- SK-27: The classifier classifies bounded questions; it does not plan, write, summarize or give permission.
- SK-29: Ordinary code routes on the typed answer, so the answer has no free text.
- SK-30: The classifier runs under one small monthly cap, so that no hook and no loop spends without notice.
- SK-32: Each identity of the machine can ask the classifier without sight of the key.
- SK-33: A desktop client on a second machine asks the same schemas through one remote command.
- SK-34: The count measures the words of the owner, so that the owner can give each frequent word one meaning.
- SK-39: The removal of a worktree stays a step that a person approves.
- SK-41: Copied code that nothing calls is not kept in the platform; the vendor copy and the Git history hold it.

**SK-01.** When the owner equips a home with no role, the equip command MUST link each platform skill into each skill folder of that home.
<!-- id: SDD-SK-01 | tdd: TDD-13.1 -->

- Actor: The owner, and the bootstrap of the machine for the home of each user.
- Behavior: `ai-guardrails install` makes one link for each skill of the release in the skill folders of Claude Code, of Codex and of the shared agents folder. Each link points into the activated release, and a platform link whose skill is gone from the release is removed.
- Observable: `ai-guardrails status` prints no line for a skill.
- Verified by: A test that equips a new home and compares the links with the skills of the release, and a test with a link of an old layout.

**SK-02.** Where the owner names a role, the equip command MUST link only the session entry and the skills of that role.
<!-- id: SDD-SK-02 | tdd: TDD-13.1 -->

- Behavior: The role table of the release gives the skills of each role, and the Pi sessions of the role load from the same table. A platform link of a skill that the role does not get is removed.
- Observable: The skill folders of the home hold the session entry and the row of the role, and no other platform skill.
- Verified by: A test that equips one home for each role and compares the folder names with the row of the table.
- Limits: The roles are `assistant`, `ops` and `engineer`.

**SK-03.** The equip command MUST NOT replace a file, a folder, a link or a setting that the platform did not make.
<!-- id: SDD-SK-03 | tdd: TDD-13.1, TDD-13.2, TDD-13.3 -->

- Behavior: A skill folder of the user, a link to a different place, Codex rules of the user, a Git hooks path of the user and a settings file that is not valid JSON stay as they are. In an instruction file, each line outside the marked block stays.
- On failure: The command prints one note on the error stream for each thing that it left alone, and exits with 0.
- Verified by: Tests with a skill folder of the user, a foreign link, a foreign hooks path and a line of the user in an instruction file.

**SK-04.** The equip command MUST write one marked block with the session entry into the global instruction file of each client.
<!-- id: SDD-SK-04 | tdd: TDD-13.2 -->

- Behavior: The block holds the session entry, the commit attribution rule, the session title rule and the words of the owner. Claude Code gets an include of the session entry; Codex and Pi get one line that tells the agent to read it at session start, on resume and on a change of task.
- Observable: The instruction file of Claude Code, of each Claude account folder, of Codex and of Pi holds one block between two marker lines.
- Verified by: Tests that read each instruction file after the install and count the markers after a second install.
- Limits: Pi gets the block only where the home holds a Pi agent folder. A second run replaces the block in place.

**SK-05.** The marked block MUST give each client the word list of the owner from one source file.
<!-- id: SDD-SK-05 | tdd: TDD-13.2 -->

- Behavior: Claude Code gets an include of the file in the release, so an activation updates the words. Codex and Pi have no include and get a copy of the text.
- Observable: After a change of the word list, `ai-guardrails status` reports the block of Codex and of Pi as out of date.
- Verified by: Tests that write the block for each client, count the words in each file, and change the source file.
- Limits: A release with no word list gives a block with no words.

**SK-06.** When the owner asks for the status of a home, the equip command MUST print one line for each missing or stale part.
<!-- id: SDD-SK-06 | tdd: TDD-13.4 -->

- Behavior: The parts are the skill links, the Codex rules link, the marked block of each instruction file, the Pi seat guard and the Git hooks path.
- Observable: `ai-guardrails status` prints nothing and exits with 0 for a full home, and exits with 1 when it prints a line.
- Verified by: Tests that read the status of a new home, of an equipped home and of a home with one part removed.
- Limits: The status does not examine the Codex sandbox mode or the session title hooks.

**SK-07.** When the equip command runs again on an unchanged release, it MUST change no file and no link of the home.
<!-- id: SDD-SK-07 | tdd: TDD-13.4 -->

- Behavior: Each step compares the present content with the wanted content and writes only on a difference.
- Verified by: A test that compares each file and each link of the home before and after a second install.

**SK-08.** The equip command MUST connect each guard and each title hook of the release to the client of the home that loads it.
<!-- id: SDD-SK-08 | tdd: TDD-13.3 -->

- Behavior: Codex gets a link to the command rules and the session title hook for four events, and Git gets the global hooks path of the release. Pi gets the seat guard in its extensions list and a copy of the session title extension, where the home holds a Pi agent folder.
- Verified by: Tests for the Codex hooks file, the Pi settings, the Pi extension, and the hooks path when it is not set, old or foreign.
- Limits: The other hooks, the other extensions and the other keys of each settings file stay. A hooks path or a link of an older platform release moves to the activated release.

**SK-09.** Where the Codex config of a home states no sandbox mode, the equip command MUST set the mode that limits writes to the workspace.
<!-- id: SDD-SK-09 | tdd: TDD-13.3 -->

- Behavior: The line goes at the top level of the config, before the first table. A mode inside a profile is not a top-level mode.
- Verified by: A test with a config that has a mode only in a profile, and a test with a config that states a mode.
- Limits: A config that states a top-level mode stays as it is.

**SK-10.** If the release folder holds no skills, then the equip command MUST exit with 1 and name the folder.
<!-- id: SDD-SK-10 | tdd: TDD-13.4 -->

- Behavior: `--release` names a release; with no option the command uses the activated release.
- On failure: The message goes to the error stream, and the command changes no file of the home.
- Verified by: A test that runs the command with a release folder that does not exist.

**SK-11.** Each skill MUST have a front matter that each client can read.
<!-- id: SDD-SK-11 | tdd: TDD-13.5 -->

- Behavior: The front matter opens on line 1, is closed, and is strict YAML. Its name is the name of the skill folder, and its description is not empty and not cut.
- Verified by: A test that parses the front matter of each tracked skill file with a strict YAML parser.
- Limits: The rule applies to each tracked skill file outside the vendor copy.

**SK-12.** The port MUST build each ported skill from the vendor copy and the overlay files, with only the declared changes.
<!-- id: SDD-SK-12 | tdd: TDD-13.6 -->

- Behavior: The declared changes are: the platform name of the front door skill, the folder name as the skill name, a tier slug for each model name, one line that points to the platform map, and the left-out paths. Each other file, a script included, is a byte copy.
- Observable: `pstack-port` prints the count of the skills that it wrote and the names of the parked skills, and writes the list of the ported skills.
- Verified by: A test that compares each ported skill with a new port, and a test that each ported skill points to the platform map.
- Limits: A parked skill is not ported. A skill that left the vendor copy loses its folder.

**SK-13.** If a skill differs from a new port, then the port check MUST exit with 1 and name that skill.
<!-- id: SDD-SK-13 | tdd: TDD-13.6 -->

- Behavior: `pstack-port --check` builds a port in a temporary folder and compares each file and the list of the ported skills. It changes no file.
- Observable: With no difference the check prints the count of the skills and exits with 0.
- Verified by: The port test, which the full check of the platform runs.

**SK-14.** Where an overlay holds a file of a vendor skill, the port MUST use the overlay file in place of the vendor file.
<!-- id: SDD-SK-14 | tdd: TDD-13.7 -->

- Behavior: An overlay replaces a full file, and the platform line of the skill says that the copy is adapted. The overlays hold the model setup skill and, for the engineering mode, seven playbooks, the worktree audit script and the package file of its scripts.
- Verified by: The port test, and a test that reads the model setup skill for the paths of the platform.
- Limits: Four playbooks are stubs that point to the development loop: Shipping, Babysit, Autopilot-full and Autopilot-stack. Three follow the tier of the repository: Opening a PR, Refactoring and Multi-phase plan.

**SK-15.** The vendor copy MUST state its source, its commit and its license.
<!-- id: SDD-SK-15 | tdd: TDD-13.6 -->

- Behavior: The port only reads the vendor copy.
- Verified by: A test that reads the license file and the commit line of the vendor copy.

**SK-16.** A ported skill MUST name a model only by a tier slug.
<!-- id: SDD-SK-16 | tdd: TDD-13.6 -->

- Behavior: The port replaces each model name of the vendor with a slug of the form `<tier>[.<n>]-<effort>`, for example `judgment-max` or `implementation-xhigh`.
- Verified by: A test that looks for a product name in each Markdown file of each ported skill.
- Limits: The model setup skill names example products, because it sorts the detected families into tiers.

**SK-17.** If a platform skill has the name of a new ported skill, then the port MUST stop and write no skill.
<!-- id: SDD-SK-17 | tdd: TDD-13.6 -->

- On failure: The port names the skill on the error stream.
- Verified by: A test with a platform skill that has the name of a vendor skill.

**SK-18.** When a caller names a role or a tier slug, the model resolver MUST print one model and one effort for the named runtime.
<!-- id: SDD-SK-18 | tdd: TDD-13.9 -->

- Actor: A skill, the loop, the role launcher, a Pi seat and the advice tool.
- Behavior: `pstack-model resolve '<role>' --runtime <name>` prints the model, a tab and the effort: the first family of the tier that the runtime can run. The effort is the last part of the slug (max, xhigh, high, medium, low) or empty.
- Verified by: Tests of the roles and the slugs for each runtime, of a panel role with `--all`, and of the two words for the parent model.
- Limits: A concrete model name passes through with no tier. With `--all` the resolver prints one line for each slug of the role line, and `inherit` stands for the model of the parent chat unless `--no-inherit` is given.

**SK-19.** The model resolver MUST print only a model that the named runtime can run.
<!-- id: SDD-SK-19 | tdd: TDD-13.9 -->

- Behavior: The Claude runtime runs only a Claude family, the Codex runtime only a Codex family, and the OpenRouter runtime only an OpenRouter family. The Pi runtime runs an OpenRouter family, a Pi provider and the OpenAI subscription, and never a Claude family.
- Verified by: Tests for each runtime, with a tier that holds only subscription families for the Pi runtime and for the OpenRouter runtime.
- Limits: With no named runtime, each family passes.

**SK-20.** If no model of the line runs on the named runtime, then the model resolver MUST print nothing and exit with 1.
<!-- id: SDD-SK-20 | tdd: TDD-13.9 -->

- Behavior: Before it stops, the resolver tries the default line of the role when the line of the owner gave no model.
- On failure: A caller, for example the start of a Pi seat, refuses to start and names the role.
- Verified by: A test with a Codex model for the Claude runtime, and a test with a parent word that the caller refuses.

**SK-21.** The model resolver MUST take each line from the user's file, else from the machine's file, else from the defaults.
<!-- id: SDD-SK-21 | tdd: TDD-13.8 -->

- Behavior: A line of the user's file replaces only the same tier line or role line. Each user of the machine reads the same machine file.
- Observable: `pstack-model source '<role>'` prints the file that states the line, or `default`.
- Verified by: Tests with a machine file, with a user file that replaces one line, with no file, and with a second user.

**SK-22.** If a line of a model file has a wrong form, then the model resolver MUST report it and ignore it.
<!-- id: SDD-SK-22 | tdd: TDD-13.8 -->

- Behavior: A line has the form `key: value`. An empty line and a comment line are permitted.
- On failure: The resolver prints the file and the line number on the error stream, and the other lines apply.
- Verified by: A test with a line that has no colon and a line that has no value.

**SK-23.** A tier slug with a family number MUST resolve to the family of that number among the families that the runtime runs.
<!-- id: SDD-SK-23 | tdd: TDD-13.9 -->

- Behavior: `judgment.2-max` is the second family of the judgment tier in the sequence of the tier line.
- Verified by: A test of a panel role for all runtimes and for the Claude runtime, and a test of the two overseer roles of a rig.
- Limits: When the runtime runs fewer families than the number, the count starts again at the first family.

**SK-24.** When the owner asks to show the model lines, the model resolver MUST print each line in force with its source file.
<!-- id: SDD-SK-24 | tdd: TDD-13.8 -->

- Behavior: `pstack-model show` prints each tier line and each role line, a tab, and the path of the file or `default`.
- Verified by: A test with one line in the machine file and one default line.

**SK-25.** Each tier of the default model file MUST list its OpenRouter families before the subscription families.
<!-- id: SDD-SK-25 | tdd: TDD-13.8 -->

- Behavior: Each role of the default file resolves for the Pi runtime and for the OpenRouter runtime. The model setup skill shows the same default file as `pstack-model defaults` prints.
- Verified by: Tests of the default tiers with no file, a test of each default role for the two runtimes, and a test that compares the setup skill with the defaults.
- Limits: The three start roles of the Pi roles name the OpenAI subscription and do not resolve for the OpenRouter runtime.

**SK-26.** Each tier slug that a ported skill names MUST resolve to a model with the default model file.
<!-- id: SDD-SK-26 | tdd: TDD-13.9 -->

- Behavior: The slugs come from the port. The default tiers are `judgment`, `implementation`, `mechanical` and `overseer`.
- Verified by: A test that collects each slug from the Markdown files of the ported skills and resolves it.

**SK-27.** Each classifier schema MUST hold only closed questions: a choice, a score or a probability.
<!-- id: SDD-SK-27 | tdd: TDD-13.10, TDD-13.12 -->

- Behavior: A choice and a score declare two or more options with unique identifiers. `ai-jev list` prints the schema names and `ai-jev show <schema>` prints one schema.
- On failure: A schema that breaks the form is refused with one message, and the command exits with 2.
- Verified by: A test that lists the schemas and loads each one.
- Limits: The schemas are `rank-context`, `verify-claim`, `classify-tool-risk`, `route-task`, `check-completion` and `detect-instruction-injection`.

**SK-28.** The classifier MUST send only the state of the caller and the closed questions of the schema to a provider.
<!-- id: SDD-SK-28 | tdd: TDD-13.10, TDD-13.12 -->

- Behavior: `ai-jev request <schema> --state <json>` prints the request: the state, the model name and the questions. The request holds no key and no free question.
- Verified by: A test that reads the printed request, and a test that reads the request that a stand-in provider received.

**SK-29.** If an answer of a provider is not complete or holds an undeclared value, then the classifier MUST refuse it and exit with 2.
<!-- id: SDD-SK-29 | tdd: TDD-13.10 -->

- Behavior: An answer has each declared question and no other, only declared options, and each confidence and probability from 0 to 1. A good answer is printed in one typed form: the schema, the model, the usage and the answers.
- Verified by: Tests with an undeclared choice, with an added answer, and with the score form and the probability form of a live provider.

**SK-30.** If the spend of the month has reached the limit, or the next call would pass it, then the classifier MUST make no paid call.
<!-- id: SDD-SK-30 | tdd: TDD-13.11 -->

- Behavior: The limit is 10 dollars for each month unless the config states a different one. The estimate of the next call comes from the size of the request.
- Observable: `ai-jev status` shows the spend, the limit, and the reason when live calls are off.
- On failure: The command prints the reason and exits with 2, and the caller continues with no answer of the classifier.
- Verified by: A test that sets the limit below the estimate of one call and reads the status.
- Limits: A fixture answer given with `--response` is not a paid call and stays available.

**SK-31.** When a paid call ends, the classifier MUST add its cost to the usage record of the month.
<!-- id: SDD-SK-31 | tdd: TDD-13.11 -->

- Behavior: The cost is the charge that the provider reports, else the token count of the request at the configured price. The record holds the count of calls, the input tokens and the last 200 events, and a new month starts a new record.
- Verified by: A test with a stand-in provider that reports a charge, which reads the record.

**SK-32.** The classifier MUST NOT print a key.
<!-- id: SDD-SK-32 | tdd: TDD-13.11 -->

- Behavior: The status shows only if a key is available, and an error of a provider reports only the status code. With the default provider the classifier holds no key: a local proxy of the machine adds it.
- Verified by: A test with a key in the environment that reads each output, and a test that reads the headers of a call through the default provider.
- Limits: `ai-jev import-key-from-env` stores nothing and exits with 2; the key store of the machine holds the key.

**SK-33.** Where a client starts the classifier as an MCP server, the classifier MUST offer one tool for each schema.
<!-- id: SDD-SK-33 | tdd: TDD-13.12 -->

- Behavior: `ai-jev mcp` serves on standard input and standard output; a tool has the name of its schema with the prefix `jev_` and takes the state. A call goes to the default provider under the same month limit.
- On failure: A refused call comes back as an error result of the tool, and the server continues.
- Verified by: A test that sends the start message, the list request and one tool call.

**SK-34.** The verb count MUST count only the prompts that the owner typed.
<!-- id: SDD-SK-34 | tdd: TDD-13.13 -->

- Behavior: `ai-prompt-verbs` reads the local transcripts of Claude Code, Codex and Pi. A subagent thread, a tool result, a worker brief, a summary and a message of a different session are not prompts; a slash command counts with its arguments.
- Verified by: A test with transcripts of the three clients that hold each kind of row.
- Limits: A repeated text counts one time, and a prompt of more than 3,000 characters is a paste and is left out. With `--rows` the command counts rows that `--save` wrote earlier and reads no transcript.

**SK-35.** The verb count MUST print the share of prompts with a vague verb, with only vague verbs and with three words or less.
<!-- id: SDD-SK-35 | tdd: TDD-13.13 -->

- Behavior: A prompt has a verb when one of its word forms occurs as a word, after code, commands, paths and links are removed. The count uses no language model.
- Observable: The output is a table with the three shares and the most frequent verbs; `--json` gives the same data as JSON.
- Verified by: A test that counts a fixed set of prompts.

**SK-36.** Where the owner gives a project name or a time window, the verb count MUST count only the prompts inside them.
<!-- id: SDD-SK-36 | tdd: TDD-13.13 -->

- Behavior: `--project` keeps a session whose folder path holds the given text. `--since` and `--until` keep a prompt whose time stamp is in the window.
- Verified by: A test with a transcript of a second project, and a test with an end time.

**SK-37.** The decision log helper MUST append each decision as one row of a tab-separated file.
<!-- id: SDD-SK-37 | tdd: TDD-13.14 -->

- Actor: An agent that follows the show-me-your-work skill.
- Behavior: A row has a time stamp in UTC and five cells: phase, decision, why, evidence and result. The helper writes the header on first use and never truncates the file.
- On failure: With a wrong count of arguments the helper prints its usage and exits with 1.
- Verified by: A run of the helper with a cell that holds a tab and a cell that starts with `=`.
- Limits: A tab or a line break in a cell becomes a space. A cell that starts with `=`, `+`, `-` or `@` gets a quote mark in front, so that a spreadsheet does not read it as a formula.

**SK-38.** If a plan file breaks the plan form, then the plan check MUST print each fault with its line and exit with 1.
<!-- id: SDD-SK-38 | tdd: TDD-13.15 -->

- Actor: An agent that follows the Multi-phase plan playbook of the engineering mode.
- Behavior: The check reads one Markdown plan and examines its sections, the blocks of each pull request section, its check boxes and its punctuation. It prints one summary line for each pull request section.
- Observable: A fault has the form `file:line: message` on the error stream, and a plan with no fault gives the exit code 0.
- Verified by: A run of the check on a good plan and on a plan with a missing block.

**SK-39.** The worktree audit MUST print one row for each linked worktree with a proposed bucket.
<!-- id: SDD-SK-39 | tdd: TDD-13.15 -->

- Actor: An agent that follows the Worktree cleanup playbook of the engineering mode.
- Behavior: A row has the size, the age, the merge state, the uncommitted work, the remote state, the pull request, the last chat and the path. The audit deletes no worktree and changes no file of a worktree.
- Verified by: A run of the audit in a repository with one clean worktree and one changed worktree.
- Limits: The buckets are `hold-wip`, `hold-open-pr`, `verify-recent-chat`, `safe` and `review`. The platform copy reads file times on Linux and on macOS.

**SK-40.** The orchestration command MUST keep the state of one orchestrated program as plain files in one store folder.
<!-- id: SDD-SK-40 | tdd: TDD-13.16 -->

- Actor: The coordinator and the workers of the Orchestrate playbook of the engineering mode.
- Behavior: The store holds the work units, the verification records, the inbox pointers, the decision gates, the standing orders and the frontier. One process writes at a time: a lock file names the holder, and `--force` takes the lock.
- Observable: `orch status` writes a status file and prints a summary, and `--json` prints full rows.
- On failure: A usage fault or a store fault gives the exit code 1, and a record that is not found gives 2.
- Verified by: The vendor tests of the store and of the command, which run with `bun test`.
- Limits: `orch frontier set` needs the `gt` command, which the platform does not install.

**SK-41.** Where the port lists a path of a vendor skill as left out, the port MUST NOT copy that path.
<!-- id: SDD-SK-41 | tdd: TDD-13.6 -->

- Behavior: The left-out list is one of the declared changes of the port. It holds the pull request watcher of the engineering mode, which no playbook of this platform calls.
- Observable: The port check passes while the path is absent from the ported skill and present in the vendor copy.
- On failure: If the vendor copy does not hold a left-out path, the port stops with an error and writes no skill.
- Verified by: A test that looks for each left-out path in the vendor copy, in the ported skill and in the text of each file of the ported skill.

**MA-48.** Where a role has a role file in the active release, the owner home MUST hold a Claude Code agent link to that file.
<!-- id: SDD-MA-48 | tdd: TDD-14.28 -->

- Behavior: The link lets the owner start a main session in a role with `claude --agent` and the role name. The link goes through the link `current`. The install of the guardrails for the owner makes the links.
- Observable: The status of the guardrails lists each agent link that is missing or wrong. The environment doctor lists each broken agent link and each role with no link.
- On failure: A file or a link of another origin with the name of the link stays, and the install reports it.
- Verified by: Guardrails tests of a new owner home, of a home with a file and a link of its own and a link of a removed role, and of a role home. A doctor test with a missing and a broken link.
- Limits: Only a role with a role file gets a link. A role home gets no agent links. The install removes only a platform link to a role file that is gone.

## ST. Specification tree
<!-- section: SDD-ST | sys: SYS-PL-09 -->

A specification tree joins the levels of a project's specification, from the top to the unit tests. The words: a *project* is one tree, of one repository or of a group of repositories with one top document. The *config* is the one file of a project that tells the compiler where each level is and how the tests run. A *layout* is how a repository keeps its SDD and TDD. A *computed status* comes from the files that exist and the kept test results; a *declared status* is written by hand in a trace comment. A *fault* is a break of the structure; a *measure* is a count that fails nothing.

**ST-01.** A specification tree must have these levels, in this order: an optional top document, the SDD, the TDD, and the code paths and test paths that the TDD items name.
<!-- id: SDD-ST-01 | tdd: TDD-1.6 | status: implemented -->

- Behavior: a tree with no top document starts at the sections of the SDD. A tree with a top document starts at its requirements.
- Observable: the page and the JSON output show each level below the level that names it.
- Verified by: a test that compiles one fixture with a top document and one with none.

**ST-02.** The compiler must read each of these layouts of a repository's SDD and TDD: `single`, `domains` and `sections`.
<!-- id: SDD-ST-02 | tdd: TDD-1.2 | status: implemented -->

- Behavior: the config names the layout and the folder of each repository. An item is found by its identifier line and its trace comment, in the form that the layout defines. `single` is one `SDD.md` and one `TDD.md`; `domains` is one folder for each domain; `sections` is one file for each section.
- On failure: a file of the specification folder that holds no item and no section heading is listed as a fault.
- Verified by: one fixture for each layout.

**ST-03.** The compiler must connect each SDD item to each TDD item that names it, and each TDD item to each code path and each test path that it names.
<!-- id: SDD-ST-03 | tdd: TDD-1.3 | status: implemented -->

- Behavior: a link is read from the two sides (`tdd:` of the SDD item, `implements:` of the TDD item). A path can carry a symbol (`path#Symbol`); the compiler looks for the symbol in the file.
- On failure: these are faults: a link to an identifier that does not exist; an identifier that occurs two times; a trace comment whose identifier is not the identifier of its line.
- Observable: a named path that does not exist, and a symbol that is not in its file, are shown at the item.
- Observable: a link that only one side states is listed as a measure. A link to a table row of the specification that has an identifier, for example an acceptance row, is shown at the item as text; a table row is no level of the tree.
- Verified by: fixtures with one fault of each kind, one link of one side and one table row.

**ST-04.** Where a config names a top document, the compiler must connect each requirement of the top document to the SDD items that its trace comment names.
<!-- id: SDD-ST-04 | tdd: TDD-1.5 | status: implemented -->

- Behavior: a trace comment names one item, a pattern of identifiers, one domain, one section, or one area of a capability catalogue. Each domain folder and each section of each repository has exactly one owner requirement.
- Behavior: a capability catalogue is the file `capability-catalog.json` beside the specification of a repository. It puts SDD items into areas. A requirement that defines a domain can own areas with the field `areas:`; each area has one owner at most.
- On failure: these are faults: a name that matches no item; a domain or a section with two owners. A domain or a section with no owner, and a requirement that names `none`, are listed as gaps.
- Verified by: a fixture with each case.

**ST-05.** The compiler MUST give each TDD item exactly one computed status, and each SDD item the worst status of its TDD items.
<!-- id: SDD-ST-05 | tdd: TDD-1.4 -->

- Behavior: the values, worst first: `failing` (a named test fails), `no TDD` (no TDD item names the SDD item), `no code` (the TDD item names no path that exists), `no test` (code exists; no test path with a test case is named), `test not run` (a test is named; no valid result is kept for it), `proved` (each named test has a result and passes).
- Behavior: a named test path is a support file when a valid result holds no case of it and its file name is no test name. A named folder is a support folder when a valid result holds no case below it and no file in it has a test name. A support path is no test: it does not hold an item at `test not run`.
- Behavior: an item owns each support path that it names. A named support path is no gap. An item that names only support paths as its tests has the status `no test`.
- Observable: the page shows the status at each item and the count of each status for each repository. The page lists each named support path as a measure.
- Verified by: a fixture with one item of each status, a fixture with a support file, and a fixture with a support folder.

**ST-06.** The compiler MUST NOT write to a file that a repository tracks.
<!-- id: SDD-ST-06 | tdd: TDD-1.7 -->

- Behavior: the compiler writes only the page and the JSON tree in the folder of ST-11, and the files of its own state folder and its own worktree. It writes no status into a document.
- Verified by: a test that compares each tracked file of the fixture before and after a compile.

**ST-07.** Where a trace comment holds a declared status, the page must show it beside the computed status and must list each item where the two disagree.
<!-- id: SDD-ST-07 | tdd: TDD-1.4 | status: implemented -->

- Behavior: the two disagree when the declared status is `implemented` and the computed status is not `proved`, or when the declared status names a gap (`pending`, `deviation`, `unverified`) and the computed status is `proved`.
- Observable: one list, "Declared and computed status differ", with the item, the two values, and the task or issue that the marker cites.
- Verified by: a fixture with each case.

**ST-08.** When an operator compiles a tree, the compiler MUST use only kept test results and run no test.
<!-- id: SDD-ST-08 | tdd: TDD-1.8 -->

- Behavior: `dev-spec test` runs the test command of each repository and keeps the result with the revision that it ran on. The result is a JUnit report in the state folder of the platform, with the revision and the count of uncommitted paths. One test run at a time for each repository.
- Behavior: where a pipeline ran the tests already, the test command takes the JUnit file of that run, keeps it as the result of the present revision and runs no test.
- Limits: a compile from kept results takes less than 30 seconds for a tree of 1,000 SDD items.
- Verified by: a test with a fixture repository and a small test command, and a test with a JUnit file.

**ST-09.** The compiler must use a kept test result only when it is valid for the compiled revision.
<!-- id: SDD-ST-09 | tdd: TDD-1.8 | status: implemented -->

- Behavior: a result is valid when its revision is the compiled revision, or when no file outside the specification folders differs between the two revisions. If not, each named test has the status `test not run`.
- Observable: the head of the page shows the compiled revision, the revision of the test result, and if the result is valid.
- Verified by: a fixture with a result for the same revision, for a revision that differs only in the specification, and for a revision that differs in code.

**ST-10.** The compiler must compile one exact revision of each repository, and it must not change the checkout or the worktree of a session.
<!-- id: SDD-ST-10 | tdd: TDD-1.9 | status: implemented -->

- Behavior: the config gives the source of each repository. `checkout`: the primary checkout as it is, with the count of its uncommitted paths in the head of the page. A ref (for example `origin/develop`): the compiler keeps one detached worktree at `<repository>/.claude/worktrees/spec-tree`, fetches the ref and moves only that worktree.
- Behavior: the compiler makes no commit, no branch and no push in any repository.
- Verified by: a test with a fixture repository that has a second branch and a dirty checkout.

**ST-11.** When an operator compiles a project, the compiler MUST write one page and one data file into the Git folder of the project's repository.
<!-- id: SDD-ST-11 | tdd: TDD-1.7 -->

- Behavior: the page is `tree.html` and the data file is `tree.data.json`. Their folder is the folder of the platform inside the Git folder of the repository, where no commit and no tool of the repository reads. Each worktree of the repository shares that folder. For a project with more than one repository, the repository is the one that holds the system requirements.
- Behavior: the record can name a different folder in the field `page`, for example for a job of a pipeline. A folder in a working tree gets its own ignore file from the compiler, so that no commit holds the page and no file of the repository names the platform.
- Observable: the command prints the path of the page. For a folder in a working tree it prints one line of caution: a formatter or a check of the repository can read that folder.
- Behavior: the page is one file with one embedded style sheet, no script and no external file. The parts of the page, in this order: the contents; the summary (for each repository its source, its revision, its uncommitted paths and its test result, then the counts); the faults; the gaps; the status differences; the top document, where the project has one; the specification of each repository; the measures; the files that no TDD item names.
- Behavior: the specification part holds the full text: each section with its own text, each SDD item with its full text, and below it each TDD item that implements it, with its full text, its code paths and its test results. A section with no item shows its text. Each item shows its identifier, its status, its file and its line.
- Behavior: the same revisions, config and kept results give the same page, byte for byte. The page holds no clock time.
- Verified by: a test that compiles one fixture two times and compares the files, and a test of each place of the page.

**ST-12.** `dev-spec check <project>` must exit with a failure when the tree has a fault, and it must not fail because of a measure or a gap.
<!-- id: SDD-ST-12 | tdd: TDD-1.10 | status: implemented -->

- Observable: each fault is one line: `file:line: problem`.
- Verified by: fixtures with a fault, with a gap only, and with a measure only.

**ST-13.** The compiler must measure the form of each SDD item and must refuse nothing because of the form.
<!-- id: SDD-ST-13 | tdd: TDD-1.3 | status: implemented -->

- Behavior: the measures of an item: its requirement sentence has "must" or "must not" (in any case of letters); the count of code names; the count of words; the count of each word that the config lists for the repository (`flag_words`).
- Observable: the page lists the items of each measure, worst first, and the totals for each repository.
- Verified by: a fixture with items that break each measure.

**ST-14.** The page must list each tracked code file and each tracked test file that no TDD item names.
<!-- id: SDD-ST-14 | tdd: TDD-1.4 | status: implemented -->

- Behavior: the config gives the file endings that are code and the folders that are not counted. A folder that a TDD item names owns each file in it.
- Verified by: a fixture with one owned file, one owned folder and one file with no owner.

**ST-15.** The compiler MUST read each setting of a project from the one project record of that project.
<!-- id: SDD-ST-15 | tdd: TDD-1.1 -->

- Behavior: the record is one file with the name of the project, in the projects folder of the platform, outside each repository (PJ-01). `dev-spec` accepts the project name, or the path of a record with `--config`. A command with no name uses the record whose repository holds the folder of the command.
- On failure: a record with an unknown field, a missing field or a path that does not exist stops the compile with one line for each problem.
- Verified by: tests for each kind of record problem.

**ST-16.** The platform MUST hold the only copy of the compiler.
<!-- id: SDD-ST-16 | tdd: TDD-1.10 -->

- Behavior: `dev-spec` is a command of the platform release. It uses the Python standard library only. A repository of a project holds its specification and its top document; it holds no file of the compiler and no config (PJ-02).
- Verified by: the release check lists `dev-spec`; a test runs it with an isolated Python environment.

**ST-17.** Where an operator asks for the proof gate, the check MUST fail when an SDD item is not proved and names no gap.
<!-- id: SDD-ST-17 | tdd: TDD-1.10 -->

- Behavior: the plain check fails only on a fault of the tree (ST-12). The proof gate is the option of a pipeline that must show a tree with each item proved. An item with a gap that names its task does not stop the gate.
- Observable: one line for each item that stops the gate, with its file, its line and its status, and the count.
- Verified by: a fixture with an item that fails, and a fixture with one proved item and one gap.

**ST-18.** When an operator exports the tool, the copy MUST NOT hold a name of the platform.
<!-- id: SDD-ST-18 | tdd: TDD-1.11 -->

- Behavior: the copy is for a repository that owns its tool, so that its pipeline needs no platform. It is one command file, the module files and a manifest with the hash of each file. The command, the module, the schema, the variables and the folders get one neutral name. The copy has no export command.
- On failure: the export writes nothing when a file of the copy would hold a name of the platform.
- Verified by: a test that exports a copy, looks for each name, and compiles a fixture with the copy.

## SP. Specification standard
<!-- section: SDD-SP | sys: SYS-PL-09 -->

One form for the specification of each project. This area is written in the form that it defines; the older areas of this document change to it in their own step. The owner approved the sentences on 2026-11-17 in the words of this area, with one requirement in each sentence.

**SP-01.** Each project MUST keep its specification in three levels: the system requirements, the SDD and the TDD.
<!-- id: SDD-SP-01 | tdd: none | gap: #33 -->

- Behavior: the system requirements say what the whole system is and does. The SDD says what the software of one repository does. The TDD says how that software is built. The code and its unit tests are the proof.
- Verified by: a tree with the three levels compiles with no fault.

**SP-02.** Where a project has more than one repository, the project MUST keep its system requirements in one document, `SYSTEM.md`.
<!-- id: SDD-SP-02 | tdd: TDD-2.3 -->

- Behavior: the document can also define the domains, the features and the rules that more than one repository carries.
- Verified by: a fixture with two repositories and one `SYSTEM.md`.

**SP-03.** Where a project has one repository, the first chapter of its SDD MUST hold its system requirements.
<!-- id: SDD-SP-03 | tdd: TDD-2.3 -->

- Behavior: the chapter holds only `SYS-` items. It has no domains, no features and no catalogue.
- Verified by: a fixture with one repository and a first chapter of `SYS-` items.

**SP-04.** Each section of an SDD MUST name exactly one system requirement as its owner.
<!-- id: SDD-SP-04 | tdd: TDD-2.3 -->

- Behavior: the comment below the section heading has the field `sys:`. One SDD item can name more system requirements in its own trace comment.
- On failure: a section with no owner, and a name of no system requirement, are faults of the tree.
- Verified by: fixtures with an owner, with no owner and with an unknown owner.

**SP-05.** An SDD MUST hold requirements only.
<!-- id: SDD-SP-05 | tdd: none | gap: #33 -->

- Behavior: an SDD holds no design, no decision, no status, no history and no list of what the system does not do. Design goes to the TDD. The reason of a change goes to the commit message.
- Behavior: the first line of each SDD file is fixed: "This is a requirements specification. It holds no design and no decision."
- Verified by: the check of the first line, and the rules SP-09 to SP-13.

**SP-06.** A TDD item MUST NOT state a behavior that no SDD item requires.
<!-- id: SDD-SP-06 | tdd: none | gap: #33 -->

- Behavior: when the design needs a new behavior, the SDD changes first.
- Verified by: a TDD item that implements no SDD item is listed on the page.

**SP-07.** Each requirement MUST be one sentence in one EARS pattern, with `MUST` or `MUST NOT` one time.
<!-- id: SDD-SP-07 | tdd: TDD-2.1 -->

- Behavior: the patterns are: always (the system `MUST`); event (When); state (While); unwanted condition (If, then); option (Where).
- Verified by: a fixture with a sentence of each pattern and with each fault.

**SP-08.** A requirement sentence MUST have 25 words or less.
<!-- id: SDD-SP-08 | tdd: TDD-2.1 -->

- Behavior: a longer rule is cut into more requirements, or its conditions move to the parts of the item.
- Verified by: a fixture with a sentence of 25 words and one of 26 words.

**SP-09.** A specification file MUST NOT hold `MUST` or `MUST NOT` outside a requirement sentence.
<!-- id: SDD-SP-09 | tdd: TDD-2.1 -->

- Behavior: only the capitals make a requirement. Text in lower case is description. A word inside code marks is a name and is not counted.
- Verified by: a fixture with the word in a part of an item.

**SP-10.** An SDD item MUST use only these parts below its sentence: Actor, Behavior, Observable, On failure, Verified by, Limits.
<!-- id: SDD-SP-10 | tdd: TDD-2.1 -->

- Behavior: each part is optional, except Verified by.
- Verified by: a fixture with an unknown part, with text outside a part and with no Verified by.

**SP-11.** An SDD item MUST NOT name a part of the implementation.
<!-- id: SDD-SP-11 | tdd: TDD-2.1 -->

- Behavior: a file, a function, a table, a migration and a page are parts of the implementation. A name that a user or a second system uses is allowed; the tree config lists these names in `interface_names`.
- Verified by: a fixture with a code name and with a listed interface name.

**SP-12.** An identifier MUST name its level, its area and a number.
<!-- id: SDD-SP-12 | tdd: TDD-2.1 -->

- Behavior: `SYS-ID-01`, `SDD-CX-02`, `TDD-2.3.2`. An identifier holds no number of a decision, a prompt or a task.
- Verified by: a fixture with an identifier of each form.

**SP-13.** A specification file MUST NOT hold a status.
<!-- id: SDD-SP-13 | tdd: TDD-2.1 -->

- Behavior: the compiler gives the status. A trace comment holds the identifier and the links only.
- Verified by: a fixture with a status in a trace comment.

**SP-14.** Where an item has a known gap, its trace comment MUST cite the task or the issue that carries the work.
<!-- id: SDD-SP-14 | tdd: TDD-2.1 -->

- Behavior: the field is `gap: #N`. The compiler reports a gap whose named tests all pass.
- Verified by: a fixture with a gap over a failing test and over a passing test.

**SP-15.** Each specification file MUST use ASD-STE100 with the glossary of its project.
<!-- id: SDD-SP-15 | tdd: none | gap: #33 -->

- Observable: the check counts the words that are not approved and not in the glossary. This count is a measure.
- Verified by: a fixture with a word that is not approved.

**SP-16.** Each project MUST have one project record in the platform.
<!-- id: SDD-SP-16 | tdd: none | gap: #33 -->

- Behavior: the record names each repository of the project and the settings of its specification. The registry fields `tree=` and `spec=` go away.
- Verified by: a test that finds a project by its record.

**SP-17.** When a commit adds or changes an item, the commit hook MUST refuse an item that breaks SP-07 to SP-14.
<!-- id: SDD-SP-17 | tdd: TDD-2.2 | gap: #33 -->

- Behavior: an item that the commit does not touch is measured and not refused.
- Observable: each refusal is one line with the file, the line, the identifier, the rule and the reason.
- Verified by: a fixture where a commit changes one of two items that break a rule.

<!-- retired: SDD-SP-18 -->

**SP-19.** A project MUST NOT hold a decision record or an amendment ledger for its specification.
<!-- id: SDD-SP-19 | tdd: none | gap: #33 -->

- Behavior: only the owner's word changes a requirement. The change edits the exact sentence, and Git records it.
- Verified by: the hook test of a decision record.

**SP-20.** Where a project turns the lock on, each section MUST carry a lock comment with the hash of its text.
<!-- id: SDD-SP-20 | tdd: none | gap: #33 -->

- Behavior: `dev-spec lock` stamps the hashes, and `dev-spec check` fails when a locked section differs from its hash.
- Verified by: a fixture with a locked section that changed.

**SP-21.** An identifier MUST NOT change after an item cites it.
<!-- id: SDD-SP-21 | tdd: none | gap: #33 -->

- Behavior: a new item gets a new number. A removed item's number is not used again.
- Verified by: a fixture where a cited identifier is gone at the new revision.

**SP-22.** Each guard of the platform MUST read the layout of a project from its tree config.
<!-- id: SDD-SP-22 | tdd: none | gap: #33 -->

- Behavior: the layouts are `single`, `sections` and `domains`, and each uses the item form of this area.
- Verified by: the guard tests with a config of each layout.

## PJ. Project record
<!-- section: SDD-PJ | sys: SYS-PL-10 -->

A repository does not depend on the platform, and the platform needs no file inside a repository. Each part of the platform is optional for a project. The owner approved this area on 2026-11-17.

**PJ-01.** The platform MUST keep each setting of a project in one project record outside each repository.
<!-- id: SDD-PJ-01 | tdd: TDD-3.5, TDD-3.7, TDD-3.9 -->

- Behavior: the record holds the Git settings (tier, mode, base, forge, kept branches, slots), the work settings (tracker, task form, decisions, incoming), the check command with its environment, the specification settings and the place of the page. A project is one repository or a group of repositories.
- Behavior: the registry file and the check environment files stay, because the hooks, the loop and the menu read them. A command makes them from the records. A person changes the record and not the file. The layout of the specification in the record gives the layout field of the registry.
- Observable: the command shows each file that differs from the records, and it can exit with a failure for that.
- Verified by: a test that makes the registry from the records and reads the same settings as before; a test that runs the check command of a record.

**PJ-02.** Where a project is not native, the platform MUST NOT read a setting of the project from a tracked file of a repository.
<!-- id: SDD-PJ-02 | tdd: TDD-3.5, TDD-1.11 -->

- Behavior: a native project owns its tool and its config. Its record names one config file of the repository in the field `config`. That file is then the one source of the specification settings; the platform reads it at the revision that the compiler reads, and its values take the place of the values of the record.
- Verified by: a test that puts a config file into a repository and shows that no command reads it; a test with a record that names the config of the repository.

**PJ-03.** A project record MUST state which parts of the platform are on for the project.
<!-- id: SDD-PJ-03 | tdd: TDD-3.8 -->

- Behavior: the parts are: the Git rules, the full check, the tree, the control of the specification, the loop, the team. The record lists the parts that are on in the field `parts`. A record with no list has each part on; the control is then on only where the field `control` says so.
- Behavior: a person or an agent can change the list. The sync command shows the change before it writes the registry.
- Verified by: a test with a record with no list, and a test with a list.

**PJ-04.** Where a part is off for a project, the platform MUST NOT act on that project through that part.
<!-- id: SDD-PJ-04 | tdd: TDD-3.8, TDD-8.6 -->

- Behavior: with the Git rules off, the Git hooks and the guard apply no rule of the project to that repository. With the full check off, a stop runs no check. With the tree off, the compiler refuses the project. With the loop off, only the read verbs of the loop work. With the team off, no seat starts in the project.
- Limits: the rules that protect the worktree of a second session and the hooks of the platform are rules of the machine. No part turns them off.
- Verified by: a test where the Git rules are off and a hook refuses nothing, and a test of each other part.

**PJ-05.** When the owner connects a folder, the platform MUST write the record and change no tracked file of the repository.
<!-- id: SDD-PJ-05 | tdd: TDD-3.11 -->

- Behavior: the command proposes the tier, the check command and the specification paths that it finds; the owner confirms each value.
- Verified by: a test that compares the tracked files before and after.

**PJ-06.** The platform MUST hide each file that it writes in a checkout with no change of a tracked file.
<!-- id: SDD-PJ-06 | tdd: TDD-1.7, TDD-8.9 -->

- Behavior: the means are the local exclude file of the repository, for each worktree of the platform, and an own ignore file inside a folder of the platform, for a page folder in a working tree (ST-11). The default page folder is inside the Git folder and needs neither.
- Verified by: a test that shows a clean status after a compile.

**PJ-07.** When a session starts in a connected folder, the platform MUST tell the agent the parts that are on and their rules.
<!-- id: SDD-PJ-07 | tdd: TDD-3.12 | gap: #34 -->

- Behavior: the text comes from the record and from the documents of the platform. The instructions of the repository do not hold it.
- Verified by: a test of the session start hook with a record.

**PJ-08.** Each command of the platform MUST run from the platform release.
<!-- id: SDD-PJ-08 | tdd: TDD-14.5, TDD-14.13 -->

- Behavior: No command, script or hook of the platform is a file of a repository. Each command is a file of the active release and loads its code from that release.
- Observable: The link `current` of the shared folder shows the release that runs. The hook settings name each hook through that link.
- Verified by: the tests of the menu restart, of the stale skill links and of the shell form of the release place; no test lists each command of a release.
- Limits: A command that a person starts from the development checkout runs from that checkout.

**PJ-09.** Where a folder has no project record, each read command MUST accept the settings as arguments.
<!-- id: SDD-PJ-09 | tdd: TDD-3.13 -->

- Behavior: a command works on any repository. On a connected project it needs only the project name.
- Verified by: a test that compiles a tree with arguments only.

**PJ-10.** Where a record names a side folder, the platform MUST read and write the specification of the project in that folder only.
<!-- id: SDD-PJ-10 | tdd: TDD-3.10, TDD-3.11 -->

- Behavior: this is for a repository that is not ours, a ghost project. The SDD and the TDD are in the side folder, which is the rig folder of the project. The code paths and the test paths of the TDD items are in the checkout. The repository gets no file of the specification.
- Behavior: a command works on the side folder when it runs in the checkout or in the side folder. The control of the specification holds in the side folder. The side folder is the top folder of its own Git repository.
- Behavior: with the tracker `side`, the task files of the project are in the side folder also. The loop and the forge read them there, a fold marks a task done there with one commit of that folder, and the repository gets no task file. The landing of such a project is local: this version opens no pull request for it.
- On failure: a side folder that does not exist, or that is a folder below the top of a repository, stops the command with one line.
- Verified by: a test that compiles a tree from a side folder and a checkout, a test that writes through a command in the checkout, a test of the control in the side folder, and a test that folds a task of the side folder.

## SW. Specification writes
<!-- section: SDD-SW | sys: SYS-PL-09 -->

No agent edits a file of the system requirements, the SDD or the TDD. A command makes each change: it shows the related items, takes one answer for each, examines the form and verifies the whole tree. The owner approved this area on 2026-11-17.

**SW-01.** Where the control is on, an agent MUST NOT write to a file of the system requirements, the SDD or the TDD.
<!-- id: SDD-SW-01 | tdd: TDD-3.4 -->

- Behavior: each other document of the project is free. The record gives the paths of the three levels.
- Verified by: the guard test and the hook test of SW-11 and SW-12.

**SW-02.** `dev-spec` MUST make each change of a specification file for an agent, one change in each command.
<!-- id: SDD-SW-02 | tdd: TDD-3.2 -->

- Behavior: the write commands are `add`, `set`, `remove`, `link`, `unlink`, `bind`, `unbind`, `own`, `move`, `renumber` and `text`. `remove` also takes out an old text block that only a trace comment names. `own` sets the one owner of a section, or one more owner of one item. `text` changes the text of a section that is outside its items.
- Behavior: `remove` takes out a system requirement of the first chapter of the SDD only when no section and no SDD item names it. `remove` takes out a section only when the section holds no item, no section and no old text block. In the sections layout the file of the section leaves with its last line.
- Behavior: `renumber` gives a TDD item a different free number of its section, only while the base branch of the repository does not hold the item. It changes each place of the specification that names the item. It lists each other file that names the item and does not change it.
- Behavior: a command removes the status of each item that it changes. A status that cites a task stays as the gap.
- Limits: no command changes a top document that is a file of its own, and no command adds a system requirement or a section.
- Verified by: a test of each command on a fixture.

**SW-03.** When an agent proposes a change of an item, the command MUST show each related item with its text.
<!-- id: SDD-SW-03 | tdd: TDD-3.3 -->

- Behavior: the related items are: the items that a link connects to it; the SDD items that share one of its TDD items; the items before and after it in its section; the items with the most shared terms, of its own level and of the other level; the system requirement that owns its section.
- Limits: 2 items before and 2 after in the section; by shared terms, 5 items of its own level and 3 of the other level.
- Verified by: a fixture with one item of each kind of relation.

**SW-04.** A write command MUST refuse to write until the agent gives one answer for each related item.
<!-- id: SDD-SW-04 | tdd: TDD-3.3 -->

- Behavior: the answers are `same`, `change` and `conflict`. With a `conflict`, the command writes nothing and prints the two items for a question to the owner.
- Verified by: a test with a missing answer and with a conflict.

**SW-05.** While an item has the answer `change` and no later change, the commit hook MUST refuse a commit of the specification.
<!-- id: SDD-SW-05 | tdd: TDD-3.3, TDD-3.4 -->

- Behavior: `dev-spec open` lists these items. A `set` of the item, or the answer `same` for it in a later proposal, closes it. Each checkout has its own list, so that an open item of one session does not stop a session in a second worktree.
- Verified by: a test with one open item, and a test with a second worktree.

**SW-06.** If a change breaks the item form, then the command MUST refuse it and write nothing.
<!-- id: SDD-SW-06 | tdd: TDD-3.2 -->

- Behavior: the rules are SP-07 to SP-14.
- Verified by: a test with a sentence of 26 words.

**SW-07.** When a command writes a change, the command MUST compile the whole tree and undo a change that adds a fault.
<!-- id: SDD-SW-07 | tdd: TDD-3.2 -->

- Behavior: the command compares the faults before and after. A fault that existed before does not stop a change.
- Verified by: a test where a removal leaves a link to no item.

**SW-08.** When a command writes a link, the command MUST write the two sides of that link.
<!-- id: SDD-SW-08 | tdd: TDD-3.2 -->

- Verified by: a test of `link` and `unlink`.

**SW-09.** A command MUST give a new item the next number of its area that no item used before.
<!-- id: SDD-SW-09 | tdd: TDD-3.2 -->

- Behavior: `remove` records the identifier in a comment of the section, `<!-- retired: SDD-CX-07 -->`. This comment is a part of the document form.
- Behavior: when a section leaves, its comments leave with it. The command then records each identifier of these comments in the state of the platform, and a new item does not get such a number.
- Limits: the record of a removed section is in the state of one machine.
- Verified by: a test that removes the last item and adds a new one, and a test that removes a section and adds an item of its area.

**SW-10.** Each write command MUST record its change and the hash of each changed file in the state of the platform.
<!-- id: SDD-SW-10 | tdd: TDD-3.2 -->

- Behavior: the write commands of one project run one at a time, so that each proposal gets its own number.
- Verified by: a test that reads the record after a change.

**SW-11.** When a commit changes a specification file, the commit hook MUST refuse a content that no command recorded.
<!-- id: SDD-SW-11 | tdd: TDD-3.4 -->

- Behavior: the hook compares the hash of each staged specification file with the records.
- Verified by: a test with a direct edit and with a command edit.

**SW-12.** The harness guard MUST refuse a direct write of an agent to a specification file, and name the command to use.
<!-- id: SDD-SW-12 | tdd: TDD-3.4 -->

- Behavior: the guard examines the edit tools and the shell commands that write a file.
- Verified by: the guard tests of each harness.

**SW-13.** Where the owner confirms a hand edit in a terminal, the commit hook MUST accept it when the form and the tree hold.
<!-- id: SDD-SW-13 | tdd: TDD-3.4 -->

- Behavior: `dev-spec accept` runs only in a terminal. It records the present content as the edit of the owner, after the checks of SW-06 and SW-07 for each changed item.
- Verified by: a test with a terminal and with none.

**SW-14.** `dev-spec why` MUST print the chain of an identifier or a path, from the system requirement to the tests.
<!-- id: SDD-SW-14 | tdd: TDD-3.1 -->

- Behavior: for a code file or a test file, the chain starts at the TDD items that name it. A file that no TDD item names gets that answer.
- Verified by: a test with an SDD item, a TDD item, a code path and a file with no owner.

**SW-15.** `dev-spec find` MUST list the items that match a text, in the order of the sections.
<!-- id: SDD-SW-15 | tdd: TDD-3.1 -->

- Behavior: the match uses the words of the text, with no model. Each line shows the identifier, the sentence, the file and the line.
- Verified by: a test with two items that share a term.

## RL. Release and machine
<!-- section: SDD-RL | sys: SYS-PL-12 -->

This area says where the platform is on a machine and how a version of it starts to run. One install serves the owner and each agent user of the machine, so the platform is in one shared folder, and each command, hook and skill runs from the one release that the owner activated. A release is the files of one commit: a copy of a working tree, or a release that a person edits in place, can run code that no commit records, so the release command builds from a commit and reports each difference. The owner uses one menu command for daily work, and the menu gives the terminal to the command that owns each job. The diagnostic command only reads, and the menu uses its report as the health gate before it starts a team or opens panels. The check command proves the platform offline, with no account and no paid service of the machine.

The reasons:

- RL-01: What runs is exactly what the commit holds; a copy of a working tree can hold a change that no commit records.
- RL-02: Each user of the machine runs the platform through this one link.
- RL-05: A release that no longer agrees with its commit is a copy of a dirty tree or was edited in place.
- RL-07: Only the owner of a release writes in it; the checks of the root user refuse a release that a group can write.
- RL-09: With one mirror, each user verifies against the same repository.
- RL-10: One install serves the owner and each agent user of the machine, so it cannot be in the home folder of one user.
- RL-11: The tests and a second machine move the places in this way.
- RL-13: A health gate that changes the machine cannot be run at each moment without risk.
- RL-17: The skills that an agent gets are those of the install, not those of the branch that the checkout has at that moment.
- RL-18: A link into a different release keeps an agent on skills that the active release replaced.
- RL-20: The checks protect the shared OpenRig install and the workspace that the menu depends on.
- RL-22: Each OpenRig seat inherits the environment of the terminal server, so an override there reaches each new seat.
- RL-23: The classifier runs under one small monthly limit.
- RL-27: The regression suite is offline, and it does not spend a paid classifier call through a hook.
- RL-28: The tests need the isolation that the check command gives, so the report comes from the same command.
- RL-29: An active release is an archive of a commit and not a repository.
- RL-30: One command is sufficient for daily work, and each tool keeps its own interface.
- RL-31: The command that owns a job does that job; the menu adds no second way.
- RL-37: A menu that stays open across an update runs the old code, and its layout rules conflict with the new rules.
- RL-38: A command that the menu starts sees what a plain terminal gives.
- RL-41: The diagnostic command is the one health gate before a team starts.
- RL-42: OpenRig writes files into the folder of a seat; in a repository they show in the Git status.
- RL-43: The record stays correct when the checkout gets a new name.
- RL-44: One space for each team prevents a new space for each open of a seat.
- RL-46: OpenRig launches again only a seat whose terminal is gone.
- RL-47: The land of a goal is the step of the owner.
- RL-49: No command of the platform starts a role alone: the role command needs the login folder that the launcher of the server gives.
- RL-50: A machine with no launcher cannot start a role, so the entry is not shown.
- PJ-08: A repository does not depend on the platform, and the platform needs no file inside a repository.

**RL-01.** When the owner activates a commit, the release command MUST build the release from the files of that commit only.
<!-- id: SDD-RL-01 | tdd: TDD-14.1 -->

- Actor: The owner, or the root user on a machine with more than one user.
- Behavior: `ai-release activate <ref>` accepts a commit, a branch or a tag and resolves it to one commit. A change of the working tree that has no commit does not go into the release.
- Observable: The release is one folder of the releases folder in the shared folder, with the full identifier of the commit as its name. The command prints a JSON report with the state, the commit and the folder.
- Verified by: a test that changes a file with no commit, activates `HEAD` and reads the committed text, the executable bit and the link in the release.

**RL-02.** When a build agrees with its commit, the release command MUST make it the active release in one atomic step.
<!-- id: SDD-RL-02 | tdd: TDD-14.2 -->

- Behavior: The link `current` of the shared folder names the folder of the active release. The command makes a new link and moves it on top of the old link, so that no moment has no active release.
- Observable: `readlink` of the link `current` shows the commit. An activation of an earlier commit is the way back to an earlier release.
- Verified by: a test that reads the link after an activation; no test proves that the step is atomic.

**RL-03.** If the given name is not a commit of the repository, then the release command MUST change nothing and exit with a failure.
<!-- id: SDD-RL-03 | tdd: TDD-14.2 -->

- On failure: The command prints one line on the error output that names the ref and the repository. The exit code is 1.
- Verified by: a test that activates a branch that does not exist and finds no active release.

**RL-04.** If a release folder of the commit exists and differs from the commit, then the release command MUST NOT activate it.
<!-- id: SDD-RL-04 | tdd: TDD-14.2 -->

- Behavior: The command uses a release folder that exists again only after the comparison with its commit. The active release stays as it is.
- On failure: The message names at most ten files that differ and tells the owner to move the folder aside. The exit code is 1.
- Verified by: a test that edits a file of an inactive release and activates its commit again.

**RL-05.** The release check MUST report each tracked file of the active release that differs from its commit or is absent.
<!-- id: SDD-RL-05 | tdd: TDD-14.3, TDD-14.7 -->

- Behavior: `ai-release verify` compares the content and the kind (file or link) of each file that the commit tracks. A file that the commit does not track, for example the link to the Pi runtime, is not a difference.
- Observable: The JSON report has the state `ok` or `broken`, the lists `changed` and `missing`, and one line with the repair. The exit code is 0 only for `ok`; the diagnostic command shows the same result.
- Verified by: a test that edits one file, deletes one file, replaces a link with a folder and adds one folder that the commit does not track.

**RL-06.** If the release check cannot compare the release with its commit, then it MUST report a state that is not `ok`.
<!-- id: SDD-RL-06 | tdd: TDD-14.3, TDD-14.7 -->

- Behavior: The state is `missing` when no release is active, and `unsupported` when the platform folder is not a release folder. The state is `unverified` when Git or the commit is not available in the repository.
- Verified by: tests of the three states: no active release, a checkout as the platform folder, and a repository folder that does not exist.

**RL-07.** A release MUST NOT hold a file or a folder that its group or other users can write.
<!-- id: SDD-RL-07 | tdd: TDD-14.1 -->

- Behavior: The build removes the write permission of the group and of other users from each file and each folder. An activation of a release that exists does this again.
- Verified by: a test that builds with an open file mask, opens two paths by hand and activates again.

**RL-08.** If the build of a release fails, then the release command MUST NOT leave a folder with the name of the commit.
<!-- id: SDD-RL-08 | tdd: TDD-14.1 -->

- Behavior: The build writes into a temporary folder of the releases folder. The folder gets the name of the commit only when the archive is complete.
- On failure: The message names the partial folder. The exit code is 1.
- Verified by: no test today; a test that stops the archive step is the proof that this item lacks.

**RL-09.** Where the shared folder holds a mirror of the repository, the release command MUST build and verify from that mirror.
<!-- id: SDD-RL-09 | tdd: TDD-14.2 -->

- Behavior: With no mirror, the command uses the checkout of the owner. The options `--checkout` and `--share` name other places.
- Verified by: the tests give both options; no test proves the selection of the mirror.

**RL-10.** The platform MUST keep its releases and its pinned runtimes in one shared folder outside the home folder of each user.
<!-- id: SDD-RL-10 | tdd: TDD-14.4 -->

- Behavior: The default is the folder /opt/dev-platform. It holds the releases, the link `current`, the pinned Pi runtime and the pinned OpenRig runtime; the checkout of the owner is for development only.
- Verified by: a test that reads the default places with an empty environment.

**RL-11.** Where an environment variable names a place of the platform, each command MUST use that place and not the default.
<!-- id: SDD-RL-11 | tdd: TDD-14.4 -->

- Behavior: The variables are `DEV_PLATFORM_SHARE`, `DEV_PLATFORM_HOME`, `DEV_PLATFORM_CHECKOUT`, `DEV_PLATFORM_TEAMS` and `DEV_PLATFORM_SEAT_BIN`. They name the shared folder, the active release, the checkout, the team folders and the seat programs.
- Verified by: a test that sets each of the first three variables and reads the places.

**RL-12.** Where the folder of the seat programs exists, the platform MUST put it first in the command path of the OpenRig daemon.
<!-- id: SDD-RL-12 | tdd: TDD-14.4 -->

- Behavior: The seat programs start a seat through the launcher, on a resolved account. Each seat inherits the command path of the daemon; no other command path holds these programs.
- Verified by: a test with a folder that exists and a test with a folder that does not exist.

**RL-13.** The diagnostic command MUST NOT change a file, a setting or a service of the machine.
<!-- id: SDD-RL-13 | tdd: TDD-14.6 -->

- Behavior: `ai-env doctor` only reads. It installs nothing, restarts nothing and edits no config; the repair stays with the tool that owns each part.
- Verified by: a test that lists each path and each link of a home folder before and after a run.

**RL-14.** Each check of the diagnostic command MUST report exactly one state from a fixed list of seven states.
<!-- id: SDD-RL-14 | tdd: TDD-14.6 -->

- Behavior: The states are `ok`, `missing`, `stale`, `unavailable`, `unverified`, `unsupported` and `broken`.
- Observable: The command prints one line for each check: the section, the name and the state. With `--json` it prints one JSON object with sorted keys.
- Verified by: the tests of the diagnostic command read the states from the JSON report.
- Limits: The command exits with success for each report that it prints. The reader decides from the states.

**RL-15.** The diagnostic report MUST NOT hold the value of a credential or of an environment variable of a service.
<!-- id: SDD-RL-15 | tdd: TDD-14.6, TDD-14.9 -->

- Behavior: For the classifier the report holds the limits, the source of the credential and whether the credential is available. For the terminal server it holds the names of the override variables and not their values.
- Verified by: a test that puts a marker text into the config of the classifier and finds no marker in the report, and the test of the listing of the terminal server.

**RL-16.** The diagnostic command MUST report each necessary program that the command path does not hold as `missing`.
<!-- id: SDD-RL-16 | tdd: TDD-14.7 -->

- Behavior: The programs are `claude`, `codex`, `code`, `gh`, `git`, `jq`, `python3` and `ai-jev`. A second check reports whether the check command of the platform folder is an executable file.
- Verified by: a test with a command path that holds only `python3`.

**RL-17.** The diagnostic command MUST compare each skill folder of a home with the skills of the active release.
<!-- id: SDD-RL-17 | tdd: TDD-14.7 -->

- Behavior: The skill folders are the skill folder of Claude Code, the skill folder of Codex and the shared skill folder of the home. Before the first release the checkout gives the expected skills, and `--platform-root` names a different platform folder.
- Observable: A folder that lacks an expected skill has the state `missing`; an extra skill is not a fault. A broken link, or a client folder that gives a different file than the shared folder, has the state `broken`.
- Verified by: tests with an absent skill, an extra skill, a broken link, a shared folder that lacks a skill and a client folder that differs from the shared folder.

**RL-18.** If a skill link points into a release that is not active or into the checkout, then the diagnostic command MUST report it as `stale`.
<!-- id: SDD-RL-18 | tdd: TDD-14.7 -->

- Behavior: A link through the link `current` follows each activation. A skill that the owner publishes from a folder outside the releases is healthy.
- Observable: The report has the list `stale` and one line with the repair.
- Verified by: a test with links into an old release, into the checkout and through the link `current`.

**RL-19.** If a necessary instruction file is absent from the platform folder, then the diagnostic command MUST report the instruction files as `broken`.
<!-- id: SDD-RL-19 | tdd: TDD-14.8 -->

- Behavior: The files are the hook settings of Claude Code, the Codex rules, the guard hook, the session length hook, the role rules, the instructions of the project template and the guidance of the control, worker and overseer seats. A hook file that is not executable gives the same state.
- Observable: The report lists the absent files and the hook files that are not executable.
- Verified by: a test with each file present; the state `broken` has no assertion today.

**RL-20.** The diagnostic command MUST compare the version, the runtime, the settings and the workspace of OpenRig with the values that the platform pins.
<!-- id: SDD-RL-20 | tdd: TDD-14.8 -->

- Behavior: A different version gives `unsupported`. A setting with a different value gives `broken` and its name in the list `wrong`; an absent runtime or workspace gives `missing`.
- Verified by: a test with the pinned values and a test where each setting differs.
- Limits: The pinned OpenRig version is 0.6.10 and the pinned Node version is 24.14.0.

**RL-21.** If the herdr server does not run or needs a restart, then the diagnostic command MUST report the server as `broken`.
<!-- id: SDD-RL-21 | tdd: TDD-14.8 -->

- Behavior: The command also reports the herdr program, its config file and its socket.
- Verified by: a test with a server that runs and a test with a server that is stopped.

**RL-22.** If the environment of the terminal server holds a provider override, then the diagnostic command MUST name each such variable.
<!-- id: SDD-RL-22 | tdd: TDD-14.8 -->

- Behavior: A provider override is a variable whose name starts with `ANTHROPIC_`, `OPENCLAW_` or `CLAUDE_CODE_USE_`. The state is `broken` with one line of repair, and `unavailable` when no terminal server (`tmux`) runs.
- Verified by: a test that reads a listing with three overrides and three other lines.

**RL-23.** If the monthly limit of the classifier is more than 10 US dollars or is not valid, then the diagnostic command MUST report `broken`.
<!-- id: SDD-RL-23 | tdd: TDD-14.9 -->

- Behavior: The command reads the config of the classifier (Jev) and the usage record of the user. It also reports whether the credential is available and whether the spend of the month is below the limit.
- Verified by: a test with a limit of 10 dollars and a test with a limit one unit above it.

**RL-24.** The check command of the platform MUST run each unit test of the platform.
<!-- id: SDD-RL-24 | tdd: TDD-14.10 -->

- Behavior: The command finds each test file of the tests folder and runs it. A test that fails makes the command exit with a failure.
- Verified by: A test runs the check command in a release folder with two test files, and again with one failed test.

**RL-25.** The check command MUST examine the syntax of each shell script of the platform before it runs a test.
<!-- id: SDD-RL-25 | tdd: TDD-14.10 -->

- Behavior: The scripts are each file with the shell script ending, the GitHub wrapper of the loop and `new-repo`. A syntax fault stops the command.
- Verified by: A test runs the check command with a syntax fault in a shell script and in the GitHub wrapper, and sees that no test runs.

**RL-26.** If a necessary tool is absent, then the check command MUST name the tool and exit with code 2.
<!-- id: SDD-RL-26 | tdd: TDD-14.10 -->

- Behavior: The tools are `bash`, `git`, `python3`, `jq` and the Python package PyYAML.
- Verified by: A test runs the check command with no jq and with a Python that has no PyYAML.

**RL-27.** While the check command runs, a test MUST NOT use an account, a credential or a paid service of the machine.
<!-- id: SDD-RL-27 | tdd: TDD-14.10 -->

- Behavior: The command gives the tests a fixed account list and names places that do not exist for the account register and the saved selection. It turns the credential helper and the paid classifier call of the hooks off.
- Verified by: A test reads the environment of a test that the check command runs, also when the caller sets other values; the tests of the accounts pass with no account of the machine.
- Limits: One test module that runs alone gets the credential guard from the test package, not the other guards.

**RL-28.** Where the owner names a report file, the check command MUST write the test results to it as one JUnit report.
<!-- id: SDD-RL-28 | tdd: TDD-14.10 -->

- Behavior: The report variable of the check command names the file. The tests and their environment are the same as with no report.
- Observable: The specification tree reads the report as the kept test results.
- Verified by: A test runs the check command with a named report file and reads the result of each test in the report.

**RL-29.** The check command MUST run in a release folder that has no Git data.
<!-- id: SDD-RL-29 | tdd: TDD-14.10 -->

- Behavior: In a checkout the command takes the list of shell scripts from Git. In a release it searches the folder and leaves the packages of the Pi runtime out.
- Observable: The diagnostic command reports whether the check command of the platform folder is an executable file.
- Verified by: A test runs the check command in a folder that has no Git data, with a script of the Pi packages that has a syntax fault.

**RL-30.** The platform MUST give one menu command that reaches each journal entry, project, session, role, team, machine part and account of the machine.
<!-- id: SDD-RL-30 | tdd: TDD-14.12, TDD-14.42 -->

- Actor: The owner at a terminal.
- Behavior: The home screen of `ai` shows the journal entries first: write, tasks, inbox, chat and search. Then it shows the projects, a new project and the recent sessions, then the roles and the teams, then the dashboard, the machine, and the accounts and setup.
- Behavior: The project of the current folder comes first where the folder is a project. The project menu shows the specification and loop entries only where the loop is on, and the role entry only for a registered project.
- Verified by: Tests that give scripted answers to each menu and read the command that the entry starts, and a test that compares the full list of home entries.

**RL-31.** When the owner opens an entry, the menu MUST give the terminal to its command and return when the command exits.
<!-- id: SDD-RL-31 | tdd: TDD-14.12, TDD-14.14, TDD-14.17 -->

- Behavior: Each entry starts a command of the same platform folder as the menu, or a program of the machine such as `tmux`, `herdr`, `git`, `code`, the role launcher `agent` or a command of the machine layer. The menu keeps no data of its own between two runs.
- On failure: When a command fails or cannot start, its output stays on the screen until the owner presses a key.
- Verified by: tests that read the exact command of the entries for clients, sessions, roles, teams, the loop, tasks, accounts and the machine layer.
- Limits: The menu changes files itself in two cases: it writes the repository record of a team folder, and it moves a taken inbox file to the inbox archive. It also sends the layout of a team space to herdr directly.

**RL-32.** Each list of the menu MUST accept the arrow keys to move, Enter to open and Escape to go back.
<!-- id: SDD-RL-32 | tdd: TDD-14.11 -->

- Behavior: Right also opens, Left also goes back, Page Up and Page Down move one page, and Ctrl+C quits. The selection goes from the last entry to the first entry and the reverse.
- Observable: Keys that arrive fast are read one at a time.
- Verified by: a test with scripted keys and a test that sends fast key sequences through a terminal pair.

**RL-33.** When the owner types text, the list MUST show only the entries that hold that text.
<!-- id: SDD-RL-33 | tdd: TDD-14.11 -->

- Behavior: The comparison ignores the case of the letters. Backspace removes one character, and Escape removes the full filter before it goes back.
- Verified by: tests of the filter with keys and with typed lines.

**RL-34.** Where the input is not a terminal, the menu MUST print numbered lists and read a number or a filter text.
<!-- id: SDD-RL-34 | tdd: TDD-14.11 -->

- Behavior: The list shows at most 30 entries. An empty line or `b` goes back, and `q` quits.
- On failure: A number that the list does not show gives one line with that number, and the menu asks again.
- Verified by: a test that filters, gives a number that is not shown and then gives a valid number.

**RL-35.** When the owner starts the menu with a text, the menu MUST open the one project whose name holds that text.
<!-- id: SDD-RL-35 | tdd: TDD-14.12 -->

- Behavior: When more than one project name holds the text, the menu shows the project list with that filter. The project list shows the project with the newest change first.
- Verified by: no test today.

**RL-36.** Where the dry run variable is set, the menu MUST print each command and start none.
<!-- id: SDD-RL-36 | tdd: TDD-14.12 -->

- Behavior: The variable is `AI_MENU_DRY_RUN=1`. A line that starts with `RUN` holds the command, the folder and the added variables; a line that starts with `HERDR` holds a request to herdr.
- Verified by: each test of the menu uses this mode and reads the lines.

**RL-37.** When the active release differs from the release of the open menu, the menu MUST restart from the active release at the home screen.
<!-- id: SDD-RL-37 | tdd: TDD-14.13 -->

- Behavior: The menu examines the active release each time it shows the home screen. A menu that starts from the checkout also restarts from the active release.
- Verified by: a test with a new release behind the link `current`, and a test with a menu that runs from the active release.
- Limits: The dry run does not restart.

**RL-38.** The menu MUST remove the marks of a client session from its environment before it starts a command.
<!-- id: SDD-RL-38 | tdd: TDD-14.12 -->

- Behavior: The marks are the variables that a Claude or Codex session sets for itself, and the Anthropic address variable only when it holds the default address. Each other provider override stays.
- Observable: The home screen names each provider override of the shell and says that a launch will refuse.
- Verified by: a test with the default address and a test with a different address; the line of the home screen has no test.

**RL-39.** When the owner opens a client in a project, the menu MUST list the accounts of that client with the most free quota first.
<!-- id: SDD-RL-39 | tdd: TDD-14.14 -->

- Behavior: An account that is exhausted or not verified comes last, and the first account with free quota has the mark `most room`. When the usage cannot be read, the menu lists the account names with an unknown state.
- Observable: The selected account goes to `ai-account run` with the client and the project folder.
- Verified by: a test with two accounts with different use, and a test with unknown usage windows.

**RL-40.** When the owner starts a new project, the menu MUST make a registered personal repository in the development folder.
<!-- id: SDD-RL-40 | tdd: TDD-14.14 -->

- Behavior: The menu asks for a name and a goal and runs `new-repo` with the options `--register` and `--personal`. With a goal, it opens a client with a request to write the specification with the intake skill, or the editor, and then the project menu.
- On failure: When the folder exists, the menu says so and starts no command.
- Verified by: tests of a new project with a client, with the editor and with an empty name.

**RL-41.** If the diagnostic report shows a fault of OpenRig, the instruction files or the terminal server, then the menu MUST NOT start a team.
<!-- id: SDD-RL-41 | tdd: TDD-14.15 -->

- Behavior: The menu reads the JSON report of the diagnostic command before it starts a team. The states `ok` and `unavailable` pass; a report that cannot be read stops the start.
- On failure: The menu names each part with its state and tells the owner to run `ai-env doctor`.
- Verified by: no test today; the dry run of the tests gives a healthy report.

**RL-42.** The menu MUST start the team of a project from a team folder outside the repository.
<!-- id: SDD-RL-42 | tdd: TDD-14.15 -->

- Behavior: The team has the name `engineer-<project>` and its folder is in the teams folder. Where the folder holds a team definition, the menu starts it; else the owner selects a shape and a runtime first.
- Observable: The menu asks before the start and then runs `dev-workspace start` with the team folder and the team name.
- Verified by: tests of a first start, of a start with a definition in the team folder and of a refused start.

**RL-43.** Where a team folder records a repository, the menu MUST use that team for the project of that repository.
<!-- id: SDD-RL-43 | tdd: TDD-14.15 -->

- Behavior: At the first start the menu writes the repository name into the file `project` of the team folder. A team with no record matches the project by its name.
- Verified by: a test that renames the checkout and finds the same team, and a test with a second repository.

**RL-44.** The menu MUST show a team in one herdr space that holds the team dashboard and one tile for each running agent.
<!-- id: SDD-RL-44 | tdd: TDD-14.16 -->

- Behavior: The space has the name of the team and one tab. A complete space is used again with no change; a space that lacks the dashboard or a running agent is closed and built again, and the spaces that OpenRig made for the team are closed.
- Verified by: tests of a new space, of a complete space and of a space that lacks an agent or has an older layout.
- Limits: A space is only a view: a closed tile, tab or space stops no agent. A stopped seat gets no tile.

**RL-45.** If herdr is not healthy or does not run, then the menu MUST attach the terminal to the session of the seat directly.
<!-- id: SDD-RL-45 | tdd: TDD-14.15, TDD-14.16 -->

- Behavior: Before it touches a space, the menu reads the diagnostic report for the herdr program, server, config and socket. Inside a `tmux` client it switches the client to the session; outside it attaches.
- Verified by: a test where herdr gives no answer and the menu attaches to the session of the seat.

**RL-46.** If an agent ended and left a bare shell in its seat, then the menu MUST show the seat as stopped.
<!-- id: SDD-RL-46 | tdd: TDD-14.15 -->

- Behavior: A seat is at a bare shell when the shell that the terminal server started is the only foreground process of its terminal. For a relaunch the menu closes that session, takes a snapshot of the team and launches the seat again.
- Verified by: a test with a seat at a bare shell and a test with an agent that runs below a wrapper script.

**RL-47.** The menu MUST ask the owner for a confirmation before it stops a team, lands a goal or deletes refs.
<!-- id: SDD-RL-47 | tdd: TDD-14.15, TDD-14.17 -->

- Behavior: The menu also asks before the start of a team and before the relaunch of a seat. Each answer that is not `y` or `yes` changes nothing.
- Verified by: tests that answer `n` and `y` to the land question and `y` to the relaunch question and the stop question.

**RL-48.** If the team of a project does not run, then the menu MUST NOT dispatch tasks as seats.
<!-- id: SDD-RL-48 | tdd: TDD-14.17 -->

- Behavior: The menu tells the owner to start the team first. With a team that runs, it asks for the number of workers (default 3) and refuses a value that is not a number of 1 or more.
- Verified by: a test with no team, with the default number, with the number 4 and with a word.

**RL-49.** When the owner opens a role entry, the menu MUST start the role through the launcher of the server.
<!-- id: SDD-RL-49 | tdd: TDD-14.14 -->

- Behavior: The menu runs `agent` with the name of the role and, for the project role, the folder of the project. The launcher asks for the harness and the account and selects the conversation.
- Verified by: a test that starts a role with no project and the project role with a project, and reads the command.
- Limits: The entry for the earlier Pi conversations of the roles is a list of the session index, and it does not start a role through the launcher.

**RL-50.** Where the launcher of the server is not on the command path, the menu MUST NOT show a role entry.
<!-- id: SDD-RL-50 | tdd: TDD-14.14 -->

- Behavior: The rule holds for the three role entries of the home screen and for the role entry of the project menu.
- Verified by: a test of the home screen and of the project menu with the launcher and with no launcher.

**RL-51.** Where the command of a machine entry is not on the command path, the menu MUST NOT show that entry.
<!-- id: SDD-RL-51 | tdd: TDD-14.42 -->

- Behavior: The machine entries are Write with `note`, Tasks with `tasks`, Inbox with `task`, Chat with `say`, Search everything with `recall`, Dashboard with `dash` and This machine with `ol-hold`. Inside This machine, each part also needs its own command.
- Observable: On a machine with no machine layer, the home screen is the same as the home screen of the platform alone.
- Verified by: A test that puts each machine command alone on a test path and reads the home screen, a test with no machine command, and a test of This machine with two commands present.

**RL-52.** When the owner opens a page entry of the write menu, the menu MUST start the note command with that day or that line.
<!-- id: SDD-RL-52 | tdd: TDD-14.42 -->

- Behavior: The entries open the page of today, the page of yesterday or an earlier page, or add one line to the page of today. The search of the journal runs `rg` in the pager.
- Verified by: A test that reads the commands `note`, `note yesterday` and `note` with a line.

**RL-53.** When the owner finishes or adds a journal task, the menu MUST start the tasks or task command with the number or the fields.
<!-- id: SDD-RL-53 | tdd: TDD-14.42 -->

- Behavior: The title of the tasks menu is the summary line of the tasks command. A new task asks for the text, the due date, the priority and the tags.
- Verified by: A test that reads `tasks done 1` and the full task command with a due date, a priority and two tags.

**RL-54.** When the owner takes a proposal of a role from the inbox, the menu MUST add it and move its file to the inbox archive.
<!-- id: SDD-RL-54 | tdd: TDD-14.42 -->

- Behavior: A task proposal becomes a task with its due date, priority and tags; a journal line goes to the page of the day where the note command is present.
- Verified by: A test that takes a proposed task, reads the task command and finds the file in the archive folder of the inbox.
- Limits: The menu deletes no file of the inbox: the file away action also moves the file to the archive.

**RL-55.** When the owner opens the chat, search or dashboard entry, the menu MUST start the say, recall or dash command.
<!-- id: SDD-RL-55 | tdd: TDD-14.42 -->

- Behavior: The chat entry gives the words of the owner to `say` and shows the last 200 lines of the chat file. The search entry gives the words to `recall` in the pager.
- Verified by: A test that reads the commands of the chat, search and dashboard entries.

**RL-56.** When the owner switches the rounds or the local model from the menu, the menu MUST start the hold command through sudo.
<!-- id: SDD-RL-56 | tdd: TDD-14.42 -->

- Behavior: The menu reads the hold files to show the state, and starts the hold command of the shared command folder, which the sudo rule allows. The other parts of This machine are the brief, the terminals, the screen, the services, the disk, the network, the snapshots and a test alert.
- Verified by: A test with a test hold folder that reads the hold command with `stream off`, and finds no entry for an absent command.

**RL-57.** Where the launcher of the server is present, the menu MUST list the earlier Pi conversations of the roles and resume the selected one.
<!-- id: SDD-RL-57 | tdd: TDD-14.42 -->

- Behavior: The list comes from the session index and holds only Pi sessions of a role. The menu resumes the selected session with `ai-session resume`.
- Verified by: A test that lists one role conversation in Pi, leaves out a Claude session of the owner and reads the resume command.

**RL-58.** When the owner drops a worker from the loop menu, the menu MUST ask first and then start the drop verb of the loop.
<!-- id: SDD-RL-58 | tdd: TDD-14.42 -->

- Verified by: A test that reads no command after the answer no and the drop verb with the task number after the answer yes.
