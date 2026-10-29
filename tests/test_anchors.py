import os
from pathlib import Path
import tempfile
import unittest

from installarr.anchors import open_anchors
from installarr.storage_process import StorageProcessError


class AnchorTests(unittest.TestCase):
    def test_descriptors_and_missing_components_survive_worker_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / 'existing'; existing.mkdir()
            held = open_anchors([{'path': str(existing)}, {'path': str(root / 'new/child')}], registry=root / 'registry')
            try:
                self.assertEqual(held[0][1], [])
                self.assertEqual(held[1][1], ['new', 'child'])
                self.assertEqual(os.fstat(held[0][0]).st_ino, existing.stat().st_ino)
                self.assertEqual(os.fstat(held[1][0]).st_ino, root.stat().st_ino)
                self.assertFalse(os.get_inheritable(held[0][0]))
                self.assertFalse((root / 'new').exists())
            finally:
                for fd, parts, observed in held:
                    os.close(fd)

    def test_symlink_refused_without_modifying_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'target'; target.mkdir()
            link = root / 'link'; link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(StorageProcessError):
                open_anchors([{'path': str(link / 'child')}], registry=root / 'registry')
            self.assertEqual(list(target.iterdir()), [])
