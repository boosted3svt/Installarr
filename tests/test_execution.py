import json
import os
from pathlib import Path
import tempfile
import unittest

from installarr.execution import Execution


class ExecutionTests(unittest.TestCase):
    def test_failed_attempt_resumes_and_completed_attempt_rechecks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state"
            with Execution(path, {"operation": "example"}) as execution:
                with self.assertRaises(RuntimeError):
                    execution.reconcile("account", lambda: (_ for _ in ()).throw(RuntimeError("secret")))
            saved = json.loads((path / "state.json").read_text())
            self.assertEqual(saved["steps"]["account"], "failed")
            self.assertNotIn("secret", (path / "state.json").read_text())
            calls = []
            for _ in range(2):
                with Execution(path, {"operation": "example"}) as execution:
                    execution.reconcile("account", lambda: calls.append(True))
            self.assertEqual(len(calls), 2)
            self.assertEqual(json.loads((path / "state.json").read_text())["steps"]["account"], "verified")
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            self.assertEqual((path / "state.json").stat().st_mode & 0o777, 0o600)

    def test_changed_operation_and_concurrent_execution_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state"
            with Execution(path, {"uid": 2000}) as execution:
                execution.reconcile("account", lambda: None)
                with self.assertRaises(BlockingIOError):
                    with Execution(path, {"uid": 2000}):
                        self.fail("Acquired held lock")
            with self.assertRaises(ValueError):
                with Execution(path, {"uid": 2001}):
                    self.fail("Accepted changed identity")

    def test_interrupted_running_step_reconciles(self):
        with tempfile.TemporaryDirectory() as directory:
            with Execution(Path(directory) / "state", {}) as execution:
                execution.state["steps"]["account"] = "running"
                execution._save()
            with Execution(Path(directory) / "state", {}) as execution:
                execution.reconcile("account", lambda: None)
                self.assertEqual(execution.state["steps"]["account"], "verified")

    def test_symlink_and_public_directory_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state"
            path.mkdir(mode=0o755)
            with self.assertRaises(ValueError):
                with Execution(path, {}):
                    self.fail("Accepted public directory")
            os.chmod(path, 0o700)
            link = Path(directory) / "link"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                with Execution(link, {}):
                    self.fail("Accepted symlink")
            (path / "state.json").symlink_to(Path(directory) / "elsewhere")
            with self.assertRaises(OSError):
                with Execution(path, {}):
                    self.fail("Accepted checkpoint symlink")

    def test_fifo_checkpoint_refused_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state"
            path.mkdir(mode=0o700)
            os.mkfifo(path / "state.json", mode=0o600)
            with self.assertRaises(ValueError):
                with Execution(path, {}):
                    self.fail("Accepted FIFO checkpoint")


    def test_directory_creation_race_cannot_redirect_private_state(self):
        from unittest.mock import patch
        from installarr.execution import private_directory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / 'intended'
            other = root / 'unrelated'
            other.mkdir(mode=0o700)
            def raced_mkdir(path, *args, **kwargs):
                self.assertEqual(path, destination)
                path.symlink_to(other, target_is_directory=True)
            with patch('pathlib.Path.mkdir', new=raced_mkdir):
                with self.assertRaises(ValueError):
                    private_directory(destination)
            self.assertEqual(list(other.iterdir()), [])
