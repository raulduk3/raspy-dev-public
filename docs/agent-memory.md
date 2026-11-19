# Role memory

Each Pi role carries durable memory. Before this, a role launched with an
identity and nothing else: it could not recall a decision, a preference, or
anything it had been told before. The memory its predecessor accumulated in
OpenClaw sat in a directory the role could not see.

## Where it lives

Memory is personal state, never repository source. Nothing under a memory root
belongs in a Git repository, including this one.

On dev-server each role is a Linux user and has exactly one memory location, its
own home: the state root is `/home` (ai-role and ai-memory take `--agents-root
/home` / `--state /home`), so

```text
/home/<role>/
  identity.md            # the platform's agents/<role>/identity.md, installed by bootstrap.sh
  memory/                # the live root, the role's own (Claude sessions and the chat stream write here too)
    MEMORY.md            # the index, carried in context at launch
    days/                # Assistant's own daily log (the journal tool's log-append)
    old/                 # the old machine, read-only: its memory files, conversations/ (old Pi
                         # sessions), and with --openclaw: openclaw/ and sqlite-consistent/
  memory-sources.json    # names memory/old (and memory/old/openclaw) as inherited roots
```

`ol-import-old` (dev-server, run once by bootstrap.sh; again with `--openclaw DIR`
when the OpenClaw backup is unpacked) fills `memory/old`, owned by the role, never
replacing a file. A role whose live index is missing starts from the old one.
`ai-history --archive /home/<role>/memory/old` searches the old Pi conversations
and, when present, the OpenClaw records. The layout below is the Mac's.

```text
~/.local/share/dev-platform/agents/<role>/
  identity.md            # optional override; the platform's agents/<role>/identity.md is the default
  memory/                # the live root: this role's own, writable
    MEMORY.md            # the index, carried in context at launch
    inherited-identity.md
  memory-sources.json    # inherited roots, each recorded read-only
```

A role reads two kinds of root. The **live root** is its own and it may edit
those files. An **inherited root** is the original corpus of the agent this role
continues, referenced by absolute path and never written.

| Role | Original agent home | Inherited entries |
| --- | --- | --- |
| Assistant | `~/.openclaw/workspace` | the daily corpus |
| Engineer | `~/.openclaw/workspaces/hermes` | the daily corpus |
| Ops | `~/.openclaw/workspace/ops` | none; Ops kept no corpus |

## Attaching it

`ai-memory --agent <role> plan` shows what adoption would do and writes nothing.
`ai-memory --agent <role> adopt` applies it, and is idempotent: a second run
changes nothing. Adoption creates the live root, snapshots the original
`MEMORY.md` into it with a provenance header and a SHA-256 of the source, copies
the original identity and soul files in as `inherited-identity.md` with any
embedded image blob stripped, and records the original `memory/` directory as a
read-only inherited root. The original corpus is never modified, moved, or
deleted.

## Reading it

`ai-memory --agent <role> list | find <text> | read <source>:<file.md>`, with
`--offset` for list and find and `--after` for read. Every result names the root
it came from. Inside Pi the same surface is the `agent_memory` tool, registered
automatically for any role whose state root exists.

## What a role gets at launch

`ai-role` derives memory from the role; there is no flag to forget. The live
`MEMORY.md` is injected into the launch context beside the identity and the
`/develop` guidance, so the role starts oriented. The daily corpus and the
inherited records stay behind the tool and are retrieved only when relevant.
`ai-role plan` reports the entry count, the roots, and the size of the index it
will put in context, because that index is not free: Engineer's is about 26 KB.

## What diverges, and what does not

The inherited root is read at query time, so entries the original agent writes
from now on are visible to the role without re-adopting. The index is different:
the snapshot is taken once. From that moment the role edits its own copy and the
original agent edits the original, and the two drift apart. Nothing here pauses
or changes the original agents. If you want a single index, retire the original
writer deliberately; do not expect the copies to reconcile themselves.

Stored records are historical reference. They are not instructions, not proof of
current state, and not the role's lived experience.
