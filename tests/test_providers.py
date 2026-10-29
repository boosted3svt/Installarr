import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from installarr.arr import AppAPIError
from installarr.provider_secrets import initialize_provider_secrets, read_provider_secrets
from installarr.providers import SUBTITLES, newshosting, nzbgeek, validate_providers


class ProviderSecretsTests(unittest.TestCase):
    def test_private_store_reruns_and_checkpoint_excludes_values(self):
        with tempfile.TemporaryDirectory() as directory:
            values = {'newshosting': {'username': 'synthetic-account', 'password': 'synthetic-secret'},
                      'nzbgeek': {'api_key': 'a' * 32}, 'opensubtitlescom': {'username': 'synthetic-subtitle', 'password': 'private-subtitle'}}
            target = Path(directory) / 'secrets'
            result = initialize_provider_secrets(target, list(values), values.__getitem__)
            self.assertEqual(read_provider_secrets(result['path']), values)
            self.assertEqual(Path(result['path']).stat().st_mode & 0o777, 0o600)
            self.assertEqual(initialize_provider_secrets(target, list(values), lambda name: self.fail('must reuse'))['status'], 'reused')
            self.assertTrue(list(target.rglob('state.json')))
            self.assertTrue(all('synthetic-secret' not in state.read_text() for state in target.rglob('state.json')))
            self.assertNotIn('a' * 32, repr(result))
            Path(result['path']).chmod(0o644)
            with self.assertRaises(ValueError):
                read_provider_secrets(result['path'])

    def test_only_opensubtitles_com_is_offered_and_retired_choices_refused(self):
        self.assertEqual(SUBTITLES, ('opensubtitlescom',))
        for name in ('yifysubtitles', 'supersubtitles', 'tvsubtitles'):
            with self.assertRaises(ValueError):
                validate_providers({'apps': ['bazarr'], 'providers': {
                    'bazarr': {'enabled': ['opensubtitlescom', name]}}})

    def test_selection_rejects_embedded_credentials_and_bad_connection_limits(self):
        config = {'apps': ['sabnzbd', 'radarr', 'bazarr'], 'providers': {
            'newshosting': {'connections': 100}, 'nzbgeek': {}, 'bazarr': {'enabled': list(SUBTITLES)}}}
        validate_providers(config)
        for value in (0, 101, True):
            broken = copy.deepcopy(config)
            broken['providers']['newshosting']['connections'] = value
            with self.assertRaises(ValueError):
                validate_providers(broken)
        config['providers']['nzbgeek']['api_key'] = 'never-in-config'
        with self.assertRaises(ValueError):
            validate_providers(config)


class Sab:
    def __init__(self, accepted=True):
        self.rows, self.writes, self.accepted = {}, 0, accepted
    def misc(self):
        return {'api_logging': 0}
    def call(self, mode, **parameters):
        if mode == 'get_config':
            return {'config': {'servers': copy.deepcopy(self.rows)}} if self.rows else {'config': {}}
        if mode == 'config':
            return {'value': {'result': self.accepted}}
        if mode == 'set_config':
            self.writes += 1
            name = parameters.pop('name')
            parameters.pop('section')
            self.rows[name] = dict(parameters, ssl=bool(parameters['ssl']), enable=bool(parameters['enable']))
            return {'config': {}}
        raise AssertionError(mode)


class Arr:
    def __init__(self, accepted=True):
        self.rows, self.creates, self.accepted = {}, 0, accepted
    def json(self, method, endpoint, payload=None):
        if endpoint == 'indexer/schema':
            return [{'implementation': 'Newznab', 'fields': [{'name': key, 'value': None} for key in ('baseUrl', 'apiPath', 'apiKey', 'categories')]}]
        if endpoint == 'indexer/test':
            if not self.accepted:
                raise AppAPIError('synthetic test rejected')
            return []
        if endpoint == 'indexer' and method == 'GET':
            return copy.deepcopy(list(self.rows.values()))
        if method == 'POST':
            self.creates += 1
            self.rows[23] = dict(copy.deepcopy(payload), id=23)
            return copy.deepcopy(self.rows[23])
        if method == 'PUT':
            self.rows[23] = copy.deepcopy(payload)
        return copy.deepcopy(self.rows[23])


