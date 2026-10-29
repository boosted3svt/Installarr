"""Private mount.cifs credentials; no mount attempt or Samba server setup."""
import os
from pathlib import Path
import tempfile

from .accounts import HostPrerequisiteError
from .atomic import publish_noreplace
from .credentials import validate_credentials, validate_secret_filename, credential_execution
from .execution import Execution
from .mounts import protected_smb_file


def validate_smb_secrets(value):
    if not isinstance(value, dict) or set(value) not in ({'username', 'password'}, {'username', 'password', 'domain'}):
        raise ValueError('SMB credentials require username/password and optional domain')
    validate_credentials({key: value[key] for key in ('username', 'password')})
    if 'domain' in value:
        domain = value['domain']
        if (not isinstance(domain, str) or not domain or domain != domain.strip() or len(domain) > 255
                or any(ord(c) < 32 or ord(c) == 127 for c in domain)):
            raise ValueError('Invalid SMB domain')
    if any(item.splitlines() != [item] for item in value.values()):
        raise ValueError('SMB credential values cannot contain line separators')
    return value


def read_smb_input(path):
    # Reuse the exact private regular-file/owner/mode/link checks, accepting the
    # optional SMB domain separately from shared GUI credential validation.
    from .credentials import read_private_json
    return validate_smb_secrets(read_private_json(path))


def initialize_smb_secrets(directory, collect, filename='smb.credentials'):
    if os.geteuid() != 0:
        raise HostPrerequisiteError('SMB credential collection requires root')
    validate_secret_filename(filename)
    if ',' in filename:
        raise ValueError('SMB credential filename cannot contain a mount-option separator')
    target = Path(directory).absolute() / filename
    if os.path.lexists(str(target)):
        protected_smb_file(target)
        return {'status': 'reused', 'credentials_file': str(target)}
    with credential_execution(directory, 'smb', filename, {'operation': 'smb-credentials-v1'}) as state:
        if os.path.lexists(str(target)):
            protected_smb_file(target)
            return {'status': 'reused', 'credentials_file': str(target)}
        values = validate_smb_secrets(collect())
        content = ''.join(key + '=' + values[key] + '\n' for key in ('username', 'password', 'domain') if key in values)
        fd, temporary = tempfile.mkstemp(prefix='.smb-', dir=str(target.parent))
        try:
            with os.fdopen(fd, 'w') as output:
                output.write(content); output.flush(); os.fsync(output.fileno())
            publish_noreplace(temporary, target)
            directory_fd = os.open(str(target.parent), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            protected_smb_file(target)
            state.state.setdefault('files', {})[filename] = 'stored'
            state._save()
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {'status': 'created', 'credentials_file': str(target)}
