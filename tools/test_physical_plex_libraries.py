"""Upgrade the authorized test Plex configuration, retaining its local database."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.lifecycle import command
from installarr.reference import apply_reference


def supplied_files():
    roots = [Path('/media/installarr/Movies/Framing Britney Spears (2021)'), Path('/media/installarr/TV/11.22.63')]
    return {str(path): [path.stat().st_size, path.stat().st_mtime_ns] for root in roots
            for path in root.rglob('*') if not path.is_symlink() and path.is_file()}


def main():
    work = Path('/var/tmp/installarr-plex-libraries-m6m4j4kb')
    config = json.loads((work / 'config.json').read_text())
    before = supplied_files()
    assert before
    print(json.dumps({'evidence': str(work), 'original_files': len(before)}), flush=True)
    ready = False
    # The same local Plex database must never be opened by two containers.
    command(['systemctl', 'stop', 'installarr-plex-auth-test.service'])
    try:
        result = apply_reference(config, 'plex-libraries-test', work / 'state',
            credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        assert before == supplied_files()
        assert len(result['applications']['plex']['configuration']['libraries']) == 15
        assert result['applications']['tautulli']['plex_integration']['connection'] == 'verified'
        ready = True
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        if not ready:
            command(['systemctl', 'start', 'installarr-plex-auth-test.service'])


if __name__ == '__main__':
    main()
