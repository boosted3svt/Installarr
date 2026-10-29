"""Visible, retained directory-preparation fixture inside the exact test export."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.cli import save_config
from installarr.directories import observed_mount, prepare_directories


def main():
    root = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    expected = {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    try:
        if observed_mount(root) != expected:
            raise ValueError('Exact writable test mount required')
    finally:
        os.close(root)
    base = Path('/media/installarr') / ('Installarr-Directory-Test-20261028-' + uuid.uuid4().hex[:8])
    work = Path(tempfile.mkdtemp(prefix='installarr-directories-', dir='/var/tmp'))
    config = {'schema_version': 1, 'apps': ['sonarr', 'radarr', 'sabnzbd'], 'timezone': 'America/Chicago',
              'bind_address': '127.0.0.1', 'plex_allowed_networks': '192.168.0.0/23',
              'service_user': {'name': 'installarr-test', 'uid': 2000, 'gid': 2000},
              'project_directory': str(work / 'project'),
              'storage': {**{key: str(base / key) for key in ('media', 'downloads', 'incomplete')},
                          'configs': str(work / 'configs'), 'backups': str(work / 'backups')},
              'storage_mounts': {**{key: {'kind': 'existing', 'mountpoint': expected['target'], 'source': expected['source'],
                                         'fstype': 'nfs', 'sentinel': 'health'} for key in ('media', 'downloads', 'incomplete')},
                                 'configs': {'kind': 'local'}, 'backups': {'kind': 'local'}}}
    save_config(work / 'config.json', config)
    state = work / 'state'
    bad = copy.deepcopy(config)
    bad['storage_mounts']['media']['source'] += '-wrong'
    try:
        prepare_directories(bad, state)
    except ValueError:
        pass
    else:
        raise ValueError('Wrong mount source accepted')
    if base.exists() or (work / 'configs').exists() or state.exists():
        raise ValueError('Storage writes preceded complete mount verification')
    print(json.dumps({'visible_test_directory': str(base), 'stage': 'preparing'}), flush=True)
    first = prepare_directories(config, state)
    files = [base / purpose / 'health' for purpose in ('media', 'downloads', 'incomplete')]
    before = {str(path): (path.stat().st_ino, path.stat().st_uid, path.stat().st_gid,
                         path.stat().st_mode, path.stat().st_mtime_ns, path.read_bytes()) for path in files}
    second = prepare_directories(config, state)
    if any(row['created_components'] != 0 for row in second['directories']):
        raise ValueError('Rerun unexpectedly created directories')
    after = {str(path): (path.stat().st_ino, path.stat().st_uid, path.stat().st_gid,
                        path.stat().st_mode, path.stat().st_mtime_ns, path.read_bytes()) for path in files}
    if before != after:
        raise ValueError('Existing health markers were changed')
    app = work / 'configs/sonarr'
    os.chown(str(app), 0, 0)
    try:
        prepare_directories(config, state)
    except ValueError:
        if app.stat().st_uid != 0:
            raise ValueError('Conflicting existing app ownership was changed')
    else:
        raise ValueError('Conflicting app ownership was accepted')
    os.chown(str(app), 2000, 2000)
    final = prepare_directories(config, state)
    save_config(work / 'final-config.json', config)
    print(json.dumps({'result': 'passed', 'retained_visible_nas_directory': str(base),
                      'retained_local_evidence': str(work), 'created_directories': first['directories'],
                      'wrong_mount_no_writes': True, 'rerun_preserved_markers': True,
                      'ownership_conflict_preserved_and_recovered': True,
                      'note': 'Health markers retained for operator observation. Original Movies and TV untouched.'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
