"""Narrow host adapter: create missing identities, never change existing ones."""
import grp
import os
from pathlib import Path
import pwd
import re
import subprocess

from .execution import Execution


class HostPrerequisiteError(ValueError):
    """Fixed, nonsecret prerequisite diagnostics safe for CLI output."""


def supported_ubuntu(release):
    version = release.get("VERSION_ID", "")
    if release.get("ID") != "ubuntu" or not re.fullmatch(r"[0-9]+\.[0-9]+", version):
        return False
    return tuple(int(part) for part in version.split(".")) >= (20, 4)


def provisioning_gate():
    release = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            release[key] = value.strip('"')
    if not supported_ubuntu(release):
        raise HostPrerequisiteError("Host provisioning requires Ubuntu 20.04 or newer")
    if os.geteuid() != 0:
        raise HostPrerequisiteError("Account preparation requires root")


def run_account_command(args):
    # No shell, inherited stdin or command output (which could disclose host data).
    result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=30, check=False,
                            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"})
    if result.returncode:
        raise ValueError("Account command failed; inspect identity before retrying")


def ensure_identity(identity, conflicts, run=run_account_command):
    name, uid, gid = (identity[key] for key in ("name", "uid", "gid"))
    if conflicts(name, uid, gid):
        raise ValueError("Account collision; existing identities are never modified")
    try:
        grp.getgrnam(name)
    except KeyError:
        run(["/usr/sbin/groupadd", "--gid", str(gid), "--", name])
    # Reinspect after each command, including interrupted previous attempts.
    if grp.getgrnam(name).gr_gid != gid or conflicts(name, uid, gid):
        raise ValueError("Group readback or identity collision")
    try:
        pwd.getpwnam(name)
    except KeyError:
        run(["/usr/sbin/useradd", "--uid", str(uid), "--gid", str(gid),
             "--no-create-home", "--home-dir", "/nonexistent", "--shell", "/usr/sbin/nologin",
             "--no-log-init", "--", name])
    user = pwd.getpwnam(name)
    if (user.pw_uid, user.pw_gid) != (uid, gid) or conflicts(name, uid, gid):
        raise ValueError("User readback or identity collision")


def prepare_accounts(config, state_directory, conflicts):
    provisioning_gate()
    identities = [config["service_user"]]
    if "netbootxyz" in config["apps"]:
        reserved = {"name": "nbxyz", "uid": 911, "gid": 1001}
        if identities[0] != reserved:
            if (identities[0]["name"] == "nbxyz" or identities[0]["uid"] == 911
                    or identities[0]["gid"] == 1001):
                raise ValueError("Media identity overlaps netbootxyz reservation")
            identities.append(reserved)
    # Check every identity before the first mutation.
    if any(conflicts(item["name"], item["uid"], item["gid"]) for item in identities):
        raise ValueError("Account collision")
    with Execution(state_directory, {"operation": "accounts-v1", "identities": identities}) as execution:
        for identity in identities:
            execution.reconcile(identity["name"], lambda item=identity: ensure_identity(item, conflicts))
    return {"accounts": identities, "status": "verified", "note": "Account identity only; application runtime permissions remain unverified."}
