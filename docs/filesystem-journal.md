# Filesystem journal

The owner's journal is plain text in `~/journal` on dev-server, owned by him. It has no
database and no application: one small file per thing.

```
~/journal/log/YYYY/MM/DD.txt      the day's note
~/journal/tasks/open/<file>       one task per file; done ones move to tasks/done/
~/journal/notes/ people/ me/      the rest of what he keeps
```

## One command set

The journal's commands are dev-server's `note`, `task`, `tasks` and `brief`
(`host/bin/`). There is no second set.

```sh
note                        # open today's note
note 2026-10-04             # open that day's (also yesterday, today, tomorrow)
note "a line"               # add the line to the end of today's note
task "pay the rent" --due friday --priority high --tag home
tasks                       # open tasks, oldest first, numbered
tasks --overdue
tasks --due-by today --sort priority
tasks --tag finance --json
tasks done 2                # finish task 2 (numbers are always those of plain `tasks`)
tasks --done                # what was finished
tasks --summary             # open, due today, overdue: what brief shows
brief                       # today's note, tasks, the inbox, what the roles proposed
```

A task file's first line is the task. Any lines after it say more, one `key: value`
each: `due`, `scheduled` (YYYY-MM-DD), `priority` (highest, high, medium, low) and
`tags` (words). That is the same shape a role's proposed task takes in the inbox, so
taking a proposal is `task` with its first line.

## Agents read; they never write here

All three roles (Assistant, Ops, Engineer) may read the journal; none writes in it. The kernel
enforces both: each agent has a read-only ACL on `~/journal`, and bootstrap checks that
no agent can create a file there. In Pi, a role reaches the journal only through its
journal tool (`integrations/pi/journal-tool.mjs`):

- reads: `tasks` (open tasks), `day` (a day's note) and `entries` (the work entries the
  roles left for a day);
- writes go to the owner's `~/inbox` as small files named
  `<date>-<time>-<role>-<kind>-<id>.txt`: `work` (any role: what was done, for which
  project, how long, so Assistant can reconcile hours), and for Assistant only `task` and
  `journal-line` (proposals the owner takes or drops);
- Assistant's own dense daily log (`log-append`, `log-path`) is in his memory,
  `/home/assistant/memory/days/`, not in the journal.

`brief` counts the proposals and work entries waiting in the inbox.

## The old vault, read-only

The Obsidian vault the journal came from is archived, unchanged, at
`~/archive/vault` (PARA folders, Tasks-plugin lines with emoji dates). Its
tasks are not in the journal. They stay searchable:

```sh
tasks --archive                      # its open task lines, with file and line
tasks --archive --tag work --due-by 2026-09-30 --sort due
tasks --archive --done --limit 20
```

`tasks --archive` runs the platform's read-only reader, `lib/journal.py`, which parses
the Tasks-plugin format: `- [ ]` and its states, 📅 due, ⏳ scheduled, 🛫 start, ✅ done,
❌ cancelled, ➕ created, priority emoji, `#tags`, 🔁 recurrence (kept as text, not
computed). It skips frontmatter, fenced examples, hidden paths and symlinks, and by
default the vault's history folders (`0. assistant`, `5. archive`, `6. templates`,
`7. data views`). Invalid or repeated dates and unknown states are flagged as warnings,
never dropped. It never writes, and `tests/test_journal.py` checks that not a byte
changes. `--priority` is not offered there; sort by it instead. For full-text search of
the vault, use `recall` or `rg`.
