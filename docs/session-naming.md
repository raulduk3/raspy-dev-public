# Session naming

One contract for what a session is called and what is recorded about it. A session has a
**title** (what it is about, below) and **launch facts** (who ran it, where, on what). The
title is set through the owning runtime; the launch facts are recorded by the launcher in
the [session index](session-index.md). Neither is a file name.

## Launch facts

| Fact | Meaning | Recorded by |
| --- | --- | --- |
| owner | `user` (the owner) or the agent: `assistant`, `ops`, `engineer` | the index, from the home it read |
| runtime | `claude`, `codex`, `pi` (and `copilot`, `openclaw` history) | the index adapter |
| place | the working directory (`cwd`) | the native record |
| kind | `chat` (owner present), `work`, `run` (unattended) | dev-server `agent-run`, via `ingest --launch` |
| portal | `term`, `desk` (the shared chat), `phone`, `none` | dev-server `agent-run` |
| model, account | the model and the account the launch resolved | `agent-run` (account from the resolver); else the transcript |
| when | first and last timestamps in the transcript | the index, from the transcript |

`ai-session list` and `show` print these; `list --owner AGENT` and `--search` find by them.
Before 2026-10-05 dev-server put these facts in a file name (`session-path`:
`~/sessions/Y/M/D/HHMM.kind.portal.model.who.place`) and filled that file with a raw copy of
the transcript (`agent-run`, the copy at the end; `ai` opened it with `less`). That was a
second session store holding raw JSON, against this repository's one-index contract, so the
code was wrong and was removed; the facts moved into the index.

# Automatic session naming

All agents and contexts may name **their own session** automatically when the task becomes
clear, and refresh their own generated title when scope materially changes. This includes
Pi roles (Assistant, Ops, Engineer), OpenRig control seats, Claude Code, Codex, editor chats, delegated
agents, headless workers, and personal/nonengineering work. No naming-only approval is
needed. This is permission to use available naming controls, not a claim every client
exposes one to the agent.

## One format everywhere

Every session title on every client uses one format. `bin/ai-title` formats and checks it;
`lib/ai_ecosystem/naming.py` is the only implementation.

```
[host/project] purpose(area): Description #ref · who · client · provider/model · type · YYYY-MM-DD
```

| Field | Value |
| --- | --- |
| `host` | Short host name where the session runs (`dev-server`), or `web` for ChatGPT and claude.ai. |
| `project` | Repository name (a worktree names its main repository), `home`, or `none`. |
| `purpose` | Engineering kinds from `ROLES.md` (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `loop`, `review`, `spike`, `forensics`, `ops`), or `chat`, `plan`, `research`, `write`, `admin`, `learn`, `personal`. |
| `area` | Commit scope for engineering; a one-word topic otherwise (`travel`, `acme`). `misc` when unknown. |
| `Description #ref` | Sentence case. `#ref` is the pull request or issue number when one exists. `purpose(area): Description #ref` is at most 80 characters. |
| `who` | Person or agent that started the session: the Unix user (`owner`, `assistant`, `ops`, `engineer`), or the launcher's `DEV_SESSION_WHO` (`loop#12`, `workers-issue-12@dev`). |
| `client` | `claude-cli`, `claude-desktop`, `claude-sdk`, `claude-vscode`, `claude-ai`, `codex-cli`, `codex-exec`, `codex-vscode`, `codex-app`, `chatgpt`, `pi`, `zed`, `copilot`, `vscode`. Add `:account` for a non-default account (`claude-cli:acme`). |
| `provider/model` | `anthropic/opus-5-5`, `openai/gpt-5-codex`, `openrouter/kimi-k2.6`, `local/...`. Launchers set `DEV_SESSION_PROVIDER` and `DEV_SESSION_MODEL`. The model is the one at session start. |
| `type` | `interactive`, `headless`, `subagent`, `seat` (OpenRig), `loop`, `scheduled`, `web` (ChatGPT, claude.ai), `cloud`. Launchers set `DEV_SESSION_TYPE`. |
| date | Date the session started. |

Example: `[dev-server/dev-platform] feat(platform): Unify session naming · owner · claude-desktop · anthropic/opus-5-5 · interactive · 2026-11-06`.

- Launchers set `DEV_SESSION_WHO`, `DEV_SESSION_ACCOUNT`, `DEV_SESSION_PROVIDER`, `DEV_SESSION_MODEL`
  and `DEV_SESSION_TYPE` when they start an agent.
