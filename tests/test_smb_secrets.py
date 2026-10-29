import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from installarr.cli import main
from installarr.credentials import validate_secret_filename
from installarr.mounts import protected_smb_file
from installarr.smb_secrets import initialize_smb_secrets, read_smb_input, validate_smb_secrets


class SMBInputTests(unittest.TestCase):
    def test_line_injection_and_reserved_filenames_refused(self):
        for value in ('with\nnewline', 'with\rreturn', 'with\x00nul', 'with\u2028separator', 'with\u0085separator'):
            for field in ('username', 'password', 'domain'):
                row = {'username': 'synthetic', 'password': 'synthetic', 'domain': 'LAB'}
                row[field] = value
                with self.assertRaises(ValueError):
                    validate_smb_secrets(row)
        for filename in ('../escape', '/absolute', 'lock', 'state.json', '.credential-state', '.', 'bad\nname'):
            with self.assertRaises(ValueError):
                validate_secret_filename(filename)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.json'
            source.write_text(json.dumps({'username': 'synthetic', 'password': 'not-a-real-password', 'domain': 'LAB'}))
            source.chmod(0o644)
            with self.assertRaises(ValueError):
                read_smb_input(source)

    @unittest.skipIf(os.geteuid() == 0, 'Nonroot refusal is tested as the normal user')
    def test_nonroot_refuses_before_creating_store(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'secrets'
            with self.assertRaises(ValueError):
                initialize_smb_secrets(target, lambda: self.fail('must not prompt'))
            self.assertFalse(target.exists())


@unittest.skipUnless(os.geteuid() == 0, 'SMB files require root ownership')
class RootSMBSecretsTests(unittest.TestCase):
    def test_private_unattended_import_reuse_and_no_secret_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = {'username': 'private-smb-user', 'password': 'synthetic=pass#with$characters', 'domain': 'PRIVATE-LAB'}
            source = root / 'input.json'
            source.write_text(json.dumps(values)); source.chmod(0o600)
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), patch('installarr.cli.getpass.getpass') as prompt:
                self.assertEqual(main(['init-smb-secrets', '--secrets-directory', str(root / 'secrets'), '--filename', 'nas-login.conf', '--credentials-file', str(source)]), 0)
                prompt.assert_not_called()
            target = root / 'secrets/nas-login.conf'
            self.assertTrue(protected_smb_file(target))
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(target.stat().st_uid, 0)
            for value in values.values():
                self.assertNotIn(value, output.getvalue())
                self.assertTrue(all(value not in state.read_text() for state in (root / 'secrets').rglob('state.json')))
            original = target.read_bytes()
            self.assertEqual(initialize_smb_secrets(root / 'secrets', lambda: self.fail('prompted again'), 'nas-login.conf')['status'], 'reused')
            self.assertEqual(target.read_bytes(), original)
            target.chmod(0o644)
            with self.assertRaises(ValueError):
                initialize_smb_secrets(root / 'secrets', lambda: self.fail('must preserve'), 'nas-login.conf')
            self.assertEqual(target.read_bytes(), original)

    def test_shared_private_directory_can_hold_distinct_share_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'secrets'
            values = {'username': 'synthetic-user', 'password': 'synthetic-password'}
            for filename in ('first.credentials', 'second.credentials'):
                initialize_smb_secrets(root, lambda: values, filename)
                self.assertTrue(protected_smb_file(root / filename))
            states = [json.loads(path.read_text()) for path in root.rglob('state.json')]
            self.assertEqual({filename for state in states for filename in state['files']}, {'first.credentials', 'second.credentials'})
            self.assertNotIn('synthetic-password', json.dumps(states))


    def test_all_collectors_share_private_parent_and_preserve_legacy_store(self):
        from installarr.credentials import initialize_credentials
        from installarr.execution import Execution
        from installarr.provider_secrets import initialize_provider_secrets
        from installarr.plex import store_claim
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'shared'
            initialize_credentials(root, lambda: {'username': 'synthetic-admin', 'password': 'synthetic-gui'})
            initialize_provider_secrets(root, ['nzbgeek'], lambda name: {'api_key': 'e' * 32}, 'provider-keys.json')
            initialize_smb_secrets(root, lambda: {'username': 'synthetic-smb', 'password': 'synthetic-smb-pass'}, 'nas-login.conf')
            store_claim(root, lambda: 'claim-abcdefghijklmnop', filename='private-claim.token')
            self.assertTrue(protected_smb_file(root / 'nas-login.conf'))
            states = [path.read_text() for path in root.rglob('state.json')]
            self.assertNotIn('synthetic-gui', repr(states))
            self.assertNotIn('synthetic-smb-pass', repr(states))
            self.assertNotIn('e' * 32, repr(states))
            legacy = Path(directory) / 'legacy'
            with Execution(legacy, {'operation': 'provider-credentials-v1', 'providers': ['nzbgeek']}) as state:
                state._save()
            target = legacy / 'providers.json'
            target.write_text(json.dumps({'nzbgeek': {'api_key': 'f' * 32}})); target.chmod(0o600)
            before = {path.name: path.read_bytes() for path in legacy.iterdir()}
            self.assertEqual(initialize_provider_secrets(legacy, ['nzbgeek'], lambda name: self.fail('must reuse'))['status'], 'reused')
            self.assertEqual(before, {path.name: path.read_bytes() for path in legacy.iterdir()})
