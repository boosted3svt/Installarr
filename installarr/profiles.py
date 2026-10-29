"""Offline, commit-pinned TRaSH profiles including default/required CF groups."""
import copy
import hashlib
import json
from pathlib import Path
import re

from .arr import AppAPIError

COMMIT = 'd24f13ceea5e82ccc20d08b7814fca93840e4046'
DATA = Path(__file__).parent / 'data/trash'


# Preferred profile is installer metadata for future request routing; never bulk
# reassign existing movie/series records.
RECOMMENDED = {
    'radarr': {'default': '9ca12ea80aa55ef916e3751f4b874151',
               'available': ['9ca12ea80aa55ef916e3751f4b874151', 'fd161a61e3ab826d3a22d53f935696dd']},
    'sonarr': {'default': '72dae194fc92bf828f32cde7744e51a1',
               'available': ['72dae194fc92bf828f32cde7744e51a1']},
}


def recommended_profiles(apps):
    return {app: copy.deepcopy(value) for app, value in RECOMMENDED.items() if app in apps}


def validate_selections(config):
    selections = config.get('quality_profiles', {})
    if not isinstance(selections, dict) or set(selections) - (set(config['apps']) & {'radarr', 'sonarr'}):
        raise ValueError('Quality profiles require a selected Radarr or Sonarr app')
    catalog = Catalog() if selections else None
    for app, choice in selections.items():
        if not isinstance(choice, dict) or set(choice) != {'default', 'available'}:
            raise ValueError('Quality profiles require default and available IDs')
        ids = choice['available']
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Available quality profiles must be unique pinned IDs')
        if not isinstance(choice['default'], str) or choice['default'] not in ids:
            raise ValueError('Default quality profile must be available')
        for identifier in ids:
            catalog.resolve(app, identifier)
    return selections


