"""Fresh NFS mount in a PRIVATE mount namespace; live fstab/NAS mount untouched."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.cli import save_config
from installarr.directories import observed_mount, prepare_directories
from installarr.mounts import prepare_mounts, runtime_mounts


def child(config_path, work):
    config = json.loads(Path(config_path).read_text())
    work = Path(work)
    fstab = work / 'fixture.fstab'
    original = b'# Existing operator fixture entry must be retained exactly\n'
    fstab.write_bytes(original)
    fstab.chmod(0o644)
    state = work / 'mount-state'
    first = prepare_mounts(config, state, fstab)
    if not first['persistence']['changed']:
        raise ValueError('New declaration not persisted')
    backup = Path(first['persistence']['backup'])
    if backup.read_bytes() != original or backup.stat().st_mode & 0o777 != 0o600:
        raise ValueError('Backup differs or is not private')
    saved = fstab.read_bytes()
    second = prepare_mounts(config, state, fstab)
    if second['persistence']['changed'] or fstab.read_bytes() != saved:
        raise ValueError('Rerun rewrote or duplicated persistence')
    result = prepare_directories(config, work / 'directory-state')
    if not all(row.get('write_verified') for row in result['directories'] if not row.get('note')):
        raise ValueError('Service-UID checks failed on new mount')
    mounts = [row for row in runtime_mounts() if row['target'] == str(work / 'mount')]
    print(json.dumps({'result': 'passed', 'private_namespace_mount': mounts,
                      'fstab_backup_exact': True, 'fstab_rerun_unchanged': True,
                      'service_uid_directory_writes': 'passed'}, indent=2), flush=True)
    subprocess.run(['umount', '--', str(work / 'mount')], check=True, timeout=15)


def main():
    root = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    expected = {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    try:
        if observed_mount(root) != expected:
            raise ValueError('Exact original test mount required')
        name = 'Installarr-Mount-Test-' + uuid.uuid4().hex[:10]
        subprocess.run([sys.executable, '-B', '-c',
                       'import os,sys; os.setgroups([]); os.setgid(2000); os.setuid(2000); os.mkdir(sys.argv[2],0o750,dir_fd=int(sys.argv[1]))',
                       str(root), name], pass_fds=(root,), check=True, timeout=10)
    finally:
        os.close(root)
    work = Path(tempfile.mkdtemp(prefix='installarr-mounts-', dir='/var/tmp'))
    target = work / 'mount'
    source = expected['source']
    config = {'schema_version': 1, 'apps': ['sabnzbd'], 'timezone': 'America/Chicago', 'bind_address': '127.0.0.1',
              'plex_allowed_networks': '192.168.0.0/23', 'service_user': {'name': 'installarr-test', 'uid': 2000, 'gid': 2000},
              'project_directory': str(work / 'project'),
              'storage': {**{key: str(target / name / key) for key in ('media', 'downloads', 'incomplete')},
                          'configs': str(work / 'configs'), 'backups': str(work / 'backups')},
              'storage_mounts': {**{key: {'kind': 'nfs', 'mountpoint': str(target), 'source': source, 'fstype': 'nfs',
                                         'sentinel': 'health'} for key in ('media', 'downloads', 'incomplete')},
                                 'configs': {'kind': 'local'}, 'backups': {'kind': 'local'}}}
    save_config(work / 'config.json', config)
    original_fstab = hashlib.sha256(Path('/etc/fstab').read_bytes()).hexdigest()
    print(json.dumps({'retained_nas_directory': '/media/installarr/' + name, 'local_evidence': str(work)}), flush=True)
    subprocess.run(['unshare', '--mount', '--propagation', 'private', sys.executable, '-B', __file__,
                    '--child', str(work / 'config.json'), str(work)], check=True, timeout=180)
    if hashlib.sha256(Path('/etc/fstab').read_bytes()).hexdigest() != original_fstab:
        raise ValueError('Live fstab changed')
    if any(row['target'] == str(target) for row in runtime_mounts()):
        raise ValueError('Private mount leaked into host namespace')
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if observed_mount(fd) != expected:
            raise ValueError('Original test mount changed')
    finally:
        os.close(fd)
    print(json.dumps({'live_fstab_unchanged': True, 'private_mount_not_visible_on_host': True,
                      'original_test_mount_preserved': True}), flush=True)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--child']:
        child(sys.argv[2], sys.argv[3])
    else:
        main()
