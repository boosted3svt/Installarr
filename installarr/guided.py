"""Plain-language setup with stable saved settings and advanced CLI kept separate."""
import getpass
import json
import os
from pathlib import Path
import platform
import sys

APPS = (
    ('plex', 'Plex — watch your movies and TV shows', True),
    ('radarr', 'Radarr — manage movies', True),
    ('sonarr', 'Sonarr — manage TV shows', True),
    ('sabnzbd', 'SABnzbd — download from a Usenet subscription', True),
    ('bazarr', 'Bazarr — find subtitles', True),
    ('ombi', 'Ombi — let family request movies and shows', True),
    ('tautulli', 'Tautulli — view Plex activity', True),
    ('jackett', 'Jackett — connect additional indexers (needs separate download setup)', True),
    ('netbootxyz', 'netboot.xyz — start other computers over the network', True),
)


def ask(label, default=''):
    suffix = ' [{}]'.format(default) if default else ''
    return input(label + suffix + ': ').strip() or default


def yes(label, default=True):
    while True:
        answer = ask(label + ' (yes/no)', 'yes' if default else 'no').lower()
        if answer in ('yes', 'y'):
            return True
        if answer in ('no', 'n'):
            return False
        print('Please enter yes or no.')


def media_identity():
    """Choose a non-root identity without asking a household user for UID numbers."""
    import pwd
    import grp
    try:
        existing = pwd.getpwnam('media')
    except KeyError:
        existing = None
    if existing:
        if existing.pw_uid < 1000 or existing.pw_gid in (0, 911, 1001):
            raise ValueError('Existing media account requires administrator review')
        return {'name': 'media', 'uid': existing.pw_uid, 'gid': existing.pw_gid}
    for identity in range(2000, 60000):
        try:
            pwd.getpwuid(identity)
            continue
        except KeyError:
            pass
        try:
            grp.getgrgid(identity)
            continue
        except KeyError:
            pass
        return {'name': 'media', 'uid': identity, 'gid': identity}
    raise ValueError('No available media account identity')


def checked_answer(label, default, validator):
    while True:
        value = ask(label, default)
        try:
            validator(value)
            return value
        except (ValueError, OSError):
            print('That answer could not be used. Please check it and try again.')


def folder(value):
    if not Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError('Choose a full folder path')


def summary(config):
    print('\nYour setup')
    print('  Programs: ' + ', '.join(config['apps']))
    print('  Media and downloads: ' + config['data_root'])
    if config['storage'].get('media_secondary'):
        print('  Additional movies: ' + config['storage']['media_secondary'])
    print('  Server address: ' + config['bind_address'])
    print('  Time zone: ' + config['timezone'])
    if 'radarr' in config['apps']:
        print('  Movies: prefer 1080p; 4K is available for manual upgrades.')
    if 'bazarr' in config['apps']:
        print('  Subtitles: standard English; OpenSubtitles.com when selected.')
    print('  Existing media files will be preserved.')


