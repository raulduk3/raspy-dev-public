"""The one account registry, its resolver and rotation,
against a fake store (no root, no network, no credential)."""
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import re
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ai_ecosystem import accounts, registry, usage  # noqa: E402


class Fake(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for name in ('state', 'store', 'usage'):
            (self.tmp / name).mkdir()
        (self.tmp / 'chat').touch()
        env = {'OL_ACCOUNTS_STATE': str(self.tmp / 'state'), 'OL_ACCOUNTS_STORE': str(self.tmp / 'store'),
               'OL_USAGE_DIR': str(self.tmp / 'usage'), 'OL_CHAT': str(self.tmp / 'chat'),
               'OL_LOGIN_RUN': str(self.tmp / 'run'), 'OL_CRED_RUN': str(self.tmp / 'cred'),
               'DEV_PLATFORM_ACCOUNT_SELECTION': str(self.tmp / 'account-selection.json')}
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        template = json.loads(registry.TEMPLATE.read_text())
        (self.tmp / 'state/registry.json').write_text(json.dumps(template))
        self.data = registry.load()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)   # 2026-11-17: 220 of these were left in /tmp

    def signed(self, account, client, identity='owner@example.invalid', verified=True):
        (self.tmp / 'state' / f'{account}.{client}.json').write_text(
            json.dumps({'identity': identity, 'verified': verified, 'checked_at': int(time.time())}))

    def used(self, account, percent, resets_in=3600):
        (self.tmp / 'usage' / f'{account}.json').write_text(json.dumps(
            {'account': account, 'captured': int(time.time()),
             'five_hour': {'used_percentage': percent, 'resets_at': int(time.time()) + resets_in}}))


class RegistryTest(Fake):
    def test_template_is_valid_and_holds_no_credential(self):
        ids = registry.ids(self.data)
        for name in ('anthropic-bravo', 'anthropic-alpha', 'openai-bravo', 'openai-alpha', 'zai', 'openrouter', 'github'):
            self.assertIn(name, ids)
        defaults = {e['provider']: e['id'] for e in self.data['accounts'] if e.get('default')}
        self.assertEqual(defaults['anthropic'], 'anthropic-bravo')
        self.assertEqual(defaults['openai'], 'openai-bravo')

    def test_a_credential_field_is_refused(self):
        bad = json.loads(registry.TEMPLATE.read_text())
        bad['accounts'][0]['refresh_token'] = 'x'
        path = self.tmp / 'bad.json'
        path.write_text(json.dumps(bad))
        with self.assertRaises(ValueError):
            registry.load(path)

    def test_a_new_account_is_one_entry(self):
        data = json.loads(registry.TEMPLATE.read_text())
        data['accounts'].append({'id': 'anthropic-work', 'provider': 'anthropic', 'kind': 'subscription',
                                 'clients': ['claude'], 'default': False, 'expected_identity': None})
        (self.tmp / 'state/registry.json').write_text(json.dumps(data))
        self.signed('anthropic-work', 'claude')
        result = registry.resolve(registry.load(), 'anthropic', 'claude')
        self.assertEqual(result['account'], 'anthropic-work')

    def test_merge_keeps_recorded_identities(self):
        live = json.loads(registry.TEMPLATE.read_text())
        live['accounts'][0]['expected_identity'] = 'owner@example.invalid'
        merged = registry.merge(json.loads(registry.TEMPLATE.read_text()), live)
        self.assertEqual(merged['accounts'][0]['expected_identity'], 'owner@example.invalid')

    def test_merge_over_a_registry_without_billing_shows_pi_on_anthropic_as_metered(self):
        # The live registry on dev-server was written before billing existed; the next
        # merge must bring it in, and status must then say metered.
        live = json.loads(registry.TEMPLATE.read_text())
        for entry in live['accounts']:
            entry.pop('billing', None)
        merged = registry.merge(json.loads(registry.TEMPLATE.read_text()), live)
        rows = {(r['account'], r['client']): r['billing'] for r in registry.status(merged)}
        self.assertEqual(rows[('anthropic-bravo', 'pi')], 'metered')
        self.assertEqual(rows[('anthropic-alpha', 'pi')], 'metered')
        self.assertEqual(rows[('anthropic-bravo', 'claude')], 'subscription')
        self.assertEqual(rows[('openai-bravo', 'pi')], 'subscription')


