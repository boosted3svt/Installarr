"""Unpublished networkless SAB server-schema/POST/persistence test, synthetic data."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.compose import IMAGES
from installarr.lifecycle import command
from installarr.sab import SabClient, SabHTTP


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-sab-provider-schema-', dir='/var/tmp'))
    config = work / 'config'
    config.mkdir(mode=0o700)
    os.chown(str(config), 2000, 2000)
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    name = 'installarr-sab-schema-' + uuid.uuid4().hex[:8]
    container = command(docker + ['run', '--detach', '--name', name, '--network', 'none', '--restart', 'no',
        '--env', 'PUID=2000', '--env', 'PGID=2000', '--env', 'TZ=America/Chicago',
        '--mount', 'type=bind,source=' + str(config) + ',target=/config,bind-propagation=rprivate', IMAGES['sabnzbd']['image']])
    print(json.dumps({'evidence': str(work), 'container': name}), flush=True)
    def ready():
        match = re.search(r'(?m)^api_key\s*=\s*([a-fA-F0-9]{32})\s*$', (config / 'sabnzbd.ini').read_text())
        if not match:
            return None
        client = SabClient(SabHTTP('unix:///run/docker.sock', container, 8080, match.group(1)))
        return client if client.call('version').get('version') == '5.1.3' else None
    try:
        client = wait_for(ready)
        fields = {'name': 'Installarr Synthetic', 'host': '127.0.0.1', 'port': 563, 'ssl': 1, 'ssl_verify': 3,
                  'connections': 100, 'enable': 0, 'username': 'synthetic-unused', 'password': 'synthetic-unused'}
        client.call('set_config', section='servers', **fields)
        def readback():
            rows = client.call('get_config', section='servers')['config']['servers']
            if isinstance(rows, dict):
                rows = [dict(row, name=key) for key, row in rows.items()]
            row = next(row for row in rows if row['name'] == fields['name'])
            assert row['host'] == fields['host'] and row['connections'] == 100
            assert row['ssl'] == 1 and row['enable'] == 0 and row['ssl_verify'] == 3
            return {'connections': row['connections'], 'ssl': row['ssl'], 'enable': row['enable'],
                    'ssl_verify': row['ssl_verify'], 'port': row['port']}
        first = readback()
        command(docker + ['restart', container])
        client = wait_for(ready)
        assert readback() == first
        result = {'server_post_and_readback': first, 'restart_persistence': 'passed',
                  'provider_authentication': 'not tested; disabled synthetic server, network none'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        command(docker + ['stop', '--time', '5', container])
        command(docker + ['rm', container])


if __name__ == '__main__':
    main()
