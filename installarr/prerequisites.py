"""Storage client prerequisites, separate from mount and persistence changes."""
from pathlib import Path
import re

from .accounts import HostPrerequisiteError, provisioning_gate
from .dockerhost import APT, installed_version, run
from .execution import Execution
from .hostplan import preparation_plan


def verify_signed_sources():
    paths = [Path("/etc/apt/sources.list"), *Path("/etc/apt/sources.list.d").glob("*.list"),
             *Path("/etc/apt/sources.list.d").glob("*.sources")]
    for path in paths:
        if not path.exists():
            continue
        text = "\n".join(line.split("#", 1)[0] for line in path.read_text().splitlines())
        if re.search(r"\b(?:trusted|allow-insecure|allow-downgrade-to-insecure)\s*[:=]\s*(?:yes|true|1)\b", text, re.I):
            raise HostPrerequisiteError("Repository bypasses signature checks; preserved for operator review")


def prepare_prerequisites(config, state_directory=Path("/var/lib/installarr-storage-prerequisites")):
    from .cli import validate
    validate(config)
    provisioning_gate()
    plan = preparation_plan(config)
    packages = sorted(set(plan["required_storage_packages"] + plan["required_application_packages"]))
    if set(packages) - {"nfs-common", "cifs-utils", "openssl"}:
        raise ValueError("Unsupported storage prerequisite")
    with Execution(state_directory, {"operation": "storage-prerequisites-v1", "packages": packages}) as execution:
        def reconcile():
            missing = [package for package in packages if installed_version(package) is None]
            if missing:
                verify_signed_sources()
                run(APT + ["-o", "APT::Update::Error-Mode=any", "update"])
                run(APT + ["install", "--yes", "--no-remove", "--no-install-recommends", *missing])
            if any(installed_version(package) is None for package in packages):
                raise HostPrerequisiteError("Storage prerequisite readback failed")
        execution.reconcile("packages", reconcile)
    return {"status": "verified", "packages": {package: installed_version(package) for package in packages},
            "note": "Storage/authentication helper packages only. No mounts, directories, fstab, service identities or media ownership changed."}
