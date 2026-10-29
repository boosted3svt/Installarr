import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from installarr.access import Access, relay


class AccessTests(unittest.TestCase):
    def test_binary_half_close_and_large_response_are_preserved(self):
        client, inbound = socket.socketpair()
        outbound, backend = socket.socketpair()
        data = bytes(range(256)) * 3000
        response = b'response' * 100000
        received = []
        errors = []
        def server():
            try:
                result = bytearray()
                while True:
                    block = backend.recv(65536)
                    if not block:
                        break
                    result.extend(block)
                received.append(bytes(result))
                backend.sendall(response)
                backend.shutdown(socket.SHUT_WR)
            except Exception as error:
                errors.append(error)
        def forward():
            try:
                relay(inbound, outbound)
            except Exception as error:
                errors.append(error)
        threads = [threading.Thread(target=server, daemon=True), threading.Thread(target=forward, daemon=True)]
        try:
            client.settimeout(5)
            for thread in threads:
                thread.start()
            client.sendall(data)
            client.shutdown(socket.SHUT_WR)
            result = bytearray()
            while True:
                block = client.recv(65536)
                if not block:
                    break
                result.extend(block)
            for thread in threads:
                thread.join(5)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertFalse(errors)
            self.assertEqual(received, [data])
            self.assertEqual(bytes(result), response)
        finally:
            for item in (client, inbound, outbound, backend):
                item.close()

    @patch('installarr.access.Server')
    def test_no_gui_authorization_never_binds_listener(self, server):
        with tempfile.TemporaryDirectory() as directory:
            controller = Mock(identity='bundle')
            access = Access(controller, Path(directory) / 'missing.json', Mock())
            access.reconcile()
            server.assert_not_called()
            controller.inventory.assert_not_called()

    @patch('installarr.access.Server')
    def test_restart_with_unverified_authentication_keeps_gui_closed(self, server):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'ready.json'
            marker.touch()
            controller = Mock(identity='bundle', config={'apps': ['radarr']})
            controller.inventory.return_value = [{'Id': 'a' * 64, 'Config': {'Labels': {'com.docker.compose.service': 'radarr'}},
                                                  'State': {'Pid': os.getpid()}}]
            reader = Mock(return_value={'schema_version': 1, 'bundle': 'bundle', 'authentication_verified': True,
                                        'credentials_file': '/private/gui-admin.json'})
            access = Access(controller, marker, reader)
            with patch.object(access, 'verify_authentication', return_value=False):
                access.reconcile()
            server.assert_not_called()
            self.assertFalse(access.status()['enabled'])
            self.assertTrue(access.status()['waiting_authentication'])
