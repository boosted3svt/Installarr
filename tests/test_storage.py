import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock

from installarr.storage import check_storage, covering_mount, mount_inventory, probe, validate_checks


class StorageTests(unittest.TestCase):
    def test_inventory_flattens_nested_json(self):
        run = Mock(return_value={"exit_code": 0, "output": '{"filesystems":[{"target":"/","source":"disk","fstype":"ext4","children":[{"target":"/media/NAS","source":"nas:/share","fstype":"nfs"}]}]}'})
        result = mount_inventory(run)
        self.assertEqual(len(result["filesystems"]), 2)
        self.assertEqual(covering_mount("/media/NAS/movies", result["filesystems"])["source"], "nas:/share")
        self.assertEqual(covering_mount("/media/NAS-other", result["filesystems"])["source"], "disk")

    def test_absent_nas_refuses_probe(self):
        config = {"storage": {"media": "/media/NAS/movies"}, "storage_checks": {"media": {"mountpoint": "/media/NAS", "source": "nas:/share", "fstype": "nfs", "sentinel": "healthcheck.txt"}}}
        access = Mock()
        result = check_storage(config, {"status": "observed", "filesystems": [{"target": "/", "source": "disk", "fstype": "ext4"}]}, access)
        self.assertEqual(result["checks"][0]["status"], "failed")
        access.assert_not_called()

    def test_actual_read_only_probe_and_missing_sentinel(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "sentinel").write_text("ready")
            before = list(path.iterdir())
            self.assertTrue(probe(directory, "sentinel")["sentinel_readable"])
            self.assertFalse(probe(directory, "absent")["sentinel_readable"])
            self.assertEqual(list(path.iterdir()), before)

    def test_sentinel_cannot_escape_via_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "escape").symlink_to("/etc/hostname")
            self.assertFalse(probe(directory, "escape")["sentinel_readable"])

    def test_missing_assertions_never_report_verified(self):
        config = {"storage": {"media": "/data"}}
        result = check_storage(config, {"status": "observed", "filesystems": [{"target": "/", "source": "disk", "fstype": "ext4"}]}, lambda *args: {"directory_readable": True})
        self.assertEqual(result["checks"][0]["status"], "incomplete")

    def test_full_assertions_and_sentinel_succeed(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "ready").write_text("ready")
            config = {"storage": {"media": directory}, "storage_checks": {"media": {
                "mountpoint": directory, "source": "test:/media", "fstype": "nfs", "sentinel": "ready"}}}
            inventory = {"status": "observed", "filesystems": [{"target": directory, "source": "test:/media", "fstype": "nfs"}]}
            self.assertEqual(check_storage(config, inventory)["checks"][0]["status"], "verified")

    def test_symlink_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "real").mkdir()
            (path / "alias").symlink_to(path / "real")
            self.assertFalse(probe(str(path / "alias"))["directory_readable"])

    def test_invalid_sentinel_paths(self):
        for sentinel in ("/etc/passwd", "../secret", ""):
            with self.subTest(sentinel=sentinel), self.assertRaises(ValueError):
                validate_checks({"media": {"mountpoint": "/data", "source": "nas:/share", "fstype": "nfs", "sentinel": sentinel}}, ["media"])


if __name__ == "__main__":
    unittest.main()
