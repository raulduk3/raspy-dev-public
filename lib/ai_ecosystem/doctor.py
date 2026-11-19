"""ai-env doctor: read-only environment diagnostics. Never installs, restarts or edits config.

Each check reports one state: ok, missing, stale, unavailable, unverified, unsupported or broken.
Output carries names and states only, never credentials or full configuration.
"""
import argparse
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import sys

from . import paths, secret
from .release import verify as verify_release

COMMANDS = ('claude', 'codex', 'code', 'gh', 'git', 'jq', 'python3', 'laya-decide', 'ai-jev')
SKILL_DIRS = ('.claude/skills', '.codex/skills', '.agents/skills')
OPENRIG_VERSION = '0.6.10'
OPENRIG_NODE = '24.14.0'
LAYA_LABEL = 'dev.raspy.laya'
LAYA_PROBE = {
    'state': 'Read-only diagnostic: choose which small local documentation task to inspect first.',
    'options': {'read_summary': 'Read a short summary.', 'read_details': 'Read the detailed notes.'},
}


def check_commands():
    return {c: {'state': 'ok' if shutil.which(c) else 'missing'} for c in COMMANDS}


def stale_release(skill, platform, checkout=None):
    """True when a skill resolves into a release other than the platform's own, or into the
    development checkout while a release is active: either one stops following activation."""
    source = skill.resolve().parent.parent
    if source == platform:
        return False
    return source.parent.name == 'releases' or (checkout is not None and source == checkout)


def check_skills(home, platform):
    platform_skills = (platform / 'skills').resolve()
    checkout = paths.checkout().resolve()
    expected = {p.parent.name for p in platform_skills.glob('*/SKILL.md') if p.is_file()}
    # The repository declares required names; shared discovery declares the active
    # source. Workshop-published overrides need not live in the repository.
    canonical = home / '.agents/skills'
    canonical_missing = sorted(name for name in expected
                               if not (canonical / name / 'SKILL.md').is_file())
    out = {}
    for rel in SKILL_DIRS:
        folder = home / rel
        if not folder.is_dir():
            out[rel] = {'state': 'missing'}
            continue
        broken, divergent = [], []
        for entry in sorted(folder.iterdir()):
            if not entry.is_symlink():
                continue
            if not entry.exists():
                broken.append(entry.name)
        if folder != canonical:
            for name in sorted(expected):
                source = canonical / name / 'SKILL.md'
                client = folder / name / 'SKILL.md'
                if source.is_file() and client.is_file() and source.resolve() != client.resolve():
                    divergent.append(name)
        missing = sorted(name for name in expected if not (folder / name / 'SKILL.md').is_file())
        # A link into another release keeps an agent on skills the activated release replaced.
        # A Workshop override lives outside releases/ and stays healthy.
        stale = sorted(name for name in expected if (folder / name / 'SKILL.md').is_file()
                       and stale_release(folder / name, platform_skills.parent, checkout))
        out[rel] = {'state': 'broken' if broken or divergent else
                           'missing' if missing or canonical_missing else 'stale' if stale else 'ok',
                    'broken': broken, 'divergent': divergent, 'missing': missing, 'stale': stale,
                    'canonical_missing': canonical_missing}
        if stale:
            out[rel]['fix'] = f'link each to {platform}/skills/<name> so it follows the activated release'
    return out


def check_platform(platform):
    check = platform / 'bin/check'
    return {'state': 'ok' if check.is_file() and os.access(check, os.X_OK) else 'missing'}


