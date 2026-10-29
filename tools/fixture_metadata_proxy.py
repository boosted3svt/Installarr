"""Container loopback HTTP CONNECT to a private Unix socket; no host TCP listener."""
import json
import select
import socket
import socketserver
import sys


def relay(left, right):
    while True:
        ready, _, _ = select.select([left, right], [], [], 30)
        if not ready:
            return
        for source in ready:
            data = source.recv(65536)
            if not data:
                return
            (right if source is left else left).sendall(data)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        header = b''
        while b'\r\n\r\n' not in header and len(header) < 8192:
            data = self.request.recv(1)
            if not data:
                return
            header += data
        words = header.split(b'\r\n', 1)[0].decode().split()
        if len(words) != 3 or words[0] != 'CONNECT':
            self.request.sendall(b'HTTP/1.1 405 Method Not Allowed\r\n\r\n')
            return
        host, port = words[1].rsplit(':', 1)
        with socket.socket(socket.AF_UNIX) as upstream:
            upstream.connect(sys.argv[1])
            upstream.sendall((json.dumps({'host': host, 'port': int(port)}) + '\n').encode())
            if upstream.recv(1) != b'1':
                self.request.sendall(b'HTTP/1.1 403 Forbidden\r\n\r\n')
                return
            self.request.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            relay(self.request, upstream)


if __name__ == '__main__':
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
    with Server(('127.0.0.1', 3128), Handler) as server:
        server.serve_forever()
