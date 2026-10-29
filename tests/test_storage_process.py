import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from installarr.storage_process import run_storage, StorageProcessError


class StorageProcessTests(unittest.TestCase):
    def test_normal_and_failed_worker_return_output_without_secret_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / 'registry'
            result = run_storage([sys.executable, '-c', 'import sys;print(sys.stdin.read());sys.exit(3)'],
                                 input='synthetic-private-input', registry=registry)
            self.assertEqual(result.returncode, 3)
            self.assertIn('synthetic-private-input', result.stdout)
            state = json.loads((registry / 'state.json').read_text())
            self.assertNotIn('pending', state)
            self.assertNotIn('synthetic-private-input', json.dumps(state))

    def test_timeout_reaps_interruptible_worker_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / 'registry'
            with self.assertRaises(StorageProcessError):
                run_storage([sys.executable, '-c', 'import time;time.sleep(60)'], timeout=0.15, registry=registry)
            result = run_storage([sys.executable, '-c', 'print("recovered")'], registry=registry)
            self.assertEqual(result.stdout.strip(), 'recovered')
            self.assertNotIn('pending', json.loads((registry / 'state.json').read_text()))

    def test_unreaped_group_blocks_new_worker_until_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / 'registry'
            pid = None
            try:
                with self.assertRaises(StorageProcessError):
                    run_storage([sys.executable, '-c', 'import os,signal,time;os.kill(os.getpid(),signal.SIGSTOP);time.sleep(60)'],
                                timeout=0.15, registry=registry, terminate=lambda process: None)
                pending = json.loads((registry / 'state.json').read_text())['pending']
                pid = pending['pid']
                with patch('installarr.storage_process.subprocess.Popen') as spawn:
                    with self.assertRaises(StorageProcessError):
                        run_storage([sys.executable, '-c', 'print("must not run")'], registry=registry)
                    spawn.assert_not_called()
                # A separate CLI process must see the durable refusal too.
                code = ('from pathlib import Path; import sys; '
                        'from installarr.storage_process import run_storage,StorageProcessError\n'
                        'try: run_storage([sys.executable,"-c","print(123)"],registry=Path(sys.argv[1]))\n'
                        'except StorageProcessError: print("blocked");sys.exit(0)\n'
                        'raise SystemExit(9)')
                other = subprocess.run([sys.executable, '-c', code, str(registry)],
                                       capture_output=True, text=True, timeout=5)
                self.assertEqual(other.returncode, 0, other.stderr)
                self.assertEqual(other.stdout.strip(), 'blocked')
                os.killpg(pid, signal.SIGKILL)
                end = time.monotonic() + 3
                while time.monotonic() < end:
                    try:
                        waited, _ = os.waitpid(pid, os.WNOHANG)
                        if waited:
                            break
                    except ChildProcessError:
                        break
                    time.sleep(0.01)
                result = run_storage([sys.executable, '-c', 'print("recovered")'], registry=registry)
                self.assertEqual(result.stdout.strip(), 'recovered')
            finally:
                if pid:
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    try:
                        os.waitpid(pid, os.WNOHANG)
                    except ChildProcessError:
                        pass
