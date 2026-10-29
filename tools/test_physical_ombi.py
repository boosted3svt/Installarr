"""Unpublished Ombi local-admin bootstrap; no family lookalikes or fake integrations."""
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.credentials import read_private_credentials
from installarr.lifecycle import command
from installarr.ombi import IMAGE, OmbiClient, OmbiHTTP


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-ombi-test-', dir='/var/tmp'))
    config = work / 'config'
    config.mkdir(mode=0o700)
    os.chown(config, 2000, 2000)
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    name = 'installarr-ombi-' + uuid.uuid4().hex[:8]
    print(json.dumps({'evidence': str(work), 'container': name}), flush=True)
    container = command(docker + ['run', '--detach', '--name', name, '--network', 'none', '--restart', 'no',
        '--env', 'PUID=2000', '--env', 'PGID=2000', '--env', 'TZ=America/Chicago',
        '--mount', 'type=bind,source=' + str(config) + ',target=/config,bind-propagation=rprivate', IMAGE])
    client = OmbiClient(OmbiHTTP('unix:///run/docker.sock', container))
    try:
        wait_for(client.status)
        first = client.configure_admin(credentials)
        command(docker + ['restart', container])
        wait_for(client.status)
        second = client.verify_admin(credentials)
        assert first == second
        owners = {p.name: [p.stat().st_uid, p.stat().st_gid] for p in config.glob('*.db')}
        assert owners and all(owner == [2000, 2000] for owner in owners.values())
        result = {'first': first, 'after_restart': second, 'database_owners': owners,
                  'plex_family_import_and_requests': 'not tested'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        command(docker + ['stop', '--time', '5', container])
        command(docker + ['rm', container])


if __name__ == '__main__':
    main()
