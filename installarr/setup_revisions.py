"""Explicit fresh-install revisions; old databases and immutable state stay intact."""
import json
import hashlib
import os
from pathlib import Path
import stat
import uuid
from .credentials import read_private_json
from .execution import Execution, private_directory
from .compose import private_artifact


def archive_local_netboot(config, old, directory):
    """Preserve only the prior owned local assets child before its parent is NFS."""
    from .hostplan import storage_assertions, preparation_plan
    from .anchors import open_anchors
    from .atomic import publish_noreplace
    path = old['storage'].get('netboot_assets')
    if not path or old.get('storage_mounts', {}).get('netboot_assets', {}).get('kind') != 'local':
        return
    desired = next((r for r in preparation_plan(config)['mounts']
                    if Path(r['mountpoint']) == Path(path).parent and r['kind'] in ('nfs', 'smb')), None)
    if desired is None:
        return
    check = storage_assertions(old).get('netboot_assets')
    if not check:
        raise ValueError('Prior local netboot filesystem is not asserted; preserved')
    parent, missing, observed = open_anchors([{'path': str(Path(path).parent)}])[0]
    try:
        if missing or observed['fstype'] in ('nfs', 'nfs4', 'cifs'):
            return
        if observed != {key: check[field] for key, field in (('target','mountpoint'),('source','source'),('fstype','fstype'))}:
            raise ValueError('Prior local netboot filesystem changed; preserved')
        contents = os.listdir(parent)
        if not contents:
            return
        leaf = Path(path).name
        if contents != [leaf] or not stat.S_ISDIR(os.stat(leaf, dir_fd=parent, follow_symlinks=False).st_mode):
            raise ValueError('Nonempty mountpoint contains unrelated files; preserved')
        archive = private_directory(Path(directory) / 'retired-local-assets')
        publish_noreplace(leaf, archive / leaf, source_dir_fd=parent)
        os.fsync(parent)
        fd = os.open(str(archive), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def selected_setup(root):
    root = Path(root)
    pointer = root / 'active-setup.json'
    if not os.path.lexists(str(pointer)):
        return root
    value = read_private_json(pointer)
    if not isinstance(value, dict) or set(value) != {'directory'} or not isinstance(value['directory'], str):
        raise ValueError('Invalid saved installation selection')
    selected = Path(value['directory'])
    if selected.parent != root / 'installations' or selected.resolve() != selected:
        raise ValueError('Saved installation selection is outside its private root')
    private_directory(selected)
    return selected


def new_setup(root, previous, name, config):
    parent = private_directory(Path(root) / 'installations')
    identifier = uuid.uuid4().hex[:12]
    directory = private_directory(parent / ('setup-' + identifier))
    metadata = {'name': 'family-' + identifier, 'previous': {
        'config_file': str(Path(previous) / 'settings.json'), 'name': name,
        'state': str(Path(previous) / 'state'), 'login': str(Path(previous) / 'login/gui-admin.json'),
        'providers': config.get('provider_secrets_file'), 'family': config.get('ombi_family_preferences_file')}}
    private_artifact(directory / 'installation.json', (json.dumps(metadata) + '\n').encode(), 0o600)
    return directory


def activate_setup(root, directory):
    root = Path(root)
    if Path(directory).parent != root / 'installations':
        return
    with Execution(root / '.selection', {'operation': 'setup-selection-v1'}):
        target = root / 'active-setup.json'
        if os.path.lexists(str(target)):
            read_private_json(target)
        temporary = root / ('selection-' + uuid.uuid4().hex + '.json')
        private_artifact(temporary, (json.dumps({'directory': str(directory)}) + '\n').encode(), 0o600)
        os.replace(str(temporary), str(target))
        fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def prepare_switch(config, directory, previous, fstab_path=Path('/etc/fstab')):
    """Only retire the verified prior owned setup and its conflicting managed mounts.

    This runs after the normal explicit Start installation confirmation. It never
    deletes an app database or media folder, and never replaces an unrelated mount.
    """
    from .cli import validate
    from .accounts import provisioning_gate
    from .reference import existing_service, reference_controller, remove_owned
    from .lifecycle import command, SERVICE_ROOT
    from .hostplan import preparation_plan
    from .mounts import runtime_mounts, parse_fstab
    from .storage_process import run_storage
    provisioning_gate()
    old = validate(read_private_json(Path(previous['config_file'])))
    validate(config)
    directory = Path(directory)
    with Execution(directory / 'switch-state', {'operation': 'fresh-install-switch-v1',
                                               'previous': previous, 'config': config}) as switch:
        if switch.state.get('complete'):
            return
        old_mounts = {row['mountpoint']: row for row in preparation_plan(old)['mounts']}
        plans = preparation_plan(config)['mounts']
        runtime = runtime_mounts()
        conflicts = []
        for mount in plans:
            for actual in (row for row in runtime if row['target'] == mount['mountpoint']):
                if (actual['source'], actual['fstype']) == (mount['source'], mount['fstype']):
                    continue
                owned = old_mounts.get(mount['mountpoint'])
                if (not owned or owned['kind'] not in ('nfs', 'smb')
                        or (actual['source'], actual['fstype']) != (owned['source'], owned['fstype'])):
                    raise ValueError('Conflicting mount is not the prior managed setup; preserved')
                conflicts.append(owned)
        fstab = Path(fstab_path)
        info = fstab.lstat()
        if (fstab.resolve() != fstab or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != 0 or info.st_mode & 0o022):
            raise ValueError('Unsafe persistence file preserved')
        before = fstab.read_bytes()
        replacements = {row['mountpoint']: row for row in plans}
        remove = set()
        for row in parse_fstab(before.decode()):
            desired = replacements.get(row['target'])
            if desired is None or (row['source'], row['fstype']) == (desired['source'], desired['fstype']):
                continue
            owned = old_mounts.get(row['target'])
            if (not owned or owned['kind'] not in ('nfs', 'smb')
                    or (row['source'], row['fstype']) != (owned['source'], owned['fstype'])):
                raise ValueError('Conflicting fstab entry is unrelated to prior managed setup; preserved')
            remove.add(row['target'])
        backup = directory / 'before-switch.fstab'
        if not os.path.lexists(str(backup)):
            private_artifact(backup, before, 0o600)
        from .runtime import read_owned
        digest = hashlib.sha256(read_owned(backup, 0o600)).hexdigest()
        if switch.state.get('fstab_backup_sha256', digest) != digest:
            raise ValueError('Persistence backup changed; switch stopped')
        switch.state['fstab_backup_sha256'] = digest
        switch._save()
        with Execution(Path(previous['state']), {'operation': 'reference-apply-v1', 'config': old,
                                                  'name': previous['name']}) as state:
            if (conflicts or remove) and state.state.get('steps', {}).get('mounts') != 'verified':
                raise ValueError('Prior mount preparation is not verified; conflicting mounts preserved')
            needs_archive = (old.get('storage_mounts', {}).get('netboot_assets', {}).get('kind') == 'local'
                             and any(Path(row['mountpoint']) == Path(old['storage']['netboot_assets']).parent
                                     for row in plans if row['kind'] in ('nfs', 'smb')))
            if needs_archive and state.state.get('steps', {}).get('directories') != 'verified':
                raise ValueError('Prior netboot directories are not verified; preserved')
            for bootstrap in (False, True):
                candidate = dict(old, project_directory=str(Path(previous['state']) / 'bootstrap')) if bootstrap else old
                name = previous['name'] + ('-boot' if bootstrap else '')
                unit = existing_service(candidate, name, state, bootstrap)
                if unit is None:
                    continue
                controller = reference_controller(candidate, 'installarr-' + name, published=not bootstrap)
                rows = controller.inventory()
                controller.audit(rows)
                evidence = directory / ('previous-' + name)
                private_directory(evidence)
                for source in (SERVICE_ROOT / name / 'definition.json', Path('/etc/systemd/system') / unit):
                    target = evidence / source.name
                    private_artifact(target, source.read_bytes(), 0o600)
                command(['systemctl', 'stop', unit])
                command(['systemctl', 'disable', unit])
                remove_owned(controller)
        archive_local_netboot(config, old, directory)
        for owned in conflicts:
            actual = [r for r in runtime_mounts() if r['target'] == owned['mountpoint']]
            if not actual:
                continue
            if len(actual) != 1 or (actual[0]['source'], actual[0]['fstype']) != (owned['source'], owned['fstype']):
                raise ValueError('Mount changed during switch; preserved')
            if run_storage(['umount', '--', owned['mountpoint']], timeout=20, operation='mount-switch').returncode:
                raise ValueError('Prior managed mount is busy; switch stopped without a lazy unmount')
        if remove:
            lines = before.decode().splitlines(keepends=True)
            kept = []
            for line in lines:
                rows = parse_fstab(line)
                if not rows or rows[0]['target'] not in remove:
                    kept.append(line)
            current = fstab.lstat()
            identity = lambda value: (value.st_dev, value.st_ino, value.st_uid, value.st_gid, value.st_mode, value.st_nlink)
            if identity(current) != identity(info) or fstab.read_bytes() != before:
                raise ValueError('Persistence changed during review; preserved')
            temporary = fstab.parent / ('.installarr-switch-' + uuid.uuid4().hex)
            try:
                with temporary.open('xb') as handle:
                    os.fchmod(handle.fileno(), stat.S_IMODE(info.st_mode))
                    handle.write(''.join(kept).encode()); handle.flush(); os.fsync(handle.fileno())
                os.replace(str(temporary), str(fstab))
                fd = os.open(str(fstab.parent), os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            finally:
                if temporary.exists():
                    temporary.unlink()
            command(['systemctl', 'daemon-reload'])
        switch.state['complete'] = True
        switch._save()
