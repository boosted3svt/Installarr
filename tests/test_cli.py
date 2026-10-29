import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from installarr.cli import main, plan, save_config, validate, validate_timezone


def configuration():
    return {
        "schema_version": 1, "apps": ["plex", "netbootxyz"],
        "timezone": "America/Chicago", "bind_address": "192.168.1.101",
        "plex_allowed_networks": "192.168.0.0/23",
        "project_directory": "/opt/media-stack",
        "service_user": {"name": "media", "uid": 2000, "gid": 2000},
        "storage": {p: f"/srv/stack/{p}" for p in ("media", "downloads", "incomplete", "configs", "backups")},
    }


class ConfigurationTests(unittest.TestCase):
    def test_timezone_database_validation(self):
        validate_timezone("America/Chicago")
        for name in ("../etc/passwd", "/etc/passwd", "", "Not/AZone", "zone.tab", None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_timezone(name)

    def test_reject_root_identity_and_invalid_storage(self):
        for field, value in (("uid", 0), ("gid", 0), ("uid", True)):
            config = configuration()
            config["service_user"][field] = value
            with self.assertRaises(ValueError):
                validate(config)
        config = configuration()
        config["storage"]["media"] = "/srv/../etc"
        with self.assertRaises(ValueError):
            validate(config)

    def test_reject_secret_fields(self):
        config = configuration()
        config["password"] = "not-a-real-password"
        with self.assertRaises(ValueError):
            validate(config)

    @patch("installarr.cli.identity_conflicts", return_value=[])
    def test_optional_netboot_identity_and_no_config_mutation(self, lookup):
        config = configuration()
        original = copy.deepcopy(config)
        self.assertEqual(plan(config)["netbootxyz_identity"], {"name": "nbxyz", "uid": 911, "gid": 1001})
        self.assertEqual(config, original)
        config["apps"] = ["plex"]
        self.assertIsNone(plan(config)["netbootxyz_identity"])

    @patch("installarr.cli.identity_conflicts", return_value=[])
    def test_reserved_id_conflict(self, lookup):
        config = configuration()
        config["service_user"]["gid"] = 1001
        self.assertTrue(plan(config)["conflicts"])
        config = configuration()
        config["service_user"]["name"] = "nbxyz"
        self.assertTrue(plan(config)["conflicts"])

    def test_save_private_and_never_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config(path, configuration())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                save_config(path, configuration())
            self.assertEqual(json.loads(path.read_text()), configuration())

    @patch("installarr.cli.identity_conflicts", return_value=["occupied UID"])
    @patch("builtins.print")
    def test_plan_conflicts_exit_nonzero(self, output, lookup):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config(path, configuration())
            self.assertEqual(main(["plan", "--config", str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
