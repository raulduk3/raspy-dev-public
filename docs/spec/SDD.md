# Software Design Description

What the dev platform must do, stated as requirements a reader can verify.

## Document control

| Field               | Value                                                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Product             | dev-platform                                                                                                                |
| Scope               | Source control for agents (area SC), task items (area TK), the specification tree (area ST), the specification standard (area SP), the project record (area PJ) and specification writes (area SW). Other areas stay in [AI-ECOSYSTEM-SPEC.md](../AI-ECOSYSTEM-SPEC.md) until they move here. |
| Authority           | This document decides what the platform does in its areas. Where code and this document disagree, one is wrong; say which. |
| Companion documents | [TDD.md](TDD.md) states how each requirement of area ST is met; `tdd: none` marks an item with no TDD item yet. [SPEC-AMENDMENTS.md](SPEC-AMENDMENTS.md) holds the changes up to 2026-11-12. |
| Change control      | Only the owner's word changes a sentence. A change edits the exact lines. Git records the change. No decision record is written (SC-19). |

## Normative language

- "must" states a requirement.
- "must not" states a prohibition.

## Conventions

- Each requirement is one sentence on a `**XX-nn.**` line.
- A trace comment follows it: `<!-- id: SDD-XX-nn | tdd: TDD-x.y or none | status: ... -->`.
- Status is `implemented`, `pending:#N` or `deviation:#N`, where `#N` is a file in `docs/tasks/`.

## SC. Source control

Decision: 0001.

**SC-01.** Each registered repository must have one tier from 0 to 4 in `repos.conf`, and an unregistered repository must get the push and forge rules of tier 3.
<!-- id: SDD-SC-01 | tdd: none | status: pending:#7 -->

- Behavior: the registry line has `tier`, `base`, `forge`, `tracker` and `auth`. `personal.conf` is not read.
- Observable: `dev-loop tier <path>` prints the tier.
- Verified by: a test for each tier and for an unregistered path.

**SC-02.** Each agent must read the tier of the repository before its first change to a file.
<!-- id: SDD-SC-02 | tdd: none | status: pending:#9 -->

- Behavior: the session entry and the repository `AGENTS.md` tell the agent the tier and its rules.
- Verified by: the develop skill and the template `AGENTS.md` contain the rule.

**SC-03.** One goal must make at most one branch ref, and a tier 1 goal must make none.
<!-- id: SDD-SC-03 | tdd: none | status: pending:#13 -->

- Behavior: spec commits, folds and the land use the goal branch only.
- Observable: `git for-each-ref` shows one new ref for each open goal.
- Verified by: a loop test that counts refs from start to land.

**SC-04.** A worker must run in a detached slot from a fixed pool for the repository, and the loop must not make or remove a worktree for each task.
<!-- id: SDD-SC-04 | tdd: none | status: pending:#10 -->

- Behavior: slots are `.claude/worktrees/slot-1` to `slot-S`. Before a task, the loop runs `git switch --detach <goal-tip>` and `git clean -fdx` in the slot.
- Limits: S is 2, or 4 for acme-app and the Globex voice agent server.
- Verified by: a loop test that runs three tasks in two slots.

**SC-05.** A reader (reviewer, overseer, control seat, planner) must not get a checkout.
<!-- id: SDD-SC-05 | tdd: none | status: pending:#11 -->

- Behavior: readers use `git show`, `git diff` and `git grep` on the home repository.
- Verified by: `dev-workspace` makes no worktree for a reader seat.

**SC-06.** A worker that runs as another Unix user must use a `git clone --shared` of the home repository, not a full clone.
<!-- id: SDD-SC-06 | tdd: none | status: pending:#12 -->

- Observable: the clone has `.git/objects/info/alternates`.
- Verified by: a loop test with `LOOP_WORKER_AS`.

**SC-07.** A fold must add one squash commit for each task and must refuse a change outside the task scope.
<!-- id: SDD-SC-07 | tdd: none | status: pending:#13 -->

