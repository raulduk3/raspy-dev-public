"""Exercise actual native TUI in a PTY via the OS-lock launch boundary."""
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import sys
import tempfile
import termios
import time
import fcntl

platform = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(platform / 'lib'))
from ai_ecosystem.pi_launch import exec_conversation

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory).resolve()
    pid, fd = pty.fork()
    if pid == 0:
        env = {key: os.environ[key] for key in ('PATH', 'LANG', 'SHELL') if key in os.environ}
        env.update(HOME=str(root), TERM='xterm-256color', PI_OFFLINE='1',
                   PI_CODING_AGENT_DIR=str(root / 'auth'))
        exec_conversation(root, [str(Path(shutil.which('node')).resolve()),
            str(platform / 'integrations/pi/check-role-terminal.mjs'), str(root)], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 110, 0, 0))
    output = b''
    sent = False
    status = None
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            if select.select([fd], [], [], .2)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    chunk = b''
                output += chunk
                # Native resource startup display proves the actual role tool loaded.
                if not sent and all(marker in output for marker in
                                    (b'integrations/pi/perplexity', b'skills/develop/', b'~/workspace')):
                    os.write(fd, b'\x04')  # native Ctrl+D on an empty editor
                    sent = True
            done, status = os.waitpid(pid, os.WNOHANG)
            if done:
                break
        else:
            os.kill(pid, signal.SIGKILL)
            _, status = os.waitpid(pid, 0)
        if not sent or os.waitstatus_to_exitcode(status) != 0:
            print(output.decode(errors='replace')[-6000:])
            raise SystemExit('Native terminal startup/exit check failed')
        with open(root / '.pi-writer.lock', 'r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps({'passed': True, 'checks': ['native Pi TUI rendered role resources',
            'native Ctrl+D exit', 'conversation lock released'],
            'scope': 'Offline temporary PTY; no model request or live account'}, indent=2))
    finally:
        os.close(fd)
