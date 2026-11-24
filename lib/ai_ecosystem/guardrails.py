"""Guardrails in one home: the platform's skills, Codex rules and session-entry instructions.

Run by each user for their own home (`ai-guardrails install`): the owner, and every agent
through bootstrap's "guardrails" step. Hooks are not here: they apply to every user at once
from Claude Code's managed settings, which bootstrap renders from hooks/claude-settings.hooks.json
(one source) into a root-owned file no user can edit away.

What a home gets, all pointing into the activated release so an activation updates it:

  ~/.claude/skills/NAME, ~/.codex/skills/NAME, ~/.agents/skills/NAME
        the owner: a link per platform skill. A role: the session entry (skills/develop) and
        the skills agents/skills.json gives it, the same table its Pi sessions load from
  ~/.claude/agents/ROLE.md             the owner: a link per agents/ROLE/role.md, so that
        `claude --agent ROLE` starts a main session in that role
  ~/.codex/rules/default.rules         a link to hooks/codex.rules
  ~/.codex/config.toml                 sandbox_mode = "workspace-write" when it says nothing
  ~/.claude/CLAUDE.md, ~/.claude-accounts/*/CLAUDE.md, ~/.codex/AGENTS.md, ~/.pi/agent/APPEND_SYSTEM.md
        one marked block: the shared session entry (skills/develop), the commit rule, the title rule
        and the owner's words (skills/develop/owner-words.md: an include for Claude, the text for the others)
  ~/.pi/agent/settings.json            when ~/.pi/agent exists: integrations/pi/seat-guard.mjs in
        its extensions list (the other keys and extensions stay)
  global core.hooksPath                the release's hooks/git (pre-push, commit-msg), only when
        it is unset or already points into a platform install; a value of its own is left alone

Nothing else in a home is touched: a real folder or someone else's link with a skill's name is
left alone and reported, the owner's own lines around the marked block are kept, and only links
into a dev-platform install are ever removed (when their skill is gone).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import paths

SKILL_DIRS = ('.claude/skills', '.codex/skills', '.agents/skills')
BEGIN = '<!-- dev-platform guardrails: begin (managed by ai-guardrails; edit outside this block) -->'
END = '<!-- dev-platform guardrails: end -->'
# Links that once pointed into a platform install: the shared one, and the old Mac layouts.
OURS = ('/opt/dev-platform/', '/Dev/dev-platform/', '/.local/share/dev-platform/')

COMMIT_RULE = (
    "Commits, pull requests and issues: where a repository's own commit check rejects tool or "
    "model attribution (scripts/checks/hygiene.py in repositories made from the platform "
    "template), add no Co-Authored-By trailer and no generated-with line. The repository's "
    "check wins over any default.")

NAMING_RULE = (
    "Session title: change ONLY the middle part, `purpose(area): Description #ref`, for example "
    "`fix(ui): Align photo captions #12`. With a session-title tool, send the full title the platform hook gives "
    "you, with only that part changed; with `/rename` or a thread-name control, write only that part. Do not "
    "change host, project, who, client, model, type or date: the hook keeps them correct. Omit `#ref` when none exists. No secrets, account "
    "identifiers or customer data. For a session you start for another agent, set its title to the output of "
    "`ai-title format '<purpose(area): Description>' --client claude-desktop --type subagent --who <worker>@<parent> "
    "--cwd <its folder>`. See docs/session-naming.md.")
TITLE_HOOK = 'codex-session-title.py'
TITLE_EVENTS = ('SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop')


def _ours(target):
    text = str(target)
    return any(mark in text for mark in OURS)


def wanted_skills(release, role=None):
    """name -> folder, for every skill the home should see."""
    if role:
        table = json.loads((release / 'agents/skills.json').read_text())
        folders = [release / 'skills/develop', *(release / rel for rel in table[role])]
    else:
        folders = sorted((release / 'skills').iterdir()) if (release / 'skills').is_dir() else []
        # The roles are roles of the owner's own account: `claude --agent engineer` needs the skill that its role file names.
        folders += sorted((release / 'agents').glob('*/skills/*'))
    return {folder.name: folder for folder in folders if (folder / 'SKILL.md').is_file()}


def link_skills(home, release, role=None):
    """Make each skill folder a link into the release; returns notes for what was left alone."""
    notes = []
    skills = wanted_skills(release, role)
    for rel in SKILL_DIRS:
        base = home / rel
        base.mkdir(parents=True, exist_ok=True)
        for name, folder in skills.items():
            path = base / name
            if path.is_symlink():
                if os.readlink(path) == str(folder):
                    continue
                if not _ours(os.readlink(path)):
                    notes.append(f'{path}: a link of its own; left alone')
                    continue
                path.unlink()
            elif path.exists():
                notes.append(f'{path}: a folder of its own; left alone')
                continue
            path.symlink_to(folder)
        for path in base.iterdir():
            if path.is_symlink() and _ours(os.readlink(path)) and path.name not in skills:
                path.unlink()              # a platform skill that is gone, or another role's
    return notes


def wanted_agents(release):
    """role -> role file, for each role of the release that has a role.md."""
    return {path.parent.name: path for path in sorted((release / 'agents').glob('*/role.md'))}


def link_agents(home, release):
    """Make ~/.claude/agents/ROLE.md a link to each role file; returns notes for what was left alone."""
    notes = []
    agents = wanted_agents(release)
    base = home / '.claude/agents'
    if agents:
        base.mkdir(parents=True, exist_ok=True)
    for role, target in agents.items():
        path = base / f'{role}.md'
        if path.is_symlink():
            if os.readlink(path) == str(target):
                continue
            if not _ours(os.readlink(path)):
                notes.append(f'{path}: a link of its own; left alone')
                continue
            path.unlink()
        elif path.exists():
            notes.append(f'{path}: a file of its own; left alone')
            continue
        path.symlink_to(target)
    if base.is_dir():
        for path in base.iterdir():
            if path.is_symlink() and _ours(os.readlink(path)) and os.readlink(path).endswith('/role.md') \
                    and path.name[:-3] not in agents:
                path.unlink()              # a role file that is gone
    return notes


def codex_rules(home, release):
    rules = home / '.codex/rules'
    rules.mkdir(parents=True, exist_ok=True)
    path, target = rules / 'default.rules', release / 'hooks/codex.rules'
    if path.is_symlink() and (os.readlink(path) == str(target) or _ours(os.readlink(path))):
        if os.readlink(path) != str(target):
            path.unlink()
            path.symlink_to(target)
        return []
    if path.exists() or path.is_symlink():
        return [f'{path}: rules of its own; left alone (the platform rules are {target})']
    path.symlink_to(target)
    return []


def codex_config(home):
    """sandbox_mode = "workspace-write" at the top level, unless the config already says one."""
    path = home / '.codex/config.toml'
    text = path.read_text() if path.exists() else ''
    lines = text.splitlines()
    top = []
    for line in lines:
        if line.strip().startswith('['):
            break
        top.append(line)
    if any(line.split('=')[0].strip() == 'sandbox_mode' for line in top if '=' in line):
        return
    new = 'sandbox_mode = "workspace-write"\n' + (text if text.endswith('\n') or not text else text + '\n')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.new')
    tmp.write_text(new)
    os.replace(tmp, path)


def codex_title_hook(home, release):
    """Link the Codex naming hook into the home and list it in hooks.json (other hooks stay).

    A home where bin/ai-title-bundle's installer already put the hook keeps that one copy."""
    source = release / 'hooks' / TITLE_HOOK
    hooks_json = home / '.codex/hooks.json'
    if not source.is_file() or (hooks_json.exists() and 'dev-platform-naming/hooks/' in hooks_json.read_text()):
        return []
    link = home / '.codex/hooks' / TITLE_HOOK
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() and os.readlink(link) != str(source) and _ours(os.readlink(link)) or \
            link.is_symlink() and not link.exists():
        link.unlink()
    if link.exists() or link.is_symlink():
        if not (link.is_symlink() and os.readlink(link) == str(source)):
            return [f'{link}: a file of its own; left alone']
    else:
        link.symlink_to(source)
    path = home / '.codex/hooks.json'
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except ValueError:
        return [f'{path}: not valid JSON; left alone']
    hooks = data.setdefault('hooks', {})
    command = f"python3 '{link}'"
    changed = False
    for event in TITLE_EVENTS:
        groups = hooks.setdefault(event, [])
        if not any(TITLE_HOOK in h.get('command', '') for g in groups for h in g.get('hooks', [])):
            groups.append({'hooks': [{'type': 'command', 'command': command, 'timeout': 10}]})
            changed = True
    if changed:
        tmp = path.with_name(path.name + '.new')
        tmp.write_text(json.dumps(data, indent=2) + '\n')
        os.replace(tmp, path)
    return []