- Behavior: `git merge --squash <commit>` and one commit with an ASD-STE100 message.
- On failure: the fold names each file outside the scope.
- Verified by: a loop test with one task inside and one task outside its scope.

**SC-08.** The full check MUST run one time on each worker result, or one time on each batch where the goal is a forge.
<!-- id: SDD-SC-08 | tdd: none | gap: #16 -->

- Behavior: the fold checks only for conflicts and scope. In a forge, a worker runs the short proof of the profile, and the orchestrator runs the full check on the stacked batch before the fold. The land runs no second check on a tree that passed.
- Verified by: a loop test that counts check runs; the batch tests of the forge.

**SC-09.** The land must follow the tier.
<!-- id: SDD-SC-09 | tdd: none | status: pending:#8 -->

- Behavior: tier 1, the agent fast-forwards and pushes `main`. Tier 2, the owner runs `dev-loop land`. Tier 3, one push and one draft pull request with `Closes #N`.
- Verified by: a test for each tier.

**SC-10.** Distill MUST write its candidates to an incoming file that no repository tracks.
<!-- id: SDD-SC-10 | tdd: none | gap: #36 -->

- Behavior: the `incoming` field of the tier record sets the place of the file. The default, `state`, is one file for each repository in the state folder of the platform. With `project`, the file is in the docs folder of the main checkout, and git ignores it.
- Observable: `dev-loop tier <path>` prints the field and the place of the file.
- Verified by: a test of the tier record; no repository tracks an incoming file.

**SC-11.** Global git hooks must refuse a push of a protected ref, a force push, a push of a `wip/*` ref and a commit with an AI attribution trailer, for every local interface.
<!-- id: SDD-SC-11 | tdd: none | status: pending:#5 -->

- Behavior: `core.hooksPath` for owner and each persona points to the platform's `pre-push` and `commit-msg` hooks. The hooks read the tier.
- Verified by: a test that runs plain `git push` and `git commit` without an agent tool.

**SC-12.** The Claude, Codex and Pi guards must refuse a merge into a protected ref, a refspec push to a protected ref, a `gh api` merge, and the deletion of another session's branch or worktree.
<!-- id: SDD-SC-12 | tdd: none | status: pending:#2 -->

