"""Generated-video acceptance through normal Radarr scans and Bazarr scheduler jobs.

No supplied media is copied/modified. No indexer/downloader is selected. All writes
are to a new asserted NAS fixture and private local application directories.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, configure_apps, wait_for
from installarr.cli import save_config
from installarr.credentials import read_private_credentials
from installarr.directories import observed_mount, prepare_directories
from installarr.profiles import recommended_profiles
from installarr.providers import SUBTITLES, load_selected_secrets
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--regenerate-video', action='store_true')
    args = parser.parse_args()
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        assert observed_mount(fd) == {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    finally:
        os.close(fd)
    if args.resume:
        work = args.resume
        config = json.loads((work / 'config.json').read_text())
        tag = config['fixture_tag'] if 'fixture_tag' in config else Path(config['data_root']).name.rsplit('-', 1)[1]
    else:
        work = Path(tempfile.mkdtemp(prefix='installarr-bazarr-scheduled-', dir='/var/tmp'))
        tag = uuid.uuid4().hex[:8]
        data = Path('/media/installarr') / ('Installarr-Bazarr-Scheduled-' + tag)
        config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
        config.update(apps=['radarr', 'bazarr'], data_root=str(data), project_directory=str(work / 'project'),
                      quality_profiles=recommended_profiles(['radarr']), bazarr_language_profile='english-standard',
                      providers={'bazarr': {'enabled': list(SUBTITLES)}},
                      provider_secrets_file='/var/tmp/installarr-providers-secrets/providers.json')
        config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                                 configs=str(work / 'configs'), backups=str(work / 'backups'))
        save_config(work / 'config.json', config)
    data = Path(config['data_root'])
    project = 'installarr-bazarr-scheduled-' + tag
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    provider_credentials = load_selected_secrets(config)
    print(json.dumps({'evidence': str(work), 'nas_fixture': str(data), 'project': project}), flush=True)
    prepare_directories(config, work / 'directories')
    write_reference_bundle(config, published=False)
    controller = reference_controller(config, project, published=False)
    stage = 'startup'
    def restart():
        controller.stop()
        controller.reconcile()
    def configure():
        return configure_apps(config, controller, credentials, restart, download_host='sabnzbd', provider_credentials=provider_credentials)
    try:
        controller.reconcile()
        first = configure()
        arr = app_client(config, controller, 'radarr')
        bazarr = app_client(config, controller, 'bazarr')
        assert arr.json('GET', 'indexer') == [] and arr.json('GET', 'downloadclient') == []
        stage = 'movie metadata'
        rows = arr.json('GET', 'movie')
        movie = next((row for row in rows if row.get('tmdbId') == 10331), None)
        if not movie:
            lookup = arr.json('GET', 'movie/lookup', query={'term': 'tmdb:10331'})
            assert len(lookup) == 1
            payload = dict(lookup[0], qualityProfileId=first['radarr']['quality_profiles']['preferred_id'],
                           rootFolderPath='/data/Movies', monitored=True, minimumAvailability='released',
                           addOptions={'searchForMovie': False})
            movie = arr.json('POST', 'movie', payload)
        assert movie['path'].startswith('/data/Movies/') and '..' not in PurePosixPath(movie['path']).parts
        container_movie = movie['path'] + '/Night of the Living Dead (1968) WEBDL-1080p.mkv'
        host_movie = data / container_movie[len('/data/'):]
        stage = 'generated video'
        if not host_movie.exists() or args.regenerate_video:
            controller.run(controller.docker + ['exec', '--user', '2000:2000', bazarr.transport.container, 'python3', '-c',
                'import os,sys;os.makedirs(sys.argv[1],exist_ok=True)', movie['path']])
            # Sparse-in-time real video:90 frames of black over90min, no copied content.
            controller.run(controller.docker + ['exec', '--user', '2000:2000', bazarr.transport.container, 'ffmpeg',
                '-hide_banner', '-loglevel', 'error', '-nostdin', '-f', 'lavfi', '-i', 'color=c=black:s=1920x1080:r=1/60:d=5400',
                '-f', 'lavfi', '-i', 'anullsrc=r=8000:cl=mono', '-t', '5400',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-b:a', '8k',
                '-metadata:s:a:0', 'language=eng', '-y', container_movie], timeout=90)
        generated = {'bytes': host_movie.stat().st_size, 'sha256': hashlib.sha256(host_movie.read_bytes()).hexdigest()}
        assert (host_movie.stat().st_uid, host_movie.stat().st_gid) == (2000, 2000)
        stage = 'Radarr scan'
        arr.json('POST', 'command', {'name': 'RescanMovie', 'movieId': movie['id']})
        def scanned():
            row = arr.json('GET', 'movie/' + str(movie['id']))
            return row if row.get('hasFile') else None
        movie = wait_for(scanned)
        stage = 'Bazarr sync'
        tasks = bazarr.json('system/tasks')['data']
        task_ids = {row['job_id'] for row in tasks}
        def trigger(identity):
            assert identity in task_ids, 'Expected native scheduled task unavailable'
            code, _ = bazarr.transport.request('POST', '/api/system/tasks', form={'taskid': identity})
            assert code == 204
        trigger('update_movies')
        def synced():
            return next((row for row in bazarr.json('movies')['data'] if row.get('radarrId') == movie['id']), None)
        synced_movie = wait_for(synced)
        assert synced_movie['profileId'] == first['bazarr']['subtitle_profile']['profile_id']
        stage = 'scheduled subtitle search'
        trigger('movies_full_scan_subtitles')
        trigger('wanted_search_missing_subtitles_movies')
        until = time.monotonic() + 240
        subtitle = None
        while time.monotonic() < until:
            subtitle = next((path for path in host_movie.parent.glob('*.srt') if path.stat().st_size > 100), None)
            if subtitle:
                break
            time.sleep(1)
        assert subtitle, 'Scheduled search did not produce a subtitle; secret-free API evidence retained'
        subtitle_result = {'file': str(subtitle.relative_to(data)), 'bytes': subtitle.stat().st_size,
                           'sha256': hashlib.sha256(subtitle.read_bytes()).hexdigest(),
                           'uid': subtitle.stat().st_uid, 'gid': subtitle.stat().st_gid}
        assert (subtitle_result['uid'], subtitle_result['gid']) == (2000, 2000)
        assert hashlib.sha256(host_movie.read_bytes()).hexdigest() == generated['sha256']
        stage = 'restart persistence'
        restart()
        second = configure()
        bazarr = app_client(config, controller, 'bazarr')
        retained = next(row for row in bazarr.json('movies')['data'] if row.get('radarrId') == movie['id'])
        assert retained['profileId'] == synced_movie['profileId']
        result = {'first': first, 'rerun': second, 'generated_video': generated, 'radarr_id': movie['id'],
                  'scheduled_jobs': ['update_movies', 'movies_full_scan_subtitles', 'wanted_search_missing_subtitles_movies'],
                  'subtitle': subtitle_result, 'original_supplied_media': 'never bound or copied', 'generated_video_unchanged': True}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'scheduled_pipeline': 'passed', 'subtitle': subtitle_result, 'generated_video_unchanged': True}), flush=True)
    except BaseException:
        (work / 'failure.json').write_text(json.dumps({'stage': stage, 'project': project}) + '\n')
        raise
    finally:
        remove_owned(controller)
        network = controller.project + '_web'
        if controller.run(controller.docker + ['network', 'ls', '--filter', 'name=^' + network + '$', '--format', '{{.Name}}']) == network:
            controller.run(controller.docker + ['network', 'rm', network])


if __name__ == '__main__':
    main()
