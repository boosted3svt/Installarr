"""Read-only discovery and declarative planning. No privileged mutations yet."""
import argparse
import grp
import ipaddress
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import subprocess
import sys

APPS = ("sabnzbd", "sonarr", "radarr", "bazarr", "jackett", "plex", "ombi", "tautulli", "netbootxyz")
PURPOSES = ("media", "downloads", "incomplete", "configs", "backups")


def validate_timezone(name):
    """Validate against Ubuntu's system tzdata without requiring Python 3.9."""
    if not isinstance(name, str) or not name or name.startswith("/") or any(
        part in ("", ".", "..") for part in name.split("/")
    ):
        raise ValueError("Invalid timezone name")
    try:
        with (Path("/usr/share/zoneinfo") / name).open("rb") as handle:
            if handle.read(4) != b"TZif":
                raise ValueError("Not a timezone data file")
    except OSError:
        raise ValueError("Unknown timezone or missing system tzdata") from None


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
        return {"available": True, "exit_code": result.returncode, "output": result.stdout.strip()}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "exit_code": None, "output": ""}


def preflight():
    release = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                release[key] = value.strip('"')
    except OSError:
        pass
    supported = release.get("ID") == "ubuntu" and release.get("VERSION_ID") == "24.04"
    return {
        "os": release.get("PRETTY_NAME", platform.system()),
        "supported_target": supported,
        "target": "Ubuntu 24.04 LTS (host provisioning not yet implemented)",
        "architecture": platform.machine(), "hostname": platform.node(),
        "running_as_root": os.geteuid() == 0,
        "systemd_running": Path("/run/systemd/system").is_dir(),
        "workspace_free_bytes": shutil.disk_usage(Path.cwd()).free,
        "docker": command(["docker", "version", "--format", "{{.Server.Version}}"]),
        "compose": command(["docker", "compose", "version", "--short"]),
        "mounts": command(["findmnt", "--json", "--output", "TARGET,SOURCE,FSTYPE"]),
        "note": "Read-only inventory; not a complete readiness or permission check.",
    }


