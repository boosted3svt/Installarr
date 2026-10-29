import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from installarr.directories import open_anchor, worker

MOUNT = {'target': '/', 'source': 'test-local', 'fstype': 'ext4'}


class DirectoryTests(unittest.TestCase):
    def spec(self, directory, parts):
        return {'fd': os.open(directory, os.O_RDONLY | os.O_DIRECTORY), 'parts': parts,
                'path': str(Path(directory).joinpath(*parts)), 'local': True, 'expected': MOUNT,
                'uid': os.geteuid(), 'gid': os.getegid(), 'sentinel': 'health'}

    @patch('installarr.directories.os.setuid')
    @patch('installarr.directories.os.setgid')
    @patch('installarr.directories.os.setgroups')
    @patch('installarr.directories.observed_mount', return_value=MOUNT)
    def test_create_and_rerun_preserve_existing_files_and_modes(self, *mocks):
        with tempfile.TemporaryDirectory() as directory:
            result = worker(self.spec(directory, ['data']))
            self.assertTrue(result['write_verified'])
            target = Path(directory) / 'data'
            health = target / 'health'
            health.write_bytes(b'Operator marker\n')
            health.chmod(0o640)
            before = (target.stat().st_ino, target.stat().st_mode, health.stat().st_ino, health.stat().st_mode)
            result = worker(self.spec(directory, ['data']))
            self.assertEqual(result['created_components'], 0)
            self.assertEqual(health.read_bytes(), b'Operator marker\n')
            self.assertEqual(before, (target.stat().st_ino, target.stat().st_mode, health.stat().st_ino, health.stat().st_mode))
            self.assertEqual({item.name for item in target.iterdir()}, {'health'})

    @patch('installarr.directories.observed_mount', return_value={**MOUNT, 'source': 'changed'})
    def test_changed_mount_refuses_before_creation(self, mount):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                worker(self.spec(directory, ['never-created']))
            self.assertEqual(list(Path(directory).iterdir()), [])

    @patch('installarr.directories.observed_mount', return_value=MOUNT)
    def test_invalid_existing_marker_and_symlink_are_preserved(self, mount):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'data'
            target.mkdir()
            (target / 'health').write_bytes(b'not a health marker')
            with self.assertRaises(ValueError):
                worker(self.spec(directory, ['data']))
            self.assertEqual((target / 'health').read_bytes(), b'not a health marker')
            (Path(directory) / 'redirect').symlink_to(target, target_is_directory=True)
            with self.assertRaises(OSError):
                worker(self.spec(directory, ['redirect']))
            with self.assertRaises(OSError):
                open_anchor(str(Path(directory) / 'redirect' / 'nested'))
