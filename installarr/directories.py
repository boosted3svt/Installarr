"""Prepare configured directories on verified, already-mounted storage."""
import json
import os
from pathlib import Path
import pwd
import grp
import stat
import subprocess
import sys
import uuid

from .accounts import provisioning_gate
from .compose import DATA_TARGETS
from .dockerhost import installed_version
from .execution import Execution
from .hostplan import preparation_plan, storage_assertions

LOCAL_FILESYSTEMS = {'ext4', 'xfs', 'btrfs'}


def observed_mount(fd, require_writable=True):
    # The descriptor's kernel mount ID avoids traversing root-private ancestors
    # after dropping privileges, and cannot fall through to a replacement path.
    fields = dict(line.split(':', 1) for line in Path('/proc/self/fdinfo/{}'.format(fd)).read_text().splitlines() if ':' in line)
    mount_id = fields['mnt_id'].strip()
    result = subprocess.run(['findmnt', '--kernel', '--list', '--json',
        '--output', 'ID,TARGET,SOURCE,FSTYPE,OPTIONS'], capture_output=True, text=True, timeout=5, check=True)
    rows = [row for row in json.loads(result.stdout)['filesystems'] if str(row['id']) == mount_id]
    if len(rows) != 1 or (require_writable and 'rw' not in rows[0]['options'].split(',')):
        raise ValueError('Writable, unambiguous storage mount required')
    return {key: rows[0][key] for key in ('target', 'source', 'fstype')}


