import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from installarr.writecheck import check_service_writes, probe_service_write, write_probe


class WriteCheckTests(unittest.TestCase):
    def test_absent_or_changed_mount_never_invokes_write_worker(self):
        expected = {"mountpoint": "/data", "source": "nas:/isolated", "fstype": "nfs"}
        config = {"storage": {"media": "/data/media"}, "storage_checks": {"media": expected},
                  "service_user": {"uid": 2000, "gid": 2000}}
        probe = Mock()
        for inventory in (
                {"status": "unavailable", "filesystems": []},
                {"status": "observed", "filesystems": [{"target": "/", "source": "disk", "fstype": "ext4"}]},
                {"status": "observed", "filesystems": [{"target": "/data", "source": "other:/share", "fstype": "nfs"}]}):
            self.assertEqual(check_service_writes(config, inventory, probe)["checks"][0]["status"], "failed")
        probe.assert_not_called()
        config["storage_checks"] = {}
        self.assertEqual(check_service_writes(config, inventory, probe)["checks"][0]["status"], "incomplete")
        probe.assert_not_called()

    @patch("installarr.writecheck.subprocess.run")
    def test_worker_rechecks_mount_and_refuses_readonly_before_mkdir(self, run):
        with tempfile.TemporaryDirectory() as directory:
            expected = {"mountpoint": "/", "source": "disk", "fstype": "ext4"}
            for source, options in (("different", "rw"), ("disk", "ro")):
                run.return_value = SimpleNamespace(stdout=json.dumps({"filesystems": [
                    {"target": "/", "source": source, "fstype": "ext4", "options": options}]}))
                with patch("installarr.writecheck.os.getgroups", return_value=[]), self.assertRaises(ValueError):
                    write_probe(directory, expected, os.geteuid(), os.getegid())
                self.assertEqual(list(Path(directory).iterdir()), [])

    @unittest.skipIf(os.geteuid() == 0, "Operator I/O probe requires a non-root invoking identity")
    def test_local_write_fsync_readback_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(["findmnt", "--json", "--target", directory,
                                     "--output", "TARGET,SOURCE,FSTYPE"], capture_output=True, text=True, check=True)
            row = json.loads(result.stdout)["filesystems"][0]
            expected = {"mountpoint": row["target"], "source": row["source"], "fstype": row["fstype"]}
            # Unit test the I/O as the operator; physical service isolation is a
            # separate root-only test. Do not claim it from this mocked group list.
            with patch("installarr.writecheck.os.getgroups", return_value=[]):
                access = write_probe(directory, expected, os.geteuid(), os.getegid())
            self.assertTrue(access["write_fsync_readback_cleanup"])
            self.assertEqual(list(Path(directory).iterdir()), [])

    @patch("installarr.writecheck.os.mkdir")
    @patch("installarr.writecheck.os.getgroups", return_value=[98765])
    def test_operator_supplementary_groups_cannot_mask_permissions(self, groups, mkdir):
        with self.assertRaises(ValueError):
            write_probe("/tmp", {"mountpoint": "/", "source": "disk", "fstype": "ext4"},
                        os.geteuid(), os.getegid())
        mkdir.assert_not_called()

    @patch("installarr.writecheck.run_storage", side_effect=subprocess.TimeoutExpired("worker", 10))
    def test_timeout_does_not_report_success(self, run):
        result = probe_service_write("/data", {}, 2000, 2000)
        self.assertEqual(result["status"], "failed")
        self.assertIn("leftover", result["reason"])

    def test_root_service_identity_rejected(self):
        with self.assertRaises(ValueError):
            write_probe("/tmp", {}, 0, 0)

class StorageIdentityTests(unittest.TestCase):
    def test_explicit_asset_probe_uses_reserved_service_identity(self):
        from unittest.mock import Mock
        expected = {'mountpoint': '/assets', 'source': 'nas:/asset-test', 'fstype': 'nfs'}
        config = {'storage': {'netboot_assets': '/assets/files'}, 'storage_checks': {'netboot_assets': expected},
                  'service_user': {'uid': 2000, 'gid': 2000}}
        inventory = {'status': 'observed', 'filesystems': [{'target': '/assets', 'source': 'nas:/asset-test', 'fstype': 'nfs'}]}
        probe = Mock(return_value={'status': 'verified'})
        self.assertEqual(check_service_writes(config, inventory, probe)['checks'][0]['status'], 'verified')
        probe.assert_called_once_with('/assets/files', expected, 911, 1001)
