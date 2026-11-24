"""One session title format for every client. See docs/session-naming.md.

    [host/project] purpose(area): Description #ref · who · client · provider/model · type · YYYY-MM-DD

`what` is `purpose(area): Description #ref`. `who` is the person or agent that started the
session. `client` is the program, with `:account` for a non-default account. `model` is the
provider and model family. `type` says how the session runs.
"""
import datetime
import getpass
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

SEP = ' · '
WHAT_MAX = 80
# ASCII, not U+2026: the Claude desktop app stores `…` as `...`, and a title that changes on the
# round trip makes the hook and the app write two versions back and forth, over any rename.
ELLIPSIS = '...'
UNTITLED = 'chat(misc): Untitled session'
PURPOSES = ('feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'loop', 'review', 'spike', 'forensics', 'ops',
            'chat', 'plan', 'research', 'write', 'admin', 'learn', 'personal')
TYPES = ('interactive', 'headless', 'subagent', 'seat', 'loop', 'scheduled', 'web', 'cloud')
CLIENTS = ('claude-cli', 'claude-desktop', 'claude-sdk', 'claude-vscode', 'claude-ai', 'codex-cli',
           'codex-exec', 'codex-vscode', 'codex-app', 'chatgpt', 'pi', 'zed', 'copilot', 'vscode',
           'openrig', 'tmux')
_TOKEN = r'[A-Za-z0-9][A-Za-z0-9._@#:+-]*'
_MODEL = r'[a-z0-9][a-z0-9.-]*(?:/[A-Za-z0-9][A-Za-z0-9._:+-]*)?'
TITLE = re.compile(rf'^\[(?P<host>{_TOKEN})/(?P<project>{_TOKEN})\] (?P<what>.+?) · (?P<who>{_TOKEN}) · '
                   rf'(?P<client>{_TOKEN}) · (?P<model>{_MODEL}) · (?P<type>[a-z]+) · (?P<date>\d{{4}}-\d{{2}}-\d{{2}})$')
WHAT = re.compile(r'^(?P<purpose>[a-z]+)\((?P<area>[a-z0-9][a-z0-9-]*)\): (?P<description>\S.*?)(?: (?P<ref>#\d+))?$')
_SECRET = re.compile(r'(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abp]-|AKIA[0-9A-Z]{16}|'
                     r'-----BEGIN|eyJ[A-Za-z0-9_-]{20,}\.)')


# First-guess purpose rules, most specific first. A renamer that can read the transcript or
# ask a model should correct this guess; it must never be the only evidence for `chat`.
_PURPOSE_RULES = (
    ('review', r'\b(review|pr #?\d+|pull request|audit)\b'),
    ('forensics', r'\b(diagnos\w*|root cause|forensic\w*|incident|outage|why (is|does|did)|logs?)\b'),
    ('fix', r'\b(fix\w*|bug\w*|broken|error\w*|crash\w*|fail\w*|regression|repair|stuck|not working|hold\w*)\b'),
    ('ops', r'\b(deploy\w*|release\w*|restart\w*|install\w*|configur\w*|server setup|dns|ssh|webhook|'
            r'credential\w*|login|account\w*|backup\w*|upgrade\w*|provision\w*|host|readiness|go[- ]live)\b'),
    ('test', r'\b(tests?|testing|coverage|e2e|qa)\b'),
    ('refactor', r'\b(refactor\w*|clean ?up|consolidat\w*|centrali[sz]\w*|restructur\w*|align\w*|rename\w*|unif\w*|simplif\w*)\b'),
    ('docs', r'\b(docs?|documentation|readme|runbook)\b'),
    ('plan', r'\b(plan\w*|design\w*|architect\w*|roadmap|spec\w*|proposal|strateg\w*|scope)\b'),
    ('research', r'\b(research\w*|compar\w*|evaluat\w*|options|inventory|investigat\w*|explor\w*)\b'),
    ('write', r'\b(draft\w*|letter|announcement|blog post|reply to|write (an?|the) \w+|writing)\b'),
    ('admin', r'\b(invoice\w*|billing|harvest|timesheet|tax\w*|payment\w*|subscription\w*)\b'),
    ('learn', r'^(how|what|explain|teach)\b|\b(how do i|what is)\b'),
    ('feat', r'\b(add\w*|build\w*|implement\w*|creat\w*|support\w*|new|feature|workflow|integrat\w*|enable\w*|'
             r'smart|launch\w*|automat\w*|presentation|format\w*|polish\w*|improv\w*|identif\w*|hydrat\w*)\b'),
    ('chat', r'\b(status|question|update|check)\b'),
)
_VERBS = re.compile(r'(fix|add|build|make|implement|create|support|review|investigate|plan|design|research|'
                    r'refactor|align|unify|rename|update|check|write|draft|improve|enable|centralize|centralization)\w*')
