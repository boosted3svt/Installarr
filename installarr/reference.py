"""Reference web-bridge proof of concept using the tested app adapters."""
import copy
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .accounts import prepare_accounts, provisioning_gate
from .apply import app_client, configure_apps, wait_for
from .arr import ArrClient
from .compose import IMAGES, compose_literals, private_artifact, render_bundle
from .credentials import initialize_credentials, read_private_credentials
from .directories import prepare_directories
from .execution import Execution
from .hosthttp import HostHTTP
from .lifecycle import Controller, SERVICE_ROOT, command, install_service, local_mount, root_json, service_status
from .mounts import prepare_mounts
from .prerequisites import prepare_prerequisites
from .network import prepare_standard_docker
from .sab import SabClient
from .bazarr import BazarrClient
from .jackett import JackettClient, JackettHostHTTP
from .netboot import NetbootClient, seed_admin
from .ombi import OmbiClient, OmbiHostHTTP
from .plex import PlexClient, PlexHostHTTP, read_claim_file
from .tautulli import TautulliClient, TautulliHostHTTP, initialize_config

SOCKET = 'unix:///run/docker.sock'
PORTS = {'netbootxyz': [(3250, 3000, 'tcp'), (7171, 80, 'tcp'), (69, 69, 'udp')], 'ombi': [(3579, 3579, 'tcp')], 'plex': [(32400, 32400, 'tcp'), (3005, 3005, 'tcp'), (8324, 8324, 'tcp'), (32469, 32469, 'tcp'),
                  (32410, 32410, 'udp'), (32412, 32412, 'udp'), (32413, 32413, 'udp'), (32414, 32414, 'udp')], 'tautulli': [(8181, 8181, 'tcp')], 'jackett': [(9117, 9117, 'tcp')], 'bazarr': [(6767, 6767, 'tcp')], 'sabnzbd': [(8090, 8080, 'tcp')],
         'radarr': [(7878, 7878, 'tcp')], 'sonarr': [(8989, 8989, 'tcp')]}


def identity(config, published=True):
    return hashlib.sha256(json.dumps({'config': config, 'images': {app: IMAGES[app] for app in config['apps']},
                                     'reference': 'web-published-v1' if published else 'web-bootstrap-v1'},
                                    sort_keys=True).encode()).hexdigest()


def render_reference_bundle(config, published=True):
    if not config.get('data_root'):
        raise ValueError('Reference deployment requires an explicit shared data_root')
    bundle = render_bundle(config)
    token = identity(config, published)
    for app, service in bundle['compose']['services'].items():
        service.pop('network_mode', None)
        service['networks'] = ['web']
        service['labels']['org.installarr.bundle'] = token
        service.pop('depends_on', None)
        if published:
            service['ports'] = [{'host_ip': config['bind_address'], 'published': host, 'target': target, 'protocol': protocol}
                                for host, target, protocol in PORTS[app]]
            service['volumes'].append({'type': 'bind', 'source': compose_literals(str(Path(config['project_directory']) / 'auth-ready.txt')),
                'target': '/installarr-auth-verified', 'read_only': True,
                'bind': {'create_host_path': False, 'propagation': 'rprivate'}})
            guard = bundle['guards'][app + '.guard.sh']
            checks = ['[ ! -L /installarr-auth-verified ] && [ -f /installarr-auth-verified ] || deny',
                      'IFS= read -r auth < /installarr-auth-verified || deny',
                      '[ "$auth" = ' + token + ' ] || deny']
            if app in ('radarr', 'sonarr'):
                checks += ['[ ! -L /config/config.xml ] && [ -s /config/config.xml ] || deny',
                           '[ ! -L /config/' + app + '.db ] && [ -s /config/' + app + '.db ] || deny',
                           "grep -qi '<AuthenticationMethod>Forms</AuthenticationMethod>' /config/config.xml || deny",
                           "grep -qi '<AuthenticationRequired>Enabled</AuthenticationRequired>' /config/config.xml || deny"]
            elif app == 'netbootxyz':
                checks += ['[ ! -L /config/.installarr-admin.htpasswd ] && [ -s /config/.installarr-admin.htpasswd ] || deny',
                           '[ ! -L /config/nginx/site-confs/installarr-admin ] && [ -s /config/nginx/site-confs/installarr-admin ] || deny',
                           "grep -Fq 'auth_basic \"Installarr\";' /config/nginx/site-confs/installarr-admin || deny",
                           "grep -Fq 'auth_basic_user_file /config/.installarr-admin.htpasswd;' /config/nginx/site-confs/installarr-admin || deny"]
            elif app == 'ombi':
                checks += ['[ ! -L /config/Ombi.db ] && [ -s /config/Ombi.db ] || deny']
            elif app == 'plex':
                checks += ["[ ! -L '/config/Library/Application Support/Plex Media Server/Preferences.xml' ] || deny",
                           "grep -Eq 'PlexOnlineToken=\"[^\"]+\"' '/config/Library/Application Support/Plex Media Server/Preferences.xml' || deny"]
            elif app == 'tautulli':
                checks += ['[ ! -L /config/config.ini ] && [ -s /config/config.ini ] || deny',
                           "grep -Eq '^http_password[[:space:]]*=[[:space:]]*PBKDF2' /config/config.ini || deny",
                           "grep -Eq '^http_username[[:space:]]*=[[:space:]]*[^[:space:]]' /config/config.ini || deny"]
            elif app == 'jackett':
                checks += ['[ ! -L /config/Jackett/ServerConfig.json ] && [ -s /config/Jackett/ServerConfig.json ] || deny',
                           "grep -Eq '\"AdminPassword\"[[:space:]]*:[[:space:]]*\"[^\"]+\"' /config/Jackett/ServerConfig.json || deny"]
            elif app == 'bazarr':
                checks += ['[ ! -L /config/config/config.yaml ] && [ -s /config/config/config.yaml ] || deny',
                           "grep -Eq '^  type: basic$' /config/config/config.yaml || deny"]
            else:
                checks += ['[ ! -L /config/sabnzbd.ini ] && [ -s /config/sabnzbd.ini ] || deny',
                           "grep -Eq '^html_login[[:space:]]*=[[:space:]]*0[[:space:]]*$' /config/sabnzbd.ini || deny",
                           "grep -Eq '^username[[:space:]]*=[[:space:]]*[^[:space:]]' /config/sabnzbd.ini || deny",
                           "grep -Eq '^password[[:space:]]*=[[:space:]]*[^[:space:]]' /config/sabnzbd.ini || deny"]
            bundle['guards'][app + '.guard.sh'] = guard.replace('exec "$@"\n', '\n'.join(checks) + '\nexec "$@"\n')
    bundle['compose']['networks'] = {'web': {'driver': 'bridge'}}
    return bundle


