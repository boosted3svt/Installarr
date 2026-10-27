"""Storage choices and declarative host preparation; never executes changes."""
from pathlib import PurePosixPath


def absolute_path(value):
    return isinstance(value, str) and value.startswith("/") and value != "/" and not any(
        part in ("..",) for part in PurePosixPath(value).parts
    ) and not any(c.isspace() for c in value) and "\x00" not in value


def validate_mounts(config):
    mounts = config.get("storage_mounts", {})
    if not isinstance(mounts, dict) or set(mounts) - set(config["storage"]):
        raise ValueError("Mounts must reference storage purposes")
    targets = {}
    for purpose, mount in mounts.items():
        if not isinstance(mount, dict) or mount.get("kind") not in ("local", "existing", "nfs", "smb"):
            raise ValueError("Choose local, existing, nfs or smb storage")
        kind = mount["kind"]
        allowed = {"kind"} if kind == "local" else {"kind", "mountpoint", "source", "fstype", "sentinel"}
        if kind == "smb":
            allowed.add("credentials_file")
        if set(mount) - allowed:
            raise ValueError("Unknown mount fields; credentials must not be embedded")
        if kind == "local":
            continue
        target, source, fstype = (mount.get(key) for key in ("mountpoint", "source", "fstype"))
        if not absolute_path(target) or not isinstance(source, str) or not source or any(c.isspace() for c in source):
            raise ValueError("Invalid mountpoint or source")
        path = PurePosixPath(config["storage"][purpose])
        if path != PurePosixPath(target) and PurePosixPath(target) not in path.parents:
            raise ValueError("Storage directory must be inside its mountpoint")
        if kind == "nfs" and (fstype not in ("nfs", "nfs4") or ":/" not in source):
            raise ValueError("NFS requires server:/export and nfs/nfs4 filesystem")
        if kind == "smb" and (fstype != "cifs" or not source.startswith("//") or len(source[2:].split("/")) != 2 or not absolute_path(mount.get("credentials_file"))):
            raise ValueError("SMB requires //server/share, cifs and a protected credentials file path")
        if not isinstance(fstype, str) or not fstype:
            raise ValueError("Expected filesystem type is required")
        identity = (source, fstype, mount.get("credentials_file"))
        if target in targets and targets[target] != identity:
            raise ValueError("Conflicting sources for one mountpoint")
        targets[target] = identity
    points = sorted(targets)
    for index, target in enumerate(points):
        if any(PurePosixPath(target) in PurePosixPath(other).parents for other in points[index + 1:]):
            raise ValueError("Nested managed mountpoints require a separate reviewed layout")


def storage_assertions(config):
    checks = dict(config.get("storage_checks", {}))
    for purpose, mount in config.get("storage_mounts", {}).items():
        if mount["kind"] == "local":
            continue
        derived = {key: mount[key] for key in ("mountpoint", "source", "fstype", "sentinel") if key in mount}
        if purpose in checks and checks[purpose] != derived:
            raise ValueError("Storage mount and check assertions disagree")
        checks[purpose] = derived
    return checks


def preparation_plan(config):
    packages, mounts, directories = set(), {}, []
    for purpose, path in config["storage"].items():
        mount = config.get("storage_mounts", {}).get(purpose)
        directories.append({"purpose": purpose, "path": path, "action": "inspect; create only after storage validation and apply approval"})
        if not mount or mount["kind"] == "local":
            continue
        if mount["kind"] == "nfs":
            packages.add("nfs-common")
        if mount["kind"] == "smb":
            packages.add("cifs-utils")
        mounts[mount["mountpoint"]] = {**mount, "action": "reuse without editing persistence" if mount["kind"] == "existing" else "inspect existing mount/fstab; propose persistent mount after conflict and access checks"}
    return {
        "required_storage_packages": sorted(packages),
        "mounts": list(mounts.values()), "directories": directories,
        "blockers": (["Storage type has not been selected for every purpose"] if set(config.get("storage_mounts", {})) != set(config["storage"]) else []),
        "apply_available": False,
        "requirements_before_apply": [
            "Supported Ubuntu, account collisions and Docker workload inspection",
            "Existing mount and persistence reconciliation; backup before approved edits",
            "NAS service-UID access and nonempty mountpoint checks",
            "Systemd and Docker restart protection for unavailable storage",
        ],
    }


def collect_storage(ask, purposes):
    paths, mounts = {}, {}
    for purpose in purposes:
        kind = ask("{} storage type: local/existing/nfs/smb".format(purpose), "local").lower()
        path = ask("Host directory for {}".format(purpose), "/srv/media-stack/{}".format(purpose))
        paths[purpose] = path
        mount = {"kind": kind}
        if kind in ("existing", "nfs", "smb"):
            mount["mountpoint"] = ask("Mountpoint containing this directory", path)
            mount["source"] = ask("Exact source (server:/export, //server/share or local device)", "")
            mount["fstype"] = ask("Filesystem type", "cifs" if kind == "smb" else "nfs" if kind == "nfs" else "ext4")
            if kind == "smb":
                mount["credentials_file"] = ask("Root-protected SMB credentials file path (never enter credentials here)", "/etc/installarr/smb.credentials")
            sentinel = ask("Existing sentinel file relative to this directory (blank skips)", "")
            if sentinel:
                mount["sentinel"] = sentinel
        mounts[purpose] = mount
    return paths, mounts
