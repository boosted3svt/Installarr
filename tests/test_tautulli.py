import json
import os
from pathlib import Path
import tempfile
import unittest

from installarr.arr import AppAPIError
from installarr.tautulli import initialize_config, matches_password, password_hash, TautulliClient


CREDENTIALS = {'username': 'admin', 'password': 'test-only-synthetic-password'}


class Transport:
    def __init__(self, accept_wrong=False, version='v2.18.2'):
        self.accept_wrong, self.version = accept_wrong, version

    def request(self, method, path, authenticated=True, query=None):
        if not authenticated:
            return (401, '') if path == '/api/v2' else (302, '')
        data = ({'tautulli_version': self.version} if query['cmd'] == 'get_tautulli_info' else
                {'http_username': 'admin', 'http_basic_auth': 0, 'allow_guest_access': 0, 'http_plex_admin': 0})
        return 200, json.dumps({'response': {'result': 'success', 'data': data}})

    def login(self, credentials):
        good = credentials == CREDENTIALS or self.accept_wrong
        return {'login': 200 if good else 401, 'success': good, 'gui': 200 if good else 302}


class TautulliTests(unittest.TestCase):
    def test_upstream_hash_format_and_wrong_password(self):
        hashed = password_hash(CREDENTIALS['password'])
        self.assertTrue(matches_password(CREDENTIALS['password'], hashed))
        self.assertFalse(matches_password('wrong', hashed))
        self.assertFalse(matches_password('wrong', 'invalid'))

    def test_seed_is_private_and_does_not_replace_existing_or_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            initialize_config(directory, CREDENTIALS, os.getuid(), os.getgid())
            path = Path(directory) / 'config.ini'
            original = path.read_bytes()
            self.assertEqual(initialize_config(directory, CREDENTIALS, os.getuid(), os.getgid())['authentication_seed'], 'retained')
            self.assertNotIn(CREDENTIALS['password'].encode(), original)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(AppAPIError):
                initialize_config(directory, dict(CREDENTIALS, password='different'), os.getuid(), os.getgid())
            self.assertEqual(path.read_bytes(), original)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'operator.ini'
            target.write_text('preserve')
            (Path(directory) / 'config.ini').symlink_to(target)
            with self.assertRaises(OSError):
                initialize_config(directory, CREDENTIALS, os.getuid(), os.getgid())
            self.assertEqual(target.read_text(), 'preserve')

    def test_authentication_checks_real_rejection_and_runtime_version(self):
        self.assertEqual(TautulliClient(Transport()).verify_admin(CREDENTIALS)['anonymous_api'], 401)
        for transport in (Transport(accept_wrong=True), Transport(version='v0.0.1')):
            with self.assertRaises(AppAPIError):
                TautulliClient(transport).verify_admin(CREDENTIALS)

    def test_offline_plex_link_preserves_unrelated_settings_and_refuses_other_account(self):
        from installarr.tautulli import configure_plex_offline
        with tempfile.TemporaryDirectory() as directory:
            initialize_config(directory, CREDENTIALS, os.getuid(), os.getgid())
            path = Path(directory) / 'config.ini'
            with path.open('a') as output:
                output.write('[PMS]\npms_token = \npms_identifier = \npms_uuid = operator-tautulli-uuid\n[Other]\noperator_value = preserve, exact\n')
            original = path.read_bytes()
            token, identifier = 'synthetic-plex-token-1234', 'test-machine-identifier-1234'
            configure_plex_offline(directory, token, identifier, os.getuid(), os.getgid())
            self.assertIn('operator_value = preserve, exact', path.read_text())
            self.assertIn('pms_uuid = operator-tautulli-uuid', path.read_text())
            backups = list(Path(directory).glob('.installarr-before-plex-*.ini'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            self.assertEqual(configure_plex_offline(directory, token, identifier, os.getuid(), os.getgid())['plex_connection'], 'retained')
            changed = path.read_bytes()
            with self.assertRaises(AppAPIError):
                configure_plex_offline(directory, 'other-plex-token-1234', identifier, os.getuid(), os.getgid())
            self.assertEqual(path.read_bytes(), changed)
