"""Explicit host folders, stable container paths and per-application access."""
from pathlib import Path
from .hostplan import absolute_path, storage_assertions

FOLDERS = {
    'movies': 'media-movies', 'lenora_movies': 'media-lenoramovies',
    'jeremy_movies': 'media-jeremymovies', 'tv': 'media-tv',
    'lenora_tv': 'media-lenoratv', 'jeremy_tv': 'media-jeremytv',
    'sports': 'media-Sports', 'standup': 'media-Standup',
}
MOVIES = ('movies', 'lenora_movies', 'jeremy_movies', 'secondary')
TV = ('tv', 'lenora_tv', 'jeremy_tv')


def default_folders(root):
    return {key: str(Path(root) / leaf) for key, leaf in FOLDERS.items()}


def validate_layout(config):
    if 'folder_map' not in config:
        return
    folders = config['folder_map']
    if not isinstance(folders, dict) or set(folders) != set(FOLDERS):
        raise ValueError('Explicit media layout requires all eight named media folders')
    if config.get('data_root') != config['storage']['media']:
        raise ValueError('Explicit layout data root must identify its primary media root')
    if 'media_secondary' in config['storage'] and config.get('secondary_media_read_only', True):
        raise ValueError('Explicit writable movie layout requires writable secondary preparation')
    paths = []
    for value in folders.values():
        if not absolute_path(value):
            raise ValueError('Media folders require absolute non-root paths without whitespace')
        path = Path(value)
        root = Path(config['storage']['media'])
        if root not in path.parents:
            raise ValueError('Primary media folders must be inside the selected media root')
        paths.append(path)
    if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(paths) for b in paths[i + 1:]):
        raise ValueError('Media folder roles must not overlap')
    private = [Path(config['storage'][key]) for key in ('configs', 'backups')]
    data = paths + [Path(config['storage'][key]) for key in ('downloads', 'incomplete')]
    if 'media_secondary' in config['storage']:
        data.append(Path(config['storage']['media_secondary']))
    if 'netboot_assets' in config['storage']:
        data.append(Path(config['storage']['netboot_assets']))
    for i, a in enumerate(data):
        for b in data[i + 1:] + private:
            if a == b or a in b.parents or b in a.parents:
                raise ValueError('Media, download and private folder roles must not overlap')
    for key in ('media', 'downloads', 'incomplete'):
        check = storage_assertions(config).get(key)
        if not check or not check.get('sentinel'):
            raise ValueError('Explicit layout requires exact storage checks and health markers')
        path, point = Path(config['storage'][key]), Path(check['mountpoint'])
        if path != point and point not in path.parents:
            raise ValueError('Storage role must be inside its asserted filesystem')
        if config['storage_mounts'].get(key, {}).get('kind') == 'local' and check['fstype'] not in ('ext4', 'xfs', 'btrfs'):
            raise ValueError('Local storage selection must assert a supported local filesystem')
    identities = {}
    for check in storage_assertions(config).values():
        identity = (check['source'], check['fstype'])
        point = check['mountpoint']
        if point in identities and identities[point] != identity:
            raise ValueError('Conflicting filesystem identities for one selected mount')
        identities[point] = identity


def entries(config):
    """All data entries carry their own asserted source, even in mixed layouts."""
    checks = storage_assertions(config)
    rows = []
    for role, path in config['folder_map'].items():
        rows.append({'role': role, 'host': path, 'target': '/data/' + FOLDERS[role],
                     'purpose': 'media', 'check': checks['media']})
    for role, purpose, leaf in (('finished', 'downloads', 'finished-downloads'),
                                ('unfinished', 'incomplete', 'unfinished-downloads')):
        rows.append({'role': role, 'host': config['storage'][purpose], 'target': '/data/' + leaf,
                     'purpose': purpose, 'check': checks[purpose]})
    if 'media_secondary' in config['storage']:
        rows.append({'role': 'secondary', 'host': config['storage']['media_secondary'],
                     'target': '/data/media-movies-2', 'purpose': 'media_secondary',
                     'check': checks['media_secondary']})
    return rows


def app_entries(config, app):
    roles = {'sabnzbd': ('finished', 'unfinished'),
             'radarr': ('finished',) + MOVIES + ('sports', 'standup'),
             'sonarr': ('finished',) + TV,
             'plex': MOVIES + TV + ('sports', 'standup'),
             'bazarr': MOVIES + TV + ('sports', 'standup')}.get(app, ())
    return [row for row in entries(config) if row['role'] in roles]


def role(config, name):
    return next(row for row in entries(config) if row['role'] == name)


def libraries(config):
    movies = [key for key in MOVIES if key != 'secondary' or 'media_secondary' in config['storage']]
    return [{'name': name, 'type': kind, 'relative_paths': list(roles), 'language': 'en-US'}
            for name, kind, roles in (('Movies', 'movie', movies), ('TV Shows', 'show', TV),
                                     ('Sports', 'other', ('sports',)), ('Standup', 'movie', ('standup',)))]
