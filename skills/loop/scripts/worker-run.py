#!/usr/bin/env python3
"""Bound one worker's wall time and process group; no scheduling or account fallback."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time


def process_identity(pid):
    """Read identity, never expose worker arguments (which may contain private prompts)."""
    start = subprocess.check_output(['ps', '-p', str(pid), '-o', 'lstart='], text=True, stderr=subprocess.DEVNULL).strip()
    command = subprocess.check_output(['ps', '-ww', '-p', str(pid), '-o', 'command='], text=True, stderr=subprocess.DEVNULL).strip()
    proc = Path(f'/proc/{pid}/cwd')
    if proc.exists():
        cwd = str(proc.resolve(strict=True))
    else:
        output = subprocess.check_output(['lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'],
                                         text=True, stderr=subprocess.DEVNULL, timeout=3)
        cwd = next(line[1:] for line in output.splitlines() if line.startswith('n'))
    if not start or not command:
        raise ValueError('process identity unavailable')
    return {'pid': pid, 'started': start, 'cwd': str(Path(cwd).resolve()),
            'command_sha256': hashlib.sha256(command.encode()).hexdigest()}, command


def common_dir(cwd):
    value = subprocess.check_output(['git', '-C', cwd, 'rev-parse',
                                    '--path-format=absolute', '--git-common-dir'],
                                   text=True, stderr=subprocess.DEVNULL).strip()
    return str(Path(value).resolve(strict=True))


def running_workers(ctl, repository):
    """Only this repository's live supervisors; legacy PID existence is not evidence."""
    owner = common_dir(repository)
    seen = set()
    root = Path(ctl)
    # Global pre-ledger entries have no repository ownership and cannot identify this loop.
    for pf in sorted(root.glob('*/workers/*.pid')) + sorted(root.glob('worker-*.pid')):
        issue = pf.stem.removeprefix('worker-')
        result = pf.with_suffix('.exit')
        if not issue.isdigit() or result.exists():
            continue
        try:
            pid = int(pf.read_text().strip())
            if pid <= 0 or pid in seen:
                continue
            identity, command = process_identity(pid)
            # Match the real supervisor invocation, not a worker prompt mentioning its name.
            pattern = r'^\S+ (.+/worker-run\.py) [1-9][0-9]* ' + re.escape(str(result)) + r' -- '
            if not re.match(pattern, command) or common_dir(identity['cwd']) != owner:
                continue
            receipt = pf.with_suffix('.identity.json')
            if receipt.exists():
                try:
                    matches = json.loads(receipt.read_text()) == identity
                except (OSError, ValueError):
                    matches = False
                if not matches:
                    raise SystemExit('loop: live supervisor identity changed; inspect its receipt before dispatch')
            # A live pre-receipt supervisor still occupies capacity after an upgrade.
            seen.add(pid)
            print(f'{pid} {issue}')
        except (OSError, ValueError, StopIteration, subprocess.SubprocessError):
            continue


def main():
    seconds, result, sep, *command = sys.argv[1:]
    if sep != '--' or not command or int(seconds) <= 0:
        raise SystemExit('worker-run: invalid arguments')
    target = Path(result)
    identity, _ = process_identity(os.getpid())
    receipt = target.with_suffix('.identity.json')
    temporary = receipt.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(identity) + '\n')
    temporary.replace(receipt)
    names = ['HOME', 'PATH', 'USER', 'LANG', 'CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS']
    names.extend(os.environ.get('DEV_PLATFORM_ENV_PASS', '').split())
    env = {k: os.environ[k] for k in names if k in os.environ}
    env['TERM'] = 'dumb'
    process = None
    started = time.monotonic()
    code = 1
    reason = 'failed_to_start'
    def interrupted(signum, frame):
        raise InterruptedError(signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        process = subprocess.Popen(command, env=env, start_new_session=True)
        try:
            code = process.wait(timeout=int(seconds))
            reason = 'exited'
        except (subprocess.TimeoutExpired, InterruptedError) as error:
            code = 124 if isinstance(error, subprocess.TimeoutExpired) else 130
            reason = 'wall_time_limit' if code == 124 else 'interrupted'
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            # Kill remaining grandchildren even if the process-group leader already exited.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    finally:
        target = Path(result)
        tmp = target.with_suffix('.exit.tmp')
        tmp.write_text(json.dumps({'exit_code': code, 'reason': reason,
                                  'elapsed_seconds': round(time.monotonic() - started, 2)}) + '\n')
        tmp.replace(target)
    return code if code >= 0 else 128 - code


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--running':
        running_workers(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
