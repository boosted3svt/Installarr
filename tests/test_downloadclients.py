import copy
import unittest
from unittest.mock import Mock, patch

from installarr.arr import AppAPIError
from installarr.downloadclients import NAME, ensure_sabnzbd


class DownloaderTests(unittest.TestCase):
    def client(self):
        client = Mock(expected_version="6.4.4.10685")
        schema = {"implementation": "Sabnzbd", "fields": [{"name": name, "value": None} for name in
                  ("host", "port", "useSsl", "urlBase", "apiKey", "username", "password", "movieCategory")]}
        saved = {}
        def request(method, endpoint, payload=None):
            if endpoint == "downloadclient/schema":
                return [copy.deepcopy(schema)]
            if endpoint == "downloadclient" and method == "GET":
                return [copy.deepcopy(saved)] if saved else []
            if endpoint == "downloadclient/test":
                if next(field["value"] for field in payload["fields"] if field["name"] == "apiKey") != "a" * 32:
                    raise AppAPIError("Rejected")
                return []
            if endpoint == "downloadclient" and method == "POST":
                saved.update(copy.deepcopy(payload), id=17)
                return copy.deepcopy(saved)
            if endpoint == "downloadclient/17" and method == "GET":
                return copy.deepcopy(saved)
            raise AssertionError("Unexpected mutation or endpoint")
        client.json.side_effect = request
        return client, saved

    @patch("installarr.downloadclients.application_paths", return_value={"download_category": "movies"})
    def test_real_validation_before_save_and_idempotent_dynamic_id(self, paths):
        client, saved = self.client()
        first = ensure_sabnzbd(client, {}, "radarr", "a" * 32)
        self.assertEqual(first["id"], 17)
        self.assertEqual(first, ensure_sabnzbd(client, {}, "radarr", "a" * 32))
        before = copy.deepcopy(saved)
        with self.assertRaises(AppAPIError):
            ensure_sabnzbd(client, {}, "radarr", "b" * 32)
        self.assertEqual(saved, before)
        self.assertEqual(sum(call.args[:2] == ("POST", "downloadclient") for call in client.json.call_args_list), 1)

    @patch("installarr.downloadclients.application_paths", return_value={"download_category": "movies"})
    def test_conflicting_implementation_preserved(self, paths):
        client, saved = self.client()
        saved.update(name=NAME, implementation="AnotherClient")
        with self.assertRaises(AppAPIError):
            ensure_sabnzbd(client, {}, "radarr", "a" * 32)
        self.assertFalse(any(call.args[0] != "GET" for call in client.json.call_args_list))

    def test_wrong_app_version_blocks_even_schema_access(self):
        client = Mock(expected_version="unreviewed")
        with self.assertRaises(AppAPIError):
            ensure_sabnzbd(client, {}, "radarr", "a" * 32)
        client.json.assert_not_called()

    @patch("installarr.downloadclients.application_paths", return_value={"download_category": "movies"})
    def test_operator_endpoint_change_preserved_without_testing_or_writing(self, paths):
        client, saved = self.client()
        ensure_sabnzbd(client, {}, "radarr", "a" * 32)
        for field in saved["fields"]:
            if field["name"] == "host":
                field["value"] = "operator-host"
        client.json.reset_mock()
        before = copy.deepcopy(saved)
        with self.assertRaises(AppAPIError):
            ensure_sabnzbd(client, {}, "radarr", "a" * 32)
        self.assertEqual(saved, before)
        self.assertTrue(all(call.args[0] == "GET" for call in client.json.call_args_list))
