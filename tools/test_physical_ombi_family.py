"""Unpublished Ombi local-admin bootstrap; real read-only Plex lookup and availability sync."""
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.credentials import read_private_credentials
from installarr.lifecycle import command
from installarr.ombi import IMAGE, OmbiClient, OmbiHTTP


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-ombi-plex-', dir='/var/tmp'))
    config = work / 'config'
    config.mkdir(mode=0o700)
    os.chown(config, 2000, 2000)
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    name = 'installarr-ombi-' + uuid.uuid4().hex[:8]
    print(json.dumps({'evidence': str(work), 'container': name}), flush=True)
    container = command(docker + ['run', '--detach', '--name', name, '--network', 'installarr-plex-standard-test_web', '--restart', 'no',
        '--env', 'PUID=2000', '--env', 'PGID=2000', '--env', 'TZ=America/Chicago',
        '--mount', 'type=bind,source=' + str(config) + ',target=/config,bind-propagation=rprivate', IMAGE])
    client = OmbiClient(OmbiHTTP('unix:///run/docker.sock', container))
    try:
        wait_for(client.status)
        first = client.configure_admin(credentials)
        from installarr.apply import app_client
        from installarr.reference import reference_controller
        plex_config = json.loads(Path('/var/tmp/installarr-plex-standard-2bbujwqu/config.json').read_text())
        controller = reference_controller(plex_config, 'installarr-plex-standard-test')
        plex = app_client(plex_config, controller, 'plex')
        status = plex.status()
        libraries = [{'id': int(row.get('key')), 'name': row.get('title')}
                     for row in plex.xml('/library/sections').findall('Directory')]
        with client.administrator(credentials):
            linked = client.connect_plex(plex.transport.api_key, status['machine_identifier'],
                                         libraries, 'Installarr Test')
        with client.administrator(credentials):
            friends = client.json('GET', '/api/v1/Plex/friends')
            targets = {'lenora8', 'rebel739', 'beanie08'}
            visible = [{'username': row.get('username'), 'id': row.get('id')} for row in friends
                       if (row.get('username') or '').lower() in targets]
            print(json.dumps({'family_accounts_visible': visible, 'other_account_count': len(friends) - len(visible)}), flush=True)
            (work / 'family-discovery.json').write_text(json.dumps({'targets': visible, 'total': len(friends)}))
        from installarr.ombi_family import FAMILY, import_family_once, configure_family
        with client.administrator(credentials):
            imported = import_family_once(client, wait_for)
            family = configure_family(client, {name: {} for name in FAMILY})
            print(json.dumps({'family_import_and_roles': family}), flush=True)
        import sqlite3
        def sync_counts():
            db = sqlite3.connect('file:' + str(config / 'OmbiExternal.db') + '?mode=ro', uri=True)
            try:
                movies = db.execute("SELECT COUNT(*) FROM PlexServerContent WHERE Title = ?", ('Framing Britney Spears',)).fetchone()[0]
                shows = db.execute("SELECT COUNT(*) FROM PlexServerContent WHERE Title = ?", ('11.22.63',)).fetchone()[0]
                episodes = db.execute('SELECT COUNT(*) FROM PlexEpisode').fetchone()[0]
                return {'movie': movies, 'show': shows, 'episodes': episodes} if movies and shows and episodes else None
            finally:
                db.close()
        synced = wait_for(sync_counts)
        command(docker + ['restart', container])
        wait_for(client.status)
        second = client.verify_admin(credentials)
        assert first == second
        assert sync_counts() == synced
        with client.administrator(credentials):
            retained = client.connect_plex(plex.transport.api_key, status['machine_identifier'],
                                           libraries, 'Installarr Test')
            assert retained == linked
        with client.administrator(credentials):
            assert configure_family(client, {name: {} for name in FAMILY}) == family
        owners = {p.name: [p.stat().st_uid, p.stat().st_gid] for p in config.glob('*.db')}
        assert owners and all(owner == [2000, 2000] for owner in owners.values())
        result = {'first': first, 'after_restart': second, 'database_owners': owners,
                  'plex_link': linked, 'content_sync': synced, 'family': family, 'family_login_and_routes': 'not tested'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        command(docker + ['stop', '--time', '5', container])
        command(docker + ['rm', container])


if __name__ == '__main__':
    main()
