from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from installarr.prerequisites import prepare_prerequisites, verify_signed_sources
from test_compose import compose_configuration


class PrerequisiteTests(unittest.TestCase):
    @patch("installarr.prerequisites.provisioning_gate")
    @patch("installarr.prerequisites.verify_signed_sources")
    @patch("installarr.prerequisites.run")
    @patch("installarr.prerequisites.installed_version")
    def test_client_install_before_readback_never_mounts_or_removes(self, version, run, verify, gate):
        config = compose_configuration()
        for purpose in ("media", "downloads", "incomplete"):
            config["storage_mounts"][purpose] = {"kind": "existing", "mountpoint": "/srv/stack", "source": "nas:/isolated", "fstype": "nfs", "sentinel": "health"}
        version.side_effect = [None, "version-verified", "version-verified"]
        with tempfile.TemporaryDirectory() as directory:
            result = prepare_prerequisites(config, Path(directory) / "state")
        self.assertEqual(result["packages"], {"nfs-common": "version-verified"})
        verify.assert_called_once()
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn("update", commands[0])
        self.assertIn("--no-remove", commands[1])
        self.assertIn("nfs-common", commands[1])
        self.assertFalse(any(command[0] == "mount" for command in commands))

    @patch("installarr.prerequisites.Path.exists", return_value=True)
    @patch("installarr.prerequisites.Path.glob", return_value=[])
    @patch("installarr.prerequisites.Path.read_text")
    def test_explicit_repository_trust_bypass_refused(self, read, glob, exists):
        for text in ("deb [trusted=yes] https://example.invalid stable main", "Trusted: yes", "allow-insecure=true"):
            read.return_value = text
            with self.assertRaises(ValueError):
                verify_signed_sources()
        read.return_value = "# Trusted: yes\nTypes: deb\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg"
        verify_signed_sources()
