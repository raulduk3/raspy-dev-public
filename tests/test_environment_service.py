import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from ai_ecosystem.environment_service import remaining, choose, launch_plan


def row(account, state, left, runtime='codex'):
    return dict(account=account, state=state, remaining_percent=left, runtime=runtime,
                capabilities={'codex':'authenticated', 'claude':'unverified', 'pi':'unverified'},
                container='container-'+account, image='pinned', quota=[], observed_at=100)


class EnvironmentReadiness(unittest.TestCase):
    def test_exhausted_core_is_not_rescued_by_separate_model_pool(self):
        quota=[{'limit_id':'base_model_inference','primary':{'usedPercent':0}},
               {'limit_id':'codex','primary':{'usedPercent':100}}]
        self.assertEqual(remaining(quota), 0)
        self.assertIsNone(remaining(quota[:1]))
        self.assertIsNone(remaining(None))

    def test_unavailable_and_exhausted_accounts_do_not_block_healthy_choice(self):
        rows=[row('openai-bravo','exhausted',0), row('openai-alpha','ready',27),
              row('unreachable','unavailable',100)]
        self.assertEqual(choose(rows,'codex')['account'], 'openai-alpha')
        self.assertIsNone(choose(rows,'claude'))

    def test_pi_native_auth_is_not_inferred_from_codex_login(self):
        result=launch_plan([row('openai-alpha','ready',27)],Path('/state'),'pi','openai')
        self.assertIsNone(result['selected'])
        self.assertFalse(result['launch_allowed'])
        self.assertEqual(result['execution_kind'],'host')
        self.assertNotIn('mounts',result)

    def test_explicit_unavailable_account_does_not_silently_switch(self):
        rows=[row('openai-bravo','login_required',None),row('openai-alpha','ready',27)]
        result=launch_plan(rows,Path('/state'),'codex','openai','openai-bravo')
        self.assertIsNone(result['selected'])
        self.assertFalse(result['launch_allowed'])

    def test_unknown_quota_requires_explicit_account_and_override(self):
        account=row('anthropic-alpha','quota_unknown',None,'claude')
        account['capabilities']['claude']='authenticated'
        for preferred, override in [(None,False),(None,True),('anthropic-alpha',False)]:
            self.assertFalse(launch_plan([account],Path('/state'),'claude','anthropic',preferred,override)['launch_allowed'])
        self.assertTrue(launch_plan([account],Path('/state'),'claude','anthropic','anthropic-alpha',True)['launch_allowed'])
