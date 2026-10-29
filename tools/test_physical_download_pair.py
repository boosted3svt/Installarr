"""Disposable application/SAB pair sharing only a container's isolated loopback.

No host network configuration, bridge, published ports, provider or indexer access.
Canonical generated bundles remain network_mode none. A fixture-only Compose
extension joins Radarr to SAB's already networkless namespace.
"""
import json
from pathlib import Path
import re
import secrets
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.arr import AppAPIError, ArrClient, DockerHTTP
from installarr.compose import IMAGES
from installarr.downloadclients import ensure_sabnzbd
from installarr.lifecycle import SOCKET
from installarr.sab import SabClient, SabHTTP
from physical_fixtures import DOCKER, Fixture, run
from test_physical_sab import wait_for


def main(app):
    fixture = Fixture([app, "sabnzbd"], "download-pair")
    passed = False
    stage = "startup"
    try:
        override = fixture.work / "shared-loopback.json"
        override.write_text(json.dumps({"services": {app: {"network_mode": "service:sabnzbd"}}}))
        fixture.compose += ["--file", str(override)]
        fixture.up()
        arr_id, sab_id = fixture.container(app), fixture.container("sabnzbd")
        def sab_ready():
            text = (fixture.work / "configs/sabnzbd/sabnzbd.ini").read_text()
            match = re.search(r"(?m)^api_key\s*=\s*([a-fA-F0-9]{32})\s*$", text)
            if not match:
                return None
            sab = SabClient(SabHTTP(SOCKET, sab_id, 8080, match.group(1)))
            return sab if sab.call("version").get("version") == "5.1.3" else None
        def arr_ready():
            root = ET.fromstring((fixture.work / ("configs/" + app + "/config.xml")).read_text())
            client = ArrClient(DockerHTTP(SOCKET, arr_id, IMAGES[app]["port"], root.findtext("ApiKey")), IMAGES[app]["version"].split("-ls", 1)[0])
            return client if client.json("GET", "system/status").get("version") == client.expected_version else None
        sab = wait_for(sab_ready)
        try:
            arr = wait_for(arr_ready)
        except ET.ParseError:
            arr = wait_for(arr_ready)
        stage = "authentication"
        credentials = {"username": "installarr-pair-admin", "password": secrets.token_urlsafe(36)}
        sab.configure_admin(credentials)
        # Restart the namespace owner and recreate its dependent, so Radarr cannot
        # retain an old sandbox while SAB moves into a new one.
        run(fixture.compose + ["stop"])
        run(fixture.compose + ["up", "--detach", "--force-recreate", "--pull", "never"])
        arr_id, sab_id = fixture.container(app), fixture.container("sabnzbd")
        sab, arr = wait_for(sab_ready), wait_for(arr_ready)
        sab.verify_admin(credentials)
        arr.configure_admin(credentials)
        sab.configure_storage(fixture.config)
        stage = "connection"
        key = sab.transport.api_key
        first = ensure_sabnzbd(arr, fixture.config, app, key)
        second = ensure_sabnzbd(arr, fixture.config, app, key)
        if first != second or len(arr.json("GET", "downloadclient")) != 1:
            raise ValueError("Downloader rerun duplicated or changed IDs")
        stage = "bad_key_rejection"
        wrong = ("a" if key[0] != "a" else "b") + key[1:]
        try:
            ensure_sabnzbd(arr, fixture.config, app, wrong)
        except AppAPIError:
            pass
        else:
            raise ValueError("Invalid downloader key was accepted")
        if ensure_sabnzbd(arr, fixture.config, app, key) != first:
            raise ValueError("Rejected key changed the configured downloader")
        stage = "operator_change_preserved"
        edited = arr.json("GET", "downloadclient/{}".format(first["id"]))
        edited["priority"] = 2
        arr.json("PUT", "downloadclient/{}".format(first["id"]), edited)
        try:
            ensure_sabnzbd(arr, fixture.config, app, key)
        except AppAPIError:
            pass
        else:
            raise ValueError("Operator priority edit was overwritten")
        if arr.json("GET", "downloadclient/{}".format(first["id"]))["priority"] != 2:
            raise ValueError("Operator priority was not preserved")
        edited["priority"] = 1
        arr.json("PUT", "downloadclient/{}".format(first["id"]), edited)
        stage = "restart"
        run(fixture.compose + ["stop"])
        run(fixture.compose + ["up", "--detach", "--force-recreate", "--pull", "never"])
        arr_id, sab_id = fixture.container(app), fixture.container("sabnzbd")
        sab, arr = wait_for(sab_ready), wait_for(arr_ready)
        sab.verify_admin(credentials)
        arr.verify_admin(credentials)
        sab.verify_storage(fixture.config)
        if ensure_sabnzbd(arr, fixture.config, app, sab.transport.api_key) != first:
            raise ValueError("Downloader identity did not persist")
        rows = json.loads(run(DOCKER + ["inspect", arr_id, sab_id]))
        if rows[0]["HostConfig"]["NetworkMode"] != "container:" + sab_id or rows[1]["HostConfig"]["NetworkMode"] != "none":
            raise ValueError("Isolated namespace ownership differs")
        if any(row["HostConfig"].get("PortBindings") for row in rows):
            raise ValueError("Unexpected published ports")
        passed = True
        print(json.dumps({"result": "passed", "apps": {app: IMAGES[app] for app in fixture.config["apps"]},
                          "downloader": first, "rerun_and_restart": "passed", "bad_key_rejected_before_save": True, "operator_edit_preserved": True,
                          "network": "shared container-only loopback, no ports or bridge", "dispatch_tested": False,
                          "import_tested": False}, indent=2))
    except Exception:
        print(json.dumps({"failed_stage": stage}))
        raise
    finally:
        fixture.close(passed)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", choices=("radarr", "sonarr"), default="radarr")
    main(parser.parse_args().app)