- A session that another agent starts (a spawned worker, a delegated session, a cloud task)
  uses type `subagent` and `who` = `<worker-handle>@<parent-handle>`, for example
  `renamer@session-naming`. The parent sets the title right after the start, to the output of
  `ai-title format '<purpose(area): Description>' --client claude-desktop --type subagent --who <worker>@<parent> --cwd <its folder>`.
- Hooks and extensions add the context fields. A model changes only `purpose(area): Description #ref`;
  it never changes host, project, who, client, model, type or date. In the Claude desktop app it sends the full title that the hook gives it, because the app shows the title the tool sent. The Claude hook wraps a bare
  `purpose(area): ...` title (and repairs a damaged full title) on the next prompt. A title with no
  model-written part is replaced once per session, from the first prompt; injected client text such as
  "You are operating in a git worktree" is skipped.
- A title from before the scheme gets a purpose and area from evidence: branch kind and slug,
  old title, first prompts, then a model classification. `ai-title guess` is only the first guess.
  `chat` and `misc` are for sessions where no evidence points elsewhere.
- Do not put secrets, account identifiers, customer data, raw prompts or billing details
  in `what`. The formatter redacts obvious tokens; that is a backstop, not permission.
- Preserve native session/thread IDs, account selection, ownership and worktree bindings.
  Naming does not take over a session, resume it, change its scope, or authorize execution.
- Owner decision, 2026-11-06: all historical sessions are renamed to this format. A rename
  keeps the old title as `what`. Each bulk rename writes a backup first and skips live
  sessions. `ai-title check` reports titles that do not conform.

## Rename history

`ai-title rename [--store claude|codex|pi|copilot|all] [--home DIR] [--dry-run] [--backup-dir DIR]
[--skip-live-minutes 30]` renames every session in the local stores (`lib/ai_ecosystem/retitle.py`).

- It copies each file it changes to `~/.local/state/dev-platform/retitle-backup/<timestamp>/`
  (same relative paths) and writes `manifest.json` there before it changes anything.
- `ai-title rename --undo MANIFEST` reverses a run.
- It skips a session changed in the last 30 minutes and a title that already conforms, so a second run changes nothing.
- Claude: one `custom-title` and one `agent-name` line at the end of the transcript.
  Codex: `thread/name/set` when the app-server answers, otherwise `threads.name`/`title` and `session_index.jsonl`.
  Pi: one `session_info` line. Copilot: the `name:` key of `workspace.yaml`.
- Another Unix user runs it for the own home: `ai-title rename --home /home/<user>`.

## Use the owning runtime

| Surface | Supported path and boundary |
| --- | --- |
| Claude desktop (Code tab) | Load the deferred tool `mcp__ccd_session_mgmt__set_session_title` with ToolSearch, then call it with `session_id: "self"` and the full title the hook gives, with only `purpose(area): Description #ref` changed. A `PostToolUse` hook on that tool records the middle part; when the model sent a title without the other fields, or a middle part that is not standard, it tells the model the exact title to send again. The `Stop` hook blocks the end of a turn (at most twice in a session) until such a title exists and passes `naming.style_problems`. The app can put back its own old copy of a title; the hook reads the last short-form rename from the transcript and writes it again on each prompt. No hook event after a prompt can set a title, so an old title can show until the next prompt. |
| Claude Code CLI | Installed CLI `-n/--name` sets a new session's display name. The interactive `/rename` command is a user-facing native control; do not assume an agent can invoke slash commands as tools. |
| Codex | New threads are named by `hooks/codex-session-title.py` (SessionStart, UserPromptSubmit, PostToolUse, Stop) through the app-server control socket `~/.codex/app-server-control/app-server-control.sock`: WebSocket, JSON-RPC `thread/name/set`, the call that `/rename` and the desktop app use. It reads the thread table read-only to find the client (`cli`, `exec`, `vscode`, desktop app, subagent), never writes SQLite, never changes a conforming title and skips resumed threads. PostToolUse only wraps a model-written `purpose(area): Description`, so a long turn gets the full title at once. A spawned thread has no user prompt: its title comes from `agent_path`, and its who is `<nickname>@<parent area>`. `ai-guardrails install` links the hook and lists it in `hooks.json`. Codex runs a hook only after its hash is trusted: `codex_control.trust_hooks` writes that through the app-server config writer. Persona homes without a daemon trust the hook in the Codex hook review. |
| Pi | `integrations/pi/session-title.mjs` names a new session on `session_start` and on the first input, sets the terminal title, and gives the agent a `session_title` tool. Roles load it in `role-resources.mjs` with the role as `who`. `ai-guardrails install` copies it to `~/.pi/agent/extensions/session-title.ts` for plain `pi`. |
| OpenClaw (retired) | Not used. Its preserved sessions are archives and are never renamed. |
| Pi roles | The role launcher may give a new conversation its title (`ai-session conversation create --title`). Check the installed Pi for a native session-name control before using one. |
| OpenRig | Name the underlying harness conversation through a supported control. Rig names, seat IDs, member labels and native conversation titles are distinct; changing one does not prove the others changed. |
| VS Code / other clients | Use the client's exposed native naming action if available. Otherwise retain its automatic title or suggest a concise title; do not invent a rename API. |
| Filesystem index | `ai-session title` is an **index-only** display override. See [Session index](session-index.md). It never renames a native conversation. |

