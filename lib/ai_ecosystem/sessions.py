"""ai-session: scan, list, show, title, handoff and resume over the filesystem index.

One store for every harness (Claude Code, Codex, Pi) in every home on the machine. The
owner's own home is scanned directly. An agent's home (assistant, ops, engineer) is read only by
that agent: `ai-session export` runs as the agent and prints its sessions, readable text
included; `ai-session ingest --owner AGENT` runs as the owner and files them here. Root
pipes one into the other (dev-server's ol-sessions-sync); nobody reads another's home.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

from . import adapters, transcript
from .store import MAX_HANDOFF, RevisionConflict, Store, check_id, session_id

NATIVE_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
MERGED = ('cwd', 'title', 'branch', 'updated_at', 'native')
KEPT = ('title_override', 'has_handoff', 'conversation_id', 'derived', 'launch')
AGENTS = ('assistant', 'ops', 'engineer')


def _mtime(rec):
    path = rec.get('native', {}).get('transcript_path')
    try:
        return int(os.stat(path).st_mtime) if path else None
    except OSError:
        return None


def readable(runtime, rec):
    """Attach the readable transcript (rec['text']) and what it says about itself (rec['derived'])."""
    path, mtime = rec.get('native', {}).get('transcript_path'), _mtime(rec)
    if not path or mtime is None or runtime not in transcript.READERS:
        return rec
    try:
        text, meta = transcript.render(runtime, path)
    except (OSError, ValueError):
        return rec
    rec['text'] = text
    rec['derived'] = dict(meta, mtime=mtime, title=meta.get('title') or meta.get('ai_title') or meta.get('first_prompt'))
    return rec


def _attach_text(store, runtime, sid, rec, old):
    """File the readable text when it is new and return what the transcript says about itself.
    An ingested record brings its text; a local one is rendered only when its file changed."""
    if 'text' not in rec and rec.get('native', {}).get('transcript_path'):
        if old.get('derived', {}).get('mtime') == _mtime(rec) and store.read_text(sid) is not None:
            return old['derived']
        readable(runtime, rec)
    if isinstance(rec.get('text'), str):
        store.write_text(sid, rec['text'])
    return rec.get('derived') or old.get('derived')


def scan(store, sources, limit):
    status = store.sources()
    report = {}
    for src in sources:
        records, truncated = [], False
        source_info = {'runtime': src.runtime, 'store': src.store, 'owner': src.owner}
        try:
            for rec in src.read():
                if len(records) >= limit:
                    truncated = True
                    break
                records.append(rec)
        except Exception as exc:  # one broken source must not touch any other source
            status[src.key] = dict(source_info, state='unavailable' if isinstance(exc, FileNotFoundError) else 'error',
                                   error=type(exc).__name__, at=time.time())
            report[src.key] = status[src.key]
            continue
        seen = set()
        for rec in records:
            sid = session_id(src.runtime, src.store, rec['native_id'])
            seen.add(sid)
            with store.lock(sid):
                old = store.get(sid) or {}
                new = {k: old[k] for k in KEPT if k in old}
                new.update({k: rec.get(k) for k in MERGED})
                derived = _attach_text(store, src.runtime, sid, rec, old)
                if derived:
                    new['derived'] = derived
                if rec.get('launch'):
                    new['launch'] = rec['launch']
                new.update(id=sid, runtime=src.runtime, store=src.store, source=src.key, owner=src.owner,
                           native_id=rec['native_id'], missing=bool(rec.get('native', {}).get('transcript_missing')),
                           status='stale' if rec.get('native', {}).get('transcript_missing') else 'unknown')
                if {k: old.get(k) for k in new} != new:
                    store.put(new)
                    store.event(sid, 'scan', source=src.key)
        stale = 0
        if not truncated:
            for item in store.all():
                if item.get('source') == src.key and item['id'] not in seen and not item.get('missing'):
                    with store.lock(item['id']):
                        current = store.get(item['id'])
                        if current and current.get('source') == src.key and not current.get('missing'):
                            store.put(dict(current, missing=True, status='stale'))
                            store.event(item['id'], 'missing', source=src.key)
                            stale += 1
        status[src.key] = dict(source_info, state='truncated' if truncated else 'ok',
                               count=len(records), stale=stale, at=time.time())
        report[src.key] = status[src.key]
    store.save_sources(status)
    return report


def resume_plan(m):
    handoff = {'supported': False, 'runtime': m['runtime']}
    if m.get('native', {}).get('archived'):
        return dict(handoff, reason='history from the old machine: read it here, it cannot be resumed')
    if m.get('owner') in AGENTS:
        return agent_resume_plan(m)
    if m.get('owner') != 'user':
        return dict(handoff, reason=f"runtime-owned by {m.get('owner')}; resume through its owner, not the standalone CLI")
    if m['runtime'] == 'pi':
        # A Pi session resumes as its role, through the launcher that hands it the Pi login
        # (agent_resume_plan). ai-role starts nothing without that folder, so no command
        # resumes a Pi session of the owner's own store.
        return dict(handoff, reason='a Pi session resumes as its role, through the launcher (agent); '
                                    'this one is not the session of a role')
    if m.get('status') == 'stale' or not NATIVE_ID_RE.match(m.get('native_id') or ''):
        return dict(handoff, reason='native record missing or its id is not trustworthy')
    cwd = m.get('cwd')
    if not cwd or not os.path.isabs(cwd):
        return dict(handoff, reason='no absolute working directory recorded')
    from .accounts import conflicts
    if conflicts(os.environ):
        return dict(handoff, reason='conflicting inherited provider settings; resume from a clean native environment')
    env = {}
    if m['runtime'] == 'claude':
        argv = ['claude', '--resume', m['native_id']]
        if m.get('native', {}).get('isolated_profile'):
            env['CLAUDE_CONFIG_DIR'] = m['store']
    elif m['runtime'] == 'codex':
        argv = ['codex', 'resume', m['native_id']]
        env['CODEX_HOME'] = m['store']
    else:
        return dict(handoff, reason='runtime not supported')
    unset_env = ['CODEX_HOME', 'CLAUDE_CONFIG_DIR']
    prefix = ['env', *[part for key in unset_env for part in ('-u', key)],
              *[f'{k}={v}' for k, v in env.items()]]
    command = f"cd {shlex.quote(cwd)} && {shlex.join(prefix + argv)}"
    return {'supported': True, 'runtime': m['runtime'], 'argv': argv, 'cwd': cwd,
            'env': env, 'unset_env': unset_env, 'command': command}


def metered_through_pi(account):
    """Whether the registry says this account costs API money through Pi; unknown is not metered."""
    from . import registry
    try:
        entry = registry.get(registry.load(), account)
    except (OSError, ValueError, KeyError, registry.Refused):
        return False
    return registry.billing(entry, 'pi') == 'metered'


def agent_resume_plan(m):
    """An agent's session resumes as that agent, through the launcher that bounds it."""
    who, runtime = m['owner'], m['runtime']
    handoff = {'supported': False, 'runtime': runtime}
    if m.get('status') == 'stale' or not NATIVE_ID_RE.match(m.get('native_id') or ''):
        return dict(handoff, reason='native record missing or its id is not trustworthy')
    place = [m['cwd']] if who == 'engineer' and m.get('cwd') else []
    if runtime == 'claude':
        argv = ['agent', who, *place, '--', '--resume', m['native_id']]
    elif runtime == 'pi':
        # A role's Pi session resumes as the role, through `agent` (OL_MODEL=pi), in its
        # conversation and on the account it started on: a native Pi session belongs to it.
        native = m.get('native', {})
        conversation, path = native.get('conversation'), native.get('transcript_path')
        if not conversation or not path:
            return dict(handoff, reason='a Pi session resumes through its role conversation, and this one has none')
        account = str(native.get('account') or (m.get('derived') or {}).get('account') or '').removesuffix(':pi')
        # A metered account (an API key: OpenRouter) starts only with the owner's yes for the
        # launch, which the launcher takes as OL_METERED_OK=1. This command is the owner's to
        # run, at his terminal, for the account the session already ran on: it carries the yes.
        metered = ['OL_METERED_OK=1'] if account and metered_through_pi(account) else []
        argv = ['env', 'OL_MODEL=pi', *([f'OL_ACCOUNT={account}'] if account else []), *metered,
                'agent', who, *place, '--', '--conversation', conversation, '--resume', path]
    else:
        return dict(handoff, reason=f'{runtime} sessions of an agent cannot be resumed through the launcher yet')
    return {'supported': True, 'runtime': runtime, 'argv': argv, 'cwd': None, 'env': {}, 'unset_env': [],
            'command': shlex.join(argv)}


