"""Detach only an owned bind of the approved NAS export; preserve live deployments."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.cli import save_config
from installarr.directories import observed_mount
from installarr.lifecycle import command, service_status
from installarr.reference import apply_reference, reference_controller, remove_owned

SOURCE = '192.168.1.102:/share/MD0_DATA/Public/installarr'


def main():
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        assert observed_mount(fd) == {'target': '/media/installarr', 'source': SOURCE, 'fstype': 'nfs'}
    finally:
        os.close(fd)
    work = Path(tempfile.mkdtemp(prefix='installarr-mount-detach-', dir='/var/tmp'))
    mount = work / 'mount'
    mount.mkdir()
    tag = uuid.uuid4().hex[:8]
    name = 'mount-detach-' + tag
    data = mount / ('Installarr-Mount-Detach-' + tag)
    config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    config.update(apps=['sabnzbd'], bind_address='127.0.0.1', data_root=str(data), project_directory=str(work / 'project'))
    for key in ('quality_profiles', 'providers', 'provider_secrets_file', 'plex_libraries', 'plex_claim_file', 'ombi_family_presets'):
        config.pop(key, None)
    config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                             configs=str(work / 'configs'), backups=str(work / 'backups'))
    for purpose in ('media', 'downloads', 'incomplete'):
        old = config['storage_mounts'][purpose]
        old.update(kind='existing', mountpoint=str(mount), source=SOURCE, fstype='nfs')
        if purpose in config.get('storage_checks', {}):
            config['storage_checks'][purpose].update(mountpoint=str(mount), source=SOURCE, fstype='nfs')
    save_config(work / 'config.json', config)
    print(json.dumps({'evidence': str(work), 'unit': 'installarr-' + name + '.service',
                      'detach_target': str(mount), 'retained_mount': '/media/installarr'}), flush=True)
    mounted = False
    try:
        subprocess.run(['mount', '--bind', '/media/installarr', str(mount)], check=True, timeout=15)
        mounted = True
        apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        controller = reference_controller(config, 'installarr-' + name)
        assert all(row['State']['Running'] for row in controller.inventory())
        # Ordinary unmount only. A busy refusal is evidence, never a reason to force/lazy unmount.
        detached = subprocess.run(['umount', '--', str(mount)], capture_output=True, timeout=15)
        if detached.returncode:
            raise RuntimeError('Ordinary disposable-mount unmount refused; no force/lazy fallback attempted')
        mounted = False
        wait_for(lambda: service_status(name).get('phase') == 'waiting_storage')
        assert all(not row['State']['Running'] for row in controller.inventory())
        assert list(mount.iterdir()) == [], 'Unexpected local fallback writes'
        subprocess.run(['mount', '--bind', '/media/installarr', str(mount)], check=True, timeout=15)
        mounted = True
        wait_for(lambda: service_status(name).get('phase') == 'containers_running')
        assert all(row['State']['Running'] for row in controller.inventory())
        result = {'status': 'passed', 'ordinary_unmount': 'owned bind only', 'stopped_on_missing_mount': True,
                  'local_fallback_directory_empty': True, 'healthy_remount_recovered': True,
                  'retained_export_mount': 'unchanged', 'network_server_outage': 'not simulated',
                  'fixture_config': str(work / 'config.json'), 'unit': 'installarr-' + name + '.service'}
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
        if mounted:
            subprocess.run(['umount', '--', str(mount)], check=True, timeout=15)


if __name__ == '__main__':
    main()
