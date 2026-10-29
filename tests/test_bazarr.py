import copy
import json
import unittest

from installarr.arr import AppAPIError
from installarr.bazarr import BazarrClient


class Transport:
    def __init__(self):
        self.version = '1.6.2'
        self.saved = {'auth': {'type': None, 'username': '', 'password': ''},
                      'general': {'use_radarr': False}, 'sonarr': {},
                      'radarr': {'ip': '127.0.0.1', 'port': 7878, 'base_url': '/', 'ssl': False, 'apikey': ''}}
        self.posts = 0
        self.drop_write = False

    def request(self, method, path, authenticated=True, form=None, basic=None):
        if path == '/':
            allowed = self.saved['auth']['type'] is None or basic == {
                'username': self.saved['auth']['username'], 'password': self.saved['auth']['password']}
            return (200 if allowed else 401), ''
        if not authenticated:
            return 401, ''
        if path == '/api/system/status':
            return 200, json.dumps({'data': {'bazarr_version': self.version, 'radarr_version': '6.4.4.10685'}})
        if method == 'POST':
            self.posts += 1
            if not self.drop_write:
                for field, value in form.items():
                    _, section, key = field.split('-', 2)
                    self.saved[section][key] = {'true': True, 'false': False}.get(value, value) if isinstance(value, str) else value
            return 204, ''
        return 200, json.dumps(self.saved)


class BazarrTests(unittest.TestCase):
    def test_real_auth_acceptance_and_connection_readback_required(self):
        transport = Transport()
        client = BazarrClient(transport)
        credentials = {'username': 'admin', 'password': 'test-password'}
        self.assertEqual(client.configure_admin(credentials)['invalid'], 401)
        link = client.connect_arr('radarr', 'a' * 32, '6.4.4.10685')
        self.assertEqual(link['connection'], 'verified')
        client.connect_arr('radarr', 'a' * 32, '6.4.4.10685')
        with self.assertRaises(AppAPIError):
            client.connect_arr('radarr', 'b' * 32, '6.4.4.10685')

    def test_untested_version_unknown_schema_and_failed_readback_refuse(self):
        transport = Transport()
        client = BazarrClient(transport)
        transport.version = '99.0'
        with self.assertRaises(AppAPIError):
            client.update({'auth': {'type': 'basic'}})
        self.assertEqual(transport.posts, 0)
        transport.version = '1.6.2'
        with self.assertRaises(AppAPIError):
            client.update({'auth': {'unknown': True}})
        self.assertEqual(transport.posts, 0)
        transport.drop_write = True
        with self.assertRaises(AppAPIError):
            client.update({'auth': {'type': 'basic'}})

    def test_accepted_setting_is_not_proof_of_valid_password(self):
        transport = Transport()
        client = BazarrClient(transport)
        credentials = {'username': 'admin', 'password': 'test-password'}
        client.configure_admin(credentials)
        with self.assertRaises(AppAPIError):
            client.verify_admin(dict(credentials, password='wrong-password'))

class LanguageClient(BazarrClient):
    def __init__(self):
        import copy
        self.transport = self
        self.posts = []
        self.profiles = [{'profileId': 41, 'name': 'Existing French', 'items': [], 'cutoff': None,
                          'mustContain': [], 'mustNotContain': [], 'originalFormat': None, 'tag': None}]
        self.languages = [{'code2': 'en', 'enabled': False}, {'code2': 'fr', 'enabled': True}]
        self.general = {'movie_default_enabled': False, 'movie_default_profile': '',
                        'serie_default_enabled': False, 'serie_default_profile': ''}
    def status(self):
        return {'bazarr_version': '1.6.2'}
    def settings(self):
        import copy
        return {'general': copy.deepcopy(self.general)}
    def json(self, endpoint):
        import copy
        return copy.deepcopy(self.profiles if endpoint.endswith('/profiles') else self.languages)
    def request(self, method, path, form=None):
        import json
        self.posts.append((method, path, form))
        if 'languages-profiles' in form:
            self.profiles = json.loads(form['languages-profiles'])
        if 'languages-enabled' in form:
            for row in self.languages:
                row['enabled'] = row['code2'] in form['languages-enabled']
        return 204, ''
    def update(self, values):
        self.posts.append(('settings', values))
        self.general.update(values['general'])


class SubtitleLanguageTests(unittest.TestCase):
    def test_dynamic_id_preserves_other_profiles_languages_and_rerun(self):
        import copy
        client = LanguageClient()
        original = copy.deepcopy(client.profiles[0])
        result = client.configure_english_subtitles()
        self.assertEqual(result['profile_id'], 42)
        self.assertEqual(client.profiles[0], original)
        self.assertTrue(all(row['enabled'] for row in client.languages))
        self.assertFalse(result['forced'])
        self.assertFalse(result['hearing_impaired'])
        self.assertEqual(client.general['movie_default_profile'], 42)
        count = len(client.posts)
        self.assertEqual(client.configure_english_subtitles(), result)
        self.assertEqual(len(client.posts), count)

    def test_existing_default_or_english_profile_conflicts_preserved_before_writes(self):
        from installarr.arr import AppAPIError
        for conflict in ('default', 'profile'):
            client = LanguageClient()
            if conflict == 'default':
                client.general.update(movie_default_enabled=True, movie_default_profile=99)
            else:
                client.profiles[0]['name'] = 'English'
            with self.assertRaises(AppAPIError):
                client.configure_english_subtitles()
            self.assertEqual(client.posts, [])
