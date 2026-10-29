"""Real operator Plex authentication and request dispatch to an owned test root.

Uses the retained POC Radarr with no indexers, preserving existing records and
assignments. No tokens, credentials or request bodies are printed.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, wait_for
from installarr.credentials import read_private_credentials
from installarr.directories import prepare_directories
from installarr.profiles import RECOMMENDED, ensure_profile
from installarr.reference import reference_controller

WORK = Path('/var/tmp/installarr-ombi-family-gui-o799mzbk')
OWNER = 'boosted3svt'
TMDB_ID = 961


def main():
    config = json.loads((WORK / 'config.json').read_text())
    arr_config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    plex_config = json.loads(Path('/var/tmp/installarr-plex-standard-2bbujwqu/config.json').read_text())
    arr = app_client(arr_config, reference_controller(arr_config, 'installarr-poc-http-d29db77d'), 'radarr')
    plex = app_client(plex_config, reference_controller(plex_config, 'installarr-plex-standard-test'), 'plex')
    ombi = app_client(config, reference_controller(config, 'installarr-ombi-family-2274744e'), 'ombi')
    assert arr.json('GET', 'indexer') == [], 'Refuse request test with configured indexers'
    original_movies = arr.json('GET', 'movie')
    media = Path(arr_config['storage']['media']) / 'Ombi-Operator-Test'
    shadow = dict(arr_config, storage=dict(arr_config['storage'], media=str(media)))
    prepare_directories(shadow, WORK / 'operator-request-directories')
    root_path = '/data/Ombi-Operator-Test/Movies'
    root = arr.ensure_root(root_path)
    profile = ensure_profile(arr, 'radarr', RECOMMENDED['radarr']['default'])['id']
    credentials = read_private_credentials(WORK / 'state/secrets/gui-admin.json')
    with ombi.administrator(credentials):
        link = ombi.connect_arr('radarr', arr.transport.api_key, profile, root, root_path, host='10.70.0.99')
    with ombi.plex_identity(plex.transport.api_key):
        identity = ombi.json('GET', '/api/v1/Identity')
        assert identity['userName'].lower() == OWNER and identity['userType'] == 2
        rows = ombi.json('GET', '/api/v1/Request/movie')
        matching = [row for row in rows if row.get('theMovieDbId') == TMDB_ID]
        if not matching:
            assert arr.json('GET', 'indexer') == []
            response = ombi.json('POST', '/api/v1/Request/movie', {'theMovieDbId': TMDB_ID, 'is4kRequest': False, 'languageCode': 'en'})
            assert response.get('result') is True, 'Operator request rejected'
        def request():
            rows = ombi.json('GET', '/api/v1/Request/movie')
            return next((row for row in rows if row.get('theMovieDbId') == TMDB_ID), None)
        saved = wait_for(request)
        assert saved['requestedUserId'] == identity['id'], 'Requested identity differs'
        def remote_movie():
            return next((row for row in arr.json('GET', 'movie') if row.get('tmdbId') == TMDB_ID), None)
        movie = wait_for(remote_movie)
        assert movie['qualityProfileId'] == profile and movie['path'].startswith(root_path + '/')
        assert movie['monitored'] is True
    assert ombi.transport.api_key == ''
    after = {row['id']: row for row in arr.json('GET', 'movie')}
    for row in original_movies:
        assert after[row['id']]['path'] == row['path'] and after[row['id']]['qualityProfileId'] == row['qualityProfileId']
    result = {'username': OWNER, 'identity': 'native Plex-authenticated', 'request_user_id_verified': True,
              'request_id': saved['id'], 'radarr_id': movie['id'], 'profile_id': profile, 'path': movie['path'],
              'existing_assignments': 'preserved', 'indexers': 0, 'download': 'not tested', 'integration': link}
    (WORK / 'operator-request-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
