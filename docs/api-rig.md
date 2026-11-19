# The API rig

A project's team that runs on dev-server with nobody at the keyboard, on API keys alone, through
OpenRouter. No Claude Code or Codex seat and no subscription is involved. One supervisor per
project, `api-rig`, runs the development lifecycle again and again:

1. **Spend.** It checks the OpenRouter key's usage against a daily and a monthly cap.
2. **Team.** It keeps the project's Pi team running: a control seat, two overseers, and a fresh
   worker for each task.
3. **Loop.** It works the goal's rig branch with the loop. Each finished worker gets the
   repository's check, the overseers review it, and the control seat folds it.
4. **Steps.** When everything dispatched is folded, the control seat runs the staging deploy, the
   runner and the journeys through the project's own helpers.
5. **Merge request.** A green head gets its merge request written. Landing stays the owner's.

The long seats, the control and the overseers, re-open on a fresh context at a cadence, from a
checkpoint file. No context window grows past it.

This page covers the shape, the accounts, the model file, the cadence, the caps, the holds, and
how to switch a project over and back.

## The shape

`rig-shape write <project> review --all pi` writes the team. Every seat runs on Pi, and its model
is its role's line in the model file, resolved for the `openrouter` runtime. That runtime takes
only OpenRouter families, so a seat can never fall back to a subscription.

| Seat | Role line | Model with today's defaults |
| --- | --- | --- |
| Control (`control.lead`) | `rig control` (`implementation-high`) | DeepSeek V4 Pro (`deepseek/deepseek-v4-pro-0813`), high |
| Overseer (`review.overseer`) | `rig overseer` (`overseer-max`) | Claude Fable 5.1 (`anthropic/claude-fable-5.1`), max |
| Second overseer (`review.second`) | `rig second overseer` (`overseer.2-max`) | GPT-6 Astra Pro (`openai/gpt-6-astra-pro`), max |
| Each worker | `rig worker` (`implementation-xhigh`); `judgment and prose` for spec, decision, privacy and security tasks; `mechanical` for documentation | DeepSeek V4 Pro, xhigh |
| `ask_advice`, on every seat and worker | `advice` (`judgment-max`) | Claude Fable 5.1 |

- **Two families.** The two overseers are the first and second families of the `overseer` tier.
  `rig-shape` refuses a `review` team whose two overseers resolve to one maker.
- **Workers.** A worker is the loop's own one-task headless Pi run by default. Each task gets a
  new session, with a turn cap, a billed-token cap and a wall-time cap. Set `workers.mode` to
  `seat` for OpenRig worker seats instead (`dev-workspace add-worker pi`). The launcher refuses
  those in a professional checkout, because OpenRig writes its context into the worktree.
- **What every Pi process loads.** Each seat and worker loads two extensions from its own Pi
  agent folder.
  - `seat-guard.mjs` runs the platform's guard script before every shell command, because Pi has
    no hooks. It refuses what Claude Code's hook refuses: pushes to protected branches, history
    rewrites, merges into the base, restarts.
  - `advice-tool.mjs` is `ask_advice`, a second opinion from the `advice` model through the same
    key. Its cost counts against the caps.
  - A headless worker also loads `worker-limits.mjs`. Over its turn cap or billed-token cap, the
    worker writes `.worker-blocked.md` and stops.

`build` and `solo` work as before. Claude Code and Codex seats work as before for every other
project.

## Accounts and the key

The key is the registry's `openrouter` account, of kind api-key. It is typed once on dev-server
with `ol-login openrouter`, into root's store at `/etc/dev-server/accounts/openrouter.key`.
`ol-login status` shows it verified, with its credit.

The unit `api-rig@<engagement>.service` runs as owner. It receives the key as a systemd credential
(`LoadCredential=openrouter:...`) and hands it on by name to two places only:

- **The rig's own OpenRig daemon.** It has its own state folder
  (`~/.local/state/dev-platform/api-rig/openrig`) and port (7533), separate from the owner's
  daemon. It also has its own tmux server (`~/.local/state/dev-platform/api-rig/tmux-7533`). A
  seat's pane takes its environment from the tmux server, so the server must be the one this
  daemon starts with the key. OpenRig then passes only the declared provider's key to each Pi
  seat.
- **The loop, for headless workers.** The worker supervisor passes `OPENROUTER_API_KEY` by name
  when `LOOP_RUNTIME=pi`, and never as an argument.

No key is written to a repository, a log, a spec or a prompt. One exposure remains: a Pi seat's
own shell tool inherits the key, so a seat could print it. The caps and the key's own credit
limit on OpenRouter bound the damage. Give the key a credit limit on OpenRouter's site.

Billing is metered. The registry's resolver never picks a metered account by itself. The rig
names `openrouter` and confirms the billing (`--metered-ok`). The owner gives that yes when he
enables the unit with his password.

