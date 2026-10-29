"""Unpublished unclaimed official Plex identity/permissions/restart fixture."""
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.lifecycle import command
from installarr.plex import IMAGE, PREFERENCES, PlexClient, PlexHTTP


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-plex-test-', dir='/var/tmp'))
    for name in ('config', 'transcode'):
        (work / name).mkdir(mode=0o700)
        os.chown(work / name, 2000, 2000)
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    name = 'installarr-plex-' + uuid.uuid4().hex[:8]
    print(json.dumps({'evidence': str(work), 'container': name}), flush=True)
    args = ['run', '--detach', '--name', name, '--network', 'none', '--restart', 'no',
            '--env', 'PLEX_UID=2000', '--env', 'PLEX_GID=2000', '--env', 'TZ=America/Chicago',
            '--env', 'CHANGE_CONFIG_DIR_OWNERSHIP=false', '--env', 'ALLOWED_NETWORKS=192.168.0.0/23',
            '--env', 'ADVERTISE_IP=http://10.70.0.99:32400/']
    for role in ('config', 'transcode'):
        args += ['--mount', 'type=bind,source=' + str(work / role) + ',target=/' + role + ',bind-propagation=rprivate']
    container = command(docker + args + [IMAGE])
    client = PlexClient(PlexHTTP('unix:///run/docker.sock', container))
    try:
        first = wait_for(client.status)
        assert not first['claimed']
        prefs = ET.parse(str(work / 'config' / PREFERENCES)).getroot()
        assert prefs.get('allowedNetworks') == '192.168.0.0/23'
        assert prefs.get('customConnections') == 'http://10.70.0.99:32400/'
        database = work / 'config/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
        wait_for(lambda: database.exists())
        owner = [database.stat().st_uid, database.stat().st_gid]
        assert owner == [2000, 2000]
        # Check the actual long-running Plex process, independent of file ownership.
        processes = command(docker + ['exec', container, 'ps', '-eo', 'uid,gid,args'])
        main = [line.split(None, 2) for line in processes.splitlines() if '/usr/lib/plexmediaserver/Plex Media Server' in line]
        assert len(main) == 1 and main[0][:2] == ['2000', '2000']
        command(docker + ['restart', container])
        second = wait_for(client.status)
        assert first == second
        result = {'image': IMAGE, 'first': first, 'after_restart': second, 'database_owner': owner,
                  'process_uid_gid': main[0][:2], 'allowed_networks': prefs.get('allowedNetworks'),
                  'claim_and_library_authorization': 'pending; no ports published'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        command(docker + ['stop', '--time', '5', container])
        command(docker + ['rm', container])


if __name__ == '__main__':
    main()
