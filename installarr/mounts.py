"""Read-only reconciliation of declared mounts, runtime identity and fstab."""
from pathlib import Path
import re

from .hostplan import preparation_plan


def unescape(value):
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match.group(1), 8)), value)


def parse_fstab(text):
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        if not fields or fields[0].startswith('#'):
            continue
        for index in range(3, len(fields)):
            if fields[index].startswith('#'):
                fields = fields[:index]
                break
        if len(fields) < 3:
            raise ValueError('Malformed fstab entry on line {}'.format(number))
        rows.append({'source': unescape(fields[0]), 'target': unescape(fields[1]),
                     'fstype': fields[2], 'options': fields[3].split(',') if len(fields) > 3 else ['defaults'],
                     'line': number})
    return rows


def mount_review(config, runtime_rows, fstab_text):
    records = parse_fstab(fstab_text)
    results = []
    for mount in preparation_plan(config)['mounts']:
        target = mount['mountpoint']
        declarations = [row for row in records if row['target'] == target]
        actual = [row for row in runtime_rows if row['target'] == target]
        result = {'mountpoint': target, 'kind': mount['kind'], 'runtime': 'missing', 'persistence': 'missing',
                  'action': 'reuse' if mount['kind'] == 'existing' else 'prepare', 'conflicts': []}
        def compatible(row):
            return row['source'] == mount['source'] and (row['fstype'] == mount['fstype'] or
                   {row['fstype'], mount['fstype']} <= {'nfs', 'nfs4'})
        if len(declarations) > 1:
            result['conflicts'].append('duplicate_fstab_target')
        elif declarations:
            if not compatible(declarations[0]):
                result['conflicts'].append('fstab_source_or_type')
            elif 'ro' in declarations[0]['options'] and not mount.get('read_only'):
                result['conflicts'].append('fstab_read_only')
            else:
                result['persistence'] = 'matching_fstab'
                result['automatic_mount'] = 'noauto' not in declarations[0]['options'] or 'x-systemd.automount' in declarations[0]['options']
                # Never reveal credentials from operator-owned fstab mount options.
                if any(item.startswith(('username=', 'password=', 'user=', 'pass=')) for item in declarations[0]['options']):
                    result['conflicts'].append('inline_credentials_preserved')
        if len(actual) > 1:
            result['conflicts'].append('ambiguous_runtime_mount')
        elif actual:
            if actual[0]['source'] != mount['source'] or actual[0]['fstype'] != mount['fstype']:
                result['conflicts'].append('runtime_source_or_type')
            else:
                result['runtime'] = 'matching'
        if result['conflicts']:
            result['action'] = 'refuse_preserve_existing'
        elif result['runtime'] == 'missing' and mount['kind'] == 'existing':
            result['action'] = 'existing_mount_required'
        results.append(result)
    return {'status': 'conflict' if any(row['conflicts'] for row in results) else 'reviewed',
            'mounts': results, 'changed': False,
            'note': 'Read-only review; missing fstab may be managed elsewhere and is not boot-persistence proof.'}


def check_mounts(config):
    from .cli import command, validate
    from .storage import mount_inventory
    validate(config)
    observed = mount_inventory(command)
    if observed['status'] != 'observed':
        raise ValueError('Mount inventory unavailable')
    return mount_review(config, observed['filesystems'], Path('/etc/fstab').read_text())


def require_existing_mounts(config):
    result = check_mounts(config)
    if result['status'] == 'conflict' or any(row['runtime'] != 'matching' for row in result['mounts']):
        raise ValueError('Mount reconciliation failed; existing configuration preserved')
    return result


def escape_field(value):
    return value.replace('\\', r'\134').replace(' ', r'\040').replace('\t', r'\011')


def mount_options(mount, identity):
    if mount['kind'] == 'nfs':
        # Keep the configured filesystem assertion deterministic: nfs=v3,
        # nfs4=v4. Never weaken hard-mount data-integrity semantics.
        return ['ro' if mount.get('read_only') else 'rw', 'vers=4' if mount['fstype'] == 'nfs4' else 'vers=3', 'proto=tcp', 'hard']
    if mount['kind'] == 'smb':
        if ',' in mount['credentials_file']:
            raise ValueError('SMB credential path cannot contain a mount-option separator')
        return ['ro' if mount.get('read_only') else 'rw', 'vers=3.0', 'credentials=' + mount['credentials_file'],
                'uid=' + str(identity['uid']), 'gid=' + str(identity['gid']),
                'forceuid', 'forcegid', 'dir_mode=0750', 'file_mode=0640']
    raise ValueError('Existing mounts do not receive new options')


def persistence_line(mount, identity, transport=None):
    options = mount_options(mount, identity) + (transport or []) + ['_netdev', 'nofail', 'x-systemd.mount-timeout=15s']
    return '{} {} {} {} 0 0\n'.format(escape_field(mount['source']), escape_field(mount['mountpoint']),
                                      mount['fstype'], ','.join(escape_field(item) for item in options))


