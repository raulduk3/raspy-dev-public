"""Thin project organization over Git, the session index, and the existing loop.

No task database, dispatcher, transcript import, native-account changes, or daemon.
The only authored projection is an explicitly requested external OpenRig catalog.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from .store import ID_RE, VERSION, default_root

PLATFORM = Path(__file__).resolve().parents[2]
REPO_RE = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
VERBS = ('status', 'plan', 'start', 'go', 'pause', 'collect')


def git(path, *args):
    run = subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True,
                         timeout=10)
    return run.stdout.strip() if run.returncode == 0 else None


def identity(path):
    """Resolve linked worktrees/symlinks to the same actual Git repository."""
    value = git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    return str(Path(value).resolve()) if value else None


def project_id(repo):
    # Avoid flattening owner/repo into a potentially ambiguous string.
    slug = re.sub(r'[^a-z0-9-]+', '-', repo.lower()).strip('-')[:55]
    return slug + '-' + hashlib.sha256(repo.encode()).hexdigest()[:8]


def catalog(config, dev_root=None):
    projects, warnings, identities = [], [], {}
    if config.exists():
        for number, line in enumerate(config.read_text().splitlines(), 1):
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            fields = line.split()
            if len(fields) not in (3, 4) or not REPO_RE.fullmatch(fields[0]) or fields[2] not in ('local', 'owner', 'bot'):
                raise ValueError(f'{config}:{number}: expected owner/repo checkout local|owner|bot [base]')
            repo, path = fields[:2]
            root = Path(path).expanduser().resolve()
            common = identity(root)
            if any(p['repo'] == repo for p in projects) or (common and common in identities):
                raise ValueError(f'ambiguous configured repository: {repo}')
            item = dict(id=project_id(repo), repo=repo, root=str(root), group=repo.split('/')[0],
                        common_dir=common, available=bool(common), loop_enabled=True,
                        source='repos.conf', mode=fields[2])
            projects.append(item)
            if common:
                identities[common] = item
            else:
                warnings.append(f'{repo}: configured checkout unavailable')
    else:
        warnings.append(f'repository configuration missing: {config}')
    if dev_root:
        dev_root = Path(dev_root).expanduser().resolve()
        if not dev_root.is_dir():
            raise ValueError(f'development root is not a directory: {dev_root}')
        for item in projects:
            try:
                relative = Path(item['root']).relative_to(dev_root)
            except ValueError:
                continue
            item['group'] = relative.parts[0] if len(relative.parts) > 1 else 'local'
        # Repo directly under Dev or beneath one grouping directory, never worktree recursion.
        candidates = []
        for entry in sorted(dev_root.iterdir()):
            if not entry.is_dir() or entry.name.startswith('.'):
                continue
            if (entry / '.git').exists():
                candidates.append((entry, 'local'))
            else:
                candidates.extend((child, entry.name) for child in sorted(entry.iterdir())
                                  if child.is_dir() and not child.name.startswith('.') and (child / '.git').exists())
        for root, group in candidates:
            common = identity(root)
            if not common or common in identities:
                continue
            root = root.resolve()
            item = dict(id=project_id(str(root)), repo=None, root=str(root), group=group,
                        common_dir=common, available=True, loop_enabled=False, source='dev-root')
            projects.append(item)
            identities[common] = item
    projects.sort(key=lambda p: (p['group'], p['repo'] or p['root']))
    return projects, warnings


def find_project(projects, name):
    matches = [p for p in projects if name in (p['id'], p['repo'], p['root'])]
    if len(matches) != 1:
        raise ValueError(f'project must identify exactly one catalog entry: {name}')
    return matches[0]


def session_rows(projects, state, selected=None, limit=20):
    """Read existing manifests only. Missing worktrees are unassigned, never guessed."""
    by_common = {p['common_dir']: p for p in projects if p['common_dir']}
    cache, rows = {}, []
    for path in sorted((state / 'manifests').glob('*.json')):
        if not ID_RE.fullmatch(path.stem):
            continue
        try:
            item = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        if not isinstance(item, dict) or item.get('version') != VERSION:
            continue
        cwd = item.get('cwd')
        key = cwd if isinstance(cwd, str) and os.path.isabs(cwd) else None
        if key and key not in cache:
            cache[key] = identity(key)
        project = by_common.get(cache.get(key))
        pid = project['id'] if project else None
        if selected and (pid != selected if selected != 'unassigned' else pid is not None):
            continue
        rows.append({**{k: item.get(k) for k in ('id', 'runtime', 'owner', 'cwd', 'updated_at', 'status')},
                     'title': item.get('title_override') or item.get('title'), 'project': pid})
    rows.sort(key=lambda r: str(r.get('updated_at') or ''), reverse=True)
    return dict(sessions=rows[:limit], total=len(rows), has_more=len(rows) > limit)


def loop_argv(project, verb, selectors):
    if not project['loop_enabled'] or not project['available']:
        raise ValueError('loop controls require an available configured repos.conf checkout')
    if verb not in VERBS:
        raise ValueError('unsupported loop operation')
    if verb == 'start':
        # start names the goal's branch, an ordinary type/slug branch.
        if len(selectors) != 1 or not re.fullmatch(r'(feat|fix|docs|refactor|test|chore|perf)/[a-z0-9][a-z0-9._-]*',
                                                   selectors[0]):
            raise ValueError('start takes the branch for the goal: type/slug, for example feat/snake-game')
    elif selectors and (verb != 'go' or selectors[0] not in ('only', 'skip') or len(selectors) < 2
                        or any(not re.fullmatch(r'[1-9][0-9]*', n) for n in selectors[1:])):
        raise ValueError('only go accepts selectors: only|skip followed by positive issue numbers')
    return [str(PLATFORM / 'skills/loop/scripts/loop.sh'), verb, project['repo'], *selectors]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp)


def safe_path(root, relative, directory=False):
    path = root / relative
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
        raise ValueError(f'projection path cannot be a symlink: {path}')
    if path.exists() and (not path.is_dir() if directory else not path.is_file()):
        raise ValueError(f'projection path has wrong type: {path}')
    for parent in path.parents:
        if parent == root.parent:
            break
        if parent.exists() and not parent.is_dir():
            raise ValueError(f'projection parent is not a directory: {parent}')
    return path


def sync_openrig(projects, destination):
    # Resolve only after rejecting a symlink at the requested root.
    raw = Path(destination).expanduser().absolute()
    if raw.is_symlink():
        raise ValueError('workspace root cannot be a symlink')
    root = raw.resolve()
    ancestor = root
    while not ancestor.exists():
        ancestor = ancestor.parent
    if identity(ancestor):
        raise ValueError('OpenRig projection must be outside Git repositories')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = safe_path(root, '.ai-work.lock')
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        receipt_path = safe_path(root, '.ai-work-projection.json')
        old = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'version': 1, 'files': {}}
        if old.get('version') != 1 or not isinstance(old.get('files'), dict):
            raise ValueError('invalid projection ownership receipt')
        files, directories, entries = {}, [], []
        for project in projects:
            rel = 'projects/' + project['id']
            entries.append(dict(id=project['id'], root=rel))
            directories.extend([rel, rel + '/missions', rel + '/exhaust'])
            files[rel + '/project.yaml'] = json.dumps({
                'schema': 'openrig.project/v0alpha1', 'kind': 'project',
                'metadata': {'id': project['id'], 'name': project['group'] + ' / ' + Path(project['root']).name},
                'install': {'intent': 'SPEC.md', 'context': [], 'skills': []},
                'missions': {'root': 'missions'}}, indent=2) + '\n'
            files[rel + '/SPEC.md'] = (
                '# ' + (project['repo'] or Path(project['root']).name) + '\n\n'
                'External development workspace; the code checkout is ' + json.dumps(project['root']) + '.\n\n'
                'Display group: ' + project['group'] + '. Grouping grants no authorization.\n'
                'The existing development loop owns execution. No OpenRig missions or queue entries are inferred.\n'
                'Use ai-work with this project identity: `' + project['id'] + '`.\n'
                'Read repository instructions in the code checkout before changes.\n')
        files['workspace.yaml'] = json.dumps({'schema': 'openrig.workspace/v0alpha1', 'projects': entries}, indent=2) + '\n'
        # Preflight the entire projection before changing any generated content.
        for rel in directories:
            safe_path(root, rel, directory=True)
        for rel, content in files.items():
            path = safe_path(root, rel)
            if path.exists() and old['files'].get(rel) != digest(path.read_bytes()):
                raise ValueError(f'unowned or locally modified projection: {path}')
        for rel in directories:
            (root / rel).mkdir(parents=True, exist_ok=True, mode=0o700)
        owned = dict(old['files'])
        for rel, content in files.items():
            data = content.encode()
            if not (root / rel).exists() or (root / rel).read_bytes() != data:
                atomic(root / rel, data)
            owned[rel] = digest(data)
        atomic(receipt_path, (json.dumps({'version': 1, 'files': owned}, indent=2) + '\n').encode())
        return dict(workspace=str(root), catalog=str(root / 'workspace.yaml'), projects=len(entries),
                    native_config_changed=False, dispatch_started=False)
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='ai-work', description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(os.environ.get('DEV_PLATFORM_REPOS', Path.home() / '.config/dev-platform/repos.conf')))
    parser.add_argument('--dev-root', help='also discover Git roots directly below this directory or one group below it')
    parser.add_argument('--state-root', type=Path, default=default_root(), help='existing ai-session index')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('projects')
    s = sub.add_parser('sessions'); s.add_argument('--project'); s.add_argument('--limit', type=int, default=20)
    s = sub.add_parser('loop'); s.add_argument('project'); s.add_argument('verb', choices=VERBS)
    s.add_argument('--dry-run', action='store_true'); s.add_argument('selectors', nargs='*')
    s = sub.add_parser('sync-openrig'); s.add_argument('--workspace', required=True)
    a = parser.parse_args(argv)
    try:
        config = a.config.expanduser().resolve()
        projects, warnings = catalog(config, a.dev_root)
        if a.command == 'projects':
            result = dict(projects=projects, warnings=warnings)
        elif a.command == 'sessions':
            if not 1 <= a.limit <= 200:
                raise ValueError('--limit must be between 1 and 200')
            selected = (find_project(projects, a.project)['id'] if a.project and a.project != 'unassigned' else a.project)
            result = dict(session_rows(projects, a.state_root, selected, a.limit), warnings=warnings)
        elif a.command == 'loop':
            command = loop_argv(find_project(projects, a.project), a.verb, a.selectors)
            if not a.dry_run:
                return subprocess.run(command, env=dict(os.environ, DEV_PLATFORM_REPOS=str(config))).returncode
            result = dict(argv=command, config=str(config), execute=False)
        else:
            result = dict(sync_openrig(projects, a.workspace), warnings=warnings)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f'ai-work: {exc}', file=sys.stderr)
        return 2
