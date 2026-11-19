#!/usr/bin/env python3
"""Check running local environments without logging in or launching agents."""
import argparse
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

from prepare import ACCOUNTS


def request(port, path, token=None):
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def check(root, names):
    results = []
    networks = set()
    for name in names:
        port = 17433 + ACCOUNTS.index(name)
        container = 'engineer-account-environments-' + name + '-1'
        state = json.loads(subprocess.check_output(['docker', 'inspect', container]))[0]
        assert state['State']['Running'], name + ' is not running'
        assert state['HostConfig']['PortBindings']['7433/tcp'] == [
            {'HostIp': '127.0.0.1', 'HostPort': str(port)}]
        own_networks = set(state['NetworkSettings']['Networks'])
        assert len(own_networks) == 1 and not own_networks & networks
        networks.update(own_networks)
        mounts = {m['Destination']: m['Source'] for m in state['Mounts']}
        assert mounts['/home/node'] == str(root / name / 'home')
        assert mounts['/workspace'] == str(root / name / 'workspace')
        assert '/var/run/docker.sock' not in mounts
        token = (root / name / 'secrets/control-token').read_text().strip()
        other = ACCOUNTS[(ACCOUNTS.index(name) + 1) % len(ACCOUNTS)]
        wrong = (root / other / 'secrets/control-token').read_text().strip()
        status, health = request(port, '/healthz')
        assert status == 200
        # Deliberately nonexistent route tests middleware without sending a message.
        path = '/api/transport/environment-acceptance-probe'
        assert request(port, path)[0] == 401
        assert request(port, path, wrong)[0] == 401
        assert request(port, path, token)[0] == 404
        versions = {}
        for command, expected in [('node', 'v24.14.0'), ('rig', '0.5.14'),
                                  ('codex', 'codex-cli 0.144.6'), ('claude', '2.1.280'),
                                  ('pi', '0.87.1')]:
            value = subprocess.check_output(['docker', 'exec', container, command, '--version'], text=True).strip()
            assert value.startswith(expected), value
            versions[command] = value
        uid = subprocess.check_output(['docker', 'exec', container, 'id', '-u'], text=True).strip()
        assert uid != '0'
        results.append({'environment': name, 'uid': uid, 'versions': versions,
                        'host_id': health.get('selfHostId'), 'checks': 'passed',
                        'account_identity': 'not checked'})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('environments', nargs='+', choices=ACCOUNTS)
    args = parser.parse_args()
    print(json.dumps(check(args.root.resolve(), args.environments), indent=2))
