"""Deadline-bound storage subprocesses with durable unreaped-group tracking.

A launcher waits for input until its PID is checkpointed, then execs the worker.
Timeouts never use an unbounded wait. Subsequent calls refuse to spawn while an
old process group remains, including across CLI invocations. No daemon/listener.
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import uuid

from .accounts import HostPrerequisiteError
from .execution import Execution


_unreaped = {}


def reap_local():
    for pid, process in list(_unreaped.items()):
        if process.poll() is not None:
            del _unreaped[pid]


class StorageProcessError(HostPrerequisiteError):
    pass


def registry_path():
    if os.geteuid() == 0:
        return Path('/run/installarr-storage-workers')
    return Path('/var/tmp/installarr-storage-workers-' + str(os.geteuid()))


def start_time(pid):
    try:
        return int(Path('/proc/{}/stat'.format(pid)).read_text().rsplit(')', 1)[1].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def group_alive(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def kill_group(process):
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


class WorkerSlot:
    def __init__(self, registry=None, operation='storage', terminate=None):
        self.execution = Execution(registry or registry_path(), {'operation': 'bounded-storage-workers-v1'})
        self.operation = operation
        self.terminate = terminate or kill_group
        self.process = None
        self.nonce = uuid.uuid4().hex

    def __enter__(self):
        reap_local()
        self.execution.__enter__()
        try:
            pending = self.execution.state.get('pending')
            if pending:
                pid = pending.get('pid')
                if (type(pid) is not int or pid <= 1 or pending.get('pgid') != pid
                        or not re.fullmatch(r'[0-9a-f]{32}', str(pending.get('nonce', '')))):
                    raise StorageProcessError('Unsafe saved storage worker record; preserved')
                # Reap only a matching direct child, without waiting. Never signal
                # a recovered PID/group: it could have been reused by the kernel.
                if start_time(pid) == pending.get('start_time'):
                    try:
                        os.waitpid(pid, os.WNOHANG)
                    except ChildProcessError:
                        pass
                if group_alive(pid):
                    raise StorageProcessError('Previous storage worker has not exited; no new worker started')
                self.execution.state.pop('pending', None)
                self.execution._save()
            return self
        except BaseException:
            self.execution.__exit__(None, None, None)
            raise

    def spawn(self, args, **kwargs):
        self.process = subprocess.Popen(args, start_new_session=True, **kwargs)
        self.execution.state['pending'] = {'pid': self.process.pid, 'pgid': self.process.pid,
            'start_time': start_time(self.process.pid), 'nonce': self.nonce, 'kind': self.operation}
        try:
            # The child has not received its launch/request frame yet.
            self.execution._save()
        except BaseException:
            self.terminate(self.process)
            raise
        return self.process

    def finish(self):
        if self.process is None:
            return
        self.process.poll()
        if group_alive(self.process.pid):
            raise StorageProcessError('Storage worker group remains active; no new worker started')
        self.execution.state.pop('pending', None)
        self.execution._save()

    def abort(self):
        if self.process is not None:
            self.terminate(self.process)
            try:
                self.process.communicate(timeout=0.2)
            except (subprocess.TimeoutExpired, OSError, ValueError):
                pass
            self.process.poll()
            if not group_alive(self.process.pid):
                self.execution.state.pop('pending', None)
                self.execution._save()

    def __exit__(self, kind, value, traceback):
        try:
            if self.process is not None and ('pending' in self.execution.state):
                self.abort()
        finally:
            if self.process is not None:
                if self.process.poll() is None:
                    _unreaped[self.process.pid] = self.process
                for handle in (self.process.stdin, self.process.stdout, self.process.stderr):
                    if handle is not None:
                        handle.close()
            self.execution.__exit__(kind, value, traceback)


def run_storage(args, input=None, pass_fds=(), timeout=15, registry=None, operation='storage', terminate=None):
    if not isinstance(args, (list, tuple)) or not args or any(not isinstance(arg, str) for arg in args):
        raise ValueError('Invalid storage command')
    with WorkerSlot(registry, operation, terminate) as slot:
        process = slot.spawn([sys.executable, '-B', '-m', 'installarr.storage_process', '--launch', slot.nonce],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, pass_fds=pass_fds)
        frame = (json.dumps({'nonce': slot.nonce, 'command': list(args)}) + '\n').encode()
        payload = input.encode() if isinstance(input, str) else input or b''
        try:
            output, error = process.communicate(frame + payload, timeout=timeout)
        except subprocess.TimeoutExpired:
            slot.abort()
            raise StorageProcessError('Storage operation exceeded its deadline; check storage recovery before retrying') from None
        slot.finish()
        return subprocess.CompletedProcess(args, process.returncode, output.decode(), error.decode())


def launch(nonce):
    header = bytearray()
    while len(header) <= 65536:
        item = os.read(0, 1)
        if not item:
            return 70
        if item == b'\n':
            break
        header.extend(item)
    else:
        return 70
    try:
        spec = json.loads(header)
        args = spec['command']
        if spec.get('nonce') != nonce or not isinstance(args, list) or not args or any(not isinstance(arg, str) for arg in args):
            return 70
        os.execvp(args[0], args)
    except (OSError, ValueError, KeyError, TypeError):
        return 70


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--launch' or not re.fullmatch(r'[0-9a-f]{32}', sys.argv[2]):
        raise SystemExit('Internal storage launcher only')
    raise SystemExit(launch(sys.argv[2]))
