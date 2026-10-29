"""Reference secondary movies: native Radarr root/Bazarr access, generated empty paths only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client
from installarr.cli import save_config
from installarr.directories import observed_mount
from installarr.lifecycle import command
from installarr.reference import apply_reference, reference_controller, remove_owned
from installarr.storage_process import run_storage


def main():
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    expected = {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    try:
        assert observed_mount(fd) == expected
    finally:
        os.close(fd)
    tag = uuid.uuid4().hex[:8]
    work = Path(tempfile.mkdtemp(prefix='installarr-secondary-writable-', dir='/var/tmp'))
    fixture = Path('/media/installarr') / ('Installarr-Writable-Secondary-' + tag)
    assert not fixture.exists()
    data = fixture / 'Primary'
    config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    config.update(apps=['radarr', 'bazarr'], bind_address='127.0.0.1', data_root=str(data),
                  project_directory=str(work / 'project'), secondary_media_read_only=False)
    for key in ('providers', 'provider_secrets_file', 'plex_claim_file', 'plex_libraries', 'ombi_family_presets'):
        config.pop(key, None)
    config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                             configs=str(work / 'configs'), backups=str(work / 'backups'), media_secondary=str(fixture / 'Movies'))
    config['storage_mounts']['media_secondary'] = dict(config['storage_mounts']['media'])
    config.setdefault('storage_checks', {})['media_secondary'] = dict(config['storage_mounts']['media'])
    config['storage_checks']['media_secondary'].pop('kind', None)
    save_config(work / 'config.json', config)
    name = 'secondary-rw-' + tag
    print(json.dumps({'evidence': str(work), 'unit': 'installarr-' + name + '.service'}), flush=True)
    try:
        first = apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        second = apply_reference(config, name, work / 'state')
        controller = reference_controller(config, 'installarr-' + name)
        radarr = app_client(config, controller, 'radarr')
        roots = radarr.json('GET', 'rootfolder')
        assert any(r['path'] == '/media-secondary' for r in roots)
        for row in controller.inventory():
            app = row['Config']['Labels']['com.docker.compose.service']
            mounts = [m for m in row['Mounts'] if m['Destination'] == '/media-secondary']
            assert len(mounts) == 1 and mounts[0]['RW']
            controller.run(controller.docker + ['exec', '--user', '2000:2000', row['Id'], '/bin/sh', '-c',
                'printf "fixture-only write\\n" > /media-secondary/.installarr-' + app + '-probe'])
        assert first['applications']['radarr']['additional_root_ids'] == second['applications']['radarr']['additional_root_ids']
        result = {'status': 'passed', 'native_radarr_secondary_root': 'verified', 'bazarr_shared_path_write': 'verified',
                  'both_service_uid': 2000, 'rerun_root_ids': 'stable', 'real_media': 'none bound or modified',
                  'cleanup': 'owned generated NAS fixture removed after containers stopped'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        for suffix in ('', '-boot'):
            unit = 'installarr-' + name + suffix + '.service'
            if not Path('/etc/systemd/system/' + unit).exists():
                continue
            command(['systemctl', 'stop', unit])
            candidate = config if not suffix else dict(config, project_directory=str(work / 'state/bootstrap'))
            controller = reference_controller(candidate, 'installarr-' + name + suffix, published=not suffix)
            remove_owned(controller)
            network = controller.project + '_web'
            if subprocess.run(controller.docker + ['network', 'inspect', network], capture_output=True).returncode == 0:
                controller.run(controller.docker + ['network', 'rm', network])
        cleanup = run_storage([sys.executable, '-B', '-c',
            'import os,shutil,sys;from installarr.directories import observed_mount;'
            'fd=os.open("/media/installarr",os.O_RDONLY|os.O_DIRECTORY);'
            'assert observed_mount(fd)=='+repr(expected)+';os.close(fd);shutil.rmtree(sys.argv[1])', str(fixture)],
            timeout=15, operation='owned-fixture-cleanup')
        if cleanup.returncode:
            raise RuntimeError('Owned fixture cleanup needs review; original media untouched')


if __name__ == '__main__':
    main()
