"""Readable text from native session transcripts (Claude Code, Codex, Pi). Never raw JSON.

render(runtime, path) returns (text, meta). meta carries what the transcript itself says
about the session: title, cwd, model, account, first and last timestamps. Anything that
looks like a credential is masked before it leaves this module.
"""
import json
from pathlib import Path
import re

TOOL_ARGS = 240
TOOL_RESULT = 600
SUMMARY = 1500

SECRETS = [
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)', re.S),
    re.compile(r'\bsk-ant-[A-Za-z0-9_-]{10,}'),
    re.compile(r'\bsk-(?:proj-|or-v1-|svcacct-)?[A-Za-z0-9_-]{20,}'),
    re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}'),
    re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}'),
    re.compile(r'\bglpat-[A-Za-z0-9_-]{20,}'),
    re.compile(r'\bxox[abposr]-[A-Za-z0-9-]{10,}'),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(r'\bAIza[0-9A-Za-z_-]{30,}'),
    re.compile(r'\bya29\.[0-9A-Za-z_-]{20,}'),
    re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
    re.compile(r'\bpplx-[A-Za-z0-9]{20,}'),
    re.compile(r'\b(?:hf|gsk|xai|npm|tskey|pk|sk|rk)_(?:live_|test_)?[A-Za-z0-9]{24,}'),
    re.compile(r'\btskey-[a-z]+-[A-Za-z0-9-]{16,}'),
    re.compile(r'\b\d{8,10}:AA[A-Za-z0-9_-]{30,}'),                       # Telegram bot token
    re.compile(r'(?i)(?P<keep>\bbearer\s+)[A-Za-z0-9._~+/=-]{16,}'),
    re.compile(r'(?i)(?P<keep>\bbasic\s+)[A-Za-z0-9+/=]{16,}'),
    # A password in a URL: scheme://user:password@host
    re.compile(r'(?P<keep>\b[a-z][a-z0-9+.-]*://[^\s/:@"\']*:)[^\s/@"\']{3,}(?=@)'),
    # name = value, name: value, "name": "value", for names that say what they hold, in any case and
    # with any prefix (client_secret, OPENAI_API_KEY, x-api-key, private_key, db_password ...).
    re.compile(r'(?i)(?P<keep>["\']?\b[A-Za-z0-9_.-]*(?:api[_-]?key|access[_-]?key|access[_-]?token|auth[_-]?token|'
               r'refresh[_-]?token|id[_-]?token|bot[_-]?token|session[_-]?token|secret|password|passwd|passphrase|'
               r'private[_-]?key|credentials?)\b["\']?\s*[:=]\s*["\']?)(?![\[{])[^\s"\',;}<>]{6,}'),
]
# One pass that only answers "is there anything to mask here?": cheap enough to run over a whole archive.
# Each pattern keeps its own flags inside the alternation, so this agrees with mask() exactly.
ANY_SECRET = re.compile('|'.join(
    ('(?i:' + p.pattern.replace('(?i)', '', 1) + ')') if p.flags & re.I else f'(?s:{p.pattern})' if p.flags & re.S
    else f'(?:{p.pattern})' for p in SECRETS).replace('?P<keep>', ''))
HIDDEN = '[secret hidden]'


def mask(text):
    for pattern in SECRETS:
        text = pattern.sub(lambda m: (m.groupdict().get('keep') or '') + HIDDEN, text)
    return text


def has_secret(text):
    """True when mask() would change the text. The hidden marker itself is never a hit."""
    for m in ANY_SECRET.finditer(text):
        if HIDDEN not in m.group(0):
            return True
    return False


def _clip(text, limit):
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + f' … ({len(text) - limit} more characters)'


def _args(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return _clip(' '.join(value.split()), TOOL_ARGS)
    if isinstance(value, dict):
        for key in ('command', 'cmd', 'file_path', 'path', 'pattern', 'url', 'query', 'description', 'prompt'):
            if isinstance(value.get(key), (str, list)):
                shown = value[key] if isinstance(value[key], str) else ' '.join(map(str, value[key]))
                return _clip(' '.join(shown.split()), TOOL_ARGS)
        value = ', '.join(f'{k}={v}' for k, v in value.items() if isinstance(v, (str, int, float, bool)))
    return _clip(' '.join(str(value).split()), TOOL_ARGS)


def _text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for item in content if isinstance(content, list) else []:
        if isinstance(item, dict) and isinstance(item.get('text'), str):
            parts.append(item['text'])
        elif isinstance(item, str):
            parts.append(item)
    return '\n'.join(parts)


def _when(stamp):
    if isinstance(stamp, (int, float)):
        import time
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(stamp / 1000 if stamp > 1e11 else stamp))
    if isinstance(stamp, str) and len(stamp) >= 16:
        return stamp[:16].replace('T', ' ')
    return ''


class _Out:
    def __init__(self):
        self.lines, self.meta, self.last_role = [], {}, None

    def turn(self, role, stamp, text):
        text = text.strip()
        if not text:
            return
        if role != self.last_role:
            self.lines.append(f'\n## {role}  {_when(stamp)}'.rstrip())
            self.last_role = role
        self.lines.append(text)

    def tool(self, name, args):
        self.lines.append(f'  → {name}: {_args(args)}')

    def result(self, text, error=False):
        text = _clip(text, TOOL_RESULT)
        if text:
            self.lines.append(('  ← error: ' if error else '  ← ') + text.replace('\n', '\n    '))

    def seen(self, stamp):
        if stamp:
            self.meta.setdefault('started_at', stamp)
            self.meta['updated_at'] = stamp

    def text(self):
        return mask('\n'.join(self.lines).strip() + '\n')


