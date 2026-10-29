"""Explicit root-only probes confined to the authorized NAS and own local fixtures.

Never unmounts storage, changes mount settings or accesses sibling NAS paths.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.accounts import provisioning_gate
from installarr.writecheck import probe_service_write


def main():
    provisioning_gate()
    expected = {"mountpoint": "/media/installarr",
                "source": "192.168.1.102:/share/MD0_DATA/Public/installarr", "fstype": "nfs"}
    result = subprocess.run(["findmnt", "--json", "--target", expected["mountpoint"],
                             "--output", "TARGET,SOURCE,FSTYPE,OPTIONS"],
                            capture_output=True, text=True, check=True, timeout=5)
    rows = json.loads(result.stdout)["filesystems"]
    if len(rows) != 1 or any(rows[0][actual] != expected[field] for field, actual in (
            ("mountpoint", "target"), ("source", "source"), ("fstype", "fstype"))):
        raise ValueError("Isolated test mount mismatch")
    results = []
    for name, uid, gid in (("installarr-test", 2000, 2000), ("nbxyz", 911, 1001)):
        access = probe_service_write(expected["mountpoint"], expected, uid, gid)
        if access["status"] != "verified":
            raise ValueError("Service write test failed")
        results.append({"test": "nas-write-readback-cleanup", "name": name, **access})
    wrong_source = dict(expected, source="invalid-test-source:/installarr")
    access = probe_service_write(expected["mountpoint"], wrong_source, 2000, 2000)
    if access["status"] != "failed":
        raise ValueError("Wrong source unexpectedly passed")
    results.append({"test": "wrong-source-refused", "status": "passed"})
    with tempfile.TemporaryDirectory(prefix="installarr-missing-mount-", dir="/var/tmp") as directory:
        os.chown(directory, 2000, 2000)
        absent = dict(expected, mountpoint=directory)
        access = probe_service_write(directory, absent, 2000, 2000)
        if access["status"] != "failed" or list(Path(directory).iterdir()):
            raise ValueError("Absent mount did not refuse writes")
        results.append({"test": "absent-mount-local-directory-unmodified", "status": "passed"})
    with tempfile.TemporaryDirectory(prefix="installarr-root-only-", dir="/var/tmp") as directory:
        result = subprocess.run(["findmnt", "--json", "--target", directory,
                                 "--output", "TARGET,SOURCE,FSTYPE"],
                                capture_output=True, text=True, check=True, timeout=5)
        row = json.loads(result.stdout)["filesystems"][0]
        local = {"mountpoint": row["target"], "source": row["source"], "fstype": row["fstype"]}
        access = probe_service_write(directory, local, 2000, 2000)
        if access["status"] != "failed" or list(Path(directory).iterdir()):
            raise ValueError("Service unexpectedly accessed root-only directory")
        results.append({"test": "root-only-directory-refused-after-drop", "status": "passed"})
    print(json.dumps({"results": results}, indent=2))


if __name__ == "__main__":
    main()
