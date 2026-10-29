"""Private provider credentials, separate from plans and execution checkpoints."""
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from .credentials import MAX_BYTES, validate_credentials, validate_secret_filename, credential_execution
from .atomic import publish_noreplace
from .execution import private_directory

PROVIDERS = ('newshosting', 'nzbgeek', 'opensubtitlescom')


def validate_provider_secrets(value):
    if not isinstance(value, dict) or not value or set(value) - set(PROVIDERS):
        raise ValueError('Choose supported provider credential records')
    for name, credentials in value.items():
        if name == 'nzbgeek':
            if (not isinstance(credentials, dict) or set(credentials) != {'api_key'}
                    or not isinstance(credentials['api_key'], str)
                    or not re.fullmatch(r'[A-Za-z0-9]{16,128}', credentials['api_key'])):
                raise ValueError('Invalid NZBGeek API credential')
        else:
            validate_credentials(credentials)
    return value


def read_provider_secrets(path):
    path = Path(path).absolute()
    if path.resolve() != path:
        raise ValueError('Provider credential path contains a symlink')
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > MAX_BYTES):
            raise ValueError('Provider credential file must be private and owned by executor')
        return validate_provider_secrets(json.loads(handle.read(MAX_BYTES + 1)))


def initialize_provider_secrets(directory, names, collect, filename="providers.json"):
    if not isinstance(names, list) or not names or len(set(names)) != len(names) or set(names) - set(PROVIDERS):
        raise ValueError('Select unique supported providers')
    validate_secret_filename(filename)
    operation = {'operation': 'provider-credentials-v1', 'providers': sorted(names)}
    if filename != 'providers.json':
        operation['filename'] = filename
    directory = private_directory(directory)
    target = directory / filename
    if os.path.lexists(str(target)):
        existing = read_provider_secrets(target)
        if set(existing) != set(names):
            raise ValueError('Existing provider credential selection differs; preserved')
        return {'status': 'reused', 'path': str(target), 'providers': sorted(names)}
    with credential_execution(directory, 'provider', filename, operation) as execution:
        execution._save()  # Selection metadata only; never credential values.
        if os.path.lexists(str(target)):
            existing = read_provider_secrets(target)
            if set(existing) != set(names):
                raise ValueError('Existing provider credential selection differs; preserved')
            return {'status': 'reused', 'path': str(target), 'providers': sorted(names)}
        values = validate_provider_secrets({name: collect(name) for name in names})
        fd, temporary = tempfile.mkstemp(prefix='.provider-', dir=str(directory))
        try:
            with os.fdopen(fd, 'w') as handle:
                json.dump(values, handle)
                handle.write('\n')
                handle.flush()
                os.fsync(handle.fileno())
            publish_noreplace(temporary, target)
            descriptor = os.open(str(directory), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            read_provider_secrets(target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {'status': 'created', 'path': str(target), 'providers': sorted(names)}
