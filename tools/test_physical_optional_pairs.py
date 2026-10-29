"""Reference apply without inferred dependencies, using minimal standalone pairs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.cli import save_config
from installarr.hostplan import integration_plan
from installarr.lifecycle import command
from installarr.reference import apply_reference, reference_controller, remove_owned


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apps', choices=('bazarr,jackett', 'tautulli,ombi'), required=True)
    args = parser.parse_args()
    apps = args.apps.split(',')
    work = Path(tempfile.mkdtemp(prefix='installarr-optional-pair-', dir='/var/tmp'))
    tag = uuid.uuid4().hex[:8]
    data = Path('/media/installarr') / ('Installarr-Optional-' + tag)
    config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    config.update(apps=apps, bind_address='127.0.0.1', data_root=str(data), project_directory=str(work / 'project'))
    for key in ('quality_profiles', 'providers', 'provider_secrets_file', 'plex_claim_file', 'plex_libraries', 'ombi_family_presets'):
        config.pop(key, None)
    if 'bazarr' in apps:
        config['bazarr_language_profile'] = 'english-standard'
    config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                             configs=str(work / 'configs'), backups=str(work / 'backups'))
    save_config(work / 'config.json', config)
    name = 'optional-' + tag
    print(json.dumps({'evidence': str(work), 'unit': 'installarr-' + name + '.service', 'apps': apps}), flush=True)
    try:
        first = apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        second = apply_reference(config, name, work / 'state')
        controller = reference_controller(config, 'installarr-' + name)
        inventory = controller.inventory()
        selected = sorted(row['Config']['Labels']['com.docker.compose.service'] for row in inventory)
        assert selected == sorted(apps)
        assert set(first['applications']) == set(second['applications']) == set(apps)
        for app in apps:
            assert first['applications'][app]['host_gui_authentication'] == second['applications'][app]['host_gui_authentication']
        dependencies = integration_plan(config)
        assert dependencies['automatic_app_additions'] == []
        assert dependencies['operator_inputs'], 'Missing external integrations/providers must remain explicit'
        result = {'first': first, 'rerun': second, 'actual_apps': selected, 'dependencies': dependencies,
                  'scope': 'protected standalone apps; unselected request/media backends remain unconfigured'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'status': 'passed', 'apps': selected, 'operator_inputs': dependencies['operator_inputs']}), flush=True)
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


if __name__ == '__main__':
    main()
