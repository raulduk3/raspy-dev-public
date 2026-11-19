"""A rig the owner starts himself may run paid seats for a while (dev-server decision
2026-10-05). The launcher (agent-run, "rig approval") refuses a seat's paid session unless
the owner approved its rig: `sudo ol-rig-approve RIG`, at his terminal, with his password.
`rig up` and `dev-workspace start` ask for it; a daemon restoring a rig on its own cannot."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HELPER = '/usr/local/bin/ol-rig-approve'
NAME = re.compile(r'[A-Za-z0-9_.-]{1,64}')
NO_APPROVAL = {'--plan', '--dry-run', '--help', '-h'}


def rig_name(argv: list[str]) -> str | None:
    """The rig `rig up ARGS` starts: its name, or the `name:` its spec file declares."""
    words = [a for a in argv if not a.startswith('-')]
    if not words:
        return None
    target = words[0]
    path = Path(target)
    if path.suffix in ('.yaml', '.yml') and path.is_file():
        declared = re.search(r"^name:\s*['\"]?([^'\"\s]+)", path.read_text(errors='replace'), re.MULTILINE)
        target = declared.group(1) if declared else ''
    return target if NAME.fullmatch(target) else None


def needs_approval(argv: list[str]) -> bool:
    """`rig up` that starts seats (not a plan or help)."""
    return bool(argv) and argv[0] == 'up' and not NO_APPROVAL.intersection(argv[1:])


def approve(rig: str | None, run=subprocess.run, tty=None) -> bool:
    """Ask for the owner's approval at his terminal. False (and why) when there is none to ask."""
    at_terminal = tty if tty is not None else (sys.stdin.isatty() and sys.stdout.isatty())
    if not rig:
        print('rig: no rig name to approve; its seats will not start paid sessions', file=sys.stderr)
        return False
    if not at_terminal:
        print(f'rig: {rig} was not started at your terminal; its seats will not start paid sessions',
              file=sys.stderr)
        return False
    return run(['sudo', HELPER, rig]).returncode == 0
