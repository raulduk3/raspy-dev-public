---
name: intake
description: >-
  Turn a goal, meeting notes, a transcript, an email or a `distill` candidate into
  specification changes that the owner accepts and implementable tasks. Works in local
  repositories (task files) and GitHub-backed ones (task issues). By default a repository
  keeps no decision record (`decisions=none`): intake asks the owner, then changes the
  specification. In a repository with `decisions=frozen` it changes no specification: it stops
  and points to distill, the owner's hand edit or the `dev-spec` write commands. With
  `decisions=open` it also drafts decision records. Use when asked to spec something out,
  plan work, or turn a request into tasks.
---

# intake

Turn one source into the records the loop needs: the specification lines that change, which the
owner accepts first, and tasks a worker can take without asking. Every task cites the
specification; every change cites its task. The specification is the one record of a
requirement. Git records each change, and the commit message gives the reason.

## Which backend

Resolve the repository through `ai-work projects` or the repository's line in
`~/.config/dev-platform/repos.conf` (`owner/repo checkout local|owner|bot [base] [key=value ...]`).
Read the tier with `dev-loop tier <path>`. Read the tracker from the line: `tracker=files` or `tracker=github`.

- **tracker=files** (the default for `local` mode): tasks are files under `docs/tasks/`, and
  nothing leaves the machine. `#N` means task N.
- **tracker=github**: tasks are GitHub issues written through
  `<loop skill>/scripts/ghx <owner/repo> issue create ...`, which picks the identity. `#N` means
  issue N. Use GitHub issues only for this tracker.
- Not listed: the `dev-loop` commands will refuse it. Propose the line
  (`<owner>/<name> <checkout> local <base> tier=2 tracker=files`) for the owner to add, or work with the files by hand
  in the same format.

Read the mode from the same record: `spec=single|domains` and `decisions=none|frozen|open`
(defaults `single` and `none`).

- `decisions=none`: the repository keeps no decision record. Use the **Procedure**. Never write,
  change or rename a file under `docs/decisions/`, and never add a `SPEC-AMENDMENTS.md`:
  the git pre-commit hook and the loop's fold refuse both. Files that are there are history.
  They do not override the current specification. Delete them only on the owner's word. Where the repository's `AGENTS.md` or
  `CONTRIBUTING.md` asks for a decision record or a ledger row, this rule wins: tell the owner.
- `decisions=frozen`: use **Frozen repository** below and not the Procedure. When the
  repository's `AGENTS.md` says that it uses direct specification edits, use Frozen repository
  too, and tell the owner that its `repos.conf` line has no `decisions=frozen`.
- `decisions=open`: use the Procedure with the additions of **Repository with decision records**.

Read the place of the candidates from the same record: `incoming_file` (SDD-SC-10). It is
`~/.local/state/dev-platform/incoming/<repo-name>.html`, or `docs/incoming.html` in the main
checkout when the line has `incoming=project`. Git ignores that file. Read and change it at that
path, also when you work in a worktree: a worktree does not have the ignored file.

## Frozen repository (`decisions=frozen`)

Intake changes no specification here (SDD-SC-20). This is the one difference from the default
mode. The specification is the only record of a
requirement, and only the owner changes it: by hand, or through an agent that uses the `dev-spec`
write commands where the project has a specification tree (a project record in `~/.config/dev-platform/projects/`). The
git pre-commit hook and the loop's fold refuse a change under `docs/decisions/` for every agent.

- Never edit a specification file, and never write, change, rename or delete a file under
  `docs/decisions/`. Old decisions are history. They do not override the current specification.
- Never draft a decision, a decision issue, a `kind: decision` task, an `open.tsv` row or a
  `SPEC-AMENDMENTS.md`.
- The repository's `AGENTS.md` is the contract for its checks and task format. Where it tells intake
  to edit the specification, this rule wins: tell the owner.

1. **Stop** when the source asks for a change of a requirement. Tell the owner in one or two
   sentences, and give the way that applies:
   - a raw record or many takeaways: run `distill`, which writes candidates to `incoming_file`;
   - one change: the owner changes the specification by hand, or, with a specification tree, the
     owner tells an agent to make the change with the `dev-spec` write commands.
2. **Tasks only.** After the owner changed the specification, or when the source names items that
   the specification already holds, intake may cut tasks for the gaps between the code and those
   items, as in Procedure step 6. Each task cites current IDs in `refs`. A build task changes only
   the `status:`, `tests:` and `code:` lines of the items it cites. Then run the checks that
   `AGENTS.md` names and `spec-lint`, and commit the tasks on the goal's branch.
3. **Candidates.** When the owner took a candidate in or rejected it, remove its block from
   `incoming_file` (SDD-SC-21) and add its ID to the commit message of the tasks.

A self-test of this mode: `dev-loop tier <path>` prints `decisions=frozen`. A plan that names a
path under `docs/decisions/` or a change of a specification file is wrong.

## Procedure

This is the procedure for `decisions=none`, the default.

1. **Source.** One of: the owner's goal in a sentence or a paragraph; meeting notes, a call
   transcript or an email; a candidate ID (`C-YYYY-MM-DD-n`): read its block from `incoming_file`,
   or take a block that the owner pasted (cite its id). Raw
   records stay in the owner's notes and are never copied into a repository. Refer to them by
   date and type only (`client call, 2026-09-17`); no quotes, no private names.
