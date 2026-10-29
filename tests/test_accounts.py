from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from installarr.accounts import ensure_identity, prepare_accounts, provisioning_gate, supported_ubuntu
from test_cli import configuration


class AccountTests(unittest.TestCase):
    def test_partial_group_creation_recovers_without_repeating_mutation(self):
        groups, users, calls = {}, {}, []
        identity = {"name": "media", "uid": 2000, "gid": 2000}

        def group(name):
            if name not in groups:
                raise KeyError(name)
            return groups[name]

        def user(name):
            if name not in users:
                raise KeyError(name)
            return users[name]

        def run(args):
            calls.append(args)
            if args[0].endswith("groupadd"):
                groups["media"] = SimpleNamespace(gr_gid=2000)
                raise RuntimeError("Interrupted after group creation")
            users["media"] = SimpleNamespace(pw_uid=2000, pw_gid=2000)

        with patch("installarr.accounts.grp.getgrnam", side_effect=group), patch("installarr.accounts.pwd.getpwnam", side_effect=user):
            with self.assertRaises(RuntimeError):
                ensure_identity(identity, lambda *args: [], run)
            ensure_identity(identity, lambda *args: [], run)
            ensure_identity(identity, lambda *args: [], run)
        self.assertEqual(len(calls), 2)
        self.assertIn("--no-create-home", calls[1])
        self.assertIn("/usr/sbin/nologin", calls[1])

    def test_collision_refuses_all_commands(self):
        with patch("installarr.accounts.run_account_command") as run:
            with self.assertRaises(ValueError):
                ensure_identity({"name": "media", "uid": 2000, "gid": 2000}, lambda *args: ["collision"], run)
            run.assert_not_called()

    @patch("installarr.accounts.provisioning_gate")
    @patch("installarr.accounts.ensure_identity")
    def test_reserved_name_and_late_collision_prevent_any_mutation(self, ensure, gate):
        config = configuration()
        config["service_user"]["name"] = "nbxyz"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state"
            with self.assertRaises(ValueError):
                prepare_accounts(config, path, lambda *args: [])
            self.assertFalse(path.exists())
            config = configuration()
            with self.assertRaises(ValueError):
                prepare_accounts(config, path, lambda name, *args: ["collision"] if name == "nbxyz" else [])
            self.assertFalse(path.exists())
            ensure.assert_not_called()

    @patch("installarr.accounts.Path.read_text", return_value='ID=ubuntu\nVERSION_ID="18.04"\n')
    def test_unsupported_host_refused(self, read):
        with self.assertRaises(ValueError):
            provisioning_gate()

    @patch("installarr.accounts.Path.read_text", return_value='ID=ubuntu\nVERSION_ID="24.04"\n')
    @patch("installarr.accounts.os.geteuid", return_value=1000)
    def test_unprivileged_host_refused(self, uid, read):
        with self.assertRaises(ValueError):
            provisioning_gate()

    def test_ubuntu_20_and_newer_accepted_older_and_unknown_refused(self):
        for version in ("20.04", "20.10", "22.04", "24.04", "26.04"):
            with self.subTest(version=version):
                self.assertTrue(supported_ubuntu({"ID": "ubuntu", "VERSION_ID": version}))
                with patch("installarr.accounts.Path.read_text", return_value='ID=ubuntu\nVERSION_ID="{}"\n'.format(version)), patch("installarr.accounts.os.geteuid", return_value=0):
                    provisioning_gate()
        for release in ({}, {"ID": "debian", "VERSION_ID": "24.04"},
                        {"ID": "ubuntu", "VERSION_ID": "18.04"},
                        {"ID": "ubuntu", "VERSION_ID": "invalid"}):
            self.assertFalse(supported_ubuntu(release))
