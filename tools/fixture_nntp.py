"""Loopback-only NNTP fixture serving one generated, noncopyrighted article."""
import json
from pathlib import Path
import socketserver
import threading
import zlib

PAYLOAD = (b"Installarr generated test payload. No third-party content.\n" * 64)
MESSAGE_ID = "installarr-proof@fixture.invalid"
FILENAME = "installarr-proof.bin"
COUNTS = {"body_requests": 0, "article_requests": 0}
LOCK = threading.Lock()


def yenc():
    lines, line = [], bytearray()
    for item in PAYLOAD:
        value = (item + 42) & 255
        token = bytes([61, (value + 64) & 255]) if value in (0, 10, 13, 61) else bytes([value])
        if len(line) + len(token) > 128:
            lines.append(bytes(line)); line = bytearray()
        line.extend(token)
    if line:
        lines.append(bytes(line))
    data = ["=ybegin line=128 size={} name={}".format(len(PAYLOAD), FILENAME).encode(), *lines,
            "=yend size={} crc32={:08x}".format(len(PAYLOAD), zlib.crc32(PAYLOAD) & 0xffffffff).encode()]
    return b"\r\n".join((b"." + item if item.startswith(b".") else item) for item in data) + b"\r\n.\r\n"


class Handler(socketserver.StreamRequestHandler):
    def send(self, text):
        self.wfile.write(text.encode() + b"\r\n")

    def handle(self):
        self.send("200 Installarr generated NNTP fixture ready")
        while True:
            raw = self.rfile.readline(8192)
            if not raw:
                return
            words = raw.decode("ascii", errors="replace").strip().split()
            if not words:
                continue
            verb = words[0].upper()
            if verb == "QUIT":
                self.send("205 Closing"); return
            if verb == "CAPABILITIES":
                self.wfile.write(b"101 Capabilities\r\nVERSION 2\r\nREADER\r\n.\r\n")
            elif verb == "MODE":
                self.send("200 Reader mode")
            elif verb == "GROUP":
                self.send("211 1 1 1 alt.binaries.installarr")
            elif verb == "DATE":
                self.send("111 20261028010000")
            elif verb == "AUTHINFO":
                self.send("381 Password required" if len(words) > 1 and words[1].upper() == "USER" else "281 Authenticated")
            elif verb in ("BODY", "ARTICLE", "STAT", "HEAD") and len(words) > 1 and words[1].strip("<>") == MESSAGE_ID:
                code = {"BODY": 222, "ARTICLE": 220, "STAT": 223, "HEAD": 221}[verb]
                self.send("{} 1 <{}>".format(code, MESSAGE_ID))
                if verb in ("BODY", "ARTICLE"):
                    with LOCK:
                        COUNTS["body_requests" if verb == "BODY" else "article_requests"] += 1
                        Path("/tmp/installarr-nntp-counts.json").write_text(json.dumps(COUNTS))
                if verb in ("ARTICLE", "HEAD"):
                    self.wfile.write(('Message-ID: <{}>\r\nSubject: "{}" yEnc (1/1)\r\nNewsgroups: alt.binaries.installarr\r\n\r\n'.format(MESSAGE_ID, FILENAME)).encode())
                if verb in ("BODY", "ARTICLE"):
                    self.wfile.write(yenc())
                elif verb == "HEAD":
                    self.wfile.write(b".\r\n")
            elif verb in ("BODY", "ARTICLE", "STAT", "HEAD"):
                self.send("430 No such article")
            else:
                self.send("500 Unsupported fixture command")


if __name__ == "__main__":
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
    with Server(("127.0.0.1", 21119), Handler) as server:
        Path("/tmp/installarr-nntp-ready").write_text("ready\n")
        server.serve_forever()
