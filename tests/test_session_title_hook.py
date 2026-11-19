"""hooks/session-title.py gives a Claude Code session a conforming title and never fails."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'hooks/session-title.py'
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import guardrails, naming  # noqa: E402

GOOD = '[dev-server/dev-platform] feat(platform): Unify session naming · owner · claude-desktop · anthropic/opus-5-5 · interactive · 2026-11-06'


def run(data, **env):
    base = {k: v for k, v in os.environ.items()
            if not k.startswith(('DEV_SESSION_', 'CLAUDE_CODE_', 'ANTHROPIC_MODEL', 'CLAUDE_CONFIG_DIR'))}
    base.update(env)
    done = subprocess.run([sys.executable, str(HOOK)], input=data if isinstance(data, str) else json.dumps(data),
                          capture_output=True, text=True, env=base, timeout=20)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)['hookSpecificOutput'] if done.stdout.strip() else None


def run_raw(data, **env):
    base = {k: v for k, v in os.environ.items()
            if not k.startswith(('DEV_SESSION_', 'CLAUDE_CODE_', 'ANTHROPIC_MODEL', 'CLAUDE_CONFIG_DIR'))}
    base.update(env)
    done = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(data), capture_output=True, text=True,
                          env=base, timeout=20)
    return json.loads(done.stdout) if done.stdout.strip() else None


def prompt(text, **extra):
    return dict({'hook_event_name': 'UserPromptSubmit', 'prompt': text, 'cwd': str(ROOT),
                 'transcript_path': '/nonexistent'}, **extra)


class SessionTitleHook(unittest.TestCase):
    def test_first_prompt_gets_a_conforming_title(self):
        out = run(prompt('Fix the login bug'), CLAUDE_CODE_ENTRYPOINT='cli', ANTHROPIC_MODEL='claude-opus-5-5')
        self.assertEqual(naming.problems(out['sessionTitle']), [])
        fields = naming.parse(out['sessionTitle'])
        self.assertEqual((fields['client'], fields['model'], fields['type']), ('claude-cli', 'anthropic/opus-5-5', 'interactive'))
        self.assertIn('Fix the login bug', fields['description'])
        self.assertNotIn('additionalContext', out)         # the CLI agent has no rename control

    def test_a_session_is_titled_and_nudged_once(self):
        import tempfile
        state = tempfile.mkdtemp()
        data = prompt('Fix the login bug', session_id='abc-123', session_title='Fix login bug')
        first = run(data, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)
        self.assertIn('additionalContext', first)
        self.assertIsNone(run(dict(data, prompt='and the logout'), CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))
        self.assertIsNotNone(run(dict(data, session_id='other'), CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))

    def test_a_cut_title_survives_the_desktop_round_trip(self):
        # The desktop app stores U+2026 as three dots. The hook must not then rewrite the title on
        # every prompt, because each rewrite let the app put back an old title over a rename.
        import tempfile
        state = tempfile.mkdtemp()
        data = prompt('Is our development platform in line with the latest from Anthropic about how to build',
                      session_id='round-trip', cwd='/home/owner/dev/dev-platform')
        first = run(data, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)['sessionTitle']
        self.assertNotIn('\u2026', first)
        self.assertEqual(naming.problems(first), [])
        again = dict(data, prompt='next', session_title=first)
        self.assertIsNone(run(again, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))
        stale = ('[dev-server/dev-platform] refactor(development): Is our development platform in line with the latest '
                 'from... \u00b7 owner \u00b7 claude-desktop \u00b7 anthropic/opus-5-5 \u00b7 interactive \u00b7 2026-11-08')
        self.assertTrue(naming.problems(stale))          # the old hook cut to 80 with U+2026; the app made it 82
        fixed = run(dict(data, prompt='next', session_title=stale),
                    CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)['sessionTitle']
        self.assertEqual(naming.problems(fixed), [])
        self.assertIsNone(run(dict(data, prompt='next', session_title=fixed),
                              CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))

    def test_a_rename_wins_over_an_old_title_the_app_puts_back(self):
        import json as _json
        import tempfile
        state = tempfile.mkdtemp()
        stale = ('[dev-server/dev-platform] refactor(development): Is our development platform in line with the latest '
                 'fr... \u00b7 owner \u00b7 claude-desktop \u00b7 anthropic/opus-5-5 \u00b7 interactive \u00b7 2026-11-08')
        rename = 'research(platform): Compare platform with Anthropic multiagent research'
        transcript = Path(tempfile.mkdtemp()) / 't.jsonl'
        records = [{'type': 'custom-title', 'customTitle': stale}, {'type': 'custom-title', 'customTitle': rename},
                   {'type': 'custom-title', 'customTitle': stale}]
        transcript.write_text(''.join(_json.dumps(r) + '\n' for r in records))
        data = prompt('next', session_id='rename-wins', session_title=stale, transcript_path=str(transcript))
        out = run(data, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)
        fields = naming.parse(out['sessionTitle'])
        self.assertEqual(fields['what'], rename)
        self.assertEqual((fields['who'], fields['client']), ('owner', 'claude-desktop'))
        self.assertNotIn('additionalContext', out)
        self.assertIsNone(run(dict(data, session_title=out['sessionTitle']),
                              CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))

    def _transcript(self, *titles):
        import json as _json
        import tempfile
        path = Path(tempfile.mkdtemp()) / 't.jsonl'
        path.write_text(''.join(_json.dumps({'type': 'custom-title', 'customTitle': t}) + '\n' for t in titles))
        return str(path)

    def test_stop_blocks_until_the_model_sets_a_standard_title(self):
        import tempfile
        state = tempfile.mkdtemp()
        guess = ('[dev-server/dev-platform] refactor(development): Is our development platform in line with the latest '
                 'fr... \u00b7 owner \u00b7 claude-desktop \u00b7 anthropic/opus-5-5 \u00b7 interactive \u00b7 2026-11-08')
        stop = {'hook_event_name': 'Stop', 'session_id': 'stop-1', 'cwd': str(ROOT), 'stop_hook_active': False,
                'transcript_path': self._transcript(guess)}
        out = run_raw(stop, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)
        self.assertEqual(out['decision'], 'block')
        self.assertIn('mcp__ccd_session_mgmt__set_session_title', out['reason'])
        self.assertIn('guessed from the first prompt', out['reason'])
        bad = dict(stop, transcript_path=self._transcript(guess, 'research(platform): comparing the platform.'))
        reason = run_raw(bad, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)['reason']
        self.assertIn('capital letter', reason)
        self.assertIn('full stop', reason)
        self.assertIsNone(run_raw(bad, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))   # no loop
        good = dict(stop, session_id='stop-2', transcript_path=self._transcript(
            guess, 'research(platform): Compare platform with Anthropic multiagent research'))
        self.assertIsNone(run_raw(good, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))

    def test_stop_leaves_the_cli_and_subagents_alone(self):
        stop = {'hook_event_name': 'Stop', 'session_id': 'stop-3', 'cwd': str(ROOT), 'transcript_path': self._transcript()}
        self.assertIsNone(run_raw(stop, CLAUDE_CODE_ENTRYPOINT='cli'))
        self.assertIsNone(run_raw(dict(stop, agent_id='a1'), CLAUDE_CODE_ENTRYPOINT='claude-desktop'))

    def test_a_rename_with_only_the_middle_part_is_sent_again_in_full(self):
        import tempfile
        state = tempfile.mkdtemp()
        what = 'research(platform): Compare platform with Anthropic multiagent research'
        call = {'hook_event_name': 'PostToolUse', 'session_id': 'post-1', 'cwd': str(ROOT), 'model': 'claude-opus-5-5',
                'tool_name': 'mcp__ccd_session_mgmt__set_session_title',
                'tool_input': {'session_id': 'self', 'title': what}, 'transcript_path': self._transcript()}
        note = run_raw(call, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)
        context = note['hookSpecificOutput']['additionalContext']
        full = context.split('`')[1]
        self.assertEqual(naming.problems(full), [])
        self.assertEqual(naming.parse(full)['what'], what)
        self.assertIsNone(run_raw(dict(call, tool_input={'session_id': 'self', 'title': full}),
                                  CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))
        stop = {'hook_event_name': 'Stop', 'session_id': 'post-1', 'cwd': str(ROOT), 'transcript_path': self._transcript()}
        self.assertIsNone(run_raw(stop, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))
        stale = ('[dev-server/dev-platform] refactor(development): Is our development platform in line with the latest '
                 'from... \u00b7 owner \u00b7 claude-desktop \u00b7 anthropic/opus-5-5 \u00b7 interactive \u00b7 2026-11-08')
        back = run(dict(prompt('next', session_id='post-1', session_title=stale), transcript_path=self._transcript()),
                   CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)
        self.assertEqual(naming.parse(back['sessionTitle'])['what'], what)

    def test_a_rename_of_another_session_or_a_bad_middle_part(self):
        import tempfile
        state = tempfile.mkdtemp()
        call = {'hook_event_name': 'PostToolUse', 'session_id': 'post-2', 'cwd': str(ROOT),
                'tool_name': 'mcp__ccd_session_mgmt__set_session_title',
                'tool_input': {'session_id': 'local_other', 'title': 'x'}}
        self.assertIsNone(run_raw(call, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state))
        bad = dict(call, tool_input={'session_id': 'self', 'title': 'fix(misc): fixing stuff.'})
        context = run_raw(bad, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)['hookSpecificOutput']['additionalContext']
        self.assertIn('not standard', context)
        self.assertIn('<purpose(area): Description #ref>', context)

    def test_style_problems(self):
        self.assertEqual(naming.style_problems('fix(naming): Keep a rename when the app restores an old title #12'), [])
        self.assertTrue(naming.style_problems('fix(misc): Keep it'))
        self.assertTrue(naming.style_problems('fix(ui): Fixing the photo captions'))
        self.assertTrue(naming.style_problems('fix(ui): Align ' + 'photo ' * 10 + 'captions'))
        self.assertTrue(naming.style_problems('[h/p] fix(ui): Align captions \u00b7 owner'))

    def test_entrypoints_map_to_clients_and_types(self):
        for entry, client, kind in (('claude-desktop', 'claude-desktop', 'interactive'),
                                    ('sdk-cli', 'claude-sdk', 'headless'), ('sdk-ts', 'claude-sdk', 'headless'),
                                    ('claude-vscode', 'claude-vscode', 'interactive')):
            fields = naming.parse(run(prompt('Do a thing'), CLAUDE_CODE_ENTRYPOINT=entry)['sessionTitle'])
            self.assertEqual((fields['client'], fields['type'], fields['provider'] if 'provider' in fields else None),
                             (client, kind, None), entry)

    def test_subagent_type(self):
        data = prompt('Search the code', agent_id='a1')
        self.assertEqual(naming.parse(run(data, CLAUDE_CODE_ENTRYPOINT='sdk-cli')['sessionTitle'])['type'], 'subagent')

    def test_desktop_prompt_asks_the_agent_for_a_better_title(self):
        out = run(prompt('Plan the work'), CLAUDE_CODE_ENTRYPOINT='claude-desktop')
        self.assertIn('mcp__ccd_session_mgmt__set_session_title', out['additionalContext'])
        self.assertIn('Change ONLY the middle part', out['additionalContext'])
        self.assertIn('<purpose(area): Description #ref> · ', out['additionalContext'])   # the exact frame to fill
        self.assertEqual(out['hookEventName'], 'UserPromptSubmit')

    def test_branch_helps_guess_the_purpose_and_the_nudge_says_so(self):
        out = run(prompt('Look at this', git_branch='fix/login-bug-abc123'), CLAUDE_CODE_ENTRYPOINT='claude-desktop')
        self.assertEqual(naming.parse(out['sessionTitle'])['purpose'], 'fix')
        self.assertIn('rename the session', out['additionalContext'])

    def test_a_model_written_part_is_wrapped_on_any_prompt(self):
        import tempfile
        state = tempfile.mkdtemp()
        first = prompt('Plan it', session_id='s1')
        run(first, CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)          # marks the session
        out = run(dict(first, session_title='fix(ui): Align photo captions #12'),
                  CLAUDE_CODE_ENTRYPOINT='claude-desktop', XDG_STATE_HOME=state)
        fields = naming.parse(out['sessionTitle'])
        self.assertEqual((fields['what'], fields['client']), ('fix(ui): Align photo captions #12', 'claude-desktop'))
        self.assertNotIn('additionalContext', out)

    def test_a_spawned_worker_keeps_its_parent_and_damaged_fields_are_rebuilt(self):
        damaged = 'review(calls): Verify call records · verify-records@calls · claude-desktop · anthropic/sonnet-5-5 · subagent · 2026-11-06'
        fields = naming.parse(run(prompt('x', session_title=damaged), CLAUDE_CODE_ENTRYPOINT='claude-desktop')['sessionTitle'])
        self.assertEqual((fields['who'], fields['type'], fields['what']),
                         ('verify-records@calls', 'subagent', 'review(calls): Verify call records'))
        self.assertEqual(fields['project'], naming.project_of(str(ROOT)))

    def test_injected_text_is_not_the_description(self):
        out = run(prompt('You are operating in a git worktree.\nFix the call transfer routing'), CLAUDE_CODE_ENTRYPOINT='cli')
        self.assertIn('Fix the call transfer routing', out['sessionTitle'])

    def test_a_title_comes_out_with_no_transcript_and_no_model_on_a_command_line(self):
        # 2026-11-17: under the stop hook the claude process is more than five processes up, so
        # no --model is found; the hook then opened a transcript path of None and printed nothing.
        probe = ("import importlib.util, sys; s = importlib.util.spec_from_file_location('h', sys.argv[1]); "
                 "h = importlib.util.module_from_spec(s); s.loader.exec_module(h); "
                 "print(h.read_jsonl_head(None), h.last_assistant_model(None), h.read_jsonl_head(''))")
        done = subprocess.run([sys.executable, '-c', probe, str(HOOK)], capture_output=True, text=True, timeout=20)
        self.assertEqual(done.stdout.strip(), '[] None []', done.stderr)

    def test_a_conforming_title_is_left_alone(self):
        self.assertIsNone(run(prompt('anything', session_title=GOOD)))
        self.assertIsNone(run({'hook_event_name': 'SessionStart', 'source': 'resume', 'session_title': GOOD,
                               'cwd': str(ROOT)}))

    def test_an_old_title_becomes_the_description(self):
        out = run({'hook_event_name': 'SessionStart', 'source': 'startup', 'session_title': 'Plan October travel',
                   'cwd': str(ROOT)}, CLAUDE_CODE_ENTRYPOINT='cli')
        self.assertEqual(naming.parse(out['sessionTitle'])['description'], 'Plan October travel')
        self.assertEqual(out['hookEventName'], 'SessionStart')

    def test_session_start_without_a_title_or_prompt_does_nothing(self):
        self.assertIsNone(run({'hook_event_name': 'SessionStart', 'source': 'startup', 'cwd': str(ROOT)}))

    def test_secrets_and_tags_do_not_reach_the_title(self):
        text = '<system-reminder>x</system-reminder>\ndeploy with token=abc123 and sk-abcdefghijklmnop1234'
        title = run(prompt(text))['sessionTitle']
        self.assertNotIn('abc123', title)
        self.assertNotIn('sk-abcdef', title)
        self.assertNotIn('system-reminder', title)

    def test_the_prompt_part_is_short(self):
        fields = naming.parse(run(prompt('word ' * 100))['sessionTitle'])
        self.assertLessEqual(len(fields['description']), 61)

    def test_launcher_context_wins(self):
        out = run(prompt('Do it'), DEV_SESSION_WHO='ops', DEV_SESSION_TYPE='seat', DEV_SESSION_MODEL='gpt-5',
                  DEV_SESSION_PROVIDER='openai')
        fields = naming.parse(out['sessionTitle'])
        self.assertEqual((fields['who'], fields['type'], fields['model']), ('ops', 'seat', 'openai/gpt-5'))

    def test_bad_input_prints_nothing_and_exits_zero(self):
        for bad in ('', 'not json', '[]', '{"hook_event_name":"UserPromptSubmit","prompt":5}'):
            self.assertIsNone(run(bad))


class Wiring(unittest.TestCase):
    def test_one_owner_registers_the_hook(self):
        # bin/ai-title-bundle's installer registers the hook; the settings fragment must not add a second copy.
        self.assertNotIn('session-title.py', (ROOT / 'hooks/claude-settings.hooks.json').read_text())
        self.assertTrue(os.access(HOOK, os.X_OK))

    def test_guardrails_block_carries_the_naming_rule(self):
        block = guardrails.block('claude', Path('/opt/dev-platform/current'))
        self.assertIn('purpose(area): Description #ref', block)
        self.assertTrue(block.endswith(guardrails.END))


if __name__ == '__main__':
    unittest.main()
