"""bin/pstack-model turns a pstack role or tier slug into a model and effort for one runtime."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PstackModel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / 'pstack-models.md'
        self.system = Path(self.tmp.name) / 'system-pstack-models.md'
        self.addCleanup(self.tmp.cleanup)

    def run_model(self, *args, expected=0):
        env = dict(os.environ, DEV_PLATFORM_PSTACK_MODELS=str(self.file),
                   DEV_PLATFORM_PSTACK_SYSTEM=str(self.system))
        result = subprocess.run([str(ROOT / 'bin/pstack-model'), *args],
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def resolve(self, *args, expected=0):
        result = self.run_model('resolve', *args, expected=expected)
        return [tuple(line.split('\t')) for line in result.stdout.splitlines()]

    def test_without_a_file_a_role_takes_its_default_tier(self):
        # OpenRouter is first in every tier (owner, 2026-10-12).
        self.assertEqual(self.resolve('judgment and prose'), [('openrouter:anthropic/claude-fable-5.1', 'max')])
        self.assertEqual(self.resolve('swarm workers'), [('openrouter:deepseek/deepseek-v4-pro-0813', 'xhigh')])
        self.assertEqual(self.resolve('mechanical'), [('openrouter:deepseek/deepseek-v4.1-flash', '')])

    def test_claude_and_codex_are_the_fallbacks_at_the_bottom(self):
        self.assertEqual(self.resolve('judgment and prose', '--runtime', 'claude'), [('claude-opus-5-5', 'max')])
        self.assertEqual(self.resolve('swarm workers', '--runtime', 'codex'), [('gpt-6.1-sol', 'xhigh')])
        self.assertEqual(self.resolve('mechanical', '--runtime', 'claude'), [('claude-haiku-4-5', '')])

    def test_a_panel_spreads_across_families(self):
        self.assertEqual(self.resolve('arena runners', '--all'),
                         [('openrouter:anthropic/claude-fable-5.1', 'max'), ('openrouter:openai/gpt-6-astra-pro', 'max'),
                          ('openrouter:deepseek/deepseek-v4-pro-0813', 'xhigh')])
        # `.2` is the second family the runtime can run, so a Claude panel keeps a second opinion.
        self.assertEqual(self.resolve('arena runners', '--all', '--runtime', 'claude'),
                         [('claude-opus-5-5', 'max'), ('claude-fable-5-1', 'max'),
                          ('claude-opus-5-5', 'xhigh')])

    def test_codex_takes_its_own_families(self):
        self.assertEqual(self.resolve('reflect tooling', '--runtime', 'codex'), [('gpt-6.1-sol', 'max')])

    def test_the_owners_tiers_and_roles_win(self):
        self.file.write_text('# budget: small (medium)\ntier judgment: opus\n'
                             'judgment and prose: judgment-medium\nhow explorer: sonnet-low\n')
        self.assertEqual(self.resolve('judgment and prose'), [('opus', 'medium')])
        self.assertEqual(self.resolve('how explorer'), [('sonnet', 'low')])
        self.assertEqual(self.resolve('hardest tasks'), [('opus', 'max')])

    def test_aliases_inherit_unless_refused(self):
        self.file.write_text('judgment and prose: inherit-parent\n')
        self.assertEqual(self.resolve('judgment and prose'), [('inherit', '')])
        # With nothing runnable on the owner's line, the default line decides.
        self.assertEqual(self.resolve('judgment and prose', '--no-inherit', '--runtime', 'claude'), [('claude-opus-5-5', 'max')])

    def test_nothing_runnable_exits_one(self):
        self.assertEqual(self.resolve('codex:gpt-5.6-sol-high', '--runtime', 'claude', expected=1), [])


    def test_the_system_file_is_read_and_a_users_file_overrides_it_line_by_line(self):
        self.system.write_text('tier judgment: codex:gpt-6.1-sol\nhow explorer: judgment-high\n')
        self.assertEqual(self.resolve('hardest tasks'), [('codex:gpt-6.1-sol', 'max')])
        self.assertEqual(self.resolve('how explorer'), [('codex:gpt-6.1-sol', 'high')])
        self.file.write_text('how explorer: mechanical\n')
        self.assertEqual(self.resolve('how explorer'), [('openrouter:deepseek/deepseek-v4.1-flash', '')])
        # The user's file names one line; the system's tier still applies everywhere else.
        self.assertEqual(self.resolve('hardest tasks'), [('codex:gpt-6.1-sol', 'max')])
        self.assertEqual(self.run_model('source', 'how explorer').stdout.strip(), str(self.file))
        self.assertEqual(self.run_model('source', 'hardest tasks').stdout.strip(), 'default')

    def test_without_a_system_file_the_defaults_hold(self):
        self.assertFalse(self.system.exists())
        self.assertEqual(self.resolve('hardest tasks'), [('openrouter:anthropic/claude-fable-5.1', 'max')])

    def test_a_malformed_line_is_reported_and_not_used(self):
        self.system.write_text('tier judgment: codex:gpt-6.1-sol\nhardest tasks judgment-low\nhow explorer:\n')
        result = self.run_model('resolve', 'hardest tasks')
        self.assertEqual(result.stdout.split('\t')[0], 'codex:gpt-6.1-sol')
        self.assertIn(f'{self.system}:2: not a `key: value` line', result.stderr)
        self.assertIn(f'{self.system}:3: not a `key: value` line', result.stderr)

    def test_show_names_each_lines_file(self):
        self.system.write_text('swarm workers: judgment-high\n')
        shown = dict(line.rsplit('\t', 1) for line in self.run_model('show').stdout.splitlines())
        self.assertEqual(shown['swarm workers: judgment-high'], str(self.system))
        self.assertEqual(shown['hardest tasks: judgment-max'], 'default')

    def test_pi_runs_the_openai_subscription_and_never_a_claude_family(self):
        self.system.write_text('tier judgment: claude-opus-5-5, codex:gpt-6.1-sol\ntier mechanical: claude-haiku-4-5\n')
        self.assertEqual(self.resolve('assistant start', '--runtime', 'pi'), [('openai-codex/gpt-6.1-sol', '')])
        self.assertEqual(self.resolve('ops start', '--runtime', 'pi'), [('openai-codex/gpt-6-luna', '')])
        self.assertEqual(self.resolve('engineer start', '--runtime', 'pi'), [('openai-codex/gpt-6-sol', '')])
        self.assertEqual(self.resolve('judgment and prose', '--runtime', 'pi'), [('openai-codex/gpt-6.1-sol', 'max')])
        self.assertEqual(self.resolve('mechanical', '--runtime', 'pi', expected=1), [])
        self.assertEqual(self.resolve('pi:openai-codex/gpt-6-sol-high', '--runtime', 'pi'), [('openai-codex/gpt-6-sol', 'high')])
        self.assertEqual(self.resolve('pi:openrouter/z-ai/glm-5-high', '--runtime', 'pi'), [('openrouter/z-ai/glm-5', 'high')])
        self.assertEqual(self.resolve('pi:openrouter/z-ai/glm-5', '--runtime', 'claude', expected=1), [])

    def test_pi_takes_the_first_family_it_can_run_openrouter_included(self):
        self.assertEqual(self.resolve('judgment and prose', '--runtime', 'pi'),
                         [('openrouter/anthropic/claude-fable-5.1', 'max')])
        self.assertEqual(self.resolve('mechanical', '--runtime', 'pi'), [('openrouter/deepseek/deepseek-v4.1-flash', '')])
        self.assertEqual(self.resolve('openrouter:x-ai/grok-4.3', '--runtime', 'pi'), [('openrouter/x-ai/grok-4.3', '')])

    def test_the_openrouter_runtime_never_picks_a_subscription(self):
        self.assertEqual(self.resolve('rig worker', '--runtime', 'openrouter'),
                         [('openrouter/deepseek/deepseek-v4-pro-0813', 'high')])
        self.assertEqual(self.resolve('rig worker retry', '--runtime', 'openrouter'),
                         [('openrouter/anthropic/claude-opus-5.5', 'high')])
        self.assertEqual(self.resolve('rig control', '--runtime', 'openrouter'),
                         [('openrouter/deepseek/deepseek-v4-pro-0813', 'high')])
        self.assertEqual(self.resolve('advice', '--runtime', 'openrouter'),
                         [('openrouter/anthropic/claude-fable-5.1', 'max')])
        self.assertEqual(self.resolve('pi:openrouter/z-ai/glm-5-high', '--runtime', 'openrouter'),
                         [('openrouter/z-ai/glm-5', 'high')])
        # A tier with no OpenRouter family resolves nothing rather than a subscription.
        self.system.write_text('tier mechanical: claude-haiku-4-5, codex:gpt-6-luna\n')
        self.assertEqual(self.resolve('mechanical', '--runtime', 'openrouter', expected=1), [])
        self.assertEqual(self.resolve('assistant start', '--runtime', 'openrouter', expected=1), [])

    def test_the_two_rig_overseers_sit_on_two_families(self):
        first = self.resolve('rig overseer', '--runtime', 'openrouter')[0][0]
        second = self.resolve('rig second overseer', '--runtime', 'openrouter')[0][0]
        self.assertEqual((first, second), ('openrouter/anthropic/claude-fable-5.1', 'openrouter/openai/gpt-6-astra-pro'))

    def test_every_role_resolves_for_pi_and_openrouter(self):
        roles = [line.split(': ', 1)[0] for line in self.run_model('defaults').stdout.splitlines()
                 if ': ' in line and not line.startswith(('#', 'tier '))]
        for runtime in ('pi', 'openrouter'):
            for role in roles:
                if runtime == 'openrouter' and role.endswith(' start'):
                    continue  # the Pi roles start on the OpenAI subscription, by the launcher's choice
                with self.subTest(runtime=runtime, role=role):
                    self.assertTrue(self.resolve(role, '--all', '--runtime', runtime))

    def test_another_user_resolves_the_same_from_the_system_file(self):
        self.system.write_text('tier judgment: codex:gpt-6.1-sol\n')
        other_home = Path(self.tmp.name) / 'ops'
        other_home.mkdir()
        env = dict(os.environ, HOME=str(other_home), DEV_PLATFORM_PSTACK_SYSTEM=str(self.system))
        env.pop('DEV_PLATFORM_PSTACK_MODELS', None)
        theirs = subprocess.run([str(ROOT / 'bin/pstack-model'), 'resolve', 'judgment-max'],
                                capture_output=True, text=True, env=env).stdout
        self.assertEqual(theirs, self.run_model('resolve', 'judgment-max').stdout)


if __name__ == '__main__':
    unittest.main()
