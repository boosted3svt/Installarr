"""Resumable isolated deployment of the three version-tested applications."""
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from .accounts import prepare_accounts, provisioning_gate
from .arr import AppAPIError, ArrClient, DockerHTTP
from .compose import IMAGES, application_paths, private_artifact, render_bundle, write_bundle
from .credentials import initialize_credentials, read_private_credentials, validate_credentials
from .directories import prepare_directories
from .dockerhost import prepare_docker, prepare_test_daemon, trusted_directory
from .downloadclients import ensure_sabnzbd
from .execution import Execution
from .lifecycle import Controller, SOCKET, SERVICE_ROOT, command, install_service, local_mount, root_json, service_status
from .prerequisites import prepare_prerequisites
from .sab import SabClient, SabHTTP
from .bazarr import BazarrClient
from .jackett import JackettClient, JackettHTTP
from .tautulli import TautulliClient, TautulliHTTP
from .netboot import NetbootClient, NetbootHTTP
from .ombi import OmbiClient, OmbiHTTP
from .plex import PlexClient, PlexHTTP, PREFERENCES
from .hosthttp import HostHTTP
from .mounts import prepare_mounts


class ApplyError(ValueError):
    pass


def wait_for(action, seconds=120):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        try:
            result = action()
            if result:
                return result
        except (AppAPIError, FileNotFoundError, ET.ParseError):
            pass
        time.sleep(0.5)
    raise ApplyError('Application readiness deadline exceeded')


def app_client(config, controller, app, credentials=None):
    rows = controller.inventory()
    if not controller.audit(rows):
        return None
    matches = [row for row in rows if row['Config']['Labels']['com.docker.compose.service'] == app]
    if len(matches) != 1:
        return None
    container = matches[0]['Id']
    directory = Path(config['storage']['configs']) / app
    if app == 'netbootxyz':
        if credentials is None:
            raise AppAPIError('Netboot requires its separate GUI credentials for verification')
        client = NetbootClient(NetbootHTTP(controller.socket, container))
        client.verify_admin(credentials)
    elif app == 'ombi':
        client = OmbiClient(OmbiHTTP(controller.socket, container))
        client.status()
    elif app == 'plex':
        preferences = ET.parse(str(directory / PREFERENCES)).getroot()
        client = PlexClient(PlexHTTP(controller.socket, container, api_key=preferences.get('PlexOnlineToken', '')))
        client.status()
    elif app == 'tautulli':
        import configparser
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(str(directory / 'config.ini'))
        key = parser['General']['api_key']
        client = TautulliClient(TautulliHTTP(controller.socket, container, 8181, key))
        client.status()
    elif app == 'jackett':
        if credentials is None:
            raise AppAPIError('Jackett requires its separate GUI credentials for management')
        settings = json.loads((directory / 'Jackett/ServerConfig.json').read_text())
        client = JackettClient(JackettHTTP(controller.socket, container, 9117, settings['APIKey']), credentials)
        client.config()
    elif app == 'bazarr':
        text = (directory / 'config/config.yaml').read_text()
        # Read only Bazarr's generated auth section; do not parse arbitrary YAML.
        section = re.search(r'(?ms)^auth:\s*\n(.*?)(?=^[^ \n]|\Z)', text)
        match = re.search(r'(?m)^  apikey: [\"\']?([a-fA-F0-9]{32})[\"\']?\s*$', section.group(1)) if section else None
        if not match:
            return None
        client = BazarrClient(DockerHTTP(controller.socket, container, 6767, match.group(1)))
        client.status()
    elif app == 'sabnzbd':
        text = (directory / 'sabnzbd.ini').read_text()
        match = re.search(r'(?m)^api_key\s*=\s*([a-fA-F0-9]{32})\s*$', text)
        if not match:
            return None
        client = SabClient(SabHTTP(controller.socket, container, 8080, match.group(1)))
        if client.call('version').get('version') != IMAGES[app]['version'].split('-ls', 1)[0]:
            raise ApplyError('Untested SABnzbd runtime version')
    else:
        key = ET.fromstring((directory / 'config.xml').read_text()).findtext('ApiKey')
        client = ArrClient(DockerHTTP(controller.socket, container, IMAGES[app]['port'], key), IMAGES[app]['version'].split('-ls', 1)[0],
                           secondary_root=bool(app == 'radarr' and 'media_secondary' in config['storage'] and not config.get('secondary_media_read_only', True)))
        if client.json('GET', 'system/status').get('version') != client.expected_version:
            raise ApplyError('Untested application runtime version')
    return client


