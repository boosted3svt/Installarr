import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from installarr.startup import container_mount_assertion, render_storage_guard


class StartupTests(unittest.TestCase):
    def test_container_assertions_derive_exact_subtree_without_changing_case(self):
        expected = {"mountpoint": "/media/installarr", "source": "nas:/export", "fstype": "nfs", "sentinel": "health"}
        result = container_mount_assertion("/media/installarr/Movies/Lenora", "/data/media", expected)
        self.assertEqual(result["root"], "/Movies/Lenora")
        self.assertEqual(result["source"], "nas:/export")
        for path in ("/media/installarr-other/Movies", "/media/installarr/../sibling"):
            with self.assertRaises(ValueError):
                container_mount_assertion(path, "/data", expected)
        with self.assertRaises(ValueError):
            container_mount_assertion("/media/installarr", "/data", {key: value for key, value in expected.items() if key != "sentinel"})

    def test_real_mount_and_sentinel_before_entrypoint(self):
        with tempfile.NamedTemporaryFile(mode="w", prefix="installarr-guard-", dir="/dev/shm") as sentinel:
            sentinel.write("synthetic health sentinel\n")
            sentinel.flush()
            result = subprocess.run(["findmnt", "--json", "--target", sentinel.name,
                                     "--output", "TARGET,SOURCE,FSTYPE"], capture_output=True, text=True, check=True)
            row = json.loads(result.stdout)["filesystems"][0]
            spec = {"target": row["target"], "source": row["source"], "fstype": row["fstype"],
                    "sentinel": Path(sentinel.name).name}
            script = render_storage_guard([spec])
            result = subprocess.run(["/bin/sh", "-c", script, "guard", "/bin/echo", "entrypoint-ran"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "entrypoint-ran")
            for changed in (dict(spec, source="wrong-source"), dict(spec, fstype="nfs"), dict(spec, root="/wrong-subtree"),
                            dict(spec, sentinel="missing-installarr-sentinel")):
                result = subprocess.run(["/bin/sh", "-c", render_storage_guard([changed]), "guard",
                                         "/bin/echo", "entrypoint-ran"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 78)
                self.assertNotIn("entrypoint-ran", result.stdout)
            link = Path(sentinel.name + "-link")
            link.symlink_to(sentinel.name)
            try:
                result = subprocess.run(["/bin/sh", "-c", render_storage_guard([dict(spec, sentinel=link.name)]),
                                         "guard", "/bin/echo", "entrypoint-ran"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 78)
                self.assertNotIn("entrypoint-ran", result.stdout)
            finally:
                link.unlink()

    def test_invalid_mounts_and_ambiguous_sentinels_rejected(self):
        spec = {"target": "/data", "source": "nas:/test", "fstype": "nfs", "sentinel": "health"}
        for specs in ([], [dict(spec, target="/")], [dict(spec, sentinel="../sibling")],
                      [dict(spec, sentinel="nested/file")], [dict(spec, source="ambiguous source")], [spec, spec]):
            with self.assertRaises(ValueError):
                render_storage_guard(specs)
