"""Private, locked checkpoints for idempotent host reconciliation.

Checkpoints are evidence of an attempt, never a reason to skip inspecting the host.
Only nonsecret operation names and statuses belong here.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile


def private_directory(directory):
    """Create/verify an executor-private directory beneath trusted ancestors."""
    directory = Path(directory).absolute()
    if directory.resolve() != directory:
        raise ValueError("State directory must not contain symlinks")
    for parent in directory.parents:
        info = parent.stat()
        if info.st_uid not in (0, os.geteuid()) or (
            info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX)
        ):
            raise ValueError("State ancestors must be trusted")
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700 or directory.resolve() != directory):
        raise ValueError("State directory must be owned by executor and mode 0700")
    return directory


class Execution:
    def __init__(self, directory, configuration):
        self.directory = Path(directory).absolute()
        self.fingerprint = hashlib.sha256(json.dumps(
            configuration, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        self.lock = None

    def __enter__(self):
        private_directory(self.directory)
        fd = os.open(str(self.directory / "lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        self.lock = os.fdopen(fd, "r+")
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
                raise ValueError("Unsafe state lock")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.state = {"schema_version": 1, "fingerprint": self.fingerprint, "steps": {}}
            try:
                saved_fd = os.open(str(self.directory / "state.json"), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except FileNotFoundError:
                saved_fd = None
            if saved_fd is not None:
                with os.fdopen(saved_fd) as handle:
                    info = os.fstat(handle.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
                        raise ValueError("Unsafe checkpoint")
                    self.state = json.load(handle)
                if (not isinstance(self.state, dict) or self.state.get("schema_version") != 1
                        or self.state.get("fingerprint") != self.fingerprint
                        or not isinstance(self.state.get("steps"), dict)):
                    raise ValueError("Checkpoint does not match this operation")
            return self
        except BaseException:
            self.lock.close()
            self.lock = None
            raise

    def _save(self):
        fd, name = tempfile.mkstemp(prefix=".checkpoint-", dir=str(self.directory))
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(self.state, handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, str(self.directory / "state.json"))
            directory_fd = os.open(str(self.directory), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def reconcile(self, name, action):
        self.state["steps"][name] = "running"
        self._save()
        try:
            action()
        except BaseException:
            self.state["steps"][name] = "failed"
            self._save()
            raise
        self.state["steps"][name] = "verified"
        self._save()

    def __exit__(self, *args):
        self.lock.close()
