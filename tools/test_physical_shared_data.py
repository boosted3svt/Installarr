"""Verify reference-style shared data paths using only a new owned NAS subtree."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.cli import save_config
from installarr.compose import application_paths, render_bundle, write_bundle
from installarr.directories import observed_mount, prepare_directories

DOCKER = ['docker', '--host', 'unix:///run/docker.sock']


def main():
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    expected = {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    try:
        if observed_mount(fd) != expected:
            raise ValueError('Exact authorized test mount required')
    finally:
        os.close(fd)
    root = Path('/media/installarr') / ('Installarr-Shared-Data-' + uuid.uuid4().hex[:10])
    work = Path(tempfile.mkdtemp(prefix='installarr-shared-data-', dir='/var/tmp'))
    config = {'schema_version': 1, 'apps': ['radarr', 'sabnzbd'], 'timezone': 'America/Chicago',
              'bind_address': '127.0.0.1', 'plex_allowed_networks': '192.168.0.0/23',
              'service_user': {'name': 'installarr-test', 'uid': 2000, 'gid': 2000},
              'project_directory': str(work / 'project'), 'data_root': str(root),
              'storage': {'media': str(root), 'downloads': str(root / 'downloads'),
                          'incomplete': str(root / 'incomplete-downloads'),
                          'configs': str(work / 'configs'), 'backups': str(work / 'backups')},
              'storage_mounts': {**{purpose: {'kind': 'existing', 'mountpoint': expected['target'], 'source': expected['source'],
                                             'fstype': 'nfs', 'sentinel': 'health'} for purpose in ('media', 'downloads', 'incomplete')},
                                 'configs': {'kind': 'local'}, 'backups': {'kind': 'local'}}}
    save_config(work / 'config.json', config)
    prepare_directories(config, work / 'state')
    write_bundle(config)
    service = render_bundle(config)['compose']['services']['sabnzbd']
    def run(script, extra=None):
        args = DOCKER + ['run', '--rm', '--network', 'none', '--user', '2000:2000', '--entrypoint', '/bin/sh']
        volumes = service['volumes'] + (extra or [])
        for volume in volumes:
            value = 'type=bind,source=' + volume['source'] + ',target=' + volume['target'] + ',bind-propagation=rprivate'
            if volume['read_only']:
                value += ',readonly'
            args += ['--mount', value]
        args += [service['image'], '/installarr-storage-guard', '/bin/sh', '-c', script]
        return subprocess.run(args, capture_output=True, text=True, timeout=30)
    script = '''set -eu
from=/data/downloads/.installarr-link-probe
to=/data/Movies/.installarr-link-probe
trap 'rm -f "$from" "$to"' EXIT
(set -C; printf 'Installarr shared-path proof\n' > "$from")
ln "$from" "$to"
[ "$(stat -c %i "$from")" = "$(stat -c %i "$to")" ]
printf 'shared_hardlink_verified\n'
'''
    result = run(script)
    if result.returncode or result.stdout.strip() != 'shared_hardlink_verified':
        raise ValueError('Shared bind did not permit the expected guarded hardlink')
    fake = work / 'fake-media'
    fake.mkdir(mode=0o755)
    (fake / 'health').write_text('Fake local filesystem marker\n')
    from installarr.compose import bind
    result = run('echo ENTRYPOINT_RAN', [bind(fake, '/data/downloads')])
    if result.returncode != 78 or 'ENTRYPOINT_RAN' in result.stdout:
        raise ValueError('Wrong child mount reached the application command')
    print(json.dumps({'result': 'passed', 'shared_data_root': str(root), 'local_evidence': str(work),
                      'paths': {app: application_paths(config, app) for app in config['apps']},
                      'hardlink_same_inode': True, 'wrong_nested_mount_refused_before_entrypoint': True,
                      'original_media_touched': False}, indent=2))


if __name__ == '__main__':
    main()
