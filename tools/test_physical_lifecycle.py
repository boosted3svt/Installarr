"""Real systemd lifecycle, storage failure and ownership-isolation test.

One guarded Sonarr plus one disposable unrelated BusyBox witness. Never unmounts
the actual NAS, changes networking or restarts the Docker daemon.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.accounts import provisioning_gate
from installarr.cli import save_config
from installarr.compose import DATA_TARGETS, write_bundle
from installarr.lifecycle import SERVICE_ROOT, SOCKET, install_service, service_status

DOCKER = ["docker", "--host", SOCKET]
BUSYBOX = "busybox@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"


def run(args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, check=False, timeout=120, **kwargs)
    if result.returncode:
        raise ValueError("Physical lifecycle command failed")
    return result.stdout.strip()


def wait_for(check, seconds=60):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if check():
            return
        time.sleep(0.25)
    raise ValueError("Physical lifecycle condition timed out")


def main():
    provisioning_gate()
    if run(DOCKER + ["ps", "--all", "--quiet"]):
        raise ValueError("Existing test containers preserved")
    nas = ".installarr-lifecycle-" + uuid.uuid4().hex
    name = "life-" + uuid.uuid4().hex[:12]
    project = "installarr-" + name
    unit = project + ".service"
    work = Path(tempfile.mkdtemp(prefix="installarr-lifecycle-", dir="/var/tmp"))
    root = os.open("/media/installarr", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    expected = {"target": "/media/installarr", "source": "192.168.1.102:/share/MD0_DATA/Public/installarr", "fstype": "nfs"}
    rows = json.loads(run(["findmnt", "--json", "--target", "/proc/self/fd/{}".format(root), "--output", "TARGET,SOURCE,FSTYPE"], pass_fds=(root,)))["filesystems"]
    if rows != [expected]:
        raise ValueError("Exact isolated mount required")
    (work / "configs").mkdir()
    (work / "configs" / "sonarr").mkdir(mode=0o700)
    os.chown(str(work / "configs" / "sonarr"), 2000, 2000)
    (work / "backups").mkdir()
    config = {"schema_version": 1, "apps": ["sonarr"], "timezone": "America/Chicago", "bind_address": "127.0.0.1",
              "plex_allowed_networks": "192.168.0.0/23", "service_user": {"name": "installarr-test", "uid": 2000, "gid": 2000},
              "project_directory": str(work / "project"), "storage": {
                  **{purpose: "/media/installarr/" + nas + "/" + purpose for purpose in DATA_TARGETS},
                  "configs": str(work / "configs"), "backups": str(work / "backups")},
              "storage_mounts": {**{purpose: {"kind": "existing", "mountpoint": expected["target"], "source": expected["source"],
                  "fstype": "nfs", "sentinel": "health"} for purpose in DATA_TARGETS}, "configs": {"kind": "local"}, "backups": {"kind": "local"}}}
    compose = DOCKER + ["compose", "--project-name", project, "--file", str(work / "project" / "compose.json")]
    created = installed = passed = False
    witness = None
    events = []

    def service_script(body):
        script = "import os,sys\nos.setgroups([])\nos.setgid(2000)\nos.setuid(2000)\n" + body
        return run([sys.executable, "-B", "-c", script, str(root), nas], pass_fds=(root,))

    def rename_health(remove):
        first, second = ("health", "health.off") if remove else ("health.off", "health")
        service_script("root=int(sys.argv[1]); name=sys.argv[2]\nfd=os.open(name+'/media',os.O_RDONLY|os.O_DIRECTORY,dir_fd=root)\nos.rename(" + repr(first) + "," + repr(second) + ",src_dir_fd=fd,dst_dir_fd=fd)\nos.close(fd)\n")

    def app_running():
        ids = run(compose + ["ps", "--all", "--quiet", "sonarr"])
        if not ids:
            return False
        return json.loads(run(DOCKER + ["inspect", ids]))[0]["State"]["Running"]

    def witness_running():
        return json.loads(run(DOCKER + ["inspect", witness]))[0]["State"]["Running"]

    def make_witness(collision=False):
        labels = ["--label", "com.docker.compose.project=" + project, "--label", "com.docker.compose.service=operator-witness"] if collision else []
        return run(DOCKER + ["run", "--detach", "--network", "none", "--user", "2000:2000", "--cap-drop", "ALL",
                            "--read-only", *labels, BUSYBOX, "sleep", "3600"])

    try:
        service_script("""root=int(sys.argv[1]); name=sys.argv[2]
