"""Signed old/current Compose refuse absent binds on the owned standard engine.

No app starts/ports/provider credentials. The probe overrides the cached SAB image
entrypoint with an exiting shell and uses network_mode none. Only a new local
fixture source path is touched; no NAS or existing app configuration is bound.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.compose import IMAGES
from test_native_compose_matrix import signed_compose


def main():
    if os.geteuid() != 0:
        raise ValueError('Owned engine bind-refusal probe requires root')
    work = Path(tempfile.mkdtemp(prefix='installarr-compose-bind-', dir='/var/tmp'))
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    image = IMAGES['sabnzbd']['image']
    subprocess.run(docker + ['image', 'inspect', image], stdout=subprocess.DEVNULL, check=True)
    server = subprocess.check_output(docker + ['version', '--format', '{{.Server.Version}}'], text=True).strip()
    env_dir = work / 'empty-docker-config'; env_dir.mkdir(mode=0o700)
    empty = work / 'empty.env'; empty.write_text('')
    environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C.UTF-8', 'DOCKER_CONFIG': str(env_dir),
                   'DOCKER_HOST': 'unix:///run/docker.sock', 'COMPOSE_ANSI': 'never'}
    print(json.dumps({'evidence': str(work), 'server': server}), flush=True)
    results = []
    for codename, version in (('focal', '2.35.1-1~ubuntu.20.04~focal'), ('noble', '5.6.1-1~ubuntu.24.04~noble')):
        output = work / codename; output.mkdir(mode=0o700)
        cache = Path('/var/tmp/installarr-native-compose-p7w2c81e') / codename / 'compose.deb'
        # Copy public package bytes into the root-private fixture, then reverify
        # their signed repository hash before extracting/executing anything.
        shutil.copyfile(str(cache), str(output / 'compose.deb'))
        binary, authenticity = signed_compose(output, codename, version)
        project = 'installarr-bind-' + uuid.uuid4().hex[:10]
        absent = output / 'must-stay-absent'
        config = output / 'compose.json'
        config.write_text(json.dumps({'services': {'probe': {'image': image, 'pull_policy': 'never', 'network_mode': 'none',
            'restart': 'no', 'user': '2000:2000', 'entrypoint': ['/bin/sh'], 'command': ['-c', 'exit 0'],
            'labels': {'org.installarr.test': 'compose-bind-refusal'},
            'volumes': [{'type': 'bind', 'source': str(absent), 'target': '/probe', 'read_only': True,
                         'bind': {'create_host_path': False, 'propagation': 'rprivate'}}]}}}))
        command = [str(binary), '--project-name', project, '--env-file', str(empty), '--file', str(config)]
        assert not subprocess.check_output(docker + ['ps', '--all', '--quiet', '--filter', 'label=com.docker.compose.project=' + project], text=True).strip()
        try:
            response = subprocess.run(command + ['up', '--detach', '--no-build', '--pull', 'never'],
                                      capture_output=True, text=True, env=environment, cwd=str(output), timeout=30)
            (output / 'up.stderr').write_text(response.stderr)
            assert response.returncode != 0 and 'bind source path does not exist' in response.stderr.lower()
            assert not absent.exists()
            results.append({'compose': version, 'authenticity': authenticity, 'up': 'refused absent bind',
                            'fallback_directory': 'not created', 'application': 'never started'})
        finally:
            ids = subprocess.check_output(docker + ['ps', '--all', '--quiet', '--no-trunc', '--filter',
                'label=com.docker.compose.project=' + project], text=True).splitlines()
            for identity in ids:
                row = json.loads(subprocess.check_output(docker + ['inspect', identity], text=True))[0]
                assert row['Config']['Labels'].get('org.installarr.test') == 'compose-bind-refusal'
                assert row['Config']['Image'] == image
                if row['State']['Running']:
                    subprocess.run(docker + ['stop', '--time', '1', identity], capture_output=True, check=True)
                subprocess.run(docker + ['rm', identity], capture_output=True, check=True)
    (work / 'result.json').write_text(json.dumps({'server': server, 'cases': results,
        'scope': 'Compose bind behavior on current engine, not Focal engine/boot acceptance'}, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'cases': len(results), 'ports': 'none', 'existing_services': 'untouched'}), flush=True)


if __name__ == '__main__':
    main()
