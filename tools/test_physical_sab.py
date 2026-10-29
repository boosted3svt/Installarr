"""SABnzbd authentication, persistence and a real generated NNTP/yEnc download.

No provider credentials, indexers, external articles or host network changes.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.arr import AppAPIError, DockerHTTP
from installarr.compose import IMAGES
from installarr.credentials import initialize_credentials, read_private_credentials
from installarr.lifecycle import SOCKET
from installarr.sab import SabClient, SabHTTP
from fixture_nntp import FILENAME, MESSAGE_ID, PAYLOAD
from physical_fixtures import DOCKER, Fixture, run


def wait_for(action, seconds=100):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        try:
            result = action()
            if result:
                return result
        except (AppAPIError, FileNotFoundError):
            pass
        time.sleep(0.5)
    raise ValueError("Isolated downloader condition timed out")


def main():
    fixture = Fixture(["sabnzbd"], "sab")
    passed = False
    stage = "startup"
    history_status = None
    try:
        fixture.up()
        container = fixture.container("sabnzbd")
        def ready():
            text = (fixture.work / "configs" / "sabnzbd" / "sabnzbd.ini").read_text()
            match = re.search(r"(?m)^api_key\s*=\s*([a-fA-F0-9]{32})\s*$", text)
            if not match:
                return None
            api = SabClient(SabHTTP(SOCKET, container, 8080, match.group(1)))
            if api.call("version").get("version") != "5.1.3":
                raise ValueError("Unexpected SABnzbd runtime version")
            return api
        api = wait_for(ready)
        stage = "authentication"
        credentials = {"username": "installarr-test-admin", "password": secrets.token_urlsafe(36)}
        initialize_credentials(fixture.work / "secrets", lambda: credentials)
        credentials = read_private_credentials(fixture.work / "secrets" / "gui-admin.json")
        api.configure_admin(credentials)
        run(fixture.compose + ["restart"])
        api = wait_for(ready)
        auth = api.verify_admin(credentials)
        stage = "storage"
        # Public category fields only; never retain a raw configuration response.
        api.configure_storage(fixture.config)
        api.configure_storage(fixture.config)
        identities = json.loads(run(DOCKER + ["exec", container, "python3", "-c", """import json,os,pathlib
result=[]
for path in pathlib.Path('/proc').iterdir():
    if not path.name.isdigit() or int(path.name)==os.getpid(): continue
    try:
        if b'SABnzbd.py' not in (path/'cmdline').read_bytes(): continue
        values={line.split(':',1)[0]:line.split(':',1)[1].split() for line in (path/'status').read_text().splitlines() if ':' in line}
        result.append({'uid':int(values['Uid'][1]),'gid':int(values['Gid'][1])})
    except (FileNotFoundError,PermissionError): pass
print(json.dumps(result))
"""]))
        if identities != [{"uid": 2000, "gid": 2000}]:
            raise ValueError("SABnzbd runtime identity differs")
        stage = "fixture_server"
        source = (Path(__file__).parent / "fixture_nntp.py").read_text()
        run(DOCKER + ["exec", "--interactive", "--user", "2000:2000", container, "/bin/sh", "-c",
                      "umask 077; cat > /tmp/installarr-nntp.py"], input=source)
        run(DOCKER + ["exec", "--detach", "--user", "2000:2000", container, "python3", "/tmp/installarr-nntp.py"])
        wait_for(lambda: run(DOCKER + ["exec", container, "/bin/sh", "-c", "test -f /tmp/installarr-nntp-ready && echo ready || true"]) == "ready")
        api.call("set_config", section="servers", name="installarr-local-fixture", host="127.0.0.1", port=21119,
                 ssl=0, enable=1, connections=1, priority=0, timeout=5, send_group=1)
        stage = "download"
        nzb = '''<?xml version="1.0" encoding="utf-8"?>
<nzb xmlns="http://www.newzbin.com/DTD/2003/nzb">
<file poster="Installarr Fixture" date="1793145600" subject='"installarr-proof.bin" yEnc (1/1)'>
<groups><group>alt.binaries.installarr</group></groups>
<segments><segment bytes="{}" number="1">{}</segment></segments>
</file></nzb>'''.format(len(PAYLOAD), MESSAGE_ID)
        run(DOCKER + ["exec", "--interactive", "--user", "2000:2000", container, "/bin/sh", "-c",
                      "umask 077; cat > /config/installarr-fixture.nzb"], input=nzb)
        result = api.call("addlocalfile", name="/config/installarr-fixture.nzb", cat="tv", pp=0)
        ids = result.get("nzo_ids")
        if not isinstance(ids, list) or len(ids) != 1:
            raise ValueError("Downloader did not return one dynamic job ID")
        api.call("resume")
        def completed():
            nonlocal history_status
            slots = api.call("history", limit=10).get("history", {}).get("slots", [])
            matches = [item for item in slots if item.get("nzo_id") == ids[0]]
            if not matches:
                return None
            history_status = matches[0].get("status")
            if history_status == "Failed":
                raise ValueError("Generated fixture download failed")
            return matches[0] if history_status == "Completed" and str(matches[0].get("storage", "")).startswith("/data/downloads/") else None
        history = wait_for(completed)
        print(json.dumps({"generated_job_result": {key: history.get(key) for key in ("status", "storage", "path", "fail_message", "bytes", "downloaded", "category")}}))
        storage = PurePosixPath(history["storage"])
        if ".." in storage.parts:
            raise ValueError("Unsafe downloader storage result")
        relative = storage.relative_to(PurePosixPath("/data/downloads"))
        if not relative.parts or relative.parts[0] != "tv":
            raise ValueError("Category did not use the configured completed root")
        if relative.suffix != ".bin":
            relative = relative / FILENAME
        evidence = json.loads(fixture.service_script("""import hashlib,json
root=int(sys.argv[1]); name=sys.argv[2]
parts=json.loads(sys.argv[3]); fd=os.open(name+'/downloads',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
try:
    for part in parts[:-1]:
        nextfd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd); os.close(fd); fd=nextfd
    file=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
    with os.fdopen(file,'rb') as handle:
        data=handle.read(); info=os.fstat(handle.fileno())
    print(json.dumps({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'uid':info.st_uid,'gid':info.st_gid}))
finally: os.close(fd)
""", extra=(json.dumps(list(relative.parts)),)))
        if evidence != {"bytes": len(PAYLOAD), "sha256": hashlib.sha256(PAYLOAD).hexdigest(), "uid": 2000, "gid": 2000}:
            raise ValueError("Actual completed bytes or ownership differ")
        counts = json.loads(run(DOCKER + ["exec", container, "cat", "/tmp/installarr-nntp-counts.json"]))
        if counts.get("body_requests", 0) + counts.get("article_requests", 0) < 1:
            raise ValueError("NNTP transfer was not observed")
        stage = "restart_persistence"
        run(fixture.compose + ["restart"])
        api = wait_for(ready)
        api.verify_admin(credentials)
        api.verify_storage(fixture.config)
        if not completed():
            raise ValueError("Completed job did not persist")
        passed = True
        print(json.dumps({"result": "passed", "image": IMAGES["sabnzbd"], "authentication_http_status": auth,
                          "uid": 2000, "gid": 2000, "actual_completed_file": evidence, "nntp_requests": counts,
                          "storage_categories_and_restart": "passed", "prerequisites": fixture.prerequisites,
                          "real_provider_tested": False, "sonarr_import_tested": False}, indent=2))
    except Exception:
        print(json.dumps({"failed_stage": stage, "history_status": history_status}))
        raise
    finally:
        fixture.close(passed)


if __name__ == "__main__":
    main()
