"""Protected netboot.xyz frontend using Nginx already included in its image."""
import hmac
import os
from pathlib import Path
import re
import subprocess

from .arr import AppAPIError, DockerHTTP
from .credentials import validate_credentials

IMAGE = 'ghcr.io/netbootxyz/netbootxyz@sha256:109e60b2d0090a6b34a5ac67e7ccc623991f7291ab25c37040fd2e554a14d7fe'
VERSION = '0.7.6-nbxyz27'
MENU_VERSION = '3.0.3'

ADMIN_SITE = '''server {
    listen 3000;
    auth_basic "Installarr";
    auth_basic_user_file /config/.installarr-admin.htpasswd;
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
'''


def hashed_password(password, salt=None):
    args = ['openssl', 'passwd', '-6', '-stdin']
    if salt is not None:
        if not re.fullmatch(r'[A-Za-z0-9./]{1,16}', salt):
            raise AppAPIError('Invalid netboot password salt')
        args += ['-salt', salt]
    # Secrets travel only over stdin. Never include subprocess diagnostics.
    try:
        result = subprocess.run(args, input=password + '\n', capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise AppAPIError('OpenSSL SHA512 password hashing unavailable') from None
    value = result.stdout.strip()
    if result.returncode or not re.fullmatch(r'\$6\$[A-Za-z0-9./]{1,16}\$[A-Za-z0-9./]{86}', value):
        raise AppAPIError('Invalid netboot password hash')
    return value


def seed_admin(directory, credentials):
    validate_credentials(credentials)
    if ':' in credentials['username']:
        raise AppAPIError('Netboot Basic-auth username cannot contain a colon')
    directory = Path(directory)
    if directory.resolve() != directory:
        raise AppAPIError('Netboot config path must not contain symlinks')
    site = directory / 'nginx/site-confs/installarr-admin'
    if site.parent.resolve() != site.parent:
        raise AppAPIError('Netboot frontend path must not contain symlinks')
    site.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    password = directory / '.installarr-admin.htpasswd'
    if os.path.lexists(str(password)):
        fd = os.open(str(password), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        import stat
        with os.fdopen(fd) as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077 or info.st_size > 65536:
                raise AppAPIError('Unsafe netboot authentication file preserved')
            row = source.read(65537).rstrip('\n')
        try:
            username, saved = row.split(':', 1)
            salt = saved.split('$')[2]
        except (ValueError, IndexError):
            raise AppAPIError('Invalid existing netboot authentication preserved') from None
        if username != credentials['username'] or not hmac.compare_digest(saved, hashed_password(credentials['password'], salt)):
            raise AppAPIError('Existing netboot authentication differs; preserved')
    else:
        from .compose import private_artifact
        private_artifact(password, (credentials['username'] + ':' + hashed_password(credentials['password']) + '\n').encode(), 0o600)
    if os.path.lexists(str(site)):
        fd = os.open(str(site), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        import stat
        with os.fdopen(fd) as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode) or source.read(65537) != ADMIN_SITE:
                raise AppAPIError('Existing netboot frontend configuration differs; preserved')
    else:
        from .compose import private_artifact
        private_artifact(site, ADMIN_SITE.encode(), 0o600)
    return {'authentication': 'seeded', 'backend': 'existing image Nginx', 'node_port': 3001, 'admin_port': 3000}


class NetbootHTTP(DockerHTTP):
    def __init__(self, socket, container, port=3000, api_key=''):
        if socket != 'unix:///run/docker.sock' or port not in (3000, 80) or not re.fullmatch(r'[0-9a-f]{64}', container):
            raise AppAPIError('Invalid netboot transport identity')
        self.socket, self.container, self.port, self.api_key = socket, container, port, api_key


class NetbootClient:
    def __init__(self, transport):
        self.transport = transport

    def verify_admin(self, credentials):
        validate_credentials(credentials)
        wrong = dict(credentials, password=('A' if credentials['password'][0] != 'A' else 'B') + credentials['password'][1:])
        result = {}
        for path, key, query in (('/', 'gui', None), ('/socket.io/', 'socket', {'EIO': '4', 'transport': 'polling'})):
            codes = [self.transport.request('GET', path, authenticated=False, basic=value, query=query)[0]
                     for value in (None, credentials, wrong)]
            if codes != [401, 200, 401]:
                raise AppAPIError('Netboot authenticated {} access/rejection failed'.format(key))
            result[key] = {'anonymous': codes[0], 'valid': codes[1], 'invalid': codes[2]}
        return result
