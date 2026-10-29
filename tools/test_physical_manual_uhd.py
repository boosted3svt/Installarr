"""Manual UHD movie assignment survives HD-preferred installer reconciliation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, configure_apps, wait_for
from installarr.credentials import read_private_credentials
from installarr.directories import prepare_directories
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    fixture = Path('/var/tmp/installarr-arr-import-4gd29mnj')
    config = json.loads((fixture / 'config.json').read_text())
    assert config['apps'] == ['radarr', 'sabnzbd']
    assert config['data_root'] == '/media/installarr/Installarr-Arr-Import-2b3a21fb'
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    work = Path(tempfile.mkdtemp(prefix='installarr-manual-uhd-', dir='/var/tmp'))
    controller = reference_controller(config, 'installarr-arr-import-2b3a21fb', published=False)
    assert controller.inventory() == []
    print(json.dumps({'evidence': str(work), 'fixture_config': str(fixture / 'config.json')}), flush=True)
    prepare_directories(config, fixture / 'directories')
    write_reference_bundle(config, published=False)
    def restart():
        controller.stop(); controller.reconcile()
    try:
        controller.reconcile()
        evidence = configure_apps(config, controller, credentials, restart, download_host='sabnzbd')
        arr = app_client(config, controller, 'radarr')
        assert arr.json('GET', 'indexer') == []
        profiles = evidence['radarr']['quality_profiles']
        hd = profiles['preferred_id']
        uhd_key = config['quality_profiles']['radarr']['available'][1]
        uhd = profiles['available'][uhd_key]['id']
        movie = next(row for row in arr.json('GET', 'movie') if row.get('tmdbId') == 10331)
        assert movie['hasFile']
        file = arr.json('GET', 'moviefile/' + str(movie['movieFileId']))
        path = Path(config['data_root']) / Path(movie['path']).relative_to('/data') / file['relativePath']
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        before_file = movie['movieFileId']
        original_profile = movie['qualityProfileId']
        movie['qualityProfileId'] = uhd
        arr.json('PUT', 'movie/' + str(movie['id']), movie)
        assert arr.json('GET', 'movie/' + str(movie['id']))['qualityProfileId'] == uhd
        restart()
        after = configure_apps(config, controller, credentials, restart, download_host='sabnzbd')
        arr = wait_for(lambda: app_client(config, controller, 'radarr'))
        saved = arr.json('GET', 'movie/' + str(movie['id']))
        assert after['radarr']['quality_profiles']['preferred_id'] == hd
        assert saved['qualityProfileId'] == uhd and saved['movieFileId'] == before_file
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        assert arr.json('GET', 'indexer') == []
        result = {'status': 'passed', 'original_movie_profile_id': original_profile,
                  'installer_preferred_hd_id': hd, 'manual_movie_uhd_id': uhd,
                  'after_restart_rerun': saved['qualityProfileId'], 'movie_file_id': before_file,
                  'generated_video_sha256': digest, 'generated_video': 'unchanged',
                  'indexers': 'none; no media downloads attempted',
                  'staged_setting': 'only this disposable generated movie retains manual UHD assignment'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        controller.stop(); remove_owned(controller)
        network = controller.project + '_web'
        if subprocess.run(controller.docker + ['network', 'inspect', network], capture_output=True).returncode == 0:
            controller.run(controller.docker + ['network', 'rm', network])


if __name__ == '__main__':
    main()
