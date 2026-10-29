"""Opt-in service-identity storage write probes, isolated from discovery."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from .storage import covering_mount, validate_checks
from .storage_process import run_storage, StorageProcessError


def write_probe(path, expected, uid, gid):
    """Worker entrypoint. Fail closed before creating anything on a wrong mount."""
    if any(type(value) is not int or not 1 <= value <= 2147483647 for value in (uid, gid)):
        raise ValueError("Write checks require a non-root service identity")
    validate_checks({"probe": expected}, ["probe"])
    if not isinstance(path, str) or not path.startswith("/") or ".." in Path(path).parts:
        raise ValueError("Invalid storage path")
    root_invocation = os.geteuid() == 0
    if not root_invocation and (os.geteuid(), os.getegid()) != (uid, gid):
        raise ValueError("Cannot assume service identity")
    elif not root_invocation and os.getgroups():
        # An operator's supplementary groups must not mask service permission failures.
        if any(group != gid for group in os.getgroups()):
            raise ValueError("Supplementary groups differ; root is required for an isolated service check")
    if str(Path(path).resolve()) != path:
        raise ValueError("Storage directory contains a symlink")
    directory_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        result = subprocess.run(
            ["findmnt", "--json", "--target", "/proc/self/fd/{}".format(directory_fd),
             "--output", "TARGET,SOURCE,FSTYPE,OPTIONS"],
            pass_fds=(directory_fd,), capture_output=True, text=True, timeout=5, check=True)
        rows = json.loads(result.stdout)["filesystems"]
        if len(rows) != 1:
            raise ValueError("Ambiguous mount")
        row = rows[0]
        if any(row[key] != expected[field] for field, key in (
                ("mountpoint", "target"), ("source", "source"), ("fstype", "fstype"))):
            raise ValueError("Unexpected mount")
        if "rw" not in row["options"].split(","):
            raise ValueError("Read-only mount")
        # Docker opens a bind source as root, then applications access its leaf
        # as their service identity. Private host ancestors need not be traversable.
        if root_invocation:
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)
        access_fd = os.open('.', os.O_RDONLY | os.O_DIRECTORY, dir_fd=directory_fd)
        os.close(access_fd)
        name = ".installarr-write-" + uuid.uuid4().hex
        os.mkdir(name, mode=0o700, dir_fd=directory_fd)
        probe_fd = None
        try:
            probe_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            fd = os.open("sentinel", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=probe_fd)
            try:
                payload = b"Installarr service identity write check\n"
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                fd = os.open("sentinel", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=probe_fd)
                with os.fdopen(fd, "rb") as handle:
                    if handle.read() != payload:
                        raise ValueError("Write readback failed")
            finally:
                os.unlink("sentinel", dir_fd=probe_fd)
        finally:
            if probe_fd is not None:
                os.close(probe_fd)
            os.rmdir(name, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)
    return {"uid": os.geteuid(), "gid": os.getegid(), "write_fsync_readback_cleanup": True}


def probe_service_write(path, expected, uid, gid):
    try:
        result = run_storage(
            [sys.executable, "-m", "installarr.writecheck"],
            input=json.dumps({"path": path, "expected": expected, "uid": uid, "gid": gid}),
            timeout=10, operation="write-probe")
        if result.returncode != 0:
            return {"status": "failed", "reason": "Identity, mount, access or cleanup check failed"}
        access = json.loads(result.stdout)
        if access != {"uid": uid, "gid": gid, "write_fsync_readback_cleanup": True}:
            return {"status": "failed", "reason": "Invalid worker readback"}
        return {"status": "verified", **access}
    except (subprocess.TimeoutExpired, StorageProcessError):
        return {"status": "failed", "reason": "Probe timed out; inspect for leftover .installarr-write-* artifacts"}
    except (OSError, ValueError):
        return {"status": "failed", "reason": "Write probe unavailable"}


def check_service_writes(config, inventory, probe=probe_service_write):
    rows = []
    for purpose, path in config["storage"].items():
        if purpose == 'media_secondary' and config.get('secondary_media_read_only', True):
            rows.append({'purpose': purpose, 'path': path, 'status': 'not_required',
                         'reason': 'Read-only secondary source; directory preparation checks service-UID reads'})
            continue
        expected = config.get("storage_checks", {}).get(purpose)
        observed = covering_mount(path, inventory["filesystems"])
        if not expected:
            result = {"status": "incomplete", "reason": "Exact mount assertions required for write checks"}
        elif inventory["status"] != "observed" or not observed or any(
                expected[field] != observed.get(key) for field, key in (
                    ("mountpoint", "target"), ("source", "source"), ("fstype", "fstype"))):
            result = {"status": "failed", "reason": "Mount assertion failed; no write attempted"}
        else:
            from .hostplan import purpose_identity
            owner = purpose_identity(config, purpose)
            result = probe(path, expected, owner["uid"], owner["gid"])
        rows.append({"purpose": purpose, "path": path, **result})
    return {"checks": rows, "note": "Write checks only; sentinel reads, boot persistence and mount-loss protection are separate gates. Explicit netboot assets use UID 911/GID 1001; default assets are checked by directory preparation."}


if __name__ == "__main__":
    try:
        print(json.dumps(write_probe(**json.load(sys.stdin))))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        sys.exit(1)
