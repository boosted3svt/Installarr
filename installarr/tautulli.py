"""Tautulli 2.18.2 protected first-start and real form-login verification.

Plex authorization is separate. Authentication groundwork does not establish a
working Plex integration or completed first-run setup.
"""
from .atomic import publish_noreplace
import base64
import configparser
import hashlib
import hmac
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import uuid
import urllib.request

from .arr import AppAPIError, DockerHTTP
from .credentials import validate_credentials
from .hosthttp import HostHTTP, NoRedirect

VERSION = '2.18.2'
IMAGE = 'lscr.io/linuxserver/tautulli@sha256:c6a48416d16b26f254b000133d2d844c1905ee58ed0f44aad9bda66598d39988'


def password_hash(password):
    # Exact upstream lib/hashing_passwords.py encoding: the base64 salt itself
    # is the PBKDF2 salt, rather than its decoded bytes.
    salt = base64.b64encode(os.urandom(16))
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000, 24)
    return 'PBKDF2$sha256$600000$' + salt.decode() + '$' + base64.b64encode(key).decode()


def matches_password(password, encoded):
    try:
        algorithm, digest, cost, salt, key = encoded.split('$')
        if algorithm != 'PBKDF2' or digest != 'sha256' or cost != '600000':
            return False
        expected = base64.b64decode(key, validate=True)
        if len(expected) != 24:
            return False
        actual = hashlib.pbkdf2_hmac(digest, password.encode(), salt.encode(), int(cost), len(expected))
        return hmac.compare_digest(expected, actual)
    except (ValueError, TypeError):
        return False


def quote_scalar(value):
    for delimiter in ('"', "'", '"' * 3, "'" * 3):
        if delimiter not in value:
            return delimiter + value + delimiter
    raise AppAPIError('Tautulli username contains unsupported quote combinations')


def unquote_scalar(value):
    for delimiter in ('"' * 3, "'" * 3, '"', "'"):
        if value.startswith(delimiter) and value.endswith(delimiter):
            return value[len(delimiter):-len(delimiter)]
    return value


