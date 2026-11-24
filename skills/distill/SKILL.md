---
name: distill
description: Turn a raw record (meeting transcript, message, email, notes) into ranked, color-coded candidate requirement statements appended to one incoming HTML file that git does not track, for people to read, discuss and edit by hand. The file is `~/.local/state/dev-platform/incoming/<repo-name>.html`, or `docs/incoming.html` in the checkout, ignored by git, when the `repos.conf` line has `incoming=project`. Each candidate is ranked for congruency with the specification and for complexity. Nothing is filed, edited or opened; a person promotes a candidate by giving its ID to an `intake` session, or in a `decisions=frozen` repository by taking it into the specification by hand or with the `dev-spec` write commands.
---

# distill

Turn a raw record (meeting transcript, message, email, notes, stored in the owner's notes and never in a repository) into candidate requirement statements, each ranked against the repository's specification for congruency and for complexity, and append them as one dated batch to the incoming file of the repository. `dev-loop tier <path>` prints its place as `incoming_file` (SDD-SC-10):

- `incoming=state` (the default): `~/.local/state/dev-platform/incoming/<repo-name>.html`, where `<repo-name>` is the repository name without the owner.
- `incoming=project`: `docs/incoming.html` in the main checkout. Git ignores it, so it makes no commit and no branch.

People read, discuss and edit that file by hand. When a person decides a candidate is worth acting on, they give its ID to an `intake` session (`intake C-2026-11-17-3`), and `intake` reads the block from the file. In a `decisions=frozen` repository intake changes no specification (SDD-SC-20): the owner takes the candidate in by hand, or an agent uses the `dev-spec` write commands where the project has a specification tree. Distill runs the same in every repository. Nothing else reads the file: the loop, workers and hooks never reference it. The skill files no issue, edits no specification and opens nothing.

## Procedure

1. **Source.** Any raw record. It stays in the owner's notes; it is never copied into a repository.
   The HTML receives derived statements and a source reference by date and type only, for example
   `stakeholder call, 2026-09-17`. No raw quotes and no names of private individuals.
2. **Extract** candidate statements. Each is one sentence in `MUST`, `MUST NOT` or `SHOULD` form,
   with a kind: `bug`, `amendment`, `feature` or `question`.
3. **Resolve the specification and evidence.** Read the repository's mode with
   `dev-loop tier <path>`. With `spec=domains`, the index `docs/spec/index.json` is the reader:
   find each item by its ID or by its `domain` and `file` there, and read its source text in
   `docs/spec/<domain>/sdd.md` or `tdd.md`. Use `bun run spec:show <ID>` and
   `bun run spec:impact <ID>` where the repository has them. Never fall back to
   `docs/spec/SDD.md` or `TDD.md` in that mode; they are retired. With `decisions=none` or `decisions=frozen`, an old
   decision is history: rank against the current specification text. Otherwise use the project's
   configured specification reader or project-local spec tool first, preserving its native
   section IDs and output format. If no configured reader exists, fall back to `docs/spec/SDD.md`, `docs/spec/TDD.md`, the other
   documents under `docs/`, and the code the TDD `code:` comments name. Use `dev-loop tasks
   <repo>` for local task state and `ghx`/GitHub for GitHub-backed task state when task status
   matters. When a configured reader or fallback file is absent or empty, say so in the report.
   Every candidate is `brand new` except one that cannot be acted on at all, which is still
   `nonsense`.
4. **Rank** each candidate on two axes.
   - Congruency: `already satisfied`, `clarifies`, `amends`, `contradicts`, `brand new` or
     `nonsense`. Cite the specification item ids it touches (`SDD-XX-nn`, `TDD-x.y.z`); a
     `brand new` candidate may cite none. With `spec=domains`, use the IDs as the index writes
     them (`SDD-D1`, `TDD-1.1`).
   - Complexity: `S`, `M`, `L` or `XL`, judged from the specification items touched, the files
     likely in scope, external provider effects and data migrations. One line of rationale that
     names what drove the size.
5. **Append** the candidates to the `incoming_file` that `dev-loop tier <path>` prints, as one dated
   batch. Create the folder and the file from the `incoming.template.html` that sits beside this
   skill file when the file is absent. Git must never track the file:
   - With `incoming=project`, run `git -C <checkout> ls-files --error-unmatch docs/incoming.html`
     first. If git tracks the file, stop and tell the owner. Then run
     `git -C <checkout> check-ignore -q docs/incoming.html`. If git does not ignore the file, add
     the line `docs/incoming.html` to the file that `git -C <checkout> rev-parse --git-path
     info/exclude` names. Do not change the `.gitignore` of the repository; that is a commit.
   - With `incoming=state`, never write the file inside the repository.

   Copy the
   example batch in the template, place the new batch directly under the
   `batches below, newest first` marker, and never rewrite, reorder or delete an existing block:
   people edit them by hand. Escape `&`, `<` and `>` in every statement and rationale. Candidate
   ids are `C-YYYY-MM-DD-n`; n starts at 1 and continues within the day across batches, so search
   the existing file for the day's highest n before writing. Set the `class` of each block to the
   congruency class: `satisfied`, `clarifies`, `amends`, `contradicts`, `new` or `nonsense`.
6. **Stop.** Report the batch as a short table: id, statement, kind, congruency, complexity. Do not
   file issues, edit the specification or open anything. Promotion is a person giving a candidate
   ID to `intake`, or, in a `decisions=frozen` repository, the owner's own change of the
   specification.

## Plain reading

An easy patch is `clarifies` or `amends` at `S`. A hard change is `amends` or `contradicts` at `L`
or `XL`. `already satisfied` and `nonsense` need no work; they stay in the file so the discussion
can confirm that.