## The model file

OpenRouter is the centre of the ecosystem (owner, 2026-10-12). Every tier lists its OpenRouter
families first and the Claude and Codex subscriptions last. Claude Code and Codex skip families
they cannot run, so their sessions resolve as before. `bin/pstack-model defaults` prints the
default file:

```
tier judgment: openrouter:anthropic/claude-fable-5.1, openrouter:openai/gpt-6-astra-pro, claude-opus-5-5, codex:gpt-6.1-sol, claude-fable-5-1
tier implementation: openrouter:deepseek/deepseek-v4-pro-0813, openrouter:deepseek/deepseek-v4.1-flash, codex:gpt-6.1-sol, claude-opus-5-5
tier mechanical: openrouter:deepseek/deepseek-v4.1-flash, openrouter:deepseek/deepseek-v4-flash, claude-haiku-4-5
tier overseer: openrouter:anthropic/claude-fable-5.1, openrouter:openai/gpt-6-astra-pro, codex:gpt-6.1-sol, claude-fable-5-1
advice: judgment-max
rig control: implementation-high
rig overseer: overseer-max
rig second overseer: overseer.2-max
rig worker: implementation-xhigh
```

The pieces work like this:

- **Families.** `openrouter:<maker>/<model>` is a model OpenRouter serves.
- **Runtimes.** `pstack-model resolve '<role>' --runtime pi` answers for Pi, taking OpenRouter
  first. `--runtime openrouter` is the API rig's runtime: OpenRouter families only.
- **Panels.** `.n` in a tier slug counts only the families the asking runtime can run, so a
  Claude Code panel keeps a second family.
- **The loop.** `LOOP_MODEL` accepts a model, a tier slug such as `implementation-high`, or a
  role name.
- **Changing it.** `/setup-pstack` detects OpenRouter families from OpenRouter's model list and
  Pi's catalog, and writes the file.

**The machine's file still has the old tiers.** `/etc/dev-platform/pstack-models.md` comes from
`~/dev/dev-server/etc/pstack-models.md` and holds no OpenRouter family yet. Until `/setup-pstack`
writes the OpenRouter tiers there and bootstrap installs them, `rig-shape write ... --all pi`
refuses with "no OpenRouter model for 'rig control'". Set the model file before switching a
project.

## The cadence

The control and overseer seats re-open on a fresh context when any of these is due:

| Setting in `cadence` | Default | Meaning |
| --- | --- | --- |
| `per_fold` | `true` | a child was folded since the seat opened |
| `turns` | 20 | turns in the seat's current Pi session |
| `tokens` | 250000 | the seat's current context, read from the last request's tokens |

When a rotation is due and the seat is idle, the supervisor asks the seat to write its
checkpoint, `.run/handoff-<seat>.md` in the engagement folder. Once the file is newer than the
request, it removes the seat and adds it back from the same member of `rig.yaml`. Then it tells
the fresh seat to read its checkpoint, `dev-loop status` and the plan. If a seat does not write
its checkpoint after three asks, it is re-opened anyway and the room is told. Workers are fresh
for every task.

## The caps

`caps.day_usd` and `caps.month_usd` are dollars on the OpenRouter key, per UTC day and month.

- **The reading.** Each pass refreshes the key's usage (`sudo -n ol-login-root usage`, no
  password needed) and reads `/var/lib/dev-server/usage/openrouter.json`. OpenRouter's own daily
  and monthly figures win. `ol-login-root` records them from this change on, live after the next
  bootstrap. Until then, spend is the difference from the first reading of the window this rig
  recorded.
- **Over a cap.** The rig writes steer `pause`, stops running workers, aborts every Pi seat's
  turn, and tells the room once. The hold clears by itself when spend is under the caps again.
- **No current reading.** Spend is unknown, never zero. A reading missing or older than 15
  minutes holds the same way.
- **Lag.** OpenRouter can report a call's cost late, and a cap stops the next dispatch, not the
  call in flight. Keep the caps below the key's own credit limit, and below the account's prepaid
  balance: an empty balance refuses every request whatever the key's limit says.

## Holds

A hold is quiet: one line in the room, nothing dispatched, no seat prompted. A cap or unknown
spend clears by itself. These need the owner:

| Hold | When |
| --- | --- |
| `check` | the repository's check failed twice on the same task |
| `deploy` | the staging deploy failed once |
| `credits` | a seat's latest reply is OpenRouter's 402: the account's prepaid credits are spent. The key's own limit can still show room, so the spend reading alone does not catch it. Add credits at openrouter.ai/settings/credits, then release |
| `key` | a seat's latest reply is OpenRouter's 401 or 403: re-enter the key with `ol-login openrouter`, restart the unit, then release |
| `owner` | `api-rig hold <project> [reason]` |

