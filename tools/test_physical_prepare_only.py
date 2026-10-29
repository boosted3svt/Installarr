"""Prepare a fresh Plex deployment without a claim or application startup."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.cli import save_config
from installarr.reference import apply_reference


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-prepare-only-', dir='/var/tmp'))
    tag = uuid.uuid4().hex[:8]
    name = 'prepared-' + tag
    data = Path('/media/installarr') / ('Installarr-Prepared-' + tag)
    config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    config.update(apps=['plex'], data_root=str(data), project_directory=str(work / 'project'),
                  plex_claim_file=str(work / 'claim/plex-claim.txt'))
    config.pop('quality_profiles', None)
    config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                             configs=str(work / 'configs'), backups=str(work / 'backups'))
    save_config(work / 'config.json', config)
    print(json.dumps({'evidence': str(work), 'name': name}), flush=True)
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    baseline = subprocess.check_output(docker + ['ps', '--all', '--quiet', '--no-trunc'], text=True)
    first = apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'), prepare_only=True)
    second = apply_reference(config, name, work / 'state', prepare_only=True)
    assert first == second
    assert first['status'] == 'reference_prepared' and not first['new_application_containers_started']
    assert not Path(config['plex_claim_file']).exists()
    assert not (work / 'project').exists()
    assert subprocess.check_output(docker + ['ps', '--all', '--quiet', '--no-trunc'], text=True) == baseline
    assert not Path('/etc/systemd/system/installarr-' + name + '.service').exists()
    assert not Path('/etc/systemd/system/installarr-' + name + '-boot.service').exists()
    assert json.loads((work / 'state/state.json').read_text())['phase'] == 'reference_prepared'
    result = {'first': first, 'rerun': second, 'container_inventory': 'unchanged', 'claim_file': 'absent as intended',
              'application_units': 'not created', 'config_file': str(work / 'config.json'),
              'next_action': 'operator claim and same apply without --prepare-only; no action requested during absence'}
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
