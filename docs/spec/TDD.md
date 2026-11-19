# Technical Design Description

How the platform is built to meet each requirement of [SDD.md](SDD.md), item by item, with the code and tests that carry it.

## Document control

| Field               | Value                                                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Product             | dev-platform                                                                                                                |
| Scope               | The design of the areas ST, SP and SW of the SDD. The areas SC, TK and PJ have no TDD item yet.                             |
| Authority           | This document decides how the platform is built in its scope. Where code and this document disagree, one is wrong; say which. |
| Companion documents | [SDD.md](SDD.md) states what the platform must do.                                                                          |
| Change control      | A change of the design edits the exact lines in the same commit as the code. Git records the change.                        |

## Conventions

- Each item is a `#### TDD-<section>.<n> Title` heading.
- A trace comment follows it: `<!-- id: TDD-x.y | implements: XX-nn | code: path#Symbol | tests: path or none | status: ... -->`.
- A cited item is never renumbered; new items are appended.
- This document adds no behavior. A behavior that no SDD item requires goes to the SDD first.

## 1. Specification tree

One module, `lib/ai_ecosystem/spectree.py`, holds the compiler. `bin/dev-spec` only starts it. The module reads the config, makes one record for each repository (its SDD items, its TDD items, the paths that they name, the kept test results), joins the optional top document to the SDD items, and writes the page and the JSON tree from that one data structure. The start of the module is the script of the Acme company specification of 2026-11-17; on that day the two programs gave the same status, links and paths for each of 1,011 SDD items and 668 TDD items.

#### TDD-1.1 The config and the project name

<!-- id: TDD-1.1 | implements: ST-15 | code: lib/ai_ecosystem/spectree.py#load_config, lib/ai_ecosystem/spectree.py#find_config, lib/ai_ecosystem/tiers.py#KEYS | tests: tests/test_spec_tree.py -->

`load_config` reads one JSON file with the schema `dev-platform.spec-tree@1`. It collects each problem (an unknown field, a missing field, a wrong type, a folder that does not exist) and raises one `ConfigError` with one line for each; `main` prints them and exits with 2. The fields of a repository: `name`, `path` (relative to the folder of the config; `~` is the home folder), `layout`, and the optional `title`, `source`, `sdd`, `tdd`, `test`, `prepare`, `code_endings`, `not_counted`, `flag_words`, `interface_names`, `result_prefixes`. `top` is `null`, a path, or an object with `path`, `prefix` and `repository`. `find_config` takes the project record `<name>.json` from the projects folder of the platform (TDD-3.5). The older way stays until the registry field goes away: a `repos.conf` line with the field `tree=<path>` names a config in that checkout, and `tiers.py` accepts the field `tree`.

#### TDD-1.2 The three layouts

<!-- id: TDD-1.2 | implements: ST-02 | code: lib/ai_ecosystem/spectree.py#parse_single, lib/ai_ecosystem/spectree.py#parse_domains, lib/ai_ecosystem/spectree.py#parse_sections | tests: tests/test_spec_tree.py | status: implemented -->

Each layout has one parser that returns the SDD items, the TDD items, the groups (the sections or the domains) and the table rows that have an identifier. `single` and `sections` share two row readers: an SDD item is a `**XX-nn.**` line with a trace comment in the next three lines, and a TDD item is a heading of four or five `#` with `TDD-<numbers>` and a trace comment. A heading with no identifier above a TDD trace comment is still read as that item, and it is a fault. `sections` reads each `.md` file of the two folders in number order (`2.1` before `10.1`). `domains` reads `sdd.md` and `tdd.md` of each domain folder: an item is a `### <id> <title>` heading with `key: value` lines. Lines inside a code fence are not read.

#### TDD-1.3 The links and the form measures

<!-- id: TDD-1.3 | implements: ST-03, ST-13 | code: lib/ai_ecosystem/spectree.py#load_repo, lib/ai_ecosystem/spectree.py#keep, lib/ai_ecosystem/spectree.py#parse_sdd_rows | tests: tests/test_spec_tree.py | status: implemented -->

