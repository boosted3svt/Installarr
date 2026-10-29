"""Disposable operator-UID write/read test for the single authorized NAS subtree.

Run explicitly: python3 tools/probe_test_mount.py. Never used during discovery.
No directory listing, existing-file reads, ownership changes or mount changes.
"""
import json
import os
from pathlib import Path
import subprocess
import uuid


def main():
    target = "/media/installarr"
    expected = "192.168.1.102:/share/MD0_DATA/Public/installarr"
    if str(Path(target).resolve()) != target:
        raise ValueError("Test mount path contains a symlink")
    # Hold an open directory so mount disappearance cannot redirect writes into
    # the local directory beneath it. Check the covering identity AFTER opening.
    root_fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        result = subprocess.run(
            ["findmnt", "--json", "--target", "/proc/self/fd/{}".format(root_fd),
             "--output", "TARGET,SOURCE,FSTYPE,OPTIONS"],
            pass_fds=(root_fd,), capture_output=True, text=True, check=True, timeout=5)
        rows = json.loads(result.stdout)["filesystems"]
        if len(rows) != 1:
            raise ValueError("Ambiguous test mount")
        row = rows[0]
        if (row["target"], row["source"], row["fstype"]) != (target, expected, "nfs"):
            raise ValueError("Unexpected mount; refusing writes")
        if "rw" not in row["options"].split(","):
            raise ValueError("Test mount is read-only")
        name = ".installarr-probe-" + uuid.uuid4().hex
        os.mkdir(name, mode=0o700, dir_fd=root_fd)
        probe_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        try:
            data = b"Installarr isolated operator UID probe\n"
            fd = os.open("sentinel", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=probe_fd)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                fd = os.open("sentinel", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=probe_fd)
                with os.fdopen(fd, "rb") as handle:
                    if handle.read() != data:
                        raise ValueError("Readback mismatch")
            finally:
                os.unlink("sentinel", dir_fd=probe_fd)
        finally:
            os.close(probe_fd)
            os.rmdir(name, dir_fd=root_fd)
        print(json.dumps({"mountpoint": target, "source": expected, "fstype": "nfs",
                          "uid": os.geteuid(), "gid": os.getegid(),
                          "write_fsync_readback_cleanup": "passed",
                          "service_uid_access": "not tested"}, indent=2))
    finally:
        os.close(root_fd)


if __name__ == "__main__":
    main()
