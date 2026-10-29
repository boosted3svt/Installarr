"""Signed fresh-host Docker staging followed by standard bridge-capable startup.

Normal reference installation uses Docker's bridge/NAT defaults. No host address,
DNS, SSH or manual firewall changes are made. Boot enablement remains explicit.
"""
import json
from pathlib import Path
import subprocess

from .accounts import provisioning_gate
from .dockerhost import PACKAGES, UNITS, installed_version, prepare_docker
from .execution import Execution
from .lifecycle import command, root_json

TEST = ['docker', '--host', 'unix:///run/installarr-docker-test/docker.sock']
NORMAL = ['docker', '--host', 'unix:///run/docker.sock']
NETWORK = 'installarr-reference-check_web'


def prepare_standard_docker():
    provisioning_gate()
    saved = Path('/var/lib/installarr-reference-network/state.json')
    if not saved.exists() or root_json(saved).get('steps', {}).get('engine') not in ('running', 'failed', 'verified'):
        prepare_docker()
    packages = root_json('/var/lib/installarr-docker-install/state.json').get('package_versions', {})
    if set(packages) != set(PACKAGES) or any(installed_version(p) != packages[p] for p in PACKAGES):
        raise ValueError('Docker package versions differ from signed installation checkpoint; preserved')
    if any(installed_version(package) is None for package in PACKAGES):
        raise ValueError('Official Docker packages must already be staged')
    with Execution('/var/lib/installarr-reference-network', {'operation': 'standard-web-transition-v1'}) as execution:
        previous = bool(execution.state['steps'])
        if not previous:
            if any(Path(path).exists() for path in ('/run/docker.sock', '/var/lib/docker', '/etc/docker/daemon.json')):
                raise ValueError('Existing standard Docker configuration/data preserved')
            if Path('/run/installarr-docker-test/docker.sock').exists() and command(TEST + ['ps', '--all', '--quiet']):
                raise ValueError('Isolated workloads preserved; transition refused')
            for unit in UNITS:
                result = subprocess.run(['systemctl', 'is-enabled', unit], capture_output=True, text=True)
                if result.stdout.strip() != 'masked':
                    raise ValueError('Unexpected standard Docker service state preserved')
        already_prepared = execution.state['steps'].get('engine') == 'verified'
        def engine():
            if already_prepared:
                if Path('/etc/docker/daemon.json').exists():
                    raise ValueError('Unexpected daemon configuration preserved')
                active = subprocess.run(['systemctl', 'is-active', 'docker.service'], capture_output=True, text=True)
                if active.stdout.strip() == 'inactive':
                    command(['systemctl', 'start', 'docker.service'])
                command(NORMAL + ['version', '--format', '{{.Server.Version}}'])
                return
            active = subprocess.run(['systemctl', 'is-active', 'installarr-test-docker.service'], capture_output=True, text=True)
            if active.stdout.strip() == 'active' and command(TEST + ['ps', '--all', '--quiet']):
                raise ValueError('New isolated workloads appeared; preserved')
            if Path('/etc/docker/daemon.json').exists():
                raise ValueError('Unexpected daemon configuration preserved')
            if active.stdout.strip() == 'active':
                command(['systemctl', 'stop', 'installarr-test-docker.service'])
            command(['systemctl', 'unmask', *UNITS])
            command(['systemctl', 'disable', *UNITS])
            command(['systemctl', 'start', 'docker.service'])
            command(NORMAL + ['version', '--format', '{{.Server.Version}}'])
        execution.reconcile('engine', engine)
        def network():
            result = subprocess.run(NORMAL + ['network', 'inspect', NETWORK], capture_output=True, text=True)
            if result.returncode == 0:
                row = json.loads(result.stdout)[0]
                if row.get('Driver') != 'bridge' or row.get('Labels', {}).get('org.installarr.reference-check') != '1':
                    raise ValueError('Existing network differs; preserved')
            else:
                command(NORMAL + ['network', 'create', '--driver', 'bridge', '--label', 'org.installarr.reference-check=1', NETWORK])
        execution.reconcile('web-network', network)
        execution.state['phase'] = 'standard_reference_network_ready'
        execution._save()
    return {'status': 'standard_reference_network_ready', 'network': NETWORK,
                      'note': 'No application containers or published ports started; boot enablement remains disabled.'}
