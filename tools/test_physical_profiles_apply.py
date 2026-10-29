"""Published Radarr profiles bootstrap/apply acceptance, without claiming Plex readiness."""
import json
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.lifecycle import command
from installarr.reference import apply_reference, reference_controller, remove_owned


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-profile-apply-', dir='/var/tmp'))
    config = json.loads(Path('/var/tmp/installarr-bazarr-test-d5rjwtr7/config.json').read_text())
    config.update(apps=['radarr'], bind_address='127.0.0.1', project_directory=str(work / 'project'))
    config['storage'].update(configs=str(work / 'configs'), backups=str(work / 'backups'))
    from installarr.profiles import recommended_profiles
    config['quality_profiles'] = recommended_profiles(['radarr'])
    path = work / 'config.json'
    path.write_text(json.dumps(config, indent=2) + '\n')
    path.chmod(0o600)
    name = 'profiles-'  + uuid.uuid4().hex[:8]
    print(json.dumps({'evidence': str(work), 'unit': 'installarr-' + name + '.service'}), flush=True)
    try:
        first = apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        second = apply_reference(config, name, work / 'state')
        assert first['applications']['radarr']['host_gui_authentication'] == second['applications']['radarr']['host_gui_authentication']
        result = {'first': first, 'rerun': second, 'existing_assignments': 'preserved'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'published_auth': second['applications']['radarr'], 'rerun': 'passed'}), flush=True)
    finally:
        for suffix in ('', '-boot'):
            unit = 'installarr-' + name + suffix + '.service'
            if not Path('/etc/systemd/system/' + unit).exists():
                continue
            command(['systemctl', 'stop', unit])
            controller = reference_controller(config, 'installarr-' + name) if not suffix else reference_controller(
                dict(config, project_directory=str(work / 'state/bootstrap')), 'installarr-' + name + suffix, published=False)
            remove_owned(controller)
            controller.run(controller.docker + ['network', 'rm', controller.project + '_web'])


if __name__ == '__main__':
    main()
