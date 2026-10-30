import json
import subprocess
import unittest
from unittest.mock import Mock, patch

from installarr.arr import AppAPIError, ArrClient, DockerHTTP


class ArrTests(unittest.TestCase):
    @patch('installarr.arr.subprocess.run')
    def test_root_timeout_is_bounded_specific_private_and_not_retried(self, run):
        run.return_value = Mock(returncode=28, stdout='secret-response', stderr='secret-password')
        transport = DockerHTTP('unix:///run/docker.sock', 'a' * 64, 8989, 'b' * 32)
        for method in ('GET', 'POST'):
            run.reset_mock()
            with self.assertRaises(AppAPIError) as raised:
                transport.request(method, '/api/v3/rootfolder', {'path': '/data/private-folder'})
            message = str(raised.exception)
            self.assertIn('Sonarr media-folder request timed out after 60 seconds', message)
            self.assertNotIn('secret', message)
            self.assertNotIn('private-folder', message)
            run.assert_called_once()
            args = run.call_args.args[0]
            self.assertEqual(args[args.index('--max-time') + 1], '60')
            self.assertEqual(run.call_args.kwargs['timeout'], 65)

    @patch('installarr.arr.subprocess.run')
    def test_transport_errors_keep_safe_diagnostics_and_ordinary_deadline(self, run):
        transport = DockerHTTP('unix:///run/docker.sock', 'a' * 64, 7878, 'b' * 32)
        for failure, expected in ((Mock(returncode=7), 'transport failed (exit 7)'),
                                  (subprocess.TimeoutExpired('private-secret', 15), 'timed out after 10 seconds'),
                                  (Mock(returncode=0, stdout='private-secret'), 'application request failed')):
            run.reset_mock(side_effect=True)
            if isinstance(failure, Exception):
                run.side_effect = failure
            else:
                run.return_value = failure
            with self.assertRaises(AppAPIError) as raised:
                transport.request('GET', '/api/v3/system/status')
            self.assertIn('Radarr', str(raised.exception))
            self.assertIn(expected, str(raised.exception))
            self.assertNotIn('private-secret', str(raised.exception))
            run.assert_called_once()
            self.assertEqual(run.call_args.kwargs['timeout'], 15)

    def test_root_rerun_no_duplicate_and_dynamic_id(self):
        transport = Mock()
        transport.request.return_value = (200, json.dumps([{"id": 91, "path": "/data/media/TV", "accessible": True}]))
        client = ArrClient(transport)
        self.assertEqual(client.ensure_root("/data/media/TV"), 91)
        self.assertEqual(transport.request.call_count, 1)
        with self.assertRaises(AppAPIError):
            client.ensure_root("/data/media/../outside")

    def test_secondary_root_requires_explicit_owned_mapping_and_exact_target(self):
        transport = Mock()
        transport.request.return_value = (200, json.dumps([{'id': 33, 'path': '/media-secondary', 'accessible': True}]))
        with self.assertRaises(AppAPIError):
            ArrClient(transport).ensure_root('/media-secondary')
        transport.request.assert_not_called()
        client = ArrClient(transport, secondary_root=True)
        self.assertEqual(client.ensure_root('/media-secondary'), 33)
        for path in ('/media-secondary/other', '/media-secondary/../etc', '/etc'):
            with self.assertRaises(AppAPIError):
                client.ensure_root(path)

    def test_write_requires_accessible_readback(self):
        transport = Mock()
        transport.request.side_effect = [(200, "[]"), (200, '{"version":"4.0.20.3014"}'), (201, '{"id":17}'),
                                        (200, '[{"id":17,"path":"/data/media/Movies","accessible":false}]')]
        with self.assertRaises(AppAPIError):
            ArrClient(transport, expected_version="4.0.20.3014").ensure_root("/data/media/Movies")
        self.assertEqual(transport.request.call_count, 4)

    def test_runtime_version_mismatch_prevents_writes(self):
        transport = Mock()
        transport.request.return_value = (200, '{"version":"unreviewed"}')
        with self.assertRaises(AppAPIError):
            ArrClient(transport, expected_version="4.0.20.3014").json("PUT", "config/host/1", {})
        self.assertEqual(transport.request.call_args.args[0], "GET")
        with self.assertRaises(AppAPIError):
            ArrClient(transport).json("PUT", "config/host/1", {})

    def test_auth_acceptance_is_not_proof_of_working_credentials(self):
        transport = Mock()
        transport.request.side_effect = [(200, json.dumps({"username": "example", "authenticationMethod": "forms", "authenticationRequired": "enabled"})),
                                        (302, ""), (401, "")]
        transport.login.return_value = {"login": 302, "api": 401, "gui": 302}
        with self.assertRaises(AppAPIError):
            ArrClient(transport).verify_admin({"username": "example", "password": "synthetic"})

    def test_valid_gui_cookie_does_not_substitute_for_an_api_key(self):
        transport = Mock()
        transport.request.side_effect = [(200, json.dumps({"username": "example", "authenticationMethod": "forms", "authenticationRequired": "enabled"})),
                                        (302, ""), (401, "")]
        transport.login.side_effect = [{"login": 302, "api": 401, "gui": 200},
                                      {"login": 302, "api": 401, "gui": 302}]
        result = ArrClient(transport).verify_admin({"username": "example", "password": "synthetic"})
        self.assertEqual(result["valid_login"]["gui"], 200)
        self.assertEqual(result["anonymous_api"], 401)

    @patch("installarr.arr.subprocess.run")
    def test_credentials_and_api_key_only_on_stdin(self, run):
        run.return_value = Mock(returncode=0, stdout='{}\n200')
        transport = DockerHTTP("unix:///run/installarr-docker-test/docker.sock", "a" * 64, 8989, "b" * 32)
        transport.request("PUT", "/api/v3/config/host", {"password": "synthetic-private"})
        args = run.call_args.args[0]
        self.assertNotIn("synthetic-private", " ".join(args))
        self.assertNotIn("b" * 32, " ".join(args))
        self.assertIn("synthetic-private", run.call_args.kwargs["input"])
        self.assertIn("b" * 32, run.call_args.kwargs["input"])