def pi_title_extension(home, release):
    """Copy the Pi naming extension where plain `pi` loads user extensions (it loads .ts files)."""
    source = release / 'integrations/pi/session-title.mjs'
    if not source.is_file() or not (home / '.pi/agent').is_dir():
        return []
    dest = home / '.pi/agent/extensions/session-title.ts'
    text = source.read_text()
    if dest.exists() and dest.read_text() == text:
        return []
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + '.new')
    tmp.write_text(text)
    os.replace(tmp, dest)
    return []


def pi_guard(home, release):
    """Add seat-guard.mjs to the extensions of the owner's Pi, when the home has one."""
    agent = home / '.pi/agent'
    if not agent.is_dir():
        return []
    settings = agent / 'settings.json'
    guard = str(release / 'integrations/pi/seat-guard.mjs')
    try:
        data = json.loads(settings.read_text()) if settings.is_file() else {}
    except ValueError:
        return [f'{settings}: not valid JSON; left alone (add {guard} to its extensions)']
    if not isinstance(data, dict) or not isinstance(data.get('extensions', []), list):
        return [f'{settings}: unexpected shape; left alone (add {guard} to its extensions)']
    extensions = data.get('extensions', [])
    if guard in extensions:
        return []
    data['extensions'] = [e for e in extensions if not (isinstance(e, str) and e.endswith('/seat-guard.mjs'))] + [guard]
    tmp = settings.with_name(settings.name + '.new')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    os.replace(tmp, settings)
    return []


