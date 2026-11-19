#!/usr/bin/env python3
"""Git and gh rules of the platform guard (hooks/pre-tool-use-guard.sh).

Reads one shell command on stdin. Exits 0 to allow. Exits 2 and prints the reason to refuse.

  guard_git.py --cwd DIR

The command is split into words the way a shell does it. Quoted text, comments and heredoc
bodies never count as commands, so `grep 'gh pr merge' file` passes. A rule applies only to a
command word: the start of a line, or the word after ; & | ( or $( . A `bash -c` or `eval`
string is read again. The tier of the repository comes from lib/ai_ecosystem/tiers.py.

A command that moves HEAD or the index (checkout, switch, merge, reset, pull, cherry-pick, revert,
stash pop and apply) is refused when another live agent process (Claude Code or Codex) has its
working directory in the same worktree, or in a folder of it. Sessions that share a bench must not
move HEAD under each other (2026-11-06: a checkout and a merge in a shared worktree broke the check
of another session).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

PROTECTED = ('main', 'master', 'develop')
TOOL_BRANCH = ('claude/', 'codex/', 'copilot/')
TIERS = Path(__file__).resolve().parent.parent / 'lib/ai_ecosystem/tiers.py'
LAND_VARIABLE = 'DEV_LOOP_LAND'
ENV_WORD = re.compile(r'[A-Za-z_][A-Za-z0-9_]*=')
KEYWORDS = {'{', '!', 'if', 'then', 'else', 'elif', 'do', 'while', 'until', 'time'}
WRAPPERS = {'sudo', 'nohup', 'command', 'exec', 'nice', 'env', 'builtin', 'setsid', 'xargs'}
WRAPPER_ARG_OPTIONS = {'sudo': {'-u', '-g', '-h', '-p', '-C', '-D', '-R', '-T', '-U'}, 'nice': {'-n'}}
SHELLS = {'bash', 'sh', 'zsh', 'dash'}
AGENTS = ('claude', 'codex')
# Claude Code builds whose executable is named by version (the desktop app, the native installer).
AGENT_DIRS = ('/ccd-cli/', '/claude/versions/')
HEAD_MOVERS = {'checkout', 'switch', 'merge', 'reset', 'pull', 'cherry-pick', 'revert'}


class Refuse(Exception):
    pass


# ---------------------------------------------------------------- shell words

def match_paren(text, start):
    """Index of the ) that closes a $( whose body starts at START."""
    depth, i = 1, start
    while i < len(text):
        c = text[i]
        if c == "'":
            i = text.find("'", i + 1)
            if i < 0:
                return len(text)
        elif c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == '\\' else 1
        elif c == '\\':
            i += 1
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text)


def parse(text):
    """The simple commands of TEXT, each a list of words, in order. Substitutions add commands."""
    segments, words, cur, has = [], [], [], False
    heredocs = []
    i, n = 0, len(text)

    def end_word():
        nonlocal cur, has
        if has:
            words.append(''.join(cur))
        cur, has = [], False

    def end_segment():
        end_word()
        if words:
            segments.append(list(words))
            words.clear()

    def substitution(start, body_start, closer):
        """Add the commands inside $( ) or backticks; return the index after the closer."""
        if closer == ')':
            end = match_paren(text, body_start)
        else:
            end = text.find('`', body_start)
            end = n if end < 0 else end
        segments.extend(parse(text[body_start:end]))
        return end + 1

    while i < n:
        c = text[i]
        if c == "'":
            j = text.find("'", i + 1)
            j = n if j < 0 else j
            cur.append(text[i + 1:j])
            has = True
            i = j + 1
        elif c == '"':
            j, buf = i + 1, []
            while j < n and text[j] != '"':
                if text[j] == '\\' and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                elif text.startswith('$(', j):
                    k = substitution(j, j + 2, ')')
                    buf.append(text[j:k])
                    j = k
                elif text[j] == '`':
                    k = substitution(j, j + 1, '`')
                    buf.append(text[j:k])
                    j = k
                else:
                    buf.append(text[j])
                    j += 1
            cur.append(''.join(buf))
            has = True
            i = j + 1
        elif c == '\\':
            if i + 1 < n and text[i + 1] == '\n':
                i += 2
            else:
                if i + 1 < n:
                    cur.append(text[i + 1])
                    has = True
                i += 2
        elif text.startswith('$(', i):
            i = substitution(i, i + 2, ')')
            cur.append('$()')
            has = True
        elif c == '`':
            i = substitution(i, i + 1, '`')
            cur.append('``')
            has = True
        elif c == '#' and not has:
            while i < n and text[i] != '\n':
                i += 1
        elif c in ' \t':
            end_word()
            i += 1
        elif c == '\n':
            end_segment()
            i += 1
            for delimiter, dash in heredocs:
                while i < n:
                    j = text.find('\n', i)
                    j = n if j < 0 else j
                    line = text[i:j]
                    i = j + 1
                    if (line.lstrip('\t') if dash else line) == delimiter:
                        break
            heredocs = []
        elif c in ';&|()':
            end_segment()
            while i < n and text[i] in ';&|()':
                i += 1
        elif text.startswith('<<', i) and not text.startswith('<<<', i):
            i += 2
            dash = i < n and text[i] == '-'
            i += 1 if dash else 0
            while i < n and text[i] in ' \t':
                i += 1
            delimiter = []
            while i < n and text[i] not in ' \t\n;&|()':
                if text[i] not in '\'"\\':
                    delimiter.append(text[i])
                i += 1
            heredocs.append((''.join(delimiter), dash))
        else:
            cur.append(c)
            has = True
            i += 1
    end_segment()
    return segments


def command_words(words):
    """Drop assignments, keywords and wrappers (sudo, env, ...); the rest starts with the command."""
    words = [w for w in words if not re.fullmatch(r'[0-9]*[<>]+', w)]
    for k, word in enumerate(words):
        if word.startswith(LAND_VARIABLE) and (ENV_WORD.match(word) and k < 6 or words[0] == 'export'):
            raise Refuse('DEV_LOOP_LAND is set by the loop land verb only; an agent must not set it')
        if not (ENV_WORD.match(word) or word.startswith('-') or os.path.basename(word) in WRAPPERS or word == 'export'):
            break
    i = 0
    while i < len(words):
        word = words[i]
        base = os.path.basename(word)
        if word in KEYWORDS or ENV_WORD.match(word):
            i += 1
        elif base in WRAPPERS:
            i += 1
            while i < len(words) and (words[i].startswith('-') or ENV_WORD.match(words[i])):
                takes_argument = words[i] in WRAPPER_ARG_OPTIONS.get(base, ())
                i += 2 if takes_argument else 1
        else:
            break
    return words[i:]


def expand(segments, depth=0):
    """SEGMENTS with every `bash -c STRING` and `eval STRING` read as commands too."""
    out = []
    for words in segments:
        words = command_words(words)
        if not words:
            continue
        out.append(words)
        base = os.path.basename(words[0])
        if depth < 4 and base in SHELLS:
            for k, word in enumerate(words[1:], 1):
                if word.startswith('-') and not word.startswith('--') and 'c' in word and k + 1 < len(words):
                    out.extend(expand(parse(words[k + 1]), depth + 1))
                    break
        elif depth < 4 and base == 'eval':
            out.extend(expand(parse(' '.join(words[1:])), depth + 1))
    return out


# ---------------------------------------------------------------- git facts

def run(args, timeout=10):
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def git(directory, *args):
    return run(['git', '-C', str(directory), *args])


class Context:
    def __init__(self, cwd):
        self.cwd = Path(cwd or os.getcwd())
        self.dir = self.cwd
        self.branch = {}
        self.tiers = {}
        self.offs = {}
        self.own = self.toplevel(self.cwd)

    def resolve(self, base, path):
        path = Path(os.path.expanduser(path))
        return Path(os.path.normpath(path if path.is_absolute() else Path(base) / path))

    def toplevel(self, directory):
        top = git(directory, 'rev-parse', '--show-toplevel') if Path(directory).is_dir() else None
        return os.path.realpath(top) if top else None

    def tier(self, directory):
        """The tier of the repository at DIRECTORY. No answer, or tier 0, counts as tier 3."""
        key = str(directory)
        if key not in self.tiers:
            value = run([sys.executable, '-I', str(TIERS), '--field', 'tier', key]) if TIERS.is_file() else None
            self.tiers[key] = int(value) if value and value.isdigit() and int(value) > 0 else 3
        return self.tiers[key]

    def git_off(self, directory):
        """True when the project record turns the Git rules off for the repository at DIRECTORY (SDD-PJ-04)."""
        key = str(directory)
        if key not in self.offs:
            value = run([sys.executable, '-I', str(TIERS), '--field', 'off', key]) if TIERS.is_file() else None
            self.offs[key] = 'git' in (value or '').split(',')
        return self.offs[key]

    def current_branch(self, directory):
        key = str(directory)
        if key in self.branch:
            return self.branch[key]
        return git(directory, 'symbolic-ref', '--short', '-q', 'HEAD')

    def checked_out(self, directory):
        """branch name -> worktree path, for every worktree of the repository."""
        found, path = {}, None
        for line in (git(directory, 'worktree', 'list', '--porcelain') or '').splitlines():
            if line.startswith('worktree '):
                path = os.path.realpath(line[9:])
            elif line.startswith('branch refs/heads/') and path:
                found[line[18:]] = path
        return found


# ---------------------------------------------------------------- live agents

def proc_parent(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[1])
    except (OSError, ValueError, IndexError):
        out = run(['ps', '-o', 'ppid=', '-p', str(pid)])
        return int(out) if out and out.strip().isdigit() else 0


def ancestors():
    """This process and its parents: the agent that runs this guard is not "another" agent."""
    found, pid = set(), os.getpid()
    while pid > 1 and pid not in found:
        found.add(pid)
        pid = proc_parent(pid)
    return found


def agent_name(exe, argv0):
    """'claude' or 'codex' when EXE or ARGV0 is an agent, else None."""
    for path in (exe, argv0):
        base = os.path.basename(path or '')
        stem = base[:-4] if base.endswith('.exe') else base
        if stem in AGENTS:
            return stem
    if exe and any(part in exe for part in AGENT_DIRS):
        return 'claude'
    return None


def live_agents():
    """(pid, name, cwd) of every agent process that this user can read."""
    found = []
    proc = Path('/proc')
    if proc.is_dir():
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                exe = os.readlink(entry / 'exe')
            except OSError:
                exe = ''
            try:
                argv0 = (entry / 'cmdline').read_bytes().split(b'\0', 1)[0].decode(errors='replace')
                name = agent_name(exe, argv0)
                if name:
                    found.append((int(entry.name), name, os.readlink(entry / 'cwd')))
            except OSError:
                continue
        return found
    for line in (run(['ps', '-axo', 'pid=,comm=']) or '').splitlines():
        pid, _, comm = line.strip().partition(' ')
        name = agent_name(comm.strip(), comm.strip())
        if name and pid.isdigit():
            out = run(['lsof', '-a', '-p', pid, '-d', 'cwd', '-Fn']) or ''
            cwd = next((l[1:] for l in out.splitlines() if l.startswith('n')), '')
            if cwd:
                found.append((int(pid), name, cwd))
    return found


def other_agent_in(ctx, top):
    """(pid, name, cwd) of a live agent, not this one, whose cwd is in the worktree TOP."""
    mine = ancestors()
    for pid, name, cwd in live_agents():
        if pid in mine:
            continue
        real = os.path.realpath(cwd)
        if real != top and not real.startswith(top.rstrip('/') + '/'):
            continue
        # A folder inside TOP can be another worktree (.claude/worktrees/slot-1): compare its own top.
        if ctx.toplevel(real) == top:
            return pid, name, real
    return None


# ---------------------------------------------------------------- git rules

def rule_shared_worktree(ctx, gdir, sub, args):
    if any(arg in ('--abort', '--quit', '-h', '--help') for arg in args):
        return
    top = ctx.toplevel(gdir) if Path(gdir).is_dir() else None
    if not top:
        return
    other = other_agent_in(ctx, top)
    if other:
        pid, name, cwd = other
        what = f'git {sub} {args[0]}' if sub == 'stash' else f'git {sub}'
        raise Refuse(f'{what} moves HEAD or the index of {top}, and another live agent works there '
                     f'({name}, pid {pid}, in {cwd}). Do not move HEAD under it. Commit on the bench '
                     f'where it is, under the lock; to read another ref, use git show <ref>:<path> '
                     f'and git diff <a> <b>')


def short_letters(arg):
    return set(arg[1:]) if arg.startswith('-') and not arg.startswith('--') else set()


def push_target(spec, current):
    """(destination branch name, forced) of one refspec."""
    forced = spec.startswith('+')
    spec = spec.lstrip('+')
    source, colon, destination = spec.partition(':')
    name = destination if colon else source
    if name in ('HEAD', '@'):
        name = current or ''
    for prefix in ('refs/heads/',):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name, forced


def rule_push(ctx, gdir, args):
    tier = ctx.tier(gdir)
    force = False
    positional = []
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in ('-o', '--push-option', '--receive-pack', '--exec', '--repo'):
            skip = True
        elif arg in ('--all', '--mirror', '--branches'):
            raise Refuse(f'git push {arg} is refused; name the branch: git push -u origin <type/short-description>')
        elif arg.startswith('--force') or 'f' in short_letters(arg):
            force = True
        elif arg.startswith('-'):
            continue
        else:
            positional.append(arg)
    if force:
        raise Refuse('force push is refused; nothing pushed for review is rewritten')
    specs = positional[1:]
    current = ctx.current_branch(gdir)
    if not specs:
        if tier == 1:
            return
        raise Refuse('bare git push is refused; name the branch: git push -u origin <type/short-description>')
    for spec in specs:
        name, forced = push_target(spec, current)
        if forced:
            raise Refuse('force push is refused; nothing pushed for review is rewritten')
        if name.startswith('wip/'):
            raise Refuse('a wip/ branch is never pushed; rename it to a type/short-description branch first')
        if name in PROTECTED:
            if tier == 1 and name in ('main', 'master'):
                continue
            raise Refuse(f'git push to {name} is refused; open a pull request from a type/short-description branch')
        if tier == 3 and name.startswith(TOOL_BRANCH):
            raise Refuse('professional repository: no tool or model attribution reaches the ledger (tool-named branch)')


def rule_merge(ctx, gdir, args):
    if any(arg in ('--abort', '--quit', '--continue') for arg in args):
        return
    branch = ctx.current_branch(gdir)
    if branch not in PROTECTED:
        return
    if '--ff-only' in args and branch in ('main', 'master') and ctx.tier(gdir) == 1:
        return
    raise Refuse(f'merging into {branch} is refused; the owner merges')


def rule_commit(ctx, gdir, args):
    for arg in args:
        if arg == '--':
            break
        if arg == '--no-verify' or 'n' in short_commit_flags(arg):
            raise Refuse('--no-verify is refused; fix the cause of the hook failure')
    if '--amend' in args:
        raise Refuse('history rewrite is refused (rebase, reset --hard, commit --amend, filter-branch)')


def short_commit_flags(arg):
    """The flag letters of a short option group, up to the first letter that takes an argument."""
    letters = []
    if arg.startswith('-') and not arg.startswith('--'):
        for letter in arg[1:]:
            if letter in 'mFcCtSu':
                break
            letters.append(letter)
    return set(letters)


def rule_branch(ctx, gdir, args):
    delete = force = False
    targets = []
    for arg in args:
        letters = short_letters(arg)
        if arg == '--delete' or 'd' in letters or 'D' in letters:
            delete = True
        if arg == '--force' or 'f' in letters or 'D' in letters:
            force = True
        if not arg.startswith('-'):
            targets.append(arg)
    if not (delete and force):
        return
    owners = ctx.checked_out(gdir)
    for name in targets:
        where = owners.get(name)
        if where and where != ctx.own:
            raise Refuse(f'deleting branch {name} is refused; another worktree ({where}) has it checked out')


def rule_worktree(ctx, gdir, args):
    if not args or args[0] != 'remove':
        return
    paths = [a for a in args[1:] if not a.startswith('-')]
    for path in paths:
        target = os.path.realpath(ctx.resolve(gdir, path))
        if target != ctx.own:
            raise Refuse(f'removing worktree {path} is refused; only the worktree of this session can be removed')


def rule_clean(ctx, gdir, args):
    if '--dry-run' in args or any('n' in short_letters(a) for a in args):
        return
    targets = [gdir]
    after = False
    for arg in args:
        if arg == '--':
            after = True
        elif after or not arg.startswith('-'):
            targets.append(ctx.resolve(gdir, arg))
    for target in targets:
        probe = target if Path(target).is_dir() else Path(target).parent
        top = ctx.toplevel(probe)
        if top and top != ctx.own:
            raise Refuse(f'git clean is refused in {top}; it is not the worktree of this session')


def rule_config(ctx, gdir, args):
    if any(a.lower() == 'core.hookspath' for a in args) and not any(
            a in ('--get', '--get-all', '--list', '-l', '--show-origin') for a in args):
        raise Refuse('changing core.hooksPath is refused; it carries the platform git hooks')


def git_segment(ctx, words):
    gdir = ctx.dir
    i = 1
    while i < len(words):
        arg = words[i]
        if arg == '-C' and i + 1 < len(words):
            gdir = ctx.resolve(gdir, words[i + 1])
            i += 2
        elif arg == '-c' and i + 1 < len(words):
            if words[i + 1].lower().startswith('core.hookspath'):
                raise Refuse('changing core.hooksPath is refused; it carries the platform git hooks')
            i += 2
        elif arg in ('--git-dir', '--work-tree', '--namespace', '--exec-path', '--super-prefix', '--config-env'):
            i += 2
        elif arg.startswith('--work-tree='):
            gdir = ctx.resolve(gdir, arg.split('=', 1)[1])
            i += 1
        elif arg.startswith('-'):
            i += 1
        else:
            break
    if i >= len(words):
        return
    sub, args = words[i], words[i + 1:]
    if sub in HEAD_MOVERS or (sub == 'stash' and args[:1] in (['pop'], ['apply'])):
        rule_shared_worktree(ctx, gdir, sub, args)
    if sub in ('push', 'merge', 'commit', 'rebase', 'filter-branch', 'reset', 'branch') and ctx.git_off(gdir):
        return   # the Git rules of this project are off; the rules for a second session and for the hooks stay
    if sub == 'push':
        if '--no-verify' in args:
            raise Refuse('--no-verify is refused; fix the cause of the hook failure')
        rule_push(ctx, gdir, args)
    elif sub == 'merge':
        rule_merge(ctx, gdir, args)
    elif sub == 'commit':
        rule_commit(ctx, gdir, args)
    elif sub in ('rebase', 'filter-branch'):
        raise Refuse('history rewrite is refused (rebase, reset --hard, commit --amend, filter-branch)')
    elif sub == 'reset' and '--hard' in args:
        raise Refuse('history rewrite is refused (rebase, reset --hard, commit --amend, filter-branch)')
    elif sub in ('checkout', 'switch'):
        names = [a for a in args if not a.startswith('-')]
        creates = [k for k, a in enumerate(args) if a in ('-b', '-B', '-c', '-C')]
        name = args[creates[0] + 1] if creates and creates[0] + 1 < len(args) else (names[0] if names else None)
        if name:
            ctx.branch[str(gdir)] = name
    elif sub == 'branch':
        rule_branch(ctx, gdir, args)
    elif sub == 'worktree':
        rule_worktree(ctx, gdir, args)
    elif sub == 'clean':
        rule_clean(ctx, gdir, args)
    elif sub == 'config':
        rule_config(ctx, gdir, args)


def gh_segment(ctx, words):
    if ctx.git_off(ctx.dir):
        return
    args = []
    skip = False
    for arg in words[1:]:
        if skip:
            skip = False
        elif arg in ('-R', '--repo', '--hostname'):
            skip = True
        else:
            args.append(arg)
    names = [a for a in args if not a.startswith('-')]
    if names[:2] == ['pr', 'merge'] or names[:2] == ['pr', 'ready']:
        raise Refuse('gh pr merge, ready and approve are refused; the owner reviews, marks ready and merges')
    if names[:2] == ['pr', 'review'] and any(a in ('--approve', '-a') for a in args):
        raise Refuse('gh pr merge, ready and approve are refused; the owner reviews, marks ready and merges')
    if names[:1] == ['api']:
        for arg in args:
            if re.search(r'/merges?(\?|$)', arg) or re.search(r'pulls/[^/]+/merge(\?|$)', arg) or 'mergePullRequest' in arg:
                raise Refuse('a gh api call that merges is refused; the owner merges')


def check(command, cwd):
    ctx = Context(cwd)
    for words in expand(parse(command)):
        base = os.path.basename(words[0])
        if base == 'cd' or base == 'pushd':
            target = words[1] if len(words) > 1 else str(Path.home())
            if target != '-':
                ctx.dir = ctx.resolve(ctx.dir, target)
        elif base == 'git':
            git_segment(ctx, words)
        elif base == 'gh':
            gh_segment(ctx, words)


def main(argv):
    cwd = argv[argv.index('--cwd') + 1] if '--cwd' in argv else ''
    try:
        check(sys.stdin.read(), cwd)
    except Refuse as refusal:
        print(refusal)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
