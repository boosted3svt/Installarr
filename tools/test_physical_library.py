"""Read-only existing-library scan; original media never copied, renamed or deleted.

A private Unix-socket relay permits TLS metadata requests to two official hosts.
It neither listens on host TCP nor changes any host/container network configuration.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import socketserver
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.arr import AppAPIError, ArrClient, DockerHTTP
from installarr.compose import IMAGES, bind
from installarr.lifecycle import SOCKET
from physical_fixtures import DOCKER, Fixture, run
from fixture_metadata_proxy import relay
from test_physical_sab import wait_for

ALLOWED = {'api.radarr.video', 'skyhook.sonarr.tv'}


class MetadataRelay(socketserver.BaseRequestHandler):
    def handle(self):
        line = b''
        while not line.endswith(b'\n') and len(line) < 1024:
            data = self.request.recv(1)
            if not data:
                return
            line += data
        spec = json.loads(line)
        if spec.get('host') not in ALLOWED or spec.get('port') != 443:
            self.request.sendall(b'0')
            return
        try:
            with socket.create_connection((spec['host'], 443), timeout=15) as upstream:
                self.request.sendall(b'1')
                self.server.observed.add(spec['host'])
                relay(self.request, upstream)
        except OSError:
            return


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


def main(app):
    fixture = Fixture([app, 'sabnzbd'], 'library')
    passed, stage, server = False, 'startup', None
    leaf = 'Movies' if app == 'radarr' else 'TV'
    directory = 'Framing Britney Spears (2021)' if app == 'radarr' else '11.22.63'
    source = Path('/media/installarr') / leaf / directory
    target = '/data/media/' + leaf + '/' + directory
    # Inventory only these user-supplied examples. Never follow symlinks.
    before = {str(path.relative_to(source)): (path.stat().st_size, path.stat().st_mtime_ns)
              for path in source.rglob('*') if path.is_file() and not path.is_symlink()}
    try:
        fixture.service_script("""root=int(sys.argv[1]); name=sys.argv[2]