- Behavior: the guard matches command words, not text in quotes or search patterns. Codex gets the missing prefix rules (#3). The owner's Pi loads `seat-guard` (#4).
- Verified by: guard tests for each refusal and for a read-only `grep` that contains a refused phrase.

**SC-13.** A daily timer must remove merged refs and clean worktrees older than 7 days.
<!-- id: SDD-SC-13 | tdd: none | status: pending:#14 -->

- Behavior: a systemd user timer runs `dev-loop tidy --apply`. Refs go to a bundle first.
- Verified by: `systemctl --user list-timers` shows the timer.

**SC-14.** A desktop session branch must start with `wip/` and must not be pushed.
<!-- id: SDD-SC-14 | tdd: none | status: pending:#5 -->

- Behavior: the agent renames the branch to `type/slug` before a push.
- Verified by: the `pre-push` hook test in SC-11.

**SC-15.** A cloud agent must work only on a tier 2 or tier 3 GitHub repository, and the fold must take its result by commit ID.
<!-- id: SDD-SC-15 | tdd: none | status: pending:#22 -->

- Behavior: `dev-loop fold` fetches the cloud branch, folds its commit, then deletes the remote branch.
- Verified by: a loop test with a fake remote branch.

**SC-16.** The Zed agent must not write code in a registered repository.
<!-- id: SDD-SC-16 | tdd: none | status: pending:#23 -->

- Behavior: Zed writes go through Claude Code or Codex over ACP.
- Verified by: the Zed settings and `docs/zed.md`.

**SC-17.** Agents must write commit, pull request and issue text in ASD-STE100.
<!-- id: SDD-SC-17 | tdd: none | status: pending:#17 -->

- Behavior: the worker, control and reviewer guidance give the rule. The type prefix stays.
- Verified by: the guidance files contain the rule.

**SC-18.** The platform must have one development loop.
<!-- id: SDD-SC-18 | tdd: none | status: pending:#18 -->

- Behavior: Acme uses `dev-loop` with base `feat/example`. `factory-merge` and `factory-task` go away.
- Verified by: `~/.local/bin` has no `factory-*` file.

**SC-19.** Where a repository has `decisions=frozen`, an agent and a terminal MUST NOT add, change or delete a decision record, or add an amendment log.
<!-- id: SDD-SC-19 | tdd: none -->

- Behavior: `spec=single|domains` and `decisions=open|frozen` are fields of the tier record. The global `pre-commit` hook and `dev-loop fold` refuse the change. With `spec=domains`, a build task changes only the `status:`, `tests:` and `code:` lines of the items it cites. The `intake`, `distill`, `spec-lint` and `loop` skills read both fields and follow the agent instructions of the repository.
- Verified by: the pre-commit hook tests of the frozen mode, and the loop test of the frozen mode.

**SC-20.** Where a repository has `decisions=frozen`, intake MUST NOT change the specification.
<!-- id: SDD-SC-20 | tdd: none | gap: #36 -->

- Behavior: distill still writes candidates. The owner takes a candidate in by hand. Where the project has a specification tree, an agent uses the `dev-spec` write commands.
- Verified by: the intake skill says so.

**SC-21.** When intake promotes or rejects a candidate, intake MUST remove that candidate from the incoming file.
<!-- id: SDD-SC-21 | tdd: none | gap: #36 -->

- Behavior: intake reads a candidate by its identifier from the incoming file, so that the owner does not copy the block. The decision record or the log of the sources keeps the identifier.
- Verified by: the intake skill says so.

**SC-22.** If the full check fails on a batch, then the forge MUST fold only the tasks before the first task that fails.
<!-- id: SDD-SC-22 | tdd: none -->

- Behavior: the forge stacks one commit for each task on the goal tip, in a check folder that keeps its build output. It searches the first bad task in halves. It posts the failure with the log to the orchestrator. The later tasks stay for the next batch.
- Verified by: a batch test with a bad task in the middle.

**SC-23.** Where the profile of a forge names no full check, the forge MUST NOT fold a task.
<!-- id: SDD-SC-23 | tdd: TDD-3.9 -->

- Behavior: the forge stacks the batch and stops for the owner. The full check is the command that the profile states, or the check command of the project record that the profile names.
- Verified by: the batch test of a profile with no full check, and a test of a profile that names a project record.

**SC-24.** A forge MUST give each task to a worker with a new context.
<!-- id: SDD-SC-24 | tdd: none -->

- Behavior: the slot and the seat live for the goal; the context lives for one task. The worker brief holds the rules of the profile. The start of a worker is the only part that differs for each runtime: a headless run, a seat of a rig, or a start by hand.
- Verified by: the brief tests and the test of a start by hand.

**SC-25.** The machine MUST run at most the configured number of heavy commands of all forges at one time.
<!-- id: SDD-SC-25 | tdd: none -->

- Behavior: a command takes a place of the machine. Waiters stand in one line, and a later waiter does not pass an earlier one. A command waits for free memory before it starts.
- Verified by: a test that starts three commands on one place.

**SC-26.** While a running task shares a scope path with a ready task, the forge MUST NOT list the ready task as free.
<!-- id: SDD-SC-26 | tdd: none -->

- Behavior: the wide paths of the profile hold no task. A task with no scope is free only when no task runs.
- Verified by: the tests of the ready list.

**SC-27.** When a session posts a report, the forge MUST write the report as one file in the inbox of the reader.
<!-- id: SDD-SC-27 | tdd: none -->

- Behavior: a wait prints each new report and moves it to the read folder, which is the record. A report gives no permission and is never the owner's word.
- Verified by: the channel tests.

## TK. Task items

Decision: 0002.

**TK-01.** A repository with `tasks=json` on its `repos.conf` line must keep each task as one file `docs/tasks/<N>.json`, and a repository without it must keep its tracker unchanged.
<!-- id: SDD-TK-01 | tdd: none | status: implemented -->

- Behavior: `dev-loop tier <path>` prints `tasks=json` or `tasks=md`. Markdown task files, GitHub issues and repositories with no tracker work as before.
- Verified by: a test that reads one repository of each kind.

**TK-02.** Each JSON task must validate against `schemas/task/v1.schema.json`, and a task with an unknown field, a missing required field or a wrong type must fail the check.
<!-- id: SDD-TK-02 | tdd: none | status: implemented -->

- Behavior: the schema is JSON Schema 2020-12 with closed objects. An existing validator (`jsonschema` or `check-jsonschema`) runs it.
- Verified by: valid and invalid example tasks in the tests.

**TK-03.** Each task must have a `kind` from the list code, spec, research, ops, decision, writing and data, and the `work` fields of that kind must be present.
<!-- id: SDD-TK-03 | tdd: none | status: implemented -->

- Behavior: code and spec need `scope` (and may list `changes`); research needs `questions` and `deliverable`; ops needs `host`, `steps` and `rollback`; decision needs `question` and `options`; writing needs `destination` and `form`; data needs `source`, `target` and `transform`.
- Verified by: one valid and one invalid example for each kind.

**TK-04.** Each task must name a goal and must have one to eight acceptance checks, and each check must say how it is verified.
<!-- id: SDD-TK-04 | tdd: none | status: implemented -->

- Behavior: `by` is test, command, eval, review, artifact or host, and each has its own required fields (for example `run` for command, `metric`, `op` and `value` for eval).
- Verified by: examples with no goal, no check and nine checks fail.

**TK-05.** A JSON task must be done when a commit on the base has the trailer `Closes: #<N>`, and a JSON task must have no done field.
<!-- id: SDD-TK-05 | tdd: none | status: implemented -->

- Behavior: `fold` adds the trailers `Task: #<N>` and `Closes: #<N>` to its squash commit and does not move the file. `close --merge` moves no JSON task. A `Task: #<N>` trailer alone does not close a task.
- Verified by: a test that folds a JSON task and reads it as closed.

**TK-06.** The loop must give a task to an agent worker only when its state is ready, its kind is code or spec, and its assignee is not a person.
<!-- id: SDD-TK-06 | tdd: none | status: implemented -->

- Behavior: any other ready task gets the label `not-for-workers` and stays for a person.
- Verified by: a test with a ready decision task and a ready code task.

**TK-07.** `dev-loop` must read Markdown and JSON tasks in one repository and give both the shape that `gh issue list --json` gives.
<!-- id: SDD-TK-07 | tdd: none | status: implemented -->

- Behavior: a JSON task gets a body with `Scope:` and `Depends on:` lines, so plan, dispatch and fold read it as before.
- Verified by: a test with one task of each format.

**TK-08.** `dev-loop tasks <repo> view` must write the open tasks as an HTML table with no styles.
<!-- id: SDD-TK-08 | tdd: none | status: implemented -->

- Behavior: one row for each task with its number, title, kind, goal, state, depends and checks. No `style`, class or script.
- Verified by: a test that parses the output and finds no style.

**TK-09.** A repository must add its own task fields only under `ext`, with keys that start with `x-`.
<!-- id: SDD-TK-09 | tdd: none | status: implemented -->

- Behavior: `routing` carries lane, tier and model for the loop; anything else goes in `ext`.
- Verified by: an example with `ext.x-lane` passes and one with a top-level `lane` fails.

**TK-10.** `new-repo --personal` must register the repository with `tasks=json` and copy the schema and its check into it.
<!-- id: SDD-TK-10 | tdd: none | status: implemented -->

- Behavior: the template `scripts/check` validates every `docs/tasks/*.json` file. `dev-loop tasks <repo> new` writes a JSON task in such a repository.
- Verified by: a `new-repo` test.

**TK-11.** Each task must carry a `brief` that states the task in prose, and the loop must give the brief to the worker whole.
<!-- id: SDD-TK-11 | tdd: none | status: implemented -->

- Behavior: `brief` is required, up to 12000 characters, in the language the repository writes tasks in. The title keeps the repository's form, up to 140 characters. The worker's task body ends with the brief.
- Verified by: a task with no brief fails the schema; the body from `loop-tasks.py view` holds the brief.

## ST. Specification tree

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

A repository does not depend on the platform, and the platform needs no file inside a repository. Each part of the platform is optional for a project. The owner approved this area on 2026-11-17.

**PJ-01.** The platform MUST keep each setting of a project in one project record outside each repository.
<!-- id: SDD-PJ-01 | tdd: TDD-3.5, TDD-3.7, TDD-3.9 | gap: #34 -->

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
<!-- id: SDD-PJ-04 | tdd: TDD-3.8 -->

- Behavior: with the Git rules off, the Git hooks and the guard apply no rule of the project to that repository. With the full check off, a stop runs no check. With the tree off, the compiler refuses the project. With the loop off, only the read verbs of the loop work. With the team off, no seat starts in the project.
- Limits: the rules that protect the worktree of a second session and the hooks of the platform are rules of the machine. No part turns them off.
- Verified by: a test where the Git rules are off and a hook refuses nothing, and a test of each other part.

**PJ-05.** When the owner connects a folder, the platform MUST write the record and change no tracked file of the repository.
<!-- id: SDD-PJ-05 | tdd: none | gap: #34 -->

- Behavior: the command proposes the tier, the check command and the specification paths that it finds; the owner confirms each value.
- Verified by: a test that compares the tracked files before and after.

**PJ-06.** The platform MUST hide each file that it writes in a checkout with no change of a tracked file.
<!-- id: SDD-PJ-06 | tdd: TDD-1.7 | gap: #34 -->

- Behavior: the means are the local exclude file of the repository, for each worktree of the platform, and an own ignore file inside a folder of the platform, for a page folder in a working tree (ST-11). The default page folder is inside the Git folder and needs neither.
- Verified by: a test that shows a clean status after a compile.

**PJ-07.** When a session starts in a connected folder, the platform MUST tell the agent the parts that are on and their rules.
<!-- id: SDD-PJ-07 | tdd: none | gap: #34 -->

- Behavior: the text comes from the record and from the documents of the platform. The instructions of the repository do not hold it.
- Verified by: a test of the session start hook with a record.

**PJ-08.** Each command of the platform MUST run from the platform release.
<!-- id: SDD-PJ-08 | tdd: none | gap: #34 -->

- Behavior: no command, script or hook of the platform is a file of a repository.
- Verified by: the release check lists each command.

**PJ-09.** Where a folder has no project record, each read command MUST accept the settings as arguments.
<!-- id: SDD-PJ-09 | tdd: none | gap: #34 -->

- Behavior: a command works on any repository. On a connected project it needs only the project name.
- Verified by: a test that compiles a tree with arguments only.

**PJ-10.** Where a record names a side folder, the platform MUST read and write the specification of the project in that folder only.
<!-- id: SDD-PJ-10 | tdd: TDD-3.10 -->

- Behavior: this is for a repository that is not ours, a ghost project. The SDD and the TDD are in the side folder, which is the rig folder of the project. The code paths and the test paths of the TDD items are in the checkout. The repository gets no file of the specification.
- Behavior: a command works on the side folder when it runs in the checkout or in the side folder. The control of the specification holds in the side folder. The side folder is the top folder of its own Git repository.
- Behavior: with the tracker `side`, the task files of the project are in the side folder also. The loop and the forge read them there, a fold marks a task done there with one commit of that folder, and the repository gets no task file. The landing of such a project is local: this version opens no pull request for it.
- On failure: a side folder that does not exist, or that is a folder below the top of a repository, stops the command with one line.
- Verified by: a test that compiles a tree from a side folder and a checkout, a test that writes through a command in the checkout, a test of the control in the side folder, and a test that folds a task of the side folder.

## SW. Specification writes

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
<!-- id: SDD-SW-12 | tdd: TDD-3.4 | gap: #35 -->

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
