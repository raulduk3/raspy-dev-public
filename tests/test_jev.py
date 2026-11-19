"""Jev adapter tests: schemas are closed, results are typed, no provider secrets or prose."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLATFORM = Path(__file__).resolve().parents[1]
CLI = PLATFORM / 'bin/ai-jev'
sys.path.insert(0, str(PLATFORM / 'lib'))
from ai_ecosystem import jev  # noqa: E402


class JevAdapter(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='ai-jev-')
        self.addCleanup(tmp.cleanup)
        self.temp = Path(tmp.name)
        self.base_env = {
            'OL_SECRET_LAUNCH_ONLY': '1',          # the CLI never reaches the owner's real key
            'PATH': os.environ.get('PATH', ''),
            'HOME': str(self.temp / 'home'),
            'DEV_PLATFORM_CONFIG': str(self.temp / 'config'),
            'DEV_PLATFORM_STATE': str(self.temp / 'state'),
            'PYTHONDONTWRITEBYTECODE': '1',
            'OL_SECRET_LAUNCH_ONLY': '1',     # the machine's own Jev key never reaches a test
        }

    def run_cli(self, *args, stdin=None, check=True, env=None):
        merged = dict(self.base_env)
        if env:
            merged.update(env)
        run = subprocess.run([str(CLI), *args], input=stdin, capture_output=True, text=True,
                             timeout=30, env=merged)
        if check and run.returncode:
            self.fail(f'{args}: {run.returncode}\nSTDOUT={run.stdout}\nSTDERR={run.stderr}')
        return run

    def test_registry_contains_only_valid_bounded_schemas(self):
        names = json.loads(self.run_cli('list').stdout)['schemas']
        self.assertEqual(names, [
            'check-completion',
            'classify-tool-risk',
            'detect-instruction-injection',
            'rank-context',
            'route-task',
            'verify-claim',
        ])
        for name in names:
            schema = jev.load_schema(name)
            self.assertIn(schema['questions'][0]['type'], {'choice', 'score', 'noul'})
            self.assertNotIn('plan', json.dumps(schema).lower()) if name != 'route-task' else None

    def test_request_contains_closed_questions_and_caller_state(self):
        state = {'task': 'Find the best source', 'candidate': 'docs/how-it-connects.md'}
        out = json.loads(self.run_cli('request', 'rank-context', '--state', json.dumps(state)).stdout)
        self.assertEqual(out['model'], 'typesafeai/jev-latest')
        self.assertEqual(out['state'], state)
        self.assertEqual(sorted(out['questions']), ['load_first', 'relevance'])
        self.assertEqual(out['questions']['relevance']['type'], 'score')
        self.assertNotIn('reasoning', json.dumps(out).lower())

    def test_fixture_decision_validates_and_canonicalizes_provider_response(self):
        response = {
            'answers': {
                'risk_level': {'choice': 'destructive_or_external', 'confidence': 0.82,
                               'probabilities': {'destructive_or_external': 0.82, 'local_reversible': 0.10}},
                'requires_confirmation': {'probability': 0.91, 'confidence': 0.88},
            }
        }
        out = json.loads(self.run_cli('decide', 'classify-tool-risk', '--state', '{"cmd":"git push"}',
                                      '--response', json.dumps(response)).stdout)
        self.assertEqual(out['answers']['risk_level']['choice'], 'destructive_or_external')
        self.assertEqual(out['answers']['requires_confirmation']['probability'], 0.91)
        self.assertEqual(set(out), {'schema', 'model', 'usage', 'answers'})

    def test_rejects_undeclared_choices_and_extra_answers(self):
        bad_choice = {'answers': {
            'source_relation': {'choice': 'probably_true', 'confidence': 0.7},
            'quote_faithful': {'probability': 0.5, 'confidence': 0.7},
        }}
        run = self.run_cli('decide', 'verify-claim', '--state', '{}', '--response', json.dumps(bad_choice), check=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn('choice is not one of the declared options', run.stderr)

        extra = {'answers': {
            'source_relation': {'choice': 'supports', 'confidence': 0.7},
            'quote_faithful': {'probability': 0.5, 'confidence': 0.7},
            'freeform_reason': {'text': 'because I think so', 'confidence': 0.7},
        }}
        run = self.run_cli('decide', 'verify-claim', '--state', '{}', '--response', json.dumps(extra), check=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn('undeclared answers', run.stderr)

    def test_command_provider_receives_no_secret_and_secret_is_not_echoed(self):
        with tempfile.TemporaryDirectory(prefix='jev-provider-') as tmp:
            provider = Path(tmp) / 'provider.py'
            seen = Path(tmp) / 'seen.json'
            provider.write_text(
                'import json, os, pathlib, sys\n'
                f'pathlib.Path({str(seen)!r}).write_text(sys.stdin.read())\n'
                'assert os.environ.get("JEV_API_KEY") == "SECRET-DO-NOT-PRINT"\n'
                'print(json.dumps({"answers": {\n'
                '  "task_kind": {"choice": "engineering_change", "confidence": 0.9},\n'
                '  "plan_first": {"probability": 0.8, "confidence": 0.9}\n'
                '}}))\n'
            )
            result = self.run_cli('decide', 'route-task', '--state', '{"request":"implement"}',
                                  env={'JEV_COMMAND': f'{sys.executable} {provider}',
                                       'JEV_API_KEY': 'SECRET-DO-NOT-PRINT'})
            self.assertNotIn('SECRET-DO-NOT-PRINT', result.stdout + result.stderr)
            request = json.loads(seen.read_text())
            self.assertEqual(request['model'], 'typesafeai/jev-latest')
            self.assertIn('task_kind', request['questions'])
            self.assertEqual(json.loads(result.stdout)['answers']['task_kind']['choice'], 'engineering_change')

    def test_status_install_and_monthly_limit_disable_live_calls(self):
        installed = json.loads(self.run_cli('install-research').stdout)
        self.assertTrue(installed['installed'].endswith('jev.json'))
        self.assertFalse(installed['config']['credential']['available'])
        status = json.loads(self.run_cli('status').stdout)
        self.assertEqual(status['config']['endpoint'], 'https://gateway.ngrok.ai/v1/systemone')
        self.assertEqual(status['config']['monthly_limit_micros'], 10_000_000)
        self.assertEqual(status['usage']['spent_micros'], 0)
        config = self.temp / 'config/jev.json'
        data = json.loads(config.read_text())
        data['monthly_limit_micros'] = 1
        config.write_text(json.dumps(data))
        provider = self.temp / 'provider.py'
        provider.write_text('print("{}")\n')
        run = self.run_cli('decide', 'route-task', '--state', '{"request":"implement"}',
                           env={'JEV_COMMAND': f'{sys.executable} {provider}'}, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn('monthly limit would be exceeded', run.stderr)
        blocked = json.loads(self.run_cli('status').stdout)['usage']
        self.assertFalse(blocked['enabled'])
        self.assertEqual(blocked['disabled_reason'], 'monthly_limit_would_be_exceeded')

    def test_live_score_and_noul_shapes_are_accepted(self):
        response = {'model': 'jev-1.13.0', 'usage': {'input_tokens': 123}, 'answers': {
            'relevance': {'type': 'score', 'score': 2.7, 'confidence': 0.8,
                          'probabilities': {'0': 0.01, '1': 0.04, '2': 0.2, '3': 0.75}},
            'load_first': {'type': 'noul', 'noul': 0.93},
        }}
        out = json.loads(self.run_cli('decide', 'rank-context', '--state', '{}',
                                      '--response', json.dumps(response)).stdout)
        self.assertEqual(out['model'], 'jev-1.13.0')
        self.assertEqual(out['answers']['relevance']['score'], 2.7)
        self.assertEqual(out['answers']['relevance']['choice'], 'critical')
        self.assertEqual(out['answers']['load_first']['probability'], 0.93)


if __name__ == '__main__':
    unittest.main()
