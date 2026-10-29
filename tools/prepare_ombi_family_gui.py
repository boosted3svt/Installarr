"""Retain a protected Ombi-only GUI fixture for genuine family Plex sign-in.

Copy only a stopped, installer-owned local test database. Never copy production
state or supplied media. Request/download testing is not the purpose of this GUI.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.reference import apply_reference
from installarr.cli import save_config
from installarr.lifecycle import command


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-ombi-family-gui-', dir='/var/tmp'))
    source = Path('/var/tmp/installarr-ombi-plex-ijlmfvek/config')
    # Source fixture's container must be gone before making its SQLite snapshot.
    rows = [json.loads(line) for line in command(['docker', 'ps', '-a', '--format', 'json']).splitlines() if line]
    assert not any(row['Names'] == 'installarr-ombi-474e8301' for row in rows)
    target = work / 'configs/ombi'
    target.parent.mkdir(mode=0o700)
    assert source.resolve() == source and not any(path.is_symlink() for path in source.rglob('*'))
    shutil.copytree(str(source), str(target), symlinks=False)
    for path in [target] + list(target.rglob('*')):
        assert not path.is_symlink()
        os.chown(str(path), 2000, 2000)
    config = json.loads(Path('/var/tmp/installarr-bazarr-test-d5rjwtr7/config.json').read_text())
    config.update(apps=['ombi'], bind_address='10.70.0.99', project_directory=str(work / 'project'))
    config['storage'].update(configs=str(work / 'configs'), backups=str(work / 'backups'))
    for key in ('quality_profiles', 'plex_claim_file', 'plex_libraries', 'plex_server_name', 'ombi_family_presets'):
        config.pop(key, None)
    save_config(work / 'config.json', config)
    name = 'ombi-family-' + uuid.uuid4().hex[:8]
    print(json.dumps({'evidence': str(work), 'unit': 'installarr-' + name + '.service'}), flush=True)
    first = apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
    second = apply_reference(config, name, work / 'state')
    result = {'first': first, 'rerun': second, 'purpose': 'Plex-family GUI sign-in only; no request backends selected'}
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'gui': 'http://10.70.0.99:3579', 'authentication': second['applications']['ombi']['host_gui_authentication'],
                      'purpose': result['purpose']}), flush=True)


if __name__ == '__main__':
    main()