`load_repo` joins the two sides of the trace. A link to an identifier that is no item is a fault, except when a table row has that identifier: then the item keeps it in `rows` and the page shows it as text. A link that only one side states goes to the list `one_sided`, which is a measure. `keep` refuses the second item with one identifier, and the row readers compare the identifier of the trace comment with the identifier of its line. The measures of an SDD item: `has_must` (the word in any case of letters, in the requirement sentence where the layout has one, else in the item's text), `code_names`, `words` and `flag_words`.

#### TDD-1.4 The paths, the status and the files with no owner

<!-- id: TDD-1.4 | implements: ST-05, ST-07, ST-14 | code: lib/ai_ecosystem/spectree.py#resolve_paths, lib/ai_ecosystem/spectree.py#differs, lib/ai_ecosystem/spectree.py#declared_kinds, lib/ai_ecosystem/spectree.py#TEST_NAME | tests: tests/test_spec_tree.py -->

`resolve_paths` looks at each path that a TDD item names: does it exist, does the file hold the symbol after `#`, and what is the kept result of a test path. A symbol with a dot, for example `Class.method`, is found when the file holds each of its names as a word: code does not hold the text with the dot. A test path is a support path (`support`) when a valid result holds no case of it and no file name matches `TEST_NAME`: the name of the file itself, or for a folder (`folder`) the name of each tracked file below it. A support path is not one of the tests of the item, so an item with support paths alone has the status `no test`. A support path owns its files as each other named path, and the page lists it as a measure and not as a gap. From these facts it sets one status for the TDD item, in the order of `ORDER`, and each SDD item takes the worst status of its TDD items. It then lists each tracked file with a code ending that no named path owns; a named folder owns each file in it. `differs` compares the declared status with the computed one: a marker with a gap kind (`pending`, `deviation`, `unverified`) disagrees with `proved`, and a marker that says only `implemented` disagrees with each other status.

#### TDD-1.5 The top document

<!-- id: TDD-1.5 | implements: ST-04 | code: lib/ai_ecosystem/spectree.py#parse_top, lib/ai_ecosystem/spectree.py#join, lib/ai_ecosystem/spectree.py#resolve_selector | tests: tests/test_spec_tree.py | status: implemented -->

`parse_top` reads the numbered sections of the top document: a requirement is a `**XX-nn.**` line, and its trace comment gives the identifier with the prefix of the config and the field `sdd:`. `resolve_selector` turns each name into SDD items: `repo:ID`, a pattern (`repo:LN-*`), a group (`repo:section/1`, `repo:domain/estimate`) or an area of a capability catalogue where the repository has one. `join` records the owner of each group and returns the faults (a name that matches nothing, a second owner) and the gaps (a group with no owner, a requirement that names `none`).

#### TDD-1.6 The levels of the tree

<!-- id: TDD-1.6 | implements: ST-01 | code: lib/ai_ecosystem/spectree.py#build, lib/ai_ecosystem/spectree.py#render | tests: tests/test_spec_tree.py | status: implemented -->

`build` makes the one data structure. With a top document, the tree part of the page goes from each top requirement to its groups and items; a group that no top requirement owns is shown below its repository. With no top document, the tree part starts at the groups of each repository.

#### TDD-1.7 The page and the JSON tree

<!-- id: TDD-1.7 | implements: ST-06, ST-11, SDD-PJ-06 | code: lib/ai_ecosystem/spectree.py#render, lib/ai_ecosystem/spectree.py#lists, lib/ai_ecosystem/spectree.py#as_json, lib/ai_ecosystem/spectree.py#md_html, lib/ai_ecosystem/spectree.py#set_spans, lib/ai_ecosystem/spectree.py#output_paths, lib/ai_ecosystem/spectree.py#in_checkout, lib/ai_ecosystem/spectree.py#home_git_dir, lib/ai_ecosystem/spectree.py#own_ignore | tests: tests/test_spec_tree.py -->

`render` returns the page as text and `as_json` the same data with sorted keys; `main` writes them as `tree.html` and `tree.data.json` into the folder that `output_paths` gives. That folder is the field `page` of the record, else the folder `dev-platform` inside the Git folder that `home_git_dir` finds: the common Git folder of the repository of the top document, else of the first repository with a specification. Git, a formatter and a linter do not read a file there, and each worktree shares it. `in_checkout` asks Git if a folder is in a working tree; for such a page folder `own_ignore` writes a `.gitignore` file with one `*` line, and `main` prints one line of caution. Each parser keeps the first and the last line of each section and each item (`set_spans`), and `md_html` turns those source lines into HTML: paragraphs, lists with levels, tables and code blocks. `inline` writes the line break tag `<br>` of the source as a line break, because a table cell has no other form for it; each other tag is text. The page prints each section with its text, each SDD item in full, and below it each TDD item in full inside a `details` element. One `style` element holds the style sheet (`STYLE`); the page has no script and no external file. No part of the output reads a clock. The compiler opens a specification file only to read it.

#### TDD-1.8 The kept test results

<!-- id: TDD-1.8 | implements: ST-08, ST-09 | code: lib/ai_ecosystem/spectree.py#run_tests, lib/ai_ecosystem/spectree.py#load_results, lib/ai_ecosystem/spectree.py#results_valid, lib/ai_ecosystem/spectree.py#keep_results | tests: tests/test_spec_tree.py -->

`run_tests` holds a lock file for each repository, runs the optional `prepare` command and then the `test` command with `{out}` replaced by a new file, and moves that file over the kept JUnit report only when the command wrote it. It writes the revision and the count of uncommitted paths beside the report. `keep_results` is the path of a pipeline: it takes a JUnit file that exists, refuses a file that is no XML and a config with more than one repository, and writes the file and the present revision in the same two places; it starts no command. `load_results` counts the passed, failed and skipped cases for each test file. `results_valid` accepts a report of the compiled revision, and a report of an earlier revision when `git diff` shows no change outside the two specification paths.

#### TDD-1.9 The source of a repository

<!-- id: TDD-1.9 | implements: ST-10 | code: lib/ai_ecosystem/spectree.py#source_root | tests: tests/test_spec_tree.py | status: implemented -->

With the source `checkout`, the compiler reads the primary checkout. With a ref, `source_root` fetches the branch when the ref starts with the name of a remote, and keeps a detached worktree at `.claude/worktrees/spec-tree` of the repository at the commit of the ref. It runs `git worktree add --detach` one time and `git checkout --detach` in that worktree after that. It runs no other command that changes a repository.

#### TDD-1.10 The command

<!-- id: TDD-1.10 | implements: ST-12, ST-16, SDD-ST-17 | code: bin/dev-spec, lib/ai_ecosystem/spectree.py#main, lib/ai_ecosystem/spectree.py#not_proved | tests: tests/test_spec_tree.py -->

`dev-spec` has four commands of the tree. `compile` writes the page and the JSON tree. `check` prints each fault as `file:line: problem` and exits with 1 when the list of faults is not empty; a gap and a measure are not in that list. With `--proved` it also prints the rows of `not_proved` (each SDD item whose status is not `proved` and whose trace comment has no gap) and exits with 1 when one exists. `test` runs `run_tests`, or `keep_results` with `--junit`. `form` prints each break of the item form (TDD-2.1). `main` gives each other command to the module of the write commands (chapter 3), and `export` to `specexport.py`. The module imports only the standard library.

#### TDD-1.11 The copy of the tool
<!-- id: TDD-1.11 | implements: ST-18, PJ-02 | code: lib/ai_ecosystem/specexport.py#neutral, lib/ai_ecosystem/specexport.py#main, lib/ai_ecosystem/spectree.py#native_config | tests: tests/test_spec_tree.py -->

`specexport.main` writes a folder: the command file with the given name (default `spec-tree`), a module folder with `spectree.py` and `specwrite.py`, and `MANIFEST.json` with the commit of the source and the SHA-256 of each file. `neutral` takes the part between the two export marks out of the source (the `export` command itself) and replaces the name of the schema, the prefix of the environment variables, the name of the platform in each folder and the name of the command and of the package. `FORBIDDEN` lists the names of the platform; the export looks for them in each file of the copy and in the given name, and writes nothing when one is left. `spectree.SCHEMAS` accepts the neutral schema name beside the name of the platform, so that the platform reads the config that a copy reads. `native_config` is the other side: for a record with the field `config` it reads that file from the first repository, from the checkout or with `git show` from the source ref, and copies the keys of `NATIVE_KEYS` and `top` into the record before the usual checks.

## 2. Specification standard

The checks of area SP are functions of the same module, `lib/ai_ecosystem/spectree.py`. They use the items and the line spans that the compiler already has. The items of this chapter have no status field: the compiler gives the status, and a known gap cites its task.

#### TDD-2.1 The form rules of an item

<!-- id: TDD-2.1 | implements: SP-07, SP-08, SP-09, SP-10, SP-11, SP-12, SP-13, SP-14 | code: lib/ai_ecosystem/spectree.py#form_faults, lib/ai_ecosystem/spectree.py#RULES, lib/ai_ecosystem/spectree.py#differs | tests: tests/test_spec_tree.py -->

`form_faults` returns a list of pairs for one SDD item: the rule and the reason. It examines the requirement sentence with the code spans removed: the count of the word in capitals, a second sentence, a first word that is no EARS pattern, the count of words. It then reads the lines of the item: each top-level bullet is a part, a part with an unknown name is a break, text that is no part is a break, and the word in capitals in a part is a break. It counts code names that the config does not list in `interface_names`, checks the form of the identifier, and looks for a `status` field and for a `gap` that is not `#N`. `load_repo` stores the list in the item; the page has one list for each rule, and the JSON tree has the field `form`. A `gap:` field is a declared gap: `differs` reports it when each named test passes.

#### TDD-2.2 The check of the items that a change touches

<!-- id: TDD-2.2 | implements: SP-17 | code: lib/ai_ecosystem/spectree.py#form_command, lib/ai_ecosystem/spectree.py#touched_lines | tests: tests/test_spec_tree.py | gap: #33 -->

`dev-spec form` prints one line for each break: the file, the line, the identifier, the rule and the reason, and exits with 1 when it prints a line. With `--base`, `touched_lines` reads `git diff -U0` against that revision, and the command examines only an item whose lines overlap a changed range. The commit hook does not call this command yet; task 33 adds that.

#### TDD-2.3 The system requirements and the owner of a section

<!-- id: TDD-2.3 | implements: SP-02, SP-03, SP-04 | code: lib/ai_ecosystem/spectree.py#parse_sdd_rows, lib/ai_ecosystem/spectree.py#join, lib/ai_ecosystem/spectree.py#is_upward, lib/ai_ecosystem/spectree.py#build | tests: tests/test_spec_tree.py -->

A requirement line of an SDD whose trace comment has an identifier that starts with `SYS-` is a system requirement, not an SDD item; `build` makes the top of the tree from these when the config names no top document. A comment in the three lines below a section heading gives the owner of the section in the field `sys:`, and the trace comment of an SDD item can name more owners. When a project has an owner in a section or a system requirement in an SDD, `join` works upward: a section with no owner, with two owners or with an unknown owner is a fault, and a requirement of a separate system document needs no `sdd:` field. A project with no owner in a section keeps the downward names of its top document.

## 3. Specification writes

A second module, `lib/ai_ecosystem/specwrite.py`, holds the commands that explain and change a specification. `spectree.main` gives it each of its command names. It uses the tree that the compiler builds: the items, their line spans and their links. It works on the checkout of the folder where the command runs, so a session in a worktree changes its own worktree.

#### TDD-3.1 Find and why

<!-- id: TDD-3.1 | implements: SW-14, SW-15 | code: lib/ai_ecosystem/specwrite.py#find, lib/ai_ecosystem/specwrite.py#why, lib/ai_ecosystem/specwrite.py#by_terms, lib/ai_ecosystem/specwrite.py#catalogue | tests: tests/test_spec_write.py -->

`catalogue` lists each system requirement, SDD item and TDD item in the order of the documents. `by_terms` takes the words of four letters or more of a text, drops common words, and gives each item the sum of a weight for each shared word; a word that few items hold has a higher weight. `find` prints the best 25 in the order of the documents. `why` takes an identifier or a path. For an item it prints the system requirements above it, the item, its TDD items and each path with its test result. For a path it prints each TDD item that names the path or a folder above it, or says that no item explains the file.

#### TDD-3.2 The write commands

<!-- id: TDD-3.2 | implements: SW-02, SW-06, SW-07, SW-08, SW-09, SW-10 | code: lib/ai_ecosystem/specwrite.py#propose, lib/ai_ecosystem/specwrite.py#confirm, lib/ai_ecosystem/specwrite.py#change_set, lib/ai_ecosystem/specwrite.py#change_add, lib/ai_ecosystem/specwrite.py#change_remove, lib/ai_ecosystem/specwrite.py#change_links, lib/ai_ecosystem/specwrite.py#trial, lib/ai_ecosystem/specwrite.py#change_move, lib/ai_ecosystem/specwrite.py#loose_block, lib/ai_ecosystem/specwrite.py#change_text, lib/ai_ecosystem/specwrite.py#drop_status, lib/ai_ecosystem/specwrite.py#locked, lib/ai_ecosystem/specwrite.py#change_retire, lib/ai_ecosystem/specwrite.py#change_section, lib/ai_ecosystem/specwrite.py#change_renumber | tests: tests/test_spec_write.py -->

Each change function returns the new lines of each file that it changes; it writes nothing. `change_set` replaces the text of one item: the first line of the given text is the requirement sentence or the title, the trace comment keeps its links, and the given lines take the place of the old body. `change_add` puts a new item after the last item of its section, with the next number of its area that no item and no `retired` comment holds. `change_remove` puts a `retired` comment in the place of the item and takes its identifier out of the trace comment of each linked item. `change_links` rewrites one field of a trace comment; `link` and `unlink` call it for the two items, and `bind` refuses a path that does not exist. `drop_status` removes the status from each trace comment that a command writes; a status that cites a task stays as the field `gap`. `propose` writes the new lines for a trial, compiles, refuses a new fault of the tree and a break of the item form of the changed SDD item, and puts the old content back. `confirm` writes the files, compiles again, puts the content back if a fault is new, and appends the command, the target, the answers and the hash of each file to `journal.jsonl` in the state folder of the project. `locked` holds one file lock of the project during each proposal and each confirm, so that two sessions get two proposal numbers. `change_move` takes the lines of an SDD item out of its section and puts them at the end of a different section; the identifier stays, because it names the area. A TDD item cannot move: its identifier holds its section.

Three changes have no item as their target. `loose_block` finds an old text block of the SDD: a trace comment whose identifier is no item, with the lines below it up to the next item, trace comment or heading. `remove` with that identifier calls `change_loose`, which takes the block out and takes the identifier out of each TDD item that names it. `own` with the identifier of an SDD item writes the field `sys:` of its trace comment: one more owner, or none. `text` calls `change_text`: it replaces the lines of a section that are before its first item (`free_span`), below the owner comment and the lock comment, or the lines between the title and the first section of a single file. It refuses a text, old or new, that holds an item, a trace comment or a heading, so that it cannot change an item.

`change_retire` takes a system requirement of the first chapter of the SDD out, with its trace comment and its parts, and leaves a `retired` comment; it refuses a requirement that a section or an SDD item names. `change_section` takes a section out, from its heading to the next heading of the same level; it refuses a section that holds an item, a system requirement, a section or a trace comment. In the sections layout a file with no line left has no lines (`None`), and `write_lines` removes it; the journal then holds `deleted` for the file, which the commit hook accepts. The proposal keeps each identifier of the `retired` comments of the section, `confirm` writes them to the journal as `retired`, and `numbers_used` reads them through `retired_before`.

`change_renumber` gives a TDD item a different number of its section. It refuses a number that `numbers_used` holds, an item with items below it, and an item that the base branch holds: `base_ref` takes the base from the field `git.base` of the record, else from the source of the repository, fetches a ref of the remote, and `git grep` looks for the trace comment of the item in that revision. It replaces the identifier as a whole name in each file of the specification, so the heading, the trace comment, each `tdd:` field and each text change in one proposal. The proposal lists each other tracked file that names the item; the command does not change such a file.

#### TDD-3.3 The related items and the answers

<!-- id: TDD-3.3 | implements: SW-03, SW-04, SW-05 | code: lib/ai_ecosystem/specwrite.py#related, lib/ai_ecosystem/specwrite.py#propose, lib/ai_ecosystem/specwrite.py#confirm, lib/ai_ecosystem/specwrite.py#open_items, lib/ai_ecosystem/specwrite.py#read_open | tests: tests/test_spec_write.py -->

`related` returns the identifiers that a change can affect, each with its reasons, in a fixed order: the linked items; for an SDD item the SDD items that share one of its TDD items and the system requirement of its section; for a TDD item the TDD items that name the same path; the two items before and the two after in the section; then by shared terms up to five items of its own level and up to three of the other level (`by_terms`). `terms` removes the usual endings of a word, so that two forms of one word are one term. `propose` prints each with its full text, saves the proposal with a number in the state folder, and exits with 3. `confirm` needs one answer for each identifier of the proposal. One `conflict` stops it and marks the proposal. An item with the answer `change` goes to the open list of the checkout of the proposal (`open_files`: one file for each checkout in the folder `open`); a later change of that item, or the answer `same` for it, takes it out. `read_open` also reads the one `open.json` that the release before wrote for each checkout. `dev-spec open` lists the open items and exits with 1 when one exists. The commit hook refuses a commit of a specification file while the list of its checkout holds an item (TDD-3.4).

#### TDD-3.4 The control: the commit hook, the guard and accept
<!-- id: TDD-3.4 | implements: SW-01, SW-05, SW-11, SW-12, SW-13 | code: lib/ai_ecosystem/specwrite.py#staged, lib/ai_ecosystem/specwrite.py#accept, lib/ai_ecosystem/specwrite.py#spec_paths, hooks/spec_guard.py, hooks/git/pre-commit | tests: tests/test_spec_write.py -->

Where the record of a project has `control` set, three functions enforce that a command makes each change of a specification file. `spec_paths` gives the paths of the system requirements, the SDD and the TDD of the repository of a checkout; each other file is free. `staged` is the check of the commit hook: `hooks/git/pre-commit` calls `dev-spec staged`. It takes the hash of each staged specification file and looks for it in the hashes that `confirm` and `accept` wrote to `journal.jsonl`; a content with no record is refused, and so is a commit while `open.json` holds an item. `hooks/spec_guard.py` is the harness guard: for an edit tool it refuses a path of the specification, and for a shell command it refuses a redirect, an in-place edit, `tee`, `rm`, and `mv` or `cp` with the specification file as the target. The pre-tool guard calls it for each shell command, and the Claude Code settings call it for the edit tools. `accept` runs only with a terminal on its input and output; it refuses a break of the item form in a changed SDD item and a fault in a changed file, and then records the hashes as the edit of the owner. The edit tools of Codex and Pi have no guard yet; the commit hook covers them.

#### TDD-3.5 The project record
<!-- id: TDD-3.5 | implements: PJ-01, PJ-02 | code: lib/ai_ecosystem/spectree.py#projects_dir, lib/ai_ecosystem/spectree.py#output_paths, lib/ai_ecosystem/specwrite.py#config_of | tests: tests/test_spec_tree.py -->

`spectree.projects_dir` is the projects folder of the platform. `find_config` takes `<name>.json` from it before it reads the registry, and `specwrite.config_of` takes the record whose repository holds the folder of the command. A record has the fields of the tree config and two more: `control`, and `page`, a folder for the compiled page. With no `page` field the page is in the Git folder of the repository (TDD-1.7). A repository of a record can also hold `remote`, `git` and `work`: the Git settings, the work settings and the check command (TDD-3.7). The compiler accepts these fields and does not read them. The record can also hold the list `parts` (TDD-3.8).

#### TDD-3.7 The record as the source of the registry
<!-- id: TDD-3.7 | implements: PJ-01 | code: lib/ai_ecosystem/projectrecord.py#generated, lib/ai_ecosystem/projectrecord.py#imported, lib/ai_ecosystem/projectrecord.py#sync, bin/dev-project, hooks/check-once.sh | tests: tests/test_project_record.py -->

`dev-project` is the command (`projectrecord.py`). A repository of a record can hold `remote`, an object `git` (`tier`, `mode`, `base`, `forge`, `keep`, `slots`, `large`) and an object `work` (`tracker`, `tasks`, `decisions`, `incoming`, `check`, `check_path`, `env`). `registry_line` makes one line of the registry from these, with each field stated, and reads it back with the parser of `tiers.py`, so that a wrong value stops the command. The layout `domains` of the record gives `spec=domains`; each other layout gives `spec=single`. `env_text` makes the check environment file of a repository: the folders of `check_path` first in the PATH, each variable of `env`, and the check command as `DEV_PLATFORM_CHECK`. `generated` refuses a folder that two records hold. `sync` shows the difference between the files and the records; with `--write` it writes them and keeps one copy of a file that a person wrote, and with `--check` it exits with 1 on a difference. It refuses when a line of the registry has no record. `imported` is the one-time step: it makes a record for each line of the registry with the completed values of `tiers.py` (so the personal list gives the tier one last time), and it reads a check environment file that holds only `export` lines. A record that exists keeps each field that it has. `hooks/check-once.sh` runs `DEV_PLATFORM_CHECK` of the environment file before it looks for a check in the repository; a variable of the session does not count. The readers of the registry are not changed: `tiers.py`, the loop and the menu read the file that `sync` makes.

#### TDD-3.8 The parts of the platform
<!-- id: TDD-3.8 | implements: PJ-03, PJ-04 | code: lib/ai_ecosystem/projectrecord.py#parts_off, hooks/guard_git.py#git_off, hooks/stop-check.sh, hooks/git/pre-push, hooks/git/commit-msg, hooks/git/pre-commit | tests: tests/test_project_record.py -->

`projectrecord.parts_off` gives the parts that a record does not list in `parts`, without the control, and `registry_line` writes them as the registry field `off=`; `tiers.py` accepts the field and gives an empty value where no line has it. The readers: `hooks/git/pre-commit` does not apply the rule of the frozen decisions; `hooks/git/commit-msg` and `hooks/git/pre-push` go to the hook of the repository with no rule; `guard_git.py` asks `Context.git_off` for the repository that a command names and then skips the rules of push, merge, commit, history rewrite, branch and the forge command, and keeps the rules for a second session, for a worktree and for the hooks path; `pre-tool-use-guard.sh` does not apply the rules of a professional repository; `stop-check.sh` exits with a line and runs no check; the loop refuses each verb that is no read verb; `dev-workspace` refuses to plan or start a seat. The compiler reads the record directly: `load_config` keeps the list, sets `control` from it, and `main` refuses a project that does not list the tree. The check of the commit hook for a controlled specification belongs to the control, so it still runs when the Git rules are off.

#### TDD-3.9 The rig profile
<!-- id: TDD-3.9 | implements: SC-23, PJ-01 | code: lib/ai_ecosystem/forge.py#resolved, lib/ai_ecosystem/forge.py#record_repository, lib/ai_ecosystem/forge.py#load_profile, lib/ai_ecosystem/forge.py#cmd_init | tests: tests/test_forge.py -->

The profile of a rig is one file in the rig folder, read by `forge.load_profile`. `resolved` fills what the project record holds, so that the profile does not state it a second time. The field `project` names a record, and `record_repository` takes its one repository with a remote, or the one that the field `repository` names. From that repository come the remote, the worker slots where `workers.limit` is null, and the check command where `commands.full` is null. A value of the profile wins; a `repo` that differs from the record is refused. With no project, the slots come from the registry line of `repo`. The field `kind` is one of the names of `KINDS` and gives the worker runtime; a profile that states a runtime of a different kind is refused, and a profile with a runtime only gets its kind from it. `cmd_init` proposes a profile that names the project (`record_at` finds the record of the checkout) and leaves each value of the record empty.

#### TDD-3.10 The side folder of a ghost project
<!-- id: TDD-3.10 | implements: PJ-10 | code: lib/ai_ecosystem/spectree.py#load_repo, lib/ai_ecosystem/specwrite.py#spec_home, lib/ai_ecosystem/specwrite.py#spec_paths, lib/ai_ecosystem/specwrite.py#config_of, skills/loop/scripts/loop.sh, lib/ai_ecosystem/forge.py#task_home | tests: tests/test_spec_write.py, tests/test_forge.py -->

A repository of a record can hold `spec_root`. `load_config` makes it an absolute path and refuses a path that is no folder or that is not the top folder of its Git repository. `load_repo` keeps two folders: `root`, the checkout or the worktree of the compiler, where `resolve_paths` looks for the code paths and the test paths, and `spec_root`, which is the side folder or else `root`; each parser, the capability catalogue, the top document and `touched_lines` read `spec_root`. In the write commands, `propose` writes the trial and the proposal to `spec_root`, so `confirm`, the journal and the open list belong to the side folder. `config_of` finds the record from the checkout and from the side folder. `spec_paths` gives the specification paths only for the repository of the side folder, so the commit hook and the guard act there and a file of the foreign repository is free. `spec_home` gives the side folder to `open` when it runs in the checkout.

The tasks use the same folder. `projectrecord.registry_line` writes `tracker=side` with the registry field `side=`, the absolute path of `spec_root`, and refuses the tracker with no side folder. In the loop, `side_mode` is a local mode: `tasks_dir` and `tasks_ref` give the side folder and its HEAD to the task reader in place of the checkout and the base branch, the brief of a worker names the task file by its full path, and `side_done` moves the task file to the done folder and commits only that move in the side folder after the fold commit. The forge reads the same place through `task_home`.
