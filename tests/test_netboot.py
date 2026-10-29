from pathlib import Path
import tempfile
import unittest

from installarr.arr import AppAPIError
from installarr.netboot import seed_admin


class NetbootTests(unittest.TestCase):
    def test_private_hash_rerun_and_conflicting_auth_or_nginx_are_preserved(self):
        credentials = {'username': 'admin', 'password': 'synthetic-test-password'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed_admin(root, credentials)
            password = root / '.installarr-admin.htpasswd'
            before = password.read_bytes()
            self.assertNotIn(credentials['password'].encode(), before)
            self.assertEqual(password.stat().st_mode & 0o777, 0o600)
            seed_admin(root, credentials)
            self.assertEqual(password.read_bytes(), before)
            with self.assertRaises(AppAPIError):
                seed_admin(root, dict(credentials, password='different'))
            site = root / 'nginx/site-confs/installarr-admin'
            site.write_text('operator settings')
            with self.assertRaises(AppAPIError):
                seed_admin(root, credentials)
            self.assertEqual(site.read_text(), 'operator settings')
            self.assertEqual(password.read_bytes(), before)

class AssetStorageTests(unittest.TestCase):
    def config(self):
        import copy
        from test_compose import compose_configuration
        config = copy.deepcopy(compose_configuration())
        config['apps'] = ['netbootxyz']
        config['storage']['netboot_assets'] = '/media/Media/netboot-assets'
        config['storage_mounts']['netboot_assets'] = {'kind': 'existing', 'mountpoint': '/media/Media',
            'source': 'nas:/Public', 'fstype': 'nfs', 'sentinel': 'assets-ready'}
        config['storage_checks']['netboot_assets'] = {key: value for key, value in config['storage_mounts']['netboot_assets'].items() if key != 'kind'}
        return config

    def test_one_asset_map_controls_bind_guard_directory_owner_and_health_identity(self):
        from installarr.compose import application_paths, render_bundle
        from installarr.directories import directory_plan
        from installarr.lifecycle import health_spec
        config = self.config()
        bundle = render_bundle(config)
        assets = next(row for row in bundle['compose']['services']['netbootxyz']['volumes'] if row['target'] == '/assets')
        self.assertEqual(assets['source'], config['storage']['netboot_assets'])
        self.assertFalse(assets['bind']['create_host_path'])
        self.assertIn('assets-ready', bundle['guards']['netbootxyz.guard.sh'])
        entries = [row for row in directory_plan(config) if row['path'] == assets['source']]
        self.assertEqual([(row['uid'], row['gid']) for row in entries], [(911, 1001)])
        spec = health_spec(config, {'target': '/', 'source': '/dev/local', 'fstype': 'ext4'})
        check = next(row for row in spec['checks'] if row['path'] == assets['source'])
        self.assertEqual((check['uid'], check['gid'], check['sentinel']), (911, 1001, 'assets-ready'))
        self.assertEqual(application_paths(config, 'netbootxyz')['assets_directory'], assets['source'])

    def test_missing_assertion_or_app_is_rejected_and_shared_smb_identity_conflicts(self):
        from installarr.cli import validate
        from installarr.compose import render_bundle
        config = self.config()
        config['apps'] = ['plex']
        with self.assertRaises(ValueError):
            validate(config)
        config = self.config()
        config['storage_mounts']['netboot_assets'] = {'kind': 'local'}
        config['storage_checks'].pop('netboot_assets')
        with self.assertRaises(ValueError):
            render_bundle(config)
        config = self.config()
        for purpose in config['storage']:
            if purpose not in ('configs', 'backups'):
                config['storage'][purpose] = '/media/Media/' + purpose
                config['storage_mounts'][purpose] = {'kind': 'smb', 'mountpoint': '/media/Media', 'source': '//nas/Media',
                    'fstype': 'cifs', 'sentinel': 'ready', 'credentials_file': '/private/smb'}
                config['storage_checks'][purpose] = {k: v for k, v in config['storage_mounts'][purpose].items() if k not in ('kind', 'credentials_file')}
        with self.assertRaisesRegex(ValueError, 'Conflicting sources'):
            validate(config)

    def test_dedicated_smb_asset_mount_uses_reserved_identity_in_options(self):
        from installarr.hostplan import preparation_plan
        from installarr.mounts import mount_options
        config = self.config()
        config['storage']['netboot_assets'] = '/assets'
        config['storage_mounts']['netboot_assets'] = {'kind': 'smb', 'mountpoint': '/assets', 'source': '//nas/Assets',
            'fstype': 'cifs', 'sentinel': 'ready', 'credentials_file': '/private/smb'}
        mount = next(row for row in preparation_plan(config)['mounts'] if row['mountpoint'] == '/assets')
        self.assertEqual(mount['write_identity'], {'uid': 911, 'gid': 1001})
        options = mount_options(mount, mount['write_identity'])
        self.assertIn('uid=911', options)
        self.assertIn('gid=1001', options)