def verify_scoped_paths(config, controller, app):
    if 'folder_map' not in config:
        return
    from .layout import app_entries
    rows = controller.inventory()
    controller.audit(rows)
    container = next(row['Id'] for row in rows if row['Config']['Labels']['com.docker.compose.service'] == app)
    checks = app_entries(config, app)
    paths = [row['target'] for row in checks]
    if app in ('radarr', 'sonarr', 'sabnzbd'):
        paths += ['/data/finished-downloads/' + category for category in ('movies', 'tv')]
    if paths:
        script = 'for path do test -d "$path" && test -r "$path" && test -x "$path" || exit 1; '
        script += ('test ! -w "$path"' if app == 'plex' else 'test -w "$path"') + ' || exit 1; done'
        try:
            controller.run(controller.docker + ['exec', '--user', '{}:{}'.format(config['service_user']['uid'], config['service_user']['gid']),
                           container, '/bin/sh', '-c', script, 'installarr-path-check'] + paths)
        except (OSError, ValueError):
            raise ApplyError('Application media/download folders are missing or have incorrect access; setup remains incomplete') from None


def configure_apps(config, controller, credentials, restart, download_host="127.0.0.1", family_state_directory=None, provider_credentials=None):
    from .credentials import validate_selected_gui_credentials
    validate_selected_gui_credentials(config, credentials)
    evidence = {}
    from .ombi_family import read_family_preferences
    family_preferences = read_family_preferences(config["ombi_family_preferences_file"]) if config.get("ombi_family_preferences_file") else {}
    from .providers import required_secrets
    provider_choices = config.get('providers', {})
    provider_credentials = provider_credentials or {}
    if required_secrets(config) - set(provider_credentials):
        raise ApplyError('Selected provider credentials are required before application configuration')
    if 'sabnzbd' in config['apps']:
        sab = wait_for(lambda: app_client(config, controller, 'sabnzbd'))
        try:
            sab.verify_admin(credentials)
        except AppAPIError:
            sab.configure_admin(credentials)
            restart()
            sab = wait_for(lambda: app_client(config, controller, 'sabnzbd'))
        auth = sab.verify_admin(credentials)
        sab.configure_storage(config)
        verify_scoped_paths(config, controller, 'sabnzbd')
        evidence['sabnzbd'] = {'authentication': auth, 'storage': 'verified'}
        if 'newshosting' in provider_choices:
            from .providers import newshosting
            evidence['sabnzbd']['provider'] = newshosting(sab, provider_credentials['newshosting'],
                provider_choices['newshosting']['connections'])
    for app in ('sonarr', 'radarr'):
        if app not in config['apps']:
            continue
        client = wait_for(lambda: app_client(config, controller, app))
        try:
            auth = client.verify_admin(credentials)
        except AppAPIError:
            auth = client.configure_admin(credentials)
        root = client.ensure_root(application_paths(config, app)['media_root'])
        item = {'authentication': auth, 'root_id': root}
        extra_roots = application_paths(config, app).get('additional_media_roots', [])
        if extra_roots:
            item['additional_root_ids'] = {path: client.ensure_root(path) for path in extra_roots}
        if 'sabnzbd' in config['apps']:
            item['downloader'] = ensure_sabnzbd(client, config, app, sab.transport.api_key, host=download_host)
        choice = config.get('quality_profiles', {}).get(app)
        if choice:
            from .profiles import ensure_profile
            profiles = {identifier: ensure_profile(client, app, identifier)
                        for identifier in choice['available']}
            item['quality_profiles'] = {'available': profiles,
                'preferred_id': profiles[choice['default']]['id'],
                'existing_assignments': 'preserved'}
            if 'folder_map' in config:
                from .quality_sizes import ensure_quality_sizes
                item['quality_sizes'] = ensure_quality_sizes(client, app)
        if 'nzbgeek' in provider_choices:
            from .providers import nzbgeek
            item['indexer'] = nzbgeek(client, app, provider_credentials['nzbgeek'])
        verify_scoped_paths(config, controller, app)
        if 'folder_map' in config:
            problems = client.json('GET', 'health')
            if any('does not appear to exist' in str(row.get('message', '')) and 'download' in str(row.get('message', '')).lower() for row in problems):
                raise ApplyError('Application reports an inaccessible completed-download folder; setup remains incomplete')
        evidence[app] = item
    if 'bazarr' in config['apps']:
        client = wait_for(lambda: app_client(config, controller, 'bazarr'))
        try:
            auth = client.verify_admin(credentials)
        except AppAPIError:
            auth = client.configure_admin(credentials)
        links = {}
        for app in ('sonarr', 'radarr'):
            if app in config['apps']:
                backend = wait_for(lambda: app_client(config, controller, app))
                links[app] = client.connect_arr(app, backend.transport.api_key, backend.expected_version)
        evidence['bazarr'] = {'authentication': auth, 'integrations': links}
        verify_scoped_paths(config, controller, 'bazarr')
        if config.get('bazarr_language_profile') == 'english-standard':
            evidence['bazarr']['subtitle_profile'] = client.configure_english_subtitles()
        if 'bazarr' in provider_choices:
            from .providers import bazarr_providers
            evidence['bazarr']['providers'] = bazarr_providers(client, provider_choices['bazarr']['enabled'],
                                                            provider_credentials.get('opensubtitlescom'))
    if 'jackett' in config['apps']:
        client = wait_for(lambda: app_client(config, controller, 'jackett', credentials))
        try:
            auth = client.verify_admin()
        except AppAPIError:
            auth = client.configure_admin()
        evidence['jackett'] = {'authentication': auth, 'indexers': 'operator selection and credentials required'}
    if 'netbootxyz' in config['apps']:
        client = wait_for(lambda: app_client(config, controller, 'netbootxyz', credentials))
        evidence['netbootxyz'] = {'authentication': client.verify_admin(credentials), 'dhcp_pxe_client_tests': 'out of scope'}
    if 'ombi' in config['apps']:
        client = wait_for(lambda: app_client(config, controller, 'ombi'))
        try:
            authentication = client.verify_admin(credentials)
        except AppAPIError:
            authentication = client.configure_admin(credentials)
        links = {}
        with client.administrator(credentials):
            for app in ('radarr', 'sonarr'):
                if app not in config['apps']:
                    continue
                profile = evidence[app].get('quality_profiles', {}).get('preferred_id')
                if profile is None:
                    links[app] = {'status': 'preferred quality profile selection required'}
                    continue
                backend = wait_for(lambda: app_client(config, controller, app))
                links[app] = client.connect_arr(app, backend.transport.api_key, profile,
                    evidence[app]['root_id'], application_paths(config, app)['media_root'])
        evidence['ombi'] = {'authentication': authentication, 'integrations': links,
                            'plex_family_import_and_requests': 'not configured'}
    if 'plex' in config['apps']:
        client = wait_for(lambda: app_client(config, controller, 'plex'))
        # The claim exchange precedes PMS account initialization. A usable HTTP
        # listener can appear before /identity reports the claimed state.
        if not client.transport.api_key:
            client.verify_authorization()  # Explicit actionable refusal, no polling.
        evidence['plex'] = wait_for(client.verify_authorization)
        from .plex import configure_server
        evidence['plex']['configuration'] = configure_server(client, config)
        verify_scoped_paths(config, controller, 'plex')
        if 'ombi' in config['apps']:
            ombi = wait_for(lambda: app_client(config, controller, 'ombi'))
            status = client.status()
            with ombi.administrator(credentials):
                evidence['ombi']['integrations']['plex'] = ombi.connect_plex(client.transport.api_key,
                    status['machine_identifier'], evidence['plex']['configuration']['libraries'],
                    evidence['plex']['configuration']['server_name'])
    if config.get('ombi_family_presets'):
        if family_state_directory is None:
            raise ApplyError('Family import requires a private recovery checkpoint')
        from .ombi_family import FAMILY, family_paths, import_family, configure_family
        from .profiles import RECOMMENDED
        ombi = wait_for(lambda: app_client(config, controller, 'ombi'))
        plex = wait_for(lambda: app_client(config, controller, 'plex'))
        routes = {name: {} for name in FAMILY}
        for name, paths in family_paths(config).items():
            for app, path in paths.items():
                backend = wait_for(lambda: app_client(config, controller, app))
                profile = evidence[app]['quality_profiles']['available'][RECOMMENDED[app]['default']]['id']
                routes[name][app + 'RootPath'] = backend.ensure_root(path['container_path'])
                routes[name][app + 'QualityProfile'] = profile
        with ombi.administrator(credentials):
            import_family(ombi, wait_for, family_state_directory, plex.status()['machine_identifier'])
            evidence['ombi']['family'] = configure_family(ombi, routes, family_preferences)
            evidence['ombi']['plex_family_import_and_requests'] = 'Plex identities/settings verified; family GUI login and requests pending'
    if 'tautulli' in config['apps']:
        client = wait_for(lambda: app_client(config, controller, 'tautulli'))
        authentication = client.verify_admin(credentials)
        link = 'authorization required; not configured'
        if 'plex' in config['apps']:
            from .tautulli import configure_plex_offline
            plex = wait_for(lambda: app_client(config, controller, 'plex'))
            status = plex.status()
            directory = Path(config['storage']['configs']) / 'tautulli'
            # Tautulli intentionally masks the Plex token in API settings.
            import configparser
            from .tautulli import unquote_scalar
            parser = configparser.ConfigParser(interpolation=None)
            parser.read(str(directory / 'config.ini'))
            desired = {'pms_token': plex.transport.api_key, 'pms_identifier': status['machine_identifier'],
                       'pms_ip': 'plex', 'pms_port': '32400', 'pms_url': 'http://plex:32400',
                       'pms_url_manual': '1', 'pms_ssl': '0', 'pms_is_remote': '0', 'pms_logs_folder': '/plexlogs'}
            if (any(unquote_scalar(parser.get('PMS', key, fallback='')) != value for key, value in desired.items())
                    or parser.get('General', 'first_run_complete', fallback='0') != '1'):
                restart(lambda: configure_plex_offline(directory, plex.transport.api_key,
                    status['machine_identifier'], config['service_user']['uid'], config['service_user']['gid']))
                client = wait_for(lambda: app_client(config, controller, 'tautulli'))
                authentication = client.verify_admin(credentials)
            link = wait_for(lambda: client.verify_plex(status['machine_identifier'], status['version']))
        evidence['tautulli'] = {'authentication': authentication, 'plex_integration': link}
    return evidence


