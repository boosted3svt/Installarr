"""Authentication-gated GUI listeners without host network configuration changes.

Each accepted connection enters only the audited app network namespace in a child,
then drops to the service identity. Bytes cross a private socketpair, never logs.
"""
import json
import os
from pathlib import Path
import select
import socket
import socketserver
import stat
import subprocess
import sys
import threading
import time

from .compose import IMAGES

def relay(left, right, stopped=None):
    left.setblocking(False)
    right.setblocking(False)
    peers = {left: right, right: left}
    buffers = {left: bytearray(), right: bytearray()}
    readable = set(peers)
    ended = set()
    idle = time.monotonic() + 300
    while (readable or any(buffers.values())) and time.monotonic() < idle:
        if stopped is not None and stopped.is_set():
            return
        reads = [item for item in readable if len(buffers[peers[item]]) < 262144]
        writes = [item for item in peers if buffers[item]]
        ready, writable, _ = select.select(reads, writes, [], 0.25)
        for item in ready:
            try:
                data = item.recv(65536)
            except BlockingIOError:
                continue
            if data:
                buffers[peers[item]].extend(data)
                idle = time.monotonic() + 300
            else:
                readable.discard(item)
        for item in writable:
            data = buffers[item]
            try:
                count = item.send(data)
            except BlockingIOError:
                continue
            del data[:count]
        for source, target in peers.items():
            if source not in readable and target not in ended and not buffers[target]:
                target.shutdown(socket.SHUT_WR)
                ended.add(target)


WORKER = "import os,select,socket,sys,time\ndef relay(left, right, stopped=None):\n    left.setblocking(False)\n    right.setblocking(False)\n    peers = {left: right, right: left}\n    buffers = {left: bytearray(), right: bytearray()}\n    readable = set(peers)\n    ended = set()\n    idle = time.monotonic() + 300\n    while (readable or any(buffers.values())) and time.monotonic() < idle:\n        if stopped is not None and stopped.is_set():\n            return\n        reads = [item for item in readable if len(buffers[peers[item]]) < 262144]\n        writes = [item for item in peers if buffers[item]]\n        ready, writable, _ = select.select(reads, writes, [], 0.25)\n        for item in ready:\n            try:\n                data = item.recv(65536)\n            except BlockingIOError:\n                continue\n            if data:\n                buffers[peers[item]].extend(data)\n                idle = time.monotonic() + 300\n            else:\n                readable.discard(item)\n        for item in writable:\n            data = buffers[item]\n            try:\n                count = item.send(data)\n            except BlockingIOError:\n                continue\n            del data[:count]\n        for source, target in peers.items():\n            if source not in readable and target not in ended and not buffers[target]:\n                target.shutdown(socket.SHUT_WR)\n                ended.add(target)\n\nos.setgroups([]); os.setgid(int(sys.argv[2])); os.setuid(int(sys.argv[1]))\nleft=socket.socket(fileno=0)\nright=socket.create_connection(('127.0.0.1',int(sys.argv[3])),timeout=5)\nrelay(left,right)\n"

