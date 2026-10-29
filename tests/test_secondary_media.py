import unittest
from unittest.mock import patch
from installarr.cli import validate
from installarr.compose import render_bundle
from installarr.directories import directory_plan
from installarr.lifecycle import health_spec
from installarr.plex import library_paths, reference_libraries
from installarr.writecheck import check_service_writes
from test_compose import compose_configuration


def secondary_configuration():
    config = compose_configuration()
    config['apps'] = ['plex', 'radarr']
    config['plex_libraries'] = reference_libraries()
    config['storage']['media_secondary'] = '/secondary/Movies'
    check = {'mountpoint': '/secondary', 'source': 'nas:/secondary', 'fstype': 'nfs', 'sentinel': 'health'}
    config['storage_mounts']['media_secondary'] = dict(check, kind='existing')
    return config


class SecondaryMediaTests(unittest.TestCase):
    def test_one_map_readonly_bind_library_health_and_no_directory_writes(self):
        config = secondary_configuration()
        validate(config)
        movies = library_paths(config)[0]
        self.assertEqual(movies['host_paths'][1], '/secondary/Movies')
        self.assertEqual(movies['container_paths'][1], '/media-secondary')
        self.assertEqual(movies['container_paths'][0], '/data/media/Movies')
        bundle = render_bundle(config)
        volume = next(v for v in bundle['compose']['services']['plex']['volumes'] if v['target'] == '/media-secondary')
        self.assertTrue(volume['read_only'])
        self.assertFalse(volume['bind']['create_host_path'])
        self.assertFalse(any(v['target'] == '/media-secondary' for v in bundle['compose']['services']['radarr']['volumes']))
        self.assertIn('/media-secondary', bundle['guards']['plex.guard.sh'])
        planned = [r for r in directory_plan(config) if r['path'] == '/secondary/Movies']
        self.assertEqual(len(planned), 1)
        self.assertTrue(planned[0]['read_only'])
        self.assertFalse(any(r['path'].endswith('/media/Movies-2') for r in directory_plan(config)))
        check = next(r for r in health_spec(config, {'target': '/', 'source': 'disk', 'fstype': 'ext4'})['checks'] if r['path'] == '/secondary/Movies')
        self.assertTrue(check['read_only'])
        self.assertEqual(check['expected']['source'], 'nas:/secondary')
        # A write-check command must never probe the read-only source.
        config['storage'] = {'media_secondary': '/secondary/Movies'}
        with patch('installarr.writecheck.probe_service_write') as probe:
            checked = check_service_writes(config, {'status': 'observed', 'filesystems': []}, probe)
            probe.assert_not_called()
            self.assertEqual(checked['checks'][0]['status'], 'not_required')

    def test_reference_writable_secondary_is_shared_with_radarr_bazarr_and_guarded(self):
        from installarr.compose import application_paths
        from installarr.hostplan import preparation_plan
        config = secondary_configuration()
        config['apps'].append('bazarr')
        config['secondary_media_read_only'] = False
        validate(config)
        bundle = render_bundle(config)
        for app in ('radarr', 'bazarr', 'plex'):
            volume = next(v for v in bundle['compose']['services'][app]['volumes'] if v['target'] == '/media-secondary')
            self.assertEqual(volume['read_only'], app == 'plex')
            self.assertFalse(volume['bind']['create_host_path'])
            self.assertIn('/media-secondary', bundle['guards'][app + '.guard.sh'])
        self.assertEqual(application_paths(config, 'radarr')['additional_media_roots'], ['/media-secondary'])
        entry = next(r for r in directory_plan(config) if r['path'] == '/secondary/Movies')
        self.assertFalse(entry['read_only'])
        mount = next(m for m in preparation_plan(config)['mounts'] if m['mountpoint'] == '/secondary')
        self.assertFalse(mount['read_only'])
        check = next(r for r in health_spec(config, {'target': '/', 'source': 'disk', 'fstype': 'ext4'})['checks'] if r['path'] == '/secondary/Movies')
        self.assertFalse(check['read_only'])

    def test_secondary_requires_plex_assertions_and_separate_paths(self):
        for change in ('no_plex', 'overlap', 'no_marker'):
            config = secondary_configuration()
            if change == 'no_plex':
                config['apps'] = ['radarr']
                config.pop('plex_libraries')
            elif change == 'overlap':
                config['storage']['media_secondary'] = config['storage']['media'] + '/Movies-2'
            else:
                config['storage_mounts']['media_secondary'].pop('sentinel')
            with self.assertRaises(ValueError):
                validate(config)


    def test_readonly_mount_persistence_and_mixed_purpose_deduplication(self):
        from installarr.hostplan import preparation_plan
        from installarr.mounts import mount_review, persistence_line
        config = secondary_configuration()
        plan = next(m for m in preparation_plan(config)['mounts'] if m['mountpoint'] == '/secondary')
        self.assertTrue(plan['read_only'])
        plan['kind'] = 'nfs'
        self.assertIn(' ro,', persistence_line(plan, config['service_user']))
        review = mount_review(config, [{'target': '/secondary', 'source': 'nas:/secondary', 'fstype': 'nfs'}],
                              'nas:/secondary /secondary nfs ro,_netdev 0 0\n')
        row = next(r for r in review['mounts'] if r['mountpoint'] == '/secondary')
        self.assertEqual(row['conflicts'], [])
        self.assertEqual(row['persistence'], 'matching_fstab')
        # A mount shared by a writable media purpose may never become read-only
        # merely because the secondary purpose was visited last (or first).
        for reverse in (False, True):
            config = secondary_configuration()
            config['storage']['media_secondary'] = '/srv/stack/secondary'
            config['storage_mounts']['media_secondary'] = {'kind': 'existing', 'mountpoint': '/srv/stack',
                'source': 'nas:/isolated', 'fstype': 'nfs', 'sentinel': 'health'}
            config['storage_mounts']['media'] = dict(config['storage_mounts']['media_secondary'])
            if reverse:
                config['storage'] = dict(reversed(list(config['storage'].items())))
            shared = next(m for m in preparation_plan(config)['mounts'] if m['mountpoint'] == '/srv/stack')
            self.assertFalse(shared['read_only'])
