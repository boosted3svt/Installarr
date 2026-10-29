import json
import unittest

from installarr.arr import AppAPIError
from installarr.jackett import JackettClient


class Transport:
    def __init__(self):
        self.password = ''
        self.version = 'v0.24.2949'
        self.writes = 0
        self.accept_wrong_password = False

    def request(self, *args, **kwargs):
        return (302 if self.password else 200), ''

    def session_request(self, credentials, method, path, data=None):
        authorized = not self.password or credentials['password'] == self.password or self.accept_wrong_password
        if not authorized:
            return 302, ''
        if path.endswith('/Config'):
            return 200, json.dumps({'app_version': self.version, 'password': self.password[:10]})
        if method == 'POST':
            self.writes += 1
            self.password = data
            return 204, ''
        return 200, ''


class JackettTests(unittest.TestCase):
    def test_password_only_auth_requires_real_wrong_password_rejection(self):
        transport = Transport()
        client = JackettClient(transport, {'username': 'shared-admin', 'password': 'test-password'})
        evidence = client.configure_admin()
        self.assertFalse(evidence['username_support'])
        self.assertEqual(evidence['invalid'], 302)
        transport.accept_wrong_password = True
        with self.assertRaises(AppAPIError):
            client.verify_admin()

    def test_unknown_version_blocks_password_write(self):
        transport = Transport()
        transport.version = 'v99.0'
        with self.assertRaises(AppAPIError):
            JackettClient(transport, {'username': 'admin', 'password': 'test-password'}).configure_admin()
        self.assertEqual(transport.writes, 0)