def config_file(home):
    """The global config file of HOME: ~/.gitconfig, or the XDG file when only that exists."""
    xdg = home / '.config/git/config'
    return xdg if xdg.is_file() and not (home / '.gitconfig').exists() else home / '.gitconfig'


def hooks_path(home):
    """The core.hooksPath that HOME's global config sets, or None."""
    for path in (home / '.gitconfig', home / '.config/git/config'):
        if path.is_file():
            done = subprocess.run(['git', 'config', '--file', str(path), '--get', 'core.hooksPath'],
                                  capture_output=True, text=True)
            if done.returncode == 0 and done.stdout.strip():
                return done.stdout.strip()
    return None


def hooks_setting(home, release):
    """Point core.hooksPath at the release's hooks/git unless the home sets one of its own."""
    target = release / 'hooks/git'
    current = hooks_path(home)
    if current == str(target):
        return []
    if current is not None and not (_ours(current) and current.rstrip('/').endswith('/hooks/git')):
        return [f'core.hooksPath is {current}; left alone (the platform hooks are {target})']
    subprocess.run(['git', 'config', '--file', str(config_file(home)), 'core.hooksPath', str(target)],
                   check=True)
    return []


OWNER_WORDS = 'skills/develop/owner-words.md'


def owner_words(release):
    """The owner's word list and the ask-first rule (one source file in the release), or ''."""
    path = release / OWNER_WORDS
    return path.read_text().strip() if path.is_file() else ''


def block(kind, release):
    entry = release / 'skills/develop/SKILL.md'
    words = owner_words(release)
    if kind == 'claude':
        first = f'@{entry}'
        # Claude Code follows the include, so an activation updates the words with no reinstall.
        words = f'@{release / OWNER_WORDS}' if words else ''
    else:
        first = (f'At session start, on resume and when the task changes, read and apply {entry} '
                 '(the shared session entry).')
    parts = [BEGIN, first, '', COMMIT_RULE, '', NAMING_RULE]
    if words:
        parts += ['', words]
    return '\n'.join(parts + [END])


