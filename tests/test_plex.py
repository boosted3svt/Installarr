import os
from pathlib import Path
import tempfile
import unittest

from installarr.arr import AppAPIError
from installarr.plex import PlexClient, VERSION, read_claim_file, store_claim


class PlexTests(unittest.TestCase):
    def test_claim_private_retained_and_explicit_replacement_without_secret_in_result(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'claims'
            first = store_claim(target, lambda: 'claim-synthetic-token-1234')
            path = target / 'plex-claim.txt'
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(read_claim_file(path), 'claim-synthetic-token-1234')
            self.assertNotIn('synthetic', repr(first))
            self.assertEqual(store_claim(target, lambda: self.fail('must retain'))['status'], 'retained')
            store_claim(target, lambda: 'claim-new-synthetic-1234', replace=True)
            self.assertEqual(read_claim_file(path), 'claim-new-synthetic-1234')
            path.chmod(0o644)
            with self.assertRaises(AppAPIError):
                read_claim_file(path)

    def test_unclaimed_server_and_wrong_version_never_satisfy_authorization(self):
        class Transport:
            api_key = ''
            def request(self, *args, **kwargs):
                return 200, '<MediaContainer version="{}" machineIdentifier="fixture" claimed="0"/>'.format(VERSION)
        client = PlexClient(Transport())
        self.assertFalse(client.status()['claimed'])
        with self.assertRaises(AppAPIError):
            client.verify_authorization()

    def test_cold_plex_requests_have_a_longer_but_bounded_deadline(self):
        from unittest.mock import Mock, patch
        from installarr.plex import PlexHTTP
        transport = PlexHTTP('unix:///run/docker.sock', 'c' * 64, api_key='t' * 24)
        with patch('subprocess.run', return_value=Mock(returncode=0, stdout='ready\n200')) as run:
            self.assertEqual(transport.request('GET', '/system/agents'), (200, 'ready'))
        command = run.call_args.args[0]
        self.assertEqual(command[command.index('--max-time') + 1], '60')
        self.assertEqual(run.call_args.kwargs['timeout'], 65)

    def test_agent_discovery_retries_only_transient_readiness_failure(self):
        from unittest.mock import Mock, patch
        from installarr.plex import read_agents_when_ready
        client = Mock(); client.xml.side_effect = [AppAPIError('Application request failed'), 'agents']
        with patch('time.sleep'):
            self.assertEqual(read_agents_when_ready(client), 'agents')
        self.assertEqual(client.xml.call_count, 2)
        client = Mock();client.xml.side_effect = AppAPIError('Plex API rejected request (HTTP 401)')
        with self.assertRaises(AppAPIError): read_agents_when_ready(client)
        self.assertEqual(client.xml.call_count, 1)
        client = Mock();client.xml.side_effect = AppAPIError('Application request failed')
        with self.assertRaisesRegex(AppAPIError, 'rerun setup'):
            read_agents_when_ready(client, seconds=0)

    def test_library_startup_refusal_retries_until_ready(self):
        from unittest.mock import Mock, patch
        from installarr.plex import write_library_request
        transport = Mock()
        transport.request.side_effect = [(400, 'the server is still starting up. Please retry later\n'), (201, '<created/>')]
        with patch('time.sleep'):
            self.assertEqual(write_library_request(transport, 'POST', '/library/sections', [('name', 'Movies')]), 201)
        self.assertEqual(transport.request.call_count, 2)

    def test_library_validation_error_is_not_retried(self):
        from unittest.mock import Mock
        from installarr.plex import write_library_request
        transport = Mock();transport.request.return_value = (400, "'language' is invalid")
        self.assertEqual(write_library_request(transport, 'POST', '/library/sections', []), 400)
        self.assertEqual(transport.request.call_count, 1)

    def test_library_startup_deadline_has_safe_resumable_error(self):
        from unittest.mock import Mock
        from installarr.plex import write_library_request
        transport = Mock();transport.request.return_value = (400, 'the server is still starting up. Please retry later')
        with self.assertRaisesRegex(AppAPIError, 'rerun setup'):
            write_library_request(transport, 'POST', '/library/sections', [], seconds=0)
        self.assertEqual(transport.request.call_count, 1)

    def test_reference_paths_are_relative_unique_and_reject_escape(self):
        from installarr.plex import reference_libraries, library_paths, validate_libraries
        config = {'apps': ['plex'], 'storage': {'media': '/media/test'}, 'plex_libraries': reference_libraries()}
        rows = library_paths(config)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]['host_path'], '/media/test/Movies')
        self.assertEqual([row['relative_paths'] for row in rows if row['name'] == 'sports'], [['sports']])
        config['plex_libraries'][0]['relative_paths'][0] = '../other'
        with self.assertRaises(ValueError):
            validate_libraries(config)

    def test_existing_library_path_conflict_refuses_before_mutation(self):
        import xml.etree.ElementTree as ET
        from unittest.mock import Mock
        from installarr.plex import configure_server
        client = Mock()
        client.xml.side_effect = [ET.fromstring('<MediaContainer><Agent identifier="tv.plex.agents.movie"><Language code="en-US"/></Agent></MediaContainer>'),
            ET.fromstring('<MediaContainer><Directory title="Movies" type="movie" agent="tv.plex.agents.movie"><Location path="/data/operator-movies"/></Directory></MediaContainer>')]
        config = {'apps': ['plex'], 'storage': {'media': '/media/test'}, 'plex_libraries': [
            {'name': 'Movies', 'type': 'movie', 'relative_path': 'Movies', 'language': 'en-US'}]}
        with self.assertRaises(AppAPIError):
            configure_server(client, config)
        client.transport.request.assert_not_called()

    def test_adds_folders_to_one_existing_library_using_repeated_location_parameters(self):
        import xml.etree.ElementTree as ET
        from unittest.mock import Mock
        from installarr.plex import configure_server
        client = Mock()
        agent = ET.fromstring('<MediaContainer><Agent identifier="tv.plex.agents.series"><Language code="en-US"/></Agent></MediaContainer>')
        def section(paths):
            return ET.fromstring('<MediaContainer><Directory key="42" title="TV" type="show" agent="tv.plex.agents.series" scanner="Plex TV Series" language="en-US">' +
                ''.join('<Location path="' + p + '"/>' for p in paths) + '</Directory></MediaContainer>')
        paths = ['/data/media/TV', '/data/media/lenoratv', '/data/media/jeremytv']
        client.xml.side_effect = [agent, section(paths[:1]), section(paths), ET.fromstring('<MediaContainer friendlyName="test"/>')]
        client.transport.request.return_value = (200, '')
        config = {'apps': ['plex'], 'storage': {'media': '/media/test'}, 'plex_libraries': [
            {'name': 'TV', 'type': 'show', 'relative_paths': ['TV', 'lenoratv', 'jeremytv'], 'language': 'en-US'}]}
        result = configure_server(client, config)
        args, kwargs = client.transport.request.call_args
        self.assertEqual(args, ('PUT', '/library/sections/42'))
        self.assertEqual([value for key, value in kwargs['query'] if key == 'location'], paths)
        self.assertEqual(len(result['libraries']), 1)
        self.assertEqual(result['libraries'][0]['id'], '42')
        self.assertEqual(result['libraries'][0]['paths'], paths)

    def test_removed_libraries_lowres_and_mismatched_conventions_are_refused(self):
        from installarr.plex import validate_libraries
        for name, paths in [('Disney', ['Disney']), ('Only Heather', ['Only_Heather']),
                            ('YouTube Videos', ['yt-videos']), ('TubeSync Videos', ['tubesync_downloads/video']),
                            ('sports', ['sport']), ('Sports', ['sports']), ('StandUp', ['comedy']),
                            ('TV', ['TV', 'low-res-TV'])]:
            with self.subTest(name=name, paths=paths), self.assertRaises(ValueError):
                validate_libraries({'apps': ['plex'], 'plex_libraries': [
                    {'name': name, 'type': 'other', 'relative_paths': paths, 'language': 'en-US'}]})

