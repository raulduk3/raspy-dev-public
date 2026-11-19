# Usage

`ai-usage` (and `ol-login status`) shows what each account has left, from one record:
`/var/lib/dev-server/usage/ACCOUNT.json`, user owner, group agents. `ai-usage --json` gives
the structured view. Account switches are in `/var/lib/dev-server/accounts/rotations.log`
(root's).

## Where readings come from

| Account | Source | Freshness |
| --- | --- | --- |
| Anthropic (Claude) | `ol-status`, the status line of every session: Claude Code hands it a `rate_limits` object (five-hour and seven-day windows) on each render of a paid session, and it keeps that reading for the session's `OL_ACCOUNT` | Only while a session runs on that account; a snapshot with an age |
| OpenAI (Codex) | `ol-login-root usage`: a short-lived `codex app-server` with the stored login, `account/rateLimits/read`, no thread or turn | Read before each OpenAI launch (at most ten minutes old) and by `ol-login status` |
| OpenRouter | `ol-login-root usage`: the key's own `/api/v1/key` (credits used, limit, remaining, and OpenRouter's spend for its current UTC day and month, which the API rig's caps read; see api-rig.md) | As above |
| z.ai, GitHub | Not reported | — |
| OpenRig Claude seats | OpenRig's own status line cache (`~/.openrig/state/provider-usage/`, one file per seat), attributed to the account the seat was launched on (`usage/seats/SEAT`, written by the seat launcher); a reading fresher than the record joins the record | When `ai-usage` runs |

A seat launched by OpenRig runs OpenRig's status line, not `ol-status`, because OpenRig
writes a project-level `.claude/settings.local.json` and project-level wins; hence the
second source. Stock OpenRig 0.5.14 discarded every window (it expected a string reset
time; Claude sends a number); the patched runtime normalizes both.

## Reading it honestly

- A window whose reset time has passed is dropped: its percentage says nothing about now.
- No reading is `unknown`, never zero. The resolver ranks unknown after any known
  remainder and never treats it as exhausted.
- Every reading carries `captured` and `by`; the table shows its age (`read 12m ago`).
- Only real readings are written: a render with no rate limits leaves the last one.
- Nothing but the account, the time and the windows (or credits) is ever written: no
  session id, no transcript path, no credential.
