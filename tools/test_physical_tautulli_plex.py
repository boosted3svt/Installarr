"""Unpublished Tautulli auth/ownership fixture; no Plex integration claim."""
import configparser
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.credentials import read_private_credentials
from installarr.lifecycle import command
from installarr.tautulli import IMAGE, VERSION, TautulliClient, TautulliHTTP, initialize_config, configure_plex_offline


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-tautulli-test-', dir='/var/tmp'))
    config = work / 'config'
    config.mkdir(mode=0o700)
    os.chown(config, 2000, 2000)
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    initialize_config(config, credentials, 2000, 2000)
    from installarr.plex import PREFERENCES
    plex_config = json.loads(Path('/var/tmp/installarr-plex-authorize-uo198y7v/config.json').read_text())
    prefs = ET.parse(str(Path(plex_config['storage']['configs']) / 'plex' / PREFERENCES)).getroot()
    configure_plex_offline(config, prefs.get('PlexOnlineToken'), prefs.get('ProcessedMachineIdentifier'), 2000, 2000)
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(str(config / 'config.ini'))
    key = parser['General']['api_key']
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    name = 'installarr-tautulli-' + uuid.uuid4().hex[:8]
    print(json.dumps({'evidence': str(work), 'container': name}), flush=True)
    container = command(docker + ['run', '--detach', '--name', name, '--network', 'installarr-plex-auth-test_web', '--restart', 'no',
        '--env', 'PUID=2000', '--env', 'PGID=2000', '--env', 'TZ=America/Chicago',
        '--mount', 'type=bind,source=' + str(config) + ',target=/config,bind-propagation=rprivate', IMAGE])
    client = TautulliClient(TautulliHTTP('unix:///run/docker.sock', container, 8181, key))
    try:
        wait_for(client.status)
        first = client.verify_admin(credentials)
        def connection():
            rows = client.call('get_servers_info')
            matches = [row for row in rows if row.get('machine_identifier') == prefs.get('ProcessedMachineIdentifier')]
            assert len(matches) == 1 and matches[0]['version'] == '1.43.5.11079-b3b13e506'
            return {'connection': 'verified', 'remote_version': matches[0]['version']}
        linked = wait_for(connection)
        command(docker + ['restart', container])
        wait_for(client.status)
        second = client.verify_admin(credentials)
        assert wait_for(connection) == linked
        retained = initialize_config(config, credentials, 2000, 2000)
        files = [config / 'config.ini', config / 'tautulli.db']
        owners = {p.name: [p.stat().st_uid, p.stat().st_gid] for p in files}
        assert all(owner == [2000, 2000] for owner in owners.values())
        result = {'version': VERSION, 'image': IMAGE, 'first': first, 'after_restart': second,
                  'rerun': retained, 'owners': owners, 'plex_integration': linked}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        command(docker + ['stop', '--time', '5', container])
        command(docker + ['rm', container])


if __name__ == '__main__':
    main()
