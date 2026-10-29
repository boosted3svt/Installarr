from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from installarr.boot import enable_startup
from installarr.execution import Execution


class AutomaticStartupTests(unittest.TestCase):
    def test_only_verified_owned_deployment_and_engine_units_enabled(self):
        from test_reference import reference_configuration
        config = reference_configuration()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state'
            with Execution(state, {'operation': 'reference-apply-v1', 'config': config, 'name': 'sample'}) as e:
                e.state['phase'] = 'reference_poc_ready';e._save()
            with patch('installarr.boot.provisioning_gate'), patch('installarr.reference.existing_service', return_value='installarr-sample.service'), patch('installarr.lifecycle.service_status', return_value={'phase':'containers_running'}), patch('installarr.lifecycle.command', side_effect=['', 'enabled\nenabled\nenabled']) as command:
                self.assertEqual(enable_startup(config,'sample',state)['automatic_startup'], 'enabled')
            self.assertEqual(command.call_args_list[0].args[0], ['systemctl','enable','docker.service','containerd.service','installarr-sample.service'])

    def test_incomplete_or_conflicting_deployment_never_enables_units(self):
        from test_reference import reference_configuration
        config = reference_configuration()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state'
            with Execution(state, {'operation': 'reference-apply-v1', 'config': config, 'name': 'sample'}) as e:
                e.state['phase'] = 'applying';e._save()
            with patch('installarr.boot.provisioning_gate'), patch('installarr.lifecycle.command') as command:
                with self.assertRaises(ValueError): enable_startup(config,'sample',state)
                command.assert_not_called()
