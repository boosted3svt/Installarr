import unittest

from installarr.hostplan import collect_shared_storage, collect_storage, preparation_plan, storage_assertions, validate_mounts
from installarr.storage import validate_checks


class HostPlanTests(unittest.TestCase):
    def config(self):
        return {"storage": {"media": "/media/Media/movies", "downloads": "/media/Media/downloads"},
                "storage_mounts": {purpose: {"kind": "nfs", "mountpoint": "/media/Media", "source": "nas:/Public", "fstype": "nfs"}
                                   for purpose in ("media", "downloads")}}

    def test_shared_mount_is_deduplicated(self):
        config = self.config()
        validate_mounts(config)
        result = preparation_plan(config)
        self.assertEqual(len(result["mounts"]), 1)
        self.assertEqual(result["required_storage_packages"], ["nfs-common"])
        self.assertFalse(result["apply_available"])
        self.assertFalse(result["blockers"])

    def test_conflicting_mounts_rejected(self):
        config = self.config()
        config["storage_mounts"]["downloads"]["source"] = "other:/Public"
        with self.assertRaises(ValueError):
            validate_mounts(config)

    def test_existing_and_managed_persistence_choices_cannot_silently_override(self):
        config = self.config()
        config['storage_mounts']['media']['kind'] = 'existing'
        with self.assertRaises(ValueError):
            validate_mounts(config)
        config['storage_mounts'] = dict(reversed(list(config['storage_mounts'].items())))
        with self.assertRaises(ValueError):
            validate_mounts(config)

    def test_directory_outside_mount_rejected(self):
        config = self.config()
        config["storage"]["media"] = "/media/Media-other/movies"
        with self.assertRaises(ValueError):
            validate_mounts(config)

    def test_embedded_smb_password_rejected(self):
        config = {"storage": {"media": "/data/media"}, "storage_mounts": {"media": {
            "kind": "smb", "mountpoint": "/data", "source": "//nas/media", "fstype": "cifs",
            "credentials_file": "/etc/installarr/smb.credentials"}}}
        validate_mounts(config)
        self.assertEqual(preparation_plan(config)["required_storage_packages"], ["cifs-utils"])
        config["storage_mounts"]["media"]["password"] = "dummy"
        with self.assertRaises(ValueError):
            validate_mounts(config)

    def test_inline_network_credentials_and_smb_option_separator_rejected(self):
        for source, kind, fstype in (('user:private@nas:/export', 'nfs', 'nfs'),
                                     ('//user:private@nas/share', 'smb', 'cifs')):
            config = {'storage': {'media': '/data/media'}, 'storage_mounts': {'media': {
                'kind': kind, 'mountpoint': '/data', 'source': source, 'fstype': fstype}}}
            if kind == 'smb':
                config['storage_mounts']['media']['credentials_file'] = '/private/smb.credentials'
            with self.assertRaises(ValueError):
                validate_mounts(config)
        config = {'storage': {'media': '/data/media'}, 'storage_mounts': {'media': {
            'kind': 'smb', 'mountpoint': '/data', 'source': '//nas/share', 'fstype': 'cifs',
            'credentials_file': '/private/unsafe,option.credentials'}}}
        with self.assertRaises(ValueError):
            validate_mounts(config)

    def test_disagreeing_assertions_rejected(self):
        config = self.config()
        config["storage_checks"] = {"media": {"source": "other:/share"}}
        with self.assertRaises(ValueError):
            storage_assertions(config)

    def test_existing_mount_never_requests_persistence_edits(self):
        config = self.config()
        for mount in config["storage_mounts"].values():
            mount["kind"] = "existing"
        result = preparation_plan(config)
        self.assertEqual(result["required_storage_packages"], ["nfs-common"])
        self.assertEqual(result["mounts"][0]["action"], "reuse without editing persistence")

    def test_wizard_collects_nfs_and_generates_checks(self):
        answers = iter(["nfs", "/data/movies", "/data", "nas:/media", "nfs", "ready"])
        paths, mounts = collect_storage(lambda *args: next(answers), ["media"])
        config = {"storage": paths, "storage_mounts": mounts}
        validate_mounts(config)
        checks = storage_assertions(config)
        validate_checks(checks, ["media"])
        self.assertEqual(checks["media"]["sentinel"], "ready")

    def test_shared_wizard_produces_one_mount_and_consistent_app_paths(self):
        from test_cli import configuration
        from installarr.cli import plan, validate
        from installarr.compose import application_paths
        def answer(label, default):
            if label.startswith('Exact mounted source'):
                return 'nas:/test-export'
            return default
        root, paths, mounts, checks = collect_shared_storage(answer)
        config = configuration()
        config.update(apps=['radarr', 'sabnzbd'], data_root=root, storage=paths,
                      storage_mounts=mounts, storage_checks=checks)
        validate(config)
        self.assertEqual(len(preparation_plan(config)['mounts']), 1)
        self.assertEqual(application_paths(config, 'radarr')['media_root'], '/data/Movies')
        self.assertEqual(plan(config)['proposed_container_paths']['incomplete'], '/data/incomplete-downloads')
        self.assertTrue(preparation_plan(config)['reference_apply_available'])

    def test_legacy_paths_require_storage_choices(self):
        config = {"storage": {"media": "/data/media"}}
        self.assertTrue(preparation_plan(config)["blockers"])


if __name__ == "__main__":
    unittest.main()

class IntegrationPlanTests(unittest.TestCase):
    def test_all_reference_adapters_available_without_adding_apps(self):
        from installarr.compose import IMAGES
        from installarr.hostplan import integration_plan
        config = {'apps': list(IMAGES), 'data_root': '/srv/data', 'storage': {}}
        self.assertTrue(preparation_plan(config)['reference_apply_available'])
        links = integration_plan(config)
        self.assertIn({'from': 'ombi', 'to': 'plex', 'purpose': 'availability'}, links['selected_links'])
        self.assertEqual(links['automatic_app_additions'], [])
        self.assertEqual(links['torrent_downloader'], 'not provided')

    def test_optional_apps_report_missing_integrations(self):
        from installarr.hostplan import integration_plan
        report = integration_plan({'apps': ['ombi', 'tautulli', 'jackett']})
        self.assertFalse(report['selected_links'])
        self.assertIn('ombi: no selected request backend', report['operator_inputs'])
        self.assertTrue(any('not a torrent downloader' in row for row in report['operator_inputs']))


class ConfiguredInputDiscoveryTests(unittest.TestCase):
    def test_configured_providers_are_not_reported_as_missing_choices(self):
        from installarr.hostplan import integration_plan
        config = {'apps': ['radarr', 'sabnzbd', 'bazarr'],
                  'providers': {'newshosting': {'connections': 100}, 'nzbgeek': {},
                                'bazarr': {'enabled': ['opensubtitlescom']}},
                  'provider_secrets_file': '/private/providers.json',
                  'bazarr_language_profile': 'english-standard'}
        report = integration_plan(config)
        self.assertEqual(report['operator_inputs'], [])
        self.assertEqual(report['automatic_app_additions'], [])
        config.pop('provider_secrets_file')
        self.assertTrue(any('private credential file required' in s for s in integration_plan(config)['operator_inputs']))
