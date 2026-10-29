import json
import unittest

from installarr.arr import AppAPIError
from installarr.ombi import OmbiClient

CREDENTIALS = {'username': 'admin', 'password': 'synthetic-only'}


class Transport:
    api_key = ''
    def __init__(self, wrong_accepted=False, version='4.53.10'):
        self.wrong_accepted, self.version = wrong_accepted, version
    def request(self, method, path, data=None, authenticated=True):
        if path.endswith('/info'):
            return 200, json.dumps(self.version)
        if path.endswith('/Wizard'):
            return 200, json.dumps({'result': True})
        if path.endswith('/Token'):
            if data['password'] != CREDENTIALS['password'] and not self.wrong_accepted:
                return 401, ''
            return 200, json.dumps({'access_token': 'part1.part2.part3'})
        if not authenticated or not self.api_key:
            return 401, ''
        return 200, json.dumps({'id': 'dynamic-admin-id', 'userName': 'admin', 'claims': [{'value': 'Admin', 'enabled': True}]})


class OmbiTests(unittest.TestCase):
    def test_login_checks_role_identity_anonymous_and_bad_password_and_clears_bearer(self):
        transport = Transport()
        result = OmbiClient(transport).verify_admin(CREDENTIALS)
        self.assertEqual(result['administrator_id'], 'dynamic-admin-id')
        self.assertEqual(result['invalid_login'], 401)
        self.assertEqual(transport.api_key, '')
        self.assertNotIn('part1', repr(result))
        for broken in (Transport(wrong_accepted=True), Transport(version='0.0.0')):
            with self.assertRaises(AppAPIError):
                OmbiClient(broken).verify_admin(CREDENTIALS)

    def test_completed_wizard_never_creates_another_admin(self):
        with self.assertRaises(AppAPIError):
            OmbiClient(Transport()).configure_admin(CREDENTIALS)

    def test_database_gate_rejects_reset_or_passwordless_admin(self):
        import os
        from pathlib import Path
        import sqlite3
        import tempfile
        from installarr.ombi import verify_admin_database
        with tempfile.TemporaryDirectory() as directory:
            connection = sqlite3.connect(str(Path(directory) / 'Ombi.db'))
            connection.executescript('''CREATE TABLE AspNetUsers (Id TEXT, UserType INTEGER, PasswordHash TEXT);
                CREATE TABLE AspNetRoles (Id TEXT, Name TEXT);
                CREATE TABLE AspNetUserRoles (UserId TEXT, RoleId TEXT);
                INSERT INTO AspNetRoles VALUES ('role', 'Admin');
                INSERT INTO AspNetUsers VALUES ('user', 1, '');
                INSERT INTO AspNetUserRoles VALUES ('user', 'role');''')
            connection.commit()
            with self.assertRaises(AppAPIError):
                verify_admin_database(directory, os.getuid(), os.getgid())
            connection.execute("UPDATE AspNetUsers SET PasswordHash = 'synthetic-nonempty-hash'")
            connection.commit()
            self.assertEqual(verify_admin_database(directory, os.getuid(), os.getgid())['local_administrator'], 'present')
            connection.execute('DELETE FROM AspNetUsers')
            connection.commit()
            with self.assertRaises(AppAPIError):
                verify_admin_database(directory, os.getuid(), os.getgid())
            connection.close()

class ArrTransport(Transport):
    def __init__(self, app='radarr', bad_root=False, conflict=False):
        super().__init__()
        self.app, self.bad_root, self.writes = app, bad_root, 0
        self.settings = {'enabled': False, 'ip': '', 'port': 0, 'ssl': False, 'subDir': '',
                         'apiKey': '', 'addOnly': False, 'untouched': 'keep'}
        self.settings.update({'defaultQualityProfile': '', 'defaultRootPath': '', 'minimumAvailability': ''}
                             if app == 'radarr' else {'qualityProfile': '', 'rootPath': '', 'seasonFolders': False})
        if conflict:
            self.settings.update(enabled=True, ip='operator-server')
        self.uhd = {'enabled': False, 'operatorSetting': 'preserved'}
    def request(self, method, path, data=None, authenticated=True):
        if '/Settings/' in path:
            if method == 'POST':
                self.writes += 1
                self.settings = data['radarr'] if self.app == 'radarr' else data
                return 200, 'true'
            return 200, json.dumps({'radarr': self.settings, 'radarr4K': self.uhd}
                                   if self.app == 'radarr' else self.settings)
        if path.endswith('/Profiles'):
            return 200, '[{"id": 17, "name": "preferred"}]'
        if path.endswith('/RootFolders'):
            return 200, json.dumps([{'id': 23, 'path': '/data/different' if self.bad_root else '/data/Movies'}])
        return super().request(method, path, data, authenticated)