def validate(config):
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("Expected a version 1 configuration object")
    allowed = {"schema_version", "apps", "timezone", "bind_address", "plex_allowed_networks", "service_user", "storage", "project_directory"}
    if set(config) - allowed:
        raise ValueError("Unknown configuration fields; do not store credentials in this file")
    apps = config.get("apps")
    if not isinstance(apps, list) or not apps or any(a not in APPS for a in apps) or len(set(apps)) != len(apps):
        raise ValueError("Choose a nonempty, unique list of supported apps")
    try:
        ipaddress.IPv4Address(config["bind_address"])
        ipaddress.IPv4Network(config["plex_allowed_networks"], strict=False)
        validate_timezone(config["timezone"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("Valid IPv4 binding, Plex CIDR and timezone are required") from None
    identity = config.get("service_user", {})
    if not isinstance(identity, dict) or set(identity) != {"name", "uid", "gid"} or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", str(identity.get("name", ""))):
        raise ValueError("Service user requires name, uid and gid")
    for field in ("uid", "gid"):
        value = identity[field]
        if type(value) is not int or not 1 <= value <= 2147483647:
            raise ValueError("Service UID/GID must be positive non-root integers")
    storage = config.get("storage", {})
    if not isinstance(storage, dict) or set(storage) != set(PURPOSES):
        raise ValueError("Storage must specify media, downloads, incomplete, configs and backups")
    for value in [config.get("project_directory"), *storage.values()]:
        if not isinstance(value, str) or not value.startswith("/") or value == "/" or ".." in Path(value).parts or "\n" in value:
            raise ValueError("Directories must be absolute, non-root paths without parent traversal")
    if len(set(storage.values())) != len(storage):
        raise ValueError("Use distinct directories for each storage purpose")
    return config


def identity_conflicts(name, uid, gid):
    conflicts = []
    for lookup, key, label, expected in (
        (pwd.getpwnam, name, "named user's UID", uid),
        (pwd.getpwuid, uid, "UID owner's name", name),
        (grp.getgrnam, name, "named group's GID", gid),
        (grp.getgrgid, gid, "GID owner's name", name),
    ):
        try:
            record = lookup(key)
        except KeyError:
            continue
        actual = record.pw_uid if label == "named user's UID" else record.gr_gid if label == "named group's GID" else record[0]
        if actual != expected:
            conflicts.append(f"{name}: {label} is {actual}, expected {expected}")
    try:
        if pwd.getpwnam(name).pw_gid != gid:
            conflicts.append(f"{name}: existing primary group differs from requested GID {gid}")
    except KeyError:
        pass
    return conflicts


def plan(config):
    validate(config)
    user = config["service_user"]
    conflicts = identity_conflicts(user["name"], user["uid"], user["gid"])
    if "netbootxyz" in config["apps"]:
        conflicts += identity_conflicts("nbxyz", 911, 1001)
        if user["name"] != "nbxyz" and (user["uid"] == 911 or user["gid"] == 1001):
            conflicts.append("Media identity overlaps reserved netbootxyz UID 911 / GID 1001")
    return {
        "mode": "preview only; no system changes",
        "apps": config["apps"], "service_user": user,
        "netbootxyz_identity": {"name": "nbxyz", "uid": 911, "gid": 1001} if "netbootxyz" in config["apps"] else None,
        "host_storage": config["storage"],
        "proposed_container_paths": {"media": "/data/media", "downloads": "/data/downloads", "incomplete": "/data/incomplete"},
        "plex_allowed_networks": config["plex_allowed_networks"],
        "conflicts": conflicts,
        "pending_checks": [
            "Official image permission mechanisms and pinned versions",
            "Storage source/protocol, persistent mounts, service-UID access and mount-loss protection",
            "Host binding ownership and port conflicts",
            "Application-specific roots, credentials and integration configuration",
        ],
        "scope": "Fresh provisioning; DHCP/PXE reachability is operator-managed. No migration.",
    }


def save_config(path, config):
    validate(config)
    # Refuse replacement, including symlinks; secrets are never collected here.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")


def configure(path):
    if not sys.stdin.isatty():
        raise ValueError("configure requires an interactive terminal; use a JSON file with plan for unattended review")
    def ask(label, default):
        return input(f"{label} [{default}]: ").strip() or default
    print("Collecting nonsecret choices only. No packages, accounts or mounts will be changed.")
    print("Available apps: " + ", ".join(APPS))
    config = {
        "schema_version": 1,
        "apps": ask("Apps (comma separated)", "sabnzbd,sonarr,radarr,bazarr,plex,ombi").replace(" ", "").split(","),
        "timezone": ask("Timezone", "America/Chicago"),
        "bind_address": ask("Server LAN IPv4 address", "192.168.1.101"),
        "plex_allowed_networks": ask("Plex allowed networks CIDR", "192.168.0.0/23"),
        "project_directory": ask("Compose project directory", "/opt/media-stack"),
        "service_user": {
            "name": ask("Media service account", "media"),
            "uid": int(ask("Media UID (availability checked by plan)", "1000")),
            "gid": int(ask("Media GID (availability checked by plan)", "1000")),
        },
        "storage": {purpose: ask(f"Host directory for {purpose}", f"/srv/media-stack/{purpose}") for purpose in PURPOSES},
    }
    preview = plan(config)
    print(json.dumps(preview, indent=2))
    if ask("Save these choices? yes/no", "no").lower() == "yes":
        save_config(path, config)
        print(f"Saved nonsecret configuration to {path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("preflight", help="Read-only host inventory")
    for name in ("configure", "plan"):
        child = sub.add_parser(name)
        child.add_argument("--config", type=Path, default=Path("installarr.json"))
    args = parser.parse_args(argv)
    try:
        if args.action == "preflight":
            print(json.dumps(preflight(), indent=2))
        elif args.action == "configure":
            configure(args.config)
        else:
            result = plan(json.loads(args.config.read_text()))
            print(json.dumps(result, indent=2))
            return 2 if result["conflicts"] else 0
        return 0
    except (OSError, ValueError, TypeError, EOFError, KeyboardInterrupt) as error:
        # Do not echo arbitrary configuration contents or exception text.
        print(f"Unable to complete {args.action}: invalid input, inaccessible file, or interrupted operation ({type(error).__name__}).", file=sys.stderr)
        return 1
