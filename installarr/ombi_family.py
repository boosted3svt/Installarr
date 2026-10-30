"""Native Plex-family import and settings for the version-tested Ombi adapter.

The one-shot import is not scheduled: callers must keep their fixture/deployment
protected until import completes. It never creates a local account or password.
"""
import copy

from .arr import AppAPIError

FAMILY = ('lenora8', 'rebel739', 'beanie08')


def settings_values(value):
    # A pristine default settings record receives its first database ID on save.
    return {key: item for key, item in value.items() if key != 'id'}


def family_users(client):
    rows = client.json('GET', '/api/v1/Identity/Users')
    if not isinstance(rows, list):
        raise AppAPIError('Unsupported Ombi users response')
    found = {}
    for name in FAMILY:
        matches = [row for row in rows if str(row.get('userName', '')).lower() == name]
        if len(matches) > 1 or (matches and (matches[0].get('userType') != 2 or not matches[0].get('id'))):
            raise AppAPIError('Family identity conflicts with a non-Plex account; preserved')
        if matches:
            found[name] = matches[0]
    return found


def import_family_once(client, wait, journal=None):
    """Use Ombi's own Plex importer, excluding every unrelated known friend.

    General apply supplies a locked recovery journal before any temporary write.
    """
    existing = family_users(client)
    original_ids = {row['id'] for row in client.json('GET', '/api/v1/Identity/Users')}
    if len(existing) == len(FAMILY):
        return existing
    friends = client.json('GET', '/api/v1/Plex/friends')
    if not isinstance(friends, list):
        raise AppAPIError('Unsupported Plex friends response')
    selected = {}
    for name in FAMILY:
        matches = [row for row in friends if str(row.get('username', '')).lower() == name]
        if len(matches) != 1 or not str(matches[0].get('id', '')).isdigit():
            raise AppAPIError('A required family Plex account is unavailable')
        selected[name] = str(matches[0]['id'])
    endpoint = '/api/v1/Settings/UserManagement'
    original = client.json('GET', endpoint)
    required = {'importPlexUsers', 'importPlexAdmin', 'cleanupPlexUsers', 'bannedPlexUserIds', 'defaultRoles'}
    if not isinstance(original, dict) or not required <= set(original):
        raise AppAPIError('Unsupported Ombi user import settings')
    if original['importPlexUsers'] or original['importPlexAdmin'] or original['cleanupPlexUsers']:
        raise AppAPIError('Existing scheduled Plex import settings preserved')
    if set(original['bannedPlexUserIds'] or []) & set(selected.values()):
        raise AppAPIError('An explicitly banned family Plex account was preserved')
    candidate = copy.deepcopy(original)
    candidate.update(importPlexUsers=True, importPlexAdmin=False, cleanupPlexUsers=False,
                     defaultRoles=[], bannedPlexUserIds=sorted(set(original['bannedPlexUserIds'] or []) |
                     {str(row['id']) for row in friends if str(row.get('id')) not in selected.values()}))
    if journal is not None:
        journal.state['restore_settings'] = original
        journal._save()
    try:
        if client.json('POST', endpoint, candidate) is not True:
            raise AppAPIError('Ombi temporary import selection refused')
        if settings_values(client.json('GET', endpoint)) != settings_values(candidate):
            raise AppAPIError('Ombi temporary import selection readback differs')
        if client.json('POST', '/api/v1/Job/plexuserimporter') is not True:
            raise AppAPIError('Ombi native Plex import refused')
        def imported():
            users = family_users(client)
            return users if len(users) == len(FAMILY) else None
        users = wait(imported)
        actual_ids = {row['id'] for row in client.json('GET', '/api/v1/Identity/Users')}
        if actual_ids - original_ids - {row['id'] for row in users.values()}:
            raise AppAPIError('Unexpected Plex imports detected; publication refused')
        return users
    finally:
        if client.json('POST', endpoint, original) is not True or settings_values(client.json('GET', endpoint)) != settings_values(original):
            raise AppAPIError('Ombi user import settings restoration failed')
        if journal is not None:
            journal.state.pop('restore_settings', None)
            journal._save()


