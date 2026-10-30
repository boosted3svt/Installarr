"""Opt-in, bounded host-side repair of Plex media read access.

No media is opened for writing. Ownership UIDs are preserved; when required, the
shared service GID receives read/search permission. Policy and progress are local
and private, independent of immutable Compose/config fingerprints.
"""
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import threading
import time

INTERVAL = 60
BATCH_ENTRIES = 1000
BATCH_SECONDS = 5
WORKER_TIMEOUT = 30
MAX_DEPTH = 128


def repair_spec(config):
    from .hostplan import storage_assertions
    from .plex import library_paths
    if 'plex' not in config['apps']:
        raise ValueError('Media permission repair requires selected Plex')
    checks = storage_assertions(config)
    roots = []
    for library in library_paths(config):
        for path in library['host_paths']:
            secondary = path == config['storage'].get('media_secondary')
            if secondary and config.get('secondary_media_read_only', True):
                continue  # Explicit existing read-only source protection still applies.
            purpose = 'media_secondary' if secondary else 'media'
            check = checks.get(purpose)
            anchor = config['storage'][purpose]
            if (not check or not check.get('sentinel') or '/' in check['sentinel']
                    or Path(path) != Path(anchor) and Path(anchor) not in Path(path).parents):
                raise ValueError('Media repair requires exact configured storage assertions')
            root = {'path': path, 'anchor': anchor, 'sentinel': check['sentinel'],
                    'expected': {k: check[v] for k, v in
                                 (('target', 'mountpoint'), ('source', 'source'), ('fstype', 'fstype'))}}
            if root not in roots:
                roots.append(root)
    if not roots:
        raise ValueError('No writable host media sources are authorized for repair')
    return {'roots': roots, 'uid': config['service_user']['uid'], 'gid': config['service_user']['gid']}


def mount_id(fd):
    fields = dict(line.split(':', 1) for line in Path('/proc/self/fdinfo/{}'.format(fd)).read_text().splitlines() if ':' in line)
    return fields['mnt_id'].strip()


def checked_directory(path, expected):
    from .directories import open_anchor, observed_mount
    fd, missing = open_anchor(path)
    try:
        if missing or observed_mount(fd) != expected:
            raise ValueError('Media repair source is absent or changed')
        return fd
    except BaseException:
        os.close(fd)
        raise


def needed_bits(info, uid, gid):
    """Use the POSIX access class that applies to the service identity."""
    required = 5 if stat.S_ISDIR(info.st_mode) else 4
    shift = 6 if info.st_uid == uid else 3 if info.st_gid == gid else 0
    return required, shift, ((info.st_mode >> shift) & required) == required


def service_access(fd, info, uid, gid, parent=None, name=None):
    """Verify as a permanently dropped real identity in a short-lived child.

    Older libc/Python combinations emulate effective-ID faccessat flags; avoid
    relying on that emulation with a root real UID. The supervisor never switches
    credentials. Verifier children remain in the bounded worker's process group.
    """
    if os.geteuid() != 0:
        return needed_bits(info, uid, gid)[2]
    reader, writer = os.pipe()
    try:
        pid = os.fork()
    except BaseException:
        os.close(reader); os.close(writer)
        raise
    if pid == 0:
        os.close(reader)
        try:
            os.setgroups([]); os.setgid(gid); os.setuid(uid)
            readable = (os.access('.', os.R_OK | os.X_OK, dir_fd=fd)
                        if stat.S_ISDIR(info.st_mode) else os.access(name, os.R_OK, dir_fd=parent))
            os.write(writer, b'1' if readable else b'0')
            os._exit(0)
        except BaseException:
            os._exit(1)
    os.close(writer)
    try:
        answer = os.read(reader, 1)
        _, status = os.waitpid(pid, 0)
        return answer == b'1' and status == 0
    finally:
        os.close(reader)


