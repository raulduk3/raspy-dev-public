"""Read a secret the launcher handed to this process. The one place the platform reads one.

On the Mac these lived in the login Keychain. On dev-server a secret is a root-owned 0600 file
(kept in /etc/dev-server/accounts as ID.key, written only by ol-login) and reaches a process the
way Claude tokens do: the launcher passes it as a systemd credential, so it appears read-only
at $CREDENTIALS_DIRECTORY/<name> for that process alone. Nothing here writes, copies or prints
one; a missing secret is None, and the caller says which name is missing.

Names in use: harvest-api (JSON: account_id, token), dev-platform-jev, dev-platform-perplexity.
"""
import os
import re
from pathlib import Path

NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,63}')


HELPER = '/usr/local/bin/ol-login-root'
# Tests (and anyone who wants the launcher's copy only) turn the owner's read off.
OFF = 'OL_SECRET_LAUNCH_ONLY'


def _owner_read(name):
    """Outside a launch, the owner's own tools (ai-jev) ask root's helper through a
    pipe, password-free, for keys marked owner_read; each use is noted in the journal. Only a
    member of wheel (the owner) asks: an agent never touches sudo."""
    import grp
    import subprocess
    try:
        if os.environ.get(OFF) or grp.getgrnam('wheel').gr_gid not in os.getgroups() or not os.access(HELPER, os.X_OK):
            return None
        out = subprocess.run(['sudo', '-n', HELPER, 'secret', name], capture_output=True, text=True,
                             timeout=20, stdin=subprocess.DEVNULL)
    except (KeyError, OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def read(name):
    if not NAME.fullmatch(name):
        raise ValueError(f'not a secret name: {name!r}')
    folder = os.environ.get('CREDENTIALS_DIRECTORY')
    if folder:
        try:
            value = (Path(folder) / name).read_text().strip()
        except OSError:
            value = ''
        if value:
            return value
    return _owner_read(name)


def available(name):
    return read(name) is not None


HOW = ('the owner stores it once through ol-login (a hidden prompt on dev-server, kept by root); '
       'the launcher hands it to the process that needs it')
