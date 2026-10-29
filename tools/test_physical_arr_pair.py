"""Disposable guarded Sonarr/Radarr pair; no ports, networks or downloads.

Root-only, uses only the confirmed NAS test subtree plus newly created local
fixtures. Local private evidence is retained on failure; NAS cleanup is explicit.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.accounts import provisioning_gate
from installarr.arr import AppAPIError, ArrClient, DockerHTTP
from installarr.cli import main as cli_main, save_config
from installarr.compose import DATA_TARGETS, IMAGES, application_paths, bind, write_bundle
from installarr.credentials import initialize_credentials, read_private_credentials

SOCKET = "unix:///run/installarr-docker-test/docker.sock"
DOCKER = ["docker", "--host", SOCKET]
APPS = ("sonarr", "radarr")


def run(args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=120, check=False, **kwargs)
    if result.returncode:
        raise ValueError("Isolated pair command failed")
    return result.stdout.strip()


def wait_for(action, seconds=100):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = action()
            if result:
                return result
        except (AppAPIError, FileNotFoundError, ET.ParseError):
            pass
        time.sleep(0.5)
    raise ValueError("Isolated application readiness timed out")


def main():
    provisioning_gate()
    if run(DOCKER + ["ps", "--all", "--quiet"]):
        raise ValueError("Test daemon contains existing containers; preserved")
    root_fd = os.open("/media/installarr", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    expected = {"target": "/media/installarr", "source": "192.168.1.102:/share/MD0_DATA/Public/installarr", "fstype": "nfs"}
    actual = json.loads(run(["findmnt", "--json", "--target", "/proc/self/fd/{}".format(root_fd),
                             "--output", "TARGET,SOURCE,FSTYPE"], pass_fds=(root_fd,)))
    if actual["filesystems"] != [expected]:
        raise ValueError("Exact isolated mount required before writes")
    name = ".installarr-arr-$literal-" + uuid.uuid4().hex
    work = Path(tempfile.mkdtemp(prefix="installarr-arr-pair-", dir="/var/tmp"))
    project = "installarr-pair-" + uuid.uuid4().hex[:12]
    (work / "configs").mkdir()
    (work / "backups").mkdir()
    local_mount = json.loads(run(["findmnt", "--json", "--target", str(work), "--output", "TARGET,SOURCE,FSTYPE"]))["filesystems"][0]
    if local_mount["fstype"] not in ("ext4", "xfs", "btrfs"):
        raise ValueError("App databases require a verified local test filesystem")
    for app in APPS:
        directory = work / "configs" / app
        directory.mkdir(mode=0o700)
        os.chown(str(directory), 2000, 2000)
    config = {"schema_version": 1, "apps": list(APPS), "timezone": "America/Chicago",
              "bind_address": "127.0.0.1", "plex_allowed_networks": "192.168.0.0/23",
              "service_user": {"name": "installarr-test", "uid": 2000, "gid": 2000},
              "project_directory": str(work / "project"),
              "storage": {**{purpose: "/media/installarr/" + name + "/" + purpose for purpose in DATA_TARGETS},
                          "configs": str(work / "configs"), "backups": str(work / "backups")},
              "storage_mounts": {**{purpose: {"kind": "existing", "mountpoint": expected["target"],
                  "source": expected["source"], "fstype": "nfs", "sentinel": "health"} for purpose in DATA_TARGETS},
                  "configs": {"kind": "local"}, "backups": {"kind": "local"}}}
    compose = DOCKER + ["compose", "--project-name", project, "--file", str(work / "project" / "compose.json")]
    created = False
    deployed = False
    passed = False

    def service_script(body):
        script = "import os,sys\nos.setgroups([])\nos.setgid(2000)\nos.setuid(2000)\n" + body
        return run([sys.executable, "-B", "-c", script, str(root_fd), name], pass_fds=(root_fd,))

    def client(app):
        container = run(compose + ["ps", "--all", "--quiet", app])
        key = ET.parse(str(work / "configs" / app / "config.xml")).findtext("ApiKey")
        return container, ArrClient(DockerHTTP(SOCKET, container, IMAGES[app]["port"], key),
                                    expected_version=IMAGES[app]["version"].split("-ls", 1)[0])

    def ready(app):
        container, api = client(app)
        status = api.json("GET", "system/status")
        expected_version = IMAGES[app]["version"].split("-ls", 1)[0]
        if not isinstance(status, dict) or status.get("version") != expected_version:
            raise ValueError("Runtime application version differs from image catalog")
        return container, api, status["version"]

    try:
        service_script("""root=int(sys.argv[1]); name=sys.argv[2]
os.mkdir(name, 0o700, dir_fd=root)
base=os.open(name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=root)
for purpose in ('media','downloads','incomplete'):
    os.mkdir(purpose, 0o700, dir_fd=base)
    directory=os.open(purpose, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=base)
    fd=os.open('health', os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o644, dir_fd=directory)
    with os.fdopen(fd,'w') as handle:
        handle.write('Installarr pair health sentinel\\n'); handle.flush(); os.fsync(handle.fileno())
    if purpose=='media':
        for leaf in ('TV','Movies'): os.mkdir(leaf, 0o700, dir_fd=directory)
    os.close(directory)