class Catalog:
    def __init__(self, directory=DATA):
        self.directory = Path(directory)
        manifest = json.loads((self.directory / 'manifest.json').read_text())
        if manifest.get('commit') != COMMIT or manifest.get('repository') != 'https://github.com/TRaSH-Guides/Guides':
            raise ValueError('TRaSH snapshot revision differs')
        self.documents = {}
        for name, expected in manifest['files'].items():
            path = Path(name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Invalid TRaSH snapshot path')
            content = (self.directory / path).read_bytes()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError('TRaSH snapshot checksum differs')
            self.documents[name] = json.loads(content)

    def section(self, app, section):
        if app not in ('radarr', 'sonarr'):
            raise ValueError('TRaSH profiles require Sonarr or Radarr')
        prefix = app + '/' + section + '/'
        return {doc['trash_id']: doc for name, doc in self.documents.items()
                if name.startswith(prefix) and isinstance(doc, dict) and 'trash_id' in doc}

    def list_profiles(self, app):
        return sorted([{'id': item['trash_id'], 'name': item['name']}
                       for item in self.section(app, 'quality-profiles').values()
                       if item.get('group') != 99], key=lambda item: item['name'])

    def resolve(self, app, profile_id):
        profiles = self.section(app, 'quality-profiles')
        if profile_id not in profiles or profiles[profile_id].get('group') == 99:
            raise ValueError('Select an explicit supported TRaSH profile ID')
        profile = copy.deepcopy(profiles[profile_id])
        selected = set(profile.get('formatItems', {}).values())
        groups = []
        for group in self.section(app, 'cf-groups').values():
            applies = profile_id in group.get('quality_profiles', {}).get('include', {}).values()
            if applies and str(group.get('default', False)).lower() == 'true':
                groups.append(group['trash_id'])
                selected.update(item['trash_id'] for item in group['custom_formats']
                                if item.get('required') is True or item.get('default') is True)
        formats = self.section(app, 'cf')
        result = []
        score_set = profile.get('trash_score_set', 'default')
        for identifier in sorted(selected):
            if identifier not in formats:
                raise ValueError('Pinned TRaSH profile has an unresolved custom format')
            item = formats[identifier]
            scores = item.get('trash_scores', {})
            # Upstream unscored informational formats retain the API's neutral zero.
            score = scores.get(score_set, scores.get('default', 0))
            if type(score) is not int:
                raise ValueError('Pinned TRaSH custom format lacks an explicit score')
            result.append({'id': identifier, 'score': score, 'definition': copy.deepcopy(item)})
        return {'commit': COMMIT, 'profile': profile, 'groups': sorted(groups), 'formats': result}


def render_quality_profile(snapshot, schema, format_ids, languages=None):
    """Resolve actual runtime quality/group/language IDs; preserve full ordering."""
    profile = snapshot['profile']
    leaves = {}
    def walk(items):
        for item in items:
            if item.get('quality'):
                quality = item['quality']
                leaves[quality['name']] = quality
            else:
                walk(item.get('items', []))
    walk(schema['items'])
    used, ordered, cutoffs = set(), [], {}
    group_id = max([999] + [q['id'] for q in leaves.values()]) + 1
    for item in reversed(profile['items']):
        names = item.get('items', [item['name']])
        children = []
        for name in reversed(names):
            if name not in leaves or name in used:
                raise AppAPIError('TRaSH quality schema differs; no profile write attempted')
            used.add(name)
            children.append({'quality': copy.deepcopy(leaves[name]), 'items': [], 'allowed': item['allowed']})
        if 'items' in item:
            row = {'id': group_id, 'name': item['name'], 'items': children, 'allowed': item['allowed']}
            cutoffs[item['name']] = group_id
            group_id += 1
        else:
            row = children[0]
            cutoffs[item['name']] = row['quality']['id']
        ordered.append(row)
    if used != set(leaves) or profile['cutoff'] not in cutoffs:
        raise AppAPIError('TRaSH profile does not cover the complete runtime quality schema')
    result = {key: profile[key] for key in ('name', 'upgradeAllowed', 'minFormatScore', 'cutoffFormatScore', 'minUpgradeFormatScore')}
    result.update(items=ordered, cutoff=cutoffs[profile['cutoff']], formatItems=[
        {'format': format_ids[item['id']], 'score': item['score']} for item in snapshot['formats']])
    if 'language' in profile:
        matches = [item for item in languages or [] if item['name'] == profile['language']]
        if len(matches) != 1:
            raise AppAPIError('TRaSH language must resolve dynamically')
        result['language'] = {'id': matches[0]['id'], 'name': matches[0]['name']}
    return result


def format_signature(value):
    return {'name': value['name'], 'includeCustomFormatWhenRenaming': value['includeCustomFormatWhenRenaming'],
            'specifications': [{'name': spec['name'], 'implementation': spec['implementation'],
                'negate': spec['negate'], 'required': spec['required'],
                'fields': spec['fields'] if isinstance(spec['fields'], dict) else
                          {field['name']: field.get('value') for field in spec['fields']}}
                for spec in value['specifications']]}


def ensure_profile(client, app, profile_id):
    """Add a complete pinned profile, refuse conflicting operator definitions."""
    snapshot = Catalog().resolve(app, profile_id)
    schema = client.json('GET', 'qualityprofile/schema')
    languages = client.json('GET', 'language') if app == 'radarr' else None
    # Validate all runtime qualities before creating even one custom format.
    render_quality_profile(snapshot, schema, {cf['id']: i + 1 for i, cf in enumerate(snapshot['formats'])}, languages)
    implementations = {item['implementation']: item for item in client.json('GET', 'customformat/schema')}
    definitions = {}
    for item in snapshot['formats']:
        source = item['definition']
        specs = []
        for spec in source['specifications']:
            if spec['implementation'] not in implementations:
                raise AppAPIError('TRaSH custom-format implementation unavailable')
            available = implementations[spec['implementation']]
            fields = {field['name']: field for field in available['fields']}
            if set(spec['fields']) - set(fields):
                raise AppAPIError('TRaSH custom-format field schema differs')
            rendered = {key: copy.deepcopy(available[key]) for key in
                        ('implementation', 'implementationName') if key in available}
            rendered.update({key: spec[key] for key in ('name', 'negate', 'required')})
            rendered['fields'] = [dict(copy.deepcopy(field), value=spec['fields'].get(key, field.get('value', False if field.get('type') == 'checkbox' else None)))
                                  for key, field in fields.items()]
            specs.append(rendered)
        definitions[item['id']] = {'name': source['name'],
            'includeCustomFormatWhenRenaming': source['includeCustomFormatWhenRenaming'], 'specifications': specs}
    def existing_formats():
        rows = client.json('GET', 'customformat')
        if not isinstance(rows, list) or any(type(row.get('id')) is not int for row in rows):
            raise AppAPIError('Unsupported custom-format inventory')
        result = {}
        for row in rows:
            if row['name'] in result:
                raise AppAPIError('Duplicate custom-format names preserved')
            result[row['name']] = row
        return result
    existing = existing_formats()
    for definition in definitions.values():
        saved = existing.get(definition['name'])
        if saved is not None and format_signature(saved) != format_signature(definition):
            raise AppAPIError('Existing custom format differs from pinned guide; preserved')
    profiles = client.json('GET', 'qualityprofile')
    matching = [row for row in profiles if row['name'] == snapshot['profile']['name']]
    if len(matching) > 1:
        raise AppAPIError('Duplicate quality-profile names preserved')
    if matching and any(value['name'] not in existing for value in definitions.values()):
        raise AppAPIError('Existing profile lacks pinned custom formats; preserved')
    for definition in definitions.values():
        if definition['name'] not in existing:
            client.json('POST', 'customformat', definition)
    existing = existing_formats()
    ids = {}
    for identifier, definition in definitions.items():
        saved = existing.get(definition['name'])
        if saved is None or format_signature(saved) != format_signature(definition):
            raise AppAPIError('Custom-format write/readback differs')
        ids[identifier] = saved['id']
    desired = render_quality_profile(snapshot, schema, ids, languages)
    # Other installed CFs are explicitly neutral in this new guide-backed profile.
    selected = {row['format'] for row in desired['formatItems']}
    desired['formatItems'] += [{'format': row['id'], 'score': 0} for row in existing.values() if row['id'] not in selected]
    def signature(row):
        result = {key: row[key] for key in desired if key not in ('items', 'formatItems')}
        def qualities(items):
            return [{'name': item.get('name') or item.get('quality', {}).get('name'),
                     'allowed': item['allowed'], 'items': qualities(item.get('items', []))} for item in items]
        result['items'] = qualities(row['items'])
        result['formatItems'] = sorted([{'format': item['format'], 'score': item['score']}
                                        for item in row['formatItems'] if item['score'] != 0], key=lambda value: value['format'])
        return result
    if matching and signature(matching[0]) != signature(desired):
        raise AppAPIError('Existing quality profile differs from pinned guide; preserved')
    if not matching:
        client.json('POST', 'qualityprofile', desired)
    saved = [row for row in client.json('GET', 'qualityprofile') if row['name'] == desired['name']]
    if len(saved) != 1 or signature(saved[0]) != signature(desired):
        raise AppAPIError('Full quality-profile readback differs')
    return {'id': saved[0]['id'], 'name': desired['name'], 'commit': COMMIT,
            'custom_formats': len(snapshot['formats']), 'default_groups': len(snapshot['groups'])}
