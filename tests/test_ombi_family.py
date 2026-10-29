import copy
from pathlib import Path
import tempfile
import unittest

from installarr.arr import AppAPIError
from installarr.execution import Execution
from installarr.ombi_family import FAMILY, configure_family, family_paths, import_family, import_family_once


class Client:
    def __init__(self, imported=False, unexpected=False):
        self.users, self.writes = {}, []
        self.preferences = {name: {'agent': 1, 'value': '', 'enabled': False} for name in FAMILY}
        self.unexpected = unexpected
        self.settings = {'id': 0, 'importPlexUsers': False, 'importPlexAdmin': False,
                         'cleanupPlexUsers': False, 'bannedPlexUserIds': [], 'defaultRoles': []}
        if imported:
            self.populate()
    def populate(self):
        roles = ['RequestMovie', 'RequestTv', 'AutoApproveMovie', 'AutoApproveTv', 'PowerUser']
        for name in FAMILY:
            self.users[name] = {'id': name, 'userName': name, 'userType': 2, 'emailAddress': 'private@example.invalid',
                'claims': [{'value': role, 'enabled': False} for role in roles],
                'userQualityProfiles': {'id': 0, 'userId': name, 'radarrRootPath': 0, 'radarrQualityProfile': 0,
                                        'sonarrRootPath': 0, 'sonarrQualityProfile': 0}}
        if self.unexpected:
            self.users['unexpected'] = {'id': 'unexpected', 'userName': 'unexpected', 'userType': 2}
    def json(self, method, path, payload=None):
        if method != 'GET':
            self.writes.append((method, path, copy.deepcopy(payload)))
        if path.endswith('/Identity/Users'):
            return copy.deepcopy(list(self.users.values()))
        if path.endswith('/Plex/friends'):
            return [{'id': str(i + 1), 'username': name} for i, name in enumerate(FAMILY + ('other-account',))]
        if path.endswith('/Settings/UserManagement'):
            if method == 'POST':
                self.settings = dict(copy.deepcopy(payload), id=3)
                return True
            return copy.deepcopy(self.settings)
        if path.endswith('/Job/plexuserimporter'):
            self.populate()
            return True
        if method == 'PUT' and path.endswith('/Identity'):
            self.users[payload['userName']] = copy.deepcopy(payload)
            return {'successful': True}
        if '/Identity/User/' in path:
            return copy.deepcopy(self.users[path.rsplit('/', 1)[1]])
        if '/notificationpreferences/' in path:
            return [copy.deepcopy(self.preferences[path.rsplit('/', 1)[1]])]
        if path.endswith('/Identity/NotificationPreferences'):
            for row in payload:
                self.preferences[row['userId']] = copy.deepcopy(row)
            return True
        raise AssertionError((method, path))


