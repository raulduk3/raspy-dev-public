"""A project's team is shaped from a named shape into its engagement folder, with a history."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SHAPES = ROOT / 'integrations/openrig/shapes'


class RigShape(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.checkout = self.base / 'Tetris_Game'
        self.checkout.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.checkout)], check=True)
        (self.base / 'repos.conf').write_text(f'owner/tetris {self.checkout} local develop\n')
        self.engagements = self.base / 'engagements'
        self.env = {**os.environ, 'HOME': str(self.base / 'home'), 'GIT_CONFIG_GLOBAL': os.devnull,
                    'DEV_PLATFORM_REPOS': str(self.base / 'repos.conf'),
                    'DEV_PLATFORM_ENGAGEMENTS': str(self.engagements)}

    def shape(self, *args, expected=0):
        result = subprocess.run([str(ROOT / 'bin/rig-shape'), *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_the_build_shape_is_the_standard_team(self):
        strip = lambda path: [l for l in path.read_text().splitlines() if not l.startswith('summary:')]
        self.assertEqual(strip(SHAPES / 'build.yaml'), strip(ROOT / 'integrations/openrig/helm.yaml'))
        self.assertEqual([line.split('\t')[0] for line in self.shape('list').splitlines()], ['build', 'review', 'solo'])

    def test_a_shape_is_written_to_the_engagement_folder_with_its_own_history(self):
        out = self.shape('write', 'owner/tetris', 'review', '--runtime', 'lead=codex')
        folder = self.engagements / 'tetris-game'
        self.assertIn('helm-tetris-game: review shape recorded', out)
        self.assertIn('takes effect the next time the team starts', out)
        spec = yaml.safe_load((folder / 'rig.yaml').read_text())
        self.assertEqual(spec['name'], 'helm-tetris-game')
        members = {m['id']: m for pod in spec['pods'] for m in pod['members']}
        self.assertEqual({k: m['runtime'] for k, m in members.items()},
                         {'lead': 'codex', 'overseer': 'codex', 'second': 'claude-code'})
        for member in members.values():
            ref = Path(member['agent_ref'].removeprefix('path:'))
            self.assertTrue(ref.is_absolute() and (ref / 'agent.yaml').is_file(), ref)
        self.assertEqual((folder / 'project').read_text(), 'owner/tetris\n')
        self.assertIn('unchanged', self.shape('write', 'owner/tetris', 'review', '--runtime', 'lead=codex'))
        (folder / 'CLAUDE.md').write_text('seat guidance written by OpenRig\n')
        self.shape('write', str(self.checkout.resolve()), 'solo')
        history = self.shape('history', 'owner/tetris').splitlines()
        self.assertEqual([line.split(' ', 3)[3] for line in history],
                         ['rig: solo shape for helm-tetris-game',
                          'rig: review shape for helm-tetris-game (lead=codex)'])
        tracked = subprocess.run(['git', '-C', str(folder), 'ls-files'], capture_output=True, text=True).stdout
        self.assertEqual(tracked.split(), ['.gitignore', 'project', 'rig.yaml'])
        self.assertIn('name: helm-tetris-game', self.shape('show', 'owner/tetris'))

    def test_every_seat_goes_on_one_runtime_for_a_claude_only_team(self):
        self.shape('write', 'owner/tetris', 'build', '--all', 'claude-code')
        spec = yaml.safe_load((self.engagements / 'tetris-game' / 'rig.yaml').read_text())
        self.assertEqual({m['id']: m['runtime'] for pod in spec['pods'] for m in pod['members']},
                         {'lead': 'claude-code', 'overseer': 'claude-code'})
        self.assertIn('(lead=claude-code, overseer=claude-code)', self.shape('history', 'owner/tetris'))

    def test_a_team_keeps_the_engagement_folder_its_repository_already_has(self):
        folder = self.engagements / 'older-name'
        folder.mkdir(parents=True)
        (folder / 'project').write_text('owner/tetris\n')
        self.assertIn('helm-older-name', self.shape('write', 'owner/tetris', 'build'))

    def test_unknown_shapes_seats_and_runtimes_are_refused(self):
        self.assertIn('no shape named huge', self.shape('write', 'owner/tetris', 'huge', expected=2))
        self.assertIn('no seat named second', self.shape('write', 'owner/tetris', 'solo', '--runtime', 'second=codex',
                                                         expected=2))
        self.assertIn('runtime must be one of', self.shape('write', 'owner/tetris', 'build', '--runtime', 'lead=gpt',
                                                           expected=2))
        self.assertFalse(self.engagements.exists())

    def test_a_validator_that_cannot_run_is_reported_not_taken_as_a_verdict(self):
        fake = self.base / 'bin'
        fake.mkdir()
        (fake / 'rig').write_text('#!/bin/sh\necho "Pinned OpenRig runtime missing" >&2\nexit 1\n')
        (fake / 'rig').chmod(0o755)
        self.env['PATH'] = f"{fake}{os.pathsep}{self.env['PATH']}"
        self.assertIn('not validated', self.shape('write', 'owner/tetris', 'build'))
        (fake / 'rig').write_text('#!/bin/sh\necho \'{"valid":false,"errors":["pods[0]: bad"]}\'\nexit 1\n')
        self.assertIn('OpenRig rejects this spec: pods[0]: bad', self.shape('write', 'owner/tetris', 'solo', expected=2))

    @unittest.skipUnless(shutil.which('rig'), 'OpenRig is not installed; its validator cannot run')
    def test_every_shape_passes_openrig_validation(self):
        self.env['HOME'] = os.environ['HOME']  # the rig launcher finds its pinned runtime there
        for shape in ('build', 'review', 'solo'):
            with self.subTest(shape=shape):
                self.assertIn('valid by rig spec validate', self.shape('write', 'owner/tetris', shape))


if __name__ == '__main__':
    unittest.main()
