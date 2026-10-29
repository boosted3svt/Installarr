import unittest
from unittest.mock import Mock, patch

from installarr.apply import ApplyError, apply, configure_apps
from test_compose import compose_configuration


class ApplyTests(unittest.TestCase):
    @patch('installarr.apply.provisioning_gate')
    @patch('installarr.apply.prepare_accounts')
    def test_unsupported_app_refused_before_host_preparation(self, accounts, gate):
        config = compose_configuration()
        config['apps'] = ['plex']
        with self.assertRaises(ApplyError):
            apply(config, 'test')
        accounts.assert_not_called()

    @patch('installarr.apply.wait_for')
    @patch('installarr.apply.ensure_sabnzbd')
    def test_sab_authentication_restart_precedes_connection_configuration(self, connect, wait):
        config = compose_configuration()
        config['apps'] = ['radarr', 'sabnzbd']
        sab, arr = Mock(), Mock()
        from installarr.arr import AppAPIError
        sab.verify_admin.side_effect = [AppAPIError('not configured'), {'valid': 200}]
        wait.side_effect = [sab, sab, arr]
        events = []
        sab.configure_admin.side_effect = lambda credentials: events.append('credentials')
        restart = lambda: events.append('restart')
        connect.side_effect = lambda *args, **kwargs: events.append('connection') or {'id': 4}
        result = configure_apps(config, Mock(), {'username': 'example', 'password': 'synthetic'}, restart)
        self.assertEqual(events, ['credentials', 'restart', 'connection'])
        self.assertEqual(result['radarr']['downloader'], {'id': 4})
        self.assertNotIn('password', repr(result))

    @patch('installarr.profiles.ensure_profile')
    @patch('installarr.apply.wait_for')
    def test_configured_profiles_return_dynamic_preference_without_media_assignment(self, wait, ensure):
        from installarr.profiles import recommended_profiles
        config = compose_configuration()
        config['apps'] = ['radarr']
        config['quality_profiles'] = recommended_profiles(config['apps'])
        client = Mock()
        wait.return_value = client
        ensure.side_effect = [{'id': 43}, {'id': 98}]
        result = configure_apps(config, Mock(), {'username': 'example', 'password': 'synthetic'}, Mock())
        self.assertEqual(ensure.call_count, 2)
        self.assertEqual(result['radarr']['quality_profiles']['preferred_id'], 43)
        self.assertEqual(result['radarr']['quality_profiles']['existing_assignments'], 'preserved')
        client.json.assert_not_called()

class FamilyApplyTests(unittest.TestCase):
    @patch('installarr.ombi_family.configure_family')
    @patch('installarr.ombi_family.import_family')
    @patch('installarr.plex.configure_server')
    @patch('installarr.profiles.ensure_profile')
    @patch('installarr.apply.app_client')
    @patch('installarr.apply.wait_for', side_effect=lambda action: action())
    def test_family_routes_use_hd_even_when_global_preference_is_uhd(self, wait, clients, ensure, plex_config, imported, family):
        from pathlib import Path
        from unittest.mock import MagicMock
        from installarr.profiles import recommended_profiles
        config = compose_configuration()
        config.update(apps=['ombi', 'plex', 'radarr'], ombi_family_presets=True)
        config['quality_profiles'] = recommended_profiles(config['apps'])
        config['quality_profiles']['radarr']['default'] = config['quality_profiles']['radarr']['available'][1]
        arr, plex, ombi = MagicMock(), MagicMock(), MagicMock()
        arr.ensure_root.side_effect = [101, 23, 87]
        plex.status.return_value = {'machine_identifier': 'test-machine'}
        clients.side_effect = lambda config, controller, app, *args: {'radarr': arr, 'plex': plex, 'ombi': ombi}[app]
        ensure.side_effect = [{'id': 7}, {'id': 8}]
        plex_config.return_value = {'server_name': 'Test', 'libraries': []}
        family.return_value = {'settings': 'verified'}
        checkpoint = Path('/private/family-import')
        result = configure_apps(config, Mock(), {'username': 'admin', 'password': 'synthetic'}, Mock(), family_state_directory=checkpoint)
        routes = family.call_args[0][1]
        self.assertEqual(result['radarr']['quality_profiles']['preferred_id'], 8)
        self.assertEqual(routes['lenora8'], {'radarrRootPath': 23, 'radarrQualityProfile': 7})
        self.assertEqual(routes['rebel739'], {'radarrRootPath': 87, 'radarrQualityProfile': 7})
        self.assertEqual(routes['beanie08'], {})
        self.assertEqual(imported.call_args[0][2:], (checkpoint, 'test-machine'))
