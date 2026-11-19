"""Count the verbs in the prompts that the owner typed, from local Claude, Codex and Pi transcripts.

    ai-prompt-verbs [--project acme] [--since 2026-10-01] [--until 2026-11-08T13:05] [--json]
    ai-prompt-verbs --rows prompts.jsonl          # count rows saved earlier (agent, text, src, dup)

Extraction (one row for each prompt the owner typed):

  Claude  ~/.claude/projects/*<project>*/*.jsonl and ~/.claude-accounts/*/projects/...: rows with
          type "user" and origin.kind "human", and slash commands with their arguments. Sidechain,
          isMeta, compact summaries, tool results, task notifications, messages from other sessions
          and worker briefs are not prompts.
  Codex   ~/.codex/sessions and ~/.codex/archived_sessions: threads whose session_meta has
          thread_source "user" (and a cwd that contains the project); user input_text that does
          not start with "<" or "# AGENTS.md".
  Pi      ~/.pi/agent/sessions: message rows with role "user" in sessions whose cwd contains the
          project.

Then a repeated text counts once, and a prompt longer than 3,000 characters (a paste) is removed.

The count uses word forms, not a language model: a prompt "has" a verb when one of its forms
occurs as a word. Code, quoted commands, paths and links are removed first. A prompt is "only
vague" when it has a vague verb and no specific verb from the SPECIFIC list (base forms only).
"""
import argparse
import collections
import datetime
import json
import re
from pathlib import Path

LONG = 3000


def _forms(*words):
    return re.compile(r'\b(' + '|'.join(re.escape(w).replace(r'\ ', r'\s+') for w in words) + r')\b', re.I)


# The vague verbs of the 2026-11-08 count. "do" leaves out its use as an auxiliary.
VAGUE = {
    'make': _forms('make', 'makes', 'making', 'made'),
    'do': re.compile(r"\b(do|does|doing|did|done)\b(?!\s*(not|n't|you|we|i|it|they|that\s+mean))", re.I),
    'get': _forms('get', 'gets', 'getting', 'got', 'gotten'),
    'ensure / make sure': _forms('ensure', 'ensures', 'ensuring', 'ensured', 'make sure'),
    'improve': _forms('improve', 'improves', 'improving', 'improved'),
    'polish': _forms('polish', 'polished', 'polishing'),
    'fix': _forms('fix', 'fixes', 'fixing', 'fixed'),
    'harden': _forms('harden', 'hardened', 'hardening'),
    'stabilize': _forms('stabilize', 'stabilise', 'stabilized', 'stabilizing'),
    'integrate': _forms('integrate', 'integrated', 'integrating'),
    'align': _forms('align', 'aligned', 'aligning'),
    'look at': _forms('look at', 'looked at', 'looking at', 'look into'),
    'assess': _forms('assess', 'assessed', 'assessing'),
    'clean up': _forms('clean up', 'cleaned up', 'cleaning up', 'cleanup'),
    'finalize': _forms('finalize', 'finalise', 'finalized', 'finalizing'),
    'handle': _forms('handle', 'handled', 'handling'),
    'work on': _forms('work on', 'working on', 'worked on'),
    'provide': _forms('provide', 'provides', 'providing', 'provided'),
}
SPECIFIC = ('write push deploy merge commit build run test add remove delete update create install restart '
            'read search find rename move copy send start stop check review compare explain draft generate '
            'configure connect fold land save continue resume revert replace document port migrate upgrade '
            'download upload reply').split()
SPECIFIC_RE = _forms(*SPECIFIC)
# The verbs of the "most frequent" table: the vague ones and these (all their forms).
OTHER = {
    'write': _forms('write', 'writes', 'writing', 'wrote', 'written'),
    'push': _forms('push', 'pushes', 'pushed', 'pushing'),
    'deploy': _forms('deploy', 'deploys', 'deployed', 'deploying'),
    'merge': _forms('merge', 'merges', 'merged', 'merging'),
    'build': _forms('build', 'builds', 'building', 'built'),
    'run': _forms('run', 'runs', 'running', 'ran'),
    'continue': _forms('continue', 'continues', 'continued'),
    'save': _forms('save', 'saves', 'saved'),
    'fold': _forms('fold', 'folds', 'folded', 'folding'),
    'land': _forms('land', 'lands', 'landed', 'landing'),
    'ship': _forms('ship', 'ships', 'shipped', 'shipping'),
    'commit': _forms('commit', 'commits', 'committed', 'committing'),
}
NOT_PROMPTS = ('# Worker brief', 'This session is being continued', 'Background (from the session',
               '<task-notification', '<local-command', 'Another Claude', '[Cross-session')