_BRANCH_PREFIX = re.compile(r'^(?:claude|codex|wip|worktree|agent|users?/[^/]+)/')
_STOP = set('a an the and or for to of in on with from into via by at as is are be my our this that it its '
            'new add fix build make use using live local session sessions request job visit app web stop smart polish '
            'project business date personal description application dynamic unbound reply only task ok please '
            .split())


def infer_purpose(text, branch=None, default='chat'):
    """Return (purpose, area) guessed from a title, prompt or branch name."""
    branch = _BRANCH_PREFIX.sub('', branch or '')
    head = branch.split('/', 1)[0] if '/' in branch else ''
    words = ' '.join(filter(None, [text or '', re.sub(r'[-_/]+', ' ', re.sub(r'-[0-9a-f]{6}$', '', branch))])).lower()
    purpose = head if head in PURPOSES else None
    if not purpose:
        purpose = next((name for name, rule in _PURPOSE_RULES if re.search(rule, words)), default)
    area = 'misc'
    slug = re.sub(r'[-_/]+', ' ', re.sub(r'-[0-9a-f]{6}$', '', branch.split('/', 1)[1])) if head else ''
    for word in re.findall(r'[a-z][a-z0-9.-]{1,30}', f'{slug} {words}'.lower()):
        word = word.strip('.-')
        if len(word) > 2 and word not in _STOP and word not in PURPOSES and not re.fullmatch(_VERBS, word):
            area = word
            break
    return purpose, token(area.lower(), 'misc')[:24]


# Text a client puts in front of the first prompt; it never describes the task.
_INJECTED = re.compile(r'^(you are operating in a git worktree|caveat:|warmup\b|this session is being continued|'
                       r'base directory for this skill|\[request interrupted|contents of /|<command-|'
                       r'the user hasn.t heard from you)', re.I)
_TAGGED = re.compile(r'<(system-reminder|command-[a-z-]+|local-command-[a-z-]+|pasted_content)[^>]*>.*?</\1>', re.S)
_ANY_TAG = re.compile(r'<[^>]{1,80}>')
_PASSWORD = re.compile(r'(?i)\b(?:password|passwd|secret|token|api[_-]?key|bearer)\b\s*[=:]?\s*\S+|\b[A-Za-z0-9+/_-]{32,}\b')


