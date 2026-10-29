"""SIGKILL the importing CLI after temporary settings; recover in an unpublished fixture."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, wait_for
from installarr.credentials import read_private_credentials
from installarr.execution import Execution
from installarr.lifecycle import command
from installarr.ombi import IMAGE, OmbiClient, OmbiHTTP
from installarr.ombi_family import FAMILY, family_users, import_family, settings_values
from installarr.reference import reference_controller

CREDENTIALS = '/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'


def fault(work):
    scenario = json.loads((work / 'scenario.json').read_text())
    client = OmbiClient(OmbiHTTP('unix:///run/docker.sock', scenario['container']))
    with client.administrator(read_private_credentials(CREDENTIALS)), Execution(work / 'import',
            {'operation': 'ombi-family-import-v1', 'machine_identifier': scenario['machine_identifier']}) as journal:
        endpoint = '/api/v1/Settings/UserManagement'
        original = client.json('GET', endpoint)
        friends = client.json('GET', '/api/v1/Plex/friends')
        excluded = [str(row['id']) for row in friends if str(row.get('username', '')).lower() not in FAMILY]
        journal.state['restore_settings'] = original
        journal._save()
        assert client.json('POST', endpoint, dict(original, importPlexUsers=True, importPlexAdmin=False,
            cleanupPlexUsers=False, defaultRoles=[], bannedPlexUserIds=excluded)) is True
        assert client.json('GET', endpoint)['importPlexUsers'] is True
        os.kill(os.getpid(), signal.SIGKILL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fault', type=Path)
    args = parser.parse_args()
    if args.fault:
        fault(args.fault)
        return
    work = Path(tempfile.mkdtemp(prefix='installarr-ombi-import-recovery-', dir='/var/tmp'))
    directory = work / 'config'
    directory.mkdir(mode=0o700)
    os.chown(str(directory), 2000, 2000)
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    name = 'installarr-ombi-recovery-' + uuid.uuid4().hex[:8]
    container = command(docker + ['run', '--detach', '--name', name, '--network', 'installarr-plex-standard-test_web',
        '--restart', 'no', '--env', 'PUID=2000', '--env', 'PGID=2000', '--env', 'TZ=America/Chicago',
        '--mount', 'type=bind,source=' + str(directory) + ',target=/config,bind-propagation=rprivate', IMAGE])
    print(json.dumps({'evidence': str(work), 'container': name}), flush=True)
    client = OmbiClient(OmbiHTTP('unix:///run/docker.sock', container))
    try:
        wait_for(client.status)
        credentials = read_private_credentials(CREDENTIALS)
        client.configure_admin(credentials)
        config = json.loads(Path('/var/tmp/installarr-plex-standard-2bbujwqu/config.json').read_text())
        plex = app_client(config, reference_controller(config, 'installarr-plex-standard-test'), 'plex')
        machine = plex.status()['machine_identifier']
        libraries = [{'id': row.get('key'), 'name': row.get('title')} for row in plex.xml('/library/sections')]
        with client.administrator(credentials):
            client.connect_plex(plex.transport.api_key, machine, libraries, 'Installarr Test')
        scenario = work / 'scenario.json'
        scenario.write_text(json.dumps({'container': container, 'machine_identifier': machine}))
        scenario.chmod(0o600)
        process = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--fault', str(work)],
                                 capture_output=True, timeout=90)
        assert process.returncode == -signal.SIGKILL, 'Fault did not reach intended checkpoint'
        state = json.loads((work / 'import/state.json').read_text())
        assert 'restore_settings' in state
        original = state['restore_settings']
        with client.administrator(credentials):
            assert client.json('GET', '/api/v1/Settings/UserManagement')['importPlexUsers'] is True
            users = import_family(client, wait_for, work / 'import', machine)
            identities = {name: row['id'] for name, row in users.items()}
            assert settings_values(client.json('GET', '/api/v1/Settings/UserManagement')) == settings_values(original)
            assert len(client.json('GET', '/api/v1/Identity/Users')) == 4
        assert 'restore_settings' not in json.loads((work / 'import/state.json').read_text())
        command(docker + ['restart', container])
        wait_for(client.status)
        client.verify_admin(credentials)
        with client.administrator(credentials):
            rerun = import_family(client, wait_for, work / 'import', machine)
            assert {name: row['id'] for name, row in rerun.items()} == identities
            assert settings_values(client.json('GET', '/api/v1/Settings/UserManagement')) == settings_values(original)
        result = {'interrupted_cli': 'SIGKILL after temporary settings', 'durable_journal': 'recovered and cleared',
                  'selected_plex_users': list(FAMILY), 'other_users_imported': 0,
                  'settings_restored': True, 'restart_and_rerun': 'stable native identities'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        command(docker + ['stop', '--time', '5', container])
        command(docker + ['rm', container])


if __name__ == '__main__':
    main()
