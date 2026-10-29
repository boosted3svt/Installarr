"""Query three configured public providers with the actual pinned image's code."""
import json
from pathlib import Path
import subprocess
import tempfile
import uuid


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-public-subtitle-probes-', dir='/var/tmp'))
    script = Path(__file__).with_name('bazarr_public_provider_probe.py').read_text()
    image = 'ghcr.io/linuxserver/bazarr@sha256:9a625883f054e722795affe5e3ca71057e6ed817ecdf99f4a99624346fcc509c'
    results = []
    print(json.dumps({'evidence': str(work)}), flush=True)
    for name in ('supersubtitles', 'tvsubtitles'):
        container = 'installarr-public-sub-' + uuid.uuid4().hex[:8]
        try:
            probe = subprocess.run(['docker', 'run', '--rm', '--name', container, '--interactive', '--network', 'bridge', '--user', '2000:2000',
                '--cap-drop', 'ALL', '--entrypoint', 'python3', image, '-B', '-c', script],
                input=json.dumps({'provider': name}), capture_output=True, text=True, timeout=90)
            result = json.loads(probe.stdout)
        except subprocess.TimeoutExpired:
            result = {'provider': name, 'native_search': 'timed out'}
        finally:
            subprocess.run(['docker', 'rm', '--force', container], capture_output=True, timeout=20)
        results.append(result)
        (work / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
