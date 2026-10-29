"""Prepare one new all-app acceptance config without starting a second live stack."""
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.cli import save_config
from installarr.directories import observed_mount
from installarr.lifecycle import local_mount
from installarr.plex import reference_libraries
from installarr.profiles import recommended_profiles
from installarr.reference import apply_reference


def main():
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        assert observed_mount(fd) == {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    finally:
        os.close(fd)
    tag = uuid.uuid4().hex[:8]
    work = Path(tempfile.mkdtemp(prefix='installarr-fresh-acceptance-', dir='/var/tmp'))
    fixture = Path('/media/installarr') / ('Installarr-Fresh-Acceptance-' + tag)
    assert not fixture.exists()
    config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    apps = ['sabnzbd', 'sonarr', 'radarr', 'bazarr', 'jackett', 'plex', 'ombi', 'tautulli', 'netbootxyz']
    config.update(apps=apps, data_root=str(fixture / 'Primary'), project_directory=str(work / 'project'),
                  quality_profiles=recommended_profiles(apps), plex_server_name='Installarr Fresh Acceptance',
                  plex_libraries=reference_libraries(), plex_claim_file=str(work / 'claim' / 'plex-claim.txt'),
                  ombi_family_presets=True, ombi_family_preferences_file='/var/lib/installarr-setup/family/family.json',
                  bazarr_language_profile='english-standard', secondary_media_read_only=False,
                  providers={'newshosting': {'connections': 100}, 'nzbgeek': {}, 'bazarr': {'enabled': ['opensubtitlescom']}},
                  provider_secrets_file='/var/tmp/installarr-providers-secrets/providers.json')
    data = Path(config['data_root'])
    config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                             configs=str(work / 'apps'), backups=str(work / 'backups'),
                             media_secondary=str(fixture / 'AdditionalMovies'), netboot_assets=str(work / 'netboot-assets'))
    config['storage_mounts']['media_secondary'] = dict(config['storage_mounts']['media'])
    config.setdefault('storage_checks', {})['media_secondary'] = dict(config['storage_mounts']['media'])
    config['storage_checks']['media_secondary'].pop('kind', None)
    local = local_mount(work)
    config['storage_mounts']['netboot_assets'] = {'kind': 'local'}
    config['storage_checks']['netboot_assets'] = {'mountpoint': local['target'], 'source': local['source'], 'fstype': local['fstype'], 'sentinel': 'assets-ready'}
    save_config(work / 'config.json', config)
    name = 'freshcheck-' + tag
    print(json.dumps({'evidence': str(work), 'name': name, 'generated_fixture': str(fixture), 'status': 'preparing'}), flush=True)
    result = apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'), prepare_only=True)
    manifest = {'name': name, 'config': str(work / 'config.json'), 'state': str(work / 'state'), 'status': result['status'],
                'apps': apps, 'generated_fixture': str(fixture), 'claim_store': str(work / 'claim'),
                'new_containers_started': False, 'remaining': 'fresh Plex claim and coordinated temporary switch of retained test ports',
                'retained_units': ['installarr-poc-http-d29db77d.service', 'installarr-plex-standard-test.service', 'installarr-ombi-family-2274744e.service'],
                'production_exports': 'not accessed; owned test-export paths only'}
    (work / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__':
    main()