def write_block(path, text):
    """Put the marked block in the file, replacing an earlier one; everything else stays."""
    old = path.read_text() if path.exists() else ''
    if BEGIN in old and END in old:
        head, rest = old.split(BEGIN, 1)
        tail = rest.split(END, 1)[1]
        new = head + text + tail
    else:
        new = (old.rstrip('\n') + '\n\n' if old.strip() else '') + text + '\n'
    if new != old:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.new')
        tmp.write_text(new)
        os.replace(tmp, path)


def prompt_files(home):
    """Every global prompt file in a home that gets the block, with its kind."""
    files = [(home / '.claude/CLAUDE.md', 'claude'), (home / '.codex/AGENTS.md', 'codex')]
    files += [(path / 'CLAUDE.md', 'claude') for path in sorted((home / '.claude-accounts').glob('*/'))
              if (path / 'settings.json').exists() or (path / '.claude.json').exists()]
    if (home / '.pi/agent').is_dir():
        files.append((home / '.pi/agent/APPEND_SYSTEM.md', 'pi'))
    return files


def install(home, release, role=None):
    notes = link_skills(home, release, role)
    if not role:
        notes += link_agents(home, release)
    notes += codex_rules(home, release)
    codex_config(home)
    notes += codex_title_hook(home, release)
    notes += pi_title_extension(home, release)
    for path, kind in prompt_files(home):
        write_block(path, block(kind, release))
    notes += pi_guard(home, release)
    notes += hooks_setting(home, release)
    return notes


def status(home, release, role=None):
    """Problems, one line each; empty when the home is fully equipped."""
    out = []
    for rel in SKILL_DIRS:
        for name, folder in wanted_skills(release, role).items():
            path = home / rel / name
            if not (path.is_symlink() and os.readlink(path) == str(folder)):
                out.append(f'{path}: not linked to {folder}')
    for name, target in ({} if role else wanted_agents(release)).items():
        path = home / '.claude/agents' / f'{name}.md'
        if not (path.is_symlink() and os.readlink(path) == str(target)):
            out.append(f'{path}: not linked to {target}')
    rules = home / '.codex/rules/default.rules'
    if not (rules.is_symlink() and os.readlink(rules) == str(release / 'hooks/codex.rules')):
        out.append(f'{rules}: not the platform rules')
    for path, kind in prompt_files(home):
        text = path.read_text() if path.exists() else ''
        if BEGIN not in text:
            out.append(f'{path}: no session-entry block')
        elif block(kind, release) not in text:
            out.append(f'{path}: session-entry block is out of date')
    if (home / '.pi/agent').is_dir():
        guard = str(release / 'integrations/pi/seat-guard.mjs')
        try:
            listed = json.loads((home / '.pi/agent/settings.json').read_text()).get('extensions', [])
        except (OSError, ValueError, AttributeError):
            listed = []
        if guard not in listed:
            out.append(f'{home / ".pi/agent/settings.json"}: seat-guard.mjs is not in extensions ({guard})')
    wanted = str(release / 'hooks/git')
    current = hooks_path(home)
    if current is None:
        out.append(f'{config_file(home)}: core.hooksPath is not set (the platform hooks are {wanted})')
    elif current != wanted:
        out.append(f'{config_file(home)}: core.hooksPath is {current}, not {wanted}')
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(prog='ai-guardrails', description=__doc__.split('\n')[0])
    parser.add_argument('command', choices=('install', 'status'))
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--release', type=Path, default=None,
                        help='the release to point at (default: the activated one)')
    parser.add_argument('--role', choices=('assistant', 'ops', 'engineer'), default=None,
                        help="link only this role's skills (agents/skills.json)")
    args = parser.parse_args(argv)
    release = args.release or paths.install()
    if not (release / 'skills').is_dir():
        print(f'ai-guardrails: no platform release at {release}', file=sys.stderr)
        return 1
    if args.command == 'install':
        for note in install(args.home, release, args.role):
            print(f'ai-guardrails: {note}', file=sys.stderr)
        return 0
    problems = status(args.home, release, args.role)
    for line in problems:
        print(line)
    return 1 if problems else 0
