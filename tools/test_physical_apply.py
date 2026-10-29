"""Minimal app/SAB apply, failure stop, CLI resume and persistence experiment."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import ApplyError, apply, wait_for
from installarr.cli import save_config
from installarr.credentials import initialize_credentials
from installarr.directories import observed_mount
from installarr.lifecycle import Controller, LifecycleError, SOCKET, command, service_status


def main(app):
    if command(['docker', '--host', SOCKET, 'ps', '--all', '--quiet']):
        raise ValueError('Existing isolated test workloads preserved')
    fd = os.open('/media/installarr', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    expected = {'target': '/media/installarr', 'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'}
    try:
        if observed_mount(fd) != expected:
            raise ValueError('Exact test export required')
    finally:
        os.close(fd)
    tag = uuid.uuid4().hex[:10]
    name = 'apply-' + tag
    base = Path('/media/installarr') / ('Installarr-Apply-Test-' + tag)
    work = Path(tempfile.mkdtemp(prefix='installarr-apply-', dir='/var/tmp'))
    config = {'schema_version': 1, 'apps': [app, 'sabnzbd'], 'timezone': 'America/Chicago',
        'bind_address': '127.0.0.1', 'plex_allowed_networks': '192.168.0.0/23',
        'service_user': {'name': 'installarr-test', 'uid': 2000, 'gid': 2000}, 'project_directory': str(work / 'project'),
        'storage': {**{key: str(base / key) for key in ('media', 'downloads', 'incomplete')},
                    'configs': str(work / 'configs'), 'backups': str(work / 'backups')},
        'storage_mounts': {**{key: {'kind': 'existing', 'mountpoint': expected['target'], 'source': expected['source'],
                                  'fstype': 'nfs', 'sentinel': 'health'} for key in ('media', 'downloads', 'incomplete')},
                           'configs': {'kind': 'local'}, 'backups': {'kind': 'local'}}}
    save_config(work / 'config.json', config)
    password = secrets.token_urlsafe(36)
    initialize_credentials(work / 'seed', lambda: {'username': 'installarr-apply-admin', 'password': password})
    credentials_file = work / 'seed/gui-admin.json'
    state = work / 'state'
    unit = 'installarr-' + name + '.service'
    controller = Controller(config, 'installarr-' + name)
    stage = 'injected_failure'
    try:
        print(json.dumps({'test_directory': str(base), 'local_evidence': str(work), 'unit': unit}), flush=True)
        with patch('installarr.apply.configure_apps', side_effect=ApplyError('Injected interruption before app settings')):
            try:
                apply(config, name, state_directory=state, credentials_file=credentials_file)
            except ApplyError as error:
                if str(error) != 'Injected interruption before app settings':
                    raise
            else:
                raise ValueError('Injected failure was not observed')
        rows = controller.inventory()
        if len(rows) != 2 or any(row['State']['Running'] for row in rows):
            raise ValueError('Failure did not stop only managed containers')
        checkpoint = json.loads((state / 'state.json').read_text())
        if checkpoint['steps'].get('applications') != 'failed':
            raise ValueError('Failure checkpoint missing')
        stage = 'cli_resume'
        args = [sys.executable, '-B', '-m', 'installarr', 'apply', '--config', str(work / 'config.json'),
                '--name', name, '--state-directory', str(state)]
        result = subprocess.run(args, capture_output=True, text=True, timeout=300)
        if result.returncode:
            print(result.stdout)
            print(result.stderr)
            raise ValueError('CLI resume failed')
        evidence = json.loads(result.stdout)
        if evidence.get('status') != 'isolated_configured':
            raise ValueError('Wrong apply result')
        before = {row['Config']['Labels']['com.docker.compose.service']: row['Id'] for row in controller.inventory()}
        stage = 'rerun'
        result2 = subprocess.run(args, capture_output=True, text=True, timeout=300)
        if result2.returncode:
            print(result2.stdout)
            print(result2.stderr)
            raise ValueError('CLI rerun failed')
        after = {row['Config']['Labels']['com.docker.compose.service']: row['Id'] for row in controller.inventory()}
        if before != after:
            raise ValueError('Rerun replaced containers')
        first_ids = evidence['applications'][app]
        second_ids = json.loads(result2.stdout)['applications'][app]
        if first_ids['root_id'] != second_ids['root_id'] or first_ids['downloader'] != second_ids['downloader']:
            raise ValueError('Rerun changed root/downloader IDs')
        if not controller.audit(controller.inventory()):
            raise ValueError('Supervisor topology audit failed')
        stage = 'namespace_owner_restart'
        owner = next(row for row in controller.inventory() if row['Config']['Labels']['com.docker.compose.service'] == 'sabnzbd')
        command(controller.docker + ['restart', owner['Id']])
        def recovered():
            try:
                return controller.audit(controller.inventory())
            except LifecycleError:
                return False
        wait_for(recovered)
        stage = 'storage_closes_gui'
        wait_for(lambda: service_status(name).get('health', {}).get('gui', {}).get('enabled'))
        mediafd = os.open(str(base / 'media'), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            if observed_mount(mediafd) != expected:
                raise ValueError('Test mount changed before owned marker rename')
            def marker_move(source, target):
                script = "import os,sys; os.setgroups([]); os.setgid(2000); os.setuid(2000); os.rename(sys.argv[2],sys.argv[3],src_dir_fd=int(sys.argv[1]),dst_dir_fd=int(sys.argv[1]))"
                subprocess.run([sys.executable, '-B', '-c', script, str(mediafd), source, target],
                               pass_fds=(mediafd,), check=True, timeout=10)
            marker_move('health', 'health-paused')
            try:
                wait_for(lambda: service_status(name).get('phase') == 'waiting_storage')
                for port in (8080, 7878 if app == 'radarr' else 8989):
                    connection = socket.socket()
                    try:
                        connection.settimeout(1)
                        if connection.connect_ex(('127.0.0.1', port)) == 0:
                            raise ValueError('GUI still reachable after storage failure')
                    finally:
                        connection.close()
                if any(row['State']['Running'] for row in controller.inventory()):
                    raise ValueError('Storage failure left apps running')
            finally:
                marker_move('health-paused', 'health')
            wait_for(lambda: service_status(name).get('health', {}).get('gui', {}).get('enabled'))
        finally:
            os.close(mediafd)
        stage = 'failure_after_success'
        with patch('installarr.apply.configure_apps', side_effect=ApplyError('Injected interruption after previous success')):
            try:
                apply(config, name, state_directory=state)
            except ApplyError as error:
                if str(error) != 'Injected interruption after previous success':
                    raise
            else:
                raise ValueError('Second interruption not observed')
        if json.loads((state / 'state.json').read_text()).get('phase') != 'failed':
            raise ValueError('Previous ready phase survived a failed rerun')
        if any(row['State']['Running'] for row in controller.inventory()):
            raise ValueError('Failed rerun left apps running')
        resumed = subprocess.run(args, capture_output=True, text=True, timeout=300)
        if resumed.returncode:
            print(resumed.stdout); print(resumed.stderr)
            raise ValueError('Second CLI recovery failed')
        if password in result.stdout + result.stderr + result2.stdout + result2.stderr:
            raise ValueError('Secret appeared in output')
        for path in state.rglob('state.json'):
            if password in path.read_text():
                raise ValueError('Secret appeared in checkpoints')
        enabled = subprocess.run(['systemctl', 'is-enabled', unit], capture_output=True, text=True)
        if enabled.stdout.strip() != 'disabled':
            raise ValueError('Apply unexpectedly enabled boot execution')
        print(json.dumps({'result': 'passed', 'app': app, 'failure_stopped_managed_containers': True,
                          'cli_resume_and_rerun': 'passed', 'namespace_owner_restart_recovery': True,
                          'failed_rerun_cleared_ready_phase': True, 'storage_failure_closed_gui_and_recovered': True, 'stable_root_downloader_and_container_ids': True,
                          'credentials_absent_from_output_and_checkpoints': True, 'apply': evidence,
                          'retained_evidence': str(work), 'retained_nas_test_directory': str(base)}, indent=2), flush=True)
    except Exception:
        print(json.dumps({'failed_stage': stage}), flush=True)
        raise
    finally:
        if Path('/var/lib/installarr-services', name, 'definition.json').exists():
            command(['systemctl', 'stop', unit])
            controller.stop()
        rows = controller.inventory()
        ids = [row['Id'] for row in rows if controller.owns(row)]
        if ids:
            command(controller.docker + ['rm', *ids])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', choices=('radarr', 'sonarr'), default='radarr')
    main(parser.parse_args().app)