class LibraryWizardTests(unittest.TestCase):
    def test_defaults_keep_grouped_reference_libraries(self):
        from installarr.plex import collect_libraries, reference_libraries
        self.assertEqual(collect_libraries(lambda label, default: default), reference_libraries())

    def test_selective_groups_and_edited_locations(self):
        from installarr.plex import collect_libraries
        def ask(label, default):
            if label.startswith('Include all'):
                return 'no'
            if label.startswith('Include Plex library '):
                return 'yes' if 'Movies?' in label or 'TV?' in label else 'no'
            if label.startswith('Edit Plex'):
                return 'yes'
            if label.startswith('Folders for Movies'):
                return 'Movies,Movies-2'
            return default
        selected = collect_libraries(ask)
        self.assertEqual([item['name'] for item in selected], ['Movies', 'TV'])
        self.assertEqual(selected[0]['relative_paths'], ['Movies', 'Movies-2'])
        self.assertEqual(len(selected[1]['relative_paths']), 3)


class PrivateClaimOutputTests(unittest.TestCase):
    def test_unattended_claim_uses_configured_filename_without_echo(self):
        import contextlib
        import io
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from installarr.cli import main
        from installarr.plex import read_claim_file
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.txt'
            token = 'claim-abcdefghijklmnop'
            source.write_text(token + '\n'); source.chmod(0o600)
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), patch('installarr.cli.getpass.getpass') as prompt:
                self.assertEqual(main(['init-plex-claim', '--secrets-directory', str(root / 'secrets'),
                    '--claim-file', str(source), '--filename', 'private-claim.token']), 0)
                prompt.assert_not_called()
            self.assertEqual(read_claim_file(root / 'secrets/private-claim.token'), token)
            self.assertNotIn(token, output.getvalue())
            self.assertFalse((root / 'secrets/plex-claim.txt').exists())