def clean(text):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.S)
    text = re.sub(r'`[^`]*`', 'X', text)
    text = re.sub(r'https?://\S+', 'X', text)
    return re.sub(r'\S*/\S+', 'X', text)


def _jsonl(path):
    try:
        with open(path, errors='replace') as handle:
            for line in handle:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except OSError:
        return


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(part.get('text', '') for part in content
                         if isinstance(part, dict) and part.get('type') in ('text', 'input_text'))
    return ''


def _slash(text):
    name = re.search(r'<command-name>\s*(/?[^<\s]+)\s*</command-name>', text)
    if not name:
        return None
    args = re.search(r'<command-args>(.*?)</command-args>', text, re.S)
    command = name.group(1) if name.group(1).startswith('/') else '/' + name.group(1)
    return (command + ' ' + (args.group(1).strip() if args else '')).strip()


def claude_rows(home, project):
    roots = [home / '.claude/projects'] + sorted((home / '.claude-accounts').glob('*/projects'))
    for root in roots:
        for path in sorted(root.glob(f'*{project}*/*.jsonl')):
            for row in _jsonl(path):
                if row.get('type') != 'user' or row.get('isSidechain') or row.get('isMeta') \
                        or row.get('isCompactSummary'):
                    continue
                text = _text((row.get('message') or {}).get('content'))
                kind = (row.get('origin') or {}).get('kind')
                if kind == 'human':
                    src = 'human'
                elif kind is None and text.lstrip().startswith('<command-name>'):
                    text, src = _slash(text), 'slash'
                    if not text:
                        continue
                else:
                    continue
                if not text.strip() or text.lstrip().startswith(NOT_PROMPTS):
                    continue
                yield {'agent': 'claude', 'sid': row.get('sessionId', path.stem), 'ts': row.get('timestamp', ''),
                       'text': text, 'src': src, 'uuid': row.get('uuid')}


def codex_rows(home, project):
    for base in (home / '.codex/sessions', home / '.codex/archived_sessions'):
        for path in sorted(base.rglob('*.jsonl')) if base.is_dir() else ():
            keep, sid, meta = False, path.stem, False
            for row in _jsonl(path):
                payload = row.get('payload') or {}
                if row.get('type') == 'session_meta':
                    if not meta:   # a subagent's file repeats its parent's session_meta later: use the first
                        keep = payload.get('thread_source') == 'user' and project in (payload.get('cwd') or '')
                        sid, meta = payload.get('id', sid), True
                    continue
                if not keep or row.get('type') != 'response_item' or payload.get('type') != 'message' \
                        or payload.get('role') != 'user':
                    continue
                for part in payload.get('content') or []:
                    text = part.get('text', '') if part.get('type') == 'input_text' else ''
                    if text.strip() and not text.lstrip().startswith(('<', '# AGENTS.md')):
                        yield {'agent': 'codex', 'sid': sid, 'ts': row.get('timestamp', ''), 'text': text,
                               'src': 'human'}


def pi_rows(home, project):
    base = home / '.pi/agent/sessions'
    for path in sorted(base.rglob('*.jsonl')) if base.is_dir() else ():
        keep, sid = False, path.stem
        for row in _jsonl(path):
            if row.get('type') == 'session':
                keep, sid = project in (row.get('cwd') or ''), row.get('id', sid)
                continue
            message = row.get('message') or {}
            if keep and row.get('type') == 'message' and message.get('role') == 'user':
                text = _text(message.get('content'))
                if text.strip():
                    yield {'agent': 'pi', 'sid': sid, 'ts': row.get('timestamp', ''), 'text': text, 'src': 'human'}