def apply(config, name, state_directory=None, secrets_directory=None, credentials_file=None):
    from .cli import validate, identity_conflicts
    validate(config)
    provisioning_gate()
    if config.get('providers'):
        raise ApplyError('Provider configuration requires the reference apply workflow')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,31}', name):
        raise ApplyError('Invalid deployment name')
    if not config['apps'] or set(config['apps']) - {'sonarr', 'radarr', 'sabnzbd'}:
        raise ApplyError('Apply currently supports a nonempty selection of Sonarr, Radarr and SABnzbd only')
    if not shutil.which('nsenter'):
        raise ApplyError('GUI access requires nsenter from util-linux')
    render_bundle(config)  # Reject incomplete storage/image plans before host mutations.
    definition = SERVICE_ROOT / name / 'definition.json'
    unit = 'installarr-' + name + '.service'
    if definition.exists():
        saved = root_json(definition)
        if saved.get('config') != config or saved.get('name') != name:
            raise ApplyError('Existing deployment differs; preserved')
    elif os.path.lexists('/etc/systemd/system/' + unit):
        raise ApplyError('Existing service name conflicts; preserved')
    default_parent = Path('/var/lib/installarr-apply')
    state = Path(state_directory) if state_directory else default_parent / name
    secrets = Path(secrets_directory) if secrets_directory else state / 'secrets'
    credentials = None
    if (secrets / 'gui-admin.json').exists():
        credentials = read_private_credentials(secrets / 'gui-admin.json')
    elif credentials_file:
        credentials = read_private_credentials(credentials_file)
    elif not sys.stdin.isatty():
        raise ApplyError('Unattended apply requires a private credential store or credentials file')
    if credentials and ':' in credentials['username'] and 'sabnzbd' in config['apps']:
        raise ApplyError('SABnzbd Basic authentication requires a username without a colon')
    if state_directory is None:
        trusted_directory(default_parent)
    local_mount(state.parent)
    local_mount(secrets.parent if secrets.parent.exists() else state.parent)
    controller = Controller(config, 'installarr-' + name)
    managed = definition.exists()
    evidence = {}
    ready_file = SERVICE_ROOT / name / 'gui-ready.json'
    authorization = {'schema_version': 1, 'bundle': controller.identity, 'authentication_verified': True,
                     'credentials_file': str((secrets / 'gui-admin.json').absolute())}
    with Execution(state, {'operation': 'isolated-apply-v1', 'config': config, 'name': name}) as execution:
        execution.state['phase'] = 'applying'
        execution._save()
        try:
            if os.path.lexists(str(ready_file)):
                if root_json(ready_file) != authorization:
                    raise ApplyError('Existing GUI authorization differs; preserved')
                ready_file.unlink()
                wait_for(lambda: not service_status(name).get('health', {}).get('gui', {}).get('enabled', False))
            def collect():
                value = credentials or validate_credentials({'username': input('Shared GUI administrator username: '),
                                                             'password': getpass.getpass('Shared GUI administrator password: ')})
                if 'sabnzbd' in config['apps'] and ':' in value['username']:
                    raise ApplyError('SABnzbd username cannot contain a colon')
                return value
            execution.reconcile('credentials', lambda: initialize_credentials(secrets, collect))
            credentials = read_private_credentials(secrets / 'gui-admin.json')
            execution.reconcile('accounts', lambda: prepare_accounts(config, state / 'accounts', identity_conflicts))
            execution.reconcile('prerequisites', lambda: prepare_prerequisites(config, state / 'prerequisites'))
            execution.reconcile('mounts', lambda: prepare_mounts(config, state / 'mounts'))
            execution.reconcile('directories', lambda: prepare_directories(config, state / 'directories'))
            execution.reconcile('docker', prepare_docker)
            execution.reconcile('daemon', prepare_test_daemon)
            def images():
                for app in config['apps']:
                    image = IMAGES[app]['image']
                    exists = subprocess.run(controller.docker + ['image', 'inspect', image], capture_output=True, timeout=15)
                    if exists.returncode:
                        command(controller.docker + ['pull', image], timeout=600)
            execution.reconcile('images', images)
            execution.reconcile('compose', lambda: write_bundle(config))
            execution.reconcile('service', lambda: install_service(config, name))
            managed = True
            def start():
                command(['systemctl', 'start', unit])
                wait_for(lambda: service_status(name).get('phase') == 'containers_running')
            def restart():
                command(['systemctl', 'restart', unit])
                wait_for(lambda: service_status(name).get('phase') == 'containers_running')
            execution.reconcile('start', start)
            def applications():
                evidence.update(configure_apps(config, controller, credentials, restart))
            execution.reconcile('applications', applications)
            # Readiness requires audited live containers plus actual API/auth/root
            # checks above, not merely a successful systemd start.
            if not controller.audit(controller.inventory()):
                raise ApplyError('Managed containers are not running')
            def gui():
                private_artifact(ready_file, (json.dumps(authorization) + '\n').encode(), 0o600)
                wait_for(lambda: service_status(name).get('health', {}).get('gui', {}).get('enabled'))
                for app in config['apps']:
                    backend = wait_for(lambda: app_client(config, controller, app))
                    transport = HostHTTP(config['bind_address'], IMAGES[app]['port'], backend.transport.api_key)
                    client = SabClient(transport) if app == 'sabnzbd' else ArrClient(transport, backend.expected_version)
                    evidence[app]['host_gui_authentication'] = client.verify_admin(credentials)
            execution.reconcile('gui', gui)
            execution.state['phase'] = 'isolated_configured'
            execution._save()
        except BaseException:
            if os.path.lexists(str(ready_file)) and root_json(ready_file) == authorization:
                ready_file.unlink()
            execution.state['phase'] = 'failed'
            execution._save()
            if managed:
                try:
                    command(['systemctl', 'stop', unit])
                    controller.stop()
                except Exception:
                    execution.state['phase'] = 'stop_unconfirmed'
                    execution._save()
                    raise ApplyError('Apply failed and managed stop is unconfirmed; inspect the service') from None
            raise
    return {'status': 'isolated_configured', 'unit': unit, 'applications': evidence,
            'gui_urls': {app: 'http://{}:{}/'.format(config['bind_address'], IMAGES[app]['port']) for app in config['apps']},
            'note': 'Authenticated host GUI listeners; container outbound networking remains isolated. No host network configuration edits or boot enablement. General deployment and reboot remain unvalidated.'}