def configure_family(client, routes, discord_targets=None):
    """Reconcile roles/overrides only for existing genuine Plex identities."""
    discord_targets = validate_discord_targets(discord_targets or {})
    users = family_users(client)
    if set(users) != set(FAMILY) or set(routes) != set(FAMILY):
        raise AppAPIError('All three imported Plex identities and routes are required')
    allowed = {'radarrRootPath', 'radarrQualityProfile', 'sonarrRootPath', 'sonarrQualityProfile'}
    plans = []
    for name in FAMILY:
        route = routes[name]
        if (not isinstance(route, dict) or set(route) - allowed
                or any(type(value) is not int or value < 0 for value in route.values())
                or (name == 'beanie08' and any(route.values()))):
            raise AppAPIError('Invalid family profile/root overrides')
        user = users[name]
        claims = copy.deepcopy(user.get('claims'))
        if not isinstance(claims, list):
            raise AppAPIError('Unsupported Ombi family roles')
        desired_roles = {'RequestMovie', 'RequestTv', 'AutoApproveMovie', 'AutoApproveTv'}
        if name == 'beanie08':
            desired_roles.add('PowerUser')
        if any(sum(row.get('value') == role for row in claims) != 1 for role in desired_roles):
            raise AppAPIError('Required Ombi family roles unavailable')
        for row in claims:
            if row.get('value') in desired_roles:
                row['enabled'] = True
        profiles = copy.deepcopy(user.get('userQualityProfiles'))
        if not isinstance(profiles, dict) or set(route) - set(profiles):
            raise AppAPIError('Unsupported Ombi per-user profile settings')
        profiles.update(route)
        if name == 'beanie08':
            # Zero is the native sentinel for inheriting the global settings.
            for key in allowed | {'radarr4KRootPath', 'radarr4KQualityProfile',
                                  'sonarrRootPathAnime', 'sonarrQualityProfileAnime'}:
                if key in profiles:
                    profiles[key] = 0
        desired = dict(user, claims=claims, userQualityProfiles=profiles, password=None)
        plans.append((name, user, desired))
    result = {}
    for name, original, desired in plans:
        if original.get('claims') != desired['claims'] or original.get('userQualityProfiles') != desired['userQualityProfiles']:
            response = client.json('PUT', '/api/v1/Identity', desired)
            if not isinstance(response, dict) or response.get('successful') is not True:
                raise AppAPIError('Ombi family settings save refused')
        saved = client.json('GET', '/api/v1/Identity/User/' + original['id'])
        if (saved.get('id') != original['id'] or saved.get('userType') != 2
                or sorted((r.get('value'), r.get('enabled')) for r in saved.get('claims', []))
                   != sorted((r.get('value'), r.get('enabled')) for r in desired['claims'])
                or any(saved.get('userQualityProfiles', {}).get(key) != value
                       for key, value in desired['userQualityProfiles'].items() if key not in ('id', 'userId'))):
            raise AppAPIError('Ombi family settings readback differs')
        ensure_discord_preference(client, saved['id'], discord_targets.get(name))
        result[name] = {'id': saved['id'], 'identity': 'Plex', 'routes': routes[name],
                        'power_user': name == 'beanie08', 'auto_approve_movie_tv': True}
    return result


def import_family(client, wait, state_directory, machine_identifier):
    """Recover an interrupted temporary import before considering any new work."""
    from .execution import Execution
    with Execution(state_directory, {'operation': 'ombi-family-import-v1',
                                    'machine_identifier': machine_identifier}) as journal:
        original = journal.state.get('restore_settings')
        if original is not None:
            endpoint = '/api/v1/Settings/UserManagement'
            if (not isinstance(original, dict) or client.json('POST', endpoint, original) is not True
                    or settings_values(client.json('GET', endpoint)) != settings_values(original)):
                raise AppAPIError('Interrupted Ombi import could not be restored; publication refused')
            journal.state.pop('restore_settings')
            journal._save()
        return import_family_once(client, wait, journal)


