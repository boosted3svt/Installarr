"""Explicit, recoverable updates of stopped reference supervisors.

This changes only immutable Python runtime/health definitions, never images,
Compose, credentials, application databases or service enablement.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

from .accounts import provisioning_gate
from .execution import Execution
from .lifecycle import (SERVICE_ROOT, ENV, command, health_spec, local_mount,
                        root_json, snapshot_runtime, verify_bundle)

UNIT_ROOT = Path('/etc/systemd/system')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def read_owned(path, mode):
    path = Path(path)
    if path.resolve() != path:
        raise ValueError('Managed runtime path contains a symlink')
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != mode or info.st_size > 1024 * 1024):
            raise ValueError('Unsafe managed runtime artifact')
        return handle.read()


def replace_owned(path, data, mode, accepted):
    if hashlib.sha256(read_owned(path, mode)).hexdigest() not in accepted:
        raise ValueError('Managed runtime artifact changed; preserved')
    fd, temporary = tempfile.mkstemp(prefix='.runtime-', dir=str(path.parent))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, str(path))
        parent = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def stopped(name):
    result = subprocess.run(['systemctl', 'show', 'installarr-' + name + '.service',
                             '--property=ActiveState', '--value'], capture_output=True,
                            text=True, timeout=10, env=ENV, check=False)
    if result.returncode or result.stdout.strip() not in ('inactive', 'failed'):
        raise ValueError('Stop both reference units before refreshing their runtime')


def targets(name):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,25}', name):
        raise ValueError('Invalid reference deployment name')
    return [name, name + '-boot']


def paths(name):
    directory = SERVICE_ROOT / name
    return [(directory / 'definition.json', 0o600),
            (UNIT_ROOT / ('installarr-' + name + '.service'), 0o644),
            (directory / 'state.json', 0o600),
            (directory / 'runtime/state.json', 0o600)]


def source_digest(source, reader):
    files = [*source.glob('*.py'), *[p for p in (source / 'data').rglob('*') if p.is_file()]]
    content = {str(p.relative_to(source)): reader(p) for p in sorted(files)}
    return hashlib.sha256(b''.join(key.encode() + b'\0' + value for key, value in content.items())).hexdigest()


def audit_runtime(name):
    current = source_digest(Path(__file__).parent, lambda p: p.read_bytes())
    rows = []
    for target in targets(name):
        definition = root_json(SERVICE_ROOT / target / 'definition.json')
        launcher = Path(definition['launcher'])
        # Reuse exactly the snapshot content ordering, without creating a snapshot.
        source = launcher.parent / 'installarr'
        digest = source_digest(source, lambda p: read_owned(p, 0o644))
        read_owned(launcher, 0o644)
        rows.append({'name': target, 'snapshot': launcher.parent.name,
                     'integrity': digest == launcher.parent.name, 'matches_checkout': digest == current})
    return {'current_code_sha256': current, 'services': rows, 'automatic_updates': False}


def _recover(state, name):
    journal = state.state['runtime_refresh']
    expected = [str(path) for target in targets(name) for path, mode in paths(target)]
    rows = journal['files']
    if [row['path'] for row in rows] != expected:
        raise ValueError('Runtime recovery journal does not match managed paths')
    # Validate the entire transaction before restoring any bytes. Unknown edits
    # must never be overwritten by a partial rollback.
    for row in rows:
        data = read_owned(Path(row['path']), row['mode'])
        if hashlib.sha256(data).hexdigest() not in (row['old_hash'], row['new_hash']):
            raise ValueError('Runtime recovery found an operator edit; preserved')
        old = base64.b64decode(row['old'], validate=True)
        if hashlib.sha256(old).hexdigest() != row['old_hash']:
            raise ValueError('Runtime backup integrity differs')
    for row in rows:
        replace_owned(Path(row['path']), base64.b64decode(row['old']), row['mode'],
                      (row['old_hash'], row['new_hash']))
    command(['systemctl', 'daemon-reload'])
    state.state.update(journal['apply_evidence'])
    del state.state['runtime_refresh']
    state._save()


def refresh_runtime(name, state_directory):
    provisioning_gate()
    names = targets(name)
    # An interrupted refresh is recovered before interpreting a possibly newer
    # definition. The config itself is immutable throughout this transaction.
    config = root_json(SERVICE_ROOT / name / 'definition.json')['config']
    with Execution(state_directory, {'operation': 'reference-apply-v1', 'config': config, 'name': name}) as state:
        for target in names:
            stopped(target)
        if 'runtime_refresh' in state.state:
            _recover(state, name)
            return {'status': 'previous_runtime_restored', 'services_started': False,
                    'note': 'Rerun refresh-runtime to make a new attempt.'}
        if state.state.get('phase') != 'reference_poc_ready':
            raise ValueError('Runtime refresh requires a completed reference apply')
        if not all(row['integrity'] for row in audit_runtime(name)['services']):
            raise ValueError('Saved runtime snapshot integrity differs; preserved')
        from .reference import render_reference_bundle
        launcher = snapshot_runtime()
        rows = []
        evidence = {key: state.state[key] for key in ('live_unit', 'bootstrap_unit')}
        for index, target in enumerate(names):
            artifacts = paths(target)
            original = [read_owned(path, mode) for path, mode in artifacts]
            definition = json.loads(original[0])
            expected_config = config if index == 0 else dict(config, project_directory=str(Path(state_directory) / 'bootstrap'))
            mode = 'reference' if index == 0 else 'reference-bootstrap'
            key = 'live_unit' if index == 0 else 'bootstrap_unit'
            if (definition.get('config') != expected_config or definition.get('deployment_mode') != mode
                    or definition.get('name') != target or definition.get('project') != 'installarr-' + target
                    or hashlib.sha256(original[0] + original[1]).hexdigest() != evidence[key]):
                raise ValueError('Saved reference service differs; preserved')
            verify_bundle(expected_config, render_reference_bundle(expected_config, published=index == 0))
            managed = json.loads(original[2])
            runtime = json.loads(original[3])
            for checkpoint, operation in ((managed, 'managed-service-v1'), (runtime, 'supervisor-v1')):
                if checkpoint.get('fingerprint') != fingerprint({'operation': operation, 'definition': definition}):
                    raise ValueError('Service checkpoint differs; preserved')
            old_launcher = definition['launcher'].encode()
            if original[1].count(old_launcher) != 2:
                raise ValueError('Unit runtime paths differ; preserved')
            definition['launcher'] = str(launcher)
            definition['health'] = health_spec(expected_config, local_mount(expected_config['storage']['configs']))
            managed['fingerprint'] = fingerprint({'operation': 'managed-service-v1', 'definition': definition})
            runtime['fingerprint'] = fingerprint({'operation': 'supervisor-v1', 'definition': definition})
            updated = [encode(definition), original[1].replace(old_launcher, str(launcher).encode()), encode(managed), encode(runtime)]
            for (path, permissions), old, new in zip(artifacts, original, updated):
                rows.append({'path': str(path), 'mode': permissions,
                             'old': base64.b64encode(old).decode(),
                             'old_hash': hashlib.sha256(old).hexdigest(),
                             'new_hash': hashlib.sha256(new).hexdigest(), 'new': new})
        # Keep a durable private backup of every original byte even after success.
        backup = Path(state_directory) / ('runtime-backup-' + os.urandom(8).hex() + '.json')
        from .compose import private_artifact
        journal = {'files': [{k: v for k, v in row.items() if k != 'new'} for row in rows],
                   'apply_evidence': evidence}
        private_artifact(backup, encode(journal), 0o600)
        state.state['runtime_refresh'] = journal
        state._save()
        try:
            for row in rows:
                replace_owned(Path(row['path']), row['new'], row['mode'], (row['old_hash'],))
            command(['systemctl', 'daemon-reload'])
            for index, target in enumerate(names):
                definition_path, unit_path = paths(target)[:2]
                state.state['live_unit' if index == 0 else 'bootstrap_unit'] = hashlib.sha256(
                    read_owned(definition_path[0], 0o600) + read_owned(unit_path[0], 0o644)).hexdigest()
            del state.state['runtime_refresh']
            state._save()
        except BaseException:
            state.state['runtime_refresh'] = journal
            _recover(state, name)
            raise
        return {'status': 'runtime_refreshed', 'runtime': str(launcher), 'backup': str(backup),
                'services_started': False, 'boot_settings_changed': False,
                'note': 'Start the live unit explicitly, then rerun apply for application acceptance.'}