2. **Resolve current requirements.** Use the project's configured specification reader or
   project-local spec tool first, preserving native item IDs and format. With `spec=domains`, read
   the items through `docs/spec/index.json`. If none exists, fall back to `docs/spec/SDD.md` and
   `docs/spec/TDD.md`. Read open tasks with
   `dev-loop tasks <repo>` when the tracker is files and `ghx`/GitHub when the tracker is github.
   Then inspect only the code the TDD or spec-reader output names.
3. **Map** each takeaway. Already satisfied: nothing. Contradicted or left open: one question
   for the owner. An empty specification (a new repository) leaves everything open; the first
   answers write the first requirements, following the conventions at the top of `SDD.md` and
   `TDD.md`.
4. **Ask the owner.** For each open point give the context with the spec items quoted, the
   options, the consequences, a recommendation and the one question the owner answers. Ask in
   the conversation, and show the exact sentence that changes. Write no file for the question.
   Stop here until the owner answers. A goal the owner already stated plainly is the acceptance
   of that goal; a choice that the goal does not make is still a question.
   A question that waits for a person who is not in the conversation is a task for that person:
   a `kind: decision` task where the line has `tasks=json`, or an issue on the owner's word
   where the tracker is github.
5. **Specification change**, after acceptance, as the first commit on the goal's branch. At
   tier 2 or 3, run `dev-loop start <repo> <type/slug>` first, then commit the spec and the tasks
   in the rig worktree. At tier 1, commit on `main`. Make no separate `docs/<slug>` branch and no
   separate spec merge. Edit the exact SDD and TDD lines and set each touched status to
   `pending:#<task>`. Where the project has a specification tree with the control on, make each
   change with the `dev-spec` write commands. The commit message gives the reason of the change,
   the date of the owner's acceptance and the ID of each candidate. Write no decision record and
   no amendment ledger.
6. **Cut tasks** from the spec diff, dependency ordered, each small enough for one worker. Use the
   task backend chosen above; do not hand-write task records when the backend command can create
   and validate them.
   - files: `dev-loop tasks <repo> new "<title>" --scope <prefixes> --depends "#N"|none
     [--labels spec|enhancement|documentation] [--ready]`, run inside the rig worktree; it
     picks the number and writes the file in `docs/tasks/README.md` format. Replace the body
     with what to build, the acceptance criteria and the SDD/TDD items that govern it. Then
     `dev-loop tasks <repo> check` must report ok.
   - files with `tasks=json` on the `repos.conf` line (decision 0002 of the platform): add
     `--goal G-n`; the command writes `docs/tasks/<N>.json`. Write the `brief` as you would
     write the body of a Markdown task (what is true now, the change and why, in the
     repository's language for tasks), then the `work` scope and the `acceptance` checks, in
     place of each `TO WRITE:` line, add `refs` to the SDD/TDD items, and keep
     each check one statement with its `by`. A task that needs more than eight checks is two
     tasks. A decision, research, ops, writing or data task is a JSON task of that `kind`
     (write the file by hand from `docs/tasks/README.md`); the loop leaves it for a person.
   - github: issues through `ghx` with the same body plus `Scope:` and `Depends on:` lines, a
     milestone and `needs-triage`; the owner labels them `sprint-ready`.
   Fill the `pending:#<task>` markers with the numbers just assigned.
7. **Check** with `spec-lint` and any project-specific spec check on the branch.
8. **Clean the incoming file.** When a candidate is promoted or rejected, remove its block from
   `incoming_file` (SDD-SC-21). Write its id (`C-YYYY-MM-DD-n`) in the commit message of the
   specification change. Then hand over. The owner lands the goal's branch with the spec change
   as its first commit. With the github tracker, open one draft pull request.

## Repository with decision records (`decisions=open`)

Use the Procedure with these additions. Use this mode only where the line says `decisions=open`.

- Step 4: write each question as a decision draft also. With the files tracker it is
  `docs/decisions/NNNN-<slug>.md` from `0000-template.md`, with the next unused four-digit
  number and `Status: proposed`. With the github tracker it is a `decision` issue through `ghx`,
  on the owner's word. After the owner accepts, record `Status: accepted` and the date.
- Step 5: commit the decisions with the spec and the tasks. Set the decision's `Spec:` field,
  and append one row to `docs/spec/SPEC-AMENDMENTS.md` where the repository has that file.
- Step 6: add the decision to the `refs` of each task that depends on it.
- Step 8: write the candidate id in the decision record, and cite the decision issue in the
  draft pull request.

## Where it runs

The specification is decided before it is built. The spec change is the first commit on the
goal's branch, and the build tasks follow it on the same branch. A spec change never rides inside
a build task, and the loop's fold refuses a build branch that edits spec text.

- **From zero:** `new-repo --register --personal`, then intake in the new repository with the
  goal as the source: Engineer in its project, or Claude Code or Codex opened there (the `ai` menu
  opens any of them in the project). The owner accepts each change. Then `dev-loop start <repo>
  <type/slug>` makes the goal branch, and the spec commit comes first on it.
- **During a goal:** a worker that finds the spec wrong blocks. The control seat, a policy or
  review seat, or the owner runs intake for that one change and writes it as a task labeled
  `spec`; only that task's branch may change the specification.
- **Many raw notes at once:** `distill` first, then intake on the candidates worth acting on.

Traceability: the owner's acceptance, then the specification change whose commit message gives
the reason, then tasks depending on it, then the worker changes that close them (`Closes #N` in
the worker's `.worker-pr.md`). In a frozen repository the chain starts at the owner's
specification change, and intake starts at the tasks. With `decisions=open` the chain starts at
the decision record.

Keep the scope honest. A simple change the specification already covers goes straight to one
task; do not manufacture questions or tasks for every thought.
