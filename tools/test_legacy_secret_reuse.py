"""Read/reuse authorized legacy private stores without prompting or changing files."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.credentials import initialize_credentials
from installarr.provider_secrets import initialize_provider_secrets


def snapshot(directory, names):
    result = {'entries': sorted(path.name for path in directory.iterdir())}
    for name in names:
        path = directory / name
        if path.exists():
            info = path.stat()
            # Digests remain only in memory; they are never printed/checkpointed.
            result[name] = (hashlib.sha256(path.read_bytes()).digest(), info.st_mtime_ns,
                            info.st_uid, info.st_gid, info.st_mode, info.st_nlink)
    return result


def main():
    gui = Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets')
    providers = Path('/var/tmp/installarr-providers-secrets')
    before_gui = snapshot(gui, ['gui-admin.json', 'state.json', 'lock'])
    before_providers = snapshot(providers, ['providers.json', 'state.json', 'lock'])
    def forbidden(*unused):
        raise AssertionError('Legacy reuse attempted credential recollection')
    assert initialize_credentials(gui, forbidden)['status'] == 'reused'
    assert initialize_provider_secrets(providers, ['newshosting', 'nzbgeek', 'opensubtitlescom'], forbidden)['status'] == 'reused'
    assert snapshot(gui, ['gui-admin.json', 'state.json', 'lock']) == before_gui
    assert snapshot(providers, ['providers.json', 'state.json', 'lock']) == before_providers
    work = Path(tempfile.mkdtemp(prefix='installarr-legacy-secret-reuse-', dir='/var/tmp'))
    result = {'gui': 'legacy store reused', 'providers': 'legacy store reused',
              'values_and_file_metadata': 'unchanged', 'directory_entries': 'unchanged',
              'recollection': 'not attempted', 'secret_values_or_hashes': 'not recorded'}
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'evidence': str(work), **result}))


if __name__ == '__main__':
    main()
