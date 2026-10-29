"""Existing read-only source mount in private namespace; live mounts unchanged."""
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.cli import save_config
from installarr.directories import observed_mount, prepare_directories
from installarr.lifecycle import BoundedProbe, health_spec, local_mount
from installarr.mounts import prepare_mounts, runtime_mounts

SOURCE = '192.168.1.102:/share/MD0_DATA/Public/installarr'


def child(work):
    work = Path(work)
    config = json.loads((work / 'config.json').read_text())
    target = work / 'readonly'
    target.mkdir()
    subprocess.run(['mount', '--bind', '/media/installarr', str(target)], check=True)
    try:
        # MS_BIND remount changes only this private mount's flags, not the NAS
        # superblock or the original host mount.
        subprocess.run(['mount', '-o', 'remount,bind,ro', str(target)], check=True)
        fd = os.open(config['storage']['media_secondary'], os.O_RDONLY | os.O_DIRECTORY)
        try:
            observed = observed_mount(fd, require_writable=False)
            assert observed == {'target': str(target), 'source': SOURCE, 'fstype': 'nfs'}
            result = subprocess.run([sys.executable, '-B', '-c',
                'import errno,os,sys; os.setgroups([]); os.setgid(2000); os.setuid(2000);\ntry: os.open("must-not-exist",os.O_WRONLY|os.O_CREAT,0o600,dir_fd=int(sys.argv[1]))\nexcept OSError as e: assert e.errno==errno.EROFS\nelse: raise AssertionError("Read-only mount accepted a write")', str(fd)], pass_fds=(fd,), capture_output=True, check=True)
        finally:
            os.close(fd)
        fixture = work / 'fixture.fstab'
        original = (SOURCE + ' ' + str(target) + ' nfs ro,_netdev 0 0\n').encode()
        fixture.write_bytes(original)
        mounted = prepare_mounts(config, work / 'mount-state', fixture)
        assert not mounted['persistence']['changed'] and fixture.read_bytes() == original
        directories = prepare_directories(config, work / 'directory-state')
        secondary = next(r for r in directories['directories'] if r['path'] == config['storage']['media_secondary'])
        assert secondary['read_verified'] and not secondary['write_verified'] and secondary['created_components'] == 0
        probe = BoundedProbe(health_spec(config, local_mount(config['storage']['configs'])))
        try:
            wait_for(lambda: probe.check(threading.Event())['healthy'])
        finally:
            probe.close()
        print(json.dumps({'status': 'passed', 'private_readonly_mount': observed,
                          'service_uid_write': 'refused with EROFS', 'directory_read': secondary,
                          'uid_health': 'healthy with read-only source', 'fixture_fstab': 'unchanged',
                          'application_startup': 'not attempted in private namespace'}), flush=True)
    finally:
        subprocess.run(['umount', '--', str(target)], check=True, timeout=15)


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-readonly-secondary-', dir='/var/tmp'))
    leaf = 'Installarr-Readonly-Secondary-' + uuid.uuid4().hex[:8]
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        assert observed_mount(fd) == {'target': '/media/installarr', 'source': SOURCE, 'fstype': 'nfs'}
        script = 'import os,sys;os.setgroups([]);os.setgid(2000);os.setuid(2000);root=int(sys.argv[1]);os.mkdir(sys.argv[2],0o750,dir_fd=root);d=os.open(sys.argv[2],os.O_RDONLY|os.O_DIRECTORY,dir_fd=root);f=os.open("source-ready",os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o640,dir_fd=d);os.write(f,b"Installarr read-only source\\n");os.fsync(f);os.close(f);os.close(d)'
        subprocess.run([sys.executable, '-B', '-c', script, str(fd), leaf], pass_fds=(fd,), check=True)
    finally:
        os.close(fd)
    source_marker = Path('/media/installarr') / leaf / 'source-ready'
    before = (source_marker.read_bytes(), source_marker.stat().st_mtime_ns, source_marker.stat().st_uid, source_marker.stat().st_gid)
    config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    data = Path('/media/installarr') / (leaf + '-Primary')
    config.update(apps=['plex'], data_root=str(data), project_directory=str(work / 'project'))
    config.pop('quality_profiles', None)
    config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                             configs=str(work / 'configs'), backups=str(work / 'backups'), media_secondary=str(work / 'readonly' / leaf))
    config['storage_mounts']['media_secondary'] = {'kind': 'existing', 'mountpoint': str(work / 'readonly'),
                                                  'source': SOURCE, 'fstype': 'nfs', 'sentinel': 'source-ready'}
    save_config(work / 'config.json', config)
    fstab_hash = hashlib.sha256(Path('/etc/fstab').read_bytes()).hexdigest()
    print(json.dumps({'evidence': str(work), 'source_fixture': str(source_marker.parent)}), flush=True)
    result = subprocess.run(['unshare', '--mount', '--propagation', 'private', sys.executable, '-B', __file__, '--child', str(work)],
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        (work / 'failure.log').write_text(result.stderr)
        raise ValueError('Private read-only source acceptance failed; evidence retained')
    outcome = json.loads(result.stdout)
    assert (source_marker.read_bytes(), source_marker.stat().st_mtime_ns, source_marker.stat().st_uid, source_marker.stat().st_gid) == before
    assert hashlib.sha256(Path('/etc/fstab').read_bytes()).hexdigest() == fstab_hash
    assert not any(r['target'] == str(work / 'readonly') for r in runtime_mounts())
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert observed_mount(fd) == {'target': '/media/installarr', 'source': SOURCE, 'fstype': 'nfs'}
    finally:
        os.close(fd)
    outcome.update(live_mount_fstab='unchanged', source_bytes_metadata='unchanged')
    (work / 'result.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps(outcome), flush=True)


if __name__ == '__main__':
    child(sys.argv[2]) if sys.argv[1:2] == ['--child'] else main()
