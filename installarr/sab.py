"""Version-tested SABnzbd settings and jobs on the isolated transport."""
import json
import subprocess

from .arr import AppAPIError, DockerHTTP
from .compose import IMAGES, application_paths
from .credentials import validate_credentials


SAB_HTTP = r'''
import base64,json,urllib.request,urllib.parse,urllib.error,sys
spec=json.load(sys.stdin)
url='http://127.0.0.1:8080'+spec['path']
if spec.get('query') is not None: url+='?'+urllib.parse.urlencode(spec['query'])
headers={}
if spec.get('basic'):
    credentials=spec['basic']; token=base64.b64encode((credentials['username']+':'+credentials['password']).encode()).decode()
    headers['Authorization']='Basic '+token
body=None
if spec.get('form') is not None:
    body=urllib.parse.urlencode(spec['form']).encode(); headers['Content-Type']='application/x-www-form-urlencoded'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None
request=urllib.request.Request(url,data=body,headers=headers,method=spec['method'])
try:
    response=urllib.request.build_opener(NoRedirect).open(request,timeout=10)
except urllib.error.HTTPError as error: response=error
with response:
    print(json.dumps({'code':response.code,'body':response.read(4194304).decode()}))
'''


class SabHTTP(DockerHTTP):
    """SAB's image includes Python; use its standard HTTP client directly."""
    def request(self, method, path, data=None, authenticated=False, form=None, cookie=None, save_cookie=False, basic=None, query=None):
        if self.port != 8080 or method not in ("GET", "POST") or path not in ("/api", "/config/general/"):
            raise AppAPIError("Unsupported isolated SABnzbd request")
        if basic is not None:
            validate_credentials(basic)
        payload = {"method": method, "path": path, "form": form, "query": query, "basic": basic}
        try:
            result = subprocess.run(["docker", "--host", self.socket, "exec", "--interactive", self.container,
                                     "python3", "-c", SAB_HTTP], input=json.dumps(payload),
                                    capture_output=True, text=True, timeout=15, check=False)
            if result.returncode:
                raise AppAPIError("SABnzbd HTTP transport failed")
            response = json.loads(result.stdout)
            return int(response["code"]), response["body"]
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            raise AppAPIError("SABnzbd HTTP request unavailable") from None


class SabClient:
    def __init__(self, transport):
        self.transport = transport
        self.version = IMAGES["sabnzbd"]["version"].split("-ls", 1)[0]

    def call(self, mode, **parameters):
        if mode not in ("version", "auth", "get_cats", "get_config", "set_config", "history", "queue", "addlocalfile", "resume", "pause", "config"):
            raise AppAPIError("Unsupported isolated downloader operation")
        if mode == "config" and parameters.get("name") != "test_server":
            raise AppAPIError("Unsupported provider test operation")
        if mode in ("get_cats", "set_config", "addlocalfile", "resume", "pause", "config"):
            if self.call("version").get("version") != self.version:
                raise AppAPIError("Untested SABnzbd version; no write attempted")
        form = {"mode": mode, "output": "json", **parameters}
        if mode not in ("version", "auth"):
            form["apikey"] = self.transport.api_key
        if mode == "set_config" and parameters.get("section") == "categories":
            code, body = self.transport.request("GET", "/api", authenticated=False, query=form)
        else:
            code, body = self.transport.request("POST", "/api", authenticated=False, form=form)
        if code != 200:
            raise AppAPIError("SABnzbd request rejected (HTTP {})".format(code))
        try:
            result = json.loads(body)
        except ValueError:
            raise AppAPIError("SABnzbd response was not JSON") from None
        if not isinstance(result, dict) or result.get("error") or result.get("status") is False:
            raise AppAPIError("SABnzbd operation rejected")
        return result

    def misc(self):
        result = self.call("get_config", section="misc").get("config", {}).get("misc")
        if not isinstance(result, dict):
            raise AppAPIError("Unsupported SABnzbd settings schema")
        return result

    def set_misc(self, key, value, private=False):
        if key not in self.misc():
            raise AppAPIError("Unknown SABnzbd setting")
        self.call("set_config", section="misc", keyword=key, value=value)
        saved = self.misc()
        matches = saved.get(key) == value if key in ("html_login", "api_logging") else str(saved.get(key)) == str(value)
        if not private and not matches:
            raise AppAPIError("SABnzbd setting readback differs")

    def configure_admin(self, credentials):
        validate_credentials(credentials)
        if ":" in credentials["username"]:
            raise AppAPIError("SABnzbd Basic authentication requires a username without a colon")
        self.set_misc("api_logging", 0)
        self.set_misc("username", credentials["username"])
        self.set_misc("password", credentials["password"], private=True)
        self.set_misc("html_login", 0)
        return {"status": "configured", "restart_required_before_verification": True}

    def verify_admin(self, credentials):
        validate_credentials(credentials)
        settings = self.misc()
        if settings.get("username") != credentials["username"] or int(settings.get("html_login", -1)) != 0:
            raise AppAPIError("SABnzbd authentication settings differ")
        base = settings.get("url_base", "")
        if not isinstance(base, str) or (base and not base.startswith("/")):
            raise AppAPIError("Unsupported SABnzbd URL base")
        path = base.rstrip("/") + "/config/general/"
        statuses = []
        for value in (None, credentials, dict(credentials, password=("A" if credentials["password"][0] != "A" else "B") + credentials["password"][1:])):
            status, _ = self.transport.request("GET", path, authenticated=False, basic=value)
            statuses.append(status)
        if statuses != [401, 200, 401]:
            raise AppAPIError("SABnzbd GUI authentication/rejection failed ({})".format(statuses))
        return {"anonymous": statuses[0], "valid": statuses[1], "invalid": statuses[2]}

    def configure_storage(self, config):
        paths = application_paths(config, "sabnzbd")
        self.set_misc("download_dir", paths["incomplete_directory"])
        self.set_misc("complete_dir", paths["download_directory"])
        # SAB lazily creates the default category set on its first collection read.
        # Initialize it before writes, otherwise that read replaces new tv/movie rows.
        self.call("get_cats")
        for name in ("tv", "movies"):
            self.call("set_config", section="categories", name=name, dir=name)
        self.verify_storage(config)

    def verify_storage(self, config):
        settings = self.misc()
        paths = application_paths(config, "sabnzbd")
        if settings.get("download_dir") != paths["incomplete_directory"] or settings.get("complete_dir") != paths["download_directory"]:
            raise AppAPIError("SABnzbd storage map readback differs")
        categories = self.call("get_config", section="categories").get("config", {}).get("categories")
        if isinstance(categories, dict):
            categories = [dict(value, name=key) for key, value in categories.items()]
        if not isinstance(categories, list):
            raise AppAPIError("Unsupported SABnzbd category schema")
        for name in ("tv", "movies"):
            matches = [item for item in categories if isinstance(item, dict) and item.get("name") == name]
            if len(matches) != 1 or matches[0].get("dir") != name:
                raise AppAPIError("SABnzbd category readback differs")
