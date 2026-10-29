"""Import the operator's real Plex owner into the retained sign-in fixture."""
import json
from pathlib import Path
import sqlite3
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, wait_for
from installarr.credentials import read_private_credentials
from installarr.execution import Execution
from installarr.lifecycle import command
from installarr.ombi_family import settings_values
from installarr.plex import PREFERENCES
from installarr.reference import reference_controller


EXPECTED = 'boosted3svt'
WORK = Path('/var/tmp/installarr-ombi-family-gui-o799mzbk')
UNIT = 'installarr-ombi-family-2274744e.service'


def main():
    config = json.loads((WORK / 'config.json').read_text())
    plex_config = json.loads(Path('/var/tmp/installarr-plex-standard-2bbujwqu/config.json').read_text())
    prefs = ET.parse(str(Path(plex_config['storage']['configs']) / 'plex' / PREFERENCES)).getroot()
    assert (prefs.get('PlexOnlineUsername') or '').lower() == EXPECTED, 'Claimed Plex owner differs; no import attempted'
    credentials = read_private_credentials(WORK / 'state/secrets/gui-admin.json')
    controller = reference_controller(config, 'installarr-ombi-family-2274744e')
    client = app_client(config, controller, 'ombi')
    endpoint = '/api/v1/Settings/UserManagement'
    with client.administrator(credentials), Execution(WORK / 'operator-import', {'operation': 'ombi-owner-gui-v1', 'username': EXPECTED}) as journal:
        def restore(original):
            assert client.json('POST', endpoint, original) is True, 'Import settings restoration refused'
            assert settings_values(client.json('GET', endpoint)) == settings_values(original), 'Import settings restoration differs'
            journal.state.pop('restore_settings', None)
            journal._save()
        if journal.state.get('restore_settings') is not None:
            restore(journal.state['restore_settings'])
        def owner():
            rows = client.json('GET', '/api/v1/Identity/Users')
            selected = [row for row in rows if row['userName'].lower() == EXPECTED]
            assert len(selected) <= 1, 'Duplicate operator identity'
            if selected:
                assert selected[0]['userType'] == 2, 'Existing local lookalike preserved'
                return selected[0]
            return None
        user = owner()
        if user is None:
            original = client.json('GET', endpoint)
            assert not any(original.get(key) for key in ('importPlexAdmin', 'importPlexUsers', 'cleanupPlexUsers')), 'Existing scheduled import preserved'
            before = {row['id'] for row in client.json('GET', '/api/v1/Identity/Users')}
            journal.state['restore_settings'] = original
            journal._save()
            try:
                desired = dict(original, importPlexAdmin=True, importPlexUsers=False, cleanupPlexUsers=False)
                assert client.json('POST', endpoint, desired) is True
                assert settings_values(client.json('GET', endpoint)) == settings_values(desired)
                assert client.json('POST', '/api/v1/Job/plexuserimporter') is True
                user = wait_for(owner)
                after = {row['id'] for row in client.json('GET', '/api/v1/Identity/Users')}
                assert after - before == {user['id']}, 'Unexpected additional identity imported'
            finally:
                restore(original)
        expected_id = user['id']
    command(['systemctl', 'restart', UNIT])
    client = wait_for(lambda: app_client(config, controller, 'ombi'))
    authentication = client.verify_admin(credentials)
    with client.administrator(credentials):
        user = client.json('GET', '/api/v1/Identity/User/' + expected_id)
        assert user['userName'].lower() == EXPECTED and user['userType'] == 2
        assert any(row['value'] == 'Admin' and row['enabled'] for row in user['claims'])
        assert not client.json('GET', endpoint)['importPlexAdmin']
    database = Path(config['storage']['configs']) / 'ombi/Ombi.db'
    connection = sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True)
    try:
        kind, provider, password = connection.execute('SELECT UserType, ProviderUserId, PasswordHash FROM AspNetUsers WHERE Id = ?', (expected_id,)).fetchone()
        assert kind == 2 and provider and not password
    finally:
        connection.close()
    result = {'username': EXPECTED, 'identity': 'existing Plex owner', 'local_password_created': False,
              'administrator': True, 'restart_persistence': 'verified', 'import_flags_restored': True,
              'shared_admin_authentication': authentication, 'gui': 'http://10.70.0.99:3579'}
    (WORK / 'operator-import-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
