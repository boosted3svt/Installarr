"""Shared disposable fixtures, confined to the verified isolated NAS export."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from installarr.accounts import provisioning_gate
from installarr.cli import save_config
from installarr.compose import DATA_TARGETS, write_bundle
from installarr.lifecycle import SOCKET, local_mount
from installarr.prerequisites import prepare_prerequisites

DOCKER = ["docker", "--host", SOCKET]


def run(args, input=None, timeout=120):
    result = subprocess.run(args, input=input, capture_output=True, text=True, check=False, timeout=timeout)
    if result.returncode:
        raise ValueError("Isolated fixture command failed")
    return result.stdout.strip()


class Fixture:
    def __init__(self, apps, prefix):
        provisioning_gate()
        if run(DOCKER + ["ps", "--all", "--quiet"]):
            raise ValueError("Existing test containers preserved")
        self.root = os.open("/media/installarr", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        check = subprocess.run(["findmnt", "--json", "--target", "/proc/self/fd/{}".format(self.root), "--output", "TARGET,SOURCE,FSTYPE"],
                               pass_fds=(self.root,), capture_output=True, text=True, check=True, timeout=5)
        rows = json.loads(check.stdout)["filesystems"]
        expected = {"target": "/media/installarr", "source": "192.168.1.102:/share/MD0_DATA/Public/installarr", "fstype": "nfs"}
        if rows != [expected]:
            raise ValueError("Exact isolated NAS mount required")
        self.nas = ".installarr-" + prefix + "-" + uuid.uuid4().hex
        self.work = Path(tempfile.mkdtemp(prefix="installarr-" + prefix + "-", dir="/var/tmp"))
        local_mount(self.work)
        (self.work / "configs").mkdir()
        (self.work / "backups").mkdir()
        for app in apps:
            path = self.work / "configs" / app
            path.mkdir(mode=0o700)
            os.chown(str(path), 2000, 2000)
        self.config = {"schema_version": 1, "apps": apps, "timezone": "America/Chicago", "bind_address": "127.0.0.1",
            "plex_allowed_networks": "192.168.0.0/23", "service_user": {"name": "installarr-test", "uid": 2000, "gid": 2000},
            "project_directory": str(self.work / "project"), "storage": {
                **{purpose: "/media/installarr/" + self.nas + "/" + purpose for purpose in DATA_TARGETS},
                "configs": str(self.work / "configs"), "backups": str(self.work / "backups")},
            "storage_mounts": {**{purpose: {"kind": "existing", "mountpoint": expected["target"], "source": expected["source"],
                "fstype": "nfs", "sentinel": "health"} for purpose in DATA_TARGETS}, "configs": {"kind": "local"}, "backups": {"kind": "local"}}}
        self.project = "installarr-" + prefix + "-" + uuid.uuid4().hex[:12]
        self.compose = DOCKER + ["compose", "--project-name", self.project, "--file", str(self.work / "project" / "compose.json")]
        self.created = self.deployed = False
        self.service_script("""root=int(sys.argv[1]); name=sys.argv[2]
os.mkdir(name,0o700,dir_fd=root)
base=os.open(name,os.O_RDONLY|os.O_DIRECTORY,dir_fd=root)
for purpose in ('media','downloads','incomplete'):
    os.mkdir(purpose,0o700,dir_fd=base)
    fd=os.open(purpose,os.O_RDONLY|os.O_DIRECTORY,dir_fd=base)
    file=os.open('health',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644,dir_fd=fd)
    with os.fdopen(file,'w') as handle: handle.write('Installarr disposable health\\n')
    os.close(fd)
os.close(base)
""")
        self.created = True
        save_config(self.work / "config.json", self.config)
        self.prerequisites = prepare_prerequisites(self.config, self.work / "prerequisites")
        prepare_prerequisites(self.config, self.work / "prerequisites")
        write_bundle(self.config)

    def service_script(self, body, extra=()):
        script = "import os,sys\nos.setgroups([])\nos.setgid(2000)\nos.setuid(2000)\n" + body
        result = subprocess.run([sys.executable, "-B", "-c", script, str(self.root), self.nas, *extra],
                                pass_fds=(self.root,), capture_output=True, text=True, check=False, timeout=15)
        if result.returncode:
            raise ValueError("Isolated NAS fixture operation failed")
        return result.stdout.strip()

    def up(self):
        self.deployed = True
        run(self.compose + ["up", "--detach", "--no-build", "--pull", "never"])

    def container(self, app):
        return run(self.compose + ["ps", "--all", "--quiet", app])

    def close(self, passed):
        if self.deployed:
            run(self.compose + ["down", "--timeout", "10"])
        if self.created:
            self.service_script("""import stat
root=int(sys.argv[1]); name=sys.argv[2]
def remove(parent,name,device):
    info=os.stat(name,dir_fd=parent,follow_symlinks=False)
    if stat.S_ISDIR(info.st_mode):
        fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
        try:
            if os.fstat(fd).st_dev!=device: raise ValueError('Cross-filesystem cleanup refused')
            for child in os.listdir(fd): remove(fd,child,device)
        finally: os.close(fd)
        os.rmdir(name,dir_fd=parent)
    else: os.unlink(name,dir_fd=parent)
remove(root,name,os.fstat(root).st_dev)
""")
        os.close(self.root)
        if passed:
            shutil.rmtree(str(self.work))
        else:
            print(json.dumps({"private_local_failure_evidence": str(self.work)}))
