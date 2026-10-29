"""Secret-free retained-service snapshot for the deferred interaction queue."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.lifecycle import root_json, SERVICE_ROOT, service_status
from installarr.reference import reference_controller

BASELINE = {
    'poc-http-d29db77d': '/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json',
    'plex-standard-test': '/var/tmp/installarr-plex-standard-2bbujwqu/config.json',
    'ombi-family-2274744e': '/var/tmp/installarr-ombi-family-gui-o799mzbk/config.json',
}


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-interactive-state-', dir='/var/tmp'))
    result = {'captured_at_utc': datetime.now(timezone.utc).isoformat(), 'services': [],
              'secret_values': 'excluded; no environment/Preferences.xml/API/auth responses captured',
              'mutations': 'none beyond writing this checkpoint',
              'restore_policy': 'Only the exact three retained units; never superseded Plex units or duplicate identities'}
    for name, config_path in BASELINE.items():
        config = json.loads(Path(config_path).read_text())
        saved = root_json(SERVICE_ROOT / name / 'definition.json')
        controller = reference_controller(config, 'installarr-' + name)
        rows = controller.inventory()
        containers = []
        for row in rows:
            labels = row['Config']['Labels']
            assert labels['com.docker.compose.project'] == 'installarr-' + name
            assert labels['org.installarr.managed'] == 'isolated-compose-v1'
            containers.append({'id': row['Id'], 'name': row['Name'], 'app': labels['com.docker.compose.service'],
                'image': row['Config']['Image'], 'running': row['State']['Running'],
                'exit_code': row['State']['ExitCode'], 'ports': row['HostConfig'].get('PortBindings', {}),
                'restart_policy': row['HostConfig']['RestartPolicy'],
                'binds': [{key: mount.get(key) for key in ('Type', 'Source', 'Destination', 'RW', 'Propagation')}
                          for mount in row['Mounts']]})
        unit = 'installarr-' + name + '.service'
        states = {}
        for query in ('is-active', 'is-enabled'):
            output = subprocess.run(['systemctl', query, unit], capture_output=True, text=True, timeout=10, check=False)
            states[query] = output.stdout.strip()
        result['services'].append({'unit': unit, 'config_file': config_path, 'service_state': states,
            'supervisor': service_status(name), 'saved_launcher': saved['launcher'],
            'staged_apps': config['apps'], 'staged_quality_profiles': config.get('quality_profiles', {}),
            'staged_provider_choices': config.get('providers', {}), 'staged_plex_libraries': config.get('plex_libraries', []),
            'containers': containers,
            'restore_command': ['sudo', 'systemctl', 'start', unit]})
    target = work / 'checkpoint.json'
    target.write_text(json.dumps(result, indent=2) + '\n'); target.chmod(0o600)
    print(json.dumps({'checkpoint': str(target), 'services': len(result['services']),
                      'containers': sum(len(row['containers']) for row in result['services'])}))


if __name__ == '__main__':
    main()
