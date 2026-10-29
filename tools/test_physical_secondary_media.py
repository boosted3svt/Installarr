"""Unclaimed, unpublished Plex secondary-source startup/UID/supervision fixture."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.directories import prepare_directories
from installarr.lifecycle import command, install_service, service_status
from installarr.plex import PlexClient, PlexHTTP, reference_libraries
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-secondary-', dir='/var/tmp'))
    name = 'secondary-' + uuid.uuid4().hex[:8]
    config = json.loads(Path('/var/tmp/installarr-bazarr-test-d5rjwtr7/config.json').read_text())
    config.update(apps=['plex'], project_directory=str(work / 'project'), plex_libraries=reference_libraries())
    for key in ('quality_profiles', 'providers', 'provider_secrets_file', 'plex_claim_file', 'bazarr_language_profile'):
        config.pop(key, None)
    data = Path('/media/installarr') / ('Installarr-Secondary-Primary-' + name)
    secondary = Path('/media/installarr') / ('Installarr-Secondary-Source-' + name)
    observed = json.loads(command(['findmnt', '--json', '--target', '/media/installarr', '--output', 'TARGET,SOURCE,FSTYPE']))['filesystems']
    assert observed == [{'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}]
    config['data_root'] = str(data)
    config['storage'].update(media=str(data / 'media'), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete'),
                             configs=str(work / 'configs'), backups=str(work / 'backups'), media_secondary=str(secondary))
    check = {'mountpoint': '/media/installarr', 'source': observed[0]['source'], 'fstype': 'nfs', 'sentinel': 'source-ready'}
    config['storage_mounts']['media_secondary'] = dict(check, kind='existing')
    # Only new owned fixture directories/files are created before invoking the
    # adapter. The adapter must neither create nor write this source.
    def identity():
        os.setgroups([]); os.setgid(2000); os.setuid(2000)
    subprocess.run([sys.executable, '-c',
        'import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(mode=0o750); (p/"source-ready").write_text("fixture ready\\n"); (p/"owned-fixture.txt").write_text("Installarr secondary source\\n")', str(secondary)], preexec_fn=identity, check=True)
    config_path = work / 'config.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n'); config_path.chmod(0o600)
    print(json.dumps({'evidence': str(work), 'unit': 'installarr-' + name + '.service'}), flush=True)
    controller = reference_controller(config, 'installarr-' + name, published=False)
    marker = secondary / 'source-ready'
    held = secondary / 'source-ready.held'
    try:
        before = {p.name: (p.read_bytes(), p.stat().st_uid, p.stat().st_gid, p.stat().st_mtime_ns) for p in secondary.iterdir()}
        directories = prepare_directories(config, work / 'directories')
        read_result = next(r for r in directories['directories'] if r['path'] == str(secondary))
        assert read_result['read_verified'] and not read_result['write_verified']
        assert before == {p.name: (p.read_bytes(), p.stat().st_uid, p.stat().st_gid, p.stat().st_mtime_ns) for p in secondary.iterdir()}
        write_reference_bundle(config, published=False)
        install_service(config, name, reference=True, bootstrap=True)
        command(['systemctl', 'start', 'installarr-' + name + '.service'])
        wait_for(lambda: service_status(name).get('phase') == 'containers_running')
        row = next(r for r in controller.inventory() if r['State']['Running'])
        container = row['Id']
        status = wait_for(PlexClient(PlexHTTP('unix:///run/docker.sock', container)).status)
        assert not status['claimed']
        assert not row['HostConfig']['PortBindings']
        command(controller.docker + ['exec', '--user', '2000:2000', container, '/bin/sh', '-c',
            'test -r /media-secondary/owned-fixture.txt && ! touch /media-secondary/not-permitted'])
        assert not (secondary / 'not-permitted').exists()
        marker.rename(held)
        try:
            wait_for(lambda: service_status(name).get('phase') == 'waiting_storage')
            assert all(not r['State']['Running'] for r in controller.inventory())
        finally:
            held.rename(marker)
        wait_for(lambda: service_status(name).get('phase') == 'containers_running')
        after = {p.name: (p.read_bytes(), p.stat().st_uid, p.stat().st_gid, p.stat().st_mtime_ns) for p in secondary.iterdir()}
        assert before == after
        result = {'secondary_source': str(secondary), 'read_only_bind': 'UID2000 read passed, write refused',
                  'directory_adapter': read_result, 'supervision': 'marker loss stopped; restoration recovered',
                  'files_metadata': 'unchanged', 'plex_status': status,
                  'ports': 'unpublished', 'claimed_library_gui_acceptance': 'deferred; fresh claim/operator scope required'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        if held.exists() and not marker.exists():
            held.rename(marker)
        unit = Path('/etc/systemd/system/installarr-' + name + '.service')
        if unit.exists():
            command(['systemctl', 'stop', unit.name])
        remove_owned(controller)
        network = controller.project + '_web'
        if subprocess.run(controller.docker + ['network', 'inspect', network], capture_output=True).returncode == 0:
            command(controller.docker + ['network', 'rm', network])


if __name__ == '__main__':
    main()