def repair_batch(spec, cursor=None, limit=BATCH_ENTRIES, seconds=BATCH_SECONDS):
    """Descriptor-relative traversal; output contains counts and a private cursor."""
    from .directories import observed_mount
    uid, gid = spec['uid'], spec['gid']
    if any(type(x) is not int or x <= 0 for x in (uid, gid)):
        raise ValueError('Non-root media identity required')
    roots = spec['roots']
    cursor = cursor or {'root': 0, 'stack': [{'parts': [], 'offset': 0}]}
    # A cursor is private but still validated before constructing any path.
    if (not isinstance(cursor, dict) or set(cursor) != {'root', 'stack'}
            or type(cursor['root']) is not int or not 0 <= cursor['root'] < len(roots)
            or not isinstance(cursor['stack'], list) or not 1 <= len(cursor['stack']) <= MAX_DEPTH):
        raise ValueError('Invalid media repair progress')
    for frame in cursor['stack']:
        if (set(frame) != {'parts', 'offset'} or not isinstance(frame['parts'], list)
                or len(frame['parts']) > MAX_DEPTH or type(frame['offset']) is not int or frame['offset'] < 0
                or any(not isinstance(p, str) or p in ('', '.', '..') or '/' in p or '\0' in p for p in frame['parts'])):
            raise ValueError('Invalid media repair progress')
    counts = dict(checked=0, changed=0, denied=0, skipped=0)
    until = time.monotonic() + seconds
    while cursor['root'] < len(roots):
        root = roots[cursor['root']]
        anchor = checked_directory(root['anchor'], root['expected'])
        root_fd = None
        try:
            marker = os.open(root['sentinel'], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=anchor)
            try:
                if not stat.S_ISREG(os.fstat(marker).st_mode) or b'\n' not in os.read(marker, 4096):
                    raise ValueError('Media health marker unavailable')
            finally:
                os.close(marker)
            root_fd = checked_directory(root['path'], root['expected'])
            expected_id = mount_id(root_fd)
            def repair(fd, parent=None, name=None, parts=()):
                info = os.fstat(fd)
                if (mount_id(fd) != expected_id or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
                        or stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
                    counts['skipped'] += 1
                    return False
                required, _, _ = needed_bits(info, uid, gid)
                counts['checked'] += 1
                if service_access(fd, info, uid, gid, parent, name):
                    return True
                # Recheck the live mount and root pathname immediately before a
                # mutation; an absent mount must never become a local repair tree.
                live = checked_directory(root['path'], root['expected'])
                try:
                    if ((os.fstat(live).st_dev, os.fstat(live).st_ino) !=
                            (os.fstat(root_fd).st_dev, os.fstat(root_fd).st_ino)
                            or observed_mount(fd) != root['expected']):
                        raise ValueError('Media repair anchor changed')
                    if parent is not None:
                        current_parent = checked_directory(str(Path(root['path']).joinpath(*parts)), root['expected'])
                        try:
                            a, b = os.fstat(current_parent), os.fstat(parent)
                            if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
                                raise ValueError('Media parent moved during repair')
                        finally:
                            os.close(current_parent)
                        entry = os.stat(name, dir_fd=parent, follow_symlinks=False)
                        if (entry.st_dev, entry.st_ino) != (info.st_dev, info.st_ino):
                            raise ValueError('Media entry changed during repair')
                    if info.st_uid == uid:
                        mode = stat.S_IMODE(info.st_mode) | (required << 6)
                    else:
                        if info.st_gid != gid:
                            os.fchown(fd, -1, gid)  # Preserve owner UID; never chown to root.
                        mode = stat.S_IMODE(os.fstat(fd).st_mode) | (required << 3)
                    os.fchmod(fd, mode)
                    if not service_access(fd, os.fstat(fd), uid, gid, parent, name):
                        raise PermissionError('Media mode readback differs')
                    counts['changed'] += 1
                except PermissionError:
                    counts['denied'] += 1
                    return False
                finally:
                    os.close(live)
                return True
            if cursor['stack'] == [{'parts': [], 'offset': 0}]:
                repair(root_fd)
            while cursor['stack']:
                if counts['checked'] + counts['skipped'] >= limit or time.monotonic() >= until:
                    return {'complete': False, 'cursor': cursor, **counts}
                frame = cursor['stack'][-1]
                fd = os.dup(root_fd)
                try:
                    for part in frame['parts']:
                        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                        os.close(fd); fd = child
                        if mount_id(fd) != expected_id:
                            raise ValueError('Nested mount skipped')
                    child_frame = None
                    with os.scandir(fd) as entries:
                        for index, entry in enumerate(entries):
                            if index < frame['offset']:
                                continue
                            if counts['checked'] + counts['skipped'] >= limit or time.monotonic() >= until:
                                return {'complete': False, 'cursor': cursor, **counts}
                            frame['offset'] = index + 1
                            info = entry.stat(follow_symlinks=False)
                            if (entry.name == root['sentinel'] or entry.name.startswith('.@')
                                    or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))):
                                counts['skipped'] += 1; continue
                            flags = os.O_PATH | os.O_NOFOLLOW
                            if stat.S_ISDIR(info.st_mode):
                                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                            try:
                                item = os.open(entry.name, flags, dir_fd=fd)
                                try:
                                    held = os.fstat(item)
                                    if (held.st_dev, held.st_ino) != (info.st_dev, info.st_ino):
                                        counts['skipped'] += 1; continue
                                    if stat.S_ISREG(held.st_mode):
                                        # Reopen the pinned regular inode, not a
                                        # pathname that might become a device/FIFO.
                                        opened = os.open('/proc/self/fd/' + str(item), os.O_RDONLY | os.O_NONBLOCK)
                                        os.close(item); item = opened
                                    valid = repair(item, fd, entry.name, frame['parts'])
                                    if valid and stat.S_ISDIR(held.st_mode):
                                        if len(cursor['stack']) >= MAX_DEPTH:
                                            counts['denied'] += 1
                                        else:
                                            child_frame = {'parts': frame['parts'] + [entry.name], 'offset': 0}
                                finally:
                                    os.close(item)
                            except OSError:
                                counts['denied'] += 1
                            if child_frame:
                                break
                    if child_frame:
                        cursor['stack'].append(child_frame)
                    else:
                        cursor['stack'].pop()
                except (FileNotFoundError, NotADirectoryError, PermissionError):
                    counts['denied'] += 1
                    cursor['stack'].pop()
                finally:
                    os.close(fd)
            cursor['root'] += 1
            cursor['stack'] = [{'parts': [], 'offset': 0}]
        finally:
            if root_fd is not None:
                os.close(root_fd)
            os.close(anchor)
    return {'complete': True, 'cursor': None, **counts}


