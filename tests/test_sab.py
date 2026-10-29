import json
import unittest
from unittest.mock import Mock, patch

from installarr.arr import AppAPIError
from installarr.sab import SabClient


class SabTests(unittest.TestCase):
    def test_untested_version_blocks_configuration_writes(self):
        transport = Mock(api_key="a" * 32)
        transport.request.return_value = (200, '{"version":"unreviewed"}')
        with self.assertRaises(AppAPIError):
            SabClient(transport).call("set_config", section="misc", keyword="complete_dir", value="/data/downloads")
        self.assertEqual(transport.request.call_count, 1)
        self.assertEqual(transport.request.call_args.kwargs["form"]["mode"], "version")

    def test_status_true_is_not_setting_readback(self):
        client = SabClient(Mock())
        with patch.object(client, "misc", return_value={"complete_dir": "/wrong"}), patch.object(client, "call", return_value={"status": True}):
            with self.assertRaises(AppAPIError):
                client.set_misc("complete_dir", "/data/downloads")

    def test_boolean_config_readback_is_compared_as_boolean(self):
        client = SabClient(Mock())
        with patch.object(client, "misc", return_value={"html_login": False}), patch.object(client, "call"):
            client.set_misc("html_login", 0)
            with self.assertRaises(AppAPIError):
                client.set_misc("html_login", 1)

    def test_gui_auth_must_reject_anonymous_and_bad_passwords(self):
        transport = Mock()
        client = SabClient(transport)
        credentials = {"username": "example", "password": "synthetic"}
        with patch.object(client, "misc", return_value={"username": "example", "html_login": 0}):
            transport.request.side_effect = [(401, ""), (200, ""), (401, "")]
            self.assertEqual(client.verify_admin(credentials), {"anonymous": 401, "valid": 200, "invalid": 401})
            transport.request.side_effect = [(200, ""), (200, ""), (401, "")]
            with self.assertRaises(AppAPIError):
                client.verify_admin(credentials)

    def test_lazy_default_categories_initialized_before_custom_paths(self):
        client = SabClient(Mock())
        categories = {}
        def call(mode, **values):
            if mode == "get_cats":
                categories.update({"tv": "", "movies": "", "*": ""})
            elif mode == "set_config":
                categories[values["name"]] = values["dir"]
            return {"config": {"categories": [{"name": key, "dir": value} for key, value in categories.items()]}}
        paths = {"incomplete_directory": "/data/incomplete", "download_directory": "/data/downloads"}
        with patch("installarr.sab.application_paths", return_value=paths), patch.object(client, "set_misc"), patch.object(client, "misc", return_value={"download_dir": "/data/incomplete", "complete_dir": "/data/downloads"}), patch.object(client, "call", side_effect=call):
            client.configure_storage({})
        self.assertEqual(categories, {"*": "", "tv": "tv", "movies": "movies"})

    def test_unsupported_shared_username_refused_before_app_mutation(self):
        client = SabClient(Mock())
        with patch.object(client, "set_misc") as setting:
            with self.assertRaises(AppAPIError):
                client.configure_admin({"username": "not:valid-for-basic", "password": "synthetic"})
            setting.assert_not_called()
