"""Signed Docker package staging for a fresh host; never starts a daemon.

Standard services remain masked so package installation and reboot cannot create
bridges/firewall rules before explicit, scoped daemon setup.
"""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

from .atomic import publish_noreplace
from .accounts import HostPrerequisiteError, provisioning_gate
from .execution import Execution

PACKAGES = ("docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin", "docker-compose-plugin")
CONFLICTS = ("docker.io", "docker-compose", "docker-compose-v2", "docker-doc", "docker-buildx", "podman-docker", "containerd", "runc")
UNITS = ("docker.service", "docker.socket", "containerd.service")
# Official signed Focal archive, installed/binary-tested in Ubuntu20.04 userspace.
# This is a compatibility path, not a claim of current upstream Focal support.
FOCAL_PACKAGES = {
    "docker-ce": "5:28.1.1-1~ubuntu.20.04~focal",
    "docker-ce-cli": "5:28.1.1-1~ubuntu.20.04~focal",
    "containerd.io": "1.7.27-1",
    "docker-buildx-plugin": "0.23.0-1~ubuntu.20.04~focal",
    "docker-compose-plugin": "2.35.1-1~ubuntu.20.04~focal",
}
KEY_FINGERPRINT = "9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
SOURCE = Path("/etc/apt/sources.list.d/installarr-docker.sources")
KEY = Path("/etc/apt/keyrings/installarr-docker.asc")


def run(args, timeout=600):
    result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                            timeout=timeout, check=False, env={
                                "PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C",
                                "DEBIAN_FRONTEND": "noninteractive", "NEEDRESTART_MODE": "l"})
    if result.returncode:
        raise HostPrerequisiteError("Docker preparation command failed; inspect package/repository state before retrying")
    return result.stdout.strip()


def installed_version(package):
    result = subprocess.run(["dpkg-query", "-W", "-f=${db:Status-Status} ${Version}", package],
                            capture_output=True, text=True, timeout=10, check=False)
    if result.returncode:
        return None
    parts = result.stdout.split()
    if not parts or parts[0] in ("not-installed", "config-files"):
        return None
    if parts[0] != "installed" or len(parts) != 2:
        raise HostPrerequisiteError("Partially configured packages require operator reconciliation")
    return parts[1]


def trusted_directory(path):
    path = Path(path)
    if path.resolve() != path:
        raise ValueError("System directory contains symlinks")
    path.mkdir(mode=0o755, exist_ok=True)
    for candidate in (path, *path.parents):
        info = candidate.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("System directory is not root-controlled")


def ensure_file(path, data, mode=0o644):
    """Create atomically without replacement, or require identical trusted content."""
    path = Path(path)
    trusted_directory(path.parent)
    def verify_existing():
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1
                    or stat.S_IMODE(info.st_mode) != mode or handle.read(len(data) + 1) != data):
                raise HostPrerequisiteError("Existing system file differs; preserved without replacement")
    if os.path.lexists(str(path)):
        verify_existing()
        return
    fd, temporary = tempfile.mkstemp(prefix=".installarr-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        try:
            publish_noreplace(temporary, path)
        except FileExistsError:
            # Another deployment may have atomically published this same runtime
            # artifact. Reuse only after the complete ownership/mode/byte check.
            verify_existing()
        if os.path.exists(temporary):
            os.unlink(temporary)
        directory_fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def repository_text(codename, architecture):
    # Do not equate our broad Ubuntu acceptance with upstream Docker support.
    if codename not in ("focal", "jammy", "noble", "resolute", "stonking"):
        raise HostPrerequisiteError("This Ubuntu release needs a separately validated Docker installation path")
    if codename == "focal" and architecture != "amd64":
        raise HostPrerequisiteError("The archived Focal compatibility path has only been validated on amd64")
    if architecture not in ("amd64", "arm64", "armhf", "s390x", "ppc64el"):
        raise HostPrerequisiteError("Unsupported Docker architecture")
    return ("Types: deb\nURIs: https://download.docker.com/linux/ubuntu\n"
            "Suites: {}\nComponents: stable\nArchitectures: {}\nSigned-By: {}\n".format(
                codename, architecture, KEY)).encode()


def select_version(output):
    for line in output.splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) == 3 and parts[2].startswith("https://download.docker.com/linux/ubuntu "):
            if re.fullmatch(r"[0-9][A-Za-z0-9.+:~_-]*", parts[1]):
                return parts[1]
    raise HostPrerequisiteError("No package version from Docker's official repository")


