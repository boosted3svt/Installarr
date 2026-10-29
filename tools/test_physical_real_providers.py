"""Minimal actual-provider Radarr/SAB apply/rerun and official NNTP test download."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, wait_for
from installarr.cli import save_config
from installarr.lifecycle import command
from installarr.profiles import recommended_profiles
from installarr.reference import apply_reference, reference_controller, remove_owned


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', choices=('radarr', 'sonarr'), default='radarr')
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix='installarr-real-providers-', dir='/var/tmp'))
    tag = uuid.uuid4().hex[:8]
    data = Path('/media/installarr') / ('Installarr-Providers-' + tag)
    config = json.loads(Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-config.json').read_text())
    config.update(apps=['sabnzbd', args.app], bind_address='127.0.0.1', data_root=str(data),
                  project_directory=str(work / 'project'), quality_profiles=recommended_profiles([args.app]),
                  providers={'newshosting': {'connections': 100}, 'nzbgeek': {}},
                  provider_secrets_file='/var/tmp/installarr-providers-secrets/providers.json')
    config['storage'].update(media=str(data), downloads=str(data / 'downloads'), incomplete=str(data / 'incomplete-downloads'),
                             configs=str(work / 'configs'), backups=str(work / 'backups'))
    save_config(work / 'config.json', config)
    name = 'providers-' + tag
    print(json.dumps({'evidence': str(work), 'unit': 'installarr-' + name + '.service', 'nas_fixture': str(data)}), flush=True)
    try:
        first = apply_reference(config, name, work / 'state', credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        second = apply_reference(config, name, work / 'state')
        assert first['applications'][args.app]['indexer']['id'] == second['applications'][args.app]['indexer']['id']
        if args.app == 'sonarr':
            result = {'first_apply': first, 'rerun': second, 'official_download': 'already passed in Radarr/SAB pair; not repeated'}
            (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps({'app': args.app, 'provider_apply_and_rerun': 'passed',
                              'indexer': second['applications'][args.app]['indexer']}), flush=True)
            return
        controller = reference_controller(config, 'installarr-' + name)
        sab = app_client(config, controller, 'sabnzbd')
        assert sab.call('queue').get('queue', {}).get('slots') == []
        # Fixed official public random-data test; no movie/TV media requests.
        form = {'mode': 'addurl', 'output': 'json', 'apikey': sab.transport.api_key,
                'name': 'https://sabnzbd.org/tests/test_download_100MB.nzb', 'cat': 'movies', 'pp': 0,
                'nzbname': 'Installarr Official 100MB Test ' + tag}
        code, body = sab.transport.request('POST', '/api', form=form)
        response = json.loads(body)
        assert code == 200 and response.get('status') is True
        ids = response.get('nzo_ids')
        assert isinstance(ids, list) and len(ids) == 1
        until = time.monotonic() + 240
        item = None
        while time.monotonic() < until:
            rows = sab.call('history', limit=30).get('history', {}).get('slots', [])
            item = next((row for row in rows if row.get('nzo_id') == ids[0]), None)
            if item:
                break
            time.sleep(1)
        assert item and item.get('status') == 'Completed', 'Official download did not complete; private fixture retained'
        files = [path for path in (data / 'downloads/movies').rglob('*') if path.is_file()]
        assert files, 'No downloaded files found'
        observed = []
        for path in files:
            assert data.resolve() in path.resolve().parents
            info = path.stat()
            assert (info.st_uid, info.st_gid) == (2000, 2000)
            digest = hashlib.sha256()
            with path.open('rb') as handle:
                for block in iter(lambda: handle.read(1048576), b''):
                    digest.update(block)
            observed.append({'file': str(path.relative_to(data)), 'bytes': info.st_size, 'sha256': digest.hexdigest(), 'uid': info.st_uid, 'gid': info.st_gid})
        result = {'first_apply': first, 'rerun': second, 'download': {'source': 'official SAB100MB test', 'status': item['status'],
                  'downloaded_bytes': item.get('downloaded'), 'files': observed}, 'real_movie_tv_import': 'not tested'}
        (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'provider_apply_and_rerun': 'passed', 'indexer_id': second['applications'][args.app]['indexer']['id'],
                          'download': result['download']}), flush=True)
    finally:
        for suffix in ('', '-boot'):
            unit = 'installarr-' + name + suffix + '.service'
            if not Path('/etc/systemd/system/' + unit).exists():
                continue
            command(['systemctl', 'stop', unit])
            target = reference_controller(config, 'installarr-' + name) if not suffix else reference_controller(
                dict(config, project_directory=str(work / 'state/bootstrap')), 'installarr-' + name + suffix, published=False)
            remove_owned(target)
            network = target.project + '_web'
            if command(target.docker + ['network', 'ls', '--filter', 'name=^' + network + '$', '--format', '{{.Name}}']) == network:
                target.run(target.docker + ['network', 'rm', network])


if __name__ == '__main__':
    main()