def collect_settings(base):
    from .cli import detected_address, plan, validate_timezone
    from ipaddress import IPv4Address
    from .storage import covering_mount, mount_inventory
    from .cli import command
    from .plex import reference_libraries
    from .profiles import recommended_profiles
    print('\nChoose what this computer should run. Press Enter to accept a suggested answer.')
    selected = []
    while not selected:
        selected = [name for name, label, default in APPS if yes('Use ' + label + '?', default)]
        if not selected:
            print('Please choose at least one program to set up.')
    print('\nWhere are your media files? Enter a folder on this computer, including an already connected NAS.')
    print('If your NAS is not connected yet, choose "no" below; setup can connect an NFS share.')
    root = checked_answer('Folder for media and downloads', '/media/Media', folder)
    inventory = mount_inventory(command)
    actual = covering_mount(root, inventory.get('filesystems', []))
    connected = yes('Is the media drive or NAS already connected?',
                    bool(actual and actual.get('fstype') in ('nfs', 'nfs4', 'cifs')))
    if connected:
        if inventory['status'] != 'observed':
            raise ValueError('Unable to identify the media drive')
        actual = covering_mount(root, inventory['filesystems'])
        if not actual:
            raise ValueError('Unable to identify the media drive')
        check = {'mountpoint': actual['target'], 'source': actual['source'],
                 'fstype': actual['fstype'], 'sentinel': 'installarr-health'}
        mount = dict(check, kind='existing') if actual['fstype'] in ('nfs', 'nfs4', 'cifs') else {'kind': 'local'}
    else:
        print('Use the NFS server and shared-folder address supplied with your NAS settings.')
        source = ask('NAS address and shared folder', '192.168.1.103:/share/MD0_DATA/Public')
        point = ask('Connect the NAS at this folder', '/media/Media')
        if Path(root) != Path(point) and Path(point) not in Path(root).parents:
            print('The media folder must be inside the connected NAS folder.')
            root = ask('Folder for media and downloads', point)
        check = {'mountpoint': point, 'source': source, 'fstype': 'nfs', 'sentinel': 'installarr-health'}
        mount = dict(check, kind='nfs')
    paths = {'media': root, 'downloads': root + '/downloads', 'incomplete': root + '/incomplete-downloads',
             'configs': str(base / 'apps'), 'backups': str(base / 'backups')}
    config = {'schema_version': 1, 'apps': selected, 'hostname': platform.node(),
              'timezone': checked_answer('Time zone', 'America/Chicago', validate_timezone),
              'bind_address': checked_answer('Address for opening this server from your other devices', detected_address(), IPv4Address),
              'plex_allowed_networks': '192.168.0.0/23', 'project_directory': str(base / 'project'),
              'service_user': media_identity(), 'data_root': root,
              'storage': paths, 'storage_mounts': {key: dict(mount) for key in ('media', 'downloads', 'incomplete')},
              'storage_checks': {key: dict(check) for key in ('media', 'downloads', 'incomplete')}}
    config['storage_mounts'].update(configs={'kind': 'local'}, backups={'kind': 'local'})
    if 'plex' in selected:
        config.update(plex_server_name=ask('Name to show in Plex', 'Family Media'),
                      plex_libraries=reference_libraries(), plex_claim_file=str(base / 'plex' / 'plex-claim.txt'))
        print('Plex will group movie folders in Movies and TV folders in TV, plus sports, StandUp and Music.')
    if set(selected) & {'plex', 'radarr', 'bazarr'} and yes('Also use the additional movie folder on the second NAS?', True):
        secondary_path, secondary_mount, secondary_check = additional_movies(inventory)
        config['storage']['media_secondary'] = secondary_path
        config['storage_mounts']['media_secondary'] = secondary_mount
        config['storage_checks']['media_secondary'] = secondary_check
        config['secondary_media_read_only'] = False
    if 'netbootxyz' in selected:
        assets = checked_answer('Folder for network boot files', '/media/netbootxyz/assets', folder)
        actual = covering_mount(assets, inventory.get('filesystems', []))
        if not actual:
            raise ValueError('Unable to identify the drive for network boot files')
        asset_check = {'mountpoint': actual['target'], 'source': actual['source'], 'fstype': actual['fstype'], 'sentinel': 'installarr-assets-health'}
        config['storage']['netboot_assets'] = assets
        config['storage_checks']['netboot_assets'] = asset_check
        config['storage_mounts']['netboot_assets'] = dict(asset_check, kind='existing') if actual['fstype'] in ('nfs', 'nfs4', 'cifs') else {'kind': 'local'}
    if set(selected) & {'radarr', 'sonarr'}:
        config['quality_profiles'] = recommended_profiles(selected)
    if {'ombi', 'plex'} <= set(selected) and set(selected) & {'radarr', 'sonarr'}:
        config['ombi_family_presets'] = yes('Use the saved Lenora, Jeremy and Beanie request rules?', True)
        if config['ombi_family_presets']:
            config['ombi_family_preferences_file'] = str(base / 'family' / 'family.json')
    providers = {}
    if 'sabnzbd' in selected and yes('Do you have a Newshosting subscription?', True):
        def connections(value):
            if not 1 <= int(value) <= 100:
                raise ValueError('Connection limit')
        providers['newshosting'] = {'connections': int(checked_answer('Connections allowed by your Newshosting subscription', '100', connections))}
    if set(selected) & {'radarr', 'sonarr'} and yes('Do you have an NZBGeek account?', True):
        providers['nzbgeek'] = {}
    if 'bazarr' in selected:
        config['bazarr_language_profile'] = 'english-standard'
        if yes('Use your OpenSubtitles.com account to find subtitles?', True):
            providers['bazarr'] = {'enabled': ['opensubtitlescom']}
    if providers:
        config.update(providers=providers, provider_secrets_file=str(base / 'providers' / 'providers.json'))
    reviewed = plan(config)
    if reviewed['conflicts']:
        print('Setup found an account conflict:')
        for conflict in reviewed['conflicts']:
            print('  ' + conflict)
        print('No installation has started. Use the advanced settings to resolve this conflict.')
        raise ValueError('Account conflict')
    return config