def verify_key(key_text, runner=run):
    with tempfile.TemporaryDirectory(prefix="installarr-key-", dir="/var/tmp") as directory:
        path = Path(directory) / "docker.asc"
        path.write_text(key_text)
        output = runner(["gpg", "--batch", "--homedir", directory, "--show-keys", "--with-colons", str(path)])
    primary_fingerprints = []
    primary = False
    for line in output.splitlines():
        fields = line.split(":")
        if fields[0] in ("pub", "sub"):
            primary = fields[0] == "pub"
        elif fields[0] == "fpr" and primary:
            primary_fingerprints.append(fields[9])
            primary = False
    if primary_fingerprints != [KEY_FINGERPRINT]:
        raise HostPrerequisiteError("Docker signing key fingerprint changed; no repository installed")


APT = ["apt-get", "-o", "APT::Get::AllowUnauthenticated=false", "-o",
       "Acquire::AllowInsecureRepositories=false", "-o", "Acquire::AllowDowngradeToInsecureRepositories=false"]


def prepare_docker(state_directory=Path("/var/lib/installarr-docker-install")):
    provisioning_gate()
    release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    codename = release.get("UBUNTU_CODENAME", release.get("VERSION_CODENAME", "")).strip('"')
    architecture = run(["dpkg", "--print-architecture"])
    source_text = repository_text(codename, architecture)
    from .prerequisites import verify_signed_sources
    verify_signed_sources()
    with Execution(state_directory, {"operation": "docker-packages-masked-v1", "codename": codename,
                                     "architecture": architecture}) as execution:
        managed_packages = execution.state["steps"].get("packages") in ("running", "failed", "verified")
        if any(installed_version(package) for package in CONFLICTS):
            raise HostPrerequisiteError("Conflicting container packages found; none were removed")
        if not managed_packages and (any(installed_version(package) for package in PACKAGES)
                or Path("/var/lib/docker").exists() or Path("/run/docker.sock").exists()
                or Path("/etc/docker/daemon.json").exists()):
            raise HostPrerequisiteError("Existing Docker installation/data found; preserved for separate review")
        sources = [Path("/etc/apt/sources.list"), *Path("/etc/apt/sources.list.d").glob("*.list"),
                   *Path("/etc/apt/sources.list.d").glob("*.sources")]
        for path in sources:
            if path != SOURCE and path.exists() and "download.docker.com" in path.read_text():
                raise HostPrerequisiteError("Existing Docker repository found; preserved without duplicate entries")

        def mask_services():
            for unit in UNITS:
                path = Path("/etc/systemd/system") / unit
                if os.path.lexists(str(path)) and not (path.is_symlink() and os.readlink(str(path)) == "/dev/null"
                        and execution.state["steps"].get("service-masks") in ("running", "failed", "verified")):
                    raise HostPrerequisiteError("Existing service override found; preserved")
                active = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=10)
                if active.stdout.strip() in ("active", "activating", "reloading"):
                    raise HostPrerequisiteError("Existing container service is running; preserved")
            run(["systemctl", "mask", *UNITS])
            for unit in UNITS:
                enabled = subprocess.run(["systemctl", "is-enabled", unit], capture_output=True, text=True, timeout=10)
                if enabled.stdout.strip() != "masked":
                    raise HostPrerequisiteError("Service mask readback failed")
        execution.reconcile("service-masks", mask_services)

        def prerequisites():
            missing = [package for package in ("ca-certificates", "curl", "gnupg") if not installed_version(package)]
            if missing:
                run(APT + ["-o", "APT::Update::Error-Mode=any", "update"])
                run(APT + ["install", "--yes", "--no-remove", "--no-install-recommends", *missing])
        execution.reconcile("prerequisites", prerequisites)

        def repository():
            key_text = run(["curl", "--fail", "--silent", "--show-error", "--proto", "=https", "--tlsv1.2",
                            "--connect-timeout", "10", "--max-time", "60", "https://download.docker.com/linux/ubuntu/gpg"])
            verify_key(key_text)
            ensure_file(KEY, (key_text + "\n").encode())
            ensure_file(SOURCE, source_text)
            run(APT + ["-o", "APT::Update::Error-Mode=any", "update"])
        execution.reconcile("repository", repository)

        versions = execution.state.get("package_versions")
        if versions is None:
            versions = {package: select_version(run(["apt-cache", "madison", package])) for package in PACKAGES}
            if codename == "focal" and versions != FOCAL_PACKAGES:
                raise HostPrerequisiteError("Official Focal archive selection changed; keep the tested package set for review")
            if versions["docker-ce"] != versions["docker-ce-cli"]:
                raise HostPrerequisiteError("Docker Engine/CLI package versions differ")
            execution.state["package_versions"] = versions
            execution._save()
        if (not isinstance(versions, dict) or set(versions) != set(PACKAGES)
                or any(not isinstance(value, str) or not re.fullmatch(r"[0-9][A-Za-z0-9.+:~_-]*", value) for value in versions.values())):
            raise ValueError("Invalid saved package selection")

        def packages():
            missing = []
            for package, desired in versions.items():
                actual = installed_version(package)
                if actual is not None and actual != desired:
                    raise HostPrerequisiteError("Installed Docker package version differs; no automatic upgrade or downgrade")
                if actual is None:
                    missing.append(package + "=" + desired)
            if missing:
                run(APT + ["install", "--yes", "--no-remove", "--no-install-recommends", *missing])
            if any(installed_version(package) != desired for package, desired in versions.items()):
                raise HostPrerequisiteError("Docker package version readback failed")
        execution.reconcile("packages", packages)
        execution.reconcile("service-masks", mask_services)
    return {"status": "staged", "package_versions": versions, "standard_services": "masked",
            "release_policy": "archived Focal compatibility; not current upstream support" if codename == "focal" else "current official repository",
            "note": "No Docker daemon started. Standard reference startup and isolated test-daemon startup are separate explicit actions."}