class ResolverTest(Fake):
    def test_nothing_signed_in_stops_and_says_so(self):
        with self.assertRaisesRegex(registry.Refused, 'no anthropic account left'):
            registry.resolve(self.data, 'anthropic', 'claude', who='assistant')
        self.assertIn('no anthropic account left', (self.tmp / 'chat').read_text())

    def test_default_first_when_nothing_is_known(self):
        self.signed('anthropic-bravo', 'claude')
        self.signed('anthropic-alpha', 'claude')
        self.assertEqual(registry.resolve(self.data, 'anthropic', 'claude')['account'], 'anthropic-bravo')

    def test_most_remaining_observed_quota_wins(self):
        self.signed('openai-bravo', 'codex')
        self.signed('openai-alpha', 'codex')
        self.used('openai-bravo', 70)
        self.used('openai-alpha', 20)
        self.assertEqual(registry.resolve(self.data, 'openai', 'codex')['account'], 'openai-alpha')

    def test_known_remaining_ranks_before_unknown_and_unknown_is_not_zero(self):
        self.signed('openai-bravo', 'codex')
        self.signed('openai-alpha', 'codex')
        self.used('openai-bravo', 100)
        self.assertEqual(registry.resolve(self.data, 'openai', 'codex')['account'], 'openai-alpha')

    def test_an_expired_window_says_nothing(self):
        self.signed('anthropic-bravo', 'claude')
        self.used('anthropic-bravo', 100, resets_in=-60)
        self.assertEqual(registry.resolve(self.data, 'anthropic', 'claude')['account'], 'anthropic-bravo')

    def test_named_account_is_used_or_the_launch_fails(self):
        self.signed('anthropic-bravo', 'claude')
        self.signed('anthropic-alpha', 'claude')
        self.assertEqual(registry.resolve(self.data, 'anthropic', 'claude', 'anthropic-alpha')['account'], 'anthropic-alpha')
        self.used('anthropic-alpha', 100)
        with self.assertRaisesRegex(registry.Refused, 'never substituted'):
            registry.resolve(self.data, 'anthropic', 'claude', 'anthropic-alpha')
        with self.assertRaises(registry.Refused):
            registry.resolve(self.data, 'anthropic', 'claude', 'anthropic-work')

    def test_unverified_login_is_not_eligible(self):
        self.signed('anthropic-bravo', 'claude', verified=False)
        with self.assertRaises(registry.Refused):
            registry.resolve(self.data, 'anthropic', 'claude')

    def test_rotation_is_said_in_the_chat_and_recorded(self):
        self.signed('anthropic-bravo', 'claude')
        self.signed('anthropic-alpha', 'claude')
        self.assertEqual(registry.resolve(self.data, 'anthropic', 'claude', who='assistant')['account'], 'anthropic-bravo')
        self.used('anthropic-bravo', 100)
        result = registry.resolve(self.data, 'anthropic', 'claude', who='assistant')
        self.assertEqual((result['account'], result['rotated_from']), ('anthropic-alpha', 'anthropic-bravo'))
        chat = (self.tmp / 'chat').read_text()
        self.assertIn('assistant switched anthropic account for claude: anthropic-bravo -> anthropic-alpha', chat)
        self.assertIn('anthropic-bravo exhausted', chat)
        self.assertIn('anthropic-bravo -> anthropic-alpha', (self.tmp / 'state/rotations.log').read_text())
        # the same choice again is not a switch
        registry.resolve(self.data, 'anthropic', 'claude', who='assistant')
        self.assertEqual((self.tmp / 'chat').read_text().count('switched'), 1)

    def test_a_subscription_is_never_replaced_by_an_api_key(self):
        data = json.loads(registry.TEMPLATE.read_text())
        data['accounts'].append({'id': 'anthropic-api', 'provider': 'anthropic', 'kind': 'api-key',
                                 'clients': ['claude'], 'default': False, 'expected_identity': None})
        (self.tmp / 'state/registry.json').write_text(json.dumps(data))
        self.signed('anthropic-api', 'key')
        self.signed('anthropic-bravo', 'claude')
        self.used('anthropic-bravo', 100)
        with self.assertRaises(registry.Refused):
            registry.resolve(registry.load(), 'anthropic', 'claude')

    def test_api_key_account_resolves_through_its_one_key_when_named_and_confirmed(self):
        self.signed('openrouter', 'key', identity='key sha256:abc')
        self.assertEqual(registry.resolve(self.data, 'openrouter', 'pi', 'openrouter', metered_ok=True)['account'],
                         'openrouter')

    # The owner's launch model (decision 2026-10-05): billing per account and client.

    def test_billing_is_per_account_and_client(self):
        gmail = registry.get(self.data, 'anthropic-bravo')
        self.assertEqual((registry.billing(gmail, 'claude'), registry.billing(gmail, 'pi')), ('subscription', 'metered'))
        openai = registry.get(self.data, 'openai-bravo')
        self.assertEqual((registry.billing(openai, 'codex'), registry.billing(openai, 'pi')), ('subscription', 'subscription'))
        self.assertEqual(registry.billing(registry.get(self.data, 'openrouter'), 'pi'), 'metered')
        self.assertEqual(registry.billing(registry.get(self.data, 'zai'), 'pi'), 'metered')
        self.assertEqual(registry.billing(registry.get(self.data, 'local'), 'local'), 'free')

    def test_rotation_never_picks_pi_on_anthropic(self):
        self.signed('anthropic-bravo', 'pi')
        self.signed('anthropic-alpha', 'pi')
        with self.assertRaisesRegex(registry.Refused, 'metered API cost: never chosen for you'):
            registry.resolve(self.data, 'anthropic', 'pi', who='assistant')

    def test_a_metered_launch_without_confirmation_is_refused(self):
        self.signed('anthropic-bravo', 'pi')
        self.signed('openrouter', 'key', identity='key sha256:abc')
        for provider, account in (('anthropic', 'anthropic-bravo'), ('openrouter', 'openrouter')):
            with self.assertRaisesRegex(registry.Refused, 'only after a yes for this launch'):
                registry.resolve(self.data, provider, 'pi', account)
        result = registry.resolve(self.data, 'anthropic', 'pi', 'anthropic-bravo', metered_ok=True)
        self.assertEqual((result['account'], result['reason']), ('anthropic-bravo', 'named, metered, confirmed for this launch'))

    def test_metered_is_never_chosen_unnamed_even_when_confirmed(self):
        self.signed('openrouter', 'key', identity='key sha256:abc')
        with self.assertRaises(registry.Refused):
            registry.resolve(self.data, 'openrouter', 'pi', metered_ok=True)

    def test_rotation_stays_within_the_subscription(self):
        # Pi on OpenAI is the plan: it rotates between the two OpenAI accounts and nowhere else.
        self.signed('openai-bravo', 'pi')
        self.signed('openai-alpha', 'pi')
        self.used('openai-bravo', 100)
        result = registry.resolve(self.data, 'openai', 'pi', who='ops')
        self.assertEqual(result['account'], 'openai-alpha')
        self.assertTrue(all(r['billing'] == 'subscription' for r in result['candidates']))

    def test_the_local_model_is_free_and_needs_no_login(self):
        result = registry.resolve(self.data, 'local', 'local')
        self.assertEqual(result['account'], 'local')
        row = next(r for r in registry.status(self.data) if r['account'] == 'local')
        self.assertEqual((row['billing'], row['verified']), ('free', True))

    def test_options_list_harness_first_with_billing(self):
        self.signed('anthropic-bravo', 'claude')
        options = registry.options(self.data)
        self.assertEqual([o['harness'] for o in options], ['claude', 'codex', 'pi', 'local'])
        pi = {(r['account'], r['billing']) for r in next(o for o in options if o['harness'] == 'pi')['accounts']}
        self.assertIn(('anthropic-bravo', 'metered'), pi)
        self.assertIn(('openai-bravo', 'subscription'), pi)
        self.assertIn(('openrouter', 'metered'), pi)
        self.assertIn('BILLING', registry.table(registry.status(self.data)))

    def test_status_table_shows_identity_verification_and_quota_age(self):
        self.signed('anthropic-bravo', 'claude')
        self.used('anthropic-bravo', 42)
        text = registry.table(registry.status(self.data))
        self.assertIn('owner@example.invalid', text)
        self.assertRegex(text, r'5h 42% until \d\d:\d\d, read 0m ago')
        self.assertIn('not signed in', text)

    def test_cli_resolve_and_old_selected_verb(self):
        self.signed('anthropic-bravo', 'claude')
        with mock.patch('sys.stdout', new=io.StringIO()) as out:
            self.assertEqual(accounts.main(['resolve', '--client', 'claude']), 0)
            self.assertEqual(accounts.main(['selected']), 0)
        self.assertEqual(out.getvalue().splitlines()[0], 'anthropic-bravo')
        self.assertIn('"selected": "anthropic-bravo"', out.getvalue())

    def test_usage_view_reads_the_one_record(self):
        self.signed('openai-bravo', 'codex')
        self.used('openai-bravo', 30)
        rows = {r['account']: r for r in usage.unified_view()['accounts']}
        self.assertEqual(rows['openai-bravo']['state'], 'ready')
        self.assertEqual(rows['openai-bravo']['remaining_percent'], 70.0)
        self.assertEqual(rows['openai-alpha']['state'], 'unverified')
        self.assertIsNone(rows['anthropic-bravo']['remaining_percent'])


if __name__ == '__main__':
    unittest.main()
