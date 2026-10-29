"""Private shared GUI credentials, kept out of configuration and checkpoints."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from .atomic import publish_noreplace
from .execution import Execution, private_directory

MAX_BYTES = 65536


def validate_secret_filename(filename):
    if (not isinstance(filename, str) or not filename or Path(filename).name != filename
            or filename in ('.', '..', 'lock', 'state.json', '.credential-state') or len(os.fsencode(filename)) > 255
            or any(ord(c) < 32 or ord(c) == 127 for c in filename)):
        raise ValueError('Secret output filename must be a nonreserved basename')
    return filename


def credential_execution(directory, kind, filename, operation):
    """Independent private locks/checkpoints for credential files sharing a folder.

    Existing secret values stay at their original paths; legacy metadata is never
    rewritten. Distinct collectors/output names cannot overwrite each other's state.
    """
    validate_secret_filename(filename)
    if kind not in ('gui', 'provider', 'plex', 'smb'):
        raise ValueError('Unknown credential state namespace')
    directory = private_directory(directory)
    metadata = private_directory(directory / '.credential-state')
    namespace = kind + '-' + hashlib.sha256(filename.encode()).hexdigest()[:16]
    return Execution(metadata / namespace, operation)


def validate_credentials(value):
    if not isinstance(value, dict) or set(value) != {"username", "password"}:
        raise ValueError("Expected shared GUI username and password")
    for key in ("username", "password"):
        item = value[key]
        if not isinstance(item, str) or not item or len(item) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in item):
            raise ValueError("Invalid GUI credential")
    if value["username"] != value["username"].strip():
        raise ValueError("Invalid GUI username")
    return value


def validate_selected_gui_credentials(config, value):
    validate_credentials(value)
    if set(config.get('apps', [])) & {'sabnzbd', 'bazarr', 'netbootxyz'} and ':' in value['username']:
        from .accounts import HostPrerequisiteError
        raise HostPrerequisiteError('Selected Basic-auth applications require a GUI username without a colon')
    return value


def read_private_json(path):
    path = Path(path).absolute()
    if path.resolve() != path:
        raise ValueError("Credential path contains a symlink")
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
                or info.st_size > MAX_BYTES):
            raise ValueError("Credential file must be private and owned by executor")
        return json.loads(handle.read(MAX_BYTES + 1))


def read_private_credentials(path):
    return validate_credentials(read_private_json(path))


def initialize_credentials(directory, collect):
    directory = private_directory(directory)
    target = directory / "gui-admin.json"
    if os.path.lexists(str(target)):
        read_private_credentials(target)
        return {"status": "reused", "note": "Existing shared GUI credentials retained."}
    with credential_execution(directory, 'gui', target.name, {"operation": "gui-credentials-v1"}) as execution:
        if os.path.lexists(str(target)):
            read_private_credentials(target)
            return {"status": "reused", "note": "Existing shared GUI credentials retained."}
        credentials = validate_credentials(collect())
        fd, temporary = tempfile.mkstemp(prefix=".credentials-", dir=str(directory))
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(credentials, handle)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            # Publish a complete file without replacing even a dangling symlink.
            publish_noreplace(temporary, target)
            directory_fd = os.open(str(directory), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            read_private_credentials(target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {"status": "created", "note": "Shared GUI credentials stored privately; no applications configured yet."}