def write_reference_bundle(config, published=True):
    bundle = render_reference_bundle(config, published)
    with Execution(config['project_directory'], {'operation': 'reference-bundle-v1', 'config': config, 'published': published}) as execution:
        def write():
            for name, value in bundle['guards'].items():
                private_artifact(execution.directory / name, value.encode(), 0o555)
            for name, value in (('compose.json', bundle['compose']), ('images.json', bundle['images'])):
                private_artifact(execution.directory / name, (json.dumps(value, indent=2) + '\n').encode(), 0o600)
        execution.reconcile('artifacts', write)
    return bundle


def reference_controller(config, project, published=True):
    return Controller(config, project, socket=SOCKET, bundle=render_reference_bundle(config, published))


def existing_service(config, name, state, bootstrap=False):
    """Validate saved unit evidence without ever installing or changing a unit."""
    from .runtime import read_owned
    path = SERVICE_ROOT / name / 'definition.json'
    unit_file = Path('/etc/systemd/system/installarr-' + name + '.service')
    if not os.path.lexists(str(path)):
        if os.path.lexists(str(unit_file)):
            raise ValueError('Existing service name conflicts; preserved')
        return None
    saved = root_json(path)
    expected_mode = 'reference-bootstrap' if bootstrap else 'reference'
    if saved.get('config') != config or saved.get('deployment_mode') != expected_mode:
        raise ValueError('Existing reference deployment differs; preserved')
    actual = hashlib.sha256(read_owned(path, 0o600) + read_owned(unit_file, 0o644)).hexdigest()
    key = 'bootstrap_unit' if bootstrap else 'live_unit'
    if state.state.get(key) != actual:
        raise ValueError('Existing unit evidence differs; preserve it and use the original state directory')
    return unit_file.name


def ensure_service(config, name, state, bootstrap=False):
    unit = existing_service(config, name, state, bootstrap)
    if unit is not None:
        return unit
    install_service(config, name, reference=True, bootstrap=bootstrap)
    path = SERVICE_ROOT / name / 'definition.json'
    unit_file = Path('/etc/systemd/system/installarr-' + name + '.service')
    state.state['bootstrap_unit' if bootstrap else 'live_unit'] = hashlib.sha256(path.read_bytes() + unit_file.read_bytes()).hexdigest()
    state._save()
    return unit_file.name


