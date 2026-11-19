"""POSIX terminal-launch primitive: hold conversation ownership across exec.

Account selection and command construction belong to the caller. This module
does not authenticate, spawn a daemon, or decide which runtime to launch.
"""
import fcntl
import os
from pathlib import Path
import stat


def exec_conversation(conversation_home, argv, env):
    """Replace this process with argv while retaining an exclusive OS file lock.

    Call only in the dedicated launch process, not an embedded service process.
    The caller must close the inherited descriptor only when its writer exits.
    The lock file must never be deleted as a stale-state recovery procedure.
    """
    home = Path(conversation_home)
    if not home.is_absolute() or not home.is_dir():
        raise ValueError('conversation home must be an existing absolute directory')
    if any(part.is_symlink() for part in (home, *home.parents)):
        raise ValueError('conversation home cannot contain symlinks')
    if not argv or not Path(argv[0]).is_absolute():
        raise ValueError('runtime executable must be an explicit absolute path')
    fd = os.open(home / '.pi-writer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('conversation lock must be a regular file')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('conversation already has an active Pi writer') from None
        os.set_inheritable(fd, True)
        # exec preserves PID, terminal and exit behavior. No wrapper process or
        # stale PID record remains; the kernel releases ownership on termination.
        os.execve(argv[0], argv, {**env, 'DEV_PLATFORM_PI_LOCK_FD': str(fd)})
    finally:
        os.close(fd)  # reached only when validation or exec fails