def protected_smb_file(path):
    import os
    import stat
    path = Path(path)
    if path.resolve() != path:
        raise ValueError('SMB credential path contains a symlink')
    for parent in path.parents:
        info = parent.stat()
        if info.st_uid != 0 or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
            raise ValueError('SMB credentials require trusted parent directories')
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1 or info.st_size > 65536):
            raise ValueError('SMB credentials require a root-owned private regular file')
        values = {}
        for line in handle.read(65537).decode().splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            if '=' not in line:
                raise ValueError('Invalid SMB credential file')
            name, value = line.split('=', 1)
            if name not in ('username', 'password', 'domain') or name in values or not value or '\x00' in value:
                raise ValueError('Invalid SMB credential file')
            values[name] = value
        if not {'username', 'password'} <= set(values):
            raise ValueError('SMB credential file requires username and password')
    return True


def append_persistence(path, lines, state):
    """Append only after an exact backup and optimistic external-change check."""
    import hashlib
    import os
    import stat
    import tempfile
    from .compose import private_artifact
    from .execution import Execution
    path = Path(path)
    lock = Path('/var/lib/installarr-fstab') if path == Path('/etc/fstab') else Path(state) / 'fstab-lock'
    with Execution(lock, {'operation': 'fstab-append-v1'}):
        if path.resolve() != path:
            raise ValueError('Persistence file contains a symlink')
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1
                    or info.st_mode & 0o022 or info.st_size > 1048576):
                raise ValueError('Unsafe existing persistence file; preserved')
            old = source.read(1048577)
        records = parse_fstab(old.decode())
        additions = []
        for line in lines:
            proposed = parse_fstab(line)[0]
            matching = [row for row in records if row['target'] == proposed['target']]
            if matching:
                if len(matching) != 1 or any(matching[0][key] != proposed[key] for key in ('source', 'fstype')):
                    raise ValueError('Persistence changed before append; preserved')
                continue
            additions.append(line)
        if not additions:
            return {'changed': False}
        backup = Path(state) / ('fstab-before-' + hashlib.sha256(old).hexdigest() + '.bak')
        private_artifact(backup, old, 0o600)
        new = old + (b'\n' if old and not old.endswith(b'\n') else b'') + ''.join(additions).encode()
        fd, temporary = tempfile.mkstemp(prefix='.installarr-fstab-', dir=str(path.parent))
        try:
            with os.fdopen(fd, 'wb') as target:
                target.write(new)
                target.flush()
                os.fchmod(target.fileno(), stat.S_IMODE(info.st_mode))
                os.fchown(target.fileno(), info.st_uid, info.st_gid)
                os.fsync(target.fileno())
            current = os.stat(str(path), follow_symlinks=False)
            if (current.st_ino, current.st_dev, current.st_mtime_ns) != (info.st_ino, info.st_dev, info.st_mtime_ns) or path.read_bytes() != old:
                raise ValueError('Persistence changed during review; preserved')
            os.replace(temporary, str(path))
            parent = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {'changed': True, 'backup': str(backup)}


def runtime_mounts():
    from .cli import command
    from .storage import mount_inventory
    result = mount_inventory(command)
    if result['status'] != 'observed':
        raise ValueError('Mount inventory unavailable')
    return result['filesystems']



def verified_nfs_transport(mount):
    """Reuse only kernel-reported transport for this exact already-mounted source."""
    import subprocess
    if mount['kind'] != 'nfs':
        return []
    result = subprocess.run(['findmnt', '--kernel', '--list', '--json', '--source', mount['source'],
                             '--output', 'SOURCE,FSTYPE,OPTIONS'], capture_output=True, text=True, timeout=5)
    if result.returncode:
        return []
    choices = []
    for row in __import__('json').loads(result.stdout).get('filesystems', []):
        if row['source'] != mount['source'] or row['fstype'] != mount['fstype']:
            continue
        options = dict(item.split('=', 1) for item in row['options'].split(',') if '=' in item)
        selected = ['port=' + options.get('port', '2049')]
        for name in ('mountport', 'mountproto', 'mountvers'):
            value = options.get(name)
            if value is not None:
                if (name == 'mountproto' and value not in ('tcp', 'udp')) or (name != 'mountproto' and not value.isdigit()):
                    raise ValueError('Unexpected kernel transport option')
                selected.append(name + '=' + value)
        if not options.get('port', '2049').isdigit():
            raise ValueError('Unexpected kernel transport port')
        choices.append(selected)
    if not choices or any(value != choices[0] for value in choices):
        return []
    return choices[0]