def check_jev(home):
    config = home / '.config/dev-platform/jev.json'
    usage = home / '.local/state/dev-platform/jev/usage.json'
    out = {'config': {'state': 'missing'}, 'credential': {'state': 'missing'},
           'usage': {'state': 'missing'}}
    if config.exists():
        try:
            data = json.loads(config.read_text())
            limit = data.get('monthly_limit_micros')
            price = data.get('prompt_price_micros_per_million_tokens')
            enabled = data.get('enabled', True) is True
            safe_limit = isinstance(limit, int) and 0 <= limit <= 10_000_000
            safe_price = isinstance(price, int) and price >= 0
            out['config'] = {'state': 'ok' if enabled and safe_limit and safe_price else 'broken',
                             'enabled': enabled, 'monthly_limit_micros': limit,
                             'limit_usd': None if not isinstance(limit, int) else limit / 1_000_000,
                             'cap_policy': 'ok' if safe_limit else 'over_10_usd_or_invalid'}
            credential = data.get('credential', {}) if isinstance(data.get('credential'), dict) else {}
            # Availability only: whether the launcher handed this process the key. The value
            # is never read into the report. Skipped for synthetic test homes.
            available = bool(os.environ.get('JEV_API_KEY')) or (
                home == Path.home() and secret.available(credential.get('name', 'dev-platform-jev')))
            out['credential'] = {'state': 'ok' if available else 'missing',
                                 'source': credential.get('source', 'secret'),
                                 'available': available}
        except (OSError, ValueError, TypeError):
            out['config'] = {'state': 'broken'}
    if usage.exists():
        try:
            data = json.loads(usage.read_text())
            spent = data.get('spent_micros')
            limit = data.get('monthly_limit_micros')
            enabled = data.get('enabled', True) is True
            under_limit = isinstance(spent, int) and isinstance(limit, int) and spent < limit
            out['usage'] = {'state': 'ok' if enabled and under_limit else 'unavailable',
                            'enabled': enabled, 'month': data.get('month'),
                            'spent_micros': spent, 'monthly_limit_micros': limit,
                            'disabled_reason': data.get('disabled_reason')}
        except (OSError, ValueError, TypeError):
            out['usage'] = {'state': 'broken'}
    elif out['config'].get('state') == 'ok':
        out['usage'] = {'state': 'ok', 'enabled': True, 'spent_micros': 0,
                        'monthly_limit_micros': out['config'].get('monthly_limit_micros'),
                        'note': 'no paid calls recorded'}
    return out


def check_laya_config(home):
    folder = home / 'Library/LaunchAgents'
    paths = sorted(folder.glob('*laya*.plist'))
    primary = folder / f'{LAYA_LABEL}.plist'
    out = {'state': 'missing' if not primary.exists() else 'broken', 'count': len(paths)}
    if not primary.exists():
        return out
    try:
        with primary.open('rb') as handle:
            config = plistlib.load(handle)
        env = config.get('EnvironmentVariables', {})
        args = config.get('ProgramArguments', [])
        # The installed laya-serve entrypoint takes these settings from its environment.
        # Never report environment values or arbitrary launch arguments.
        checks = {
            'label_matches': config.get('Label') == LAYA_LABEL,
            'entrypoint_matches': len(args) == 1 and Path(args[0]).name == 'laya-serve',
            'loopback_host': env.get('LAYA_HOST') == '127.0.0.1',
            'port_matches': str(env.get('LAYA_PORT')) == '18791',
            'preload_enabled': env.get('LAYA_PRELOAD') == '1',
            'singleton_config': len(paths) == 1,
        }
        out.update(checks, state='ok' if all(checks.values()) else 'broken')
    except (OSError, ValueError, TypeError, AttributeError, plistlib.InvalidFileException):
        out['reason'] = 'launch configuration unreadable or unsupported'
    return out


def check_laya(home, probe):
    out = {'launch_config': check_laya_config(home)}
    lsof = shutil.which('lsof')
    if not lsof:
        out['listener'] = {'state': 'unverified', 'reason': 'lsof unavailable'}
    else:
        try:
            run = subprocess.run([lsof, '-nP', '-iTCP:18791', '-sTCP:LISTEN'],
                                 capture_output=True, text=True, timeout=10)
            rows = [line.split() for line in run.stdout.splitlines()[1:] if line.strip()]
            valid = all(len(row) > 8 and row[1].isdigit() for row in rows)
            pids = {row[1] for row in rows if len(row) > 8}
            addrs = {row[8] for row in rows if len(row) > 8}
            loopback = bool(addrs) and all(a in ('127.0.0.1:18791', '[::1]:18791') for a in addrs)
            if run.returncode not in (0, 1) or not valid or (run.returncode == 1 and rows):
                out['listener'] = {'state': 'unverified', 'reason': 'listener inspection failed'}
            else:
                out['listener'] = {'state': 'unavailable' if not rows else
                                   'ok' if len(pids) == 1 and loopback else 'broken',
                                   'count': len(pids), 'loopback_only': loopback}
        except (OSError, subprocess.TimeoutExpired):
            out['listener'] = {'state': 'unverified', 'reason': 'listener inspection unavailable'}
    if not probe:
        out['probe'] = {'state': 'unverified', 'reason': 'pass --probe-laya to invoke the helper'}
        return out
    helper = shutil.which('laya-decide')
    if not helper:
        out['probe'] = {'state': 'missing'}
        return out
    try:
        run = subprocess.run([helper], input=json.dumps(LAYA_PROBE), capture_output=True,
                             text=True, timeout=20)
        result = json.loads(run.stdout)
        shadow = (isinstance(result, dict) and result.get('mode') == 'shadow' and
                  result.get('automatically_applied', False) is False)
        if shadow and result.get('status') == 'unavailable' and result.get('recommendation') is None:
            out['probe'] = {'state': 'unavailable', 'reason': 'helper reported no valid inference'}
        elif (shadow and run.returncode == 0 and result.get('status') == 'recommended' and
              result.get('automatically_applied') is False and
              result.get('recommendation') in LAYA_PROBE['options'] and
              isinstance(result.get('route'), str) and bool(result['route']) and
              isinstance(result.get('checkpoint'), str) and bool(result['checkpoint'])):
            out['probe'] = {'state': 'ok', 'mode': 'shadow', 'inference': 'verified',
                            'recommendation_quality': 'unverified'}
        else:
            out['probe'] = {'state': 'broken', 'reason': 'invalid shadow inference response'}
    except subprocess.TimeoutExpired:
        out['probe'] = {'state': 'unavailable', 'reason': 'timeout'}
    except OSError:
        out['probe'] = {'state': 'unavailable', 'reason': 'helper unavailable'}
    except (ValueError, TypeError):
        out['probe'] = {'state': 'broken', 'reason': 'invalid shadow inference response'}
    return out


