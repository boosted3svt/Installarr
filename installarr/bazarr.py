"""Bazarr 1.6.2 API/auth reconciliation; no subtitle-provider credentials."""
import json

from .arr import AppAPIError
from .credentials import validate_credentials


VERSION = '1.6.2'


class BazarrClient:
    def __init__(self, transport):
        self.transport = transport

    def json(self, endpoint):
        code, body = self.transport.request('GET', '/api/' + endpoint)
        if code != 200:
            raise AppAPIError('Bazarr API read rejected (HTTP {})'.format(code))
        try:
            return json.loads(body)
        except (ValueError, TypeError):
            raise AppAPIError('Invalid Bazarr JSON') from None

    def status(self):
        result = self.json('system/status').get('data', {})
        if result.get('bazarr_version', '').lstrip('v') != VERSION:
            raise AppAPIError('Untested Bazarr version; no write attempted')
        return result

    def settings(self):
        value = self.json('system/settings')
        if not isinstance(value, dict) or not {'auth', 'general', 'sonarr', 'radarr'} <= set(value):
            raise AppAPIError('Unsupported Bazarr settings schema')
        return value

    def update(self, values):
        self.status()
        existing = self.settings()
        for section, fields in values.items():
            if section not in existing or not isinstance(fields, dict) or set(fields) - set(existing[section]):
                raise AppAPIError('Unknown Bazarr setting; no write attempted')
        form = {'settings-' + section + '-' + key: str(value).lower() if type(value) is bool else value
                for section, fields in values.items() for key, value in fields.items()}
        code, _ = self.transport.request('POST', '/api/system/settings', form=form)
        if code != 204:
            raise AppAPIError('Bazarr settings write rejected (HTTP {})'.format(code))
        saved = self.settings()
        for section, fields in values.items():
            for key, value in fields.items():
                if section == 'auth' and key == 'password':
                    continue  # Verify the actual password through HTTP below.
                # Bazarr's own URL builder strips the trailing root slash in memory.
                if key == 'base_url' and value == '/' and saved[section].get(key) == '':
                    continue
                if saved[section].get(key) != value:
                    raise AppAPIError('Bazarr setting readback differs: ' + section + '.' + key)

    def configure_admin(self, credentials):
        validate_credentials(credentials)
        if ':' in credentials['username']:
            raise AppAPIError('Bazarr Basic-auth username cannot contain a colon')
        self.update({'auth': {'type': 'basic', 'username': credentials['username'], 'password': credentials['password']}})
        return self.verify_admin(credentials)

    def verify_admin(self, credentials):
        validate_credentials(credentials)
        auth = self.settings()['auth']
        if auth.get('type') != 'basic' or auth.get('username') != credentials['username']:
            raise AppAPIError('Bazarr authentication settings differ')
        wrong = dict(credentials, password=('A' if credentials['password'][0] != 'A' else 'B') + credentials['password'][1:])
        statuses = [self.transport.request('GET', '/', authenticated=False, basic=value)[0]
                    for value in (None, credentials, wrong)]
        if statuses != [401, 200, 401]:
            raise AppAPIError('Bazarr GUI authentication/rejection failed')
        code, _ = self.transport.request('GET', '/api/system/settings', authenticated=False)
        if code != 401:
            raise AppAPIError('Bazarr anonymous API access was not rejected')
        return {'anonymous': 401, 'valid': 200, 'invalid': 401, 'anonymous_api': code}

    def connect_arr(self, app, api_key, expected_version):
        if app not in ('radarr', 'sonarr'):
            raise AppAPIError('Unsupported Bazarr integration')
        port = 7878 if app == 'radarr' else 8989
        current = self.settings()[app]
        if current.get('apikey') and (current.get('ip') != app or current.get('apikey') != api_key):
            raise AppAPIError('Existing Bazarr integration differs; preserved')
        self.update({app: {'ip': app, 'port': port, 'base_url': '/', 'ssl': False, 'apikey': api_key},
                     'general': {'use_' + app: True}})
        # This is Bazarr's own remote API/version lookup, not a host-side ping.
        if self.status().get(app + '_version') != expected_version:
            raise AppAPIError('Bazarr could not verify the selected application connection')
        return {'host': app, 'port': port, 'remote_version': expected_version, 'connection': 'verified'}

    def configure_english_subtitles(self):
        """Create/read back standard English; preserve profiles and existing media."""
        self.status()
        profiles = self.json('system/languages/profiles')
        languages = self.json('system/languages')
        if (not isinstance(profiles, list) or not isinstance(languages, list)
                or any(type(row.get('profileId')) is not int or row['profileId'] <= 0 for row in profiles)
                or len({row['profileId'] for row in profiles}) != len(profiles)):
            raise AppAPIError('Unsupported Bazarr language profile schema')
        english = [row for row in languages if row.get('code2') == 'en']
        if len(english) != 1:
            raise AppAPIError('Bazarr English language unavailable')
        matches = [row for row in profiles if row.get('name') == 'English']
        if len(matches) > 1:
            raise AppAPIError('Duplicate English subtitle profiles preserved')
        identity = matches[0]['profileId'] if matches else max([row['profileId'] for row in profiles] + [0]) + 1
        desired = {'profileId': identity, 'name': 'English', 'cutoff': 1,
                   'items': [{'id': 1, 'language': 'en', 'audio_exclude': 'False',
                              'audio_only_include': 'False', 'hi': 'False', 'forced': 'False'}],
                   'mustContain': [], 'mustNotContain': [], 'originalFormat': 0, 'tag': None}
        if matches and any(matches[0].get(key) != value for key, value in desired.items()):
            raise AppAPIError('Existing English subtitle profile differs; preserved')
        general = self.settings()['general']
        defaults = {}
        for kind in ('movie', 'serie'):
            enabled, profile = kind + '_default_enabled', kind + '_default_profile'
            if enabled not in general or profile not in general:
                raise AppAPIError('Bazarr default language profile settings unavailable')
            if general[enabled] and str(general[profile]) != str(identity):
                raise AppAPIError('Existing Bazarr subtitle defaults differ; preserved')
            defaults.update({enabled: True, profile: identity})
        form = {}
        if not english[0].get('enabled'):
            form['languages-enabled'] = sorted({row['code2'] for row in languages if row.get('enabled')} | {'en'})
        if not matches:
            # API consumes the entire collection, so retain every unrelated entry.
            if self.json('system/languages/profiles') != profiles:
                raise AppAPIError('Bazarr language profiles changed concurrently; preserved')
            form['languages-profiles'] = json.dumps(profiles + [desired])
        if form:
            code, _ = self.transport.request('POST', '/api/system/settings', form=form)
            if code != 204:
                raise AppAPIError('Bazarr English profile save rejected')
        saved = [row for row in self.json('system/languages/profiles') if row.get('profileId') == identity]
        if len(saved) != 1 or any(saved[0].get(key) != value for key, value in desired.items()):
            raise AppAPIError('Bazarr English subtitle profile readback differs')
        if not any(row.get('code2') == 'en' and row.get('enabled') for row in self.json('system/languages')):
            raise AppAPIError('Bazarr enabled-language readback differs')
        if any(general.get(key) != value for key, value in defaults.items()):
            self.update({'general': defaults})
        return {'profile_id': identity, 'language': 'en', 'forced': False, 'hearing_impaired': False,
                'defaults_for_new': ['movies', 'series'], 'existing_media_assignments': 'preserved'}
