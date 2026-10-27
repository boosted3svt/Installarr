"""Read-only mount discovery and explicit storage assertions."""
import json
import subprocess
import sys
from pathlib import PurePosixPath


def mount_inventory(run):
    result = run(["findmnt", "--json", "--output", "TARGET,SOURCE,FSTYPE"])
    if result["exit_code"] != 0:
        return {"status": "unavailable", "filesystems": []}
    try:
        rows = []
        def flatten(items):
            for item in items:
                rows.append({key: item.get(key) for key in ("target", "source", "fstype")})
                flatten(item.get("children", []))
        flatten(json.loads(result["output"])["filesystems"])
        return {"status": "observed", "filesystems": rows}
    except (ValueError, KeyError, TypeError):
        return {"status": "invalid_response", "filesystems": []}


def validate_checks(checks, purposes):
    if not isinstance(checks, dict) or set(checks) - set(purposes):
        raise ValueError("Storage checks must reference known storage purposes")
    for check in checks.values():
        if not isinstance(check, dict) or set(check) - {"mountpoint", "source", "fstype", "sentinel"}:
            raise ValueError("Invalid storage check fields")
        if not all(isinstance(check.get(key), str) and check[key] for key in ("mountpoint", "source", "fstype")):
            raise ValueError("Storage checks require mountpoint, source and fstype")
        point = PurePosixPath(check["mountpoint"])
        if not point.is_absolute() or ".." in point.parts:
            raise ValueError("Invalid expected mountpoint")
        if "sentinel" in check:
            sentinel = check["sentinel"]
            if not isinstance(sentinel, str) or not sentinel or PurePosixPath(sentinel).is_absolute() or ".." in PurePosixPath(sentinel).parts:
                raise ValueError("Sentinel must be a relative file path within the configured directory")


def covering_mount(path, rows):
    path = PurePosixPath(path)
    matches = [row for row in rows if isinstance(row.get("target"), str) and
               (PurePosixPath(row["target"]) == path or PurePosixPath(row["target"]) in path.parents)]
    return max(matches, key=lambda row: len(PurePosixPath(row["target"]).parts), default=None)


def probe(path, sentinel=None):
    # Isolate filesystem I/O from the CLI. No mkdir, touch or write calls.
    script = """
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
result = {'directory_readable': False, 'sentinel_readable': None}
try:
    if p.resolve() != p:
        raise OSError('Configured directory contains a symlink')
    if not p.is_dir():
        raise OSError('Not a directory')
    with __import__('os').scandir(str(p)) as entries:
        next(entries, None)
    result['directory_readable'] = True
    if len(sys.argv) > 2:
        candidate = (p / sys.argv[2]).resolve()
        if p.resolve() not in candidate.parents:
            raise OSError('Sentinel escapes configured directory')
        with candidate.open('rb') as handle:
            handle.read(1)
        result['sentinel_readable'] = True
except OSError:
    if len(sys.argv) > 2:
        result['sentinel_readable'] = False
print(json.dumps(result))
"""
    try:
        args = [sys.executable, "-c", script, path]
        if sentinel is not None:
            args.append(sentinel)
        result = subprocess.run(args, capture_output=True, text=True, timeout=5, check=False)
        if result.returncode != 0:
            return {"status": "probe_failed"}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except (OSError, ValueError):
        return {"status": "probe_failed"}


def check_storage(config, inventory, probe_path=probe):
    results = []
    for purpose, path in config["storage"].items():
        expected = config.get("storage_checks", {}).get(purpose)
        mount = covering_mount(path, inventory["filesystems"])
        errors = []
        if inventory["status"] != "observed" or mount is None:
            errors.append("Mount inventory unavailable or no covering mount")
        if expected and mount:
            for key, actual_key in (("mountpoint", "target"), ("source", "source"), ("fstype", "fstype")):
                if expected[key] != mount[actual_key]:
                    errors.append("Expected mount {} does not match".format(key))
        # Refuse filesystem I/O when mount assertions fail (e.g. an absent NAS).
        access = probe_path(path, expected.get("sentinel") if expected else None) if not errors else None
        if access is not None and not access.get("directory_readable"):
            errors.append("Directory unavailable, unreadable or probe timed out")
        if expected and "sentinel" in expected and access is not None and access.get("sentinel_readable") is not True:
            errors.append("Sentinel is not readable")
        results.append({"purpose": purpose, "path": path, "observed_mount": mount,
                        "status": "failed" if errors else "verified" if expected and "sentinel" in expected else "incomplete",
                        "access": access, "errors": errors})
    return {"checks": results, "note": "Read-only checks as the current operator, not the service UID. Write access, persistence and mount-loss protection remain unverified."}
