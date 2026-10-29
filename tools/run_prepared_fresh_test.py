"""Operator-approved switch to one fresh all-app deployment; scoped rollback."""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.cli import validate
from installarr.credentials import read_private_json
from installarr.plex import read_claim_file
from installarr.reference import apply_reference, reference_controller, remove_owned


def main():
    from installarr.plex import PlexHTTP
    original_request = PlexHTTP.request
    def observe_library_response(self, method, path, **kwargs):
        response = original_request(self, method, path, **kwargs)
        if method == 'POST' and path == '/library/sections' and response[0] == 400:
            query = dict(kwargs.get('query') or [])
            reason = 'invalid_language' if response[1].strip() == "'language' is invalid" else 'library_validation_rejected'
            print(json.dumps({'stage': 'plex_library_diagnostic', 'library': query.get('name'),
                              'language': query.get('language'), 'reason': reason}), flush=True)
        return response
    PlexHTTP.request = observe_library_response
    saved = read_private_json('/var/tmp/installarr-prepared-fresh-test-v2.json')
    config = validate(read_private_json(saved['config']))
    read_claim_file(config['plex_claim_file'])
    work = Path(saved['config']).parent
    previous = []
    for unit in saved['retained_units']:
        if subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode == 0:
            previous.append(unit)
    baseline = read_private_json(work / 'baseline-active.json') if (work / 'baseline-active.json').exists() else previous
    (work / 'previous-active.json').write_text(json.dumps(previous) + '\n')
    print(json.dumps({'stage': 'switching', 'name': saved['name'], 'previous_active_units': previous}), flush=True)
    try:
        for unit in previous:
            subprocess.run(['systemctl', 'stop', unit], check=True, timeout=60)
        result = apply_reference(config, saved['name'], Path(saved['state']),
                                 credentials_file=Path(saved['state']) / 'secrets/gui-admin.json')
        assert set(result['applications']) == set(saved['apps'])
        controller = reference_controller(config, 'installarr-' + saved['name'])
        inventory = controller.inventory()
        actual = sorted(row['Config']['Labels']['com.docker.compose.service'] for row in inventory)
        assert actual == sorted(saved['apps']) and all(row['State']['Running'] for row in inventory)
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'status': 'passed', 'apps': actual, 'evidence': str(work / 'result.json'),
                          'prior_services': 'stopped, boot settings unchanged', 'new_stack': 'available, boot-disabled'}), flush=True)
    except BaseException:
        for suffix in ('', '-boot'):
            unit = 'installarr-' + saved['name'] + suffix + '.service'
            if Path('/etc/systemd/system/' + unit).exists():
                subprocess.run(['systemctl', 'stop', unit], check=True, timeout=60)
                candidate = config if not suffix else dict(config, project_directory=str(Path(saved['state']) / 'bootstrap'))
                controller = reference_controller(candidate, 'installarr-' + saved['name'] + suffix, published=not suffix)
                remove_owned(controller)
        for unit in baseline:
            subprocess.run(['systemctl', 'start', unit], check=True, timeout=60)
        print('Fresh test failed; its containers stopped and prior active test services restarted.', flush=True)
        raise


if __name__ == '__main__':
    main()
