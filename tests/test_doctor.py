"""Doctor uses real CLI subprocesses with harmless executable/config fixtures."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/ai-env'
sys.path.insert(0, str(PLATFORM / 'lib'))
from ai_ecosystem import paths  # noqa: E402


class Doctor(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='ai-env-')
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        os.symlink(sys.executable, self.bin / 'python3')
        self.platform = self.home / 'Dev/dev-platform'
        (self.platform / 'skills/loop').mkdir(parents=True)
        (self.platform / 'skills/loop/SKILL.md').write_text('# Loop\n')
        (self.platform / 'bin').mkdir()
        check = self.platform / 'bin/check'
        check.write_text('#!/bin/sh\nexit 0\n')
        check.chmod(0o755)

    def binary(self, name, body):
        p = self.bin / name
        p.write_text(f'#!{sys.executable}\n' + body)
        p.chmod(0o755)

    def run_doctor(self, *args):
        run = subprocess.run([str(CLI), 'doctor', '--json', '--home', str(self.home), *args],
                             capture_output=True, text=True, timeout=30,
                             env={'PATH': str(self.bin), 'HOME': str(self.home),
                                  'DEV_PLATFORM_SHARE': str(self.home / '.local/share/dev-platform'),
                                  'DEV_PLATFORM_CHECKOUT': str(self.platform)})
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def launch(self, **env):
        path = self.home / 'Library/LaunchAgents/dev.raspy.laya.plist'
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {'Label': 'dev.raspy.laya', 'ProgramArguments': ['/local/venv/bin/laya-serve'],
                'EnvironmentVariables': {'LAYA_HOST': '127.0.0.1', 'LAYA_PORT': '18791',
                                         'LAYA_PRELOAD': '1', 'SECRET_ENV': 'DO NOT OUTPUT', **env}}
        path.write_bytes(plistlib.dumps(data))
        return path

    def listener(self, address='127.0.0.1:18791', second=False):
        table = ('COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\n'
                 f'Python 123 test 8u IPv4 0x0 0t0 TCP {address} (LISTEN)\n')
        if second:
            table += f'Python 456 test 8u IPv4 0x1 0t0 TCP {address} (LISTEN)\n'
        self.binary('lsof', "import sys\nassert sys.argv[1:] == ['-nP', '-iTCP:18791', '-sTCP:LISTEN']\n"
                           f'print({table!r})\n')

    def helper(self, result):
        self.binary('laya-decide', 'import json, sys\n'
                    'assert len(sys.argv) == 1\n'
                    'data = json.load(sys.stdin)\n'
                    "assert set(data) == {'state', 'options'} and len(data['options']) == 2\n"
                    f'print({json.dumps(result)!r})\n')

    def rig(self, config=None, version='0.6.10 (test)'):
        config = config or {
            'daemon': {'host': '127.0.0.1'},
            'workspace': {'root': str(self.home / '.local/state/dev-platform/workspace'),
                          'catalogPath': str(self.home / '.local/state/dev-platform/workspace/workspace.yaml'),
                          'projectsRoot': str(self.home / '.local/state/dev-platform/workspace/projects'),
                          'slicesRoot': str(self.home / '.local/state/dev-platform/workspace/missions')},
            'recovery': {'autoDriveProviderPrompts': False},
            'policies': {'claudeCompaction': {'enabled': False}, 'idleGateQitem': {'autoRegister': 'off'}},
            'snapshots': {'periodic': {'enabled': False}},
            'retention': {'enabled': False},
            'ui': {'timezone': 'Etc/UTC'},
            'files': {'allowlist': 'workspace:' + str(self.home / '.local/state/dev-platform/workspace')},
            'progress': {'scanRoots': 'workspace:' + str(self.home / '.local/state/dev-platform/workspace')},
        }
        self.binary('rig', 'import json, sys\n'
                   f'config = json.loads({json.dumps(json.dumps(config))})\n'
                   f'version = {version!r}\n'
                   "if sys.argv[1:] == ['--version']:\n    print(version); sys.exit(0)\n"
                   "if sys.argv[1:] == ['config', '--json']:\n    print(json.dumps(config)); sys.exit(0)\n"
                   "sys.exit(2)\n")

    def herdr(self, status='running'):
        body = "import sys\n"
        body += "if sys.argv[1:] == ['--version']:\n    print('0.9.1'); sys.exit(0)\n"
        if status == 'running':
            text = 'server:\n  status: running\n  endpoint_compatible: yes\nupdate:\n  restart_needed: no\n  server_binary_stale: no\n'
        else:
            text = 'server:\n  status: stopped\n  endpoint_compatible: no\nupdate:\n  restart_needed: yes\n  server_binary_stale: yes\n'
        body += "if sys.argv[1:] == ['status']:\n    print(" + repr(text) + "); sys.exit(0)\n"
        body += "sys.exit(2)\n"
        self.binary('herdr', body)

    def openrig_runtime(self):
        runtime = self.home / '.local/share/dev-platform/openrig-runtime'
        node = runtime / f'node-v24.14.0-{paths.node_platform()}/bin'
        node.mkdir(parents=True)
        (node / 'node').write_text('node')
        rig = runtime / 'app/node_modules/.bin/rig'
        rig.parent.mkdir(parents=True)
        rig.write_text('rig')
        dist = runtime / 'app/node_modules/@openrig/cli/daemon/dist/adapters'
        dist.mkdir(parents=True)
        workspace = self.home / '.local/state/dev-platform/workspace'
        (workspace / 'projects').mkdir(parents=True)
        (workspace / 'workspace.yaml').write_text('{}\n')

    def test_reports_missing_and_broken_without_mutation(self):
        skills = self.home / '.claude/skills'
        skills.mkdir(parents=True)
        os.symlink(self.home / 'nowhere', skills / 'gone')
        (self.home / 'elsewhere/loop').mkdir(parents=True)
        os.symlink(self.home / 'elsewhere/loop', skills / 'loop')
        before = sorted((str(p), os.readlink(p) if p.is_symlink() else None) for p in self.home.rglob('*'))
        report = self.run_doctor()
        self.assertEqual(report['commands']['claude']['state'], 'missing')
        self.assertEqual(report['commands']['laya-decide']['state'], 'missing')
        self.assertEqual(report['skills']['.claude/skills']['broken'], ['gone'])
        self.assertEqual(report['skills']['.claude/skills']['missing'], ['loop'])
        self.assertEqual(report['skills']['.claude/skills']['canonical_missing'], ['loop'])
        self.assertEqual(report['skills']['.codex/skills']['state'], 'missing')
        self.assertEqual(report['platform_check']['state'], 'ok')
        self.assertEqual(report['laya']['probe']['state'], 'unverified')
        self.assertEqual(report['laya']['listener']['state'], 'unverified')
        self.assertEqual(report['jev']['config']['state'], 'missing')
        after = sorted((str(p), os.readlink(p) if p.is_symlink() else None) for p in self.home.rglob('*'))
        self.assertEqual(before, after)

    def test_jev_diagnostic_reports_cap_credential_and_usage_without_secret(self):
        config = self.home / '.config/dev-platform/jev.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({
            'enabled': True,
            'monthly_limit_micros': 10_000_000,
            'prompt_price_micros_per_million_tokens': 42_000,
            'credential': {'source': 'keychain', 'service': 'dev-platform-jev', 'account': 'JEV_API_KEY'},
            'private': 'DO NOT OUTPUT',
        }))
        usage = self.home / '.local/state/dev-platform/jev/usage.json'
        usage.parent.mkdir(parents=True)
        usage.write_text(json.dumps({'version': 1, 'month': '2026-09', 'enabled': True,
                                     'monthly_limit_micros': 10_000_000,
                                     'spent_micros': 123, 'calls': 1}))
        report = self.run_doctor()
        self.assertEqual(report['jev']['config']['state'], 'ok')
        self.assertEqual(report['jev']['config']['limit_usd'], 10.0)
        self.assertEqual(report['jev']['credential']['state'], 'missing')
        self.assertEqual(report['jev']['usage']['state'], 'ok')
        self.assertNotIn('DO NOT OUTPUT', json.dumps(report))
        data = json.loads(config.read_text())
        data['monthly_limit_micros'] = 10_000_001
        config.write_text(json.dumps(data))
        self.assertEqual(self.run_doctor()['jev']['config']['state'], 'broken')

    def test_canonical_skill_links_do_not_depend_on_doctor_worktree(self):
        skills = self.home / '.claude/skills'
        skills.mkdir(parents=True)
        os.symlink(self.platform / 'skills/loop', skills / 'loop')
        shared = self.home / '.agents/skills'
        shared.mkdir(parents=True)
        os.symlink(self.platform / 'skills/loop', shared / 'loop')
        self.assertEqual(self.run_doctor()['skills']['.claude/skills']['state'], 'ok')
        alternate = self.home / 'alternate'
        self.platform.rename(alternate)
        (skills / 'loop').unlink()
        os.symlink(alternate / 'skills/loop', skills / 'loop')
        (shared / 'loop').unlink()
        os.symlink(alternate / 'skills/loop', shared / 'loop')
        self.assertEqual(self.run_doctor('--platform-root', str(alternate))['skills']['.claude/skills']['state'], 'ok')

    def test_skills_are_compared_with_the_activated_release_when_one_exists(self):
        release = self.home / '.local/share/dev-platform/releases/r1'
        (release / 'skills/new-only').mkdir(parents=True)
        (release / 'skills/new-only/SKILL.md').write_text('# New\n')
        (self.home / '.local/share/dev-platform/current').symlink_to(release)
        (self.home / '.agents/skills').mkdir(parents=True)
        missing = self.run_doctor()['skills']['.agents/skills']
        self.assertIn('new-only', missing.get('canonical_missing', []) + missing.get('missing', []))
        self.assertNotIn('loop', missing.get('canonical_missing', []))  # the checkout's list no longer applies

    def test_links_into_an_older_release_are_stale_until_they_follow_the_activated_one(self):
        releases = self.home / '.local/share/dev-platform/releases'
        for release in ('old', 'new'):
            (releases / release / 'skills/loop').mkdir(parents=True)
            (releases / release / 'skills/loop/SKILL.md').write_text(f'# {release} loop\n')
        current = self.home / '.local/share/dev-platform/current'
        current.symlink_to(releases / 'new')
        for rel in ('.agents/skills', '.claude/skills', '.codex/skills'):
            (self.home / rel).mkdir(parents=True)
            os.symlink(releases / 'old/skills/loop', self.home / rel / 'loop')
        report = self.run_doctor()['skills']
        for rel in ('.agents/skills', '.claude/skills', '.codex/skills'):
            self.assertEqual(report[rel]['state'], 'stale')
            self.assertEqual(report[rel]['stale'], ['loop'])
        checkout = self.platform / 'skills/loop'  # the development checkout, not a release
        for rel in ('.agents/skills', '.claude/skills', '.codex/skills'):
            (self.home / rel / 'loop').unlink()
            os.symlink(checkout, self.home / rel / 'loop')
        self.assertEqual(self.run_doctor()['skills']['.agents/skills']['stale'], ['loop'])
        for rel in ('.agents/skills', '.claude/skills', '.codex/skills'):
            (self.home / rel / 'loop').unlink()
            os.symlink(current / 'skills/loop', self.home / rel / 'loop')
        self.assertTrue(all(item['state'] == 'ok' for item in self.run_doctor()['skills'].values()))

    def test_shared_published_override_is_healthy_but_client_drift_is_not(self):
        published = self.home / 'workshop/loop'
        published.mkdir(parents=True)
        (published / 'SKILL.md').write_text('# Published loop\n')
        for rel in ('.agents/skills', '.claude/skills', '.codex/skills'):
            folder = self.home / rel
            folder.mkdir(parents=True)
            os.symlink(published, folder / 'loop')
        report = self.run_doctor()['skills']
        self.assertTrue(all(item['state'] == 'ok' for item in report.values()))

        # A valid but stale repository source must not pass merely because it exists.
        client = self.home / '.codex/skills/loop'
        client.unlink()
        os.symlink(self.platform / 'skills/loop', client)
        drift = self.run_doctor()['skills']
        self.assertEqual(drift['.codex/skills']['state'], 'broken')
        self.assertEqual(drift['.codex/skills']['divergent'], ['loop'])
        self.assertEqual(drift['.claude/skills']['state'], 'ok')

    def test_missing_or_broken_shared_source_never_makes_clients_healthy(self):
        shared = self.home / '.agents/skills'
        shared.mkdir(parents=True)
        for rel in ('.claude/skills', '.codex/skills'):
            folder = self.home / rel
            folder.mkdir(parents=True)
            os.symlink(self.platform / 'skills/loop', folder / 'loop')
        for broken in (False, True):
            with self.subTest(broken=broken):
                if broken:
                    os.symlink(self.home / 'absent/loop', shared / 'loop')
                report = self.run_doctor()['skills']
                self.assertEqual(report['.agents/skills']['state'], 'broken' if broken else 'missing')
                for rel in ('.claude/skills', '.codex/skills'):
                    self.assertEqual(report[rel]['state'], 'missing')
                    self.assertEqual(report[rel]['canonical_missing'], ['loop'])

    def test_missing_canonical_skills_report_drift_without_flagging_extra_skills(self):
        skills = self.home / '.agents/skills'
        (skills / 'bounded-decisions').mkdir(parents=True)
        (skills / 'bounded-decisions/SKILL.md').write_text('# Unmanaged extra skill\n')
        drift = self.run_doctor()['skills']['.agents/skills']
        self.assertEqual(drift['state'], 'missing')
        self.assertEqual(drift['missing'], ['loop'])
        self.assertEqual(drift['divergent'], [])
        os.symlink(self.platform / 'skills/loop', skills / 'loop')
        fixed = self.run_doctor()['skills']['.agents/skills']
        self.assertEqual(fixed['state'], 'ok')
        self.assertEqual(fixed['missing'], [])

    def test_python_listener_and_real_json_inference_contract(self):
        self.launch()
        self.listener()
        self.helper({'status': 'recommended', 'mode': 'shadow', 'automatically_applied': False,
                     'recommendation': 'read_summary', 'route': 'small', 'checkpoint': 'local'})
        default = self.run_doctor()['laya']
        self.assertEqual(default['probe']['state'], 'unverified')
        self.assertEqual(default['launch_config']['state'], 'ok')
        self.assertEqual(default['listener']['state'], 'ok')
        report = self.run_doctor('--probe-laya')
        self.assertEqual(report['laya']['probe']['inference'], 'verified')
        self.assertEqual(report['laya']['probe']['recommendation_quality'], 'unverified')
        self.assertNotIn('DO NOT OUTPUT', json.dumps(report))

    def test_unavailable_and_invalid_helper_responses_are_not_success(self):
        for result, expected in [
            ({'status': 'unavailable', 'mode': 'shadow', 'recommendation': None}, 'unavailable'),
            ({'status': 'recommended', 'mode': 'active', 'recommendation': 'read_summary'}, 'broken'),
            ({'status': 'recommended', 'mode': 'shadow', 'recommendation': 'invented'}, 'broken'),
            ('Usage: helper --help', 'broken'),
        ]:
            with self.subTest(result=result):
                self.helper(result)
                self.assertEqual(self.run_doctor('--probe-laya')['laya']['probe']['state'], expected)

    def test_launch_configuration_and_listener_semantics(self):
        for env in ({'LAYA_HOST': '0.0.0.0'}, {'LAYA_PORT': '1234'}, {'LAYA_PRELOAD': '0'}):
            self.launch(**env)
            self.assertEqual(self.run_doctor()['laya']['launch_config']['state'], 'broken')
        path = self.launch()
        path.with_name('other-laya.plist').write_bytes(path.read_bytes())
        self.assertEqual(self.run_doctor()['laya']['launch_config']['state'], 'broken')
        self.listener('0.0.0.0:18791')
        self.assertEqual(self.run_doctor()['laya']['listener']['state'], 'broken')
        self.listener(second=True)
        self.assertEqual(self.run_doctor()['laya']['listener']['state'], 'broken')
        self.binary('lsof', 'import sys\nsys.exit(1)\n')
        self.assertEqual(self.run_doctor()['laya']['listener']['state'], 'unavailable')

    def test_openrig_herdr_and_instruction_contracts_are_reported(self):
        self.openrig_runtime()
        self.rig()
        self.herdr()
        (self.home / '.config/herdr').mkdir(parents=True)
        (self.home / '.config/herdr/config.toml').write_text('')
        (self.home / '.config/herdr/herdr.sock').write_text('')
        for path in ('hooks/claude-settings.hooks.json', 'hooks/codex.rules', 'hooks/pre-tool-use-guard.sh',
                     'hooks/session-length.sh', 'agents/rules.md', 'templates/AGENTS.md',
                     'vscode/dev-platform.instructions.md',
                     'integrations/openrig/agents/control/guidance/role.md',
                     'integrations/openrig/agents/worker/guidance/role.md',
                     'integrations/openrig/agents/overseer/guidance/role.md'):
            target = self.platform / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('ok\n')
            if path.startswith('hooks/') and path.endswith('.sh'):
                target.chmod(0o755)
        report = self.run_doctor()
        self.assertEqual(report['openrig']['command']['state'], 'ok')
        self.assertEqual(report['openrig']['config']['state'], 'ok')
        self.assertEqual(report['openrig']['workspace']['state'], 'ok')
        self.assertEqual(report['herdr']['server']['state'], 'ok')
        self.assertEqual(report['surfaces']['instructions']['state'], 'ok')

    def test_openrig_config_drift_and_herdr_panel_drift_are_not_silent(self):
        self.openrig_runtime()
        bad_workspace = self.home / '.openrig/workspace'
        self.rig(config={'daemon': {'host': '0.0.0.0'},
                         'workspace': {'root': str(bad_workspace), 'catalogPath': str(bad_workspace / 'workspace.yaml'),
                                       'projectsRoot': str(bad_workspace / 'projects'),
                                       'slicesRoot': str(bad_workspace / 'missions')},
                         'recovery': {'autoDriveProviderPrompts': True},
                         'policies': {'claudeCompaction': {'enabled': True}, 'idleGateQitem': {'autoRegister': 'on'}},
                         'snapshots': {'periodic': {'enabled': True}},
                         'retention': {'enabled': True}, 'ui': {'timezone': 'UTC'},
                         'files': {'allowlist': 'home:' + str(self.home)},
                         'progress': {'scanRoots': 'home:' + str(self.home)}})
        self.herdr(status='stopped')
        report = self.run_doctor()
        self.assertEqual(report['openrig']['config']['state'], 'broken')
        self.assertIn('workspace.root', report['openrig']['config']['wrong'])
        self.assertIn('files.allowlist', report['openrig']['config']['wrong'])
        self.assertEqual(report['herdr']['server']['state'], 'broken')


class TmuxServerEnvironment(unittest.TestCase):
    def test_only_provider_override_names_are_reported_from_a_listing(self):
        from ai_ecosystem import doctor
        listing = ('ANTHROPIC_BASE_URL=http://127.0.0.1:1\nOPENCLAW_SERVICE_KIND=gateway\n'
                   'CLAUDE_CODE_USE_X=1\nPATH=/usr/bin\nTMPDIR=/tmp\n-CODEX_HOME\n')
        self.assertEqual(doctor.tmux_provider_overrides(listing),
                         ['ANTHROPIC_BASE_URL', 'OPENCLAW_SERVICE_KIND', 'CLAUDE_CODE_USE_X'])
        self.assertEqual(doctor.tmux_provider_overrides(''), [])


if __name__ == '__main__':
    unittest.main()
