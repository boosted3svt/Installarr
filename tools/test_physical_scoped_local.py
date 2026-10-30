"""Unpublished local-NVMe SAB fixture; absent-disk refusal before any creation."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import configure_apps, app_client
from installarr.cli import save_config
from installarr.credentials import read_private_credentials, read_private_json
from installarr.directories import prepare_directories, observed_mount
from installarr.layout import default_folders
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    base = Path('/var/lib/installarr-setup')
    original = read_private_json(base / 'settings.json')
    work = Path(tempfile.mkdtemp(prefix='installarr-scoped-local-', dir='/var/tmp'))
    fd = os.open(str(work), os.O_DIRECTORY | os.O_RDONLY)
    try:
        filesystem = observed_mount(fd)
    finally:
        os.close(fd)
    assert filesystem['fstype'] in ('ext4', 'xfs', 'btrfs')
    c = {key: copy.deepcopy(original[key]) for key in
         ('schema_version', 'timezone', 'bind_address', 'plex_allowed_networks', 'service_user')}
    data = work / 'data'
    c.update(apps=['sabnzbd'], project_directory=str(work / 'project'), data_root=str(data),
             storage={'media': str(data), 'downloads': str(data / 'finished-downloads'),
                      'incomplete': str(data / 'unfinished-downloads'), 'configs': str(work / 'configs'),
                      'backups': str(work / 'backups')}, folder_map=default_folders(str(data)))
    check = {'mountpoint': filesystem['target'], 'source': filesystem['source'], 'fstype': filesystem['fstype'], 'sentinel': 'health'}
    c['storage_mounts'] = {key: {'kind': 'local'} for key in c['storage']}
    c['storage_checks'] = {key: dict(check) for key in ('media', 'downloads', 'incomplete')}
    bad = copy.deepcopy(c)
    for value in bad['storage_checks'].values():
        value['source'] = '/dev/absent-installarr-test-drive'
    try:
        prepare_directories(bad, work / 'refused')
    except ValueError:
        pass
    else:
        raise AssertionError('Missing drive must refuse before writes')
    assert not data.exists() and not (work / 'configs').exists()
    save_config(work / 'config.json', c)
    prepare_directories(c, work / 'directories')
    write_reference_bundle(c, published=False)
    project = 'installarr-local-' + uuid.uuid4().hex[:8]
    controller = reference_controller(c, project, published=False)
    credentials = read_private_credentials(base / 'login/gui-admin.json')
    def restart():
        controller.stop()
        controller.reconcile()
    try:
        controller.reconcile()
        configure_apps(c, controller, credentials, restart)
        sab = app_client(c, controller, 'sabnzbd')
        assert sab.misc()['complete_dir'] == '/data/finished-downloads'
        assert sab.misc()['download_dir'] == '/data/unfinished-downloads'
        restart()
        configure_apps(c, controller, credentials, restart)
        result = {'status': 'passed', 'filesystem': filesystem, 'local_only': True,
                  'absent_disk_refused_before_directory_creation': True,
                  'category_and_scope_checks': 'passed', 'restart_rerun': 'passed',
                  'scope': 'host OS NVMe filesystem; not a separately mounted spare NVMe/boot acceptance'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'evidence': str(work), **result}), flush=True)
    finally:
        controller.stop()
        remove_owned(controller)
        if subprocess.run(controller.docker + ['network', 'inspect', project + '_web'], capture_output=True).returncode == 0:
            controller.run(controller.docker + ['network', 'rm', project + '_web'])


if __name__ == '__main__':
    main()
