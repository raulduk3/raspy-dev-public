#!/usr/bin/env python3
"""Verify one conversation lock across disposable containers on a real bind mount."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid


LAUNCH = '''import os, sys
from pathlib import Path
from pi_launch import exec_conversation
body = 'import time; print("HELD", flush=True); time.sleep(60)' if sys.argv[1] == 'hold' else 'print("ACQUIRED")'
try:
    exec_conversation(Path('/conversation'), [sys.executable, '-c', body], dict(os.environ))
except ValueError as error:
    if str(error) == 'conversation already has an active Pi writer':
        print('BUSY')
        sys.exit(23)
    raise
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[3]
    revision = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip()
    image = json.loads(subprocess.check_output(['docker', 'image', 'inspect', args.image]))[0]['Id']
    holder = 'pi-lock-check-' + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='pi-mount-check-') as directory:
        root = Path(directory)
        source, conversation = root / 'source', root / 'conversation'
        source.mkdir(); conversation.mkdir(mode=0o700)
        (source / 'pi_launch.py').write_bytes(subprocess.check_output(
            ['git', '-C', str(repository), 'show', revision + ':lib/ai_ecosystem/pi_launch.py']))
        (source / 'launch.py').write_text(LAUNCH)
        history = conversation / 'preserved-history.txt'
        history.write_text('Existing conversation data must survive container replacement.\n')
        digest = hashlib.sha256(history.read_bytes()).hexdigest()
        base = ['docker', 'run', '--rm', '--network', 'none', '--read-only',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                '--user', f'{os.getuid()}:{os.getgid()}',
                '--env', 'PYTHONDONTWRITEBYTECODE=1', '--entrypoint', 'python3',
                '--mount', f'type=bind,source={source},target=/checks,readonly',
                '--mount', f'type=bind,source={conversation},target=/conversation']
        try:
            subprocess.run([*base, '--name', holder, '-d', image, '/checks/launch.py', 'hold'],
                           check=True, capture_output=True, timeout=30)
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                logs = subprocess.check_output(['docker', 'logs', holder], text=True, timeout=5)
                if 'HELD' in logs:
                    break
                state = subprocess.check_output(['docker', 'inspect', '--format', '{{.State.Running}}', holder], text=True, timeout=5)
                if state.strip() != 'true':
                    raise RuntimeError('Lock holder exited before acquiring the conversation')
                time.sleep(.2)
            else:
                raise RuntimeError('Timed out waiting for the lock holder')
            lock = conversation / '.pi-writer.lock'
            identity = (lock.stat().st_dev, lock.stat().st_ino)
            contender = subprocess.run([*base, image, '/checks/launch.py', 'probe'],
                                       capture_output=True, text=True, timeout=30)
            if contender.returncode != 23 or contender.stdout.strip() != 'BUSY':
                raise RuntimeError('Second container was not refused: ' + contender.stdout + contender.stderr)
            subprocess.run(['docker', 'kill', '--signal', 'KILL', holder], check=True, capture_output=True, timeout=10)
            # A new container uses the same mount after abrupt termination. No
            # lock-file deletion, stale PID repair, or credential operation.
            recovered = subprocess.run([*base, image, '/checks/launch.py', 'probe'],
                                       capture_output=True, text=True, check=True, timeout=30)
            if recovered.stdout.strip() != 'ACQUIRED':
                raise RuntimeError('Replacement container did not acquire the lock')
            if identity != (lock.stat().st_dev, lock.stat().st_ino):
                raise RuntimeError('Lock file was replaced')
            if hashlib.sha256(history.read_bytes()).hexdigest() != digest:
                raise RuntimeError('Existing conversation data changed')
        finally:
            subprocess.run(['docker', 'rm', '-f', holder], capture_output=True, timeout=15)
    print(json.dumps({'passed': True, 'revision': revision, 'image': image,
                      'checks': ['second container refused', 'SIGKILL releases ownership',
                                 'replacement acquires same lock inode', 'existing data unchanged'],
                      'scope': 'Real Docker bind mount and launch lock; temporary data, no native Pi authentication or model request'}))


if __name__ == '__main__':
    main()
