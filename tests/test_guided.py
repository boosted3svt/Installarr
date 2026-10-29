import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from installarr.cli import main
from installarr.guided import run_setup, collect_settings, yes


class GuidedTests(unittest.TestCase):
    def test_no_flags_and_setup_route_to_guide_and_nonterminal_stays_readonly(self):
        with patch('installarr.guided.run_setup', return_value=0) as guide:
            self.assertEqual(main([]), 0)
            self.assertEqual(main(['setup']), 0)
            self.assertEqual(guide.call_count, 2)
        with tempfile.TemporaryDirectory() as directory, patch('sys.stdin.isatty', return_value=False), patch('sys.stdout', new_callable=io.StringIO):
            base = Path(directory) / 'unused'
            self.assertEqual(run_setup(base), 2)
            self.assertFalse(base.exists())

    def test_cancel_before_privileges_or_settings(self):
        with tempfile.TemporaryDirectory() as directory, patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='no'), patch('os.execvp') as elevate, patch('sys.stdout', new_callable=io.StringIO):
            base = Path(directory) / 'unused'
            self.assertEqual(run_setup(base), 0)
            self.assertFalse(base.exists())
            elevate.assert_not_called()

    def test_administrator_elevation_preserves_same_python_without_flags(self):
        import sys
        with patch('sys.stdin.isatty', return_value=True), patch('os.geteuid', return_value=1000), patch('builtins.input', return_value='yes'), patch('os.execvp') as elevate, patch('sys.stdout', new_callable=io.StringIO):
            run_setup()
        elevate.assert_called_once_with('sudo', ['sudo', sys.executable, '-m', 'installarr', 'setup'])

    def config(self):
        from test_reference import reference_configuration
        config = reference_configuration()
        config['apps'] = ['sabnzbd']
        return config

    def test_save_only_does_not_collect_credentials_prepare_or_start_apps(self):
        config = self.config()
        with tempfile.TemporaryDirectory() as directory, patch('sys.stdin.isatty', return_value=True), patch('installarr.guided.is_administrator', return_value=True), patch('installarr.guided.collect_settings', return_value=config), patch('builtins.input', side_effect=['yes', 'yes', 'no']), patch('installarr.reference.apply_reference') as apply, patch('installarr.credentials.initialize_credentials') as creds, patch('sys.stdout', new_callable=io.StringIO):
            base = Path(directory) / 'setup'
            self.assertEqual(run_setup(base), 0)
            self.assertEqual(json.loads((base / 'settings.json').read_text()), config)
            self.assertEqual((base / 'settings.json').stat().st_mode & 0o777, 0o600)
            apply.assert_not_called(); creds.assert_not_called()

    def test_resume_preserves_saved_choices_and_credentials_then_prepares_before_apply(self):
        from installarr.cli import save_config
        config = self.config()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / 'setup'; base.mkdir(mode=0o700)
            path = base / 'settings.json'; save_config(path, config)
            before = path.read_bytes()
            def apply(config, name, state, **kwargs):
                state.mkdir(mode=0o700, exist_ok=True)
                p = state / 'state.json'; p.write_text(json.dumps({'phase': 'reference_prepared'})); p.chmod(0o600)
                return {}
            with patch('sys.stdin.isatty', return_value=True), patch('installarr.guided.is_administrator', return_value=True), patch('builtins.input', side_effect=['yes', 'yes', 'yes', 'no']), patch('installarr.guided.collect_settings') as collect, patch('installarr.reference.apply_reference', side_effect=apply) as adapter, patch('installarr.credentials.initialize_credentials') as creds, patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(run_setup(base), 0)
                collect.assert_not_called()
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(adapter.call_count, 2)
                self.assertTrue(adapter.call_args_list[0].kwargs['prepare_only'])
                self.assertNotIn('prepare_only', adapter.call_args_list[1].kwargs)
                creds.assert_called_once()

    def test_plain_storage_detection_and_provider_choices_without_internal_file_prompts(self):
        answers = {'Folder for media and downloads': '/media/test',
                   'Name to show in Plex': 'Family', 'Time zone': 'America/Chicago',
                   'Address for opening this server from your other devices': '10.70.0.99'}
        labels = []
        def answer(label, default=''):
            labels.append(label)
            return answers.get(label, default)
        inventory = {'status': 'observed', 'filesystems': [{'target': '/', 'source': '/dev/test', 'fstype': 'ext4'}, {'target': '/media/test', 'source': 'nas:/test', 'fstype': 'nfs'}]}
        with patch('installarr.guided.ask', side_effect=answer), patch('installarr.storage.mount_inventory', return_value=inventory), patch('installarr.cli.identity_conflicts', return_value=[]), patch('installarr.guided.media_identity', return_value={'name': 'media', 'uid': 2000, 'gid': 2000}), patch('sys.stdout', new_callable=io.StringIO):
            config = collect_settings(Path('/var/lib/installarr-setup'))
        self.assertEqual(config['storage_checks']['media']['source'], 'nas:/test')
        self.assertEqual(config['apps'], ['plex', 'radarr', 'sonarr', 'sabnzbd', 'bazarr', 'ombi', 'tautulli', 'jackett', 'netbootxyz'])
        self.assertFalse(any('UID' in label or 'nonsecret' in label or 'claim file' in label for label in labels))
        self.assertEqual(config['providers']['bazarr']['enabled'], ['opensubtitlescom'])
        self.assertTrue(config['ombi_family_presets'])
        self.assertEqual(config['storage']['media_secondary'], '/media/NAS/Movies')
        self.assertEqual(config['storage_mounts']['media_secondary']['source'], '192.168.1.102:/share/MD0_DATA/Public')
        self.assertEqual(config['storage']['netboot_assets'], '/media/netbootxyz/assets')
        self.assertFalse(config['secondary_media_read_only'])

    def test_yes_no_reprompts_invalid_answer(self):
        with patch('builtins.input', side_effect=['maybe', 'y']), patch('sys.stdout', new_callable=io.StringIO):
            self.assertTrue(yes('Continue?'))
