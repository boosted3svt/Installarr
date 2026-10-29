"""Official Plex entrypoint behind real read-only NAS startup assertions."""
import json
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, wait_for
from installarr.directories import prepare_directories
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-plex-bundle-', dir='/var/tmp'))
    cfg = json.loads(Path('/var/tmp/installarr-bazarr-test-d5rjwtr7/config.json').read_text())
    cfg.update(apps=['plex'], project_directory=str(work / 'project'))
    cfg['storage'].update(configs=str(work / 'configs'), backups=str(work / 'backups'))
    cfg.pop('quality_profiles', None)
    (work / 'config.json').write_text(json.dumps(cfg, indent=2) + '\n')
    (work / 'config.json').chmod(0o600)
    prepare_directories(cfg, work / 'directories')
    write_reference_bundle(cfg, published=False)
    controller = reference_controller(cfg, 'installarr-plex-' + uuid.uuid4().hex[:8], published=False)
    print(json.dumps({'evidence': str(work), 'project': controller.project}), flush=True)
    try:
        controller.reconcile()
        client = wait_for(lambda: app_client(cfg, controller, 'plex'))
        first = client.status()
        row = controller.inventory()[0]
        media = [m for m in row['Mounts'] if m['Destination'] == '/data']
        assert len(media) == 1 and not media[0]['RW']
        controller.stop()
        controller.reconcile()
        client = wait_for(lambda: app_client(cfg, controller, 'plex'))
        second = client.status()
        assert first == second
        assert controller.audit(controller.inventory())
        result = {'first': first, 'after_restart': second, 'media_bind': 'read-only',
                  'real_guard_and_entrypoint': 'passed', 'authorization': 'unclaimed; unpublished'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        remove_owned(controller)
        controller.run(controller.docker + ['network', 'rm', controller.project + '_web'])


if __name__ == '__main__':
    main()
