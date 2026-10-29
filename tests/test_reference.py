import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from installarr.reference import identity, render_reference_bundle
from test_compose import compose_configuration


def reference_configuration():
    config = compose_configuration()
    config['apps'] = ['radarr', 'sabnzbd']
    config['data_root'] = '/srv/stack/data'
    for purpose in ('media', 'downloads', 'incomplete'):
        config['storage'][purpose] = config['data_root'] + '/' + purpose
    return config


class ReferenceTests(unittest.TestCase):
    def test_bootstrap_has_no_ports_and_final_uses_reference_ports(self):
        config = reference_configuration()
        before = copy.deepcopy(config)
        bootstrap = render_reference_bundle(config, published=False)
        final = render_reference_bundle(config)
        self.assertEqual(config, before)
        self.assertNotEqual(identity(config), identity(config, False))
        self.assertEqual(final['compose']['networks'], {'web': {'driver': 'bridge'}})
        for app, service in bootstrap['compose']['services'].items():
            self.assertNotIn('ports', service)
            self.assertNotIn('network_mode', service)
            self.assertNotIn('depends_on', service)
            self.assertEqual(service['networks'], ['web'])
            self.assertEqual(service['restart'], 'no')
        self.assertEqual(final['compose']['services']['sabnzbd']['ports'], [
            {'host_ip': config['bind_address'], 'published': 8090, 'target': 8080, 'protocol': 'tcp'}])
        self.assertEqual(final['compose']['services']['radarr']['ports'][0]['published'], 7878)
        config.pop('data_root')
        with self.assertRaises(ValueError):
            render_reference_bundle(config)

    def test_auth_marker_preserves_literal_dollars(self):
        config = reference_configuration()
        config['project_directory'] = '/srv/bundle-$literal'
        service = render_reference_bundle(config)['compose']['services']['radarr']
        marker = next(row for row in service['volumes'] if row['target'] == '/installarr-auth-verified')
        self.assertEqual(marker['source'], '/srv/bundle-$$literal/auth-ready.txt')
        self.assertTrue(marker['read_only'])
        self.assertFalse(marker['bind']['create_host_path'])

    def test_final_guard_refuses_missing_wrong_marker_or_reset_auth(self):
        # Exercise the real shell auth gate independently of the already-tested
        # storage gate. No container, privileged mount or host /config is needed.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = reference_configuration()
            with patch('installarr.reference.render_bundle', return_value={
                    'compose': {'services': {'radarr': {'labels': {}, 'volumes': []}}},
                    'guards': {'radarr.guard.sh': 'deny() { exit 78; }\nexec "$@"\n'}}):
                script = render_reference_bundle(config)['guards']['radarr.guard.sh']
            script = script.replace('/installarr-auth-verified', str(root / 'marker')).replace('/config/', directory + '/')
            def run():
                return subprocess.run(['/bin/sh', '-c', script, 'guard', '/bin/echo', 'entrypoint'],
                                      capture_output=True, text=True)
            self.assertEqual(run().returncode, 78)
            (root / 'marker').write_text('wrong-deployment\n')
            self.assertEqual(run().returncode, 78)
            (root / 'marker').write_text(identity(config) + '\n')
            (root / 'radarr.db').write_text('fixture-db')
            (root / 'config.xml').write_text('<AuthenticationMethod>None</AuthenticationMethod>')
            self.assertEqual(run().returncode, 78)
            (root / 'config.xml').write_text('<AuthenticationMethod>Forms</AuthenticationMethod>\n'
                                           '<AuthenticationRequired>Enabled</AuthenticationRequired>')
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'entrypoint')
            (root / 'config.xml').unlink()
            (root / 'config.xml').symlink_to(root / 'radarr.db')
            self.assertEqual(run().returncode, 78)


class ExistingServiceEvidenceTests(unittest.TestCase):
    def test_existing_unit_conflicts_are_read_only_and_modes_are_checked(self):
        import hashlib
        from types import SimpleNamespace
        from unittest.mock import Mock
        from installarr.reference import existing_service
        config = reference_configuration()
        definition = b'owned definition bytes'
        unit = b'owned unit bytes'
        state = SimpleNamespace(state={'live_unit': hashlib.sha256(definition + unit).hexdigest()})
        saved = {'config': config, 'deployment_mode': 'reference'}
        def read(path, mode):
            self.assertEqual(mode, 0o600 if path.name == 'definition.json' else 0o644)
            return definition if path.name == 'definition.json' else unit
        with patch('installarr.reference.os.path.lexists', return_value=True), patch('installarr.reference.root_json', return_value=saved), patch('installarr.runtime.read_owned', side_effect=read), patch('installarr.reference.install_service') as install:
            self.assertEqual(existing_service(config, 'sample', state), 'installarr-sample.service')
            state.state['live_unit'] = 'changed evidence'
            with self.assertRaises(ValueError):
                existing_service(config, 'sample', state)
            install.assert_not_called()
        with patch('installarr.reference.os.path.lexists', side_effect=[False, True]), patch('installarr.reference.install_service') as install:
            with self.assertRaises(ValueError):
                existing_service(config, 'sample', state)
            install.assert_not_called()