class OmbiArrTests(unittest.TestCase):
    def test_dynamic_selection_reruns_preserve_4k_and_clear_bearer(self):
        for app in ('radarr', 'sonarr'):
            transport = ArrTransport(app)
            client = OmbiClient(transport)
            with client.administrator(CREDENTIALS):
                first = client.connect_arr(app, 'a' * 32, 17, 23, '/data/Movies')
                second = client.connect_arr(app, 'a' * 32, 17, 23, '/data/Movies')
            self.assertEqual(first, second)
            self.assertEqual(transport.writes, 1)
            self.assertEqual(transport.settings['untouched'], 'keep')
            self.assertEqual(transport.settings['defaultRootPath' if app == 'radarr' else 'rootPath'],
                             '/data/Movies' if app == 'radarr' else '23')
            self.assertEqual(transport.uhd, {'enabled': False, 'operatorSetting': 'preserved'})
            self.assertEqual(transport.api_key, '')
            self.assertNotIn('a' * 32, repr(first))

    def test_conflict_or_wrong_remote_root_refused_before_save_and_clears_token(self):
        for transport in (ArrTransport(conflict=True), ArrTransport(bad_root=True)):
            client = OmbiClient(transport)
            with self.assertRaises(AppAPIError):
                with client.administrator(CREDENTIALS):
                    client.connect_arr('radarr', 'a' * 32, 17, 23, '/data/Movies')
            self.assertEqual(transport.writes, 0)
            self.assertEqual(transport.api_key, '')

class PlexTransport(Transport):
    def __init__(self, bad_library=False, conflict=False):
        super().__init__()
        self.bad_library, self.writes = bad_library, 0
        self.settings = {'enable': False, 'monitorAll': True, 'servers': [], 'installId': 'preserve-install-id'}
        if conflict:
            self.settings['servers'] = [{'ip': 'operator-server'}]
    def request(self, method, path, data=None, authenticated=True):
        if path.endswith('/Settings/plex'):
            if method == 'POST':
                self.writes += 1
                self.settings = data
                return 200, 'true'
            return 200, json.dumps(self.settings)
        if path.endswith('/Plex/Libraries'):
            return 200, json.dumps({'successful': True, 'data': {'mediaContainer': {'directory': [
                {'key': '1', 'title': 'Other' if self.bad_library else 'Movies'}]}}})
        return super().request(method, path, data, authenticated)


class OmbiPlexTests(unittest.TestCase):
    def test_exact_selected_libraries_and_rerun(self):
        transport = PlexTransport()
        client = OmbiClient(transport)
        for _ in range(2):
            result = client.connect_plex('private-synthetic-token', 'test-machine', [{'id': 1, 'name': 'Movies'}], 'Test')
        self.assertEqual(transport.writes, 1)
        self.assertEqual(transport.settings['installId'], 'preserve-install-id')
        self.assertFalse(transport.settings['monitorAll'])
        self.assertEqual(result['library_ids'], [1])
        self.assertNotIn('private-synthetic-token', repr(result))

    def test_conflict_and_mismatched_remote_libraries_refuse_before_save(self):
        for transport in (PlexTransport(conflict=True), PlexTransport(bad_library=True)):
            with self.assertRaises(AppAPIError):
                OmbiClient(transport).connect_plex('private-synthetic-token', 'test-machine', [{'id': 1, 'name': 'Movies'}], 'Test')
            self.assertEqual(transport.writes, 0)

class PlexIdentityTests(unittest.TestCase):
    def test_native_plex_bearer_clears_on_error(self):
        class PlexLogin(Transport):
            def request(self, method, path, data=None, authenticated=True):
                if path.endswith('/plextoken'):
                    self.plex_payload = data
                    return 200, '{"access_token":"native.plex.jwt"}'
                return super().request(method, path, data, authenticated)
        transport = PlexLogin()
        with self.assertRaises(RuntimeError):
            with OmbiClient(transport).plex_identity('authorized-test-plex-token'):
                self.assertEqual(transport.api_key, 'Bearer native.plex.jwt')
                raise RuntimeError('injected request failure')
        self.assertEqual(transport.api_key, '')
        self.assertEqual(transport.plex_payload, {'plexToken': 'authorized-test-plex-token'})

    def test_explicit_lan_address_uses_remote_lookup_and_rejects_urls(self):
        transport = ArrTransport()
        result = OmbiClient(transport).connect_arr('radarr', 'a' * 32, 17, 23, '/data/Movies', host='10.70.0.99')
        self.assertEqual(result['host'], '10.70.0.99')
        for host in ('http://10.70.0.99', '0.0.0.0', '224.0.0.1', '10.70.0.99:7878', True, 1):
            with self.assertRaises(AppAPIError):
                OmbiClient(ArrTransport()).connect_arr('radarr', 'a' * 32, 17, 23, '/data/Movies', host=host)
