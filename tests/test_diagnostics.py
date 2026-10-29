import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from installarr.arr import AppAPIError, ArrClient
from installarr.cli import main
from installarr.compose import IMAGES
from test_reference import reference_configuration


class DiagnosticTests(unittest.TestCase):
    def run_failure(self, error):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'config.json'
            config.write_text(json.dumps(reference_configuration()))
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), patch('installarr.reference.apply_reference', side_effect=error):
                code = main(['apply', '--reference', '--config', str(config), '--name', 'diagnostic-test',
                             '--state-directory', str(root / 'state')])
            self.assertEqual(code, 1)
            return output.getvalue()

    def test_fixed_application_diagnostic_visible_arbitrary_exception_text_hidden(self):
        message = 'Newshosting TLS/authentication test failed; no provider setting saved'
        self.assertIn(message, self.run_failure(AppAPIError(message)))
        for error in (ValueError('private-provider-password'), OSError('private-provider-password')):
            output = self.run_failure(error)
            self.assertNotIn('private-provider-password', output)
            self.assertIn(type(error).__name__, output)

    def test_untrusted_http_response_body_never_reaches_cli_diagnostic(self):
        class Transport:
            def request(self, *args, **kwargs):
                return 401, json.dumps({'error': 'private-provider-password', 'apiKey': 'z' * 32})
        client = ArrClient(Transport(), IMAGES['radarr']['version'].split('-ls', 1)[0])
        try:
            client.json('GET', 'system/status')
        except AppAPIError as error:
            output = self.run_failure(error)
        else:
            self.fail('Rejected HTTP response was accepted')
        self.assertIn('HTTP 401', output)
        self.assertNotIn('private-provider-password', output)
        self.assertNotIn('z' * 32, output)
