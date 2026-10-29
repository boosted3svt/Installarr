"""In-memory HTTP verification of the actual host GUI endpoints."""
import base64
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request

from .arr import AppAPIError
from .credentials import validate_credentials


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class HostHTTP:
    def __init__(self, address, port, api_key):
        self.address = '127.0.0.1' if address == '0.0.0.0' else address
        self.port, self.api_key = port, api_key

    def request(self, method, path, data=None, authenticated=True, form=None, basic=None, query=None, opener=None):
        url = 'http://{}:{}{}'.format(self.address, self.port, path)
        if query is not None:
            url += '?' + urllib.parse.urlencode(query)
        headers, body = {}, None
        if authenticated:
            headers[getattr(self, 'api_header', 'X-Api-Key')] = self.api_key
        if basic is not None:
            validate_credentials(basic)
            token = base64.b64encode((basic['username'] + ':' + basic['password']).encode()).decode()
            headers['Authorization'] = 'Basic ' + token
        if form is not None:
            body = urllib.parse.urlencode(form, doseq=True).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        elif data is not None:
            body = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        # Do not inherit operator/environment proxy settings for local verification.
        opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            try:
                response = opener.open(request, timeout=10)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.code, response.read(4194304).decode()
        except (OSError, ValueError):
            raise AppAPIError('Host GUI endpoint unavailable') from None

    def login(self, credentials):
        validate_credentials(credentials)
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPCookieProcessor(jar))
        code, _ = self.request('POST', '/login', authenticated=False,
                               form={'username': credentials['username'], 'password': credentials['password'], 'rememberMe': 'false'}, opener=opener)
        gui, _ = self.request('GET', '/', authenticated=False, opener=opener)
        api, _ = self.request('GET', '/api/v3/system/status', authenticated=False, opener=opener)
        return {'login': code, 'gui': gui, 'api': api}
