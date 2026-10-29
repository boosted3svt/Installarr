"""Fresh-Ubuntu shell bootstrap: no Python beforehand, no host/socket/NAS exposure."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(prefix='installarr-bootstrap-', dir='/var/tmp'))
    code = work / 'checkout'; code.mkdir()
    shutil.copytree(root / 'installarr', code / 'installarr', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(root / 'installarr.sh', code / 'installarr.sh')
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    print(json.dumps({'evidence': str(work)}), flush=True)
    for release in ('20.04', '24.04'):
        output = work / release; output.mkdir()
        image = json.loads(subprocess.check_output(docker + ['image', 'inspect', 'ubuntu:' + release], text=True))[0]['RepoDigests'][0]
        script = r'''set -eu
! command -v python3
cd /checkout
./installarr.sh --help >/output/help.txt
python3 -c 'from installarr.guided import run_setup; from installarr.ombi_family import ensure_discord_preference'
# No terminal: the ordinary no-argument path must stop with guidance, not deploy.
set +e
./installarr.sh >/output/no-terminal.txt
status=$?
set -e
test "$status" = 2
grep -q 'Open Installarr in a terminal' /output/no-terminal.txt
test ! -e /var/lib/installarr-setup
! command -v docker
'''
        with (output / 'bootstrap.log').open('w') as log:
            result = subprocess.run(docker + ['run', '--rm', '--network', 'bridge', '--cap-drop', 'NET_RAW',
                '--mount', 'type=bind,source=' + str(code) + ',target=/checkout,readonly',
                '--mount', 'type=bind,source=' + str(output) + ',target=/output',
                image, '/bin/sh', '-c', script], stdout=log, stderr=subprocess.STDOUT, timeout=900)
        record = {'release': release, 'image': image, 'status': result.returncode,
                  'scope': 'bare userspace bootstrap only; no host engine, storage or application deployment'}
        (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record), flush=True)
        if result.returncode:
            raise SystemExit('Bootstrap acceptance failed; inspect local evidence')


if __name__ == '__main__':
    main()
