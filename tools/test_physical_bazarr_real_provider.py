"""Minimal unpublished Bazarr/Radarr fixture; retain evidence, remove own containers."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, configure_apps, wait_for
from installarr.cli import save_config
from installarr.credentials import read_private_credentials
from installarr.directories import observed_mount, prepare_directories
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--app', choices=('radarr', 'sonarr'), default='radarr')
    args = parser.parse_args()
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        assert observed_mount(fd) == {'target': '/media/installarr',
            'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    finally:
        os.close(fd)
    base = Path('/var/tmp/installarr-reference-poc-fz5b_65a')
    config = json.loads((base / 'config.json').read_text())
    credentials = read_private_credentials(base / 'state/secrets/gui-admin.json')
    work = Path(tempfile.mkdtemp(prefix='installarr-bazarr-english-', dir='/var/tmp'))
    tag = uuid.uuid4().hex[:8]
    data = Path('/media/installarr') / ('Installarr-Bazarr-' + tag)
    config.update(apps=[args.app, 'bazarr'], bazarr_language_profile='english-standard', data_root=str(data), project_directory=str(work / 'project'))
    config['storage'] = {'media': str(data), 'downloads': str(data / 'downloads'),
                         'incomplete': str(data / 'incomplete-downloads'),
                         'configs': str(work / 'configs'), 'backups': str(work / 'backups')}
    if args.resume:
        work = args.resume
        config = json.loads((work / 'config.json').read_text())
        data = Path(config['data_root'])
        tag = data.name[len('Installarr-Bazarr-'):]
    else:
        save_config(work / 'config.json', config)
    print(json.dumps({'evidence': str(work), 'nas_fixture': str(data)}), flush=True)
    prepare_directories(config, work / 'directories')
    write_reference_bundle(config, published=False)
    controller = reference_controller(config, 'installarr-bazarr-' + tag, published=False)
    def restart():
        controller.stop()
        controller.reconcile()
    try:
        controller.reconcile()
        first = configure_apps(config, controller, credentials, restart, download_host='sabnzbd')
        from installarr.providers import SUBTITLES, bazarr_providers
        bazarr = app_client(config, controller, 'bazarr')
        from installarr.provider_secrets import read_provider_secrets
        provider_credentials = read_provider_secrets('/var/tmp/installarr-providers-secrets/providers.json')['opensubtitlescom']
        selected = bazarr_providers(bazarr, list(SUBTITLES), provider_credentials)
        import subprocess
        import xml.etree.ElementTree as ET
        plex_config = json.loads(Path('/var/tmp/installarr-plex-standard-2bbujwqu/config.json').read_text())
        plex = app_client(plex_config, reference_controller(plex_config, 'installarr-plex-standard-test'), 'plex')
        code, body = plex.transport.request('GET', '/library/metadata/1', query={'includeGuids': 1})
        assert code == 200
        metadata = ET.fromstring(body).find('Video')
        imdb = next((row.get('id').split('://', 1)[1] for row in metadata.findall('Guid') if row.get('id', '').startswith('imdb://')), None)
        probe = subprocess.run(controller.docker + ['exec', '--interactive', '--user', '2000:2000', bazarr.transport.container, 'python3', '-B', '-c',
            Path(__file__).with_name('bazarr_provider_probe.py').read_text()],
            input=json.dumps({'credentials': provider_credentials, 'title': metadata.get('title'), 'year': int(metadata.get('year')), 'imdb_id': imdb, 'download': True}),
            capture_output=True, text=True, timeout=90)
        (work / 'probe-result.json').write_text(probe.stdout)
        print(probe.stdout, flush=True)
        assert probe.returncode == 0, 'Native provider probe failed; secret-free result retained'
        search = json.loads(probe.stdout)
        restart()
        second = configure_apps(config, controller, credentials, restart, download_host='sabnzbd')
        bazarr = app_client(config, controller, 'bazarr')
        repeated = bazarr_providers(bazarr, list(SUBTITLES), provider_credentials)
        assert selected == repeated
        assert first['bazarr']['subtitle_profile'] == second['bazarr']['subtitle_profile']
        db = work / 'configs/bazarr/db/bazarr.db'
        owner = [db.stat().st_uid, db.stat().st_gid]
        assert owner == [2000, 2000]
        result = {'first': first, 'after_restart_and_rerun': second, 'database_owner': owner,
                  'container_audit': controller.audit(controller.inventory()), 'provider_settings': selected, 'provider_search': search}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        remove_owned(controller)
        # The fixture network is empty after scoped container removal.
        controller.run(controller.docker + ['network', 'rm', controller.project + '_web'])


if __name__ == '__main__':
    main()
