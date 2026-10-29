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
    work = Path(tempfile.mkdtemp(prefix='installarr-bazarr-providers-', dir='/var/tmp'))
    tag = uuid.uuid4().hex[:8]
    data = Path('/media/installarr') / ('Installarr-Bazarr-' + tag)
    config.update(apps=[args.app, 'bazarr'], data_root=str(data), project_directory=str(work / 'project'))
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
        provider_credentials = {'username': 'installarr-unused-synthetic', 'password': 'installarr-unused-synthetic'}
        selected = bazarr_providers(bazarr, list(SUBTITLES), provider_credentials)
        restart()
        second = configure_apps(config, controller, credentials, restart, download_host='sabnzbd')
        bazarr = app_client(config, controller, 'bazarr')
        repeated = bazarr_providers(bazarr, list(SUBTITLES), provider_credentials)
        assert selected == repeated
        db = work / 'configs/bazarr/db/bazarr.db'
        owner = [db.stat().st_uid, db.stat().st_gid]
        assert owner == [2000, 2000]
        result = {'first': first, 'after_restart_and_rerun': second, 'database_owner': owner,
                  'container_audit': controller.audit(controller.inventory()), 'provider_settings': selected, 'provider_search': 'not tested; empty library and synthetic credentials'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        remove_owned(controller)
        # The fixture network is empty after scoped container removal.
        controller.run(controller.docker + ['network', 'rm', controller.project + '_web'])


if __name__ == '__main__':
    main()
