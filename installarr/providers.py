"""Reference Newshosting, NZBGeek and Bazarr provider reconciliation."""
import copy

from .arr import AppAPIError
from .provider_secrets import validate_provider_secrets

SUBTITLES = ('opensubtitlescom',)


def validate_providers(config):
    values = config.get('providers', {})
    if not isinstance(values, dict) or set(values) - {'newshosting', 'nzbgeek', 'bazarr'}:
        raise ValueError('Unsupported provider selection')
    apps = set(config['apps'])
    for name, choice in values.items():
        if not isinstance(choice, dict):
            raise ValueError('Provider options must be nonsecret objects')
        if name == 'newshosting':
            if ('sabnzbd' not in apps or set(choice) != {'connections'}
                    or type(choice['connections']) is not int or not 1 <= choice['connections'] <= 100):
                raise ValueError('Newshosting requires SABnzbd and a connection limit from1 to100')
        elif name == 'nzbgeek':
            if choice or not apps & {'radarr', 'sonarr'}:
                raise ValueError('NZBGeek requires a selected Sonarr/Radarr app')
        elif ('bazarr' not in apps or set(choice) != {'enabled'} or not isinstance(choice['enabled'], list)
              or not choice['enabled'] or any(item not in SUBTITLES for item in choice['enabled'])
              or len(set(choice['enabled'])) != len(choice['enabled'])):
            raise ValueError('Choose supported Bazarr providers')
    path = config.get('provider_secrets_file')
    if path is not None:
        from .hostplan import absolute_path
        if not values or not absolute_path(path):
            raise ValueError('Provider credential path requires selected providers and an absolute private path')
    return values


def required_secrets(config):
    names = set(config.get('providers', {})) & {'newshosting', 'nzbgeek'}
    if 'opensubtitlescom' in config.get('providers', {}).get('bazarr', {}).get('enabled', []):
        names.add('opensubtitlescom')
    return names


def require_newshosting_test(value, saved=False):
    """Translate known provider refusal without exposing its arbitrary message."""
    import re
    if isinstance(value, dict) and value.get('result') is True:
        return
    message = value.get('message', '') if isinstance(value, dict) else ''
    if (isinstance(message, str) and 'connection' in message.lower()
            and re.search(r'\b502\b', message)
            and re.search(r'too many|\bmax(?:imum)?\b|limit', message, re.I)):
        raise AppAPIError('Newshosting connection limit reached. Pause other downloaders using this subscription or free account connections, then retry setup. Credentials were not changed.')
    raise AppAPIError('Saved Newshosting connection test failed' if saved else
                      'Newshosting TLS/authentication test failed; no provider setting saved')


def newshosting(client, credentials, connections=100, save=True):
    validate_provider_secrets({'newshosting': credentials})
    if type(connections) is not int or not 1 <= connections <= 100:
        raise AppAPIError('Invalid Newshosting connection limit')
    if int(client.misc().get('api_logging', -1)) != 0:
        raise AppAPIError('SAB API logging must be disabled before provider credential submission')
    name = 'Installarr Newshosting'
    desired = {'host': 'news.newshosting.com', 'port': 563, 'ssl': 1, 'ssl_verify': 3,
               'connections': connections, 'enable': 1, 'priority': 0, **credentials}
    configuration = client.call('get_config', section='servers').get('config')
    if not isinstance(configuration, dict):
        raise AppAPIError('Unsupported SAB server collection')
    rows = configuration.get('servers', [])
    if isinstance(rows, dict):
        rows = [dict(row, name=key) for key, row in rows.items()]
    if not isinstance(rows, list):
        raise AppAPIError('Unsupported SAB server schema')
    matches = [row for row in rows if row.get('name') == name]
    if len(matches) > 1 or any(row.get('host') == desired['host'] and row.get('name') != name for row in rows):
        raise AppAPIError('Existing Newshosting server conflicts; preserved')
    public = {key: value for key, value in desired.items() if key not in ('username', 'password')}
    def equal(row):
        return all(str(int(row.get(key))) == str(value) if key in ('ssl', 'enable') and isinstance(row.get(key), (bool, int))
                   else str(row.get(key)) == str(value) for key, value in public.items())
    if matches and not equal(matches[0]):
        raise AppAPIError('Existing Newshosting settings differ; preserved')
    result = client.call('config', name='test_server', **dict(desired, timeout=5)).get('value', {})
    require_newshosting_test(result)
    if save:
        client.call('set_config', section='servers', name=name, **desired)
        rows = client.call('get_config', section='servers').get('config', {}).get('servers', [])
        if isinstance(rows, dict):
            rows = [dict(row, name=key) for key, row in rows.items()]
        saved = [row for row in rows if row.get('name') == name]
        if len(saved) != 1 or not equal(saved[0]):
            raise AppAPIError('Newshosting server readback differs')
        check = dict(saved[0], server=name, timeout=5)
        check.pop('name', None)
        require_newshosting_test(client.call('config', name='test_server', **check).get('value', {}), saved=True)
    return {'provider': 'newshosting', **public, 'authentication': 'verified', 'saved': save,
            'download': 'not tested'}