class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        server = self.server
        if not server.capacity.acquire(blocking=False):
            return
        parent = child = process = None
        try:
            if server.stopped.is_set():
                return
            parent, child = socket.socketpair()
            process = subprocess.Popen(['nsenter', '--net=/proc/self/fd/{}'.format(server.nsfd),
                '--', '/usr/bin/python3', '-I', '-c', WORKER, str(server.uid), str(server.gid), str(server.port)],
                pass_fds=(server.nsfd,), stdin=child, stdout=child, stderr=subprocess.DEVNULL,
                close_fds=True, cwd='/', env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C.UTF-8'})
            child.close()
            with server.guard:
                server.clients.add(self.request)
                server.processes.add(process)
            relay(self.request, parent, server.stopped)
        except (OSError, ValueError):
            pass
        finally:
            if child is not None:
                child.close()
            if parent is not None:
                parent.close()
            if process is not None:
                if process.poll() is None:
                    process.kill()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
                with server.guard:
                    server.processes.discard(process)
            with server.guard:
                server.clients.discard(self.request)
            server.capacity.release()


class Access:
    def __init__(self, controller, ready_file, read_json):
        self.controller = controller
        self.ready_file = Path(ready_file)
        self.read_json = read_json
        self.servers = []
        self.identity = None
        self.credentials_file = None
        self.waiting_authentication = False

    def authorized(self):
        if not os.path.lexists(str(self.ready_file)):
            return False
        value = self.read_json(self.ready_file)
        if (set(value) != {'schema_version', 'bundle', 'authentication_verified', 'credentials_file'}
                or value.get('schema_version') != 1 or value.get('bundle') != self.controller.identity
                or value.get('authentication_verified') is not True
                or not isinstance(value.get('credentials_file'), str) or not value['credentials_file'].startswith('/')):
            raise ValueError('GUI authorization does not match the current bundle')
        self.credentials_file = value['credentials_file']
        return True

    def verify_authentication(self):
        from .apply import app_client
        from .credentials import read_private_credentials
        credentials = read_private_credentials(self.credentials_file)
        for app in self.controller.config['apps']:
            client = app_client(self.controller.config, self.controller, app)
            if client is None:
                return False
            client.verify_admin(credentials)
        return True

    def reconcile(self):
        if not self.authorized():
            self.close()
            return
        rows = self.controller.inventory()
        if not self.controller.audit(rows):
            raise ValueError('GUI backend is not running under the expected policy')
        app_rows = {row['Config']['Labels']['com.docker.compose.service']: row for row in rows}
        targets = []
        try:
            for app in self.controller.config['apps']:
                row = app_rows[app]
                pid = row['State']['Pid']
                fd = os.open('/proc/{}/ns/net'.format(pid), os.O_RDONLY)
                targets.append((app, row['Id'], fd, os.fstat(fd).st_ino))
            identity = tuple((app, cid, inode) for app, cid, _, inode in targets)
            if self.identity == identity and all(server.thread.is_alive() for server in self.servers):
                return
            self.close()
            try:
                verified = self.verify_authentication()
            except (ValueError, OSError):
                verified = False
            if not verified:
                self.waiting_authentication = True
                return
            self.waiting_authentication = False
            config = self.controller.config
            for app, cid, fd, inode in targets:
                port = IMAGES[app]['port']
                server = Server((config['bind_address'], port), Handler, bind_and_activate=False)
                server.nsfd = os.dup(fd)
                server.uid = config['service_user']['uid']
                server.gid = config['service_user']['gid']
                server.port = port
                server.capacity = threading.BoundedSemaphore(64)
                server.stopped = threading.Event()
                server.guard = threading.Lock()
                server.clients, server.processes = set(), set()
                # Record before bind so a conflict closes every newly held FD.
                self.servers.append(server)
                server.server_bind()
                server.server_activate()
                server.thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.2}, daemon=True)
                server.thread.start()
            self.identity = identity
        except BaseException:
            self.close()
            raise
        finally:
            for _, _, fd, _ in targets:
                os.close(fd)

    def close(self):
        for server in self.servers:
            server.stopped.set()
            thread = getattr(server, 'thread', None)
            if thread and thread.is_alive():
                server.shutdown()
            server.server_close()
            with server.guard:
                for connection in list(server.clients):
                    try:
                        connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                for process in list(server.processes):
                    if process.poll() is None:
                        process.kill()
            os.close(server.nsfd)
        self.servers = []
        self.identity = None

    def status(self):
        if not self.identity:
            return {'enabled': False, 'urls': {}, 'waiting_authentication': self.waiting_authentication}
        config = self.controller.config
        return {'enabled': True, 'urls': {app: 'http://{}:{}/'.format(config['bind_address'], IMAGES[app]['port'])
                                         for app in config['apps']}}
