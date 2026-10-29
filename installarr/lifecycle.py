"""Scoped Compose lifecycle with bounded read-only storage supervision."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import threading
import time

from .accounts import provisioning_gate
from .compose import DATA_TARGETS, bundle_identity, private_artifact, render_bundle
from .dockerhost import ensure_file, trusted_directory
from .execution import Execution
from .hostplan import storage_assertions

SOCKET = "unix:///run/installarr-docker-test/docker.sock"
SERVICE_ROOT = Path("/var/lib/installarr-services")
ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}

# A separate process owns all potentially blocking filesystem reads. It opens only
# asserted directories, rechecks the held mount, then drops ALL supplementary IDs.
HEALTH_WORKER = r'''
import json, os, pathlib, stat, subprocess, sys
fds=[]
try:
    spec=json.load(sys.stdin)
    for check in spec['checks']:
        path=check['path']
        result=subprocess.run(['findmnt','--json','--target',path,'--output','TARGET,SOURCE,FSTYPE,OPTIONS'],capture_output=True,text=True,timeout=2,check=True)
        rows=json.loads(result.stdout)['filesystems']
        expected=check['expected']
        if len(rows)!=1 or any(rows[0][key]!=expected[key] for key in ('target','source','fstype')):
            raise ValueError('mount')
        if str(pathlib.Path(path).resolve())!=path:
            raise ValueError('path')
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        fds.append((check,fd))
        result=subprocess.run(['findmnt','--json','--target','/proc/self/fd/'+str(fd),'--output','TARGET,SOURCE,FSTYPE,OPTIONS'],pass_fds=(fd,),capture_output=True,text=True,timeout=2,check=True)
        rows=json.loads(result.stdout)['filesystems']
        if len(rows)!=1 or any(rows[0][key]!=expected[key] for key in ('target','source','fstype')) or (not check.get('read_only') and 'rw' not in rows[0]['options'].split(',')):
            raise ValueError('held_mount')
    uid,gid=spec['uid'],spec['gid']
    if type(uid) is not int or type(gid) is not int or uid<=0 or gid<=0:
        raise ValueError('identity')
    os.setgroups([]); os.setgid(gid); os.setuid(uid)
    for check,directory in fds:
        access=os.open('.',os.O_RDONLY|os.O_DIRECTORY,dir_fd=directory)
        os.close(access)
        if 'sentinel' not in check:
            continue
        fd=os.open(check['sentinel'],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode) or b'\n' not in os.read(fd,4096):
                raise ValueError('sentinel')
        finally:
            os.close(fd)
    print(json.dumps({'healthy':True,'uid':os.geteuid(),'gid':os.getegid(),'groups':os.getgroups()}))
except Exception:
    print(json.dumps({'healthy':False}))
finally:
    for check,fd in fds:
        os.close(fd)
'''


class LifecycleError(ValueError):
    pass


def command(args, timeout=25):
    try:
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=timeout, check=False, env=ENV, cwd="/")
    except (OSError, subprocess.SubprocessError):
        raise LifecycleError("Container control unavailable") from None
    if result.returncode:
        raise LifecycleError("Container control request failed")
    return result.stdout.strip()


def root_json(path):
    path = Path(path)
    if path.resolve() != path:
        raise LifecycleError("Private service definition contains a symlink")
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1 or info.st_size > 65536):
            raise LifecycleError("Unsafe private service definition")
        return json.load(handle)


def verify_bundle(config, bundle=None):
    bundle = bundle or render_bundle(config)
    directory = Path(config["project_directory"])
    if directory.resolve() != directory:
        raise LifecycleError("Bundle directory contains a symlink")
    info = directory.stat()
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise LifecycleError("Supervised bundles must be root-owned and private")
    files = {name: (data.encode(), 0o555) for name, data in bundle["guards"].items()}
    files["compose.json"] = ((json.dumps(bundle["compose"], indent=2) + "\n").encode(), 0o600)
    files["images.json"] = ((json.dumps(bundle["images"], indent=2) + "\n").encode(), 0o600)
    for name, (data, mode) in files.items():
        if not os.path.lexists(str(directory / name)):
            raise LifecycleError("Bundle artifact missing")
        private_artifact(directory / name, data, mode)  # Existing-only byte/mode/ownership verification.
    return bundle


def local_mount(path):
    rows = json.loads(command(["findmnt", "--json", "--target", str(path), "--output", "TARGET,SOURCE,FSTYPE"]))["filesystems"]
    if len(rows) != 1 or rows[0]["fstype"] not in ("ext4", "xfs", "btrfs"):
        raise LifecycleError("Service control and application databases require verified local storage")
    return rows[0]


def health_spec(config, local_configs):
    expected = storage_assertions(config)
    checks = []
    for purpose in DATA_TARGETS:
        check = expected[purpose]
        sentinel = check["sentinel"]
        if "/" in sentinel or sentinel in (".", ".."):
            raise LifecycleError("A basename sentinel is required")
        checks.append({"path": config["storage"][purpose], "sentinel": sentinel,
                       "expected": {"target": check["mountpoint"], "source": check["source"], "fstype": check["fstype"]}})
    if 'media_secondary' in config['storage']:
        check = expected['media_secondary']
        checks.append({'path': config['storage']['media_secondary'], 'sentinel': check['sentinel'],
                       'read_only': config.get('secondary_media_read_only', True), 'expected': {key: check[field] for key, field in
                       (('target', 'mountpoint'), ('source', 'source'), ('fstype', 'fstype'))}})
    for app in config["apps"]:
        item = {"path": str(Path(config["storage"]["configs"]) / app), "expected": local_configs}
        if app == "netbootxyz":
            item.update(uid=911, gid=1001)
        checks.append(item)
    if 'netbootxyz' in config['apps']:
        from .compose import application_paths
        check = expected.get('netboot_assets')
        item = {'path': application_paths(config, 'netbootxyz')['assets_directory'],
                'expected': {key: check[field] for key, field in (('target', 'mountpoint'), ('source', 'source'), ('fstype', 'fstype'))} if check else local_configs,
                'uid': 911, 'gid': 1001}
        if check:
            item['sentinel'] = check['sentinel']
        checks.append(item)
    return {"checks": checks, "uid": config["service_user"]["uid"], "gid": config["service_user"]["gid"]}


class BoundedProbe:
    def __init__(self, spec, timeout=5):
        self.spec = spec
        self.timeout = timeout
        self.pending = None
        groups = {}
        for check in spec.get('checks', []):
            identity = (check.get('uid', spec['uid']), check.get('gid', spec['gid']))
            groups.setdefault(identity, []).append(check)
        self.probes = []
        if len(groups) > 1:
            self.probes = [BoundedProbe({'checks': checks, 'uid': uid, 'gid': gid}, timeout)
                           for (uid, gid), checks in groups.items()]
        elif groups:
            uid, gid = next(iter(groups))
            self.spec = dict(spec, uid=uid, gid=gid)

    def check(self, stopped):
        if self.probes:
            if any(probe.pending is not None and probe.pending.poll() is None for probe in self.probes):
                return {'healthy': False, 'reason': 'previous_probe_unreaped'}
            results = [probe.check(stopped) for probe in self.probes]
            return {'healthy': all(result['healthy'] for result in results), 'reason': 'all_service_identities', 'identities': len(results)}
        if self.pending is not None:
            if self.pending.poll() is None:
                return {"healthy": False, "reason": "previous_probe_unreaped"}
            self.pending.communicate()
            self.pending = None
        process = subprocess.Popen([sys.executable, "-I", "-c", HEALTH_WORKER], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True, env=ENV, cwd="/")
        self.pending = process
        payload = json.dumps(self.spec).encode()
        os.set_blocking(process.stdin.fileno(), False)
        deadline = time.monotonic() + self.timeout
        while payload and process.poll() is None and time.monotonic() < deadline and not stopped.is_set():
            try:
                payload = payload[os.write(process.stdin.fileno(), payload):]
            except BlockingIOError:
                stopped.wait(0.02)
            except BrokenPipeError:
                break
        process.stdin.close()
        process.stdin = None
        while process.poll() is None and time.monotonic() < deadline and not stopped.is_set():
            stopped.wait(0.05)
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            # Never wait for D-state cleanup here, and never start another worker
            # until this process has actually exited and been reaped.
            return {"healthy": False, "reason": "probe_deadline_or_shutdown"}
        output, _ = process.communicate()
        self.pending = None
        try:
            result = json.loads(output)
        except ValueError:
            return {"healthy": False, "reason": "invalid_probe_result"}
        identity_ok = (result.get("uid"), result.get("gid"), result.get("groups")) == (self.spec["uid"], self.spec["gid"], [])
        return {"healthy": process.returncode == 0 and result.get("healthy") is True and identity_ok,
                "reason": "storage_identity_and_read_check"}

    def close(self):
        for probe in self.probes:
            probe.close()
        if self.pending is not None and self.pending.poll() is None:
            try:
                os.killpg(self.pending.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


class Controller:
    def __init__(self, config, project, run=command, socket=SOCKET, bundle=None):
        self.socket = socket
        self.config, self.project, self.run = config, project, run
        self.bundle = bundle or render_bundle(config)
        self.identity = next(iter(self.bundle["compose"]["services"].values()))["labels"]["org.installarr.bundle"]
        self.docker = ["docker", "--host", socket]
        self.compose = self.docker + ["compose", "--project-name", project, "--file", str(Path(config["project_directory"]) / "compose.json")]

    def inventory(self):
        ids = self.run(self.docker + ["ps", "--all", "--quiet", "--no-trunc", "--filter", "label=com.docker.compose.project=" + self.project]).splitlines()
        if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in ids):
            raise LifecycleError("Invalid scoped container inventory")
        return json.loads(self.run(self.docker + ["inspect", *ids])) if ids else []

    def owns(self, row):
        labels = row.get("Config", {}).get("Labels", {}) or {}
        app = labels.get("com.docker.compose.service")
        return (labels.get("com.docker.compose.project") == self.project and app in self.config["apps"]
                and labels.get("org.installarr.bundle") == self.identity
                and labels.get("org.installarr.managed") == "isolated-compose-v1"
                and row.get("Config", {}).get("Image") == self.bundle["images"][app]["image"]
                and isinstance(row.get("Id"), str) and re.fullmatch(r"[0-9a-f]{64}", row["Id"]) is not None)

    def audit(self, rows):
        seen = set()
        owners = [row for row in rows if self.owns(row) and row["Config"]["Labels"]["com.docker.compose.service"] == "sabnzbd"]
        for row in rows:
            if not self.owns(row):
                raise LifecycleError("Project has foreign containers; preserved")
            app = row["Config"]["Labels"]["com.docker.compose.service"]
            if app in seen:
                raise LifecycleError("Duplicate managed application")
            seen.add(app)
            service = self.bundle["compose"]["services"][app]
            host = row["HostConfig"]
            network = "none"
            if service.get("network_mode") == "service:sabnzbd":
                if len(owners) != 1:
                    raise LifecycleError("Missing matching namespace owner")
                network = "container:" + owners[0]["Id"]
                if row["State"]["Running"]:
                    if not owners[0]["State"]["Running"]:
                        raise LifecycleError("Namespace owner is stopped")
                    try:
                        same = os.stat("/proc/{}/ns/net".format(row["State"]["Pid"])).st_ino == os.stat("/proc/{}/ns/net".format(owners[0]["State"]["Pid"])).st_ino
                    except (OSError, KeyError):
                        raise LifecycleError("Cannot verify live network namespace") from None
                    if not same:
                        raise LifecycleError("Dependent retained a stale network namespace")
            ports = {}
            if service.get('networks') == ['web']:
                network = self.project + '_web'
                if set(row.get('NetworkSettings', {}).get('Networks', {})) != {network}:
                    raise LifecycleError('Managed reference network differs')
                for port in service.get('ports', []):
                    ports[str(port['target']) + '/' + port.get('protocol', 'tcp')] = [
                        {'HostIp': port['host_ip'], 'HostPort': str(port['published'])}]
            if (host.get("NetworkMode") != network or (host.get("PortBindings") or {}) != ports or host.get("Privileged")
                    or host.get("RestartPolicy", {}).get("Name") not in ("", "no")
                    or row["Config"].get("Entrypoint") != service["entrypoint"]):
                raise LifecycleError("Managed container policy differs; stopped without overwriting changes")
            expected = {item["target"]: (item["source"].replace("$$", "$"), not item["read_only"]) for item in service["volumes"]}
            actual = {item["Destination"]: (item["Source"], item["RW"]) for item in row["Mounts"]}
            if (actual != expected or any(item.get("Type") != "bind" or item.get("Propagation") != "rprivate" for item in row["Mounts"])):
                raise LifecycleError("Managed bind policy differs; stopped without overwriting changes")
        return len(seen) == len(self.config["apps"]) and all(row["State"]["Running"] for row in rows)

    def stop(self):
        rows = self.inventory()
        ids = [row["Id"] for row in rows if self.owns(row) and row["State"]["Running"]]
        if ids:
            self.run(self.docker + ["stop", "--time", "5", *ids])
        remaining = self.inventory()
        if any(self.owns(row) and row["State"]["Running"] for row in remaining):
            raise LifecycleError("Managed stop not yet confirmed")

    def reconcile(self):
        if self.bundle['compose']['services'].get('ombi', {}).get('ports'):
            from .ombi import verify_admin_database
            verify_admin_database(Path(self.config['storage']['configs']) / 'ombi',
                self.config['service_user']['uid'], self.config['service_user']['gid'])
        verify_bundle(self.config, self.bundle)
        rows = self.inventory()
        running = self.audit(rows)
        if not running:
            self.run(self.compose + ["up", "--detach", "--no-build", "--pull", "never"])
            if not self.audit(self.inventory()):
                raise LifecycleError("Managed containers did not remain running")


class Supervisor:
    def __init__(self, controller, probe, report, access=None):
        self.access = access
        self.controller, self.probe, self.report = controller, probe, report
        self.stopped = threading.Event()
        self.retry_after = 0

    def step(self):
        health = self.probe.check(self.stopped)
        if not health["healthy"] or self.stopped.is_set():
            if self.access:
                self.access.close()
            self.controller.stop()
            self.report("stopped" if self.stopped.is_set() else "waiting_storage", health)
            return
        if time.monotonic() < self.retry_after:
            if self.access:
                self.access.close()
            self.report("retry_backoff", health)
            return
        try:
            self.controller.reconcile()
            if self.access:
                self.access.reconcile()
        except (LifecycleError, OSError, ValueError):
            if self.access:
                self.access.close()
            self.controller.stop()
            self.retry_after = time.monotonic() + 10
            self.report("blocked_policy_or_container_error", {"healthy": True})
            return
        if self.access:
            health = dict(health, gui=self.access.status())
        self.report("containers_running", health)

    def run(self):
        try:
            while not self.stopped.is_set():
                try:
                    self.step()
                except LifecycleError:
                    self.report("control_unavailable_stop_unconfirmed", {"healthy": False})
                self.stopped.wait(2)
        finally:
            if self.access:
                self.access.close()
            self.probe.close()
            self.controller.stop()
            self.report("stopped", {"healthy": False})


def snapshot_runtime():
    source = Path(__file__).parent
    paths = [*source.glob("*.py"), *[path for path in (source / "data").rglob("*") if path.is_file()]]
    contents = {str(path.relative_to(source)): path.read_bytes() for path in sorted(paths)}
    identity = hashlib.sha256(b"".join(name.encode() + b"\0" + data for name, data in contents.items())).hexdigest()
    base = Path("/usr/local/lib/installarr-runtime")
    trusted_directory(base)
    directory = base / identity
    trusted_directory(directory)
    trusted_directory(directory / "installarr")
    for name, data in contents.items():
        for parent in reversed((directory / "installarr" / name).parent.relative_to(directory / "installarr").parents):
            trusted_directory(directory / "installarr" / parent)
        trusted_directory((directory / "installarr" / name).parent)
        ensure_file(directory / "installarr" / name, data)
    launcher = b"import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent))\nfrom installarr.lifecycle import worker_main\nraise SystemExit(worker_main())\n"
    ensure_file(directory / "service.py", launcher)
    return directory / "service.py"


def install_service(config, name, reference=False, bootstrap=False):
    provisioning_gate()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name):
        raise LifecycleError("Invalid managed service name")
    if reference:
        from .reference import render_reference_bundle
        verify_bundle(config, render_reference_bundle(config, published=not bootstrap))
    else:
        verify_bundle(config)
    local_mount(config["project_directory"])
    configs_mount = local_mount(config["storage"]["configs"])
    launcher = snapshot_runtime()
    trusted_directory(SERVICE_ROOT)
    directory = SERVICE_ROOT / name
    project = "installarr-" + name
    definition = {"schema_version": 1, "config": config, "name": name, "project": project,
                  "health": health_spec(config, configs_mount), "launcher": str(launcher)}
    if reference:
        definition["deployment_mode"] = "reference-bootstrap" if bootstrap else "reference"
    with Execution(directory, {"operation": "managed-service-v1", "definition": definition}) as execution:
        private_artifact(directory / "definition.json", (json.dumps(definition, indent=2) + "\n").encode(), 0o600)
        unit = """[Unit]
