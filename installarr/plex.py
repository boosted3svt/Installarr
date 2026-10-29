"""Official Plex image/runtime groundwork; claiming uses a separate secret file."""
import re
import xml.etree.ElementTree as ET

from .atomic import publish_noreplace
from .arr import AppAPIError, DockerHTTP
from .hosthttp import HostHTTP

VERSION = '1.43.5.11079-b3b13e506'
IMAGE = 'plexinc/pms-docker@sha256:6d778d41daae68f89115aa87a44ae14a96b23e71a2093da173b5a9aac4091336'
PREFERENCES = 'Library/Application Support/Plex Media Server/Preferences.xml'


class PlexAuthorizationRequired(AppAPIError):
    pass


class PlexHTTP(DockerHTTP):
    api_header = 'X-Plex-Token'
    # Initial agent discovery/library creation may exceed the ordinary app deadline.
    request_timeout = 60

    def __init__(self, socket, container, port=32400, api_key=''):
        if (socket != 'unix:///run/docker.sock' or not re.fullmatch(r'[0-9a-f]{64}', container)
                or port != 32400 or not isinstance(api_key, str)
                or (api_key and not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', api_key))):
            raise AppAPIError('Invalid Plex transport identity')
        self.socket, self.container, self.port, self.api_key = socket, container, port, api_key


class PlexHostHTTP(HostHTTP):
    api_header = 'X-Plex-Token'


class PlexClient:
    def __init__(self, transport):
        self.transport = transport

    def xml(self, path, authenticated=True):
        code, body = self.transport.request('GET', path, authenticated=authenticated)
        if code != 200:
            raise AppAPIError('Plex API rejected request (HTTP {})'.format(code))
        try:
            return ET.fromstring(body)
        except ET.ParseError:
            raise AppAPIError('Invalid Plex XML response') from None

    def status(self):
        identity = self.xml('/identity', authenticated=False)
        if identity.get('version') != VERSION or not identity.get('machineIdentifier'):
            raise AppAPIError('Untested Plex runtime identity/version')
        return {'version': identity.get('version'), 'machine_identifier': identity.get('machineIdentifier'),
                'claimed': identity.get('claimed') == '1'}

    def verify_authorization(self):
        status = self.status()
        if not status['claimed'] or not self.transport.api_key:
            raise PlexAuthorizationRequired('Plex server requires separate account authorization')
        sections = self.xml('/library/sections')
        return {'authorization': 'verified', 'libraries': len(sections.findall('Directory'))}


def read_claim_file(path):
    import os
    from pathlib import Path
    import stat
    path = Path(path).absolute()
    if path.resolve() != path:
        raise AppAPIError('Plex claim path must not contain symlinks')
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as source:
        info = os.fstat(source.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 256):
            raise AppAPIError('Plex claim file must be private and owned by executor')
        claim = source.read(257).strip()
    if not re.fullmatch(r'claim-[A-Za-z0-9_-]{10,128}', claim):
        raise AppAPIError('Invalid Plex claim token')
    return claim


def store_claim(directory, collect, replace=False, filename="plex-claim.txt"):
    import os
    from pathlib import Path
    import tempfile
    from .execution import Execution
    from .credentials import validate_secret_filename, credential_execution
    from .execution import private_directory
    validate_secret_filename(filename)
    operation = {'operation': 'plex-claim-v1'}
    if filename != 'plex-claim.txt':
        operation['filename'] = filename
    directory = private_directory(directory)
    path = directory / filename
    if os.path.lexists(str(path)):
        read_claim_file(path)
        if not replace:
            return {'status': 'retained', 'claim_file': str(path)}
    with credential_execution(directory, 'plex', filename, operation) as execution:
        if os.path.lexists(str(path)):
            read_claim_file(path)
            if not replace:
                return {'status': 'retained', 'claim_file': str(path)}
        claim = collect()
        if not isinstance(claim, str) or not re.fullmatch(r'claim-[A-Za-z0-9_-]{10,128}', claim):
            raise AppAPIError('Invalid Plex claim token')
        fd, temporary = tempfile.mkstemp(prefix='.plex-claim-', dir=str(directory))
        try:
            with os.fdopen(fd, 'w') as target:
                target.write(claim + '\n')
                target.flush()
                os.fsync(target.fileno())
            if replace:
                os.replace(temporary, str(path))
            else:
                publish_noreplace(temporary, path)
            directory_fd = os.open(str(directory), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {'status': 'stored', 'claim_file': str(path)}


# Primary-media directories from the supplied reference, preserving path case.
# Ambiguous collections use personal-media scanning until the operator edits type.
REFERENCE_LIBRARIES = [
    ('Movies', 'movie', ['Movies', 'Movies-2', 'jeremymovies', 'lenoramovies']),
    ('TV', 'show', ['TV', 'lenoratv', 'jeremytv']),
    ('sports', 'other', ['sports']), ('StandUp', 'movie', ['StandUp']),
    ('Music', 'artist', ['Music']),
]


def reference_libraries():
    return [{'name': name, 'type': kind, 'relative_paths': list(paths), 'language': 'en-US'}
            for name, kind, paths in REFERENCE_LIBRARIES]


REMOVED_LIBRARIES = {'disney', 'onlyheather', 'youtube', 'youtubevideos', 'tubesync', 'tubesyncvideos'}


def normalized_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


def validate_libraries(config):
    from pathlib import PurePosixPath
    libraries = config.get('plex_libraries', [])
    if not isinstance(libraries, list) or (libraries and 'plex' not in config['apps']):
        raise ValueError('Plex libraries require selected Plex')
    names, paths = set(), set()
    for item in libraries:
        fields = {'name', 'type', 'language'}
        if (not isinstance(item, dict) or set(item) not in
                (fields | {'relative_path'}, fields | {'relative_paths'})):
            raise ValueError('Plex library requires name, type, relative_paths and language')
        name = item['name']
        locations = item.get('relative_paths', [item.get('relative_path')])
        if (not isinstance(name, str) or not name.strip() or len(name) > 128 or any(ord(c) < 32 for c in name)
                or not isinstance(locations, list) or not locations):
            raise ValueError('Plex library requires a name and media-relative folders')
        normalized = normalized_name(name)
        if normalized in REMOVED_LIBRARIES:
            raise ValueError('This Plex library was explicitly removed from installer policy')
        if normalized == 'sports' and (name != 'sports' or locations != ['sports']):
            raise ValueError('Use library sports with matching folder sports')
        if normalized == 'standup' and (name != 'StandUp' or locations != ['StandUp']):
            raise ValueError('Use library StandUp with matching folder StandUp')
        for path in locations:
            if (not isinstance(path, str) or not path or PurePosixPath(path).is_absolute()
                    or any(part in ('', '.', '..') for part in path.split('/')) or any(ord(c) < 32 for c in path)):
                raise ValueError('Plex folders must stay inside configured media storage')
            if any(part.lower() in ('low-res-tv', 'low-res-movies') for part in path.split('/')):
                raise ValueError('Low-resolution Plex folders are excluded by operator policy')
            if path in paths:
                raise ValueError('Duplicate Plex library folder')
            paths.add(path)
        if item['type'] not in ('movie', 'show', 'artist', 'other') or item['language'] != 'en-US':
            raise ValueError('Unsupported Plex library type/language')
        if name in names:
            raise ValueError('Duplicate Plex library name')
        names.add(name)
    return libraries


def library_paths(config):
    from pathlib import Path
    from .compose import data_targets
    result = []
    for item in validate_libraries(config):
        relative = item.get('relative_paths', [item.get('relative_path')])
        host = [str(Path(config['storage']['media']) / path) for path in relative]
        container = [data_targets(config)['media'].rstrip('/') + '/' + path for path in relative]
        if 'media_secondary' in config['storage']:
            for index, path in enumerate(relative):
                if path == 'Movies-2':
                    host[index] = config['storage']['media_secondary']
                    container[index] = '/media-secondary'
        result.append(dict(item, host_paths=host, container_paths=container,
                           host_path=host[0], container_path=container[0]))
    return result


def read_agents_when_ready(client, seconds=90):
    """Cold agent discovery can outlast one bounded HTTP read; retry reads only."""
    import time
    deadline = time.monotonic() + seconds
    while True:
        try:
            return client.xml('/system/agents')
        except AppAPIError as error:
            if str(error) not in ('Application request failed', 'Plex API rejected request (HTTP 503)'):
                raise
            if time.monotonic() >= deadline:
                raise AppAPIError('Plex agent discovery is still starting; rerun setup to continue') from None
            time.sleep(min(0.5, max(0, deadline - time.monotonic())))


def write_library_request(transport, method, path, query, seconds=90):
    """Retry only Plex's explicit pre-handler startup refusal, with a deadline."""
    import time
    deadline = time.monotonic() + seconds
    while True:
        code, body = transport.request(method, path, query=query)
        if code != 400 or body.strip() != 'the server is still starting up. Please retry later':
            return code
        if time.monotonic() >= deadline:
            raise AppAPIError('Plex library setup is waiting for server startup; rerun setup to continue')
        time.sleep(min(0.5, max(0, deadline - time.monotonic())))


def configure_server(client, config):
    """Read back every selected library; never delete or repoint existing ones."""
    client.verify_authorization()
    if config.get('plex_server_name'):
        settings = client.xml('/:/prefs')
        matches = [row for row in settings if row.get('id') == 'FriendlyName' and row.get('type') == 'text']
        if len(matches) != 1:
            raise AppAPIError('Plex friendly-name schema differs')
        if matches[0].get('value') != config['plex_server_name']:
            code, _ = client.transport.request('PUT', '/:/prefs', query={'FriendlyName': config['plex_server_name']})
            if code not in (200, 201):
                raise AppAPIError('Plex server-name write rejected')
        if client.xml('/').get('friendlyName') != config['plex_server_name']:
            raise AppAPIError('Plex server-name readback differs')
    agents = {row.get('identifier'): row for row in read_agents_when_ready(client)}
    definitions = {'movie': ('tv.plex.agents.movie', 'Plex Movie'),
                   'show': ('tv.plex.agents.series', 'Plex TV Series'),
                   'artist': ('tv.plex.agents.music', 'Plex Music'),
                   'other': ('tv.plex.agents.none', 'Plex Video Files')}
    existing = list(client.xml('/library/sections').findall('Directory'))
    plans = []
    # Refuse every conflict before creating any libraries.
    for item in library_paths(config):
        kind = 'movie' if item['type'] == 'other' else item['type']
        agent, scanner = definitions[item['type']]
        if agent not in agents or item['language'] not in {row.get('code') for row in agents[agent].iter('Language')}:
            raise AppAPIError('Selected Plex library agent/language is unavailable')
        matches = [row for row in existing if row.get('title') == item['name']
                   or (item['name'] in ('sports', 'StandUp') and normalized_name(row.get('title', '')) == normalized_name(item['name']))]
        if len(matches) > 1:
            raise AppAPIError('Duplicate Plex library names preserved')
        if matches and (matches[0].get('type') != kind or matches[0].get('agent') != agent
                        or matches[0].get('scanner') != scanner or matches[0].get('language') != item['language']
                        or not {loc.get('path') for loc in matches[0].findall('Location')} <= set(item['container_paths'])):
            raise AppAPIError('Existing Plex library differs; preserved')
        plans.append((item, kind, agent, scanner, matches))
    evidence = []
    for item, kind, agent, scanner, matches in plans:
        query = [('name', item['name']), ('type', kind), ('agent', agent), ('scanner', scanner),
                 ('language', item['language'])] + [('location', path) for path in item['container_paths']]
        if not matches:
            code = write_library_request(client.transport, 'POST', '/library/sections', query)
            if code not in (200, 201):
                raise AppAPIError('Plex library creation rejected (HTTP {})'.format(code))
        elif (matches[0].get('title') != item['name'] or
              sorted(loc.get('path') for loc in matches[0].findall('Location')) != sorted(item['container_paths'])):
            key = matches[0].get('key', '')
            if not key.isdigit():
                raise AppAPIError('Invalid Plex library identifier')
            code = write_library_request(client.transport, 'PUT', '/library/sections/' + key, query)
            if code not in (200, 201):
                raise AppAPIError('Plex library folder addition rejected')
        saved = [row for row in client.xml('/library/sections').findall('Directory') if row.get('title') == item['name']]
        if (len(saved) != 1 or not saved[0].get('key') or saved[0].get('type') != kind
                or saved[0].get('agent') != agent or saved[0].get('scanner') != scanner
                or saved[0].get('language') != item['language']
                or sorted(loc.get('path') for loc in saved[0].findall('Location')) != sorted(item['container_paths'])):
            raise AppAPIError('Plex library write/readback differs')
        evidence.append({'id': saved[0].get('key'), 'name': item['name'], 'paths': item['container_paths'], 'type': item['type']})
    removed = []
    # Explicit operator policy authorizes removing these library sections. This
    # endpoint removes library metadata; no media-file deletion endpoint is used.
    for row in existing:
        if normalized_name(row.get('title', '')) not in REMOVED_LIBRARIES:
            continue
        key = row.get('key', '')
        if not key.isdigit():
            raise AppAPIError('Invalid removed-library identifier')
        code, _ = client.transport.request('DELETE', '/library/sections/' + key)
        if code not in (200, 204):
            raise AppAPIError('Removed-library policy reconciliation rejected')
        removed.append(row.get('title'))
    if removed and any(normalized_name(row.get('title', '')) in REMOVED_LIBRARIES
                       for row in client.xml('/library/sections')):
        raise AppAPIError('Removed Plex libraries remain after readback')
    return {'server_name': client.xml('/').get('friendlyName'), 'libraries': evidence, 'removed_libraries': removed}


def collect_libraries(ask):
    """Keep all reference groups by default; edit locations without splitting them."""
    libraries = reference_libraries()
    if ask('Include all reference Plex libraries? yes/no', 'yes').lower() != 'yes':
        libraries = [item for item in libraries if ask('Include Plex library ' + item['name'] + '? yes/no', 'yes').lower() == 'yes']
    if libraries and ask('Edit Plex library folder locations? yes/no', 'no').lower() == 'yes':
        for item in libraries:
            if item['name'] in ('sports', 'StandUp'):
                continue  # These exact matching names/paths are operator policy.
            value = ask('Folders for ' + item['name'] + ' (comma separated, relative to media root)',
                        ','.join(item['relative_paths']))
            item['relative_paths'] = [part.strip() for part in value.split(',')]
    validate_libraries({'apps': ['plex'], 'plex_libraries': libraries})
    return libraries
