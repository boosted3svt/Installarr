"""Build/install the distributable wheel in official supported Ubuntu userspaces.

Only package code/pyproject are mounted read-only. No reference Compose, secrets,
NAS, Docker socket or host system paths are exposed inside these containers.
"""
import hashlib
import json
import shutil
from pathlib import Path
import subprocess
import tempfile


def main():
    source = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(prefix='installarr-distribution-', dir='/var/tmp'))
    snapshot = work / 'source'
    shutil.copytree(source / 'installarr', snapshot, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    tests_snapshot = work / 'tests'
    shutil.copytree(source / 'tests', tests_snapshot, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(source / 'pyproject.toml', work / 'pyproject.toml')
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    print(json.dumps({'evidence': str(work)}), flush=True)
    for release in ('20.04', '24.04'):
        output = work / release
        output.mkdir()
        image = json.loads(subprocess.check_output(docker + ['image', 'inspect', 'ubuntu:' + release], text=True))[0]['RepoDigests'][0]
        script = r'''set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends python3 python3-pip python3-venv ca-certificates tzdata >/dev/null
mkdir /tmp/build-source
cp -a /input/installarr /tmp/build-source/
cp /input/pyproject.toml /tmp/build-source/
python3 -m venv /tmp/wheel-env
/tmp/wheel-env/bin/python -m pip wheel --no-deps --wheel-dir /output /tmp/build-source
/tmp/wheel-env/bin/python -m pip install --no-index --no-deps /output/installarr-*.whl
cd /tmp
/tmp/wheel-env/bin/installarr --help >/output/help.txt
/tmp/wheel-env/bin/installarr apply --help >/output/apply-help.txt
grep -q -- --prepare-only /output/apply-help.txt
/tmp/wheel-env/bin/installarr preflight >/output/preflight.json
/tmp/wheel-env/bin/installarr init-smb-secrets --help >/output/smb-help.txt
/tmp/wheel-env/bin/installarr init-provider-secrets --help >/output/provider-help.txt
grep -q -- --credentials-file /output/provider-help.txt
grep -q -- --filename /output/smb-help.txt
/tmp/wheel-env/bin/python -I -B -m unittest discover -s /tests -v >/output/installed-unit-tests.log 2>&1
/tmp/wheel-env/bin/python -I - <<'INNER'
import json
from pathlib import Path
from installarr.profiles import Catalog,recommended_profiles
from installarr.atomic import publish_noreplace
from installarr.runtime import source_digest
import installarr
assert '/tmp/build-source' not in str(installarr.__file__)
assert source_digest(Path(installarr.__file__).parent,lambda p:p.read_bytes())==source_digest(Path('/input/installarr'),lambda p:p.read_bytes())
catalog=Catalog()
for app,choice in recommended_profiles(['radarr','sonarr']).items():
    for identifier in choice['available']:
        assert catalog.resolve(app,identifier)['formats']
assert (Path(installarr.__file__).parent/'data/trash/UPSTREAM_LICENSE').is_file()
source=Path('/tmp/atomic-source');target=Path('/tmp/atomic-target')
source.write_text('wheel runtime');publish_noreplace(source,target)
assert target.read_text()=='wheel runtime' and target.stat().st_nlink==1
result={'installed_from_wheel':True,'package_location':str(installarr.__file__),
        'pinned_documents_verified':len(catalog.documents),'atomic_runtime':'passed',
        'all_recommended_profiles':'resolved','entrypoint_help_and_preflight':'passed',
        'installed_code_sha256':source_digest(Path(installarr.__file__).parent,lambda p:p.read_bytes()),
        'prepare_only_cli':'available','private_provider_smb_cli':'available','installed_wheel_unit_suite':'passed'}
Path('/output/acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
INNER
'''
        with (output / 'build.log').open('w') as log:
            result = subprocess.run(docker + ['run', '--rm', '--network', 'bridge', '--cap-drop', 'NET_RAW',
                '--mount', 'type=bind,source=' + str(snapshot) + ',target=/input/installarr,readonly',
                '--mount', 'type=bind,source=' + str(work / 'pyproject.toml') + ',target=/input/pyproject.toml,readonly'
                , '--mount', 'type=bind,source=' + str(tests_snapshot) + ',target=/tests,readonly',
                '--mount', 'type=bind,source=' + str(output) + ',target=/output', image, '/bin/sh', '-c', script],
                stdout=log, stderr=subprocess.STDOUT, timeout=900)
        wheels = [{'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
                  for path in output.glob('*.whl')]
        metadata = {'release': release, 'image': image, 'status': result.returncode, 'wheels': wheels,
                    'scope': 'distribution install/entrypoint/data/runtime only; not engine/systemd/fresh-host acceptance'}
        (output / 'result.json').write_text(json.dumps(metadata, indent=2) + '\n')
        print(json.dumps(metadata), flush=True)
        if result.returncode:
            raise SystemExit('Distribution acceptance failed; inspect private build log')


if __name__ == '__main__':
    main()
