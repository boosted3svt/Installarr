"""Read-only audit of retained runtime snapshots; never rewrites managed units."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.lifecycle import SERVICE_ROOT, root_json


def digest(directory):
    paths = [*directory.glob('*.py'), *[path for path in (directory / 'data').rglob('*') if path.is_file()]]
    contents = {str(path.relative_to(directory)): path.read_bytes() for path in sorted(paths)}
    return hashlib.sha256(b''.join(name.encode() + b'\0' + data for name, data in contents.items())).hexdigest()


def main():
    current = digest(Path(__file__).resolve().parents[1] / 'installarr')
    results = []
    for name in ('poc-http-d29db77d', 'plex-standard-test', 'ombi-family-2274744e'):
        saved = root_json(SERVICE_ROOT / name / 'definition.json')
        launcher = Path(saved['launcher'])
        snapshot = digest(launcher.parent / 'installarr')
        assert launcher.parent.name == snapshot, 'Saved runtime content hash differs'
        results.append({'deployment': name, 'snapshot_integrity': 'verified', 'matches_checkout': snapshot == current,
                        'automatic_update': 'none; saved units/definitions preserved'})
    print(json.dumps({'current_code_sha256': current, 'services': results}, indent=2))


if __name__ == '__main__':
    main()