def open_anchor(path):
    """Open each existing component without symlinks; retain its directory FD."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    parts = Path(path).parts[1:]
    try:
        for index, part in enumerate(parts):
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                return fd, list(parts[index:])
            os.close(fd)
            fd = child
        return fd, []
    except BaseException:
        os.close(fd)
        raise


def directory_plan(config):
    checks = storage_assertions(config)
    if set(config.get('storage_mounts', {})) != set(config['storage']):
        raise ValueError('Storage type must be selected for every purpose')
    if config['storage_mounts']['configs']['kind'] != 'local':
        raise ValueError('Application databases require local storage')
    identity = config['service_user']
    entries = []
    for purpose, path in config['storage'].items():
        local = config['storage_mounts'][purpose]['kind'] == 'local'
        check = checks.get(purpose)
        if not local and not check:
            raise ValueError('Network directories require exact mount assertions')
        sentinel = check.get('sentinel') if check else None
        if purpose in DATA_TARGETS and (not sentinel or '/' in sentinel or sentinel in ('.', '..')
                                       or len(sentinel.encode()) > 255 or any(ord(char) < 32 or ord(char) == 127 for char in sentinel)):
            raise ValueError('Data directories require a basename health sentinel')
        from .hostplan import purpose_identity
        owner = purpose_identity(config, purpose)
        if purpose == 'netboot_assets' and (not check or not sentinel or '/' in sentinel):
            raise ValueError('Netboot assets require exact mount assertions and a basename sentinel')
        entries.append({'path': path, 'local': local, 'check': check, 'sentinel': sentinel,
                        'uid': owner['uid'], 'gid': owner['gid'], 'config_parent': purpose == 'configs', 'read_only': purpose == 'media_secondary' and config.get('secondary_media_read_only', True)})
    for app in config['apps']:
        uid, gid = (911, 1001) if app == 'netbootxyz' else (identity['uid'], identity['gid'])
        entries.append({'path': str(Path(config['storage']['configs']) / app), 'local': True,
                        'check': None, 'sentinel': None, 'uid': uid, 'gid': gid, 'application_config': True})
    if 'netbootxyz' in config['apps'] and 'netboot_assets' not in config['storage']:
        entries.append({'path': str(Path(config['storage']['configs']) / 'netbootxyz/assets'), 'local': True,
                        'check': None, 'sentinel': None, 'uid': 911, 'gid': 1001, 'application_config': True})
    if 'plex' in config['apps']:
        entries.append({'path': str(Path(config['storage']['configs']) / 'plex/transcode'), 'local': True,
                        'check': None, 'sentinel': None, 'uid': identity['uid'], 'gid': identity['gid'],
                        'application_config': True})
    if set(config['apps']) >= {'plex', 'tautulli'}:
        entries.append({'path': str(Path(config['storage']['configs']) / 'plex/Library/Application Support/Plex Media Server/Logs'),
                        'local': True, 'check': None, 'sentinel': None,
                        'uid': identity['uid'], 'gid': identity['gid'], 'application_config': True})
    if 'folder_map' in config:
        from .layout import entries as layout_entries
        for row in layout_entries(config):
            if any(entry['path'] == row['host'] for entry in entries):
                continue
            base = next(entry for entry in entries if entry['path'] == config['storage'][row['purpose']])
            entries.append({**base, 'path': row['host']})
    if 'sabnzbd' in config['apps'] or set(config['apps']) & {'radarr', 'sonarr'}:
        base = next(row for row in entries if row['path'] == config['storage']['downloads'])
        for category in ('movies', 'tv'):
            entries.append({**base, 'path': str(Path(base['path']) / category), 'sentinel': None})
    if 'plex' in config['apps'] and 'folder_map' not in config:
        from .plex import library_paths
        base = next(row for row in entries if row['path'] == config['storage']['media'])
        for item in library_paths(config):
            for path in item['host_paths']:
                if path == config['storage'].get('media_secondary'):
                    continue
                if not any(row['path'] == path for row in entries):
                    entries.append({**base, 'path': path, 'sentinel': None})
    for app, leaf in (() if 'folder_map' in config else (('sonarr', 'TV'), ('radarr', 'Movies'))):
        if app in config['apps']:
            base = next(row for row in entries if row['path'] == config['storage']['media'])
            entries.append({**base, 'path': str(Path(base['path']) / leaf), 'sentinel': None})
    if config.get('ombi_family_presets') and 'folder_map' not in config:
        from .ombi_family import family_paths
        base = next(row for row in entries if row['path'] == config['storage']['media'])
        for routes in family_paths(config).values():
            for route in routes.values():
                if not any(row['path'] == route['host_path'] for row in entries):
                    entries.append({**base, 'path': route['host_path'], 'sentinel': None})
    return entries


def worker(spec):
    fd = spec['fd']
    created = 0
    if not spec['local']:
        os.setgroups([])
        os.setgid(spec['gid'])
        os.setuid(spec['uid'])
    def verify():
        if observed_mount(fd, require_writable=not spec.get('read_only')) != spec['expected']:
            raise ValueError('Storage mount changed; no fallback writes permitted')
    try:
        verify()
        if spec.get('read_only'):
            if spec['parts']:
                raise ValueError('Secondary media must already exist; no directories created')
            if spec['local']:
                os.setgroups([])
                os.setgid(spec['gid'])
                os.setuid(spec['uid'])
            access = os.open('.', os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
            os.close(access)
            marker = os.open(spec['sentinel'], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(marker, 'rb') as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode) or b'\n' not in source.read(4096):
                    raise ValueError('Secondary health marker invalid; preserved')
            return {'path': spec['path'], 'created_components': 0, 'write_verified': False,
                    'read_verified': True, 'uid': os.geteuid(), 'gid': os.getegid()}
        for part in spec['parts']:
            verify()
            try:
                os.mkdir(part, 0o750, dir_fd=fd)
                new = True
            except FileExistsError:
                new = False
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            verify()
            if new:
                created += 1
                if spec['local']:
                    os.fchown(fd, spec['uid'], spec['gid'])
        info = os.fstat(fd)
        if spec.get('application_config') and (info.st_uid, info.st_gid) != (spec['uid'], spec['gid']):
            raise ValueError('Existing app config ownership differs; preserved')
        if spec.get('config_parent'):
            return {'path': spec['path'], 'created_components': created, 'write_verified': False,
                    'note': 'Host config parent preserved; app subdirectories checked separately'}
        sentinel = spec.get('sentinel')
        if sentinel:
            verify()
            try:
                handle = os.open(sentinel, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=fd)
            except FileExistsError:
                handle = None
            if handle is not None:
                with os.fdopen(handle, 'wb') as output:
                    output.write(b'Installarr storage health\n')
                    output.flush()
                    os.fsync(output.fileno())
            handle = os.open(sentinel, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(handle, 'rb') as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or b'\n' not in source.read(4096):
                    raise ValueError('Existing health marker invalid; preserved')
        # Actual write access is required, even for pre-existing directories.
        # For local app directories root must not hide a service-UID mismatch.
        if spec['local']:
            os.setgroups([])
            os.setgid(spec['gid'])
            os.setuid(spec['uid'])
            # Keep using the already-verified FD: private local ancestors need
            # not be traversable by the container's service user on the host.
        else:
            verify()
        probe = '.installarr-access-' + uuid.uuid4().hex
        handle = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            with os.fdopen(handle, 'wb') as output:
                output.write(b'Installarr write check\n')
                output.flush()
                os.fsync(output.fileno())
        finally:
            os.unlink(probe, dir_fd=fd)
        return {'path': spec['path'], 'created_components': created, 'uid': os.geteuid(), 'gid': os.getegid(), 'write_verified': True}
    finally:
        os.close(fd)


def prepare_directories(config, state_directory=Path('/var/lib/installarr-directories')):
    from .cli import validate
    validate(config)
    provisioning_gate()
    identity = config['service_user']
    try:
        account = pwd.getpwnam(identity['name'])
        if account.pw_uid != identity['uid'] or account.pw_gid != identity['gid']:
            raise ValueError('Prepare the configured service identity first')
        if 'netbootxyz' in config['apps'] and (pwd.getpwnam('nbxyz').pw_uid != 911 or pwd.getpwnam('nbxyz').pw_gid != 1001 or grp.getgrnam('nbxyz').gr_gid != 1001):
            raise ValueError('Prepare the required nbxyz identity first')
    except KeyError:
        raise ValueError('Prepare required service identities before directories') from None
    if any(installed_version(package) is None for package in preparation_plan(config)['required_storage_packages']):
        raise ValueError('Prepare storage client prerequisites before directory operations')
    entries = directory_plan(config)
    anchors = []
    results = []
    try:
        # Worker opens may block on a hard NAS mount. Transfer held FDs back
        # rather than repeating those opens in this foreground process.
        from .anchors import open_anchors
        requests = [{'path': entry['path'], 'read_only': entry.get('read_only', False)} for entry in entries]
        requests.append({'path': str(Path(state_directory).parent), 'read_only': False})
        held = open_anchors(requests)
        anchors = [row[0] for row in held]
        for entry, (fd, parts, observed) in zip(entries, held[:-1]):
            expected = entry['check']
            if expected and observed != {key: expected[field] for key, field in
                                        (('target', 'mountpoint'), ('source', 'source'), ('fstype', 'fstype'))}:
                raise ValueError('Configured storage is not mounted as expected')
            if entry['local'] and observed['fstype'] not in LOCAL_FILESYSTEMS:
                raise ValueError('Declared local storage is not on a supported local filesystem')
            if entry.get('read_only') and parts:
                raise ValueError('Secondary source must exist before any storage writes')
            entry.update(fd=fd, parts=parts, expected=observed)
        state_fd, missing, state_mount = held[-1]
        if missing or state_mount['fstype'] not in LOCAL_FILESYSTEMS:
            raise ValueError('Checkpoint parent must exist on local storage')
        with Execution(state_directory, {'operation': 'directories-v1', 'config': config}) as execution:
            for index, entry in enumerate(entries):
                def reconcile():
                    from .storage_process import run_storage
                    result = run_storage([sys.executable, '-B', '-m', 'installarr.directories', '--worker'],
                        input=json.dumps(entry), pass_fds=(entry['fd'],), timeout=15, operation='prepare-directory')
                    if result.returncode:
                        raise ValueError('Directory preparation refused for {}; existing data preserved'.format(entry['path']))
                    results.append(json.loads(result.stdout))
                execution.reconcile('directory-{}'.format(index), reconcile)
        return {'status': 'verified', 'directories': results, 'note': 'Existing mounts only; existing ownership/files preserved. No fstab edits or media operations.'}
    finally:
        for fd in anchors:
            os.close(fd)


if __name__ == '__main__':
    if sys.argv[1:] != ['--worker']:
        raise SystemExit('Internal directory worker only')
    print(json.dumps(worker(json.load(sys.stdin))))
