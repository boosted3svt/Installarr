"""Create and retain an authenticated Radarr/SAB proof of concept, no original media writes."""
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.cli import detected_address, save_config
from installarr.credentials import initialize_credentials
from installarr.directories import observed_mount
from installarr.reference import apply_reference


def main():
    root = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        expected = {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
        if observed_mount(root) != expected:
            raise ValueError('Exact authorized test export required')
    finally:
        os.close(root)
    tag = uuid.uuid4().hex[:8]
    name = 'poc-' + tag
    work = Path(tempfile.mkdtemp(prefix='installarr-reference-poc-', dir='/var/tmp'))
    data = Path('/media/installarr') / ('Installarr-POC-' + tag)
    config = {'schema_version': 1, 'apps': ['radarr', 'sabnzbd'], 'timezone': 'America/Chicago',
              'bind_address': detected_address(), 'plex_allowed_networks': '192.168.0.0/23',
              'service_user': {'name': 'installarr-test', 'uid': 2000, 'gid': 2000},
              'project_directory': str(work / 'project'), 'data_root': str(data),
              'storage': {'media': str(data), 'downloads': str(data / 'downloads'),
                          'incomplete': str(data / 'incomplete-downloads'),
                          'configs': str(work / 'configs'), 'backups': str(work / 'backups')},
              'storage_mounts': {**{key: {'kind': 'existing', 'mountpoint': expected['target'], 'source': expected['source'],
                                         'fstype': 'nfs', 'sentinel': 'health'} for key in ('media', 'downloads', 'incomplete')},
                                 'configs': {'kind': 'local'}, 'backups': {'kind': 'local'}}}
    save_config(work / 'config.json', config)
    initialize_credentials(work / 'input-secret', lambda: {'username': 'admin', 'password': secrets.token_urlsafe(32)})
    print(json.dumps({'deployment': name, 'local_evidence': str(work), 'nas_data': str(data), 'bind_address': config['bind_address']}), flush=True)
    result = apply_reference(config, name, work / 'state', work / 'input-secret/gui-admin.json')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
