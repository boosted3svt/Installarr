"""Preparation rerun must not restart an already ready owned disposable pair."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.lifecycle import command, root_json, SERVICE_ROOT, service_status
from installarr.reference import apply_reference, reference_controller, remove_owned


def main():
    name = 'optional-f238598b'
    fixture = Path('/var/tmp/installarr-optional-pair-48lode31')
    config = json.loads((fixture / 'config.json').read_text())
    assert config['apps'] == ['tautulli', 'ombi'] and config['bind_address'] == '127.0.0.1'
    assert root_json(SERVICE_ROOT / name / 'definition.json')['config'] == config
    controller = reference_controller(config, 'installarr-' + name)
    assert controller.inventory() == [], 'Disposable fixture must begin removed/stopped'
    work = Path(tempfile.mkdtemp(prefix='installarr-prepare-preserves-', dir='/var/tmp'))
    unit = 'installarr-' + name + '.service'
    print(json.dumps({'evidence': str(work), 'unit': unit}), flush=True)
    try:
        command(['systemctl', 'start', unit])
        wait_for(lambda: service_status(name).get('phase') == 'containers_running')
        def snapshot():
            return {row['Id']: {'started_at': row['State']['StartedAt'], 'running': row['State']['Running']}
                    for row in controller.inventory()}
        before = snapshot()
        pid = command(['systemctl', 'show', unit, '--property=MainPID', '--value'])
        phase = json.loads((fixture / 'state/state.json').read_text())['phase']
        prepared = apply_reference(config, name, fixture / 'state', prepare_only=True)
        assert snapshot() == before
        assert command(['systemctl', 'show', unit, '--property=MainPID', '--value']) == pid
        assert json.loads((fixture / 'state/state.json').read_text())['phase'] == phase == 'reference_poc_ready'
        assert command(['systemctl', 'is-active', unit]) == 'active'
        # Host preparation errors must not stop existing apps in prepare-only mode.
        with patch('installarr.reference.prepare_directories', side_effect=ValueError('synthetic preparation refusal')):
            try:
                apply_reference(config, name, fixture / 'state', prepare_only=True)
            except ValueError:
                pass
            else:
                raise AssertionError('Injected preparation failure did not propagate')
        assert snapshot() == before
        assert command(['systemctl', 'show', unit, '--property=MainPID', '--value']) == pid
        # The same early failure in a normal apply must stop the verified old
        # supervisor too, preventing its restart loop from recreating containers.
        with patch('installarr.reference.prepare_directories', side_effect=ValueError('synthetic normal-apply refusal')):
            try:
                apply_reference(config, name, fixture / 'state')
            except ValueError:
                pass
            else:
                raise AssertionError('Injected normal-apply failure did not propagate')
        assert all(not row['State']['Running'] for row in controller.inventory())
        assert subprocess.run(['systemctl', 'is-active', unit], capture_output=True, text=True).stdout.strip() == 'inactive'
        # Full same-config resume after the failed checkpoints must recover.
        recovered = apply_reference(config, name, fixture / 'state')
        assert recovered['status'] == 'reference_poc_ready'
        assert all(row['State']['Running'] for row in controller.inventory())
        result = {'prepare_only_failure': 'preserved running containers/supervisor',
                  'early_normal_apply_failure': 'stopped verified old supervisor and containers',
                  'full_resume_after_failure': 'passed',
                  'prepared': prepared, 'container_ids_started_at': 'unchanged', 'supervisor_pid': 'unchanged',
                  'ready_phase': 'preserved', 'baseline_services': 'untouched', 'fixture_after_test': 'stopped/removed'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        command(['systemctl', 'stop', unit]); remove_owned(controller)
        network = controller.project + '_web'
        if subprocess.run(controller.docker + ['network', 'inspect', network], capture_output=True).returncode == 0:
            controller.run(controller.docker + ['network', 'rm', network])


if __name__ == '__main__':
    main()
