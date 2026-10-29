import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from installarr.cli import main
from installarr.credentials import initialize_credentials, read_private_credentials


class CredentialTests(unittest.TestCase):
    def test_create_reuse_and_no_credentials_in_checkpoints_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "secrets"
            credentials = {"username": "sample-admin", "password": "synthetic-secret-123"}
            result = initialize_credentials(target, lambda: credentials)
            self.assertEqual(result["status"], "created")
            self.assertEqual(read_private_credentials(target / "gui-admin.json"), credentials)
            result = initialize_credentials(target, lambda: self.fail("Prompted again"))
            self.assertEqual(result["status"], "reused")
            self.assertFalse((target / "state.json").exists())
            self.assertEqual(sorted(path.name for path in target.iterdir()), [".credential-state", "gui-admin.json"])
            self.assertFalse(list(target.rglob("state.json")))
            self.assertNotIn(credentials["password"], json.dumps(result))

    def test_cli_unattended_import_never_prints_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            source.write_text(json.dumps({"username": "sample-admin", "password": "synthetic-secret-456"}))
            source.chmod(0o600)
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                self.assertEqual(main(["init-secrets", "--secrets-directory", str(Path(directory) / "secrets"),
                                       "--credentials-file", str(source)]), 0)
            self.assertNotIn("sample-admin", output.getvalue())
            self.assertNotIn("synthetic-secret-456", output.getvalue())

    def test_unsafe_import_files_and_invalid_values_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            source.write_text('{"username":"example","password":"synthetic"}')
            source.chmod(0o644)
            with self.assertRaises(ValueError):
                read_private_credentials(source)
            source.chmod(0o600)
            linked = Path(directory) / "linked.json"
            os.link(source, linked)
            with self.assertRaises(ValueError):
                read_private_credentials(source)
            linked.unlink()
            linked.symlink_to(source)
            with self.assertRaises(ValueError):
                read_private_credentials(linked)
            source.unlink()
            os.mkfifo(source, mode=0o600)
            with self.assertRaises(ValueError):
                read_private_credentials(source)

    def test_invalid_existing_store_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "secrets"
            target.mkdir(mode=0o700)
            saved = target / "gui-admin.json"
            saved.write_text("interrupted or corrupt")
            saved.chmod(0o600)
            with self.assertRaises(ValueError):
                initialize_credentials(target, lambda: self.fail("Must not overwrite"))
            self.assertEqual(saved.read_text(), "interrupted or corrupt")

    def test_empty_password_never_published(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "secrets"
            with self.assertRaises(ValueError):
                initialize_credentials(target, lambda: {"username": "example", "password": ""})
            self.assertFalse((target / "gui-admin.json").exists())

    def test_selected_basic_apps_reject_colon_before_private_file_publication(self):
        from installarr.credentials import validate_selected_gui_credentials
        from test_compose import compose_configuration
        credentials = {'username': 'synthetic:colon', 'password': 'synthetic-password'}
        for app in ('sabnzbd', 'bazarr', 'netbootxyz'):
            with self.assertRaises(ValueError):
                validate_selected_gui_credentials({'apps': [app]}, credentials)
        self.assertEqual(validate_selected_gui_credentials({'apps': ['radarr']}, credentials), credentials)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = compose_configuration(); config['apps'] = ['netbootxyz']
            path = root / 'config.json'; path.write_text(json.dumps(config))
            source = root / 'input.json'; source.write_text(json.dumps(credentials)); source.chmod(0o600)
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                self.assertEqual(main(['init-secrets', '--secrets-directory', str(root / 'secrets'),
                    '--credentials-file', str(source), '--config', str(path)]), 1)
            self.assertFalse((root / 'secrets/gui-admin.json').exists())
            self.assertIn('username without a colon', output.getvalue())
            self.assertNotIn('synthetic-password', output.getvalue())