`api-rig release <project>` clears a hold, resets the check counts and writes steer `go`. A first
check failure goes back to the same worker on the same branch. The failure becomes the brief's
last section, and the loop resumes the worker.

## The governance loop: you, the company, the company agent, the rig

The rig builds. People decide. Three channels carry the decisions:

- **Records in.** Drop a record in the engagement's `inbox/`: an email, a meeting's notes, an
  insurer's letter, counsel's edits. The control seat distills it into ranked candidates in the
  incoming file of the repository (`~/.local/state/dev-platform/incoming/<repo>.html`), and
  nothing is filed. To promote a candidate, paste its block into an intake session. Intake writes
  the specification change, the tasks, and a decision draft marked `Status: proposed`, then
  stops. In the Talk room, a message beginning `Record:` from you or a
  listed staff account becomes an inbox record.
- **Asks out.** Every question the rig needs a person for is an ask with an ID: A1, A2 and so
  on. Each says what it unblocks, the options and a recommendation. The rig raises one for each
  proposed decision that holds tasks, and for each hold only you can release. The control seat,
  the overseers or the company agent can raise one with `api-rig ask`. `api-rig asks <project>` lists them.
- **Answers back.** Answer on dev-server:

  ```bash
  api-rig answer <project> A7 accept it, 30 days
  ```

  Or answer in the company's Talk room, when `api-rig.json` names one. The rig posts each ask as
  its own message. A reply to it, or a message beginning `A7`, from one of your listed Talk
  accounts answers it. The company agent sits in the same room. Its job is to press you and the company for
  the open asks, and it may relay an answer only by quoting your own message (`A7 per #<message
  id>`). The rig fetches that message, checks you wrote it, and takes your words, not the relay's.
  A relay of anyone else's message is refused.

An answer reaches the control seat as a record (`.run/answers/A7.md`). Accepting a decision stays
your act: the seat writes your words and the date into the decision record. It sets
`Status: accepted` only when your words accept it.

The loop never dispatches a task until every decision it cites is accepted, cited by a
`docs/decisions/` path or a `Decision:` line. Tasks labeled `legal`, `insurance`, `privacy`,
`payments` or `policy` (the `governed_labels` setting) also need an accepted decision. The overseer seats can
also be reached directly on dev-server through OpenRig (`rig send`, `rig tui` with the rig's two
variables).

To connect the room:

1. Create a Nextcloud user for the rig.
2. Store its login once:

   ```bash
   ol-login nextcloud-rig
   ```

   It asks for the user and the app password in a hidden prompt.
3. Set `talk` in `api-rig.json`: the Nextcloud address, the room's token, your Talk account IDs as
   `owners`, the staff who may send records as `staff`, and the company agent's user as `relay`.
4. Run `api-rig switch` again. It installs a per-project drop-in that hands the login to that
   project's unit alone.

## The lifecycle and api-rig.json

`api-rig.json` sits in the engagement folder beside `rig.yaml`, tracked in the same history.
Every key is optional:

| Key | Default | Meaning |
| --- | --- | --- |
| `goal` | none | the rig branch to start when none is open; an open one is used as it is |
| `caps` | `{"day_usd": 15, "month_usd": 200}` | above |
| `cadence` | above | above |
| `workers` | `{"mode": "headless", "cap": 2, "max_seconds": 2700, "max_turns": 80, "max_tokens": 3000000}` | concurrent workers and each one's caps; tokens are billed tokens |
| `steps` | `{"deploy": [], "runner": [], "journeys": []}` | the project's helpers, as argument lists, run from the rig worktree; `[]` skips a step |
| `tag_prefix` | `staging-` | the deploy tags the head `staging-<n>`, a local tag |
| `poll_seconds`, `nudge_minutes`, `seat_wait` | 60, 30, 120 | pass interval; how often an unanswered request to a seat is repeated (three times, then the room); how long a re-opened seat may take to be ready |
| `openrig_home`, `port` | above | the rig's daemon |
| `pi_models` | none | a Pi `models.json` given to every seat and worker, such as a custom endpoint; no key |
| `governed_labels` | `["legal", "insurance", "privacy", "payments", "policy"]` | task labels that need an accepted decision before dispatch |
| `talk` | none | the company's Talk room for asks and answers: `{"url", "room", "host", "owners", "staff", "relay"}` |

Each pass of `api-rig run` does the following:

1. Gate on spend.
2. Bring the daemon and the team up fresh if they are down.
3. Start the goal branch if needed.
4. Dispatch (`dev-loop go`, then `tick`).
5. Check each finished worker.
6. Send each passing child to the control seat as `Review #N`.
7. Ask the control seat to run intake when the plan is empty.
8. Drive the steps once every task is folded and none is ready.
9. Rotate the long seats.

