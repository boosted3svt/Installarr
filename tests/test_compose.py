import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from installarr.compose import DATA_TARGETS, application_paths, render_bundle, write_bundle
from test_cli import configuration


def compose_configuration():
    config = configuration()
    config["apps"] = ["sonarr", "radarr"]
    config["storage_mounts"] = {purpose: {"kind": "local"} for purpose in config["storage"]}
    config["storage_checks"] = {purpose: {"mountpoint": "/srv/stack", "source": "nas:/isolated", "fstype": "nfs", "sentinel": "health"}
                                for purpose in DATA_TARGETS}
    return config


class ComposeTests(unittest.TestCase):
    def test_isolated_optional_apps_and_one_case_preserving_map(self):
        config = compose_configuration()
        config["apps"] = ["sonarr"]
        config["storage"]["media"] = "/srv/stack/Media"
        before = copy.deepcopy(config)
        bundle = render_bundle(config)
        self.assertEqual(config, before)
        self.assertEqual(set(bundle["compose"]["services"]), {"sonarr"})
        service = bundle["compose"]["services"]["sonarr"]
        self.assertEqual(service["network_mode"], "none")
        self.assertNotIn("ports", service)
        self.assertNotIn("user", service)  # Preserve /init privilege-drop mechanism.
        self.assertEqual(service["environment"]["PUID"], "2000")
        for volume in service["volumes"]:
            self.assertFalse(volume["bind"]["create_host_path"])
            self.assertEqual(volume["bind"]["propagation"], "rprivate")
        self.assertEqual(application_paths(config, "sonarr")["host_media_root"], "/srv/stack/Media/TV")
        self.assertIn("expected_root=/Media", bundle["guards"]["sonarr.guard.sh"])

    def test_plex_uses_official_identity_and_readonly_media_with_private_claim_path(self):
        config = compose_configuration()
        config['apps'] = ['plex']
        config['plex_claim_file'] = '/private/plex-claim.txt'
        bundle = render_bundle(config)
        service = bundle['compose']['services']['plex']
        self.assertTrue(service['image'].startswith('plexinc/pms-docker@sha256:'))
        self.assertEqual(service['environment']['PLEX_UID'], '2000')
        self.assertNotIn('PUID', service['environment'])
        self.assertNotIn('PLEX_CLAIM', service['environment'])
        self.assertEqual(service['environment']['CHANGE_CONFIG_DIR_OWNERSHIP'], 'false')
        for volume in service['volumes']:
            if volume['target'].startswith('/data/') or volume['target'] == '/run/installarr-plex-claim':
                self.assertTrue(volume['read_only'])
        self.assertIn('matched=yes', bundle['guards']['plex.guard.sh'])
        self.assertNotIn('*,ro,*) deny', bundle['guards']['plex.guard.sh'])

    def test_tautulli_has_no_writable_media_or_download_binds(self):
        config = compose_configuration()
        config['apps'] = ['tautulli']
        service = render_bundle(config)['compose']['services']['tautulli']
        self.assertEqual([v['target'] for v in service['volumes']], ['/config', '/installarr-storage-guard'])
        self.assertEqual(service['environment']['PUID'], '2000')
        self.assertNotIn('ports', service)

    def test_missing_assertions_unsupported_apps_and_nas_databases_refused(self):
        for change in ("sentinel", "unsupported", "database"):
            config = compose_configuration()
            if change == "sentinel":
                del config["storage_checks"]["media"]["sentinel"]
            elif change == "unsupported":
                config["apps"] = ["unimplemented"]
            else:
                config["storage_mounts"]["configs"] = {"kind": "existing", "mountpoint": "/srv/stack",
                                                        "source": "nas:/isolated", "fstype": "nfs"}
            with self.assertRaises(ValueError):
                render_bundle(config)

    def test_dollar_paths_are_literal_in_compose(self):
        config = compose_configuration()
        config["storage"]["media"] = "/srv/stack/$MEDIA"
        volume = render_bundle(config)["compose"]["services"]["sonarr"]["volumes"][1]
        self.assertEqual(volume["source"], "/srv/stack/$$MEDIA")
        if shutil.which("docker"):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "compose.json"
                path.write_text(json.dumps(render_bundle(config)["compose"]))
                result = subprocess.run(["docker", "compose", "--project-name", "installarr-literal-test", "--file", str(path),
                                         "config", "--format", "json"], capture_output=True, text=True, check=True,
                                        env=dict(os.environ, MEDIA="unintended-expansion"), timeout=10)
                model = json.loads(result.stdout)
                sources = [volume["source"] for volume in model["services"]["sonarr"]["volumes"]]
                # `config` emits reusable Compose data, so literal dollars stay
                # escaped in its serialized output. Physical tests verify the
                # actual bind using a NAS directory containing a literal '$'.
                self.assertIn("/srv/stack/$$MEDIA", sources)
                self.assertNotIn("/srv/stack/unintended-expansion", sources)

    def test_bundle_rerun_preserves_files_and_rejects_modified_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            config = compose_configuration()
            config["project_directory"] = directory + "/bundle"
            write_bundle(config)
            path = Path(config["project_directory"]) / "compose.json"
            before = path.stat().st_mtime_ns
            write_bundle(config)
            self.assertEqual(path.stat().st_mtime_ns, before)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.write_text("operator changed this")
            with self.assertRaises(ValueError):
                write_bundle(config)
            self.assertEqual(path.read_text(), "operator changed this")

    def test_sab_pair_uses_only_shared_container_loopback(self):
        config = compose_configuration()
        config['apps'] = ['radarr', 'sabnzbd']
        services = render_bundle(config)['compose']['services']
        self.assertEqual(services['sabnzbd']['network_mode'], 'none')
        self.assertEqual(services['radarr']['network_mode'], 'service:sabnzbd')
        self.assertTrue(services['radarr']['depends_on']['sabnzbd']['restart'])
        self.assertFalse(any(row.get('ports') for row in services.values()))

    def test_explicit_shared_root_uses_one_bind_and_derived_paths(self):
        config = compose_configuration()
        config['data_root'] = '/srv/stack/data'
        for purpose in DATA_TARGETS:
            config['storage'][purpose] = config['data_root'] + '/' + purpose
        bundle = render_bundle(config)
        for app, service in bundle['compose']['services'].items():
            data = [row for row in service['volumes'] if row['target'].startswith('/data')]
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['target'], '/data')
            self.assertEqual(data[0]['source'], '/srv/stack/data')
            self.assertFalse(data[0]['bind']['create_host_path'])
        self.assertEqual(application_paths(config, 'radarr')['media_root'], '/data/media/Movies')
        self.assertIn('probe="$probe"/media', bundle['guards']['radarr.guard.sh'])
        bad = copy.deepcopy(config)
        bad['data_root'] = '/srv/stack'
        with self.assertRaises(ValueError):
            render_bundle(bad)
        bad = copy.deepcopy(config)
        bad['storage_checks']['downloads']['source'] = 'other:/export'
        with self.assertRaises(ValueError):
            render_bundle(bad)