def nzbgeek(client, app, credentials, save=True):
    validate_provider_secrets({'nzbgeek': credentials})
    if app not in ('radarr', 'sonarr'):
        raise AppAPIError('Unsupported indexer application')
    name = 'Installarr NZBGeek'
    schemas = client.json('GET', 'indexer/schema')
    candidates = [row for row in schemas if row.get('implementation') == 'Newznab']
    if not candidates:
        raise AppAPIError('Newznab schema unavailable')
    schema = candidates[0]
    desired = {'baseUrl': 'https://api.nzbgeek.info', 'apiPath': '/api', 'apiKey': credentials['api_key'],
               'categories': [2000] if app == 'radarr' else [5000]}
    rows = client.json('GET', 'indexer')
    matching = [row for row in rows if row.get('name') == name]
    if len(matching) > 1 or (matching and matching[0].get('implementation') != 'Newznab'):
        raise AppAPIError('Indexer name conflict; preserved')
    for row in rows:
        if row.get('name') != name and any(field.get('name') == 'baseUrl' and field.get('value') == desired['baseUrl'] for field in row.get('fields', [])):
            raise AppAPIError('Existing NZBGeek indexer preserved; no duplicate created')
    payload = copy.deepcopy(matching[0] if matching else schema)
    fields = {field['name']: field for field in payload.get('fields', [])}
    if set(desired) - set(fields):
        raise AppAPIError('Required Newznab fields unavailable')
    flags = {'enableRss': True, 'enableAutomaticSearch': True, 'enableInteractiveSearch': True}
    if matching and (any(fields[key].get('value') != value for key, value in desired.items() if key != 'apiKey')
                     or any(payload.get(key) != value for key, value in flags.items())):
        raise AppAPIError('Existing NZBGeek settings differ; preserved')
    payload.update(name=name, priority=25, **flags)
    for key, value in desired.items():
        fields[key]['value'] = value
    client.json('POST', 'indexer/test', payload)
    identity = matching[0].get('id') if matching else None
    if save:
        if matching:
            client.json('PUT', 'indexer/' + str(identity), payload)
        else:
            identity = client.json('POST', 'indexer', payload).get('id')
        if type(identity) is not int or identity <= 0:
            raise AppAPIError('Invalid saved indexer identity')
        actual = client.json('GET', 'indexer/' + str(identity))
        values = {field['name']: field.get('value') for field in actual.get('fields', [])}
        if (actual.get('name') != name or actual.get('implementation') != 'Newznab' or any(actual.get(key) != value for key, value in flags.items())
                or any(values.get(key) != value for key, value in desired.items() if key != 'apiKey')):
            raise AppAPIError('NZBGeek readback differs')
        client.json('POST', 'indexer/test', actual)
    return {'provider': 'nzbgeek', 'id': identity, 'url': desired['baseUrl'], 'categories': desired['categories'],
            'connection_test': 'verified', 'saved': save, 'download': 'not tested'}


def bazarr_providers(client, enabled, credentials):
    if not enabled or any(name not in SUBTITLES for name in enabled):
        raise AppAPIError('Unsupported Bazarr provider selection')
    current = client.settings()
    existing = current['general'].get('enabled_providers')
    if not isinstance(existing, list) or (existing and set(existing) != set(enabled)):
        raise AppAPIError('Existing Bazarr provider selection differs; preserved')
    desired = {'general': {'enabled_providers': list(enabled)}}
    if 'opensubtitlescom' in enabled:
        validate_provider_secrets({'opensubtitlescom': credentials})
        account = current.get('opensubtitlescom', {})
        if account.get('username') and account.get('username') != credentials['username']:
            raise AppAPIError('Existing OpenSubtitles account differs; preserved')
        desired['opensubtitlescom'] = dict(credentials)
    client.update(desired)
    return {'enabled': list(enabled), 'settings': 'verified', 'provider_authentication_and_search': 'not tested'}


def load_selected_secrets(config):
    names = required_secrets(config)
    if not names:
        return {}
    from .provider_secrets import read_provider_secrets
    path = config.get('provider_secrets_file')
    if not path:
        raise ValueError('Selected providers require a private provider_secrets_file; collect with init-provider-secrets')
    values = read_provider_secrets(path)
    if names - set(values):
        raise ValueError('Private provider credentials are missing a selected provider')
    return {name: values[name] for name in names}


def check_existing_providers(config, name, secrets_file, connections=100):
    """Connection tests only, using unchanged owned deployment configuration."""
    import re
    from .apply import app_client, wait_for
    from .provider_secrets import read_provider_secrets
    from .reference import reference_controller
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,25}', name):
        raise ValueError('Invalid reference deployment name')
    values = read_provider_secrets(secrets_file)
    controller = reference_controller(config, 'installarr-' + name)
    results = {}
    if 'newshosting' in values and 'sabnzbd' in config['apps']:
        sab = wait_for(lambda: app_client(config, controller, 'sabnzbd'))
        results['newshosting'] = newshosting(sab, values['newshosting'], connections, save=False)
    if 'nzbgeek' in values:
        for app in ('radarr', 'sonarr'):
            if app in config['apps']:
                backend = wait_for(lambda: app_client(config, controller, app))
                results['nzbgeek_' + app] = nzbgeek(backend, app, values['nzbgeek'], save=False)
    if 'opensubtitlescom' in values:
        results['subtitles'] = 'credential file validated; actual Bazarr provider authentication/search pending'
    return {'settings_saved': False, 'checks': results, 'downloads': 'not tested'}
