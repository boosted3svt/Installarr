import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from installarr import runtime


class RuntimeTests(unittest.TestCase):
    def test_only_inactive_or_failed_units_are_accepted(self):
        for phase in ('active', 'activating', 'deactivating', 'reloading', 'unknown'):
            with patch('installarr.runtime.subprocess.run', return_value=subprocess.CompletedProcess([], 0, phase)):
                with self.assertRaises(ValueError):
                    runtime.stopped('test')
        for phase in ('inactive', 'failed'):
            with patch('installarr.runtime.subprocess.run', return_value=subprocess.CompletedProcess([], 0, phase)):
                runtime.stopped('test')
        for name in ('../etc', 'a' * 27, 'Test', 'a.service'):
            with self.assertRaises(ValueError):
                runtime.targets(name)

    def test_recovery_validates_every_artifact_before_restoring(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = []
            for target in ('sample', 'sample-boot'):
                for index in range(4):
                    path = root / (target + str(index))
                    path.write_bytes(b'updated')
                    rows.append({'path': str(path), 'mode': 0o600,
                                 'old': base64.b64encode(b'original').decode(),
                                 'old_hash': hashlib.sha256(b'original').hexdigest(),
                                 'new_hash': hashlib.sha256(b'updated').hexdigest()})
            class State:
                state = {'runtime_refresh': {'files': rows, 'apply_evidence': {'live_unit': 'old-hash'}}}
                def _save(self):
                    pass
            state = State()
            def fake_paths(name):
                return [(Path(row['path']), row['mode']) for row in rows if Path(row['path']).name.startswith(name) and ('-boot' in Path(row['path']).name) == name.endswith('-boot')]
            def fake_read(path, mode):
                return path.read_bytes()
            def fake_replace(path, data, mode, accepted):
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), accepted)
                path.write_bytes(data)
            with patch.object(runtime, 'paths', side_effect=fake_paths), patch.object(runtime, 'read_owned', side_effect=fake_read), patch.object(runtime, 'replace_owned', side_effect=fake_replace), patch.object(runtime, 'command'):
                Path(rows[-1]['path']).write_bytes(b'operator edit')
                with self.assertRaises(ValueError):
                    runtime._recover(state, 'sample')
                self.assertEqual(Path(rows[0]['path']).read_bytes(), b'updated')
                self.assertEqual(Path(rows[-1]['path']).read_bytes(), b'operator edit')
                Path(rows[-1]['path']).write_bytes(b'updated')
                runtime._recover(state, 'sample')
                self.assertTrue(all(Path(row['path']).read_bytes() == b'original' for row in rows))
                self.assertNotIn('runtime_refresh', state.state)
                self.assertEqual(state.state['live_unit'], 'old-hash')