def set_policy(name, enabled=None):
    """Explicit opt-in for an existing immutable deployment, without reconfiguring apps."""
    from .lifecycle import SERVICE_ROOT, root_json
    from .runtime import encode, replace_owned
    from .compose import private_artifact
    from .accounts import provisioning_gate
    provisioning_gate()
    from .lifecycle import service_status
    service_status(name)  # Validate the deployment name before path construction.
    directory = SERVICE_ROOT / name
    definition = root_json(directory / 'definition.json')
    if definition.get('deployment_mode') != 'reference':
        raise ValueError('Enable media repair only on a published reference deployment')
    repair_spec(definition['config'])
    path = directory / 'media-permissions.json'
    if enabled is not None:
        policy = {'schema_version': 1, 'enabled': enabled, 'interval_seconds': INTERVAL}
        data = encode(policy)
        if os.path.lexists(str(path)):
            import hashlib
            root_json(path)
            replace_owned(path, data, 0o600, (hashlib.sha256(path.read_bytes()).hexdigest(),))
        else:
            private_artifact(path, data, 0o600)
    policy = root_json(path) if os.path.lexists(str(path)) else {'enabled': False}
    return {'enabled': policy.get('enabled') is True, 'interval_seconds': INTERVAL,
            'runtime_supports_repair': (Path(definition['launcher']).parent / 'installarr/media_permissions.py').is_file(),
            'first_pass': 'after healthy storage and running containers',
            'policy_file': str(path), 'note': 'Requires a supervisor runtime containing media permission repair.'}


class MediaPermissions:
    """One asynchronous tracked worker; health supervision never waits for a walk."""
    def __init__(self, config, directory, clock=time.monotonic):
        self.config, self.directory, self.clock = config, Path(directory), clock
        self.thread = None
        self.process = None
        self.result = None
        self.cancelled = threading.Event()
        self.next_due = 0
        self.cursor = None
        self.status = {'enabled': False}

    def _run(self):
        from .storage_process import WorkerSlot
        try:
            from .execution import private_directory
            progress = private_directory(self.directory / 'media-permissions')
            # Isolated Python imports only this trusted supervisor snapshot.
            code = ('import sys,json;sys.path.insert(0,' + repr(str(Path(__file__).parent.parent)) + ');'
                    'from installarr.media_permissions import repair_batch;'
                    's=json.load(sys.stdin);print(json.dumps(repair_batch(s["spec"],s["cursor"])))')
            with WorkerSlot(progress, 'media-permissions') as slot:
                if self.cancelled.is_set():
                    self.result = {'error': 'cancelled'}; return
                process = slot.spawn([sys.executable, '-I', '-c', code], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.process = process
                # Worker cannot mutate before WorkerSlot durably records its PID.
                if self.cancelled.is_set():
                    slot.abort(); self.result = {'error': 'cancelled'}; return
                output, _ = process.communicate(json.dumps({'spec': repair_spec(self.config), 'cursor': self.cursor}).encode(),
                                                timeout=WORKER_TIMEOUT)
                slot.finish()
                self.result = json.loads(output) if process.returncode == 0 else {'error': 'storage_or_permission_error'}
        except Exception:
            self.result = {'error': 'worker_failed_or_unreaped'}
        finally:
            self.process = None

    def tick(self):
        from .lifecycle import root_json
        path = self.directory / 'media-permissions.json'
        try:
            enabled = (os.path.lexists(str(path)) and root_json(path) ==
                       {'schema_version': 1, 'enabled': True, 'interval_seconds': INTERVAL})
        except (ValueError, OSError):
            enabled = False
        if not enabled:
            self.cancel(); self.status = {'enabled': False}; return self.status
        self.status['enabled'] = True
        if self.thread is not None:
            if self.thread.is_alive():
                return dict(self.status, running=True)
            self.thread = None
            result, self.result = self.result or {'error': 'worker_failed'}, None
            self.cursor = result.get('cursor')
            self.status = {'enabled': True, 'running': False, 'checked_at': time.time(),
                           **{k: result[k] for k in ('complete', 'checked', 'changed', 'denied', 'skipped', 'error') if k in result}}
            self.next_due = self.clock() + (0 if result.get('complete') is False else INTERVAL)
        if self.clock() >= self.next_due:
            self.cancelled.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            self.status['running'] = True
        return dict(self.status, interval_seconds=INTERVAL)

    def cancel(self):
        self.cancelled.set()
        process = self.process
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