Description=Installarr supervised application bundle
Wants={docker_unit}
After={docker_unit}

[Service]
Type=exec
ExecStart=/usr/bin/python3 -I {launcher} --definition {definition}
ExecStopPost=/usr/bin/python3 -I {launcher} --definition {definition} --stop-owned
WorkingDirectory=/
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=10
TimeoutStopSec=45
KillMode=control-group

[Install]
WantedBy=multi-user.target
""".format(launcher=launcher, definition=directory / "definition.json",
           docker_unit="docker.service" if reference else "installarr-test-docker.service")
        ensure_file(Path("/etc/systemd/system") / (project + ".service"), unit.encode())
        command(["systemctl", "daemon-reload"])
        execution.reconcile("unit", lambda: None)
    return {"status": "installed", "unit": project + ".service", "boot_enabled": False,
            "note": "Start explicitly after storage preparation. Unit supervises only its matching bundle on the isolated daemon."}


def service_status(name):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name):
        raise LifecycleError("Invalid managed service name")
    path = SERVICE_ROOT / name / "runtime" / "state.json"
    if not path.exists():
        return {"phase": "not_started"}
    saved = root_json(path)
    return {key: saved.get(key) for key in ("phase", "health", "checked_at")}


def worker_main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--stop-owned", action="store_true")
    args = parser.parse_args(argv)
    provisioning_gate()
    definition = root_json(args.definition)
    config = definition["config"]
    if definition.get("deployment_mode", "").startswith("reference"):
        from .reference import reference_controller
        controller = reference_controller(config, definition["project"], published=definition["deployment_mode"] == "reference")
    else:
        controller = Controller(config, definition["project"])
    runtime = args.definition.parent / "runtime"
    if args.stop_owned:
        controller.stop()
        with Execution(runtime, {"operation": "supervisor-v1", "definition": definition}) as execution:
            execution.state.update({"phase": "stopped", "health": {"healthy": False},
                                    "checked_at": time.time(), "stop_reason": "systemd_post_stop"})
            execution._save()
        return 0
    with Execution(runtime, {"operation": "supervisor-v1", "definition": definition}) as execution:
        def report(phase, health):
            execution.state["phase"] = phase
            execution.state["health"] = health
            execution.state["checked_at"] = time.time()
            execution._save()
        from .access import Access
        access = None if definition.get("deployment_mode", "").startswith("reference") else Access(controller, args.definition.parent / "gui-ready.json", root_json)
        supervisor = Supervisor(controller, BoundedProbe(definition["health"]), report, access)
        signal.signal(signal.SIGTERM, lambda *unused: supervisor.stopped.set())
        signal.signal(signal.SIGINT, lambda *unused: supervisor.stopped.set())
        report("starting", {"healthy": False})
        supervisor.run()
    return 0
