"""Jackett password-only dashboard/API adapter for the pinned reference image."""
import json
import http.cookiejar
import subprocess
import urllib.request
import uuid

from .arr import AppAPIError, DockerHTTP
from .credentials import validate_credentials
from .hosthttp import HostHTTP, NoRedirect

VERSION = '0.24.2949'


class JackettHTTP(DockerHTTP):
    def session_request(self, credentials, method, path, data=None):
        validate_credentials(credentials)
        cookie = '/tmp/installarr-session-' + uuid.uuid4().hex
        try:
            self.request('POST', '/UI/Dashboard', authenticated=False,
                         form={'password': credentials['password']}, cookie=cookie, save_cookie=True)
            return self.request(method, path, data=data, authenticated=False, cookie=cookie)
        finally:
            result = subprocess.run(['docker', '--host', self.socket, 'exec', self.container,
                                     'rm', '--force', '--', cookie], capture_output=True, timeout=15)
            if result.returncode:
                raise AppAPIError('Jackett session cleanup failed')


class JackettHostHTTP(HostHTTP):
    def session_request(self, credentials, method, path, data=None):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                             urllib.request.HTTPCookieProcessor(jar))
        self.request('POST', '/UI/Dashboard', authenticated=False,
                     form={'password': credentials['password']}, opener=opener)
        return self.request(method, path, data=data, authenticated=False, opener=opener)


class JackettClient:
    def __init__(self, transport, credentials):
        validate_credentials(credentials)
        self.transport, self.credentials = transport, credentials

    def config(self):
        code, body = self.transport.session_request(self.credentials, 'GET', '/api/v2.0/server/Config')
        if code != 200:
            raise AppAPIError('Jackett authenticated configuration read failed')
        try:
            result = json.loads(body)
        except (ValueError, TypeError):
            raise AppAPIError('Invalid Jackett configuration JSON') from None
        if not isinstance(result, dict) or result.get('app_version', '').lstrip('v') != VERSION:
            raise AppAPIError('Untested Jackett runtime version; no write attempted')
        return result

    def configure_admin(self):
        self.config()  # Version check before any mutation.
        code, _ = self.transport.session_request(self.credentials, 'POST', '/api/v2.0/server/AdminPassword',
                                                 data=self.credentials['password'])
        if code != 204:
            raise AppAPIError('Jackett password update rejected')
        return self.verify_admin()

    def verify_admin(self, credentials=None):
        if credentials is not None and credentials != self.credentials:
            raise AppAPIError('Jackett shared credentials differ')
        if not self.config().get('password'):
            raise AppAPIError('Jackett password readback missing')
        anonymous, _ = self.transport.request('GET', '/UI/Dashboard', authenticated=False)
        valid, _ = self.transport.session_request(self.credentials, 'GET', '/UI/Dashboard')
        password = self.credentials['password']
        wrong = dict(self.credentials, password=('A' if password[0] != 'A' else 'B') + password[1:])
        invalid, _ = self.transport.session_request(wrong, 'GET', '/UI/Dashboard')
        if anonymous not in (302, 401) or valid != 200 or invalid not in (302, 401):
            raise AppAPIError('Jackett GUI authentication/rejection failed')
        return {'anonymous': anonymous, 'valid': valid, 'invalid': invalid,
                'username_support': False, 'authentication': 'password-only'}
