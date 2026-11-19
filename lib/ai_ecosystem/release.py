"""ai-release: build, verify and activate a platform release.

A release is `/opt/dev-platform/releases/<commit>/` (see paths.py), and `current` links to the
activated one, which every user runs as DEV_PLATFORM_HOME. It is built from a commit with `git archive`, never copied from a working
tree, so what runs is exactly what the commit holds. A release whose tracked files no longer
match its commit has drifted: it was copied from a dirty tree or edited in place.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from . import paths

SHARE = paths.share()
# On dev-server releases are built from root's mirror of the owner's checkout (bootstrap.sh
# keeps it fetched), so every user verifies against the same repository.
CHECKOUT = SHARE / 'repo.git' if (SHARE / 'repo.git').is_dir() else paths.checkout()


def git(checkout, *args):
    # The checkout and the user reading it may differ (root builds from the owner's repository,
    # the owner verifies against root's mirror); trust only this one repository for the call.
    return subprocess.run(['git', '-c', f'safe.directory={Path(checkout).resolve()}', '-C', str(checkout), *args],
                          capture_output=True, text=False)


def tracked(checkout, commit):
    """{path: (mode, blob)} for every file the commit tracks, or None when unknown."""
    try:
        run = git(checkout, 'ls-tree', '-r', '-z', '--full-tree', commit)
    except OSError:
        return None
    if run.returncode != 0:
        return None
    files = {}
    for entry in run.stdout.split(b'\0'):
        if not entry:
            continue
        meta, path = entry.split(b'\t', 1)
        mode, kind, blob = meta.split()
        if kind == b'blob':
            files[os.fsdecode(path)] = (mode.decode(), blob.decode())
    return files


def blob_id(path, length):
    """The id git would give this file's content, in the repository's hash length."""
    data = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
    digest = hashlib.sha256 if length == 64 else hashlib.sha1
    return digest(b'blob %d\0' % len(data) + data).hexdigest()


def verify(release, checkout=CHECKOUT):
    """Compare a release with the commit it is named for. Untracked additions, such as the
    Pi runtime link under integrations/pi/node_modules, are not drift."""
    if not Path(release).exists():
        return {'state': 'missing', 'reason': 'no release is activated'}
    release = Path(release).resolve()
    commit = release.name
    if release.parent.name != 'releases':
        return {'state': 'unsupported', 'reason': 'platform is not an activated release'}
    files = tracked(checkout, commit)
    if files is None:
        return {'state': 'unverified', 'commit': commit,
                'reason': f'git or the commit is unavailable in {checkout}'}
    changed, missing = [], []
    for rel, (mode, blob) in sorted(files.items()):
        path = release / rel
        if not path.exists() and not path.is_symlink():
            missing.append(rel)
            continue
        try:
            same = (mode == '120000') == path.is_symlink() and blob_id(path, len(blob)) == blob
        except OSError:
            same = False
        if not same:
            changed.append(rel)
    out = {'state': 'broken' if changed or missing else 'ok', 'commit': commit,
           'changed': changed, 'missing': missing}
    if changed or missing:
        out['fix'] = 'ai-release activate <commit> to build a clean release from a committed tree'
    return out


def close(tree):
    """No one but the owner writes in a release: git archive's default modes (tar.umask
    002) unpacked by root keep group write, and root's checks then refuse the release."""
    for path in [tree, *Path(tree).rglob('*')]:
        if not path.is_symlink():
            mode = path.stat().st_mode & 0o7777
            if mode & 0o022:
                path.chmod(mode & ~0o022)


def build(checkout, commit, releases):
    """Archive the commit into releases/<commit>, atomically. Returns the release folder."""
    target = releases / commit
    if target.exists():
        close(target)  # one built before close() existed
        return target
    releases.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f'.{commit[:12]}-', dir=releases))
    archive = subprocess.Popen(['git', '-c', f'safe.directory={Path(checkout).resolve()}', '-c', 'tar.umask=022',
                                '-C', str(checkout), 'archive', '--format=tar', commit],
                               stdout=subprocess.PIPE)
    unpack = subprocess.run(['tar', '-x', '-f', '-', '-C', str(staging)], stdin=archive.stdout)
    archive.stdout.close()
    if archive.wait() != 0 or unpack.returncode != 0:
        raise RuntimeError(f'could not archive {commit}; the partial build is at {staging}')
    staging.chmod(0o755)
    close(staging)
    staging.rename(target)
    return target


def activate(ref, checkout=CHECKOUT, share=SHARE):
    run = git(checkout, 'rev-parse', '--verify', f'{ref}^{{commit}}')
    if run.returncode != 0:
        raise ValueError(f'{ref} is not a commit in {checkout}')
    commit = run.stdout.decode().strip()
    release = build(checkout, commit, share / 'releases')
    report = verify(release, checkout)
    if report['state'] != 'ok':
        raise ValueError(f'{release} does not match {commit}; move it aside before activating: '
                         + ', '.join((report['changed'] + report['missing'])[:10]))
    current = share / 'current'
    link = share / f'.current-{os.getpid()}'
    link.symlink_to(Path('releases') / commit)
    os.replace(link, current)
    return {'state': 'ok', 'commit': commit, 'release': str(release)}


def main(argv=None):
    p = argparse.ArgumentParser(prog='ai-release', description=__doc__.splitlines()[0])
    p.add_argument('--checkout', default=str(CHECKOUT))
    p.add_argument('--share', default=str(SHARE))
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('verify', help='check the activated release against its commit')
    a = sub.add_parser('activate', help='build a commit into a release and activate it')
    a.add_argument('ref', help='a commit, branch or tag in the checkout')
    args = p.parse_args(argv)
    checkout, share = Path(args.checkout).expanduser(), Path(args.share).expanduser()
    try:
        report = (verify(share / 'current', checkout) if args.cmd == 'verify'
                  else activate(args.ref, checkout, share))
    except (ValueError, RuntimeError, OSError) as err:
        print(f'ai-release: {err}', file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report['state'] == 'ok' else 1