def collect_gui():
    print('\nChoose one administrator login for the programs that support it.')
    print('Plex uses your own Plex sign-in. Keep this shared login with your recovery instructions.')
    username = ask('Administrator username', 'admin')
    while True:
        password = getpass.getpass('Administrator password (hidden): ')
        if password and getpass.getpass('Enter the password again: ') == password:
            return {'username': username, 'password': password}
        print('The passwords did not match or were empty. Please try again.')


def collect_provider(name):
    labels = {'newshosting': 'Newshosting', 'nzbgeek': 'NZBGeek', 'opensubtitlescom': 'OpenSubtitles.com'}
    print('\nAccount details for ' + labels[name] + ' (saved privately on this computer).')
    if name == 'nzbgeek':
        print('Find your API key in the account section of the NZBGeek website.')
        return {'api_key': getpass.getpass('NZBGeek API key (hidden): ')}
    return {'username': getpass.getpass('Username (hidden): '), 'password': getpass.getpass('Password (hidden): ')}


def is_administrator():
    return os.geteuid() == 0


def run_setup(base=Path('/var/lib/installarr-setup')):
    from .execution import private_directory
    from .cli import save_config, validate
    from .credentials import initialize_credentials, read_private_json
    from .providers import required_secrets
    from .provider_secrets import initialize_provider_secrets
    from .reference import apply_reference
    if not sys.stdin.isatty():
        print('Open Installarr in a terminal to follow the setup guide. Advanced commands support unattended use.')
        return 2
    print('\nWelcome to Installarr\nSet up your family media server, or continue a saved installation.')
    print('This guide installs your programs and connects them to your media folders and accounts.')
    if not yes('Continue?', True):
        return 0
    if not is_administrator():
        print('Ubuntu needs your computer administrator password to install programs.')
        os.execvp('sudo', ['sudo', sys.executable, '-m', 'installarr', 'setup'])
        return 1
    base = private_directory(base)
    path = base / 'settings.json'
    if path.exists():
        config = validate(read_private_json(path))
        print('\nFound your saved setup. Your account details will be reused; you do not need to enter them again.')
        summary(config)
        if not yes('Continue this saved installation?', True):
            print('Saved settings kept. No installation started.')
            return 0
    else:
        config = collect_settings(base)
        summary(config)
        print('You can stop here and keep a copy of these choices without installing anything.')
        if not yes('Save these choices?', True):
            return 0
        save_config(path, config)
    if not yes('Start installation? This can install packages, connect storage and start the selected programs.', False):
        print('Your choices are saved. Run installarr again whenever you are ready.')
        return 0
    gui = base / 'login'
    from .credentials import validate_selected_gui_credentials
    initialize_credentials(gui, lambda: validate_selected_gui_credentials(config, collect_gui()))
    names = sorted(required_secrets(config))
    if names:
        target = Path(config['provider_secrets_file'])
        initialize_provider_secrets(target.parent, names, collect_provider, target.name)
    if config.get('ombi_family_preferences_file'):
        from .ombi_family import initialize_family_preferences
        initialize_family_preferences(Path(config['ombi_family_preferences_file']).parent, collect_family)
    state = base / 'state'
    print('\nPreparing the computer and downloading programs. This can take a while.')
    apply_reference(config, 'family-media', state, credentials_file=gui / 'gui-admin.json', prepare_only=True)
    ready = read_private_json(state / 'state.json').get('phase') == 'reference_poc_ready'
    if 'plex' in config['apps'] and not ready:
        print('\nPlex needs your permission to connect this server to your account.')
        print('Open https://www.plex.tv/claim on your phone or another computer, sign in, and copy the claim code.')
        from .plex import store_claim
        target = Path(config['plex_claim_file'])
        store_claim(target.parent, lambda: getpass.getpass('Plex claim code (hidden): '), replace=True, filename=target.name)
    print('\nConnecting the programs and checking sign-in and storage access.')
    apply_reference(config, 'family-media', state, credentials_file=gui / 'gui-admin.json')
    automatic_start = yes('Start these programs automatically when this computer turns on?', True)
    if automatic_start:
        from .boot import enable_startup
        enable_startup(config, 'family-media', state)
    print('\nSetup checks finished. Open your programs at:')
    ports = {'plex': '32400/web', 'radarr': '7878', 'sonarr': '8989', 'sabnzbd': '8090', 'bazarr': '6767',
             'ombi': '3579', 'tautulli': '8181', 'jackett': '9117', 'netbootxyz': '3250'}
    for app in config['apps']:
        print('  {}: http://{}:{}'.format(app, config['bind_address'], ports[app]))
    print('Use the administrator login you chose above, or your Plex account where requested.')
    print('Automatic startup is on.' if automatic_start else 'The programs are running now; automatic startup is off.')
    print('Your settings and private account details are saved on this computer for continuing setup.')
    return 0


