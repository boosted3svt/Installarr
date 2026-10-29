import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from installarr.atomic import publish_noreplace
from installarr.compose import private_artifact


class AtomicPublishTests(unittest.TestCase):
    def test_existing_entries_never_replaced_and_nul_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.write_bytes(b'new value')
            target = root / 'target'
            target.write_bytes(b'original')
            inode = target.stat().st_ino
            with self.assertRaises(FileExistsError):
                publish_noreplace(source, target)
            self.assertEqual(target.read_bytes(), b'original')
            self.assertEqual(target.stat().st_ino, inode)
            target.unlink()
            target.symlink_to(root / 'absent')
            with self.assertRaises(FileExistsError):
                publish_noreplace(source, target)
            self.assertTrue(target.is_symlink())
            target.unlink(); target.mkdir()
            with self.assertRaises(FileExistsError):
                publish_noreplace(source, target)
            self.assertTrue(target.is_dir())
            with self.assertRaises(ValueError):
                publish_noreplace(source, str(root / 'truncated') + '\x00suffix')
            self.assertEqual(source.read_bytes(), b'new value')
            self.assertFalse((root / 'truncated').exists())

    def test_directory_descriptor_publication_keeps_single_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'private-input'
            source.write_bytes(b'complete'); source.chmod(0o600)
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                publish_noreplace('private-input', 'private-output', source_dir_fd=fd, target_dir_fd=fd)
            finally:
                os.close(fd)
            self.assertFalse(source.exists())
            target = root / 'private-output'
            self.assertEqual(target.read_bytes(), b'complete')
            self.assertEqual(target.stat().st_nlink, 1)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_sigkill_after_publication_leaves_a_reusable_single_link_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / 'pending', root / 'published'
            source.write_bytes(b'complete crash fixture'); source.chmod(0o600)
            script = 'import os,signal,sys; from installarr.atomic import publish_noreplace; publish_noreplace(sys.argv[1],sys.argv[2]); os.kill(os.getpid(),signal.SIGKILL)'
            child = subprocess.run([sys.executable, '-B', '-c', script, str(source), str(target)], capture_output=True)
            self.assertEqual(child.returncode, -9)
            self.assertFalse(source.exists())
            self.assertEqual(target.stat().st_nlink, 1)
            private_artifact(target, b'complete crash fixture', 0o600)
            self.assertEqual(list(root.iterdir()), [target])