def resume_environment(plan):
    env = {k: v for k, v in os.environ.items() if k not in plan['unset_env']}
    env.update(plan['env'])
    return env


def load(store, sid):
    m = store.get(check_id(sid))
    if m is None:
        raise KeyError(f'no session {sid}')
    return m


def jev_rank_sessions(items, query, limit=30):
    """Advisory context ranking for session search results. Failure leaves order unchanged."""
    if not query or not shutil.which('ai-jev'):
        return items
    scored = []
    rank = {'critical': 3, 'strong': 2, 'weak': 1, 'none': 0}
    for index, item in enumerate(items[:limit]):
        state = {'task': query, 'candidate': {k: item.get(k) for k in ('id', 'runtime', 'title', 'title_override', 'cwd', 'branch', 'status')}}
        try:
            run = subprocess.run(['ai-jev', 'decide', 'rank-context', '--provider', 'http', '--state', json.dumps(state)],
                                 capture_output=True, text=True, timeout=10)
            data = json.loads(run.stdout) if run.returncode == 0 else {}
            choice = data.get('answers', {}).get('relevance', {}).get('choice')
            load_first = data.get('answers', {}).get('load_first', {}).get('probability', 0)
            scored.append((rank.get(choice, 0), load_first, -index, item))
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            scored.append((0, 0, -index, item))
    scored.sort(reverse=True)
    return [s[-1] for s in scored] + items[limit:]


