"""Signed official Compose versions parse every reference subset; no daemon needed.

Artifacts are verified against GPG-signed repository metadata before extraction.
The normal matrix points DOCKER_HOST at a nonexistent socket and uses an empty
Docker config. No host credentials/configuration or app services are used.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from installarr.cli import APPS
from installarr.dockerhost import verify_key
from installarr.reference import render_reference_bundle
from test_reference import reference_configuration

BASE = 'https://download.docker.com/linux/ubuntu/'


def fetch(url, limit=64 * 1024 * 1024):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=60) as response:
        final = urllib.parse.urlsplit(response.url)
        if final.scheme != 'https' or final.hostname != 'download.docker.com':
            raise ValueError('Unexpected repository redirect')
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError('Repository artifact exceeds bounded size')
        return body


def signed_compose(work, codename, version):
    artifact_directory = work
    work = Path(tempfile.mkdtemp(prefix='verify-', dir=str(artifact_directory)))
    key = fetch(BASE + 'gpg', 1024 * 1024)
    verify_key(key.decode())
    keyfile = work / 'docker.asc'; keyfile.write_bytes(key)
    keyring = work / 'docker.gpg'
    subprocess.run(['gpg', '--batch', '--homedir', str(work), '--dearmor', '--output', str(keyring), str(keyfile)],
                   capture_output=True, check=True)
    signed = work / 'InRelease'; signed.write_bytes(fetch(BASE + 'dists/' + codename + '/InRelease', 2 * 1024 * 1024))
    release = work / 'Release'
    subprocess.run(['gpgv', '--homedir', str(work), '--keyring', str(keyring), '--output', str(release), str(signed)],
                   capture_output=True, check=True)
    section = False
    hashes = {}
    for line in release.read_text().splitlines():
        if line == 'SHA256:':
            section = True; continue
        if section and line and not line.startswith(' '):
            section = False
        if section and line.strip():
            checksum, size, name = line.split()
            hashes[name] = (checksum, int(size))
    index_name = 'stable/binary-amd64/Packages.gz'
    expected, size = hashes[index_name]
    index = fetch(BASE + 'dists/' + codename + '/' + index_name)
    assert len(index) == size and hashlib.sha256(index).hexdigest() == expected
    packages = []
    for paragraph in gzip.decompress(index).decode().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
        if fields.get('Package') == 'docker-compose-plugin' and fields.get('Version') == version and fields.get('Architecture') == 'amd64':
            packages.append(fields)
    assert len(packages) == 1
    package = packages[0]
    name = PurePosixPath(package['Filename'])
    assert not name.is_absolute() and '..' not in name.parts
    deb = artifact_directory / 'compose.deb'
    data = deb.read_bytes() if deb.exists() else fetch(BASE + str(name))
    assert len(data) == int(package['Size']) and hashlib.sha256(data).hexdigest() == package['SHA256']
    if not deb.exists():
        deb.write_bytes(data)
    extracted = Path(tempfile.mkdtemp(prefix='extracted-', dir=str(artifact_directory)))
    subprocess.run(['dpkg-deb', '--extract', str(deb), str(extracted)], capture_output=True, check=True)
    matches = [path for path in extracted.rglob('docker-compose') if path.is_file() and os.access(path, os.X_OK)]
    assert len(matches) == 1
    return matches[0], {'version': version, 'package_sha256': package['SHA256'],
                        'InRelease': 'GPG verified; expected Docker primary fingerprint',
                        'Packages': 'signed SHA256 verified', 'deb': 'signed index SHA256 verified'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', type=Path)
    args = parser.parse_args()
    work = args.resume or Path(tempfile.mkdtemp(prefix='installarr-native-compose-', dir='/var/tmp'))
    assert work.resolve() == work and work.name.startswith('installarr-native-compose-')
    assert work.stat().st_uid == os.geteuid() and work.stat().st_mode & 0o777 == 0o700
    print(json.dumps({'evidence': str(work)}), flush=True)
    configs = work / 'configs'; configs.mkdir(exist_ok=True)
    env_dir = work / 'empty-docker-config'; env_dir.mkdir(mode=0o700, exist_ok=True)
    env_file = work / 'empty.env'; env_file.write_text('')
    environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C.UTF-8', 'DOCKER_CONFIG': str(env_dir),
                   'DOCKER_HOST': 'unix://' + str(work / 'deliberately-absent.sock'), 'COMPOSE_ANSI': 'never'}
    cases = []
    for size in range(1, len(APPS) + 1):
        for apps in itertools.combinations(APPS, size):
            config = reference_configuration()
            config['apps'] = list(apps)
            config['project_directory'] = '/srv/bundle-$literal'
            for published in (False, True):
                bundle = render_reference_bundle(config, published=published)
                path = configs / ('case-' + str(len(cases)) + '.json')
                path.write_text(json.dumps(bundle['compose']))
                cases.append((path, apps, published))
    assert len(cases) == 1022
    for codename, version in (('focal', '2.35.1-1~ubuntu.20.04~focal'), ('noble', '5.6.1-1~ubuntu.24.04~noble')):
        output = work / codename; output.mkdir(mode=0o700, exist_ok=True)
        binary, authenticity = signed_compose(output, codename, version)
        installed = subprocess.check_output([str(binary), 'version', '--short'], env=environment, text=True, timeout=10).strip()
        assert installed.lstrip('v') == version.split('-', 1)[0]
        def check(case):
            path, apps, published = case
            result = subprocess.run([str(binary), '--project-name', 'installarr-schema', '--env-file', str(env_file),
                '--file', str(path), 'config', '--format', 'json'], capture_output=True, text=True, env=environment, timeout=25)
            if result.returncode:
                (output / (path.stem + '.stderr')).write_text(result.stderr)
                raise ValueError('Native Compose schema refused case ' + path.stem)
            data = json.loads(result.stdout)
            assert set(data['services']) == set(apps)
            for app, service in data['services'].items():
                assert bool(service.get('ports')) == published
                assert service['restart'] == 'no'
                for volume in service['volumes']:
                    assert volume['type'] == 'bind'
                    assert not volume.get('bind', {}).get('create_host_path', False)
                guard = next(v for v in service['volumes'] if v['target'] == '/installarr-storage-guard')
                assert guard['source'].startswith('/srv/bundle-$$literal/')
            assert 'not set' not in result.stderr.lower()
            return True
        check(cases[0])
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            assert all(pool.map(check, cases[1:]))
        result = {'authenticity': authenticity, 'native_version': installed, 'subsets': 511,
                  'bootstrap_and_published_cases': len(cases), 'status': 'passed',
                  'daemon': 'nonexistent socket; schema/normalization only',
                  'host_credentials': 'isolated empty Docker config', 'ports_apps_started': False}
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
