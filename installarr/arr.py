"""Narrow Sonarr/Radarr v3 API reconciliation with strict readback.

Transport errors never include response bodies, credentials or API keys.
"""
import copy
import base64
import json
import re
import subprocess
import uuid
from urllib.parse import urlencode

from .credentials import validate_credentials
from .compose import IMAGES

SUPPORTED_VERSIONS = {IMAGES[app]["version"].split("-ls", 1)[0] for app in ("sonarr", "radarr")}


class AppAPIError(ValueError):
    """Public application diagnostic: never include credentials or response bodies."""


class DockerHTTP:
    def __init__(self, socket, container, port, api_key):
        if (not isinstance(container, str) or not isinstance(api_key, str)
                or not re.fullmatch(r"[0-9a-f]{64}", container)
                or not re.fullmatch(r"[A-Za-z0-9]{32}" if port == 9117 else r"[0-9a-fA-F]{32}", api_key)):
            raise AppAPIError("Invalid application transport identity")
        if socket not in ("unix:///run/installarr-docker-test/docker.sock", "unix:///run/docker.sock") or port not in (8989, 7878, 8080, 6767, 9117, 8181):
            raise AppAPIError("Only tested local Docker app transports are enabled")
        self.socket, self.container, self.port, self.api_key = socket, container, port, api_key

    def request(self, method, path, data=None, authenticated=True, form=None, cookie=None, save_cookie=False, basic=None, query=None):
        if method not in ("GET", "POST", "PUT", "DELETE") or not re.fullmatch(r"/[A-Za-z0-9/_.:-]*", path) or ".." in path.split("/"):
            raise AppAPIError("Unsupported application request")
        options = {"url": "http://127.0.0.1:{}{}".format(self.port, path), "request": method}
        if query is not None:
            options["url"] += "?" + urlencode(query)
        lines = [key + " = " + json.dumps(value, ensure_ascii=False) for key, value in options.items()]
        if authenticated:
            lines.append("header = " + json.dumps(getattr(self, "api_header", "X-Api-Key") + ": " + self.api_key))
        if basic is not None:
            validate_credentials(basic)
            if ":" in basic["username"]:
                raise AppAPIError("Basic-auth username cannot contain a colon")
            value = base64.b64encode((basic["username"] + ":" + basic["password"]).encode()).decode()
            lines.append("header = " + json.dumps("Authorization: Basic " + value))
        if cookie is not None:
            if not re.fullmatch(r"/tmp/installarr-session-[0-9a-f]{32}", cookie):
                raise AppAPIError("Invalid cookie fixture path")
            lines.append(("cookie-jar" if save_cookie else "cookie") + " = " + json.dumps(cookie))
        if form is not None:
            if data is not None:
                raise AppAPIError("Ambiguous request encoding")
            lines.append('header = "Content-Type: application/x-www-form-urlencoded"')
            lines.append("data = " + json.dumps(urlencode(form, doseq=True)))
        if data is not None:
            lines.append('header = "Content-Type: application/json"')
            lines.append("data = " + json.dumps(json.dumps(data, ensure_ascii=False), ensure_ascii=False))
        request_timeout = getattr(self, 'request_timeout', 10)
        if type(request_timeout) is not int or not 1 <= request_timeout <= 90:
            raise AppAPIError('Invalid application request deadline')
        try:
            result = subprocess.run(["docker", "--host", self.socket, "exec", "--interactive", self.container,
                "/bin/sh", "-c", 'umask 077; exec curl "$@"', "curl",
                "-q", "--silent", "--show-error", "--connect-timeout", "3", "--max-time", str(request_timeout),
                "--config", "-", "--write-out", "\n%{http_code}"],
                input="\n".join(lines) + "\n", capture_output=True, text=True, timeout=request_timeout + 5, check=False)
            if result.returncode:
                raise AppAPIError("Application request unavailable")
            body, code = result.stdout.rsplit("\n", 1)
            return int(code), body
        except (OSError, subprocess.SubprocessError, ValueError):
            raise AppAPIError("Application request failed") from None

    def login(self, credentials):
        validate_credentials(credentials)
        cookie = "/tmp/installarr-session-" + uuid.uuid4().hex
        try:
            status, _ = self.request("POST", "/login", authenticated=False,
                form={"username": credentials["username"], "password": credentials["password"], "rememberMe": "false"},
                cookie=cookie, save_cookie=True)
            api_status, _ = self.request("GET", "/api/v3/system/status", authenticated=False, cookie=cookie)
            gui_status, _ = self.request("GET", "/", authenticated=False, cookie=cookie)
            return {"login": status, "api": api_status, "gui": gui_status}
        finally:
            result = subprocess.run(["docker", "--host", self.socket, "exec", self.container, "rm", "--force", "--", cookie],
                                    capture_output=True, text=True, timeout=15, check=False)
            if result.returncode:
                raise AppAPIError("Temporary login-cookie cleanup failed")