def export(home, since, out):
    """Run as the home's own user: print every session there as one JSON line, with its
    readable text when the transcript changed at or after `since` (epoch seconds)."""
    for src in adapters.discover(home):
        info = {'key': src.key, 'runtime': src.runtime, 'store': src.store}
        try:
            for rec in src.read():
                mtime = _mtime(rec)
                if mtime is not None and mtime >= since:
                    readable(src.runtime, rec)
                out.write(json.dumps({'source': info, 'record': rec}, sort_keys=True) + '\n')
        except Exception as exc:  # reported, and the owner's index keeps that source's entries
            out.write(json.dumps({'source': info, 'error': type(exc).__name__,
                                  'unavailable': isinstance(exc, FileNotFoundError)}) + '\n')
            continue
        out.write(json.dumps({'source': info, 'done': True}) + '\n')


def ingest(store, owner, stream, launch=None, launch_since=None, limit=100000):
    """File an agent's exported sessions under owner AGENT. `launch` fields (kind, portal,
    model, account, place) go on the sessions whose transcript changed at or after launch_since."""
    if owner not in AGENTS:
        raise ValueError('ingest is for an agent home: assistant, ops or engineer')
    found = {}
    for line in stream:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        info = item.get('source') or {}
        if not all(isinstance(info.get(k), str) for k in ('key', 'runtime', 'store')):
            continue
        entry = found.setdefault(info['key'], dict(info, records=[], error=None, done=False))
        if 'record' in item and isinstance(item['record'], dict):
            rec = item['record']
            if launch and launch_since is not None and (rec.get('derived') or {}).get('mtime', 0) >= launch_since:
                rec['launch'] = launch
            entry['records'].append(rec)
        elif item.get('error'):
            entry['error'] = FileNotFoundError if item.get('unavailable') else RuntimeError
        elif item.get('done'):
            entry['done'] = True
    sources = []
    for key, entry in sorted(found.items()):
        def read(entry=entry):
            if entry['error'] or not entry['done']:
                raise (entry['error'] or RuntimeError)('export incomplete')
            yield from entry['records']
        sources.append(adapters.Source(f'{owner}:{key}', entry['runtime'], entry['store'], owner, read))
    return scan(store, sources, limit)


def import_old(source, dest):
    """Split the old machine's conversation homes by agent, ready to be placed (by root) in
    /home/AGENT/memory/old/conversations, where `export` reads them as archived history."""
    source, dest = Path(source), Path(dest)
    counts = {}
    for folder in sorted(source.glob('conversation-*')):
        manifest = folder / 'conversation.json'
        if not manifest.is_file():
            manifest = folder / 'session.json'
        try:
            agent = json.loads(manifest.read_text()).get('agent')
        except (OSError, ValueError):
            continue
        if agent not in AGENTS:
            continue
        target = dest / agent / 'conversations' / folder.name
        if target.exists():
            counts[agent] = counts.get(agent, 0) + 1
            continue
        shutil.copytree(folder, target, symlinks=False, ignore=shutil.ignore_patterns('.pi-writer.lock', '.DS_Store'))
        counts[agent] = counts.get(agent, 0) + 1
    return counts


def title_of(m):
    return m.get('title_override') or m.get('title') or (m.get('derived') or {}).get('title') or '(untitled)'