def describe_prompt(text, limit=60):
    """First line of a prompt that describes the task: no injected text, markup, URLs or secrets."""
    if not isinstance(text, str):
        return None
    text = _ANY_TAG.sub(' ', _TAGGED.sub(' ', text))
    for line in text.splitlines():
        line = re.sub(r'https?://\S+', ' ', line)
        line = _PASSWORD.sub('[redacted]', _SECRET.sub('[redacted]', line))
        line = ' '.join(re.sub(r'^[\s#>*\-•`]+', '', line).replace('·', '-').split())
        if len(re.findall(r'[A-Za-z0-9]', line)) < 3 or _INJECTED.match(line):
            continue
        if len(line) > limit:
            cut = line[:limit - len(ELLIPSIS)]
            line = (cut[:cut.rfind(' ')] if cut.rfind(' ') > limit // 2 else cut).rstrip(' ,.;:-') + ELLIPSIS
        return line[0].upper() + line[1:]
    return None


def contextual_part(title):
    """The part a model writes, taken from any title: (what, who) or None.

    Accepts `purpose(area): Description #ref`, the same with ` · who` after it (a spawned worker
    names its parent this way), and a full or damaged title with a valid `what`. The model never
    has to write host, project, client, model, type or date; `format_title` adds them."""
    if not isinstance(title, str):
        return None
    text = re.sub(r'^\[[^\]]*\]\s*', '', title.strip())
    parts = [part.strip() for part in text.split(SEP)]
    if not WHAT.match(parts[0]):
        return None
    who = parts[1] if len(parts) > 1 and re.fullmatch(_TOKEN, parts[1]) else None
    return parts[0], who


def token(value, fallback):
    value = re.sub(r'[^A-Za-z0-9._@#:+-]+', '-', str(value or '')).strip('-.')
    return value[:40] or fallback


def clean_what(text, default_purpose=None, branch=None):
    """Normalise free text into the `what` field; never raise on untrusted input."""
    if not isinstance(text, str):
        return UNTITLED
    parsed = TITLE.match(text.strip())
    if parsed:
        text = parsed['what']
    text = ' '.join(text.replace('·', '-').split())
    text = _SECRET.sub('[redacted]', text)
    if not text:
        return UNTITLED
    if not WHAT.match(text):
        purpose, area = infer_purpose(text, branch)
        if default_purpose and purpose == 'chat':
            purpose = default_purpose
        text = f'{purpose}({area}): {text[0].upper()}{text[1:]}'
    if len(text) > WHAT_MAX:
        text = text[:WHAT_MAX - len(ELLIPSIS)].rstrip() + ELLIPSIS
    return text


def project_of(cwd, home=None):
    home = Path(home or Path.home())
    if not cwd:
        return 'none'
    path = Path(cwd)
    try:
        common = subprocess.run(['git', '-C', str(path), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                capture_output=True, text=True, timeout=3, stdin=subprocess.DEVNULL)
        if common.returncode == 0 and common.stdout.strip():
            git_dir = Path(common.stdout.strip())
            return token(git_dir.parent.name if git_dir.name == '.git' else git_dir.name.removesuffix('.git'), 'repo')
    except (OSError, subprocess.SubprocessError):
        pass
    # Worktree paths that no longer exist still name their repository.
    parts = path.parts
    if '.claude' in parts and 'worktrees' in parts:
        return token(parts[parts.index('.claude') - 1], 'repo')
    if path == home:
        return 'home'
    try:
        rel = path.relative_to(home)
    except ValueError:
        return token(path.name, 'none')
    if rel.parts and rel.parts[0] in ('dev', 'Dev', 'src', 'code', 'projects') and len(rel.parts) > 1:
        return token(rel.parts[1], 'none')
    return token(rel.parts[0] if rel.parts else 'home', 'home')


def default_who():
    return token(os.environ.get('DEV_SESSION_WHO') or getpass.getuser(), 'unknown')


def client_label(client, account=None):
    client = token(client, 'unknown')
    account = account if account is not None else os.environ.get('DEV_SESSION_ACCOUNT')
    if not account:
        config = os.environ.get('CLAUDE_CONFIG_DIR', '')
        if client.startswith('claude') and '/.claude-accounts/' in config:
            account = Path(config).name
    return f'{client}:{token(account, "")}' if account and token(account, '') else client


def model_label(provider=None, model=None):
    provider = provider or os.environ.get('DEV_SESSION_PROVIDER')
    model = model or os.environ.get('DEV_SESSION_MODEL')
    if not provider and model and '/' in model:
        provider, model = model.split('/', 1)
    provider = re.sub(r'[^a-z0-9.-]+', '-', (provider or 'unknown').lower()).strip('-.') or 'unknown'
    if model:
        model = re.sub(r'^(claude-|models/)', '', model.rsplit('/', 1)[-1])
        model = re.sub(r'-\d{8}$', '', model)
        model = token(model, '')
    return f'{provider}/{model}' if model else provider


def format_title(what, *, client, cwd=None, who=None, host=None, project=None, date=None, account=None,
                 provider=None, model=None, kind=None, purpose=None, branch=None):
    date = date or datetime.date.today().isoformat()
    if isinstance(date, (int, float)):
        date = datetime.datetime.fromtimestamp(date / 1000 if date > 1e11 else date).date().isoformat()
    date = str(date)[:10]
    kind = kind or os.environ.get('DEV_SESSION_TYPE') or 'interactive'
    if kind not in TYPES:
        kind = 'interactive'
    return (f'[{token((host or socket.gethostname().split(".")[0]).lower(), "host")}/'
            f'{token(project or project_of(cwd), "none")}] {clean_what(what, purpose, branch)}{SEP}'
            f'{token(who or default_who(), "unknown")}{SEP}{client_label(client, account)}{SEP}'
            f'{model_label(provider, model)}{SEP}{kind}{SEP}{date}')


def short_title(what, project, purpose='chat'):
    """tmux window name: `project:purpose(area)`. Accepts a `what` or a full title."""
    parsed = parse(what)
    what = parsed['what'] if parsed else clean_what(what, purpose)
    match = WHAT.match(what)
    head = f"{match['purpose']}({match['area']})" if match else f'{purpose}(misc)'
    return f'{token(project, "none")}:{head}'


def parse(title):
    match = TITLE.match(title or '') if isinstance(title, str) else None
    if not match:
        return None
    fields = match.groupdict()
    what = WHAT.match(fields['what'])
    fields.update(what.groupdict() if what else {'purpose': None, 'area': None, 'description': None, 'ref': None})
    return fields


DESCRIPTION_MAX = 60
STYLE = ('`purpose(area): Description #ref`. purpose: one of ' + ', '.join(PURPOSES) + '. area: the part of the '
         'project the work changes or studies, one lowercase word or a hyphenated slug (for example ui, auth, '
         'naming, platform); never misc unless no part fits. Description: what the session does, as an instruction '
         'with a verb first, sentence case, 2 to 10 words, at most 60 characters, no full stop, no ellipsis, no '
         'raw prompt text. #ref: the issue or task number only when it exists. Example: '
         '`fix(naming): Keep a rename when the app restores an old title #12`.')


def style_problems(what):
    """Why a model-written `purpose(area): Description #ref` is not standard; empty when it is."""
    if not isinstance(what, str):
        return ['the title is missing']
    what = what.strip()
    if SEP.strip() in what:
        return ['write only purpose(area): Description #ref; the hook adds every other field']
    match = WHAT.match(what)
    if not match:
        return ['the title is not purpose(area): Description #ref']
    found = []
    if match['purpose'] not in PURPOSES:
        found.append(f"purpose {match['purpose']} is not one of {', '.join(PURPOSES)}")
    if len(match['area']) > 24:
        found.append('area is longer than 24 characters')
    if match['area'] == 'misc' and match['purpose'] != 'chat':
        found.append('area misc says nothing; name the part of the project')
    words = match['description'].split()
    first = words[0]
    if not first[:1].isupper():
        found.append('Description must start with a capital letter')
    if first.lower().endswith('ing') and len(first) > 5:
        found.append(f'Description must start with a verb as an instruction, not "{first}"')
    if not 2 <= len(words) <= 10:
        found.append('Description must have 2 to 10 words')
    if len(match['description']) > DESCRIPTION_MAX:
        found.append(f'Description is longer than {DESCRIPTION_MAX} characters')
    if match['description'].endswith(('.', ELLIPSIS, '\u2026')):
        found.append('Description must not end with a full stop or an ellipsis')
    if len(what) > WHAT_MAX:
        found.append(f'the title is longer than {WHAT_MAX} characters')
    if _SECRET.search(what):
        found.append('the title looks like it contains a secret')
    return found


def problems(title):
    found = []
    parsed = parse(title)
    if not parsed:
        return ['does not match [host/project] purpose(area): Description #ref · who · client · provider/model · type · YYYY-MM-DD']
    if not parsed['purpose']:
        found.append('what is not purpose(area): Description')
    elif parsed['purpose'] not in PURPOSES:
        found.append(f"purpose {parsed['purpose']} is not one of {', '.join(PURPOSES)}")
    if parsed['type'] not in TYPES:
        found.append(f"type {parsed['type']} is not one of {', '.join(TYPES)}")
    if parsed['what'] == UNTITLED:
        found.append('what is still a placeholder')
    if _SECRET.search(title):
        found.append('looks like it contains a secret')
    if len(parsed['what']) > WHAT_MAX:
        found.append(f'what is longer than {WHAT_MAX} characters')
    try:
        datetime.date.fromisoformat(parsed['date'])
    except ValueError:
        found.append('date is not a real date')
    return found


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog='ai-title', description='Format and check unified session titles.')
    sub = p.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('format', help='print a title for the current or given context')
    f.add_argument('what', nargs='?', default=UNTITLED)
    f.add_argument('--client', required=True)
    f.add_argument('--cwd', default=None)
    for name in ('who', 'host', 'project', 'date', 'account', 'provider', 'model'):
        f.add_argument(f'--{name}')
    f.add_argument('--type', dest='kind', choices=TYPES)
    f.add_argument('--purpose', choices=PURPOSES, help='used when what has no purpose(area): prefix and no guess fits')
    f.add_argument('--branch', help='git branch; its kind and slug help guess purpose and area')
    g = sub.add_parser('guess', help='print the guessed purpose and area for a text and branch')
    g.add_argument('text')
    g.add_argument('--branch')
    t = sub.add_parser('short', help='print the tmux window name project:purpose(area)')
    t.add_argument('what')
    t.add_argument('--project', required=True)
    t.add_argument('--purpose', default='chat', choices=PURPOSES)
    c = sub.add_parser('check', help='exit 1 and list problems when a title does not conform')
    c.add_argument('title')
    c.add_argument('--json', action='store_true')
    a = sub.add_parser('parse', help='print the fields of a conforming title as JSON')
    a.add_argument('title')
    args = p.parse_args(argv)
    if args.cmd == 'format':
        print(format_title(args.what, client=args.client, cwd=args.cwd or os.getcwd(), who=args.who,
                           host=args.host, project=args.project, date=args.date, account=args.account,
                           provider=args.provider, model=args.model, kind=args.kind, purpose=args.purpose,
                           branch=args.branch))
        return 0
    if args.cmd == 'guess':
        print(json.dumps(dict(zip(('purpose', 'area'), infer_purpose(args.text, args.branch)))))
        return 0
    if args.cmd == 'short':
        print(short_title(args.what, args.project, args.purpose))
        return 0
    if args.cmd == 'parse':
        parsed = parse(args.title)
        print(json.dumps(parsed))
        return 0 if parsed else 1
    issues = problems(args.title)
    if args.json:
        print(json.dumps({'ok': not issues, 'problems': issues}))
    else:
        for issue in issues:
            print(issue, file=sys.stderr)
    return 1 if issues else 0
