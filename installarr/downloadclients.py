"""Version-tested SABnzbd connection reconciliation for isolated app pairs."""
import copy
import re

from .arr import AppAPIError
from .compose import IMAGES, application_paths

NAME = "Installarr SABnzbd"


def ensure_sabnzbd(client, config, app, api_key, host="127.0.0.1"):
    if app not in ("sonarr", "radarr") or client.expected_version != IMAGES[app]["version"].split("-ls", 1)[0]:
        raise AppAPIError("Tested application version required for downloader integration")
    if not isinstance(api_key, str) or not re.fullmatch(r"[a-fA-F0-9]{32}", api_key):
        raise AppAPIError("Invalid downloader API key")
    if host not in ("127.0.0.1", "sabnzbd"):
        raise AppAPIError("Unsupported configured downloader host")
    category = application_paths(config, app)["download_category"]
    schemas = client.json("GET", "downloadclient/schema")
    candidates = [row for row in schemas if row.get("implementation") == "Sabnzbd"] if isinstance(schemas, list) else []
    if len(candidates) != 1:
        raise AppAPIError("Unsupported downloader schema")
    schema = candidates[0]
    category_field = "tvCategory" if app == "sonarr" else "movieCategory"
    desired = {"host": host, "port": 8080, "useSsl": False, "urlBase": "", "apiKey": api_key,
               "username": "", "password": "", category_field: category}
    fields = schema.get("fields", [])
    names = [field.get("name") for field in fields]
    if any(names.count(name) != 1 for name in desired):
        raise AppAPIError("Required downloader fields unavailable")
    rows = client.json("GET", "downloadclient")
    if not isinstance(rows, list):
        raise AppAPIError("Unsupported downloader collection")
    matching = [row for row in rows if row.get("name") == NAME]
    if len(matching) > 1 or (matching and matching[0].get("implementation") != "Sabnzbd"):
        raise AppAPIError("Downloader name conflicts with existing configuration; preserved")
    payload = copy.deepcopy(matching[0] if matching else schema)
    if matching:
        existing = {field.get("name"): field for field in payload.get("fields", [])}
        # Preserve unrelated fields; never silently replace an incompatible schema.
        if any(name not in existing for name in desired):
            raise AppAPIError("Existing downloader schema differs; preserved")
        if (matching[0].get("enable") is not True or matching[0].get("priority") != 1
                or any(existing[name].get("value") != value for name, value in desired.items()
                       if name not in ("apiKey", "password", "username"))):
            raise AppAPIError("Existing downloader settings differ; preserved")
    payload.update({"name": NAME, "enable": True, "priority": 1})
    for field in payload["fields"]:
        if field["name"] in desired:
            field["value"] = desired[field["name"]]
    # Validate the actual connection before storing any change.
    client.json("POST", "downloadclient/test", payload)
    if matching:
        identity = matching[0].get("id")
        if type(identity) is not int or identity <= 0:
            raise AppAPIError("Invalid downloader ID")
        current = {field["name"]: field.get("value") for field in matching[0]["fields"]}
        if not matching[0].get("enable") or matching[0].get("priority") != 1 or any(current.get(key) != value for key, value in desired.items()):
            client.json("PUT", "downloadclient/{}".format(identity), payload)
    else:
        created = client.json("POST", "downloadclient", payload)
        identity = created.get("id") if isinstance(created, dict) else None
        if type(identity) is not int or identity <= 0:
            raise AppAPIError("Downloader did not return a dynamic ID")
    saved = client.json("GET", "downloadclient/{}".format(identity))
    values = {field["name"]: field.get("value") for field in saved.get("fields", [])}
    if (saved.get("name") != NAME or saved.get("implementation") != "Sabnzbd" or saved.get("enable") is not True
            or any(values.get(key) != value for key, value in desired.items() if key not in ("apiKey", "password", "username"))):
        raise AppAPIError("Downloader readback differs")
    # Test the saved configuration as well: masked secrets are not equality proof.
    client.json("POST", "downloadclient/test", saved)
    return {"id": identity, "implementation": "Sabnzbd", "category": category, "connection_test": "passed"}
