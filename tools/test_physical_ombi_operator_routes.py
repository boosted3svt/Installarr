"""Exercise family-equivalent permissions with only the operator's own Plex identity."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, wait_for
from installarr.credentials import read_private_credentials
from installarr.directories import prepare_directories
from installarr.execution import Execution
from installarr.reference import reference_controller

WORK = Path('/var/tmp/installarr-ombi-family-gui-o799mzbk')


def main():
    config = json.loads((WORK / 'config.json').read_text())
    arr_config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    plex_config = json.loads(Path('/var/tmp/installarr-plex-standard-2bbujwqu/config.json').read_text())
    arr = app_client(arr_config, reference_controller(arr_config, 'installarr-poc-http-d29db77d'), 'radarr')
    plex = app_client(plex_config, reference_controller(plex_config, 'installarr-plex-standard-test'), 'plex')
    ombi = app_client(config, reference_controller(config, 'installarr-ombi-family-2274744e'), 'ombi')
    credentials = read_private_credentials(WORK / 'state/secrets/gui-admin.json')
    assert arr.json('GET', 'indexer') == [], 'Request test refuses configured indexers'
    with Execution(WORK / 'operator-route-journal', {'operation': 'operator-plex-routing-v1'}) as journal:
        def restore():
            saved = journal.state['restore_user']
            with ombi.administrator(credentials):
                assert ombi.json('PUT', '/api/v1/Identity', saved)['successful'] is True
                actual = ombi.json('GET', '/api/v1/Identity/User/' + saved['id'])
                assert sorted((x['value'], x['enabled']) for x in actual['claims']) == sorted((x['value'], x['enabled']) for x in saved['claims'])
                assert all(actual['userQualityProfiles'].get(k) == v for k, v in saved['userQualityProfiles'].items() if k not in ('id', 'userId'))
            journal.state.pop('restore_user')
            journal._save()
        if 'restore_user' in journal.state:
            restore()
        with ombi.administrator(credentials):
            original = next(row for row in ombi.json('GET', '/api/v1/Identity/Users') if row['userName'].lower() == 'boosted3svt')
            assert original['userType'] == 2
            original['password'] = None
            settings = ombi.json('GET', '/api/v1/Settings/radarr')['radarr']
        hd = int(settings['defaultQualityProfile'])
        roots = {}
        for label, leaf in (('lenora', 'lenoramovies'), ('jeremy', 'jeremymovies')):
            # Directory-only subset: SAB has no additional media-library children.
            shadow = dict(arr_config, apps=['sabnzbd'], storage=dict(arr_config['storage'], media=str(Path(arr_config['storage']['media']) / leaf)))
            shadow.pop('quality_profiles', None)
            prepare_directories(shadow, WORK / ('operator-' + label + '-directories'))
            roots[label] = arr.ensure_root('/data/' + leaf)
        journal.state['restore_user'] = original
        journal._save()
        result = {}
        try:
            for label, media_id in (('lenora', 10331), ('jeremy', 10513), ('beanie', 3085)):
                roles = {'RequestMovie', 'RequestTv', 'AutoApproveMovie', 'AutoApproveTv'}
                if label == 'beanie':
                    roles.add('PowerUser')
                claims = [dict(row, enabled=row['value'] in roles) for row in original['claims']]
                profiles = dict(original['userQualityProfiles'])
                for key in profiles:
                    if key not in ('id', 'userId'):
                        profiles[key] = 0
                if label != 'beanie':
                    profiles.update(radarrQualityProfile=hd, radarrRootPath=roots[label])
                desired = dict(original, claims=claims, userQualityProfiles=profiles)
                with ombi.administrator(credentials):
                    assert ombi.json('PUT', '/api/v1/Identity', desired)['successful'] is True
                with ombi.plex_identity(plex.transport.api_key):
                    identity = ombi.json('GET', '/api/v1/Identity')
                    assert identity['id'] == original['id'] and identity['userType'] == 2
                    assert not any(row['value'] == 'Admin' and row['enabled'] for row in identity['claims'])
                    assert arr.json('GET', 'indexer') == []
                    existing = [row for row in ombi.json('GET', '/api/v1/Request/movie') if row.get('theMovieDbId') == media_id]
                    if not existing:
                        response = ombi.json('POST', '/api/v1/Request/movie', {'theMovieDbId': media_id, 'is4kRequest': False, 'languageCode': 'en'})
                        assert response.get('result') is True, 'Regular-user request refused'
                    def remote():
                        return next((row for row in arr.json('GET', 'movie') if row.get('tmdbId') == media_id), None)
                    movie = wait_for(remote)
                    expected = settings['defaultRootPath'] if label == 'beanie' else '/data/' + ('lenoramovies' if label == 'lenora' else 'jeremymovies')
                    assert movie['path'].startswith(expected + '/') and movie['qualityProfileId'] == hd
                    request = next(row for row in ombi.json('GET', '/api/v1/Request/movie') if row.get('theMovieDbId') == media_id)
                    assert request['requestedUserId'] == original['id']
                    result[label] = {'username': 'boosted3svt', 'administrator': False, 'path': movie['path'],
                                     'profile_id': movie['qualityProfileId'], 'identity_verified': True}
                import time
                time.sleep(2)
        finally:
            restore()
        result['original_operator_settings'] = 'restored and read back'
        result['downloads'] = 'not tested; no indexers'
        (WORK / 'operator-routes-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
