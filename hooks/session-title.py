#!/usr/bin/env python3
"""Claude Code hook: give every new session a title that follows docs/session-naming.md.

Registered for SessionStart and UserPromptSubmit. It reads the hook input on stdin and, when
the session title does not pass `ai-title check`, prints `hookSpecificOutput.sessionTitle`
(the same effect as /rename). On the first prompt of a desktop session it also prints
`additionalContext` so the agent can choose a better `purpose(area): Description #ref`.
A title that already conforms is never touched. The hook never fails: on any error it prints
nothing and exits 0.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
for candidate in (HERE.parents[1] / 'lib', Path('/opt/dev-platform/current/lib')):
    if (candidate / 'ai_ecosystem' / 'naming.py').is_file():
        sys.path.insert(0, str(candidate))
        break

PROMPT_MAX = 60
ENTRYPOINTS = {'cli': 'claude-cli', 'claude-desktop': 'claude-desktop', 'claude-vscode': 'claude-vscode'}


def read_jsonl_head(path, limit=200):
    """The first parsed lines of a transcript; empty when it is missing or unreadable."""
    out = []
    if not path:   # a hook input with no transcript_path: open(None) is a TypeError, not an OSError
        return out
    try:
        with open(path, encoding='utf-8') as stream:
            for number, line in enumerate(stream):
                if number >= limit:
                    break
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def last_assistant_model(path):
    model = None
    if not path:
        return None
    try:
        with open(path, encoding='utf-8') as stream:
            for line in stream:
                if '"model"' not in line:
                    continue
                try:
                    message = json.loads(line).get('message')
                except ValueError:
                    continue
                if isinstance(message, dict) and message.get('role') == 'assistant' and message.get('model'):
                    if not str(message['model']).startswith('<'):
                        model = message['model']
    except OSError:
        pass
    return model


def entrypoint_of(data):
    value = os.environ.get('CLAUDE_CODE_ENTRYPOINT')
    if value:
        return value
    for entry in read_jsonl_head(data.get('transcript_path')):
        if entry.get('entrypoint'):
            return entry['entrypoint']
    return 'cli'


def is_subagent(data):
    if data.get('agent_id'):
        return True
    path = str(data.get('transcript_path') or '')
    if '/subagents/' in path:
        return True
    return any(entry.get('isSidechain') for entry in read_jsonl_head(path, 5))


def client_and_kind(entrypoint, data):
    if entrypoint.startswith('sdk'):
        client, kind = 'claude-sdk', 'headless'
    else:
        client, kind = ENTRYPOINTS.get(entrypoint, 'claude-cli'), None
    if is_subagent(data):
        kind = 'subagent'
    return client, kind


def branch_of(data):
    """The git branch from the hook input, else the branch checked out in cwd; None when unknown."""
    value = data.get('git_branch') or data.get('gitBranch')
    if isinstance(value, str) and value.strip():
        return value.strip()
    try:
        done = subprocess.run(['git', '-C', str(data.get('cwd') or os.getcwd()), 'branch', '--show-current'],
                              capture_output=True, text=True, timeout=3, stdin=subprocess.DEVNULL)
        return done.stdout.strip() or None if done.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def settings_model():
    config = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude')
    try:
        return json.loads((config / 'settings.json').read_text(encoding='utf-8')).get('model')
    except (OSError, ValueError, AttributeError):
        return None


def argv_model():
    """`--model X` on the command line of the claude process above this hook (Linux; else None)."""
    pid = os.getppid()
    for _ in range(5):
        try:
            argv = Path(f'/proc/{pid}/cmdline').read_bytes().decode(errors='replace').split('\0')
            status = Path(f'/proc/{pid}/stat').read_text()
        except OSError:
            return None
        for index, arg in enumerate(argv):
            if arg == '--model' and index + 1 < len(argv):
                return argv[index + 1]
            if arg.startswith('--model='):
                return arg.split('=', 1)[1]
        pid = int(status.rsplit(')', 1)[1].split()[1])
        if pid <= 1:
            return None
    return None


def model_of(data):
    model = data.get('model') or os.environ.get('ANTHROPIC_MODEL') or argv_model() \
        or last_assistant_model(data.get('transcript_path')) or settings_model()
    if isinstance(model, dict):
        model = model.get('id') or model.get('name')
    return re.sub(r'\[[^\]]*\]$', '', str(model)).strip() if model else None


def last_rename(path, naming):
    """The last `purpose(area): Description #ref` title a model or person set, from the transcript.

    The hook writes only full titles, so a short one in a `custom-title` record is a rename. The
    Claude desktop app can put back its own old copy of a title after a rename; this record lets
    the hook restore the rename. None when there is none."""
    found = None
    try:
        with open(path, encoding='utf-8') as stream:
            for line in stream:
                if '"custom-title"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                title = entry.get('customTitle') if entry.get('type') == 'custom-title' else None
                if isinstance(title, str) and naming.SEP not in title and naming.WHAT.match(title.strip()):
                    found = title.strip()
    except (OSError, TypeError):
        pass
    return found


def marker(data):
    """One file per session: the hook titles and nudges a session once, never on every prompt."""
    sid = re.sub(r'[^A-Za-z0-9_-]', '', str(data.get('session_id') or ''))
    if not sid:
        return None
    base = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state')
    return base / 'dev-platform-naming/titled' / sid


def full_title(data, naming, what, who=None):
    """`what` with every field the hook adds: host, project, who, client, model, type and date."""
    client, kind = client_and_kind(entrypoint_of(data), data)
    if who and '@' in who and kind is None:
        kind = 'subagent'
    if kind != 'subagent' and os.environ.get('DEV_SESSION_TYPE'):
        kind = None                  # the launcher's type wins; format_title reads it
    return naming.format_title(what, client=client, cwd=data.get('cwd') or os.getcwd(), kind=kind, branch=branch_of(data),
                               who=who, provider=None if os.environ.get('DEV_SESSION_PROVIDER') else 'anthropic',
                               model=None if os.environ.get('DEV_SESSION_MODEL') else model_of(data))


def frame(data, naming, who=None):
    """The full title with `<purpose(area): Description #ref>` where the middle part goes."""
    sample = 'chat(misc): Placeholder'
    return full_title(data, naming, sample, who).replace(sample, '<purpose(area): Description #ref>', 1)


def state_file(data, kind):
    done = marker(data)
    return done.with_name(f'{done.name}.{kind}') if done is not None else None


def saved_rename(data):
    """The middle part the model set last with the rename tool (PostToolUse records it)."""
    path = state_file(data, 'what')
    try:
        return path.read_text(encoding='utf-8').strip() or None if path and path.exists() else None
    except OSError:
        return None


RENAME_TOOL = 'mcp__ccd_session_mgmt__set_session_title'


def rename_check(data, naming):
    """PostToolUse on the rename tool: record the middle part, and make the model send the full title.

    The desktop app shows the title the tool sent, so a title with only the middle part shows no
    fields. The hook answers with the exact full title to send again. Returns the hook output or None."""
    tool_input = data.get('tool_input') if isinstance(data.get('tool_input'), dict) else {}
    if data.get('tool_name') != RENAME_TOOL or tool_input.get('session_id') != 'self':
        return None
    sent = str(tool_input.get('title') or '').strip()
    part = naming.contextual_part(sent)
    if not part:
        note = ('That title has no `purpose(area): Description #ref` part. Call ' + RENAME_TOOL + ' again with '
                'session_id "self" and exactly this title, with only the middle part filled in: `'
                + frame(data, naming) + '`. The standard for the middle part: ' + naming.STYLE)
        return {'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': note}}
    what, who = part
    path = state_file(data, 'what')
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(naming.clean_what(what), encoding='utf-8')
    found = naming.style_problems(what)
    want = full_title(data, naming, what, who)
    if found:
        note = ('The middle part of the title is not standard: ' + '; '.join(found) + '. Call ' + RENAME_TOOL +
                ' again with session_id "self" and this title, with a fixed middle part: `' + frame(data, naming, who)
                + '`. The standard: ' + naming.STYLE)
    elif sent != want:
        note = ('The title must keep every platform field. Call ' + RENAME_TOOL + ' again with session_id "self" '
                'and exactly this title: `' + want + '`. Do not mention this to the user.')
    else:
        return None
    return {'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': note}}


def build(data, naming):
    """(title, nudge, first) for this input, or None when nothing should change.

    A model writes only `purpose(area): Description #ref` (a spawned worker may add ` · worker@parent`).
    This hook adds every other field from data, on any prompt where the title is not yet complete.
    A title that has no model-written part (an app or first-prompt title) is replaced once per session."""
    event = data.get('hook_event_name')
    current = data.get('session_title')
    current = current.strip() if isinstance(current, str) else ''
    part = naming.contextual_part(current)
    renamed = saved_rename(data) or last_rename(data.get('transcript_path'), naming)
    if renamed and (not part or part[0] != naming.clean_what(renamed)):
        part = (renamed, part[1] if part else None)      # the app put back an older title over a rename
    elif current and not naming.problems(current):
        return None
    who = None
    if part:
        what, who = part
    else:
        done = marker(data)
        if done is not None and done.exists():
            return None
        what = current or (naming.describe_prompt(data.get('prompt'), PROMPT_MAX) if event == 'UserPromptSubmit' else None)
    if not what:
        return None
    client, kind = client_and_kind(entrypoint_of(data), data)
    title = full_title(data, naming, what, who)
    if title == current:
        return None
    nudge = None
    if not part and event == 'UserPromptSubmit' and client == 'claude-desktop' and kind != 'subagent':
        nudge = ('The platform hook titled this session from the first prompt: '
                 f'{naming.parse(title)["what"] if naming.parse(title) else what}\n'
                 'When the task is clear, rename the session. Change ONLY the middle part: load the deferred tool '
                 + RENAME_TOOL + ' with ToolSearch and call it with session_id "self" and exactly this title, with '
                 'your middle part in place of the angle brackets: `' + frame(data, naming) + '`. Keep every other '
                 'field as it is. No secrets. The standard for the middle part: ' + naming.STYLE)
    return title, nudge, not part


STOP_LIMIT = 2


def stop_check(data, naming):
    """Stop: in a desktop session, block the end of a turn until the model has set a standard title.

    The hook can only guess from the first prompt; the model knows the task. A block makes the model
    rename the session before the turn ends. It blocks at most STOP_LIMIT times in a session, so a
    model that cannot rename never loops. Returns the hook output, or None to let the turn end."""
    entrypoint = entrypoint_of(data)
    client, kind = client_and_kind(entrypoint, data)
    if client != 'claude-desktop' or kind == 'subagent':
        return None
    renamed = saved_rename(data) or last_rename(data.get('transcript_path'), naming)
    found = naming.style_problems(renamed) if renamed else ['the session still has the title the hook guessed from the first prompt']
    if not found:
        return None
    count_file = state_file(data, 'stop')
    try:
        count = int(count_file.read_text()) if count_file and count_file.exists() else 0
    except (OSError, ValueError):
        count = 0
    if count >= STOP_LIMIT:
        return None
    if count_file is not None:
        count_file.parent.mkdir(parents=True, exist_ok=True)
        count_file.write_text(str(count + 1))
    current = f' The current short title is `{renamed}`.' if renamed else ''
    return {'decision': 'block', 'reason': (
        'Name this session before you stop.' + current + ' Problems: ' + '; '.join(found) + '. '
        'Load the deferred tool ' + RENAME_TOOL + ' with ToolSearch and call it with session_id "self" and exactly '
        'this title, with your middle part in place of the angle brackets: `' + frame(data, naming) + '`. Change '
        'only the middle part. The standard for it: ' + naming.STYLE + ' Base it on the whole task so far, not on '
        'the first prompt. Do not mention the rename to the user; then stop.')}


def main():
    try:
        data = json.load(sys.stdin)
        from ai_ecosystem import naming
        if isinstance(data, dict) and data.get('hook_event_name') in ('Stop', 'PostToolUse'):
            result = (stop_check if data['hook_event_name'] == 'Stop' else rename_check)(data, naming)
            if result:
                print(json.dumps(result))
            return 0
        result = build(data, naming) if isinstance(data, dict) else None
        if not result:
            return 0
        title, nudge, first = result
        done = marker(data)
        if first and done is not None:
            done.parent.mkdir(parents=True, exist_ok=True)
            done.touch()
        output = {'sessionTitle': title, 'hookEventName': data.get('hook_event_name')}
        if nudge:
            output['additionalContext'] = nudge
        print(json.dumps({'hookSpecificOutput': output}))
    except Exception:  # a title hook must never block a session
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