def prepare_test_daemon():
    """Explicit isolated physical-test daemon; standard Docker units stay masked."""
    provisioning_gate()
    directory = Path("/var/lib/installarr-docker-test")
    configuration = {
        "hosts": ["unix:///run/installarr-docker-test/docker.sock"], "group": "root",
        "data-root": str(directory / "data"), "exec-root": "/run/installarr-docker-test/exec",
        "pidfile": "/run/installarr-docker-test/docker.pid", "bridge": "none",
        "iptables": False, "ip6tables": False, "ip-forward": False, "ip-masq": False,
        "userland-proxy": False, "live-restore": False,
        "features": {"containerd-snapshotter": False}, "storage-driver": "overlay2",
    }
    unit = """[Unit]
Description=Installarr isolated Docker test daemon (no bridge or firewall changes)
After=local-fs.target

[Service]
Type=notify
ExecStart=/usr/bin/dockerd --config-file=/var/lib/installarr-docker-test/daemon.json
RuntimeDirectory=installarr-docker-test
RuntimeDirectoryMode=0700
Delegate=yes
KillMode=process
Restart=on-failure
RestartSec=5
TimeoutStartSec=90
TimeoutStopSec=60
TasksMax=infinity
"""
    with Execution(directory, {"operation": "networkless-test-daemon-v1"}) as execution:
        def configure():
            for name in UNITS:
                result = subprocess.run(["systemctl", "is-enabled", name], capture_output=True, text=True, timeout=10)
                if result.stdout.strip() != "masked":
                    raise HostPrerequisiteError("Standard Docker/containerd services must remain masked")
            ensure_file(directory / "daemon.json", (json.dumps(configuration, indent=2) + "\n").encode(), 0o600)
            run(["dockerd", "--validate", "--config-file=" + str(directory / "daemon.json")])
            ensure_file(Path("/etc/systemd/system/installarr-test-docker.service"), unit.encode())
            run(["systemctl", "daemon-reload"])
        execution.reconcile("configuration", configure)
        execution.reconcile("start", lambda: run(["systemctl", "start", "installarr-test-docker.service"]))
        version = run(["docker", "--host", configuration["hosts"][0], "version", "--format", "{{.Server.Version}}"])
        compose = run(["docker", "compose", "version", "--short"])
    return {"status": "running", "engine": version, "compose": compose,
            "socket": configuration["hosts"][0], "boot_enabled": False,
            "note": "Dedicated test daemon only; no bridge, published ports, forwarding or firewall management."}