def remove_owned(controller):
    controller.stop()
    rows = controller.inventory()
    if any(not controller.owns(row) for row in rows):
        raise ValueError('Foreign project containers preserved')
    if rows:
        command(controller.docker + ['rm', *[row['Id'] for row in rows]])


def apply_reference(config, name, state_directory, credentials_file=None, prepare_only=False):
    from .cli import validate, identity_conflicts
    validate(config)
    provisioning_gate()
    from .providers import load_selected_secrets
    provider_credentials = load_selected_secrets(config)
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,25}', name):
        raise ValueError('Reference deployment name must be 1-26 lowercase letters/digits/hyphens')
    if not config['apps'] or set(config['apps']) - set(PORTS):
        raise ValueError('Reference proof of concept currently supports Sonarr/Radarr/SABnzbd/Bazarr/Jackett/Tautulli/Plex/Ombi/netbootxyz')
    render_reference_bundle(config)
    if config.get('plex_claim_file') and not prepare_only:
        read_claim_file(config['plex_claim_file'])
    state_directory = Path(state_directory)
    local_mount(state_directory.parent)
    local_mount(Path(config['project_directory']).parent)
    data = Path(config['data_root'])
    if any(path == data or data in path.parents for path in (state_directory, Path(config['project_directory']))):
        raise ValueError('Private deployment state/bundle must stay outside shared data')
    live = reference_controller(config, 'installarr-' + name)
    boot_config = dict(config, project_directory=str(state_directory / 'bootstrap'))
    boot = reference_controller(boot_config, 'installarr-' + name + '-boot', published=False)
    live_unit = boot_unit = None
    with Execution(state_directory, {'operation': 'reference-apply-v1', 'config': config, 'name': name}) as state:
        # Reject conflicting units before any host preparation. Retain verified
        # names so an early normal-apply failure also stops their supervisors.
        live_unit = existing_service(config, name, state)
        boot_unit = existing_service(boot_config, name + '-boot', state, bootstrap=True)
        previous_phase = state.state.get('phase')
        state.state['phase'] = 'applying'
        state._save()
        try:
            def collect():
                if credentials_file:
                    return read_private_credentials(credentials_file)
                if not sys.stdin.isatty():
                    raise ValueError('Provide a private credentials file for the first unattended reference apply')
                return {'username': input('Shared GUI administrator username: '), 'password': getpass.getpass('Shared GUI administrator password: ')}
            initialize_credentials(state_directory / 'secrets', collect)
            credentials = read_private_credentials(state_directory / 'secrets/gui-admin.json')
            from .credentials import validate_selected_gui_credentials
            validate_selected_gui_credentials(config, credentials)
            state.reconcile('accounts', lambda: prepare_accounts(config, state_directory / 'accounts', identity_conflicts))
            state.reconcile('prerequisites', lambda: prepare_prerequisites(config, state_directory / 'prerequisites'))
            state.reconcile('mounts', lambda: prepare_mounts(config, state_directory / 'mounts'))
            state.reconcile('directories', lambda: prepare_directories(config, state_directory / 'directories'))
            if 'netbootxyz' in config['apps']:
                state.reconcile('netboot_auth_seed', lambda: seed_admin(Path(config['storage']['configs']) / 'netbootxyz', credentials))
            if 'tautulli' in config['apps']:
                state.reconcile('tautulli_auth_seed', lambda: initialize_config(
                    Path(config['storage']['configs']) / 'tautulli', credentials,
                    config['service_user']['uid'], config['service_user']['gid']))
            def images():
                for app in config['apps']:
                    result = subprocess.run(live.docker + ['image', 'inspect', IMAGES[app]['image']], capture_output=True, timeout=15)
                    if result.returncode:
                        command(live.docker + ['pull', IMAGES[app]['image']], timeout=600)
            state.reconcile('docker', prepare_standard_docker)
            state.reconcile('images', images)
            if prepare_only:
                state.state['phase'] = previous_phase if previous_phase == 'reference_poc_ready' else 'reference_prepared'
                state._save()
                return {'status': 'reference_prepared', 'new_application_containers_started': False,
                        'existing_application_services': 'unchanged', 'boot_settings_changed': False,
                        'credentials_file': str(state_directory / 'secrets/gui-admin.json'),
                        'next_step': 'Collect a fresh Plex claim if selected, then rerun the same apply without --prepare-only.'}
            write_reference_bundle(config)
            existing = SERVICE_ROOT / name / 'definition.json'
            if existing.exists():
                live_unit = ensure_service(config, name, state)
                command(['systemctl', 'stop', live_unit])
                remove_owned(live)
            write_reference_bundle(boot_config, published=False)
            boot_unit = ensure_service(boot_config, name + '-boot', state, bootstrap=True)
            command(['systemctl', 'start', boot_unit])
            wait_for(lambda: service_status(name + '-boot').get('phase') == 'containers_running')
            def restart_boot(before_start=None):
                if before_start is None:
                    command(['systemctl', 'restart', boot_unit])
                else:
                    command(['systemctl', 'stop', boot_unit])
                    before_start()
                    command(['systemctl', 'start', boot_unit])
                wait_for(lambda: service_status(name + '-boot').get('phase') == 'containers_running')
            evidence = {}
            def applications():
                evidence.update(configure_apps(config, boot, credentials, restart_boot, download_host='sabnzbd',
                                               family_state_directory=state_directory / 'family-import',
                                               provider_credentials=provider_credentials))
            state.reconcile('bootstrap_auth_and_paths', applications)
            private_artifact(Path(config['project_directory']) / 'auth-ready.txt', (identity(config) + '\n').encode(), 0o444)
            command(['systemctl', 'stop', boot_unit])
            remove_owned(boot)
            live_unit = ensure_service(config, name, state)
            command(['systemctl', 'start', live_unit])
            wait_for(lambda: service_status(name).get('phase') == 'containers_running')
            def verify():
                for app in config['apps']:
                    backend = wait_for(lambda: app_client(config, live, app, credentials))
                    host = HostHTTP(config['bind_address'], PORTS[app][0][0], backend.transport.api_key)
                    if app == 'plex':
                        client = PlexClient(PlexHostHTTP(config['bind_address'], 32400, backend.transport.api_key))
                        evidence[app]['host_authorization'] = client.verify_authorization()
                        continue
                    client = (NetbootClient(host) if app == 'netbootxyz' else
                              OmbiClient(OmbiHostHTTP(config['bind_address'], 3579, '')) if app == 'ombi' else
                              TautulliClient(TautulliHostHTTP(config['bind_address'], 8181, backend.transport.api_key)) if app == 'tautulli' else
                              JackettClient(JackettHostHTTP(config['bind_address'], 9117, backend.transport.api_key), credentials) if app == 'jackett' else
                              SabClient(host) if app == 'sabnzbd' else
                              BazarrClient(host) if app == 'bazarr' else ArrClient(host, backend.expected_version))
                    evidence[app]['host_gui_authentication'] = client.verify_admin(credentials)
                    if app == 'ombi':
                        verified = []
                        with client.administrator(credentials):
                            for target, link in evidence[app]['integrations'].items():
                                remote = wait_for(lambda: app_client(config, live, target))
                                if target in ('radarr', 'sonarr') and 'profile_id' in link:
                                    client.connect_arr(target, remote.transport.api_key, link['profile_id'],
                                                       link['root_id'], link['root_path'])
                                    verified.append(target)
                                elif target == 'plex':
                                    client.connect_plex(remote.transport.api_key, remote.status()['machine_identifier'],
                                        evidence['plex']['configuration']['libraries'],
                                        evidence['plex']['configuration']['server_name'])
                                    verified.append(target)
                            if config.get('ombi_family_presets'):
                                from .ombi_family import configure_family
                                routes = {name: row['routes'] for name, row in evidence[app]['family'].items()}
                                if configure_family(client, routes) != evidence[app]['family']:
                                    raise ValueError('Published Ombi family identities/settings differ')
                                evidence[app]['published_family'] = 'Plex identities/settings verified'
                        evidence[app]['published_integrations'] = ('saved remote lookups verified' if verified
                                                                   else 'no configured links to verify')
            state.reconcile('published_gui', verify)
            state.state['phase'] = 'reference_poc_ready'
            state._save()
        except BaseException:
            state.state['phase'] = 'failed'
            state._save()
            if not prepare_only:
                for unit in (live_unit, boot_unit):
                    if unit:
                        try:
                            command(['systemctl', 'stop', unit])
                        except Exception:
                            pass
                live.stop()
                boot.stop()
            raise
    return {'status': 'reference_poc_ready', 'unit': live_unit, 'applications': evidence,
            'gui_urls': {app: 'http://{}:{}/'.format(config['bind_address'], PORTS[app][0][0]) for app in config['apps']},
            'credentials_file': str(state_directory / 'secrets/gui-admin.json'),
            'note': 'Selected apps passed protected bootstrap and published HTTP checks on the standard bridge. Full clean-host, combined integration and reboot acceptance are separate gates.'}
