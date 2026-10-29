"""Minimal unpublished Ombi/Arr fixture; retain evidence, remove own containers."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, configure_apps, wait_for
from installarr.arr import AppAPIError
from installarr.cli import save_config
from installarr.credentials import read_private_credentials
from installarr.directories import observed_mount, prepare_directories
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--app', choices=('radarr', 'sonarr'), default='radarr')
    parser.add_argument('--request', action='store_true')
    parser.add_argument('--family-user', choices=('lenora8', 'rebel739', 'beanie08'))
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
    work = Path(tempfile.mkdtemp(prefix='installarr-ombi-arr-test-', dir='/var/tmp'))
    tag = uuid.uuid4().hex[:8]
    data = Path('/media/installarr') / ('Installarr-Ombi-Arr-' + tag)
    config.update(apps=[args.app, 'ombi'], data_root=str(data), project_directory=str(work / 'project'))
    config['storage'] = {'media': str(data), 'downloads': str(data / 'downloads'),
                         'incomplete': str(data / 'incomplete-downloads'),
                         'configs': str(work / 'configs'), 'backups': str(work / 'backups')}
    from installarr.profiles import recommended_profiles
    config['quality_profiles'] = recommended_profiles([args.app])
    if args.resume:
        work = args.resume
        config = json.loads((work / 'config.json').read_text())
        data = Path(config['data_root'])
        tag = data.name[len('Installarr-Ombi-Arr-'):]
    else:
        save_config(work / 'config.json', config)
    print(json.dumps({'evidence': str(work), 'nas_fixture': str(data)}), flush=True)
    prepare_directories(config, work / 'directories')
    write_reference_bundle(config, published=False)
    controller = reference_controller(config, 'installarr-ombi-arr-' + tag, published=False)
    def restart():
        controller.stop()
        controller.reconcile()
    try:
        controller.reconcile()
        first = configure_apps(config, controller, credentials, restart, download_host='sabnzbd')
        from installarr.ombi_family import FAMILY, family_paths, import_family, configure_family
        # Plan only the extra directories; do not start a second Plex instance.
        family_config = dict(config, apps=config['apps'] + ['plex'], ombi_family_presets=True)
        prepare_directories(family_config, work / 'family-directories')
        backend = app_client(config, controller, args.app)
        routes = {name: {} for name in FAMILY}
        for name, paths in family_paths(config).items():
            routes[name] = {args.app + 'RootPath': backend.ensure_root(paths[args.app]['container_path']),
                            args.app + 'QualityProfile': first[args.app]['quality_profiles']['preferred_id']}
        ombi = app_client(config, controller, 'ombi')
        plex_config = json.loads(Path('/var/tmp/installarr-plex-standard-2bbujwqu/config.json').read_text())
        plex = app_client(plex_config, reference_controller(plex_config, 'installarr-plex-standard-test'), 'plex')
        libraries = [{'id': row.get('key'), 'name': row.get('title')} for row in plex.xml('/library/sections')]
        controller.run(controller.docker + ['network', 'connect', 'installarr-plex-standard-test_web', ombi.transport.container])
        try:
            with ombi.administrator(credentials):
                ombi.connect_plex(plex.transport.api_key, plex.status()['machine_identifier'], libraries, 'Installarr Test')
                import_family(ombi, wait_for, work / 'family-import', plex.status()['machine_identifier'])
                family = configure_family(ombi, routes)
        finally:
            controller.run(controller.docker + ['network', 'disconnect', 'installarr-plex-standard-test_web', ombi.transport.container])
        with ombi.administrator(credentials):
            endpoint = '/api/v1/Settings/' + args.app
            before = ombi.json('GET', endpoint)
            candidate = dict(before['radarr'] if args.app == 'radarr' else before)
            candidate['apiKey'] = '0' * 32
            rejected = False
            try:
                response = ombi.json('POST', '/api/v1/' + args.app.capitalize() + '/Profiles', candidate)
                rejected = not isinstance(response, list) or not response
            except AppAPIError:
                rejected = True
            assert rejected, 'Ombi accepted a wrong remote key'
            assert before == ombi.json('GET', endpoint)
        restart()
        second = configure_apps(config, controller, credentials, restart, download_host='sabnzbd')
        ombi = app_client(config, controller, 'ombi')
        backend = app_client(config, controller, args.app)
        dispatches = {}
        with ombi.administrator(credentials):
            assert configure_family(ombi, routes) == family
            movie = args.app == 'radarr'
            for name, media_id in zip(FAMILY, (10331, 10513, 961) if movie else (301824, 79257, 78874)):
                if args.family_user and name != args.family_user:
                    continue
                payload = ({'theMovieDbId': media_id, 'is4kRequest': False, 'languageCode': 'en'} if movie else
                           {'tvDbId': media_id, 'firstSeason': True, 'requestAll': False,
                            'seasons': [{'seasonNumber': 1, 'episodes': [{'episodeNumber': 1}]}]})
                payload['requestOnBehalf'] = family[name]['id']
                response = ombi.json('POST', '/api/v1/Request/' + ('movie' if movie else 'tv'), payload)
                (work / ('request-' + name + '.json')).write_text(json.dumps(response))
                assert response.get('result') is True, 'Family request refused; private evidence retained'
                def find():
                    return next((row for row in backend.json('GET', 'movie' if movie else 'series')
                                 if row.get('tmdbId' if movie else 'tvdbId') == media_id), None)
                item = wait_for(find)
                path = family_paths(config).get(name, {}).get(args.app, {}).get('container_path') or second['ombi']['integrations'][args.app]['root_path']
                assert item['path'].startswith(path + '/')
                assert item['qualityProfileId'] == second[args.app]['quality_profiles']['preferred_id']
                dispatches[name] = {'id': item['id'], 'path': item['path'], 'profile_id': item['qualityProfileId']}
                # Match an operator's sequential requests while upstream background writes settle.
                import time
                time.sleep(2)
        restart()
        ombi = wait_for(lambda: app_client(config, controller, 'ombi'))
        backend = app_client(config, controller, args.app)
        with ombi.administrator(credentials):
            assert configure_family(ombi, routes) == family
        retained = {row['id']: row for row in backend.json('GET', 'movie' if args.app == 'radarr' else 'series')}
        for row in dispatches.values():
            assert retained[row['id']]['path'] == row['path']
            assert retained[row['id']]['qualityProfileId'] == row['profile_id']
        import sqlite3
        dbcon = sqlite3.connect('file:' + str(work / 'configs/ombi/Ombi.db') + '?mode=ro', uri=True)
        rows = dbcon.execute('SELECT UserName,UserType,ProviderUserId,PasswordHash FROM AspNetUsers WHERE UserType != 0').fetchall()
        assert {row[0].lower() for row in rows} == set(FAMILY) | {credentials['username'].lower()}
        assert all(row[1] == 2 and row[2] and not row[3] for row in rows if row[0].lower() in FAMILY)
        dbcon.close()
        dispatch = {'family_on_behalf_requests': dispatches, 'restart_persistence': 'verified',
                    'family_plex_gui_login': 'not tested'}
        if args.request:
            ombi = app_client(config, controller, 'ombi')
            backend = app_client(config, controller, args.app)
            with ombi.administrator(credentials):
                movie = args.app == 'radarr'
                response = ombi.json('POST', '/api/v1/Request/' + ('movie' if movie else 'tv'),
                    {'theMovieDbId': 10331, 'is4kRequest': False, 'languageCode': 'en'} if movie else
                    {'tvDbId': 301824, 'firstSeason': True, 'requestAll': False,
                     'seasons': [{'seasonNumber': 1, 'episodes': [{'episodeNumber': 1}]}]})
                (work / 'request-response.json').write_text(json.dumps(response))
                assert response.get('result') is True, 'Ombi request rejected; private evidence retained'
                def find_request():
                    rows = backend.json('GET', 'movie' if movie else 'series')
                    return next((r for r in rows if r.get('tmdbId' if movie else 'tvdbId') == (10331 if movie else 301824)), None)
                item = wait_for(find_request)
                expected = second['ombi']['integrations'][args.app]
                assert item['qualityProfileId'] == expected['profile_id']
                assert item['path'].startswith(expected['root_path'] + '/')
                assert item['monitored'] is True
                dispatch = {'remote_id': item['id'], 'profile_id': item['qualityProfileId'],
                            'path': item['path'], 'monitored': item['monitored'],
                            'download': 'not tested; no indexer/downloader configured'}
        db = work / 'configs/ombi/Ombi.db'
        owner = [db.stat().st_uid, db.stat().st_gid]
        assert owner == [2000, 2000]
        assert first['ombi']['integrations'] == second['ombi']['integrations']
        result = {'first': first, 'after_restart_and_rerun': second, 'database_owner': owner,
                  'container_audit': controller.audit(controller.inventory()), 'wrong_key_remote_lookup': 'rejected before save', 'request_dispatch': dispatch}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        remove_owned(controller)
        # The fixture network is empty after scoped container removal.
        controller.run(controller.docker + ['network', 'rm', controller.project + '_web'])


if __name__ == '__main__':
    main()
