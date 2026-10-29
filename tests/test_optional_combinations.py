"""Render every nonempty optional-app subset without inventing dependencies."""
import itertools
import unittest

from installarr.cli import APPS
from installarr.compose import render_bundle
from installarr.reference import PORTS, render_reference_bundle
from test_compose import compose_configuration


class OptionalCombinationTests(unittest.TestCase):
    def test_all_511_app_subsets_keep_scope_ports_auth_and_bind_guards(self):
        checked = 0
        for count in range(1, len(APPS) + 1):
            for selected in itertools.combinations(APPS, count):
                with self.subTest(apps=selected):
                    config = compose_configuration()
                    config.update(apps=list(selected), data_root='/srv/stack/data')
                    config['storage'].update(media='/srv/stack/data', downloads='/srv/stack/data/downloads', incomplete='/srv/stack/data/incomplete')
                    for purpose in ('media', 'downloads', 'incomplete'):
                        config['storage_checks'][purpose] = {'mountpoint': '/srv/stack', 'source': 'nas:/isolated', 'fstype': 'nfs', 'sentinel': 'health'}
                    legacy = render_bundle(config)
                    boot = render_reference_bundle(config, published=False)
                    live = render_reference_bundle(config, published=True)
                    for bundle in (legacy, boot, live):
                        self.assertEqual(set(bundle['compose']['services']), set(selected))
                        self.assertTrue(all(not volume['bind']['create_host_path'] for service in bundle['compose']['services'].values() for volume in service['volumes']))
                    for app in selected:
                        self.assertNotIn('ports', boot['compose']['services'][app])
                        service = live['compose']['services'][app]
                        self.assertEqual(service['networks'], ['web'])
                        self.assertNotIn('network_mode', service)
                        self.assertNotIn('depends_on', service)
                        self.assertEqual({(row['published'], row['target'], row['protocol']) for row in service['ports']}, set(PORTS[app]))
                        self.assertIn('/installarr-auth-verified', live['guards'][app + '.guard.sh'])
                        self.assertEqual(service['restart'], 'no')
                        for volume in service['volumes']:
                            if volume['target'] == '/data':
                                self.assertEqual(volume['read_only'], app == 'plex')
                    if 'netbootxyz' in selected:
                        self.assertFalse(any(row['target'] == 3001 for row in live['compose']['services']['netbootxyz']['ports']))
                    if 'tautulli' in selected:
                        log_binds = [row for row in live['compose']['services']['tautulli']['volumes'] if row['target'] == '/plexlogs']
                        self.assertEqual(len(log_binds), int('plex' in selected))
                        self.assertTrue(all(row['read_only'] for row in log_binds))
                    checked += 1
        self.assertEqual(checked, 511)