def collect_family():
    from .ombi_family import FAMILY, validate_discord_targets
    print('Optional: save family Discord account numbers in Ombi. Sending notifications stays disabled.')
    print('Press Enter to skip any account you do not know. These are numeric IDs, not usernames or passwords.')
    values = {}
    for name in FAMILY:
        while True:
            value = getpass.getpass('Discord account number for ' + name + ' (hidden, optional): ').strip()
            if not value:
                break
            try:
                validate_discord_targets({name: value})
                values[name] = value
                break
            except ValueError:
                print('Please enter a numeric Discord account ID, or press Enter to skip.')
    return values


def additional_movies(inventory):
    from .storage import covering_mount
    path = checked_answer('Additional movie folder', '/media/NAS/Movies', folder)
    actual = covering_mount(path, inventory.get('filesystems', []))
    connected = yes('Is the second NAS already connected?', bool(actual and actual.get('fstype') in ('nfs', 'nfs4', 'cifs')))
    if connected:
        if not actual:
            raise ValueError('Unable to identify the second media drive')
        check = {'mountpoint': actual['target'], 'source': actual['source'], 'fstype': actual['fstype'], 'sentinel': 'installarr-health'}
        mount = dict(check, kind='existing') if actual['fstype'] in ('nfs', 'nfs4', 'cifs') else {'kind': 'local'}
    else:
        point = checked_answer('Connect the second NAS at this folder', '/media/NAS', folder)
        source = ask('Second NAS address and shared folder', '192.168.1.102:/share/MD0_DATA/Public')
        check = {'mountpoint': point, 'source': source, 'fstype': 'nfs', 'sentinel': 'installarr-health'}
        mount = dict(check, kind='nfs')
    return path, mount, check
