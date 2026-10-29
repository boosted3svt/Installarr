import io
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from installarr.menu import run_menu


class MenuTests(unittest.TestCase):
    def test_no_action_without_selection_and_nonterminal_refusal(self):
        execute = Mock()
        with patch('sys.stdin.isatty', return_value=False):
            with self.assertRaises(ValueError):
                run_menu('config.json', 'sample', None, execute)
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', side_effect=['invalid', '0']), patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(run_menu('config.json', 'sample', None, execute), 0)
        execute.assert_not_called()

    def test_failed_plan_blocks_apply_and_nonroot_blocks_private_actions(self):
        execute = Mock(return_value=2)
        with patch('sys.stdin.isatty', return_value=True), patch('os.geteuid', return_value=0), patch('builtins.input', side_effect=['7', '0']), patch('sys.stdout', new_callable=io.StringIO):
            run_menu('/config.json', 'sample', None, execute)
        execute.assert_called_once_with(['plan', '--config', '/config.json'])
        execute.reset_mock()
        with patch('sys.stdin.isatty', return_value=True), patch('os.geteuid', return_value=1000), patch('builtins.input', side_effect=['3', '4', '5', '6', '7', '8', '0']), patch('sys.stdout', new_callable=io.StringIO):
            run_menu('/config.json', 'sample', None, execute)
        execute.assert_not_called()

    def test_selected_apply_uses_same_name_config_and_private_state(self):
        execute = Mock(return_value=0)
        with patch('sys.stdin.isatty', return_value=True), patch('os.geteuid', return_value=0), patch('builtins.input', side_effect=['7', '0']), patch('sys.stdout', new_callable=io.StringIO):
            run_menu('/config.json', 'sample', Path('/private/state'), execute)
        self.assertEqual(execute.call_args_list[0].args[0], ['plan', '--config', '/config.json'])
        self.assertEqual(execute.call_args_list[1].args[0], ['apply', '--reference', '--config', '/config.json', '--name', 'sample', '--state-directory', '/private/state'])


    def test_preparation_is_explicit_and_keeps_same_resume_identity(self):
        execute = Mock(return_value=0)
        with patch('sys.stdin.isatty', return_value=True), patch('os.geteuid', return_value=0), patch('builtins.input', side_effect=['5', '0']), patch('sys.stdout', new_callable=io.StringIO):
            run_menu('/config.json', 'sample', Path('/private/state'), execute)
        self.assertEqual(execute.call_args_list[0].args[0], ['plan', '--config', '/config.json'])
        self.assertEqual(execute.call_args_list[1].args[0], ['apply', '--reference', '--config', '/config.json', '--name', 'sample', '--state-directory', '/private/state', '--prepare-only'])

    def test_provider_storage_collection_honors_configured_private_filenames(self):
        import json
        import tempfile
        from test_compose import compose_configuration
        config = compose_configuration()
        config['providers'] = {'nzbgeek': {}}
        config['provider_secrets_file'] = '/private/provider-keys.json'
        check = {'mountpoint': '/srv/stack', 'source': '//nas/media', 'fstype': 'cifs', 'sentinel': 'ready'}
        config['storage_mounts']['media'] = dict(check, kind='smb', credentials_file='/private/nas-login.conf')
        config['storage_checks']['media'] = check
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps(config))
            execute = Mock(return_value=0)
            with patch('sys.stdin.isatty', return_value=True), patch('os.geteuid', return_value=0), patch('builtins.input', side_effect=['4', '0']), patch('sys.stdout', new_callable=io.StringIO):
                run_menu(path, 'sample', Path('/private/state'), execute)
            commands = [call.args[0] for call in execute.call_args_list]
            self.assertEqual(commands, [
                ['init-provider-secrets', '--secrets-directory', '/private', '--filename', 'provider-keys.json', '--providers', 'nzbgeek'],
                ['init-smb-secrets', '--secrets-directory', '/private', '--filename', 'nas-login.conf']])
