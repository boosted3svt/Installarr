"""Official signed Focal Docker archive userspace compatibility; no daemon.

No host socket/NAS/system mounts/credentials are passed to the container.
"""
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    source = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(prefix='installarr-focal-docker-', dir='/var/tmp'))
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    subprocess.run(docker + ['pull', 'ubuntu:20.04'], check=True, stdout=subprocess.DEVNULL)
    image = json.loads(subprocess.check_output(docker + ['image', 'inspect', 'ubuntu:20.04'], text=True))[0]['RepoDigests'][0]
    script = r'''set -eu
export DEBIAN_FRONTEND=noninteractive
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
apt-get update -qq
apt-get install -y -qq --no-install-recommends python3 ca-certificates curl gnupg systemd >/dev/null
mkdir -p /etc/systemd/system /etc/apt/keyrings
for unit in docker.service docker.socket containerd.service; do ln -s /dev/null /etc/systemd/system/$unit; done
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/installarr-docker.asc
cd /workspace
python3 -B - <<'INNER'
from pathlib import Path
from installarr.dockerhost import verify_key
verify_key(Path('/etc/apt/keyrings/installarr-docker.asc').read_text())
Path('/etc/apt/sources.list.d/installarr-docker.sources').write_text('Types: deb\nURIs: https://download.docker.com/linux/ubuntu\nSuites: focal\nComponents: stable\nArchitectures: amd64\nSigned-By: /etc/apt/keyrings/installarr-docker.asc\n')
INNER
apt-get -o APT::Get::AllowUnauthenticated=false -o Acquire::AllowInsecureRepositories=false -o APT::Update::Error-Mode=any update -qq
python3 -B - <<'INNER'
import json, subprocess
from installarr.dockerhost import PACKAGES, select_version, APT
versions={p:select_version(subprocess.check_output(['apt-cache','madison',p],text=True)) for p in PACKAGES}
subprocess.run(APT+['install','--yes','--no-remove','--no-install-recommends']+[p+'='+v for p,v in versions.items()],check=True)
print('INSTALLARR_PACKAGE_VERSIONS='+json.dumps(versions,sort_keys=True))
INNER
docker --version
dockerd --version
docker compose version
docker buildx version
containerd --version
test ! -S /run/docker.sock
test "$(readlink /etc/systemd/system/docker.service)" = /dev/null
'''
    print(json.dumps({'evidence': str(work), 'image': image}), flush=True)
    with (work / 'install.log').open('w') as log:
        result = subprocess.run(docker + ['run', '--rm', '--cap-drop', 'NET_RAW', '--network', 'bridge',
            '--mount', 'type=bind,source=' + str(source / 'installarr') + ',target=/workspace/installarr,readonly',
            image, '/bin/sh', '-c', script], stdout=log, stderr=subprocess.STDOUT, timeout=900)
    lines = (work / 'install.log').read_text().splitlines()
    versions = [json.loads(line.split('=', 1)[1]) for line in lines if line.startswith('INSTALLARR_PACKAGE_VERSIONS=')]
    metadata = {'image': image, 'status': result.returncode, 'versions': versions,
                'scope': 'signed package install and binary execution only; no engine/systemd/boot acceptance; Focal is outside current upstream support list'}
    (work / 'result.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata), flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
