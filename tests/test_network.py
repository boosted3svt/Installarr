import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from installarr.dockerhost import PACKAGES
from installarr.network import prepare_standard_docker


class NetworkTests(unittest.TestCase):
    def run_case(self, phase='verified', changed_version=False, fresh=False):
        state = {'steps': {} if fresh else {'engine': phase}}
        execution = Mock()
        execution.state = state
        execution.__enter__ = Mock(return_value=execution)
        execution.__exit__ = Mock(return_value=False)
        execution.reconcile.side_effect = lambda name, action: action()
        def saved(path):
            if str(path).endswith('docker-install/state.json'):
                return {'package_versions': {p: 'pinned' for p in PACKAGES}}
            return state
        def run(args, **kwargs):
            if args[0] == 'systemctl':
                return SimpleNamespace(returncode=0, stdout='masked' if args[1] == 'is-enabled' else
                                       'active' if args[-1] == 'docker.service' else 'inactive')
            return SimpleNamespace(returncode=0, stdout=json.dumps([{'Driver': 'bridge',
                'Labels': {'org.installarr.reference-check': '1'}}]))
        with patch('installarr.network.provisioning_gate'), \
             patch('installarr.network.Path.exists', autospec=True,
                   side_effect=lambda path: not fresh and str(path).endswith('reference-network/state.json')), \
             patch('installarr.network.root_json', side_effect=saved), \
             patch('installarr.network.installed_version', return_value='changed' if changed_version else 'pinned'), \
             patch('installarr.network.prepare_docker') as stage, \
             patch('installarr.network.Execution', return_value=execution), \
             patch('installarr.network.subprocess.run', side_effect=run), \
             patch('installarr.network.command', return_value='29.9.2') as command:
            if changed_version:
                with self.assertRaises(ValueError):
                    prepare_standard_docker()
                command.assert_not_called()
            else:
                self.assertEqual(prepare_standard_docker()['status'], 'standard_reference_network_ready')
            return stage.call_count, [call.args[0] for call in command.call_args_list]

    def test_owned_live_engine_rerun_never_remasks_or_restarts(self):
        staged, commands = self.run_case()
        self.assertEqual(staged, 0)
        self.assertFalse(any(row[0] == 'systemctl' for row in commands))

    def test_interrupted_transition_resumes_without_remasking_packages(self):
        staged, commands = self.run_case(phase='failed')
        self.assertEqual(staged, 0)
        self.assertIn(['systemctl', 'start', 'docker.service'], commands)
        self.assertFalse(any(row[:2] == ['systemctl', 'mask'] for row in commands))

    def test_fresh_host_stages_signed_packages_before_start(self):
        staged, commands = self.run_case(fresh=True)
        self.assertEqual(staged, 1)
        self.assertIn(['systemctl', 'start', 'docker.service'], commands)

    def test_changed_package_versions_refuse_before_engine_commands(self):
        staged, commands = self.run_case(changed_version=True)
        self.assertEqual(staged, 0)
        self.assertEqual(commands, [])