os.close(base)
""")
        created = True
        save_config(work / "config.json", config)
        if cli_main(["render-compose", "--config", str(work / "config.json")]) != 0:
            raise ValueError("Compose renderer CLI failed")
        write_bundle(config)
        model = json.loads(run(compose + ["config", "--format", "json"]))
        if any(service.get("ports") or service.get("network_mode") != "none" for service in model["services"].values()):
            raise ValueError("Compose must not expose bootstrap services")
        credentials = {"username": "installarr-test-admin", "password": secrets.token_urlsafe(36)}
        initialize_credentials(work / "secrets", lambda: credentials)
        credentials = read_private_credentials(work / "secrets" / "gui-admin.json")
        deployed = True
        run(compose + ["up", "--detach", "--no-build", "--pull", "never"])
        report = {}
        root_ids = {}
        for app in APPS:
            container, api, version = wait_for(lambda app=app: ready(app))
            authentication = api.configure_admin(credentials)
            root_ids[app] = api.ensure_root(application_paths(config, app)["media_root"])
            api.configure_admin(credentials)
            if api.ensure_root(application_paths(config, app)["media_root"]) != root_ids[app]:
                raise ValueError("Rerun changed application root ID")
            identities = run(DOCKER + ["exec", container, "/bin/sh", "-c", '''
for status in /proc/[0-9]*/status; do
  name= uid= gid=
  while read -r key a b c d; do
    case "$key" in Name:) name=$a ;; Uid:) uid=$b ;; Gid:) gid=$b ;; esac
  done < "$status" 2>/dev/null || continue
  case "$name" in Sonarr|Radarr) printf '%s %s %s\\n' "$name" "$uid" "$gid" ;; esac
done
''']).splitlines()
            process = [row.split() for row in identities if row.startswith(app.capitalize() + " ")]
            if len(process) != 1 or process[0][1:] != ["2000", "2000"]:
                raise ValueError("Application runtime UID/GID readback failed")
            databases = [path for path in (work / "configs" / app).iterdir() if path.name.lower() == app + ".db"]
            if len(databases) != 1 or (databases[0].stat().st_uid, databases[0].stat().st_gid) != (2000, 2000):
                raise ValueError("Local app database ownership readback failed")
            report[app] = {"version": version, "image_version": IMAGES[app]["version"], "image": IMAGES[app]["image"],
                           "uid": 2000, "gid": 2000, "local_database": True,
                           "authentication_and_root_rerun": "passed", "authentication_http_status": authentication}
        run(compose + ["restart"])
        for app in APPS:
            _, api, _ = wait_for(lambda app=app: ready(app))
            api.verify_admin(credentials)
            if api.ensure_root(application_paths(config, app)["media_root"]) != root_ids[app]:
                raise ValueError("Application restart changed root IDs")
            report[app]["restart_persistence"] = "passed"
        run(compose + ["down", "--timeout", "10"])
        before = {app: hashlib.sha256((work / "configs" / app / "config.xml").read_bytes()).hexdigest() for app in APPS}
        fallback = work / "fallback"
        fallback.mkdir(mode=0o777)
        fallback.chmod(0o777)
        (fallback / "health").write_text("Installarr pair health sentinel\n")
        override = work / "missing-mount.json"
        override.write_text(json.dumps({"services": {app: {"volumes": [bind(fallback, "/data/media")]} for app in APPS}}))
        wrong = compose + ["--file", str(override)]
        run(wrong + ["up", "--detach", "--no-build", "--pull", "never"])
        for app in APPS:
            def refused(app=app):
                container = run(wrong + ["ps", "--all", "--quiet", app])
                state = json.loads(run(DOCKER + ["inspect", container]))[0]["State"]
                return not state["Running"] and state["ExitCode"] == 78
            wait_for(refused)
            if hashlib.sha256((work / "configs" / app / "config.xml").read_bytes()).hexdigest() != before[app]:
                raise ValueError("Rejected app entrypoint changed configuration")
            report[app]["wrong_filesystem_before_init"] = "passed"
        if sorted(path.name for path in fallback.iterdir()) != ["health"]:
            raise ValueError("Rejected app wrote to local fallback")
        run(wrong + ["down", "--timeout", "10"])
        run(compose + ["up", "--detach", "--no-build", "--pull", "never"])
        for app in APPS:
            _, api, _ = wait_for(lambda app=app: ready(app))
            api.verify_admin(credentials)
            if api.ensure_root(application_paths(config, app)["media_root"]) != root_ids[app]:
                raise ValueError("Recovery changed app roots")
            report[app]["recovery"] = "passed"
        passed = True
        print(json.dumps({"result": "passed", "apps": report, "no_ports_or_networks": True,
                          "local_database_filesystem": local_mount["fstype"], "downloads_tested": False}, indent=2))
    finally:
        if deployed:
            run(compose + ["down", "--timeout", "10"])
        if created:
            service_script("""root=int(sys.argv[1]); name=sys.argv[2]
base=os.open(name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=root)
for purpose in ('media','downloads','incomplete'):
    directory=os.open(purpose, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=base)
    os.unlink('health', dir_fd=directory)
    if purpose=='media':
        for leaf in ('TV','Movies'): os.rmdir(leaf, dir_fd=directory)
    os.close(directory); os.rmdir(purpose, dir_fd=base)
os.close(base); os.rmdir(name, dir_fd=root)
""")
        os.close(root_fd)
        if passed:
            shutil.rmtree(str(work))
        else:
            print(json.dumps({"private_local_failure_evidence": str(work), "credentials_not_printed": True}))


if __name__ == "__main__":
    main()