Confirm the returned label/title after a native operation when that interface supports a
read. Report an unavailable control accurately; do not claim successful native naming from
an index update, message send, terminal title or instruction alone.

## Launchers

Every launcher builds its title with `bin/ai-title format` and exports `DEV_SESSION_WHO`,
`DEV_SESSION_ACCOUNT`, `DEV_SESSION_PROVIDER`, `DEV_SESSION_MODEL` and `DEV_SESSION_TYPE`.

- **Loop headless worker** (`skills/loop/scripts/loop.sh`): purpose from the branch kind, area from
  the first issue scope path (then an `area:` label, then `repo`), who `loop#<issue>`, type `loop`.
  The title is one argv for `claude --name`, never shell code. `worker-run.py` passes the
  `DEV_SESSION_*` names to the worker. `resume` starts a new attempt; it does not rename or resume an
  existing native conversation.
- **OpenRig seats** (`bin/dev-workspace`): who is the seat name, type `seat`. OpenRig builds the
  harness command and always passes the seat name as `--name`, so a seat title is not set at launch.
  The environment goes into `<cwd>/.claude/settings.local.json` (Claude only; Codex has no
  per-seat environment). Hooks and the renamer set the title. The tmux window is renamed to
  `project:purpose(area)`; the rig and tmux session names stay.
- **Pi roles** (`bin/ai`, `lib/ai_ecosystem/role_launch.py`): the stored conversation title is
  `ai-title format --client pi`, who is the role. The launch JSON carries `sessionTitle`.
- **`ai-account run`**: exports `DEV_SESSION_ACCOUNT` and `DEV_SESSION_PROVIDER`.

## Web and desktop titles

On 2026-11-06 the owner renamed the sessions that live in apps and websites to the one
format. The procedure is below. Run it again to name new chats.

1. Claude desktop (Code tab). List sessions with `list_sessions` (include archived).
   Skip sessions where `isRunning` is true and the parent session.
2. Use `get_session` for `createdAt` and `model`. Decide `purpose(area)` for each session
   from its title, branch and folder. Do not leave `chat(misc)` unless nothing fits.
3. Build the title with `ai-title format "<purpose(area): Description>" --client claude-desktop
   --cwd <cwd> --provider anthropic --model <model> --type interactive --date <created>`.
   Let `ai-title` derive the project from the folder.
4. Set it with `set_session_title`.
5. ChatGPT and claude.ai. Use Claude in Chrome and the owner's sign-in. Host is `web`,
   project is `none` unless the chat clearly belongs to a project, client is `chatgpt` or
   `claude-ai`, type is `web`. Save the old titles to a CSV first.
6. List chats with the page's own read endpoints: `/backend-api/conversations` on ChatGPT and
   `/api/organizations/<org>/chat_conversations` on claude.ai. Rename with the page's own
   call: `PATCH /backend-api/conversation/<id>` (ChatGPT) or `PUT .../chat_conversations/<id>`
   (claude.ai). Do five first, check the result, then do the rest slowly.

Notes:

- The claude.ai sidebar can show a cached old title until the chat opens. The server value is
  the new one.
