"""One disposable writer; simulate NAS absence by removing only our private bind.

The authorized NFS mount is never unmounted. No ports or Docker networks created.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.accounts import provisioning_gate
from installarr.startup import container_mount_assertion, render_storage_guard

DOCKER = ["docker", "--host", "unix:///run/installarr-docker-test/docker.sock"]


def run(args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, check=False, timeout=90, **kwargs)
    if result.returncode:
        raise RuntimeError("Isolated test command failed: {}: {}".format(args[0], result.stderr.strip()))
    return result.stdout.strip()


def wait_for(check, seconds=25):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.25)
    raise ValueError("Physical Docker check timed out")


def main():
    provisioning_gate()
    if run(DOCKER + ["ps", "--all", "--quiet"]):
        raise ValueError("Test daemon has existing containers; preserved without changes")
    root_fd = os.open("/media/installarr", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    result = json.loads(run(["findmnt", "--json", "--target", "/proc/self/fd/{}".format(root_fd),
                             "--output", "TARGET,SOURCE,FSTYPE"], pass_fds=(root_fd,)))
    expected = {"target": "/media/installarr", "source": "192.168.1.102:/share/MD0_DATA/Public/installarr", "fstype": "nfs"}
    if result["filesystems"] != [expected]:
        raise ValueError("Unexpected isolated NAS mount; no writes attempted")
    image = run(DOCKER + ["image", "inspect", "busybox:1.37.0", "--format", "{{index .RepoDigests 0}}"])
    if "@sha256:" not in image:
        raise ValueError("Image must resolve to an immutable digest")
    fixture_name = ".installarr-docker-" + uuid.uuid4().hex
    local = Path(tempfile.mkdtemp(prefix="installarr-docker-guard-", dir="/run"))
    source = local / "source"
    source.mkdir(mode=0o777)
    source.chmod(0o777)  # Make the absent-mount test writable, so permissions cannot hide a gate failure.
    guard = local / "guard.sh"
    guard.write_text(render_storage_guard([container_mount_assertion(
        "/media/installarr/" + fixture_name, "/data", {"mountpoint": expected["target"],
            "source": expected["source"], "fstype": "nfs", "sentinel": "health"})]))
    guard.chmod(0o555)
    fixture_created = False
    container = None
    events = []

    def service_script(body):
        script = "import os\nos.setgroups([])\nos.setgid(2000)\nos.setuid(2000)\n" + body
        return run([sys.executable, "-B", "-c", script, str(root_fd), fixture_name], pass_fds=(root_fd,))

    def bind_fixture():
        run(["mount", "--bind", "/proc/{}/fd/{}/{}".format(os.getpid(), root_fd, fixture_name), str(source)])
        run(["mount", "--make-private", str(source)])

    def state():
        return json.loads(run(DOCKER + ["inspect", container]))[0]

    def log_size():
        try:
            return os.stat(fixture_name + "/probe.log", dir_fd=root_fd).st_size
        except FileNotFoundError:
            return 0

    try:
        service_script("""import sys
root = int(sys.argv[1]); name = sys.argv[2]
os.mkdir(name, 0o700, dir_fd=root)
directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
fd = os.open('health', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=directory)
with os.fdopen(fd, 'w') as handle:
    handle.write('Installarr isolated storage sentinel\\n'); handle.flush(); os.fsync(handle.fileno())
os.close(directory)
""")
        fixture_created = True
        bind_fixture()
        container = run(DOCKER + ["create", "--name", "installarr-storage-probe-" + uuid.uuid4().hex,
            "--label", "org.installarr.test=storage-startup-v1", "--network", "none", "--restart", "always",
            "--user", "2000:2000", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--read-only",
            "--mount", "type=bind,source={},target=/data,bind-propagation=rprivate".format(source),
            "--mount", "type=bind,source={},target=/installarr-storage-guard,readonly".format(guard),
            "--entrypoint", "/bin/sh", image, "/installarr-storage-guard", "/bin/sh", "-c",
            "while :; do printf 'x\\n' >> /data/probe.log; sleep 1; done"])
        run(DOCKER + ["start", container])
        wait_for(lambda: log_size() > 0)
        details = state()
        if details["HostConfig"]["NetworkMode"] != "none" or details["HostConfig"]["RestartPolicy"]["Name"] != "always":
            raise ValueError("Unexpected test container setup")
        events.append("healthy NAS: guarded non-root writer started")
        wait_for(lambda: log_size() >= 24, seconds=30)  # Run for >10 seconds so restart policy is established.
        run(["umount", str(source)])  # Only the new test bind; never /media/installarr.
        (source / "health").write_text("Installarr isolated storage sentinel\n")
        old_size = log_size()
        wait_for(lambda: log_size() > old_size)
        if (source / "probe.log").exists():
            raise ValueError("Running container wrote beneath absent bind mount")
        events.append("private propagation: running writer retained NAS; local fallback untouched")
        run(["systemctl", "restart", "installarr-test-docker.service"])
        wait_for(lambda: state()["State"]["ExitCode"] == 78 and state()["RestartCount"] > 0)
        if (source / "probe.log").exists():
            raise ValueError("Docker restart wrote beneath missing bind mount")
        events.append("daemon auto-restart with absent bind: entrypoint refused (78); local fallback untouched")
        # Manual stop suppresses the restart policy until the next daemon restart;
        # changing policy while an exit/restart is in flight can race with Engine.
        run(DOCKER + ["stop", "--time", "2", container])
        bind_fixture()
        before = log_size()
        run(DOCKER + ["start", container])
        wait_for(lambda: log_size() > before)
        events.append("restored NAS bind: explicit restart recovered")
        print(json.dumps({"image": image, "events": events, "result": "passed"}, indent=2))
    except Exception:
        if container:
            print(json.dumps({"failed_container_state": state()["State"],
                              "guard_logs": run(DOCKER + ["logs", "--tail", "4", container])}, indent=2))
            diagnostic = run(DOCKER + ["run", "--rm", "--network", "none", "--user", "2000:2000",
                "--mount", "type=bind,source={},target=/data,bind-propagation=rprivate".format(source),
                "--entrypoint", "/bin/sh", image, "-c",
                'while IFS= read -r line; do case "$line" in *" /data "*) printf "%s\\n" "$line";; esac; done < /proc/self/mountinfo; ls -ln /data/health; od -c /data/health'])
            print(json.dumps({"isolated_mount_diagnostic": diagnostic}, indent=2))
        raise
    finally:
        # Only explicit known files/directories are removed. Never recurse across a mount.
        if container:
            run(DOCKER + ["rm", "--force", container])
        if os.path.ismount(str(source)):
            run(["umount", str(source)])
        if fixture_created:
            service_script("""import sys
root = int(sys.argv[1]); name = sys.argv[2]
directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
for filename in ('probe.log', 'health'):
    try: os.unlink(filename, dir_fd=directory)
    except FileNotFoundError: pass
os.close(directory)
os.rmdir(name, dir_fd=root)
""")
        for filename in ("health", "probe.log"):
            try:
                (source / filename).unlink()
            except FileNotFoundError:
                pass
        source.rmdir()
        guard.unlink()
        local.rmdir()
        os.close(root_fd)


if __name__ == "__main__":
    main()
