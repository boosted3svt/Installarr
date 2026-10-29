"""Open/inspect storage anchors in a tracked worker and transfer held descriptors."""
import array
import fcntl
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time

from .storage_process import WorkerSlot, StorageProcessError

MAX_ANCHORS = 128


def open_anchors(requests, timeout=10, registry=None):
    if not isinstance(requests, list) or not requests or len(requests) > MAX_ANCHORS:
        raise ValueError('Storage anchor batch must contain 1-128 paths')
    for item in requests:
        if (not isinstance(item, dict) or set(item) - {'path', 'read_only'} or 'path' not in item
                or not isinstance(item['path'], str) or not Path(item['path']).is_absolute()
                or '..' in Path(item['path']).parts or ('read_only' in item and type(item['read_only']) is not bool)):
            raise ValueError('Invalid storage anchor request')
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    received = []
    try:
        with WorkerSlot(registry, 'anchors') as slot:
            request_frame = json.dumps({'nonce': slot.nonce, 'requests': requests}).encode()
            if len(request_frame) > 65536:
                raise ValueError('Storage anchor request exceeds bounded size')
            process = slot.spawn([sys.executable, '-B', '-m', 'installarr.anchors', '--channel', str(child.fileno()),
                                  '--nonce', slot.nonce], pass_fds=(child.fileno(),), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            child.close()
            start = time.monotonic()
            parent.send(request_frame)
            if not select.select([parent], [], [], timeout)[0]:
                raise StorageProcessError('Storage anchor inspection exceeded its deadline')
            body, controls, flags, address = parent.recvmsg(65536, socket.CMSG_SPACE(MAX_ANCHORS * array.array('i').itemsize))
            for level, kind, data in controls:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    descriptors = array.array('i'); descriptors.frombytes(data[:len(data) - len(data) % descriptors.itemsize])
                    received.extend(descriptors)
            if flags & (socket.MSG_CTRUNC | socket.MSG_TRUNC):
                raise StorageProcessError('Storage anchor response was truncated')
            result = json.loads(body)
            if (result.get('nonce') != slot.nonce or not result.get('ok') or len(received) != len(requests)
                    or not isinstance(result.get('anchors'), list) or len(result['anchors']) != len(requests)):
                raise StorageProcessError('Storage anchor inspection refused; existing data preserved')
            try:
                process.wait(timeout=max(0.01, timeout - (time.monotonic() - start)))
            except subprocess.TimeoutExpired:
                raise StorageProcessError('Storage anchor worker has not exited') from None
            if process.returncode:
                raise StorageProcessError('Storage anchor worker failed')
            slot.finish()
            anchors = []
            for fd, item in zip(received, result['anchors']):
                if not fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_DIRECTORY or set(item) != {'parts', 'observed'}:
                    raise StorageProcessError('Invalid held storage anchor')
                os.set_inheritable(fd, False)
                anchors.append((fd, item['parts'], item['observed']))
            received = []
            return anchors
    except (ValueError, OSError) as error:
        if isinstance(error, StorageProcessError):
            raise
        raise StorageProcessError('Storage anchor inspection failed; existing data preserved') from None
    finally:
        parent.close(); child.close()
        for fd in received:
            os.close(fd)


def worker(channel, nonce):
    from .directories import open_anchor, observed_mount
    held = []
    try:
        spec = json.loads(channel.recv(65536))
        if spec.get('nonce') != nonce or not isinstance(spec.get('requests'), list) or not 1 <= len(spec['requests']) <= MAX_ANCHORS:
            raise ValueError('Invalid internal anchor frame')
        results = []
        for item in spec['requests']:
            fd, parts = open_anchor(item['path'])
            held.append(fd)
            results.append({'parts': parts, 'observed': observed_mount(fd, require_writable=not item.get('read_only'))})
        descriptors = array.array('i', held)
        channel.sendmsg([json.dumps({'nonce': nonce, 'ok': True, 'anchors': results}).encode()],
                        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, descriptors)])
    except Exception:
        channel.send(json.dumps({'nonce': nonce, 'ok': False}).encode())
        return 1
    finally:
        for fd in held:
            os.close(fd)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 5 or sys.argv[1] != '--channel' or sys.argv[3] != '--nonce':
        raise SystemExit('Internal storage anchor worker only')
    channel = socket.socket(fileno=int(sys.argv[2]))
    try:
        raise SystemExit(worker(channel, sys.argv[4]))
    finally:
        channel.close()