PROVIDER_OVERRIDE_PREFIXES = ('ANTHROPIC_', 'OPENCLAW_', 'CLAUDE_CODE_USE_')


def tmux_provider_overrides(listing):
    """Variable names in a `tmux show-environment -g` listing that would override a seat's provider."""
    return [line.split('=', 1)[0] for line in listing.splitlines()
            if '=' in line and not line.startswith('-') and line.split('=', 1)[0].startswith(PROVIDER_OVERRIDE_PREFIXES)]


def check_tmux_environment():
    """Every OpenRig seat inherits the tmux server's global environment. Provider overrides
    there (a stale proxy URL, another agent's service variables) reach every new seat."""
    tmux = shutil.which('tmux')
    if not tmux:
        return {'state': 'missing'}
    listing = subprocess.run([tmux, 'show-environment', '-g'], text=True, capture_output=True)
    if listing.returncode != 0:
        return {'state': 'unavailable', 'note': 'no tmux server running'}
    overrides = tmux_provider_overrides(listing.stdout)
    return {'state': 'broken' if overrides else 'ok', 'overrides': overrides,
            'fix': 'dev-workspace start removes these before launching; or: tmux set-environment -g -u <NAME>'}


def nested(data, path):
    for part in path:
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def run_json(argv, timeout=10):
    try:
        run = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        if run.returncode != 0:
            return None
        return json.loads(run.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        return None


def check_openrig(home):
    """Read-only checks that protect the shared OpenRig install, workspace projection,
    account-session visibility and panel layout assumptions the ai menu depends on."""
    rig = shutil.which('rig')
    runtime = paths.openrig_runtime()
    workspace = home / '.local/state/dev-platform/workspace'
    out = {
        'command': {'state': 'missing' if rig is None else 'unverified'},
        'runtime': {'state': 'missing' if not runtime.exists() else 'unverified'},
        'config': {'state': 'unverified'},
        'workspace': {'state': 'missing'},
    }
    if rig:
        try:
            version = subprocess.run([rig, '--version'], capture_output=True, text=True, timeout=10).stdout.strip()
            out['command'] = {'state': 'ok' if OPENRIG_VERSION in version else 'unsupported',
                              'version': version, 'expected': OPENRIG_VERSION}
        except (OSError, subprocess.TimeoutExpired):
            out['command'] = {'state': 'unavailable'}
        config = run_json([rig, 'config', '--json'])
        if config is None:
            out['config'] = {'state': 'unavailable'}
        else:
            expected = {
                ('daemon', 'host'): '127.0.0.1',
                ('workspace', 'root'): str(workspace),
                ('workspace', 'catalogPath'): str(workspace / 'workspace.yaml'),
                ('workspace', 'projectsRoot'): str(workspace / 'projects'),
                ('workspace', 'slicesRoot'): str(workspace / 'missions'),
                ('recovery', 'autoDriveProviderPrompts'): False,
                ('policies', 'claudeCompaction', 'enabled'): False,
                ('policies', 'idleGateQitem', 'autoRegister'): 'off',
                ('snapshots', 'periodic', 'enabled'): False,
                ('retention', 'enabled'): False,
                ('ui', 'timezone'): 'Etc/UTC',
            }
            wrong = ['.'.join(path) for path, value in expected.items() if nested(config, path) != value]
            allowlist = nested(config, ('files', 'allowlist'))
            scan_roots = nested(config, ('progress', 'scanRoots'))
            for label, value in (('files.allowlist', allowlist), ('progress.scanRoots', scan_roots)):
                if value != f'workspace:{workspace}':
                    wrong.append(label)
            out['config'] = {'state': 'broken' if wrong else 'ok', 'wrong': sorted(wrong),
                             'workspace_root': nested(config, ('workspace', 'root'))}
    node = runtime / f'node-v{OPENRIG_NODE}-{paths.node_platform()}/bin/node'
    cli = runtime / 'app/node_modules/.bin/rig'
    out['runtime'] = {'state': 'ok' if node.is_file() and cli.is_file() else 'missing',
                      'node': OPENRIG_NODE, 'cli': 'present' if cli.is_file() else 'missing'}
    out['workspace'] = {'state': 'ok' if (workspace / 'workspace.yaml').is_file()
                        and (workspace / 'projects').is_dir() else 'missing',
                        'root': str(workspace)}
    return out


def check_herdr(home):
    herdr = shutil.which('herdr')
    config = home / '.config/herdr/config.toml'
    socket = home / '.config/herdr/herdr.sock'
    out = {'command': {'state': 'missing' if herdr is None else 'unverified'},
           'server': {'state': 'unverified'},
           'config': {'state': 'ok' if config.is_file() else 'missing'},
           'socket': {'state': 'ok' if socket.exists() else 'missing'}}
    if not herdr:
        return out
    try:
        version = subprocess.run([herdr, '--version'], capture_output=True, text=True, timeout=10).stdout.strip()
        out['command'] = {'state': 'ok' if version else 'unverified', 'version': version}
        status = subprocess.run([herdr, 'status'], capture_output=True, text=True, timeout=10).stdout
        running = 'status: running' in status and 'endpoint_compatible: yes' in status
        restart = 'restart_needed: no' in status and 'server_binary_stale: no' in status
        out['server'] = {'state': 'ok' if running and restart else 'broken',
                         'running': running, 'restart_needed': not restart}
    except (OSError, subprocess.TimeoutExpired):
        out['command'] = {'state': 'unavailable'}
        out['server'] = {'state': 'unavailable'}
    return out


def check_instruction_surfaces(platform):
    required_files = {
        'claude hook settings': platform / 'hooks/claude-settings.hooks.json',
        'codex rules': platform / 'hooks/codex.rules',
        'guard hook': platform / 'hooks/pre-tool-use-guard.sh',
        'session length hook': platform / 'hooks/session-length.sh',
        'role rules': platform / 'agents/rules.md',
        'project template instructions': platform / 'templates/AGENTS.md',
        'vscode instructions': platform / 'vscode/dev-platform.instructions.md',
        'openrig control guidance': platform / 'integrations/openrig/agents/control/guidance/role.md',
        'openrig worker guidance': platform / 'integrations/openrig/agents/worker/guidance/role.md',
        'openrig overseer guidance': platform / 'integrations/openrig/agents/overseer/guidance/role.md',
    }
    missing = sorted(name for name, path in required_files.items() if not path.is_file())
    not_executable = sorted(name for name, path in required_files.items()
                            if name.endswith('hook') and path.is_file() and not os.access(path, os.X_OK))
    return {'state': 'broken' if missing or not_executable else 'ok',
            'missing': missing, 'not_executable': not_executable}


def doctor(home, platform, probe=False):
    return {'commands': check_commands(), 'skills': check_skills(home, platform),
            'platform_check': check_platform(platform),
            'release': {'integrity': verify_release(platform, paths.checkout())},
            'surfaces': {'instructions': check_instruction_surfaces(platform)},
            'openrig': check_openrig(home), 'herdr': check_herdr(home),
            'jev': check_jev(home),
            'laya': check_laya(home, probe), 'tmux': {'server_environment': check_tmux_environment()}}


def main(argv=None):
    p = argparse.ArgumentParser(prog='ai-env')
    sub = p.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('doctor')
    d.add_argument('--json', action='store_true')
    d.add_argument('--probe-laya', action='store_true')
    d.add_argument('--home')
    d.add_argument('--platform-root', help='platform to compare against (default: the activated release, '
                                           'else the checkout; see paths.py)')
    a = p.parse_args(argv)
    home = Path(a.home or Path.home())
    # Skills are expected to match what is installed, not whichever branch the development
    # checkout happens to be on; the checkout is only the fallback before a first release.
    installed = paths.install()
    platform = (Path(a.platform_root).expanduser() if a.platform_root
                else installed if (installed / 'skills').is_dir() else paths.checkout())
    report = doctor(home, platform, a.probe_laya)
    if a.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for section, items in report.items():
            for name, value in items.items():
                state = value.get('state') if isinstance(value, dict) else value
                print(f'{section}\t{name}\t{state}')
    return 0
