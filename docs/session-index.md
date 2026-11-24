# Session index and environment doctor

`bin/ai-session` keeps the machine's one session index: Claude Code, Codex and Pi sessions in
the owner's home and in every agent's home (assistant, ops, engineer). `bin/ai-env doctor` reports on the local toolchain. Both are local only:
no daemon, scheduler or database service, and neither writes native client storage.
The doctor makes no model call.

## ai-session

The scanner also reads native Claude/Codex home locators from the non-secret
`/var/lib/dev-server/accounts/registry.json` registry. Shared/default homes are deduplicated;
isolated homes retain separate native identities. Missing stores remain unavailable,
not deleted. Discovery does not read credential files or verify the current account.
Claude resume plans for isolated stores include the corresponding `CLAUDE_CONFIG_DIR`.
Resume commands clear inherited `CODEX_HOME` and `CLAUDE_CONFIG_DIR` before applying
the recorded native home. Conflicting provider credential/routing environment
settings refuse resume; this prevents a terminal's unrelated login route from
silently changing a recovered session. This does not verify current login identity.

```
ai-session [--state-root DIR] scan [--limit N] [--home DIR]
ai-session list [--json] [--runtime claude|codex|pi] [--owner user|assistant|ops|engineer] [--limit N] [--search TEXT]
ai-session show ID [--json]
ai-session export [--home DIR] [--since EPOCH]                 (run as an agent)
ai-session ingest --owner AGENT [--launch KEY=VALUE ...] [--launch-since EPOCH]   (run as the owner, export on stdin)
ai-session import-old SOURCE DEST
ai-session title ID TEXT [--expect-revision N]
ai-session handoff ID [--import FILE|- --expect-revision N]
ai-session resume ID [--execute]
```

