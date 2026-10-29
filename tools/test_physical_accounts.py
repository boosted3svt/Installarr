"""Explicit root-only account/resume test on the authorized isolated host.

Creates only installarr-test 2000:2000 and reserved nbxyz 911:1001.
Retains those identities and private checkpoints for subsequent isolated tests.
Does not provision storage, packages, containers or application configuration.
"""
import json
import os
from pathlib import Path
import pwd
import sys
import tempfile

# Permit direct invocation from the checkout without an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.accounts import ensure_identity, provisioning_gate, run_account_command
from installarr.cli import identity_conflicts, main as cli_main, save_config
from installarr.execution import Execution


def main():
    provisioning_gate()
    identities = [{"name": "installarr-test", "uid": 2000, "gid": 2000},
                  {"name": "nbxyz", "uid": 911, "gid": 1001}]
    for item in identities:
        if identity_conflicts(item["name"], item["uid"], item["gid"]):
            raise ValueError("Test identity collision; no existing identities will be changed")
    state = Path("/var/lib/installarr-physical-test-accounts")
    operation = {"operation": "accounts-v1", "identities": identities}
    try:
        pwd.getpwnam(identities[0]["name"])
        initial_user_absent = False
    except KeyError:
        initial_user_absent = True
    interrupted = False
    if initial_user_absent:
        def interrupt_after_group(args):
            nonlocal interrupted
            run_account_command(args)
            if args[0] == "/usr/sbin/groupadd":
                interrupted = True
                raise RuntimeError("Intentional interruption after group creation")
        try:
            with Execution(state, operation) as execution:
                execution.reconcile(identities[0]["name"], lambda: ensure_identity(
                    identities[0], identity_conflicts, interrupt_after_group))
        except RuntimeError:
            if not interrupted:
                raise
        if interrupted:
            saved = json.loads((state / "state.json").read_text())
            assert saved["steps"]["installarr-test"] == "failed"
            try:
                pwd.getpwnam("installarr-test")
            except KeyError:
                pass
            else:
                raise ValueError("User was unexpectedly created before interruption")
    with tempfile.TemporaryDirectory(prefix="installarr-accounts-", dir="/var/tmp") as directory:
        config = {
            "schema_version": 1, "apps": ["sonarr", "netbootxyz"],
            "timezone": "America/Chicago", "bind_address": "127.0.0.1",
            "plex_allowed_networks": "192.168.0.0/23", "service_user": identities[0],
            "project_directory": directory + "/unused-project",
            "storage": {purpose: directory + "/unused-" + purpose for purpose in
                        ("media", "downloads", "incomplete", "configs", "backups")},
        }
        config_path = Path(directory) / "config.json"
        save_config(config_path, config)
        args = ["prepare-accounts", "--config", str(config_path), "--state-directory", str(state)]
        if cli_main(args) != 0:
            raise ValueError("Account preparation CLI failed")
        before = {item["name"]: tuple(pwd.getpwnam(item["name"])) for item in identities}
        if cli_main(args) != 0:
            raise ValueError("Account rerun CLI failed")
        after = {item["name"]: tuple(pwd.getpwnam(item["name"])) for item in identities}
        if before != after:
            raise ValueError("Completed rerun changed account records")
        for item in identities:
            user = pwd.getpwnam(item["name"])
            if (user.pw_uid, user.pw_gid, user.pw_dir, user.pw_shell) != (
                    item["uid"], item["gid"], "/nonexistent", "/usr/sbin/nologin"):
                raise ValueError("Identity/home/shell readback mismatch")
            if os.getgrouplist(item["name"], item["gid"]) != [item["gid"]]:
                raise ValueError("Unexpected supplementary memberships")
    print(json.dumps({"intentional_group_interruption": interrupted,
                      "cli_prepare_and_rerun": "passed", "identities": identities,
                      "state_directory": str(state), "accounts_retained": True}, indent=2))


if __name__ == "__main__":
    main()
