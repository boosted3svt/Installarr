import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from installarr.accounts import HostPrerequisiteError
from installarr.dockerhost import KEY_FINGERPRINT, ensure_file, repository_text, select_version, verify_key


class DockerHostTests(unittest.TestCase):
    def test_repository_is_signed_and_release_specific(self):
        source = repository_text("jammy", "amd64").decode()
        self.assertIn("Suites: jammy\n", source)
        self.assertIn("Signed-By: /etc/apt/keyrings/installarr-docker.asc", source)
        self.assertNotIn("trusted", source)
        self.assertIn("Suites: focal\n", repository_text("focal", "amd64").decode())
        for codename, architecture in (("unknown", "amd64"), ("jammy", "untrusted\nfield"), ("focal", "arm64")):
            with self.assertRaises(HostPrerequisiteError):
                repository_text(codename, architecture)

    def test_versions_selected_only_from_official_repository(self):
        output = "docker-ce | 999:bad | https://untrusted.invalid repo\n"
        output += "docker-ce | 5:29.8.2-1~ubuntu.22.04~jammy | https://download.docker.com/linux/ubuntu jammy/stable amd64 Packages\n"
        self.assertEqual(select_version(output), "5:29.8.2-1~ubuntu.22.04~jammy")
        with self.assertRaises(HostPrerequisiteError):
            select_version("docker-ce | 123 | https://untrusted.invalid repo")

    def test_changed_or_additional_signing_key_refused(self):
        fingerprint = "fpr:::::::::" + KEY_FINGERPRINT + ":"
        verify_key("synthetic", Mock(return_value="pub:::::::::\n" + fingerprint))
        for output in ("pub:::::::::\nfpr:::::::::WRONG:",
                       "pub:::::::::\n" + fingerprint + "\npub:::::::::\n" + fingerprint):
            with self.assertRaises(HostPrerequisiteError):
                verify_key("synthetic", Mock(return_value=output))


@unittest.skipUnless(os.geteuid() == 0, "System file ownership checks require root")
class RootFileTests(unittest.TestCase):
    def test_existing_changed_file_and_symlink_preserved(self):
        # /var/tmp itself is writable, so use a trusted root directory under /run.
        with tempfile.TemporaryDirectory(prefix="installarr-file-test-", dir="/run") as directory:
            path = Path(directory) / "source"
            ensure_file(path, b"original")
            ensure_file(path, b"original")
            with self.assertRaises(HostPrerequisiteError):
                ensure_file(path, b"replacement")
            self.assertEqual(path.read_bytes(), b"original")
            link = Path(directory) / "link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                ensure_file(link, b"original")
            link.unlink()
            os.link(path, link)
            with self.assertRaises(HostPrerequisiteError):
                ensure_file(path, b"original")
            self.assertEqual(path.read_bytes(), b"original")
            self.assertEqual(link.stat().st_ino, path.stat().st_ino)


    def test_concurrent_identical_publication_reuses_only_verified_content(self):
        import concurrent.futures
        import threading
        from installarr.atomic import publish_noreplace
        real_link = publish_noreplace
        barrier = threading.Barrier(6)
        with tempfile.TemporaryDirectory(prefix="installarr-file-race-", dir="/run") as directory:
            path = Path(directory) / 'shared-runtime.py'
            def publish(source, target):
                barrier.wait(timeout=10)
                return real_link(source, target)
            with patch('installarr.dockerhost.publish_noreplace', side_effect=publish):
                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                    results = list(pool.map(lambda unused: ensure_file(path, b'identical runtime'), range(6)))
            self.assertEqual(results, [None] * 6)
            self.assertEqual(path.read_bytes(), b'identical runtime')
            self.assertEqual(list(Path(directory).iterdir()), [path])
            with self.assertRaises(HostPrerequisiteError):
                ensure_file(path, b'different runtime')