`list` returns at most 20 matches by default. `--search` matches a case-insensitive
substring in title, native ID, working directory or owner, never transcript content (use
dev-server's `recall` for that; it searches the `text/` folder). `--limit 0`
explicitly requests all matches; JSON includes `total` and `has_more`. Text rows truncate
long titles and paths for readability.

`show ID` prints the session as readable text: its title, launch facts, the exact resume
command (or why it cannot resume), any handoff, then the conversation with tool calls as
one-line `→ tool: argument` and results as `← output` (clipped). Thinking blocks are left out.
Anything that looks like a credential (provider keys, GitHub/Slack tokens, bearer tokens,
JWTs, private keys, `password=`-style assignments) is shown as `[secret hidden]`.
`show --json` prints the manifest instead.

## Every home, without reading another's home

The owner's home is scanned directly (`scan`). An agent's home is readable only by that
agent, so the agent exports and the owner files:

    runuser -u assistant -- ai-session export --home /home/assistant --since EPOCH \
      | runuser -u owner -- ai-session ingest --owner assistant [--launch kind=chat ...]

dev-server's `ol-sessions-sync` (root) runs that for each agent at the end of every `agent`
launch and on a timer. `export` writes nothing; it renders text only for transcripts
changed since `--since`, and the index keeps earlier text otherwise. Ingested sources are
named `AGENT:SOURCE`; a complete export that no longer lists a session marks it `stale`
exactly as a scan does, and the owner's own `scan` never calls an agent source vanished.
`--launch` facts land on the sessions whose transcripts changed since `--launch-since`
(the launch time); they follow [Session naming](session-naming.md).

State lives under `~/.local/state/dev-platform/sessions` (or `--state-root`, or
`AI_SESSION_STATE`), owner-only:

- `manifests/<id>.json`: versioned manifest, replaced atomically under a per-session `flock`
  in `locks/`. Every write bumps `revision`.
- `handoffs/<id>.md`: a handoff you wrote, imported from a file or stdin (64 KiB limit).
  Import requires `--expect-revision`; a stale revision exits 3.
- `events/<id>/*.json`: immutable, uniquely named event files, published by fsync + atomic rename.
- `text/<id>.md`: the readable transcript, rendered when the native file changes, credentials masked.
- `sources.json`: last scan result per native source (`ok`, `truncated`, `error`, `unavailable`).

Files starting with `.` are partial writes and are ignored. Deleting `manifests/` and
rescanning rebuilds the index; titles set with `title` and handoffs live only here, so keep
the directory if you want them.

A session ID is the runtime plus a digest of the native store and native ID, so the same
native ID in two Codex homes never collides.

### Titles are index-only

`ai-session title ID TEXT --expect-revision N` changes only this index's display override.
It does not rename a Claude, Codex, Pi or OpenRig conversation. `show` keeps
both the last observed native `title` and the local `title_override`; rescanning preserves
the override and native identity. Read the current revision before writing and do not
replace an owner-assigned title. Follow [Session naming](session-naming.md) for automatic
self-naming and supported native capabilities; the index is not a native rename API.

### What each adapter reads

| Runtime | Source | Fields kept |
|---|---|---|
| Codex | `state_*.sqlite` `threads`, read-only, schema checked; `session_index.jsonl` fallback | id, rollout_path, cwd, title/name, git_branch, archived, updated_at |
| Claude Code | `projects/*/sessions-index.json`; else the first 40 lines / 256 KiB of each transcript | sessionId, cwd/projectPath, gitBranch, timestamp/modified, customTitle, transcript/index paths, transcript_missing |
| Pi | `~/.pi/agent/sessions/`, the platform's conversation homes (`~/.local/state/dev-platform/sessions/conversations/*/native/pi/`), and archived history (`~/memory/old/conversations/*/native/pi/`) | session id, cwd, model, account binding, conversation, archived, file time |

Manifests never hold message bodies, prompts or request content. The readable transcript
in `text/` does, for Claude Code, Codex and Pi, masked as above: the owner asked to read
sessions as text and to search them, and the folder is owner-only like the rest of the state. The Codex home is `~/.codex`
(owner `user`); no home is inferred from a transcript field.

### Status

Status is `unknown` unless native evidence says otherwise: `stale` when a complete scan of
its source no longer finds the record or a Claude index references a missing transcript. File
modification time is never taken as proof a session is running. A source that errors or
is truncated (by `--limit`, default 100000 per source) leaves
absent entries unchanged and is reported in the scan output (successfully read records may
update during a truncated scan). A vanished previously discovered source is `unavailable`,
not evidence its records were deleted; existing manifests and handoffs remain untouched.

### Resume

`resume` prints a JSON plan with the exact argv, working directory, environment and a
shell-quoted `command`; it runs nothing by default.

- Claude Code: `cd <cwd> && claude --resume <id>`.
- An agent's Claude Code session: `agent WHO [PROJECT] -- --resume <id>`, through the
  launcher that bounds the agent (Engineer's project is its recorded cwd). A role can hold
  several sessions and resume any of them this way.
- A role's Pi session: `env OL_MODEL=pi OL_ACCOUNT=<account> agent WHO [PROJECT] -- --conversation
  <id> --resume <file>`, through the same launcher, on the account that the session started
  on. A Pi session of the owner's own store cannot resume here: `ai-role` starts nothing
  without the login folder that the launcher hands in. Archived history from the old machine
  is read-only.
- Codex (`~/.codex` only): `cd <cwd> && CODEX_HOME=<home> codex resume <id>`.
- A session that a runtime owns (an OpenRig environment), a stale record and archived
  history: exit 2 with the reason. Never reported as success.

A native ID that is not a plain identifier, or a missing absolute cwd, makes the session
unsupported. `--execute` runs only a supported plan, only from an interactive terminal, with
argv and no shell. There is no pause, steer or cancel.

## ai-env doctor

```
ai-env doctor [--json] [--home DIR] [--platform-root DIR]
```

Read-only. Each check reports one state: `ok`, `missing`, `stale`, `unavailable`, `unverified`,
`unsupported` or `broken`. The checks (`lib/ai_ecosystem/doctor.py`):

- whether `claude`, `codex`, `code`, `gh`, `git`, `jq`, `python3` and `ai-jev` are on PATH;
- the platform skills and agent links in `~/.claude/skills`, `~/.codex/skills` and
  `~/.agents/skills`: missing, broken, divergent, and `stale` for a link into another release.
  The platform to compare is the activated release, else the checkout; `--platform-root`
  overrides it;
- the platform itself, the Jev configuration and its monthly spend, provider overrides in the
  tmux environment, OpenRig (version, runtime, configuration, workspace), herdr and the
  instruction surfaces.

It never installs, restarts, edits configuration or prints credentials or config contents.

## Cross-runtime conversations

`ai-session conversation` adds an explicit association above native sessions, in the same state root. Original transcripts are not moved or rewritten. Accounts do not define conversation identity.

```sh
ai-session conversation create --agent assistant --title 'Personal planning' --name personal-planning
ai-session conversation create --agent engineer --title 'Implement account controls' --project owner/repo --workspace /path/to/checkout
ai-session conversation create --agent engineer --title 'Explore a new project' --formation --workspace /path/to/formation
ai-session conversation create --agent ops --title 'Host maintenance' --resource local-host
ai-session conversation list
ai-session conversation bind CONVERSATION_ID_OR_NAME INDEXED_NATIVE_ID --expect-revision REVISION
ai-session conversation show CONVERSATION_ID_OR_NAME
```

Existing project names resolve to stable IDs through `~/.config/dev-platform/repos.conf`; `--repos FILE` selects another catalog configuration. The workspace must resolve to the same Git repository, including linked worktrees. Formation is an explicit temporary scope for a real directory before a catalog project exists. Assistant cannot be project-bound; Ops needs an explicit system resource or project scope. No creation command launches a runtime.

Each conversation has a canonical home at `conversations/ID/`. New homes contain `conversation.json` and a legacy-compatible `session.json`, `README.md`, `handoff.md`, `native/pi/`, `sessions/`, `events/`, `artifacts/` and `worktrees/`. Native transcripts stay in their owning runtime stores; `sessions/` contains small metadata references only. `--name` sets a stable lowercase filesystem slug, otherwise one is generated from agent, date and title.

The same conversation is exposed through filesystem view folders under `work/`: `work/conversations/<name>/ref.json`, `work/agents/<agent>/<name>/ref.json`, and, by scope, `work/projects/<project>/<name>/`, `work/formations/<name>/`, `work/resources/<resource>/<name>/` or `work/personal/<agent>/<name>/`. These are references to the canonical home, not transcript copies. `show` and `bind` accept either the stable conversation ID or the name.

Native associations also stay in existing index manifests and survive scans. Binding checks the expected native-record revision and refuses reassignment to another conversation. Project/formation bindings require a matching observed native workspace. This keeps associations evidence-based but means unavailable historical workspaces need a separate migration/rebinding procedure.

These commands record storage and association only. The role launcher applies the working folder, the resources, the native Pi session path and the account (`lib/ai_ecosystem/role_launch.py`).