class FamilyTests(unittest.TestCase):
    def test_discord_targets_saved_read_back_disabled_and_reused_without_erasing(self):
        client = Client(imported=True)
        targets = {'lenora8': '123456789012345678', 'rebel739': '234567890123456789', 'beanie08': '345678901234567890'}
        result = configure_family(client, {name: {} for name in FAMILY}, targets)
        writes = len(client.writes)
        configure_family(client, {name: {} for name in FAMILY})
        self.assertEqual(len(client.writes), writes)
        for name in FAMILY:
            self.assertEqual(client.preferences[name]['value'], targets[name])
            self.assertIs(client.preferences[name]['enabled'], False)
            self.assertNotIn(targets[name], repr(result))

    def test_private_discord_collection_reuses_ids_without_reprompting(self):
        from installarr.ombi_family import initialize_family_preferences, read_family_preferences, validate_discord_targets
        with tempfile.TemporaryDirectory() as directory:
            values = {'lenora8': '123456789012345678'}
            result = initialize_family_preferences(Path(directory) / 'private', lambda: values)
            self.assertEqual(read_family_preferences(result['path']), values)
            self.assertEqual(Path(result['path']).stat().st_mode & 0o777, 0o600)
            self.assertEqual(initialize_family_preferences(Path(directory) / 'private', lambda: self.fail('must reuse'))['status'], 'reused')
            self.assertNotIn(values['lenora8'], repr(result))
            self.assertTrue(all(values['lenora8'] not in p.read_text() for p in Path(directory).rglob('state.json')))
        for value in ({'unknown': '123456789012345678'}, {'lenora8': 'not-an-id'}, {'lenora8': '99999999999999999999'}):
            with self.assertRaises(ValueError):
                validate_discord_targets(value)

    def test_native_selective_import_restores_defaults_and_excludes_others(self):
        client = Client()
        users = import_family_once(client, lambda action: action())
        self.assertEqual(set(users), set(FAMILY))
        temporary = next(payload for method, path, payload in client.writes if path.endswith('/UserManagement'))
        self.assertEqual(temporary['bannedPlexUserIds'], ['4'])
        self.assertEqual(temporary['defaultRoles'], [])
        self.assertFalse(client.settings['importPlexUsers'])
        self.assertFalse(client.settings['cleanupPlexUsers'])
        self.assertFalse(any('/Identity' in path for method, path, data in client.writes))

    def test_unexpected_import_or_local_lookalike_refuses_and_restores(self):
        client = Client(unexpected=True)
        with self.assertRaises(AppAPIError):
            import_family_once(client, lambda action: action())
        self.assertFalse(client.settings['importPlexUsers'])
        client = Client(imported=True)
        client.users['lenora8']['userType'] = 1
        with self.assertRaises(AppAPIError):
            configure_family(client, {name: {} for name in FAMILY})
        self.assertEqual(client.writes, [])

    def test_roles_dynamic_routes_inheritance_and_no_password_assignment(self):
        client = Client(imported=True)
        routes = {'lenora8': {'radarrRootPath': 41, 'radarrQualityProfile': 17},
                  'rebel739': {'radarrRootPath': 92, 'radarrQualityProfile': 17}, 'beanie08': {}}
        result = configure_family(client, routes)
        configure_family(client, routes)
        writes = [row for row in client.writes if row[1].endswith('/Identity')]
        self.assertEqual(len(writes), 3)
        self.assertTrue(all(row[2]['password'] is None for row in writes))
        self.assertEqual(result['lenora8']['routes']['radarrRootPath'], 41)
        self.assertTrue(result['beanie08']['power_user'])
        self.assertEqual(client.users['beanie08']['userQualityProfiles']['radarrRootPath'], 0)
        self.assertNotIn('private@example', repr(result))

    def test_interrupted_import_restores_journal_before_existing_identity_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'import'
            original = Client().settings
            with Execution(state, {'operation': 'ombi-family-import-v1', 'machine_identifier': 'test-server'}) as journal:
                journal.state['restore_settings'] = original
                journal._save()
            client = Client(imported=True)
            client.settings['importPlexUsers'] = True
            result = import_family(client, lambda action: action(), state, 'test-server')
            self.assertEqual(set(result), set(FAMILY))
            self.assertFalse(client.settings['importPlexUsers'])
            with Execution(state, {'operation': 'ombi-family-import-v1', 'machine_identifier': 'test-server'}) as journal:
                self.assertNotIn('restore_settings', journal.state)

    def test_shared_storage_paths_preserve_reference_spelling(self):
        config = {'apps': ['radarr', 'sonarr'], 'storage': {'media': '/data-root', 'downloads': '/data-root/downloads',
                  'incomplete': '/data-root/incomplete'}, 'data_root': '/data-root'}
        paths = family_paths(config)
        self.assertEqual(paths['lenora8']['radarr']['container_path'], '/data/lenoramovies')
        self.assertEqual(paths['rebel739']['sonarr']['host_path'], '/data-root/jeremytv')
        self.assertNotIn('beanie08', paths)

class FamilyConfigTests(unittest.TestCase):
    def test_opt_in_requires_plex_ombi_and_safe_family_profiles(self):
        from installarr.ombi_family import validate_family_config
        from installarr.profiles import recommended_profiles
        config = {'apps': ['ombi', 'plex', 'radarr'], 'ombi_family_presets': True,
                  'quality_profiles': recommended_profiles(['radarr'])}
        validate_family_config(config)
        config['quality_profiles']['radarr']['available'] = [config['quality_profiles']['radarr']['available'][1]]
        with self.assertRaises(ValueError):
            validate_family_config(config)
        config = {'apps': ['ombi'], 'ombi_family_presets': True}
        with self.assertRaises(ValueError):
            validate_family_config(config)
        for value in ('yes', 1, None):
            with self.assertRaises(ValueError):
                validate_family_config({'apps': ['ombi'], 'ombi_family_presets': value})
