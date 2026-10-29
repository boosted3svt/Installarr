"""Published netboot.xyz existing-image Nginx auth/apply acceptance."""
import argparse
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.lifecycle import command
from installarr.reference import apply_reference, reference_controller, remove_owned


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--storage', choices=('local', 'nfs'), default='local')
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix='installarr-netboot-assets-', dir='/var/tmp'))
    config = json.loads(Path('/var/tmp/installarr-bazarr-test-d5rjwtr7/config.json').read_text())
    config.update(apps=['netbootxyz'], project_directory=str(work / 'project'))
    config['storage'].update(configs=str(work / 'configs'), backups=str(work / 'backups'))
    config.pop('quality_profiles', None)
    if args.storage == 'local':
        from installarr.lifecycle import local_mount
        observed = local_mount(work)
        asset_path = work / 'assets'
        check = {'mountpoint': observed['target'], 'source': observed['source'], 'fstype': observed['fstype'], 'sentinel': 'assets-ready'}
        mount = {'kind': 'local'}
    else:
        asset_path = Path('/media/installarr') / ('Installarr-Netboot-Assets-' + work.name.rsplit('-', 1)[1])
        check = {'mountpoint': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs', 'sentinel': 'assets-ready'}
        mount = dict(check, kind='existing')
    config['storage']['netboot_assets'] = str(asset_path)
    config['storage_mounts']['netboot_assets'] = mount
    config.setdefault('storage_checks', {})['netboot_assets'] = check
    path = work / 'config.json'
    path.write_text(json.dumps(config, indent=2) + '\n')
    path.chmod(0o600)
    name = 'netboot-assets-' + uuid.uuid4().hex[:8]
    print(json.dumps({'evidence': str(work), 'unit': 'installarr-' + name + '.service'}), flush=True)
    try:
        first = apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        second = apply_reference(config, name, work / 'state')
        assert first['applications']['netbootxyz']['host_gui_authentication'] == second['applications']['netbootxyz']['host_gui_authentication']
        from installarr.writecheck import probe_service_write
        # Directory preparation already checks writes using held FDs; network path
        # also permits a direct host service probe without private local ancestors.
        probe = probe_service_write(str(asset_path), check, 911, 1001) if args.storage == 'nfs' else {'status': 'covered by directory worker'}
        if args.storage == 'nfs':
            assert probe['status'] == 'verified'
        controller = reference_controller(config, 'installarr-' + name)
        container = next(row['Id'] for row in controller.inventory() if row['Config']['Labels']['com.docker.compose.service'] == 'netbootxyz')
        controller.run(controller.docker + ['exec', '--user', '911:1001', container, '/bin/sh', '-c',
            'test -r /assets/assets-ready; printf "Installarr asset persistence\\n" > /assets/installarr-fixture.txt'])
        assert (asset_path / 'installarr-fixture.txt').read_text() == 'Installarr asset persistence\n'
        assert ((asset_path / 'installarr-fixture.txt').stat().st_uid, (asset_path / 'installarr-fixture.txt').stat().st_gid) == (911, 1001)
        command(['systemctl', 'restart', 'installarr-' + name + '.service'])
        from installarr.apply import wait_for
        from installarr.lifecycle import service_status
        wait_for(lambda: service_status(name).get('phase') == 'containers_running')
        assert (asset_path / 'installarr-fixture.txt').read_text() == 'Installarr asset persistence\n'
        loss_recovery = 'not exercised'
        if args.storage == 'nfs':
            marker = asset_path / check['sentinel']
            held = asset_path / (check['sentinel'] + '.held')
            assert not held.exists()
            marker.rename(held)
            try:
                wait_for(lambda: service_status(name).get('phase') == 'waiting_storage')
                assert all(not row['State']['Running'] for row in controller.inventory())
                assert (asset_path / 'installarr-fixture.txt').read_text() == 'Installarr asset persistence\n'
            finally:
                held.rename(marker)
            wait_for(lambda: service_status(name).get('phase') == 'containers_running')
            loss_recovery = 'marker loss stopped owned container; restoration recovered it'
        result = {'loss_recovery': loss_recovery, 'asset_storage': args.storage, 'asset_path': str(asset_path), 'service_write': probe, 'first': first, 'rerun': second, 'dhcp_pxe': 'out of scope'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'published_auth': second['applications']['netbootxyz'], 'rerun': 'passed'}), flush=True)
    finally:
        for suffix in ('', '-boot'):
            unit = 'installarr-' + name + suffix + '.service'
            if not Path('/etc/systemd/system/' + unit).exists():
                continue
            command(['systemctl', 'stop', unit])
            controller = reference_controller(config, 'installarr-' + name) if not suffix else reference_controller(
                dict(config, project_directory=str(work / 'state/bootstrap')), 'installarr-' + name + suffix, published=False)
            remove_owned(controller)
            network = controller.project + '_web'
            if subprocess.run(controller.docker + ['network', 'inspect', network], capture_output=True).returncode == 0:
                controller.run(controller.docker + ['network', 'rm', network])


if __name__ == '__main__':
    main()