def prepare_mounts(config, state_directory=Path('/var/lib/installarr-mounts'), fstab_path=Path('/etc/fstab')):
    import os
    import subprocess
    from .accounts import provisioning_gate
    from .directories import LOCAL_FILESYSTEMS, observed_mount
    from .anchors import open_anchors
    from .storage_process import run_storage
    from .execution import Execution
    from .prerequisites import prepare_prerequisites
    from .cli import validate
    validate(config)
    provisioning_gate()
    plans = preparation_plan(config)['mounts']
    review = mount_review(config, runtime_mounts(), Path(fstab_path).read_text())
    if review['status'] == 'conflict':
        raise ValueError('Conflicting mount/persistence configuration preserved')
    if any(row['kind'] == 'existing' and row['runtime'] != 'matching' for row in review['mounts']):
        raise ValueError('Configured existing mount is absent; no replacement attempted')
    for mount in plans:
        if mount['kind'] == 'smb':
            protected_smb_file(mount['credentials_file'])
    fd, missing, observed = open_anchors([{'path': str(Path(state_directory).parent)}])[0]
    try:
        if missing or observed['fstype'] not in LOCAL_FILESYSTEMS:
            raise ValueError('Mount checkpoints require an existing local parent')
    finally:
        os.close(fd)
    evidence = []
    transport = {mount["mountpoint"]: verified_nfs_transport(mount) for mount in plans}
    with Execution(state_directory, {'operation': 'mounts-v1', 'config': config}) as execution:
        execution.reconcile('prerequisites', lambda: prepare_prerequisites(config, Path(state_directory) / 'prerequisites'))
        for index, mount in enumerate(plans):
            def reconcile():
                rows = [row for row in runtime_mounts() if row['target'] == mount['mountpoint']]
                if rows:
                    if len(rows) != 1 or rows[0]['source'] != mount['source'] or rows[0]['fstype'] != mount['fstype']:
                        raise ValueError('Unexpected mount appeared; preserved')
                    fd, missing, observed = open_anchors([{'path': mount['mountpoint'], 'read_only': bool(mount.get('read_only'))}])[0]
                    try:
                        if missing:
                            raise ValueError('Existing mount path disappeared')
                    finally:
                        os.close(fd)
                    return
                if mount['kind'] == 'existing':
                    raise ValueError('Existing mount disappeared; no fallback')
                parent, parts, expected = open_anchors([{'path': mount['mountpoint']}])[0]
                try:
                    if expected['fstype'] not in LOCAL_FILESYSTEMS:
                        raise ValueError('New mountpoints require local empty directories')
                    for part in parts:
                        if observed_mount(parent) != expected:
                            raise ValueError('Mountpoint ancestor changed')
                        try:
                            os.mkdir(part, 0o755, dir_fd=parent)
                        except FileExistsError:
                            pass
                        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                        os.close(parent)
                        parent = child
                    if observed_mount(parent) != expected or os.listdir(parent):
                        raise ValueError('Nonempty/changed mountpoint preserved')
                    # Mount the held empty directory, not a path that can be redirected.
                    options = mount_options(mount, mount.get('write_identity', config['service_user'])) + transport[mount['mountpoint']]
                    if mount['kind'] == 'nfs':
                        options = options + ['retry=0']
                    process = run_storage(['mount', '-n', '-t', mount['fstype'], '-o',
                        ','.join(options), '--', mount['source'], '/proc/self/fd/{}'.format(parent)],
                        pass_fds=(parent,), timeout=30, operation='mount')
                    if process.returncode:
                        raise ValueError('Network mount failed; configuration preserved')
                finally:
                    os.close(parent)
                rows = [row for row in runtime_mounts() if row['target'] == mount['mountpoint']]
                if len(rows) != 1 or rows[0]['source'] != mount['source'] or rows[0]['fstype'] != mount['fstype']:
                    raise ValueError('Network mount readback differs; applications remain stopped')
                fd, missing, observed = open_anchors([{'path': mount['mountpoint'], 'read_only': bool(mount.get('read_only'))}])[0]
                try:
                    if missing:
                        raise ValueError('Mounted path disappeared before readback')
                finally:
                    os.close(fd)
            execution.reconcile('mount-{}'.format(index), reconcile)
            evidence.append({'mountpoint': mount['mountpoint'], 'source': mount['source'], 'fstype': mount['fstype'], 'runtime': 'verified'})
        lines = [persistence_line(mount, mount.get('write_identity', config['service_user']), transport[mount['mountpoint']]) for mount in plans if mount['kind'] in ('nfs', 'smb')]
        persistence = {'changed': False}
        def persist():
            persistence.update(append_persistence(fstab_path, lines, state_directory))
            if Path(fstab_path) == Path('/etc/fstab') and lines:
                from .lifecycle import command
                command(['systemctl', 'daemon-reload'])
        execution.reconcile('persistence', persist)
    return {'status': 'verified', 'mounts': evidence, 'persistence': persistence,
            'note': 'Existing entries/mounts preserved; no disks formatted, no unmounts, no recursive ownership edits.'}
