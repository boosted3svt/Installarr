import unittest

from installarr.hostplan import collect_storage, preparation_plan, storage_assertions, validate_mounts
from installarr.storage import validate_checks


class HostPlanTests(unittest.TestCase):
    def config(self):
        return {"storage": {"media": "/media/Media/movies", "downloads": "/media/Media/downloads"},
                "storage_mounts": {purpose: {"kind": "nfs", "mountpoint": "/media/Media", "source": "nas:/Public", "fstype": "nfs"}
                                   for purpose in ("media", "downloads")}}

    def test_shared_mount_is_deduplicated(self):
        config = self.config()
        validate_mounts(config)
        result = preparation_plan(config)
        self.assertEqual(len(result["mounts"]), 1)
        self.assertEqual(result["required_storage_packages"], ["nfs-common"])
        self.assertFalse(result["apply_available"])
        self.assertFalse(result["blockers"])

    def test_conflicting_mounts_rejected(self):
        config = self.config()
        config["storage_mounts"]["downloads"]["source"] = "other:/Public"
        with self.assertRaises(ValueError):
            validate_mounts(config)

    def test_directory_outside_mount_rejected(self):
        config = self.config()
        config["storage"]["media"] = "/media/Media-other/movies"
        with self.assertRaises(ValueError):
            validate_mounts(config)

    def test_embedded_smb_password_rejected(self):
        config = {"storage": {"media": "/data/media"}, "storage_mounts": {"media": {
            "kind": "smb", "mountpoint": "/data", "source": "//nas/media", "fstype": "cifs",
            "credentials_file": "/etc/installarr/smb.credentials"}}}
        validate_mounts(config)
        self.assertEqual(preparation_plan(config)["required_storage_packages"], ["cifs-utils"])
        config["storage_mounts"]["media"]["password"] = "dummy"
        with self.assertRaises(ValueError):
            validate_mounts(config)

    def test_disagreeing_assertions_rejected(self):
        config = self.config()
        config["storage_checks"] = {"media": {"source": "other:/share"}}
        with self.assertRaises(ValueError):
            storage_assertions(config)

    def test_existing_mount_never_requests_persistence_edits(self):
        config = self.config()
        for mount in config["storage_mounts"].values():
            mount["kind"] = "existing"
        result = preparation_plan(config)
        self.assertEqual(result["required_storage_packages"], ["nfs-common"])
        self.assertEqual(result["mounts"][0]["action"], "reuse without editing persistence")

    def test_wizard_collects_nfs_and_generates_checks(self):
        answers = iter(["nfs", "/data/movies", "/data", "nas:/media", "nfs", "ready"])
        paths, mounts = collect_storage(lambda *args: next(answers), ["media"])
        config = {"storage": paths, "storage_mounts": mounts}
        validate_mounts(config)
        checks = storage_assertions(config)
        validate_checks(checks, ["media"])
        self.assertEqual(checks["media"]["sentinel"], "ready")

    def test_legacy_paths_require_storage_choices(self):
        config = {"storage": {"media": "/data/media"}}
        self.assertTrue(preparation_plan(config)["blockers"])


if __name__ == "__main__":
    unittest.main()