def family_paths(config):
    from pathlib import Path
    from .compose import data_targets
    base = data_targets(config)['media'].rstrip('/')
    if 'folder_map' in config:
        from .layout import role
        return {name: {app: {'host_path': role(config, key)['host'], 'container_path': role(config, key)['target']}
                       for app, key in pairs.items() if app in config['apps']}
                for name, pairs in {'lenora8': {'radarr': 'lenora_movies', 'sonarr': 'lenora_tv'},
                                    'rebel739': {'radarr': 'jeremy_movies', 'sonarr': 'jeremy_tv'}}.items()}
    return {name: {app: {'host_path': str(Path(config['storage']['media']) / leaf),
                        'container_path': base + '/' + leaf}
                   for app, leaf in entries.items() if app in config['apps']}
            for name, entries in {'lenora8': {'radarr': 'lenoramovies', 'sonarr': 'lenoratv'},
                                  'rebel739': {'radarr': 'jeremymovies', 'sonarr': 'jeremytv'}}.items()}


def validate_family_config(config):
    enabled = config.get('ombi_family_presets', False)
    if type(enabled) is not bool:
        raise ValueError('Ombi family preset choice must be yes/no')
    path = config.get('ombi_family_preferences_file')
    if path is not None:
        from .hostplan import absolute_path
        if not enabled or not absolute_path(path):
            raise ValueError('Private family preference file requires family presets and an absolute path')
    if not enabled:
        return
    if not {'ombi', 'plex'} <= set(config['apps']) or not set(config['apps']) & {'radarr', 'sonarr'}:
        raise ValueError('Family presets require Ombi, Plex and at least one request application')
    from .profiles import RECOMMENDED
    for app in set(config['apps']) & {'radarr', 'sonarr'}:
        choice = config.get('quality_profiles', {}).get(app, {})
        if RECOMMENDED[app]['default'] not in choice.get('available', []):
            raise ValueError('Family presets require the recommended full 1080p profile for each selected request app')


def validate_discord_targets(values):
    import re
    if (not isinstance(values, dict) or set(values) - set(FAMILY)
            or any(not isinstance(value, str) or not re.fullmatch(r'[0-9]{17,20}', value)
                   or not 0 < int(value) < 2**64 for value in values.values())):
        raise ValueError('Family Discord IDs must be numeric account IDs for the configured Plex usernames')
    return values


def read_family_preferences(path):
    from .credentials import read_private_json
    return validate_discord_targets(read_private_json(path))


def initialize_family_preferences(directory, collect):
    from pathlib import Path
    from .execution import Execution, private_directory
    from .compose import private_artifact
    import json
    directory = private_directory(directory)
    target = directory / 'family.json'
    with Execution(directory / '.state', {'operation': 'family-preferences-v1'}):
        if target.exists():
            read_family_preferences(target)
            return {'status': 'reused', 'path': str(target)}
        values = validate_discord_targets(collect())
        private_artifact(target, (json.dumps(values) + '\n').encode(), 0o600)
        return {'status': 'saved', 'path': str(target)}


def ensure_discord_preference(client, user_id, target=None):
    """Save the notification target separately from notification enablement."""
    if not isinstance(user_id, str) or not user_id or '/' in user_id:
        raise AppAPIError('Invalid Ombi user identity')
    if target is not None:
        validate_discord_targets({FAMILY[0]: target})
    preferences = client.json('GET', '/api/v1/Identity/notificationpreferences/' + user_id)
    discord = [row for row in preferences if row.get('agent') == 1] if isinstance(preferences, list) else []
    if len(discord) != 1 or type(discord[0].get('enabled')) is not bool:
        raise AppAPIError('Unsupported Ombi Discord preference schema')
    desired = target if target is not None else discord[0].get('value') or ''
    if discord[0].get('value') != desired or discord[0]['enabled']:
        if client.json('POST', '/api/v1/Identity/NotificationPreferences',
                       [{'userId': user_id, 'agent': 1, 'value': desired, 'enabled': False}]) is not True:
            raise AppAPIError('Ombi Discord target save refused')
    readback = client.json('GET', '/api/v1/Identity/notificationpreferences/' + user_id)
    actual = [row for row in readback if row.get('agent') == 1] if isinstance(readback, list) else []
    if len(actual) != 1 or actual[0].get('value') != desired or actual[0].get('enabled') is not False:
        raise AppAPIError('Ombi disabled Discord target readback differs')
    return {'target_saved': bool(desired), 'notifications_enabled': False}
