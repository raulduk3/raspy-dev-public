#!/usr/bin/env python3
"""Codex hook (SessionStart, UserPromptSubmit, PostToolUse, Stop): give a new thread a title in the platform format.

The hook names the thread through the app-server control socket (`thread/name/set`), the same
call the TUI `/rename` and the desktop app use. It never writes SQLite or the session index.
A title that passes `ai-title check` is never changed. A resumed thread keeps its title.
The hook prints nothing and always exits 0: a naming failure must never stop a Codex turn.
See docs/session-naming.md.
"""
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from ai_ecosystem import codex_control, naming  # noqa: E402


def first_line(text, limit=70):
    return naming.describe_prompt(text, limit) or ''


def choose_what(event, current, payload, row, home=None):
    """(what, who) for this event, or None when it should not name the thread.

    A model writes only `purpose(area): Description #ref`; the hook wraps it on the next event,
    PostToolUse included, so a long turn shows the full title right after the model renames it.
    A spawned thread is named from its agent path, nickname and parent; it has no user prompt."""
    if current and not naming.problems(current):
        return None
    spawn = codex_control.spawn_of(row['source']) if row else None
    from_spawn = codex_control.subagent_part(spawn, home) if spawn else None
    part = naming.contextual_part(current)
    if part:                                 # the model or owner wrote purpose(area): ...; wrap it
        return part[0], part[1] or (from_spawn[1] if from_spawn else None)
    if from_spawn:
        return from_spawn
    if event == 'PostToolUse':
        return None                          # only wraps; the first name comes from a prompt or Stop
    if current and naming.parse(current) is None and 'Untitled session' not in current:
        return current, None                 # a name Codex or the owner chose; keep it as the description
    if event == 'UserPromptSubmit':
        return first_line(payload.get('prompt')), None
    if event == 'Stop':
        return (first_line(row['first_user_message']) if row else ''), None
    return None


EVENTS = ('SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop')


def run(payload, home=None, setter=codex_control.set_thread_name):
    thread_id = payload.get('session_id')
    event = payload.get('hook_event_name')
    if not thread_id or event not in EVENTS:
        return None
    if event == 'SessionStart' and payload.get('source') in ('resume', 'clear'):
        return None
    row = codex_control.thread_row(thread_id, home)
    current = ((row['name'] if row else '') or '').strip()
    chosen = choose_what(event, current, payload, row, home)
    if not chosen or not chosen[0]:
        return None
    what, who = chosen
    title = codex_control.title_for(thread_id, what, row=row, cwd=payload.get('cwd'), home=home,
                                    model=payload.get('model'), who=who)
    if naming.problems(title) or title == current:
        return None
    setter(thread_id, title, codex_control.socket_path(home))
    return title


def main():
    try:
        payload = json.load(sys.stdin)
        if os.environ.get('CODEX_TITLE_DEBUG'):
            with (codex_control.codex_home() / 'session-title.log').open('a') as handle:
                handle.write(json.dumps(payload)[:400] + '\n')
        run(payload if isinstance(payload, dict) else {})
    except Exception as error:     # noqa: BLE001 - a hook must not break the turn
        try:
            log = codex_control.codex_home() / 'session-title.log'
            with log.open('a') as handle:
                handle.write(f'{type(error).__name__}: {error}\n')
        except OSError:
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