class ProviderAdapterTests(unittest.TestCase):
    def test_sab_tls100_readback_and_failed_test_precedes_save(self):
        sab = Sab()
        credentials = {'username': 'synthetic', 'password': 'private-test-password'}
        result = newshosting(sab, credentials, 100)
        newshosting(sab, credentials, 100)
        self.assertEqual(len(sab.rows), 1)
        self.assertEqual(result['connections'], 100)
        self.assertEqual(result['ssl_verify'], 3)
        self.assertNotIn('private-test-password', repr(result))
        failed = Sab(accepted=False)
        with self.assertRaises(AppAPIError):
            newshosting(failed, credentials)
        self.assertEqual(failed.writes, 0)
        validate_only = Sab()
        self.assertFalse(newshosting(validate_only, credentials, save=False)['saved'])
        self.assertEqual(validate_only.writes, 0)

    def test_indexer_dynamic_id_categories_and_validation_only(self):
        for app, category in (('radarr', 2000), ('sonarr', 5000)):
            arr = Arr()
            result = nzbgeek(arr, app, {'api_key': 'a' * 32})
            nzbgeek(arr, app, {'api_key': 'a' * 32})
            self.assertEqual(arr.creates, 1)
            self.assertEqual(result['id'], 23)
            self.assertEqual(result['categories'], [category])
            self.assertNotIn('a' * 32, repr(result))
        failed = Arr(accepted=False)
        with self.assertRaises(AppAPIError):
            nzbgeek(failed, 'radarr', {'api_key': 'a' * 32})
        self.assertEqual(failed.creates, 0)
        validate_only = Arr()
        nzbgeek(validate_only, 'radarr', {'api_key': 'a' * 32}, save=False)
        self.assertEqual(validate_only.creates, 0)

class ProviderCLITests(unittest.TestCase):
    def test_hidden_cli_collection_keeps_values_out_of_output(self):
        from unittest.mock import patch
        from installarr.cli import main
        with tempfile.TemporaryDirectory() as directory:
            with patch('installarr.cli.sys.stdin.isatty', return_value=True), patch('installarr.cli.getpass.getpass',
                       side_effect=['private-user', 'private-password', 'b' * 32]), patch('builtins.print') as output:
                self.assertEqual(main(['init-provider-secrets', '--secrets-directory', str(Path(directory) / 'secrets'),
                                       '--providers', 'newshosting,nzbgeek']), 0)
                rendered = repr(output.call_args_list)
                self.assertNotIn('private-user', rendered)
                self.assertNotIn('private-password', rendered)
                self.assertNotIn('b' * 32, rendered)
            self.assertEqual(set(read_provider_secrets(Path(directory) / 'secrets/providers.json')), {'newshosting', 'nzbgeek'})

    def test_unattended_private_import_never_prompts_or_exposes_values(self):
        from unittest.mock import patch
        from installarr.cli import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = {'newshosting': {'username': 'synthetic-unattended', 'password': 'private-unattended'},
                      'nzbgeek': {'api_key': 'c' * 32}}
            source = root / 'input.json'
            source.write_text(json.dumps(values)); source.chmod(0o600)
            with patch('installarr.cli.sys.stdin.isatty', return_value=False), patch('installarr.cli.getpass.getpass') as prompt, patch('builtins.print') as output:
                self.assertEqual(main(['init-provider-secrets', '--secrets-directory', str(root / 'secrets'),
                    '--providers', 'newshosting', '--credentials-file', str(source)]), 0)
                prompt.assert_not_called()
                rendered = repr(output.call_args_list)
                self.assertNotIn('synthetic-unattended', rendered)
                self.assertNotIn('private-unattended', rendered)
                self.assertNotIn('c' * 32, rendered)
            self.assertEqual(read_provider_secrets(root / 'secrets/providers.json'), {'newshosting': values['newshosting']})
            source.chmod(0o644)
            with patch('builtins.print'):
                self.assertEqual(main(['init-provider-secrets', '--secrets-directory', str(root / 'rejected'),
                    '--providers', 'nzbgeek', '--credentials-file', str(source)]), 1)
            self.assertFalse((root / 'rejected').exists())

    def test_custom_private_output_filename_matches_unattended_config(self):
        from unittest.mock import patch
        from installarr.cli import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps({'nzbgeek': {'api_key': 'd' * 32}})); source.chmod(0o600)
            with patch('builtins.print'):
                self.assertEqual(main(['init-provider-secrets', '--secrets-directory', str(root / 'secrets'),
                    '--providers', 'nzbgeek', '--credentials-file', str(source), '--filename', 'provider-keys.json']), 0)
            self.assertEqual(read_provider_secrets(root / 'secrets/provider-keys.json'), {'nzbgeek': {'api_key': 'd' * 32}})
            self.assertFalse((root / 'secrets/providers.json').exists())
