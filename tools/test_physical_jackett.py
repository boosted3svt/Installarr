"""Unpublished Jackett authentication fixture with local config only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.credentials import read_private_credentials
from installarr.jackett import JackettClient, JackettHTTP
from installarr.lifecycle import command

IMAGE = 'lscr.io/linuxserver/jackett@sha256:2c015f0978bb15d006937a0e6926d8a8c4ca955eed5f3372c6ec09a3a2de3ddd'


def main():
    work = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix='installarr-jackett-test-', dir='/var/tmp'))
    configs = work / 'config'
    configs.mkdir(mode=0o700, exist_ok=True)
    os.chown(configs, 2000, 2000)
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    name = 'installarr-jackett-' + uuid.uuid4().hex[:8]
    print(json.dumps({'evidence': str(work), 'container': name}), flush=True)
    container = command(docker + ['run', '--detach', '--name', name, '--network', 'none', '--restart', 'no',
        '--env', 'PUID=2000', '--env', 'PGID=2000', '--env', 'TZ=America/Chicago', '--env', 'AUTO_UPDATE=false',
        '--mount', 'type=bind,source=' + str(configs) + ',target=/config,bind-propagation=rprivate', IMAGE])
    client = JackettClient(JackettHTTP('unix:///run/docker.sock', container, 9117, '0' * 32), credentials)
    try:
        wait_for(client.config)
        first = client.configure_admin()
        command(docker + ['restart', container])
        wait_for(client.config)
        second = client.verify_admin()
        config = configs / 'Jackett/ServerConfig.json'
        owner = [config.stat().st_uid, config.stat().st_gid]
        assert owner == [2000, 2000]
        result = {'first': first, 'after_restart': second, 'config_owner': owner, 'version': client.config()['app_version']}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        command(docker + ['stop', '--time', '5', container])
        command(docker + ['rm', container])


if __name__ == '__main__':
    main()
