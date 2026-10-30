import copy
import unittest

from installarr.mounts import mount_review, parse_fstab


def config():
    return {'apps': ['sonarr'], 'storage': {'media': '/media/test/Movies'},
            'storage_mounts': {'media': {'kind': 'existing', 'mountpoint': '/media/test',
                                       'source': 'nas:/test', 'fstype': 'nfs'}}}


class MountTests(unittest.TestCase):
    def test_fstab_escapes_optional_fields_and_hash_in_path(self):
        rows = parse_fstab('# comment\nnas:/a\\040b /media/a\\040b nfs defaults 0 0 # note\nnas:/#data /media/hash nfs\n')
        self.assertEqual(rows[0]['target'], '/media/a b')
        self.assertEqual(rows[0]['source'], 'nas:/a b')
        self.assertEqual(rows[1]['source'], 'nas:/#data')

    def test_existing_mount_and_persistence_match_without_changes(self):
        value = config()
        before = copy.deepcopy(value)
        result = mount_review(value, [{'target': '/media/test', 'source': 'nas:/test', 'fstype': 'nfs'}],
                              'nas:/test /media/test nfs defaults 0 0\n')
        self.assertEqual(result['mounts'][0]['persistence'], 'matching_fstab')
        self.assertEqual(result['mounts'][0]['action'], 'reuse')
        self.assertFalse(result['changed'])
        self.assertEqual(value, before)

    def test_conflicting_and_duplicate_entries_refuse(self):
        runtime = [{'target': '/media/test', 'source': 'nas:/test', 'fstype': 'nfs'}]
        for text, reason in [('other:/test /media/test nfs defaults 0 0\n', 'fstab_source_or_type'),
                             ('nas:/test /media/test nfs defaults\nnas:/test /media/test nfs defaults\n', 'duplicate_fstab_target'),
                             ('nas:/test /media/test nfs ro\n', 'fstab_read_only')]:
            result = mount_review(config(), runtime, text)
            self.assertEqual(result['status'], 'conflict')
            self.assertIn(reason, result['mounts'][0]['conflicts'])

    def test_missing_runtime_and_missing_fstab_are_not_assumed_ready(self):
        result = mount_review(config(), [], '')
        self.assertEqual(result['mounts'][0]['action'], 'existing_mount_required')
        self.assertEqual(result['mounts'][0]['persistence'], 'missing')

    def test_operator_inline_credentials_are_not_in_output(self):
        value = config()
        result = mount_review(value, [], 'nas:/test /media/test nfs username=secret-user,password=secret-password\n')
        self.assertIn('inline_credentials_preserved', result['mounts'][0]['conflicts'])
        self.assertNotIn('secret-user', repr(result))
        self.assertNotIn('secret-password', repr(result))

    def test_new_mount_persistence_has_boot_flags_and_no_inline_secret(self):
        from installarr.mounts import persistence_line
        mount = {'kind': 'smb', 'source': '//nas/test', 'mountpoint': '/mnt/test', 'fstype': 'cifs',
                 'credentials_file': '/private/storage/smb.conf'}
        line = persistence_line(mount, {'uid': 2000, 'gid': 2000})
        self.assertIn('credentials=/private/storage/smb.conf', line)
        self.assertIn('uid=2000,gid=2000', line)
        self.assertIn('_netdev,nofail,x-systemd.mount-timeout=15s', line)
        self.assertNotIn('password=', line)
        self.assertNotIn('username=', line)

    def test_transport_reuse_is_limited_to_exact_source(self):
        import json
        from unittest.mock import Mock, patch
        from installarr.mounts import verified_nfs_transport
        mount = {'kind': 'nfs', 'source': 'nas:/test', 'fstype': 'nfs'}
        rows = [{'source': 'nas:/test', 'fstype': 'nfs', 'options': 'rw,vers=3,mountport=30000,mountproto=udp,mountvers=3'}]
        with patch('subprocess.run', return_value=Mock(returncode=0, stdout=json.dumps({'filesystems': rows}))):
            self.assertEqual(verified_nfs_transport(mount), ['port=2049', 'mountport=30000', 'mountproto=udp', 'mountvers=3'])
            rows[0]['source'] = 'nas:/other'
        with patch('subprocess.run', return_value=Mock(returncode=0, stdout=json.dumps({'filesystems': rows}))):
            self.assertEqual(verified_nfs_transport(mount), [])

    def test_explicit_fresh_nfs_transport_needs_no_existing_mount_or_rpc_discovery(self):
        from unittest.mock import patch
        from installarr.mounts import verified_nfs_transport, persistence_line
        mount = {'kind': 'nfs', 'source': 'nas:/test', 'fstype': 'nfs', 'mountpoint': '/mnt/test',
                 'nfs_transport': {'port': 2049, 'mountport': 30000, 'mountproto': 'udp', 'mountvers': 3}}
        with patch('subprocess.run') as discovery:
            options = verified_nfs_transport(mount)
        discovery.assert_not_called()
        self.assertEqual(options, ['port=2049', 'mountport=30000', 'mountproto=udp', 'mountvers=3'])
        line = persistence_line(mount, {'uid': 2000, 'gid': 2000})
        for option in options + ['proto=tcp', 'hard']:
            self.assertIn(option, line)
        self.assertNotIn('soft', line)
