"""Pinned TRaSH size limits; preserve operator edits and unrelated qualities."""
import copy
from .arr import AppAPIError
from .profiles import Catalog, COMMIT


def factory_sizes(app, name):
    # Exact factory values from tested upstream Quality.cs versions:
    # Radarr6.4.4.10685 and Sonarr4.0.20.3014.
    if app == 'radarr':
        unlimited = name in ('Bluray-1080p', 'Remux-1080p') or name.endswith('2160p')
        return {'minSize': 0, 'preferredSize': None if unlimited else 95,
                'maxSize': None if unlimited else 100}
    defaults = {
        'HDTV-720p': (3, 125), 'HDTV-1080p': (4, 125), 'HDTV-2160p': (35, 199.9),
        'WEBRip-720p': (3, 130), 'WEBDL-720p': (3, 130), 'Bluray-720p': (4, 130),
        'WEBRip-1080p': (4, 130), 'WEBDL-1080p': (4, 130), 'Bluray-1080p': (4, 155),
        'Bluray-1080p Remux': (35, None), 'WEBRip-2160p': (35, None),
        'WEBDL-2160p': (35, None), 'Bluray-2160p': (35, None), 'Bluray-2160p Remux': (35, None),
    }
    if name not in defaults:
        raise AppAPIError('Untested quality-size factory schema; preserved')
    minimum, maximum = defaults[name]
    return {'minSize': minimum, 'preferredSize': 95, 'maxSize': maximum}


def ensure_quality_sizes(client, app):
    if app not in ('radarr', 'sonarr'):
        raise AppAPIError('Unsupported quality-size application')
    filename = app + '/quality-size/' + ('movie' if app == 'radarr' else 'series') + '.json'
    definitions = Catalog().documents[filename]['qualities']
    maximum = 2000 if app == 'radarr' else 1000
    if client.json('GET', 'qualitydefinition/limits') != {'min': 0, 'max': maximum}:
        raise AppAPIError('Untested quality-size limits; no writes attempted')
    rows = client.json('GET', 'qualitydefinition')
    if not isinstance(rows, list):
        raise AppAPIError('Unsupported quality-size inventory')
    plans = []
    for guide in definitions:
        matches = [r for r in rows if r.get('quality', {}).get('name') == guide['quality']]
        if len(matches) != 1 or type(matches[0].get('id')) is not int:
            raise AppAPIError('Pinned quality-size schema differs; no writes attempted')
        row = matches[0]
        desired = {field: None if guide[key] >= maximum else guide[key]
                   for field, key in (('minSize', 'min'), ('preferredSize', 'preferred'), ('maxSize', 'max'))}
        current = {key: row.get(key) for key in desired}
        if current not in (desired, factory_sizes(app, guide['quality'])):
            raise AppAPIError('Existing quality-size settings differ from factory and pinned guide; preserved')
        plans.append((row, desired))
    for row, desired in plans:
        if any(row.get(key) != value for key, value in desired.items()):
            client.json('PUT', 'qualitydefinition/' + str(row['id']), dict(copy.deepcopy(row), **desired))
    saved = client.json('GET', 'qualitydefinition')
    for row, desired in plans:
        matches = [r for r in saved if r.get('id') == row['id']]
        if len(matches) != 1 or any(matches[0].get(key) != value for key, value in desired.items()):
            raise AppAPIError('Pinned quality-size write/readback differs')
    return {'commit': COMMIT, 'preset': 'movie' if app == 'radarr' else 'series',
            'qualities': len(plans), 'readback': 'verified'}
