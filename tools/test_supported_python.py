"""Run stdlib unit tests in disposable official Ubuntu userspace containers.

This checks Python/distro runtime compatibility, not systemd or fresh-host install
acceptance. No host Docker socket, credentials, NAS or privileged mounts exposed.
"""
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-ubuntu-runtime-', dir='/var/tmp'))
    source = Path(__file__).resolve().parents[1]
    print(json.dumps({'evidence': str(work)}), flush=True)
    for release in ('20.04', '24.04'):
        tag = 'ubuntu:' + release
        subprocess.run(['docker', 'pull', tag], check=True, stdout=subprocess.DEVNULL)
        info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], text=True))[0]
        digest = next(value for value in info['RepoDigests'] if value.startswith('ubuntu@sha256:'))
        script = '''set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends python3 openssl tzdata ca-certificates >/dev/null
python3 --version
cd /workspace
python3 -B -m unittest discover -s tests -v
'''
        with (work / (release + '.log')).open('w') as log:
            result = subprocess.run(['docker', 'run', '--rm', '--network', 'bridge', '--cap-drop', 'NET_RAW',
                '--mount', 'type=bind,source=' + str(source / 'installarr') + ',target=/workspace/installarr,readonly',
                '--mount', 'type=bind,source=' + str(source / 'tests') + ',target=/workspace/tests,readonly',
                digest, '/bin/sh', '-c', script], stdout=log, stderr=subprocess.STDOUT, timeout=600)
        metadata = {'release': release, 'image': digest, 'status': result.returncode,
                    'scope': 'Python unit runtime only; not fresh-host/systemd acceptance'}
        (work / (release + '.json')).write_text(json.dumps(metadata, indent=2) + '\n')
        print(json.dumps(metadata), flush=True)
        if result.returncode:
            raise SystemExit('Runtime test failed; see retained log')


if __name__ == '__main__':
    main()