- The Claude desktop title store is separate from the CLI transcripts. See the earlier sections.
- Claude Code cloud sessions on claude.ai/code are renamed with the page's own call:
  `PUT /v1/code/sessions/session_<id>` with `{"title": ...}` and the header
  `anthropic-version: 2023-06-01`. List them with `GET /v1/code/sessions?statuses=archived`.
  Host is `cloud`, client is `claude-ai`. Rig seats use type `seat` and the seat name
  (`role@rig`) as who. Other cloud sessions use who `owner` and type `cloud`. Renaming keeps a
  session archived.
- ChatGPT Codex cloud had no tasks at the time of the run.
- New web chats are named by hand or by running this procedure again. No hook names them.

## Evidence

- Local `claude --help`, inspected 2026-09-24, documents `-n, --name <name>` as the display
  name shown in the prompt box, resume picker and terminal title.
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) and
  [interactive mode](https://code.claude.com/docs/en/interactive-mode).
- [Codex app-server](https://developers.openai.com/codex/app-server), `thread/name/set`.

These controls are version-dependent. Check the installed interface before expanding the
integration; naming must not weaken sandboxes, change credentials, or create another service.

## Machines without the platform

A machine without the dev-platform release (for example the laptop, the owner's desktop)
gets the same naming from one self-contained installer. It needs only `python3`.

1. On dev-server, write the installer: `bin/ai-title-bundle > ~/.local/share/dev-platform/naming-install.py`.
2. On the other machine, run: `ssh dev-server 'cat ~/.local/share/dev-platform/naming-install.py' | python3 - install`.
3. Check it: `python3 ~/.local/share/dev-platform-naming/bin/ai-title check "<a title>"`, or run the
   installer again with `status` in place of `install`.

The installer puts the formatter and hooks in `~/.local/share/dev-platform-naming`. It adds the
Claude Code hook to `~/.claude/settings.json` and to each `~/.claude-accounts/*/settings.json`.
The Claude Code CLI, the desktop app and the IDE extensions read these files. It adds the Codex
hook to `~/.codex/hooks.json`, and the naming rule and the owner's words
(`skills/develop/owner-words.md`, see `docs/owner-words.md`) to each global prompt file. It keeps all other
settings, backs up each changed file to `~/.local/state/dev-platform-naming/backup/`, and is safe
to run again after an update.

### Client machines: all the portable rules (the laptop)

On a client machine, local agents (the Claude desktop app, Claude Code, Codex and pi) must follow
the same rules as on dev-server. Zed needs nothing here: it opens projects on dev-server over SSH and
reads dev-server's homes. Use the client installer in place of `naming-install.py`. It does all that
`naming-install.py` does, and it also adds these portable parts:

- the STE writing standard from `skills/develop/ste100.md`, in its `ste100: begin/end` markers, in
  each global prompt file;
- the commit rule, and this rule: "Engineering work on a platform repository runs on dev-server over SSH";
- the Claude Code PreToolUse guard (`hooks/pre-tool-use-guard.sh`) in each Claude Code home;
- the global git hooks (`hooks/git`) through `git config --global core.hooksPath`.

It leaves out the parts that need dev-server: `dev-loop`, the `/opt` release, the platform skills and
the accounts. It does not change the Codex sandbox or approval settings, or any credential.

1. On dev-server, write the installer: `bin/ai-title-bundle --client > ~/.local/share/dev-platform/client-install.py`.
2. On the Mac, read the changes first: `ssh dev-server 'cat ~/.local/share/dev-platform/client-install.py' > ~/client-install.py`.
3. On the Mac, run it: `python3 ~/client-install.py install`.
4. Read the notes that it writes to stderr. Fix each note by hand, then run step 3 again.
5. Check it: `python3 ~/client-install.py status`. It writes `ok` when every part is in place.
6. Restart the Claude desktop app, Claude Code and Codex, so that they read the new files.

The installer replaces the `naming-install.py` block with its own block, so each prompt file has
one copy of the title rule. It wraps STE text that has no markers in the markers only when the text
is the same as `skills/develop/ste100.md`. Otherwise it leaves the text and writes a note. It sets
`core.hooksPath` only when it is unset or points into a dev-platform install. A repository that the
Mac's `~/.config/dev-platform/repos.conf` does not name is tier 3, so the guard and the git hooks
apply the strictest rules there. Backups go to `~/.local/state/dev-platform-naming/backup/`.
