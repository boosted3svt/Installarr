"""Generated-video release -> SAB NNTP -> normal Radarr completed-download import.

Only generated content is served inside the disposable SAB container. No indexer,
real provider credentials or original media is used. No host ports are published.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, configure_apps, wait_for
from installarr.cli import save_config
from installarr.compose import IMAGES
from installarr.credentials import read_private_credentials
from installarr.directories import observed_mount, prepare_directories
from installarr.profiles import recommended_profiles
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--app', choices=('radarr', 'sonarr'), default='radarr')
    args = parser.parse_args()
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        assert observed_mount(fd) == {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    finally:
        os.close(fd)
    if args.resume:
        work = args.resume
        config = json.loads((work / 'config.json').read_text())
        tag = Path(config['data_root']).name.rsplit('-', 1)[1]
    else:
        work = Path(tempfile.mkdtemp(prefix='installarr-arr-import-', dir='/var/tmp'))
        tag = uuid.uuid4().hex[:8]
        data = Path('/media/installarr') / ('Installarr-Arr-Import-' + tag)
        config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
        config.update(apps=[args.app, 'sabnzbd'], data_root=str(data), project_directory=str(work / 'project'),
                      quality_profiles=recommended_profiles([args.app]))
        for key in ('providers', 'provider_secrets_file', 'bazarr_language_profile'):
            config.pop(key, None)
        config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                                 configs=str(work / 'configs'), backups=str(work / 'backups'))
        save_config(work / 'config.json', config)
    app = next(app for app in config['apps'] if app in ('radarr', 'sonarr'))
    data = Path(config['data_root'])
    project = 'installarr-arr-import-' + tag
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    print(json.dumps({'evidence': str(work), 'nas_fixture': str(data), 'project': project}), flush=True)
    prepare_directories(config, work / 'directories')
    write_reference_bundle(config, published=False)
    controller = reference_controller(config, project, published=False)
    stage = 'startup'
    def restart():
        controller.stop(); controller.reconcile()
    try:
        controller.reconcile()
        configured = configure_apps(config, controller, credentials, restart, download_host='sabnzbd')
        arr = app_client(config, controller, app)
        sab = app_client(config, controller, 'sabnzbd')
        assert arr.json('GET', 'indexer') == []
        assert not sab.call('queue').get('queue', {}).get('slots')
        stage = 'metadata'
        if app == 'radarr':
            movie = next((r for r in arr.json('GET', 'movie') if r.get('tmdbId') == 10331), None)
            if not movie:
                lookup = arr.json('GET', 'movie/lookup', query={'term': 'tmdb:10331'})
                movie = arr.json('POST', 'movie', dict(lookup[0], qualityProfileId=configured[app]['quality_profiles']['preferred_id'],
                    rootFolderPath='/data/Movies', monitored=True, minimumAvailability='released', addOptions={'searchForMovie': False}))
            media = movie
            media_endpoint = 'movie/' + str(movie['id'])
            file_endpoint, file_id_field = 'moviefile/', 'movieFileId'
            history_query = {'movieId': movie['id'], 'pageSize': 100}
            parent_path = movie['path']
        else:
            series = next((r for r in arr.json('GET', 'series') if r.get('tvdbId') == 301824), None)
            if not series:
                lookup = arr.json('GET', 'series/lookup', query={'term': 'tvdb:301824'})
                series = arr.json('POST', 'series', dict(lookup[0], qualityProfileId=configured[app]['quality_profiles']['preferred_id'],
                    rootFolderPath='/data/TV', monitored=True, seasonFolder=True, seriesType='standard',
                    seasons=[dict(row, monitored=row['seasonNumber'] > 0) for row in lookup[0]['seasons']],
                    addOptions={'searchForMissingEpisodes': False, 'searchForCutoffUnmetEpisodes': False}))
            def episode():
                return next((row for row in arr.json('GET', 'episode', query={'seriesId': series['id']})
                             if row['seasonNumber'] == 1 and row['episodeNumber'] == 1), None)
            media = wait_for(episode)
            media_endpoint = 'episode/' + str(media['id'])
            file_endpoint, file_id_field = 'episodefile/', 'episodeFileId'
            history_query = {'seriesId': series['id'], 'pageSize': 100}
            parent_path = series['path']
        assert not media.get('hasFile'), 'Use a fresh fixture after a successful import'
        stage = 'generated video'
        payload = work / 'payload'
        payload.mkdir(mode=0o700, exist_ok=True); os.chown(payload, 2000, 2000)
        filename = ('Night.of.the.Living.Dead.1968' if app == 'radarr' else '11.22.63.S01E01') + '.1080p.WEB-DL.AAC2.0.H264-INSTALLARR.mkv'
        generated = payload / filename
        if not generated.exists():
            controller.run(controller.docker + ['run', '--rm', '--network', 'none', '--user', '2000:2000', '--cap-drop', 'ALL',
                '--mount', 'type=bind,source=' + str(payload) + ',target=/payload', '--entrypoint', 'ffmpeg', IMAGES['bazarr']['image'],
                '-hide_banner', '-loglevel', 'error', '-nostdin', '-f', 'lavfi', '-i', 'color=c=black:s=1920x1080:r=1/60:d=5400',
                '-f', 'lavfi', '-i', 'anullsrc=r=8000:cl=mono', '-t', '5400', '-c:v', 'libx264', '-preset', 'ultrafast',
                '-c:a', 'aac', '-b:a', '8k', '-metadata:s:a:0', 'language=eng', '/payload/' + filename], timeout=100)
        raw = generated.read_bytes()
        expected = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'uid': 2000, 'gid': 2000}
        source = Path(__file__).with_name('fixture_nntp.py').read_text()
        source = source.replace('if __name__ == "__main__":', 'if False:')
        source += '''\nimport base64, http.server
spec=json.loads(Path('/tmp/installarr-video-spec.json').read_text())
PAYLOAD=base64.b64decode(spec['payload']); FILENAME=spec['filename']
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
nntp=Server(('127.0.0.1',21119),Handler)
threading.Thread(target=nntp.serve_forever,daemon=True).start()
class HTTP(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        nzb=('<?xml version="1.0"?><nzb xmlns="http://www.newzbin.com/DTD/2003/nzb"><file poster="Installarr" date="1793145600" subject=\\'"'+FILENAME+'" yEnc (1/1)\\'><groups><group>alt.binaries.installarr</group></groups><segments><segment bytes="'+str(len(PAYLOAD))+'" number="1">'+MESSAGE_ID+'</segment></segments></file></nzb>').encode()
        self.send_response(200); self.send_header('Content-Type','application/x-nzb'); self.send_header('Content-Length',str(len(nzb))); self.end_headers(); self.wfile.write(nzb)
Path('/tmp/installarr-video-ready').write_text('ready\\n')
http.server.ThreadingHTTPServer(('0.0.0.0',21120),HTTP).serve_forever()
'''
        compile(source, 'installarr-video-server.py', 'exec')
        stage = 'fixture server'
        for target, content in (('/tmp/installarr-video-server.py', source), ('/tmp/installarr-video-spec.json', json.dumps({'payload': base64.b64encode(raw).decode(), 'filename': filename}))):
            subprocess.run(controller.docker + ['exec', '--interactive', '--user', '2000:2000', sab.transport.container,
                '/bin/sh', '-c', 'umask 077; cat > "$1"', 'fixture', target], input=content, text=True, capture_output=True, check=True)
        controller.run(controller.docker + ['exec', '--detach', '--user', '2000:2000', sab.transport.container, 'python3', '/tmp/installarr-video-server.py'])
        wait_for(lambda: controller.run(controller.docker + ['exec', sab.transport.container, '/bin/sh', '-c', 'test -f /tmp/installarr-video-ready && echo ready || true']) == 'ready')
        sab.call('set_config', section='servers', name='installarr-local-fixture', host='127.0.0.1', port=21119,
                 ssl=0, enable=1, connections=1, priority=0, timeout=5, send_group=1)
        sab.call('resume')
        stage = 'native release push'
        release = {'title': filename[:-4], 'downloadUrl': 'http://sabnzbd:21120/installarr.nzb', 'protocol': 'usenet',
                   'publishDate': '2026-10-28T01:00:00Z', 'size': 4 * 1024 ** 3, 'indexer': 'Installarr generated fixture',
                   'downloadClientId': configured[app]['downloader']['id']}
        # Advertised release size is synthetic metadata, not transferred bytes.
        # Actual file bytes/hash are verified independently after import.
        decisions = arr.json('POST', 'release/push', release)
        (work / 'release-decision.json').write_text(json.dumps(decisions, indent=2) + '\n')
        assert decisions and decisions[0].get('approved'), 'Native release decision rejected; evidence retained'
        stage = 'normal completed-download import'
        until = time.monotonic() + 300
        imported = None
        while time.monotonic() < until:
            current = arr.json('GET', media_endpoint)
            if current.get('hasFile'):
                imported = current; break
            time.sleep(2)
        if not imported:
            queue = arr.json('GET', 'queue', query={'includeUnknownMovieItems': True})
            (work / 'queue.json').write_text(json.dumps(queue, indent=2) + '\n')
        assert imported, 'Normal completed-download handling did not import; evidence retained'
        file = arr.json('GET', file_endpoint + str(imported[file_id_field]))
        host_file = data / Path(parent_path).relative_to('/data') / file['relativePath']
        info = host_file.stat()
        actual = {'bytes': info.st_size, 'sha256': hashlib.sha256(host_file.read_bytes()).hexdigest(), 'uid': info.st_uid, 'gid': info.st_gid}
        assert actual == expected
        history = arr.json('GET', 'history', query=history_query)
        events = sorted({r['eventType'] for r in history['records']})
        assert 'grabbed' in events and 'downloadFolderImported' in events
        stage = 'restart persistence'
        restart()
        arr = wait_for(lambda: app_client(config, controller, app))
        assert arr.json('GET', media_endpoint)[file_id_field] == file['id']
        assert hashlib.sha256(host_file.read_bytes()).hexdigest() == expected['sha256']
        result = {'status': 'passed', 'pipeline': 'native release decision -> SAB NNTP/yEnc -> completed-download import',
                  'generated_file': actual, 'history_events': events, 'app': app, 'media_file_id': file['id'],
                  'advertised_release_size': 'synthetic 4GiB metadata; actual bytes above',
                  'providers': 'loopback generated fixture only; not real indexer/NNTP acceptance', 'restart': 'passed'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result), flush=True)
    except Exception:
        print(json.dumps({'failed_stage': stage}), flush=True)
        raise
    finally:
        controller.stop(); remove_owned(controller)
        network = project + '_web'
        if subprocess.run(controller.docker + ['network', 'inspect', network], capture_output=True).returncode == 0:
            controller.run(controller.docker + ['network', 'rm', network])


if __name__ == '__main__':
    main()
