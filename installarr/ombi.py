"""Ombi 4.53.10 local administrator bootstrap; family users remain Plex identities."""
import json
import re
import copy
from contextlib import contextmanager

from .arr import AppAPIError, DockerHTTP
from .credentials import validate_credentials
from .hosthttp import HostHTTP

VERSION = '4.53.10'
IMAGE = 'lscr.io/linuxserver/ombi@sha256:19d4f86713e7203d910b4aa431d7176e7a9a22f641beb1047da45aa989296509'


class OmbiHTTP(DockerHTTP):
    api_header = 'Authorization'

    def __init__(self, socket, container, port=3579, api_key=''):
        if socket != 'unix:///run/docker.sock' or port != 3579 or not re.fullmatch(r'[0-9a-f]{64}', container):
            raise AppAPIError('Invalid Ombi transport identity')
        self.socket, self.container, self.port, self.api_key = socket, container, port, api_key


class OmbiHostHTTP(HostHTTP):
    api_header = 'Authorization'


class OmbiClient:
    def __init__(self, transport):
        self.transport = transport

    def json(self, method, path, payload=None, authenticated=True):
        code, body = self.transport.request(method, path, data=payload, authenticated=authenticated)
        if code != 200:
            raise AppAPIError('Ombi request rejected (HTTP {})'.format(code))
        try:
            return json.loads(body)
        except (ValueError, TypeError):
            raise AppAPIError('Invalid Ombi JSON') from None

    def status(self):
        version = self.json('GET', '/api/v1/Status/info', authenticated=False)
        if version != VERSION:
            raise AppAPIError('Untested Ombi runtime version')
        return {'version': version}

    def token(self, credentials):
        validate_credentials(credentials)
        value = self.json('POST', '/api/v1/Token', {**credentials, 'rememberMe': False, 'usePlexOAuth': False}, authenticated=False)
        if not isinstance(value, dict) or not isinstance(value.get('access_token'), str) or not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', value['access_token']):
            raise AppAPIError('Unsupported Ombi login response')
        return value['access_token']

    @contextmanager
    def administrator(self, credentials):
        """Keep the short-lived bearer out of configuration, evidence and argv."""
        self.transport.api_key = 'Bearer ' + self.token(credentials)
        try:
            yield self
        finally:
            self.transport.api_key = ''

    @contextmanager
    def plex_identity(self, plex_token):
        """Authenticate an already-authorized Plex identity without a local password."""
        if not isinstance(plex_token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', plex_token):
            raise AppAPIError('Invalid authorized Plex token')
        self.status()
        value = self.json('POST', '/api/v1/Token/plextoken', {'plexToken': plex_token}, authenticated=False)
        if (not isinstance(value, dict) or not isinstance(value.get('access_token'), str)
                or not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', value['access_token'])):
            raise AppAPIError('Unsupported Ombi Plex login response')
        self.transport.api_key = 'Bearer ' + value['access_token']
        try:
            yield self
        finally:
            self.transport.api_key = ''

    def connect_arr(self, app, api_key, profile_id, root_id, root_path, host=None):
        """Test Ombi's remote lookups before saving; preserve conflicting setups."""
        if (app not in ('radarr', 'sonarr') or not isinstance(api_key, str)
                or not re.fullmatch(r'[a-fA-F0-9]{32}', api_key)
                or any(type(value) is not int or value <= 0 for value in (profile_id, root_id))
                or not isinstance(root_path, str) or not root_path.startswith('/data/')):
            raise AppAPIError('Invalid Ombi application selection')
        host = app if host is None else host
        if not isinstance(host, str):
            raise AppAPIError('Invalid explicit Ombi application address')
        if host != app:
            import ipaddress
            try:
                address = ipaddress.IPv4Address(host)
                if address.is_unspecified or address.is_multicast:
                    raise ValueError()
            except (ValueError, TypeError):
                raise AppAPIError('Invalid explicit Ombi application address') from None
        self.status()
        endpoint = '/api/v1/Settings/' + app
        saved = self.json('GET', endpoint)
        if not isinstance(saved, dict):
            raise AppAPIError('Unsupported Ombi application settings')
        current = saved.get('radarr') if app == 'radarr' else saved
        if not isinstance(current, dict) or (app == 'radarr' and not isinstance(saved.get('radarr4K'), dict)):
            raise AppAPIError('Unsupported Ombi application settings')
        desired = {'enabled': True, 'ip': host, 'port': 7878 if app == 'radarr' else 8989,
                   'ssl': False, 'subDir': '', 'apiKey': api_key, 'addOnly': False}
        # Ombi's movie sender takes the actual path; its TV sender resolves an ID.
        desired.update({'defaultQualityProfile': str(profile_id), 'defaultRootPath': root_path,
                        'minimumAvailability': 'released'} if app == 'radarr' else
                       {'qualityProfile': str(profile_id), 'rootPath': str(root_id), 'seasonFolders': True})
        if set(desired) - set(current):
            raise AppAPIError('Required Ombi application fields unavailable')
        if (current.get('enabled') or current.get('apiKey')) and any(
                current.get(key) != value for key, value in desired.items()):
            raise AppAPIError('Existing Ombi application integration differs; preserved')
        candidate = dict(current, **desired)
        remote = '/api/v1/' + app.capitalize()

        def check(profiles, roots):
            if not isinstance(profiles, list) or not isinstance(roots, list):
                raise AppAPIError('Ombi remote application lookup failed')
            selected = [row for row in profiles if row.get('id') == profile_id]
            folders = [row for row in roots if row.get('id') == root_id and row.get('path') == root_path]
            if len(selected) != 1 or len(folders) != 1:
                raise AppAPIError('Ombi remote profile/root readback differs')

        check(self.json('POST', remote + '/Profiles', candidate),
              self.json('POST', remote + '/RootFolders', candidate))
        if any(current.get(key) != value for key, value in desired.items()):
            payload = copy.deepcopy(saved)
            if app == 'radarr':
                payload['radarr'] = candidate  # Preserve independent 4K settings exactly.
            else:
                payload = candidate
            if self.json('POST', endpoint, payload) is not True:
                raise AppAPIError('Ombi application settings save refused')
        readback = self.json('GET', endpoint)
        actual = readback.get('radarr') if app == 'radarr' else readback
        if not isinstance(actual, dict) or any(actual.get(key) != value for key, value in desired.items()):
            raise AppAPIError('Ombi application settings readback differs')
        if app == 'radarr' and readback.get('radarr4K') != saved['radarr4K']:
            raise AppAPIError('Ombi independent 4K settings changed')
        check(self.json('GET', remote + '/Profiles'), self.json('GET', remote + '/RootFolders'))
        return {'host': host, 'profile_id': profile_id, 'root_id': root_id,
                'root_path': root_path, 'remote_lookups': 'verified', 'requests': 'not tested'}

    def connect_plex(self, token, machine_identifier, libraries, server_name):
        """Reconcile the selected server only; test through Ombi's Plex adapter."""
        self.status()
        if (not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', token)
                or not isinstance(machine_identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', machine_identifier)
                or not isinstance(server_name, str) or not server_name
                or not isinstance(libraries, list) or not libraries):
            raise AppAPIError('Invalid Ombi Plex selection')
        expected = []
        for item in libraries:
            if (not isinstance(item, dict) or not str(item.get('id', '')).isdigit()
                    or int(item['id']) <= 0 or not isinstance(item.get('name'), str)):
                raise AppAPIError('Invalid Ombi Plex library identity')
            expected.append({'key': int(item['id']), 'title': item['name'], 'enabled': True})
        if len({item['key'] for item in expected}) != len(expected):
            raise AppAPIError('Duplicate Ombi Plex library identity')
        endpoint = '/api/v1/Settings/plex'
        current = self.json('GET', endpoint)
        if not isinstance(current, dict) or not {'enable', 'servers', 'monitorAll'} <= set(current):
            raise AppAPIError('Unsupported Ombi Plex settings')
        servers = current.get('servers') or []
        if not isinstance(servers, list) or len(servers) > 1:
            raise AppAPIError('Existing Ombi Plex servers preserved')
        desired = {'name': server_name, 'ip': 'plex', 'port': 32400, 'ssl': False, 'subDir': '',
                   'plexAuthToken': token, 'machineIdentifier': machine_identifier,
                   'plexSelectedLibraries': expected}
        if servers and (not isinstance(servers[0], dict) or any(servers[0].get(key) != value for key, value in desired.items()
                           if key != 'plexSelectedLibraries')):
            raise AppAPIError('Existing Ombi Plex server differs; preserved')
        candidate = dict(servers[0] if servers else {'id': 1, 'episodeBatchSize': 1000,
                         'serverHostname': 'https://app.plex.tv'}, **desired)

        def check(server):
            result = self.json('POST', '/api/v1/Plex/Libraries', server)
            if not isinstance(result, dict) or result.get('successful') is not True:
                raise AppAPIError('Ombi remote Plex library lookup failed')
            rows = (result.get('data') or {}).get('mediaContainer', {}).get('directory')
            if not isinstance(rows, list):
                raise AppAPIError('Unsupported Ombi remote Plex library response')
            actual = {(str(row.get('key')), row.get('title')) for row in rows}
            if actual != {(str(row['key']), row['title']) for row in expected}:
                raise AppAPIError('Ombi remote Plex libraries differ')

        check(candidate)
        payload = dict(current, enable=True, monitorAll=False, servers=[candidate])
        if payload != current and self.json('POST', endpoint, payload) is not True:
            raise AppAPIError('Ombi Plex settings save refused')
        readback = self.json('GET', endpoint)
        if (not isinstance(readback, dict) or readback.get('enable') is not True or readback.get('monitorAll') is not False
                or readback.get('servers') != [candidate]):
            raise AppAPIError('Ombi Plex settings readback differs')
        check(readback['servers'][0])
        return {'host': 'plex', 'machine_identifier': machine_identifier,
                'library_ids': [row['key'] for row in expected], 'remote_libraries': 'verified',
                'content_sync_and_family': 'not tested'}

    def configure_admin(self, credentials):
        validate_credentials(credentials)
        self.status()
        wizard = self.json('GET', '/api/v1/Status/Wizard', authenticated=False)
        if not isinstance(wizard, dict) or wizard.get('result') is not False:
            raise AppAPIError('Existing Ombi setup preserved; expected credentials must work')
        result = self.json('POST', '/api/v1/Identity/Wizard', {**credentials, 'usePlexAdminAccount': False}, authenticated=False)
        if not isinstance(result, dict) or result.get('result') is not True:
            raise AppAPIError('Ombi administrator creation refused')
        return self.verify_admin(credentials)

    def verify_admin(self, credentials):
        validate_credentials(credentials)
        self.status()
        anonymous, _ = self.transport.request('GET', '/api/v1/Identity', authenticated=False)
        if anonymous != 401:
            raise AppAPIError('Ombi anonymous identity access not rejected')
        token = self.token(credentials)
        self.transport.api_key = 'Bearer ' + token
        try:
            user = self.json('GET', '/api/v1/Identity')
            if (not isinstance(user, dict) or user.get('userName') != credentials['username']
                    or not user.get('id') or not any(role.get('value') == 'Admin' and role.get('enabled') is True
                                                   for role in user.get('claims', []))):
                raise AppAPIError('Ombi authenticated administrator readback differs')
        finally:
            self.transport.api_key = ''
        wrong = dict(credentials, password=('A' if credentials['password'][0] != 'A' else 'B') + credentials['password'][1:])
        denied, _ = self.transport.request('POST', '/api/v1/Token', data={**wrong, 'usePlexOAuth': False}, authenticated=False)
        if denied != 401:
            raise AppAPIError('Ombi incorrect password not rejected')
        wizard = self.json('GET', '/api/v1/Status/Wizard', authenticated=False)
        if wizard.get('result') is not True:
            raise AppAPIError('Ombi completed wizard flag not retained')
        return {'anonymous_identity': anonymous, 'valid_login': 200, 'invalid_login': denied,
                'administrator_id': user['id'], 'wizard_complete': True}


def verify_admin_database(directory, uid, gid):
    """Host supervisor gate for the unpublished-to-published transition/reruns.

    Ombi's image has no SQLite CLI. Its existing root supervisor uses Python's
    read-only SQLite adapter instead of adding a service or tool to the image.
    """
    import os
    from pathlib import Path
    import sqlite3
    import stat
    from urllib.parse import quote
    database = Path(directory) / 'Ombi.db'
    if database.resolve() != database:
        raise AppAPIError('Ombi database path contains a symlink')
    info = database.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o022
            or (info.st_uid, info.st_gid) != (uid, gid)):
        raise AppAPIError('Unsafe Ombi database; publication refused')
    try:
        connection = sqlite3.connect('file:' + quote(str(database), safe='/') + '?mode=ro', uri=True, timeout=1)
        try:
            connection.execute('PRAGMA query_only=ON')
            count = connection.execute('''SELECT COUNT(*) FROM AspNetUsers u
                JOIN AspNetUserRoles ur ON ur.UserId = u.Id
                JOIN AspNetRoles r ON r.Id = ur.RoleId
                WHERE r.Name = 'Admin' AND u.UserType = 1
                  AND u.PasswordHash IS NOT NULL AND u.PasswordHash != '' ''').fetchone()[0]
            if count < 1:
                raise AppAPIError('Ombi administrator absent; publication refused')
        finally:
            connection.close()
    except sqlite3.Error:
        raise AppAPIError('Ombi administrator database could not be verified') from None
    return {'local_administrator': 'present'}