def initialize_config(directory, credentials, uid, gid):
    """Seed only an absent config; preserve existing settings and credentials.

    Call before starting the container. Existing configs are verified, never edited.
    The application will populate the remainder using its own defaults.
    """
    validate_credentials(credentials)
    directory = Path(directory)
    fd = os.open(str(directory), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (info.st_uid, info.st_gid) != (uid, gid):
            raise AppAPIError('Tautulli configuration directory ownership differs')
        try:
            handle = os.open('config.ini', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        except FileNotFoundError:
            handle = None
        if handle is not None:
            with os.fdopen(handle) as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (info.st_uid, info.st_gid) != (uid, gid):
                    raise AppAPIError('Unsafe existing Tautulli config preserved')
                config = configparser.ConfigParser(interpolation=None)
                config.read_file(source)
            auth = config['General']
            if (unquote_scalar(auth.get('http_username', '')) != credentials['username'] or
                    not matches_password(credentials['password'], auth.get('http_password', '')) or
                    auth.get('http_basic_auth') != '0' or auth.get('allow_guest_access') != '0' or
                    auth.get('http_plex_admin') != '0'):
                raise AppAPIError('Existing Tautulli authentication differs; preserved')
            return {'authentication_seed': 'retained', 'plex_authorization': 'separate'}
        # ConfigObj supports quoted and triple-quoted literal scalars.
        content = ('[General]\nhttp_username = ' + quote_scalar(credentials['username']) +
            '\nhttp_password = ' + password_hash(credentials['password']) +
            '\nhttp_hash_password = 1\nhttp_hashed_password = 1\nhttp_basic_auth = 0\n'
            'http_plex_admin = 0\nallow_guest_access = 0\napi_enabled = 1\napi_key = ' + secrets.token_hex(16) +
            '\nfirst_run_complete = 0\nlaunch_browser = 0\ncheck_github = 0\n'
            '[Advanced]\nconfig_version = 22\n')
        temporary = '.installarr-tautulli-' + uuid.uuid4().hex
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            with os.fdopen(handle, 'w') as target:
                target.write(content)
                target.flush()
                os.fchown(target.fileno(), uid, gid)
                os.fsync(target.fileno())
            publish_noreplace(temporary, 'config.ini', source_dir_fd=fd, target_dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=fd)
            except FileNotFoundError:
                pass
        return {'authentication_seed': 'created', 'plex_authorization': 'separate'}
    finally:
        os.close(fd)


class TautulliHTTP(DockerHTTP):
    def login(self, credentials):
        validate_credentials(credentials)
        cookie = '/tmp/installarr-session-' + uuid.uuid4().hex
        try:
            code, body = self.request('POST', '/auth/signin', form={**credentials, 'admin_login': '1'},
                                      cookie=cookie, save_cookie=True)
            gui, _ = self.request('GET', '/settings', authenticated=False, cookie=cookie)
            try:
                success = json.loads(body).get('status') == 'success'
            except ValueError:
                success = False
            return {'login': code, 'success': success, 'gui': gui}
        finally:
            result = subprocess.run(['docker', '--host', self.socket, 'exec', self.container, 'rm', '--force', '--', cookie],
                                    capture_output=True, timeout=15)
            if result.returncode:
                raise AppAPIError('Temporary Tautulli cookie cleanup failed')


class TautulliClient:
    def __init__(self, transport):
        self.transport = transport

    def call(self, command, **parameters):
        code, body = self.transport.request('GET', '/api/v2', query={'cmd': command, **parameters})
        try:
            result = json.loads(body)['response']
            if code == 200 and result['result'] == 'success':
                return result['data']
        except (ValueError, KeyError, TypeError):
            pass
        raise AppAPIError('Tautulli API request/readback failed')

    def status(self):
        result = self.call('get_tautulli_info')
        if result.get('tautulli_version', '').lstrip('v') != VERSION:
            raise AppAPIError('Untested Tautulli runtime version')
        return result

    def verify_plex(self, machine_identifier, version):
        self.status()
        rows = self.call('get_servers_info')
        if not isinstance(rows, list):
            raise AppAPIError('Tautulli Plex server response differs')
        matches = [row for row in rows if row.get('machine_identifier') == machine_identifier]
        if len(matches) != 1 or matches[0].get('version') != version:
            raise AppAPIError('Tautulli actual Plex identity/version lookup failed')
        return {'connection': 'verified', 'remote_version': version}

    def verify_admin(self, credentials):
        validate_credentials(credentials)
        self.status()
        settings = self.call('get_settings', key='General')
        if (str(settings.get('http_basic_auth')) not in ('0', 'False') or
                settings.get('http_username') != credentials['username'] or
                str(settings.get('allow_guest_access')) not in ('0', 'False') or
                str(settings.get('http_plex_admin')) not in ('0', 'False')):
            raise AppAPIError('Tautulli authentication readback differs')
        anonymous, _ = self.transport.request('GET', '/settings', authenticated=False)
        if anonymous not in (302, 303, 401):
            raise AppAPIError('Tautulli anonymous GUI not rejected (HTTP {})'.format(anonymous))
        anonymous_api, _ = self.transport.request('GET', '/api/v2', authenticated=False, query={'cmd': 'get_settings'})
        if anonymous_api != 401:
            raise AppAPIError('Tautulli anonymous API not rejected')
        good = self.transport.login(credentials)
        wrong = dict(credentials, password=('A' if credentials['password'][0] != 'A' else 'B') + credentials['password'][1:])
        bad = self.transport.login(wrong)
        if good != {'login': 200, 'success': True, 'gui': 200} or bad['login'] != 401 or bad['success'] or bad['gui'] not in (302, 303, 401):
            raise AppAPIError('Tautulli real GUI login/rejection failed')
        return {'anonymous_gui': anonymous, 'anonymous_api': anonymous_api, 'valid_login': good, 'invalid_login': bad}


class TautulliHostHTTP(HostHTTP):
    def login(self, credentials):
        validate_credentials(credentials)
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPCookieProcessor(jar))
        code, body = self.request('POST', '/auth/signin', form={**credentials, 'admin_login': '1'}, opener=opener)
        gui, _ = self.request('GET', '/settings', authenticated=False, opener=opener)
        try:
            success = json.loads(body).get('status') == 'success'
        except ValueError:
            success = False
        return {'login': code, 'success': success, 'gui': gui}


def configure_plex_offline(directory, token, machine_identifier, uid, gid):
    """Reconcile only the Plex link while Tautulli is stopped; retain a backup.

    The caller must first authorize the selected Plex server. Never replace a
    different configured server/account or alter other Tautulli settings.
    """
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', token) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', machine_identifier):
        raise AppAPIError('Invalid Plex connection identity')
    directory = Path(directory)
    fd = os.open(str(directory), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = None
    try:
        source_fd = os.open('config.ini', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(source_fd) as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (info.st_uid, info.st_gid) != (uid, gid):
                raise AppAPIError('Unsafe Tautulli connection config preserved')
            original = source.read(1048577)
        if len(original) > 1048576:
            raise AppAPIError('Tautulli configuration is oversized')
        parsed = configparser.ConfigParser(interpolation=None)
        parsed.read_string(original)
        current = parsed['PMS'] if parsed.has_section('PMS') else {}
        existing_token = unquote_scalar(current.get('pms_token', ''))
        existing_id = unquote_scalar(current.get('pms_identifier', ''))
        if (existing_token and existing_token != token) or (existing_id and existing_id != machine_identifier):
            raise AppAPIError('Existing Tautulli Plex server differs; preserved')
        desired = {'PMS': {'pms_ip': 'plex', 'pms_port': '32400', 'pms_token': token,
            'pms_identifier': machine_identifier, 'pms_ssl': '0', 'pms_url': 'http://plex:32400',
            'pms_url_manual': '1', 'pms_is_remote': '0', 'pms_logs_folder': '/plexlogs'}, 'General': {'first_run_complete': '1'}}
        if all(parsed.has_section(section) and all(unquote_scalar(parsed[section].get(key, '')) == value
               for key, value in values.items()) for section, values in desired.items()):
            return {'plex_connection': 'retained'}
        # Preserve the exact text of unrelated fields, lists and comments.
        pending = {section: dict(values) for section, values in desired.items()}
        section, lines = None, []
        for line in original.splitlines():
            heading = re.fullmatch(r'\s*\[([^\]]+)\]\s*', line)
            if heading:
                if section in pending:
                    lines.extend(key + ' = ' + value for key, value in pending.pop(section).items())
                section = heading.group(1)
            field = re.match(r'\s*([a-z_]+)\s*=', line)
            if section in pending and field and field.group(1) in pending[section]:
                key = field.group(1)
                line = key + ' = ' + pending[section].pop(key)
            lines.append(line)
        if section in pending:
            lines.extend(key + ' = ' + value for key, value in pending.pop(section).items())
        for section, values in pending.items():
            lines.append('[' + section + ']')
            lines.extend(key + ' = ' + value for key, value in values.items())
        backup = '.installarr-before-plex-' + hashlib.sha256(original.encode()).hexdigest() + '.ini'
        try:
            backup_fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        except FileExistsError:
            backup_fd = os.open(backup, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(backup_fd) as source:
                info = os.fstat(source.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                        or (info.st_uid, info.st_gid) != (uid, gid) or source.read(1048577) != original):
                    raise AppAPIError('Existing Tautulli backup conflict preserved')
        else:
            with os.fdopen(backup_fd, 'w') as target:
                target.write(original)
                target.flush()
                os.fchown(target.fileno(), uid, gid)
                os.fsync(target.fileno())
        temporary = '.installarr-plex-link-' + uuid.uuid4().hex
        target_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(target_fd, 'w') as target:
            target.write('\n'.join(lines) + '\n')
            target.flush()
            os.fchown(target.fileno(), uid, gid)
            os.fsync(target.fileno())
        os.replace(temporary, 'config.ini', src_dir_fd=fd, dst_dir_fd=fd)
        temporary = None
        os.fsync(fd)
        return {'plex_connection': 'configured', 'backup': 'retained privately'}
    finally:
        if temporary is not None:
            os.unlink(temporary, dir_fd=fd)
        os.close(fd)