def collect(home, project, since=None, until=None):
    """Prompt rows in time order, each with `dup` set when the same text came earlier."""
    rows, uuids = [], set()
    for row in [*claude_rows(home, project), *codex_rows(home, project), *pi_rows(home, project)]:
        if row.get('uuid'):
            if row['uuid'] in uuids:        # a forked or resumed transcript copies the earlier rows
                continue
            uuids.add(row['uuid'])
        ts = row.get('ts') or ''
        if (since and ts < since) or (until and ts >= until):
            continue
        rows.append(row)
    rows.sort(key=lambda r: r.get('ts') or '')
    seen = set()
    for row in rows:
        key = ' '.join(row['text'].split()).lower()
        row['dup'] = key in seen
        seen.add(key)
    return rows


def prompts(rows):
    """The texts to count: no repeats, the slash command name removed, no long pastes."""
    out, long = [], 0
    for row in rows:
        if row.get('dup') or row.get('src') not in ('human', 'slash'):
            continue
        text = row['text']
        if text.startswith('/'):
            text = text.split(' ', 1)[1] if ' ' in text else ''  # the arguments only
        if len(text) > LONG:
            long += 1
            continue
        out.append((row.get('agent', '?'), text))
    return out, long


def count(rows):
    texts, long = prompts(rows)
    n = len(texts)
    agents = collections.Counter(agent for agent, _ in texts)
    verbs = collections.Counter()
    anyv = only = short = 0
    for _, raw in texts:
        text = clean(raw)
        hits = [name for name, rx in VAGUE.items() if rx.search(text)]
        verbs.update(hits)
        verbs.update(name for name, rx in OTHER.items() if rx.search(text))
        if hits:
            anyv += 1
            only += not SPECIFIC_RE.search(text)
        short += len(re.findall(r"[\w'-]+", raw)) <= 3
    return {'prompts': n, 'long_removed': long, 'agents': dict(agents), 'any_vague': anyv,
            'only_vague': only, 'three_words_or_less': short, 'verbs': verbs.most_common()}


def pct(part, whole):
    return f'{100 * part / whole:.1f}%' if whole else '-'


def table(result, top=12):
    n = result['prompts']
    lines = [f"prompts: {n} ({', '.join(f'{k} {v}' for k, v in sorted(result['agents'].items()))}); "
             f"pastes over {LONG} characters removed: {result['long_removed']}",
             '',
             f"| measure | prompts | share |", '| --- | ---: | ---: |',
             f"| contain a vague verb | {result['any_vague']} | {pct(result['any_vague'], n)} |",
             f"| contain only vague verbs | {result['only_vague']} | {pct(result['only_vague'], n)} |",
             f"| 3 words or less | {result['three_words_or_less']} | {pct(result['three_words_or_less'], n)} |",
             '', '| verb | prompts | share | vague |', '| --- | ---: | ---: | --- |']
    for verb, c in result['verbs'][:top]:
        lines.append(f"| {verb} | {c} | {pct(c, n)} | {'yes' if verb in VAGUE else ''} |")
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='ai-prompt-verbs', description=__doc__.split('\n')[0])
    parser.add_argument('--project', default='', help='a part of the project path, for example acme')
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--since', help='first timestamp to count (ISO, UTC), for example 2026-10-01')
    parser.add_argument('--until', help='count prompts before this timestamp (ISO, UTC)')
    parser.add_argument('--rows', type=Path, help='count saved rows (JSON lines) instead of the transcripts')
    parser.add_argument('--save', type=Path, help='also write the extracted rows here (JSON lines)')
    parser.add_argument('--top', type=int, default=12)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.rows:
        rows = list(_jsonl(args.rows))
    else:
        rows = collect(args.home, args.project, args.since, args.until)
    if args.save:
        with open(args.save, 'w') as handle:
            for row in rows:
                handle.write(json.dumps({k: row.get(k) for k in ('agent', 'sid', 'ts', 'text', 'src', 'dup')}) + '\n')
    result = count(rows)
    result['generated'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    print(json.dumps(result, indent=1) if args.json else table(result, args.top))
    return 0
