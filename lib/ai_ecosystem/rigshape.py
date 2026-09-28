"""Shape a project's team: write engagements/<project>/rig.yaml from a named shape.

The team spec lives in the project's engagement folder, outside the repository. That folder is
its own small Git repository tracking only rig.yaml and the project marker, so every shape change
is a commit that can be read and reverted. Writing never starts or changes a running team; a new
shape takes effect the next time the team is started. See integrations/openrig/README.md.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from . import workspace

PLATFORM = Path(__file__).resolve().parents[2]
SHAPES = PLATFORM / 'integrations/openrig/shapes'
RUNTIMES = ('claude-code', 'codex')
TRACKED = '*\n!.gitignore\n!rig.yaml\n!project\n'


def engagements():
    return Path(os.environ.get('DEV_PLATFORM_ENGAGEMENTS',
                               Path.home() / '.local/state/dev-platform/engagements'))


def agents_root():
    """Agents through the activated release's link when this is that release, so a team follows
    each activation. OpenRig requires absolute agent paths."""
    current = Path.home() / '.local/share/dev-platform/current'
    if current.exists() and current.resolve() == PLATFORM:
        return current / 'integrations/openrig/agents'
    return PLATFORM / 'integrations/openrig/agents'


def shapes():
    found = {}
    for path in sorted(SHAPES.glob('*.yaml')):
        summary = re.search(r'^summary:\s*"?(.*?)"?\s*$', path.read_text(), re.MULTILINE)
        found[path.stem] = summary.group(1) if summary else ''
    return found


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:40] or 'project'


def engagement_for(project):
    """The folder the ai menu uses: the one whose project marker names this repository, else one
    named for the checkout folder."""
    root = engagements()
    if project.get('repo'):
        for marker in sorted(root.glob('*/project')):
            if marker.read_text().strip() == project['repo']:
                return marker.parent
    return root / slug(Path(project['root']).name)


def seats(shape):
    """The member ids of a shape, in order."""
    return re.findall(r'^\s+- id: (\S+)\n(?:\s+\w.*\n)*?\s+runtime: ', (SHAPES / f'{shape}.yaml').read_text(),
                      re.MULTILINE)


def render(shape, team, runtimes):
    text = (SHAPES / f'{shape}.yaml').read_text()
    text = re.sub(r'^name: .*$', f'name: {team}', text, count=1, flags=re.MULTILINE)
    text = text.replace('agent_ref: local:agents/', f'agent_ref: path:{agents_root()}/')
    members = re.findall(r'^\s+- id: (\S+)\n(?:\s+\w.*\n)*?\s+runtime: ', text, re.MULTILINE)
    for member, runtime in runtimes.items():
        if member not in members:
            raise ValueError(f'the {shape} shape has no seat named {member}; seats: {", ".join(members)}')
        if runtime not in RUNTIMES:
            raise ValueError(f'runtime must be one of {", ".join(RUNTIMES)}')
        text = re.sub(rf'(^\s+- id: {re.escape(member)}\n(?:\s+\w.*\n)*?\s+runtime: )\S+', rf'\g<1>{runtime}',
                      text, count=1, flags=re.MULTILINE)
    return text


def validate(text):
    """OpenRig's own schema check: (valid, errors), or None when the validator cannot run.
    A validator that fails to start says nothing about the spec, so only its verdict counts."""
    if not shutil.which('rig'):
        return None
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as handle:
        handle.write(text)
    try:
        result = subprocess.run(['rig', 'spec', 'validate', '--json', handle.name], capture_output=True, text=True)
        verdict = json.loads(result.stdout)
        return bool(verdict['valid']), '; '.join(verdict.get('errors', []))
    except (ValueError, KeyError, TypeError):
        return None
    finally:
        os.unlink(handle.name)


def git(folder, *args):
    return subprocess.run(['git', '-C', str(folder), *args], capture_output=True, text=True)


def write(project, shape, runtimes):
    if shape not in shapes():
        raise ValueError(f'no shape named {shape}; shapes: {", ".join(shapes())}')
    folder = engagement_for(project)
    team = 'helm-' + folder.name
    text = render(shape, team, runtimes)
    checked = validate(text)
    if checked and not checked[0]:
        raise ValueError(f'OpenRig rejects this spec: {checked[1]}')
    folder.mkdir(parents=True, exist_ok=True)
    if project.get('repo'):
        (folder / 'project').write_text(project['repo'] + '\n')
    if not (folder / '.git').exists():
        git(folder, 'init', '-q')
        (folder / '.gitignore').write_text(TRACKED)
    (folder / 'rig.yaml').write_text(text)
    git(folder, 'add', '.gitignore', 'rig.yaml', *(['project'] if project.get('repo') else []))
    changed = git(folder, 'diff', '--cached', '--quiet').returncode != 0
    if changed:
        seats = ', '.join(f'{m}={r}' for m, r in sorted(runtimes.items()))
        git(folder, '-c', 'user.name=dev-platform', '-c', 'user.email=dev-platform@localhost', 'commit', '-q',
            '-m', f'rig: {shape} shape for {team}' + (f' ({seats})' if seats else ''))
    return dict(team=team, spec=str(folder / 'rig.yaml'), shape=shape, changed=changed,
                validated=None if checked is None else checked[0])


def main(argv=None):
    parser = argparse.ArgumentParser(prog='rig-shape', description=__doc__.split('\n')[0])
    parser.add_argument('--config', type=Path, default=Path(os.environ.get(
        'DEV_PLATFORM_REPOS', Path.home() / '.config/dev-platform/repos.conf')))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list', help='the shapes a team can take')
    for name, help_text in (('show', "the project's current team spec"), ('history', 'every shape change, newest first')):
        sub.add_parser(name, help=help_text).add_argument('project')
    writer = sub.add_parser('write', help="write the project's team spec from a shape; the team starts with it next time")
    writer.add_argument('project', help='project id, owner/repo, or checkout path')
    writer.add_argument('shape')
    writer.add_argument('--runtime', action='append', default=[], metavar='SEAT=RUNTIME',
                        help=f'a seat on another runtime ({" or ".join(RUNTIMES)}), for example lead=codex')
    writer.add_argument('--all', choices=RUNTIMES, help='every seat on this runtime, for example claude-code')
    args = parser.parse_args(argv)
    try:
        if args.command == 'list':
            for name, summary in shapes().items():
                print(f'{name}\t{summary}')
            return 0
        project = workspace.find_project(workspace.catalog(args.config)[0], args.project)
        folder = engagement_for(project)
        if args.command == 'show':
            spec = folder / 'rig.yaml'
            print(spec.read_text() if spec.is_file() else f'{project["repo"]} has no team spec yet; it starts with the build shape')
            return 0
        if args.command == 'history':
            log = git(folder, 'log', '--format=%h %ad %s', '--date=format:%Y-%m-%d %H:%M')
            print(log.stdout.strip() or 'no shape changes recorded yet')
            return 0
        if args.shape not in shapes():
            raise ValueError(f'no shape named {args.shape}; shapes: {", ".join(shapes())}')
        runtimes = {seat: args.all for seat in seats(args.shape)} if args.all else {}
        for item in args.runtime:
            seat, _, runtime = item.partition('=')
            runtimes[seat] = runtime
        result = write(project, args.shape, runtimes)
    except ValueError as error:
        print(f'rig-shape: {error}', file=sys.stderr)
        return 2
    state = 'recorded' if result['changed'] else 'unchanged'
    check = {True: 'valid by rig spec validate', False: 'invalid', None: 'not validated (rig is not on PATH)'}[result['validated']]
    print(f"{result['team']}: {result['shape']} shape {state} in {result['spec']}; {check}. "
          'It takes effect the next time the team starts.')
    return 0