The control seat runs the steps as `api-rig step <project> deploy|runner|journeys`. That command
runs the configured helper with `API_RIG_TAG`, `API_RIG_HEAD` and `API_RIG_STEP` set, and appends
the result to `.run/api-rig-steps.jsonl`.

- A failed runner or journeys run sends the control seat to write fix tasks.
- A failed deploy holds.
- When all three pass on a head, the rig runs `dev-loop close` to write `pr.md` and tells the room
  "merge request ready", with the owner's landing command.

Files in the engagement folder's `.run/`: `api-rig-state.json`, `api-rig.log`,
`api-rig-steps.jsonl`, `handoff-<seat>.md`.

## Switching a project over and back

Before the first switch:

1. **Land and activate this platform change.** The unit runs
   `/opt/dev-platform/current/bin/api-rig`.
2. **Set the model file with OpenRouter families.** Use `/setup-pstack`, commit it in
   `~/dev/dev-server`, and run the owner's `sudo ./bootstrap.sh`.
3. **Write `api-rig.json`.** At least `steps`. Add `goal` when no rig branch is open.

Then, in a terminal, the owner runs:

```bash
api-rig switch <project> --to api
```

It writes the `review` shape with every seat on Pi and records it in the engagement folder's
history. It writes a default `api-rig.json` if there is none. Then it installs and enables
`api-rig@<engagement>.service`, and sudo asks for the owner's password. `--dry-run` prints the
commands without running them.

Back to the subscription team:

```bash
api-rig switch <project> --to subscription
```

It disables and stops the unit, which stops the rig's daemon and seats. Then it writes the
`build` shape (a Claude control seat and a Codex overseer). The loop's ledger, the rig branch and
the checkpoints stay as they are.

## Dispatching by hand

Never run plain `dev-loop go` on a project the API rig runs: it starts Claude workers on a subscription. Use
`api-rig go <project>`, which dispatches with the rig's Pi workers, caps and governed labels. The rig itself dispatches on
every pass while the steer says go. Note that `api-rig go` needs the OpenRouter key in the environment; from a terminal
the unit's key is not there, so it refuses and the rig's next pass dispatches instead.

## Watching it

```bash
api-rig status <project>
```

```bash
TMUX_TMPDIR=~/.local/state/dev-platform/api-rig/tmux-7533 tmux attach -t control-lead@engineer-<project>
```

```bash
OPENRIG_HOME=~/.local/state/dev-platform/api-rig/openrig OPENRIG_PORT=7533 rig ps --nodes
```

`rig status`, snapshots, `rig parked` and `rig down` work on Pi seats with the same two variables.
The room (`/var/lib/dev-server/chat`) carries every hold, release and merge request. The rig's log
is `.run/api-rig.log`.

## What was proven, and what was not (2026-10-12)

**Offline, with a local stand-in for OpenRouter.** Real Pi 1.0.4 seats and workers ran under a
real OpenRig 0.6.1 daemon. A scripted stand-in served the OpenAI-style and Anthropic-style APIs
that Pi uses for OpenRouter, and it lives in `tests/support/mock_openrouter.py`. On a sample
repository:

1. A headless Pi worker took task #1. It built the change, committed, checked and wrote its PR
   file.
2. The supervisor's check passed. The control seat asked both overseers, and Fable and Astra each
   answered `pass #1`. The control seat folded.
3. All three long seats wrote checkpoints, re-opened fresh and read them back.
4. The control seat ran deploy, runner and journeys through `api-rig step`. The room got "merge
   request ready".
5. With task #2 ready and spend raised over the daily cap, the next pass held. It wrote steer
   `pause`, dispatched nothing, and told the room. The hold cleared when the cap was raised.
6. An OpenRig Pi worker seat then took task #2 the same way, through review, fold, the steps and
   a second "merge request ready".

The guard refused `git push origin main` inside a real Pi run. `tests/test_api_rig.py` and the
other tests cover the rest.

**Live, on the owner's key.** DeepSeek V4.1 Flash answered one turn on the OpenRouter key
through the launcher (`agent engineer` with `OL_ACCOUNT=openrouter`).

**Not yet run.** A live rig under the unit has not run. It needs the owner to land and activate
this change, set the model file, and switch a sample project. No DeepSeek worker has written real
code on a real task, and Fable and Astra have not given a real review verdict.

## Known limits

- **Worker seats.** They work only in personal repositories. Professional ones use headless Pi
  workers, which is the default.
- **Seat shells.** A seat's shell tool can read the key.
- **Spend lag.** The cap acts on OpenRouter's reported spend, which can lag.
- **The roles.** Assistant, Ops and Engineer still start on the OpenAI subscription (their `<role>
  start` lines). Moving them to OpenRouter needs the launcher, `agent-run`, to resolve an
  OpenRouter start model. That is a separate change in `~/dev/dev-server`.