os.mkdir(name,0o700,dir_fd=root)
base=os.open(name,os.O_RDONLY|os.O_DIRECTORY,dir_fd=root)
for purpose in ('media','downloads','incomplete'):
    os.mkdir(purpose,0o700,dir_fd=base)
    fd=os.open(purpose,os.O_RDONLY|os.O_DIRECTORY,dir_fd=base)
    file=os.open('health',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644,dir_fd=fd)
    with os.fdopen(file,'w') as handle: handle.write('Installarr lifecycle health\\n')
    os.close(fd)
os.close(base)
""")
        created = True
        save_config(work / "config.json", config)
        write_bundle(config)
        result = install_service(config, name)
        installed = True
        install_service(config, name)  # Identical installation rerun.
        run(["systemd-analyze", "verify", "/etc/systemd/system/" + unit])
        run(["systemctl", "enable", unit])
        if run(["systemctl", "is-enabled", unit]) != "enabled":
            raise ValueError("Enable readback failed")
        run(["systemctl", "disable", unit])
        witness = make_witness()
        run(["systemctl", "start", unit])
        wait_for(lambda: service_status(name).get("phase") == "containers_running" and app_running())
        wait_for(lambda: (work / "configs" / "sonarr" / "config.xml").exists())
        events.append("healthy storage: root-snapshot systemd service started guarded Sonarr")
        rename_health(True)
        started = time.monotonic()
        wait_for(lambda: service_status(name).get("phase") == "waiting_storage" and not app_running())
        stop_seconds = round(time.monotonic() - started, 2)
        if not witness_running():
            raise ValueError("Unrelated witness was stopped")
        events.append("sentinel loss: managed app stopped; unrelated container stayed running")
        run(["systemctl", "restart", unit])
        wait_for(lambda: service_status(name).get("phase") == "waiting_storage")
        if app_running() or not witness_running():
            raise ValueError("Unhealthy restart was unsafe")
        events.append("unit restart while unhealthy: startup refused")
        rename_health(False)
        wait_for(lambda: service_status(name).get("phase") == "containers_running" and app_running())
        events.append("sentinel restored: supervised recovery succeeded")
        run(["systemctl", "kill", "--signal=SIGKILL", "--kill-who=main", unit])
        rename_health(True)
        wait_for(lambda: not app_running())
        wait_for(lambda: service_status(name).get("phase") == "waiting_storage", seconds=40)
        if not witness_running():
            raise ValueError("Crash fallback touched unrelated witness")
        events.append("supervisor SIGKILL: ExecStopPost stopped app; restarted supervisor refused unhealthy storage")
        rename_health(False)
        wait_for(lambda: service_status(name).get("phase") == "containers_running" and app_running())
        run(DOCKER + ["rm", "--force", witness])
        witness = make_witness(collision=True)
        wait_for(lambda: service_status(name).get("phase") in ("blocked_policy_or_container_error", "retry_backoff") and not app_running())
        if not witness_running():
            raise ValueError("Foreign project collision was stopped")
        events.append("foreign project-label collision: own app stopped; foreign container preserved")
        run(DOCKER + ["rm", "--force", witness])
        witness = None
        wait_for(lambda: service_status(name).get("phase") == "containers_running" and app_running())
        run(["systemctl", "stop", unit])
        if app_running() or service_status(name).get("phase") != "stopped":
            raise ValueError("Manual service stop was not confirmed")
        events.append("manual service stop: managed container stopped and status persisted")
        passed = True
        print(json.dumps({"result": "passed", "unit": unit, "events": events, "sentinel_loss_stop_seconds": stop_seconds,
                          "boot_enable_disable": "passed_without_reboot", "state_directory": str(SERVICE_ROOT / name)}, indent=2))
    except Exception:
        print(json.dumps({"failed_unit": unit, "private_local_evidence": str(work),
                          "last_status": service_status(name) if installed else None}, indent=2))
        raise
    finally:
        if installed:
            run(["systemctl", "stop", unit])
            run(["systemctl", "disable", unit])
        if witness:
            run(DOCKER + ["rm", "--force", witness])
        if installed:
            run(compose + ["down", "--timeout", "10"])
        if created:
            service_script("""root=int(sys.argv[1]); name=sys.argv[2]
base=os.open(name,os.O_RDONLY|os.O_DIRECTORY,dir_fd=root)
for purpose in ('media','downloads','incomplete'):
    fd=os.open(purpose,os.O_RDONLY|os.O_DIRECTORY,dir_fd=base)
    for marker in ('health','health.off'):
        try: os.unlink(marker,dir_fd=fd)
        except FileNotFoundError: pass
    os.close(fd); os.rmdir(purpose,dir_fd=base)
os.close(base); os.rmdir(name,dir_fd=root)
""")
        os.close(root)
        if passed:
            shutil.rmtree(str(work))


if __name__ == "__main__":
    main()