base=os.open(name+'/media',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
os.mkdir(sys.argv[3],0o700,dir_fd=base)
parent=os.open(sys.argv[3],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=base)
os.mkdir(sys.argv[4],0o700,dir_fd=parent)
os.close(parent); os.close(base)
""", extra=(leaf, directory))
        override = fixture.work / 'examples.json'
        override.write_text(json.dumps({'services': {app: {'network_mode': 'service:sabnzbd', 'volumes': [bind(source, target, True)]}}}))
        fixture.compose += ['--file', str(override)]
        fixture.up()
        container = fixture.container(app)
        helper = fixture.container('sabnzbd')
        def ready():
            try:
                root = ET.fromstring((fixture.work / ('configs/' + app + '/config.xml')).read_text())
            except ET.ParseError:
                return None
            client = ArrClient(DockerHTTP(SOCKET, container, IMAGES[app]['port'], root.findtext('ApiKey')),
                               IMAGES[app]['version'].split('-ls', 1)[0])
            return client if client.json('GET', 'system/status').get('version') == client.expected_version else None
        client = wait_for(ready)
        client.configure_admin({'username': 'installarr-library-admin', 'password': secrets.token_urlsafe(36)})
        inspected = json.loads(run(DOCKER + ['inspect', container]))[0]
        mounts = [row for row in inspected['Mounts'] if row['Destination'] == target]
        if len(mounts) != 1 or mounts[0]['RW'] or mounts[0]['Source'] != str(source):
            raise ValueError('Original example mount is not read-only')
        stage = 'metadata_proxy'
        sock = fixture.work / 'configs/sabnzbd/installarr-metadata.sock'
        server = Server(str(sock), MetadataRelay)
        server.observed = set()
        os.chown(str(sock), 2000, 2000)
        os.chmod(str(sock), 0o600)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        proxy = (Path(__file__).parent / 'fixture_metadata_proxy.py').read_text()
        run(DOCKER + ['exec', '--interactive', '--user', '2000:2000', helper, '/bin/sh', '-c',
                      'umask 077; cat > /tmp/installarr-metadata-proxy.py'], input=proxy)
        # Reuse the tested SAB Python runtime in the shared networkless namespace.
        run(DOCKER + ['exec', '--detach', '--user', '2000:2000', helper, '/bin/sh', '-c',
                      'exec python3 /tmp/installarr-metadata-proxy.py /config/installarr-metadata.sock > /config/installarr-proxy.log 2>&1'])
        def proxy_ready():
            result = subprocess.run(DOCKER + ['exec', '--user', '2000:2000', helper, 'python3',
                '-c', "import socket; s=socket.create_connection(('127.0.0.1',3128),timeout=1); s.close()"], capture_output=True, timeout=5)
            return result.returncode == 0
        try:
            wait_for(proxy_ready, seconds=10)
        except ValueError:
            print((fixture.work / 'configs/sabnzbd/installarr-proxy.log').read_text())
            raise
        host = client.json('GET', 'config/host')
        host.update({'proxyEnabled': True, 'proxyType': 'http', 'proxyHostname': '127.0.0.1', 'proxyPort': 3128,
                     'proxyBypassLocalAddresses': True, 'proxyBypassFilter': '127.0.0.1,localhost'})
        client.json('PUT', 'config/host/' + str(host['id']), host)
        client.ensure_root('/data/media/' + leaf)
        stage = 'lookup'
        term = 'Framing Britney Spears' if app == 'radarr' else '11.22.63'
        kind = 'movie' if app == 'radarr' else 'series'
        results = client.json('GET', kind + '/lookup', query={'term': term})
        matches = [row for row in results if (row.get('title') == term or row.get('title') == '11.22.63')]
        if len(matches) != 1:
            raise ValueError('Expected one matching example metadata result')
        entry = matches[0]
        profiles = client.json('GET', 'qualityprofile')
        if not profiles:
            raise ValueError('No dynamic quality profile')
        directory = 'Framing Britney Spears (2021)' if app == 'radarr' else '11.22.63'
        entry.update({'path': '/data/media/' + leaf + '/' + directory, 'qualityProfileId': profiles[0]['id'],
                      'monitored': False, 'rootFolderPath': '/data/media/' + leaf,
                      'addOptions': {'searchForMovie': False, 'searchForMissingEpisodes': False}})
        if app == 'sonarr':
            entry.update({'seasonFolder': True})
            for season in entry.get('seasons', []):
                season['monitored'] = False
        stage = 'add_existing'
        saved = client.json('POST', kind, entry)
        identity = saved['id']
        stage = 'initial_scan'
        files_endpoint = 'moviefile' if app == 'radarr' else 'episodefile'
        def imported():
            rows = client.json('GET', files_endpoint, query={kind + 'Id': identity})
            return rows if rows else None
        wait_for(imported, seconds=240)
        def scans_idle():
            rows = client.json('GET', 'command')
            return not any(row.get('status') in ('queued', 'started') and
                           any(word in str(row.get('name', '')).lower() for word in ('refresh', 'rescan')) for row in rows)
        wait_for(scans_idle, seconds=240)
        files = wait_for(imported, seconds=240)
        if len(files) != 1 or len({row['relativePath'] for row in files}) != len(files):
            raise ValueError('Expected exactly one unique original media file')
        evidence = [{'id': row['id'], 'relativePath': row.get('relativePath'), 'size': row.get('size'),
                     'mediaInfo_present': bool(row.get('mediaInfo'))} for row in files]
        stage = 'restart'
        run(fixture.compose + ['restart', app])
        client = wait_for(ready)
        persistent = client.json('GET', 'moviefile' if app == 'radarr' else 'episodefile', query={kind + 'Id': identity})
        if {row['id'] for row in persistent} != {row['id'] for row in files}:
            raise ValueError('Library file IDs did not persist')
        after = {str(path.relative_to(source)): (path.stat().st_size, path.stat().st_mtime_ns)
                 for path in source.rglob('*') if path.is_file() and not path.is_symlink()}
        if before != after:
            raise ValueError('Original example inventory changed')
        passed = True
        print(json.dumps({'result': 'passed', 'app': app, 'version': IMAGES[app], 'originals_read_only': True,
                          'original_inventory_unchanged': True, 'files': evidence, 'metadata_hosts': sorted(server.observed),
                          'restart_persistence': 'passed', 'download_dispatch_tested': False}, indent=2))
    except Exception:
        print(json.dumps({'failed_stage': stage}))
        raise
    finally:
        if server:
            server.shutdown()
            server.server_close()
        fixture.close(passed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', choices=('radarr', 'sonarr'), default='radarr')
    main(parser.parse_args().app)