class ArrClient:
    def __init__(self, transport, expected_version=None, secondary_root=False):
        if type(secondary_root) is not bool:
            raise AppAPIError("Invalid additional media mapping")
        self.secondary_root = secondary_root
        self.transport = transport
        self.expected_version = expected_version

    def json(self, method, endpoint, payload=None, query=None):
        if method != "GET":
            if self.expected_version not in SUPPORTED_VERSIONS:
                raise AppAPIError("A tested application version is required before writes")
            status = self.json("GET", "system/status")
            if not isinstance(status, dict) or status.get("version") != self.expected_version:
                raise AppAPIError("Runtime application version differs; no write attempted")
        if query is not None and method != "GET":
            raise AppAPIError("Query parameters are only supported for reads")
        code, body = (self.transport.request(method, "/api/v3/" + endpoint, payload, query=query)
                      if query is not None else self.transport.request(method, "/api/v3/" + endpoint, payload))
        if code not in (200, 201, 202):
            raise AppAPIError("Application API rejected request (HTTP {})".format(code))
        try:
            return json.loads(body)
        except (ValueError, TypeError):
            raise AppAPIError("Invalid application JSON response") from None

    def configure_admin(self, credentials):
        validate_credentials(credentials)
        host = self.json("GET", "config/host")
        if not isinstance(host, dict) or type(host.get("id")) is not int or host["id"] <= 0 or not {
                "authenticationMethod", "authenticationRequired", "username", "password"} <= set(host):
            raise AppAPIError("Unsupported host configuration schema")
        desired = copy.deepcopy(host)
        desired.update({"authenticationMethod": "forms", "authenticationRequired": "enabled",
                        "username": credentials["username"], "password": credentials["password"],
                        "passwordConfirmation": credentials["password"]})
        self.json("PUT", "config/host/{}".format(host["id"]), desired)
        return self.verify_admin(credentials)

    def verify_admin(self, credentials):
        validate_credentials(credentials)
        host = self.json("GET", "config/host")
        if (not isinstance(host, dict) or host.get("authenticationMethod") != "forms"
                or host.get("authenticationRequired") != "enabled" or host.get("username") != credentials["username"]):
            raise AppAPIError("Authentication configuration readback failed")
        code, _ = self.transport.request("GET", "/", authenticated=False)
        anonymous_gui = code
        if code not in (302, 401):
            raise AppAPIError("Anonymous GUI access was not rejected")
        code, _ = self.transport.request("GET", "/api/v3/system/status", authenticated=False)
        if code != 401:
            raise AppAPIError("Anonymous API access was not rejected")
        logged_in = self.transport.login(credentials)
        # Some API versions require the API key even with a valid GUI cookie.
        # GUI credentials and API keys are deliberately separate identities.
        if logged_in.get("login") != 302 or logged_in.get("gui") != 200 or logged_in.get("api") not in (200, 401):
            raise AppAPIError("Shared GUI login failed (HTTP login={}, GUI={}, API={})".format(
                logged_in.get("login"), logged_in.get("gui"), logged_in.get("api")))
        password = credentials["password"]
        wrong = dict(credentials, password=("A" if password[0] != "A" else "B") + password[1:])
        denied = self.transport.login(wrong)
        if denied.get("api") != 401 or denied.get("gui") not in (302, 401):
            raise AppAPIError("Incorrect GUI password was not rejected")
        return {"anonymous_gui": anonymous_gui, "anonymous_api": code,
                "valid_login": logged_in, "invalid_login": denied}

    def ensure_root(self, path):
        if (not isinstance(path, str) or not (path.startswith("/data/") or (self.secondary_root and path == "/media-secondary"))
                or ".." in path.split("/")):
            raise AppAPIError("Root must stay inside the configured media mapping")
        def read():
            roots = self.json("GET", "rootfolder")
            if not isinstance(roots, list) or any(not isinstance(root, dict) or not isinstance(root.get("path"), str)
                                                 or type(root.get("id")) is not int for root in roots):
                raise AppAPIError("Unsupported root-folder schema")
            matches = [root for root in roots if root["path"] == path]
            if len(matches) > 1:
                raise AppAPIError("Duplicate application roots")
            return matches
        matches = read()
        if not matches:
            self.json("POST", "rootfolder", {"path": path})
            matches = read()
        if len(matches) != 1 or matches[0].get("accessible") is not True:
            raise AppAPIError("Application root readback/access failed")
        return matches[0]["id"]