def when_of(m):
    return str((m.get('derived') or {}).get('updated_at') or m.get('updated_at') or '')


def show_text(store, m):
    derived, launch = m.get('derived') or {}, m.get('launch') or {}
    account = launch.get('account') or derived.get('account') or m.get('native', {}).get('account')
    model = launch.get('model') or derived.get('model') or m.get('native', {}).get('model')
    facts = [m['runtime'], m.get('owner'), m.get('cwd'), account, model, when_of(m)[:16].replace('T', ' ')]
    plan = resume_plan(m)
    lines = [title_of(m), ' · '.join(str(f) for f in facts if f),
             f"Resume: {plan['command']}" if plan['supported'] else f"Not resumable: {plan['reason']}",
             f"ID: {m['id']}"]
    handoff = store.read_handoff(m['id'])
    if handoff:
        lines += ['', '# Handoff', handoff.strip()]
    text = store.read_text(m['id'])
    if text is None and m['runtime'] in transcript.READERS and m.get('native', {}).get('transcript_path'):
        try:
            text = transcript.render(m['runtime'], m['native']['transcript_path'])[0]
        except (OSError, ValueError):
            text = None
    lines += ['', text.rstrip() if text else '(no readable transcript: the native record is missing or not text)']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(prog='ai-session', description='One index of Claude Code, Codex and Pi sessions, in every home on the machine.')
    p.add_argument('--state-root', help='alternate state root (default ~/.local/state/dev-platform/sessions)')
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan'); s.add_argument('--limit', type=int, default=100000); s.add_argument('--home')
    s = sub.add_parser('list'); s.add_argument('--json', action='store_true'); s.add_argument('--runtime')
    s.add_argument('--owner', help='user (the owner), assistant, ops or engineer')
    s.add_argument('--limit', type=int, default=20, help='maximum results (default 20; 0 means all)')
    s.add_argument('--search', help='case-insensitive title, native ID or cwd substring')
    s.add_argument('--jev-rank', action='store_true', help='rank search matches with the bounded Jev rank-context schema')
    s = sub.add_parser('show', help='the session as readable text, with how to resume it')
    s.add_argument('id'); s.add_argument('--json', action='store_true', help='the index manifest instead')
    s = sub.add_parser('export', help="run as an agent: print its home's sessions for ingest")
    s.add_argument('--home'); s.add_argument('--since', type=int, default=0, help='render text only for transcripts changed since (epoch)')
    s = sub.add_parser('ingest', help="run as the owner: file an agent's export (stdin) in this index")
    s.add_argument('--owner', required=True, choices=AGENTS)
    s.add_argument('--launch', action='append', default=[], metavar='KEY=VALUE', help='launch facts for this run (kind, portal, model, account, place)')
    s.add_argument('--launch-since', type=int, help='epoch; sessions changed since then get the --launch facts')
    s = sub.add_parser('import-old', help="split the old machine's conversation homes by agent")
    s.add_argument('source', type=Path); s.add_argument('dest', type=Path)
    s = sub.add_parser('title'); s.add_argument('id'); s.add_argument('title'); s.add_argument('--expect-revision', type=int)
    s = sub.add_parser('handoff'); s.add_argument('id'); s.add_argument('--import', dest='source', metavar='FILE|-')
    s.add_argument('--expect-revision', type=int)
    s = sub.add_parser('resume'); s.add_argument('id'); s.add_argument('--execute', action='store_true')
    s = sub.add_parser('conversation', help='create and inspect durable cross-runtime associations')
    cs = s.add_subparsers(dest='conversation_command', required=True)
    s = cs.add_parser('create'); s.add_argument('--agent', required=True, choices=['assistant', 'engineer', 'ops'])
    s.add_argument('--title', required=True); s.add_argument('--name', help='stable lowercase filesystem name')
    s.add_argument('--project'); s.add_argument('--workspace')
    s.add_argument('--resource'); s.add_argument('--formation', action='store_true'); s.add_argument('--repos', type=Path)
    cs.add_parser('list')
    s = cs.add_parser('show'); s.add_argument('id')
    s = cs.add_parser('bind'); s.add_argument('id'); s.add_argument('native_id')
    s.add_argument('--expect-revision', type=int, required=True)
    a = p.parse_args(argv)
    if a.cmd in ('list', 'scan') and a.limit < (1 if a.cmd == 'scan' else 0):
        p.error('--limit must be positive for scan, or nonnegative for list')
    if a.cmd == 'export':
        export(a.home or Path.home(), a.since, sys.stdout)
        return 0
    if a.cmd == 'import-old':
        print(json.dumps(import_old(a.source, a.dest), indent=2, sort_keys=True))
        return 0
    store = Store(a.state_root)
    try:
        if a.cmd == 'conversation':
            from . import conversations
            if a.conversation_command == 'create':
                result = conversations.create(store, a.agent, a.title, a.project, a.workspace, a.resource, a.formation, a.repos, a.name)
            elif a.conversation_command == 'list':
                result = {'conversations': conversations.list_conversations(store)}
            elif a.conversation_command == 'show':
                result = conversations.show(store, a.id)
            else:
                result = conversations.bind(store, a.id, a.native_id, a.expect_revision)
            print(json.dumps(result, indent=2, sort_keys=True))
        elif a.cmd == 'scan':
            # Agents' sources arrive through ingest; a scan of this home must not call them vanished.
            previous = {k: v for k, v in store.sources().items() if v.get('owner') not in AGENTS}
            print(json.dumps(scan(store, adapters.discover(a.home, previous), a.limit), indent=2, sort_keys=True))
        elif a.cmd == 'ingest':
            launch = dict(item.split('=', 1) for item in a.launch if '=' in item)
            print(json.dumps(ingest(store, a.owner, sys.stdin, launch or None, a.launch_since), indent=2, sort_keys=True))
        elif a.cmd == 'list':
            items = [m for m in store.all() if (not a.runtime or m['runtime'] == a.runtime)
                     and (not a.owner or m.get('owner') == a.owner)]
            if a.search:
                needle = a.search.casefold()
                items = [m for m in items if any(needle in str(v or '').casefold()
                         for v in (m.get('title_override'), m.get('title'), (m.get('derived') or {}).get('title'),
                                   m.get('native_id'), m.get('cwd'), m.get('owner')))]
            items.sort(key=when_of, reverse=True)
            if a.jev_rank and a.search:
                items = jev_rank_sessions(items, a.search)
            total = len(items)
            if a.limit:
                items = items[:a.limit]
            if a.json:
                print(json.dumps({'sessions': items, 'total': total, 'has_more': total > len(items), 'sources': store.sources()}, indent=2, sort_keys=True))
            for m in [] if a.json else items:
                print(f"{m['id']}\t{m.get('owner')}\t{m['status']}\t{str(title_of(m))[:80]}\t{str(m.get('cwd') or '-')[:100]}")
            if not a.json and total > len(items):
                print(f'{len(items)} of {total} matches; use --search or --limit to narrow or expand.')
        elif a.cmd == 'show':
            m = load(store, a.id)
            if a.json:
                print(json.dumps(dict(m, handoff=store.read_handoff(a.id), events=len(store.events(a.id))), indent=2, sort_keys=True))
            else:
                sys.stdout.write(show_text(store, m))
        elif a.cmd == 'title':
            with store.lock(a.id):
                m = store.put(dict(load(store, a.id), title_override=a.title[:200]), a.expect_revision)
                store.event(a.id, 'title', revision=m['revision'])
            print(m['revision'])
        elif a.cmd == 'handoff':
            load(store, a.id)
            if a.source is None:
                text = store.read_handoff(a.id)
                if text is None:
                    print('no handoff', file=sys.stderr)
                    return 1
                sys.stdout.write(text)
                return 0
            if a.expect_revision is None:
                p.error('--import requires --expect-revision (see `show`)')
            handle = sys.stdin if a.source == '-' else open(a.source, encoding='utf-8')
            with handle:
                text = handle.read(MAX_HANDOFF + 1)
            print(store.write_handoff(a.id, text, a.expect_revision)['revision'])
        elif a.cmd == 'resume':
            plan = resume_plan(load(store, a.id))
            print(json.dumps(plan, indent=2, sort_keys=True))
            if not plan['supported']:
                return 2
            if a.execute:
                exe = shutil.which(plan['argv'][0])
                if not (sys.stdin.isatty() and sys.stdout.isatty()):
                    print('--execute needs an interactive terminal', file=sys.stderr)
                    return 2
                if not exe or (plan['cwd'] and not os.path.isdir(plan['cwd'])):
                    print('native command or working directory unavailable', file=sys.stderr)
                    return 2
                return subprocess.run([exe] + plan['argv'][1:], cwd=plan['cwd'], env=resume_environment(plan)).returncode
        return 0
    except RevisionConflict as exc:
        print(f'conflict: {exc}', file=sys.stderr)
        return 3
    except (KeyError, ValueError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