def _lines(path):
    with Path(path).open(errors='replace') as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                yield record


def _claude(path, out):
    for r in _lines(path):
        kind, stamp = r.get('type'), r.get('timestamp')
        out.seen(stamp)
        if isinstance(r.get('cwd'), str):
            out.meta.setdefault('cwd', r['cwd'])
        if kind in ('custom-title', 'summary') and isinstance(r.get('customTitle') or r.get('summary'), str):
            out.meta['title'] = r.get('customTitle') or r.get('summary')
        elif kind == 'ai-title' and isinstance(r.get('aiTitle'), str):
            out.meta['ai_title'] = r['aiTitle']
        if kind not in ('user', 'assistant') or r.get('isMeta') or r.get('isSidechain'):
            continue
        message = r.get('message') or {}
        if kind == 'assistant' and isinstance(message.get('model'), str):
            out.meta['model'] = message['model']
        content = message.get('content')
        if isinstance(content, str):
            if not content.startswith('<command-') and not content.startswith('<local-command'):
                out.turn(kind, stamp, content)
            continue
        for item in content if isinstance(content, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get('type') == 'text':
                out.turn(kind, stamp, item.get('text') or '')
            elif item.get('type') == 'tool_use':
                out.last_role = out.last_role or kind
                out.tool(item.get('name') or 'tool', item.get('input'))
            elif item.get('type') == 'tool_result':
                out.result(_text_of(item.get('content')), bool(item.get('is_error')))


def _codex(path, out):
    for r in _lines(path):
        stamp, payload = r.get('timestamp'), r.get('payload') or {}
        out.seen(stamp)
        if r.get('type') == 'session_meta':
            if isinstance(payload.get('cwd'), str):
                out.meta.setdefault('cwd', payload['cwd'])
            continue
        if r.get('type') == 'turn_context' and isinstance(payload.get('model'), str):
            out.meta['model'] = payload['model']
        if r.get('type') != 'response_item':
            continue
        kind = payload.get('type')
        if kind == 'message' and payload.get('role') in ('user', 'assistant'):
            text = _text_of(payload.get('content'))
            if text.lstrip().startswith(('<environment_context>', '<user_instructions>', '# AGENTS.md')):
                continue
            out.turn(payload['role'], stamp, text)
        elif kind in ('function_call', 'custom_tool_call', 'local_shell_call'):
            out.tool(payload.get('name') or 'shell', payload.get('arguments') or payload.get('input') or payload.get('action'))
        elif kind in ('function_call_output', 'custom_tool_call_output'):
            output = payload.get('output')
            if isinstance(output, dict):
                output = output.get('content') or output.get('output') or ''
            out.result(_text_of(output) if not isinstance(output, str) else output)


def _pi(path, out):
    for r in _lines(path):
        kind, stamp = r.get('type'), r.get('timestamp')
        out.seen(stamp)
        if kind == 'session':
            if isinstance(r.get('cwd'), str):
                out.meta.setdefault('cwd', r['cwd'])
            out.meta['native_id'] = r.get('id')
        elif kind == 'model_change':
            out.meta['model'] = f"{r.get('provider')}/{r.get('modelId')}"
        elif kind == 'custom' and r.get('customType') == 'dev-platform-binding' and isinstance(r.get('data'), dict):
            data = r['data']
            for key, field in (('accountRef', 'account'), ('conversationId', 'conversation_id'), ('agent', 'agent')):
                if isinstance(data.get(key), str):
                    out.meta[field] = data[key]
        elif kind == 'session_info' and isinstance(r.get('name'), str):
            out.meta['title'] = r['name']
        elif kind == 'compaction' and isinstance(r.get('summary'), str):
            out.lines.append('\n(earlier turns were compacted; their summary:)\n' + _clip(r['summary'], SUMMARY))
            out.last_role = None
        elif kind == 'message':
            m = r.get('message') or {}
            role = m.get('role')
            if role == 'user':
                out.turn('user', stamp, _text_of(m.get('content')))
                out.meta.setdefault('first_prompt', _text_of(m.get('content')))
            elif role == 'assistant':
                for item in m.get('content') if isinstance(m.get('content'), list) else []:
                    if not isinstance(item, dict):
                        continue
                    if item.get('type') == 'text':
                        out.turn('assistant', stamp, item.get('text') or '')
                    elif item.get('type') == 'toolCall':
                        out.last_role = out.last_role or 'assistant'
                        out.tool(item.get('name') or 'tool', item.get('arguments'))
            elif role == 'toolResult':
                out.result(_text_of(m.get('content')), bool(m.get('isError')))


READERS = {'claude': _claude, 'codex': _codex, 'pi': _pi}


def render(runtime, path):
    reader = READERS.get(runtime)
    if reader is None:
        raise ValueError(f'no readable form for {runtime} sessions')
    out = _Out()
    reader(path, out)
    meta = {k: v for k, v in out.meta.items() if isinstance(v, (str, int, float))}
    for key in ('title', 'ai_title', 'first_prompt'):
        if key in meta and isinstance(meta[key], str):
            meta[key] = mask(' '.join(meta[key].split()))[:200]
    return out.text(), meta
