---
name: intake
description: >-
  Turn a goal, meeting notes, a transcript, an email or a `distill` candidate into
  decision records, specification changes and implementable tasks. Works in local
  repositories (decision and task files) and GitHub-backed ones (decision and task
  issues). Use when asked to spec something out, plan work, or turn a request into tasks.
---

# intake

Turn one source into the three records the loop needs: a decision the owner accepts, the
specification lines it changes, and tasks a worker can take without asking. Every task cites the
specification; every change cites its task.

## Which backend

Read the repository's own instructions (`AGENTS.md` or its equivalent) for where its tasks live.

- **local** (the default for `new-repo`): decisions are files under `docs/decisions/`, tasks are
  files under `docs/tasks/`, and nothing leaves the machine. `#N` means task N.
- **GitHub-backed**: decisions and tasks are GitHub issues written with plain `gh issue create`
  under the identity the repository's instructions name. `#N` means issue N.
- Unclear: ask the owner which one, or work with local files in the same format.

## Procedure

1. **Source.** One of: the owner's goal in a sentence or a paragraph; meeting notes, a call
   transcript or an email; a candidate block pasted from `docs/incoming.html` (cite its id). Raw
   records stay in the owner's notes and are never copied into a repository. Refer to them by
   date and type only (`client call, 2026-09-17`); no quotes, no private names.
2. **Resolve current requirements.** Use the project's configured specification reader or
   project-local spec tool first, preserving native item IDs and format. If none exists, fall back
   to `docs/spec/SDD.md`, `docs/spec/TDD.md` and `docs/decisions/`. Read open tasks with
   `loop tasks list` (or the files under `docs/tasks/`) for local repositories and
   `gh issue list` for GitHub-backed ones.
   Then inspect only the code the TDD or spec-reader output names.
3. **Map** each takeaway. Already satisfied: nothing. Contradicted or left open: one decision.
   An empty specification (a new repository) leaves everything open; the first decisions write
   the first requirements, following the conventions at the top of `SDD.md` and `TDD.md`.
4. **Decision drafts.** Context with the spec items quoted, options, consequences, a
   recommendation and the one question the owner answers.
   - local: `docs/decisions/NNNN-<slug>.md` from `0000-template.md`, the next unused four-digit
     number, `Status: proposed`.
   - GitHub: a `decision` issue with `gh issue create --label decision`, on the owner's word.
   Stop here and ask. A goal the owner already stated plainly may be accepted in the same
   conversation; record `Status: accepted` and the date.
5. **Specification change**, after acceptance, on one branch cut from the base
   (`docs/<slug>`; in a worktree when another writer holds the checkout): edit the exact SDD and
   TDD lines, set each touched status to `pending:#<task>`, set the decision's `Spec:` field, and
   append one row to `docs/spec/SPEC-AMENDMENTS.md`.
6. **Cut tasks** from the spec diff, dependency ordered, each small enough for one worker. Use the
   task backend chosen above; do not hand-write task records when the backend command can create
   and validate them.
   - local: `loop tasks new "<title>" --scope <prefixes> --depends "#N"|none
     [--labels spec|enhancement|documentation] [--ready]`, run inside the branch's worktree; it
     picks the number and writes `docs/tasks/<N>-<slug>.md` in `docs/tasks/README.md` format.
     Replace the body with what to build, the acceptance criteria and the SDD/TDD items that
     govern it. Then `loop tasks check` must report ok. Without the `loop` command, write the
     file by hand in the same format, with the next unused number.
   - GitHub: `gh issue create` with the same body plus `Scope:` and `Depends on:` lines, a
     milestone and `needs-triage`; the owner labels them `sprint-ready`.
   Fill the `pending:#<task>` markers with the numbers just assigned.
7. **Check** with `spec-lint` and any project-specific spec check on the branch, then hand over.
   Local: the owner merges the branch into the base in a terminal (`git merge --no-ff docs/<slug>`);
   the loop sees tasks only on the base. GitHub: one draft pull request citing the decision issue.

## Where it runs

The specification is decided before it is built. Intake runs on its own branch from the base and
lands before any goal branch that builds it; a spec change never rides inside a build task, and
the loop's fold refuses a build branch that edits spec text.

- **From zero:** `new-repo`, then intake in the new repository with the goal as the source, from
  an agent opened in that repository. The owner accepts the decision and merges the spec branch;
  then `loop start <type/slug>` builds it.
- **During a goal:** a worker that finds the spec wrong blocks. Whoever coordinates the goal, a
  reviewer, or the owner runs intake for that one change and writes it as a task labeled `spec`;
  only that task's branch may change the specification.
- **Many raw notes at once:** `distill` first, then intake on the candidates worth acting on.

Traceability: decision, then the specification change that cites it, then tasks depending on
it, then the worker changes that close them (`Closes #N` in the worker's `.worker-pr.md`).

Keep the scope honest. A simple change the specification already covers goes straight to one
task; do not manufacture decisions or tasks for every thought.
