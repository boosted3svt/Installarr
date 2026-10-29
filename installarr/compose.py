"""Generate isolated, guarded Compose bundles for version-tested app adapters.

JSON is accepted by Compose and avoids a third-party YAML dependency. Generation
does not create storage directories, collect credentials, or deploy containers.
"""
import json
import copy
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

from .atomic import publish_noreplace
from .execution import Execution
from .hostplan import storage_assertions
from .startup import container_mount_assertion, render_storage_guard

IMAGES = {
    "netbootxyz": {"version": "0.7.6-nbxyz27", "image": "ghcr.io/netbootxyz/netbootxyz@sha256:109e60b2d0090a6b34a5ac67e7ccc623991f7291ab25c37040fd2e554a14d7fe", "entrypoint": "/start.sh", "port": 3000},
    "ombi": {"version": "4.53.10-ls274", "image": "lscr.io/linuxserver/ombi@sha256:19d4f86713e7203d910b4aa431d7176e7a9a22f641beb1047da45aa989296509", "entrypoint": "/init", "port": 3579},
    "plex": {"version": "1.43.5.11079-b3b13e506", "image": "plexinc/pms-docker@sha256:6d778d41daae68f89115aa87a44ae14a96b23e71a2093da173b5a9aac4091336", "entrypoint": "/init", "port": 32400},
    "tautulli": {"version": "2.18.2-ls249", "image": "lscr.io/linuxserver/tautulli@sha256:c6a48416d16b26f254b000133d2d844c1905ee58ed0f44aad9bda66598d39988", "entrypoint": "/init", "port": 8181},
    "jackett": {"version": "0.24.2949-ls19", "image": "lscr.io/linuxserver/jackett@sha256:2c015f0978bb15d006937a0e6926d8a8c4ca955eed5f3372c6ec09a3a2de3ddd", "entrypoint": "/init", "port": 9117},
    "bazarr": {"version": "1.6.2-ls370", "image": "ghcr.io/linuxserver/bazarr@sha256:9a625883f054e722795affe5e3ca71057e6ed817ecdf99f4a99624346fcc509c", "entrypoint": "/init", "port": 6767},
    "sonarr": {"version": "4.0.20.3014-ls1", "image": "lscr.io/linuxserver/sonarr@sha256:48e36b608b461273b9dae857725cd0561a127f2c694b687318f6d0c5ce63e5c9", "entrypoint": "/init", "port": 8989},
    "radarr": {"version": "6.4.4.10685-ls324", "image": "lscr.io/linuxserver/radarr@sha256:084b3b2ab1d0ef930660727259546a241f2bdf67c9ed085d54bf1486a6887c9b", "entrypoint": "/init", "port": 7878},
    "sabnzbd": {"version": "5.1.3-ls278", "image": "lscr.io/linuxserver/sabnzbd@sha256:3ac1c9ea03bafa2588dd8acdcb809857bae305e71d2d90e11d689c78076a9c01", "entrypoint": "/init", "port": 8080},
}
DATA_TARGETS = {"media": "/data/media", "downloads": "/data/downloads", "incomplete": "/data/incomplete"}


def bundle_identity(config):
    payload = {"config": config, "images": {app: IMAGES[app] for app in config["apps"]}}
    if "sabnzbd" in config["apps"] and len(config["apps"]) > 1:
        payload["topology"] = "sab-loopback-v1"
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()



def data_targets(config):
    if 'data_root' not in config:
        return dict(DATA_TARGETS)
    root = Path(config['data_root'])
    return {purpose: '/data' + ('' if Path(config['storage'][purpose]) == root else
            '/' + str(Path(config['storage'][purpose]).relative_to(root))) for purpose in DATA_TARGETS}

def application_paths(config, app):
    if app not in IMAGES:
        raise ValueError("Application path adapter unavailable")
    targets = data_targets(config)
    paths = {"config_directory": str(Path(config["storage"]["configs"]) / app),
             "download_directory": targets["downloads"], "incomplete_directory": targets["incomplete"]}
    if app in ("sonarr", "radarr"):
        leaf = "TV" if app == "sonarr" else "Movies"
        paths["download_category"] = "tv" if app == "sonarr" else "movies"
        paths.update({"media_root": targets["media"] + "/" + leaf,
                      "host_media_root": str(Path(config["storage"]["media"]) / leaf)})
    if app == 'radarr' and 'media_secondary' in config['storage'] and not config.get('secondary_media_read_only', True):
        paths['additional_media_roots'] = ['/media-secondary']
    if app == 'netbootxyz':
        paths['assets_directory'] = config['storage'].get('netboot_assets', str(Path(paths['config_directory']) / 'assets'))
    return paths


def bind(source, target, readonly=False):
    return {"type": "bind", "source": str(source), "target": target, "read_only": readonly,
            "bind": {"create_host_path": False, "propagation": "rprivate"}}


def compose_literals(value):
    # Compose interpolates even JSON string values. Preserve literal host paths.
    if isinstance(value, str):
        return value.replace("$", "$$")
    if isinstance(value, list):
        return [compose_literals(item) for item in value]
    if isinstance(value, dict):
        return {key: compose_literals(item) for key, item in value.items()}
    return value


def render_bundle(config):
    # Local import avoids moving the existing public validation API in this step.
    from .cli import validate
    validate(config)
    if set(config["apps"]) - set(IMAGES):
        raise ValueError("Selected apps need additional version-tested Compose adapters")
    if config.get("storage_mounts", {}).get("configs", {}).get("kind") != "local":
        raise ValueError("Application configuration must be declared local storage")
    expected = storage_assertions(config)
    assertions = []
    for purpose, target in data_targets(config).items():
        if purpose not in expected or "sentinel" not in expected[purpose]:
            raise ValueError("Every data mount requires exact assertions and a sentinel")
        if 'data_root' in config:
            check = container_mount_assertion(config['data_root'], '/data', expected[purpose])
            check['probe'] = target
            assertions.append(check)
        else:
            assertions.append(container_mount_assertion(config["storage"][purpose], target, expected[purpose]))
    data_volumes = ([bind(config['data_root'], '/data')] if 'data_root' in config else
                    [bind(config['storage'][purpose], target) for purpose, target in DATA_TARGETS.items()])
    guards, services = {}, {}
    directory = Path(config["project_directory"])
    for app in config["apps"]:
        image = IMAGES[app]
        registry = r"ghcr\.io" if app == "bazarr" else r"lscr\.io"
        pattern = r"plexinc/pms-docker@sha256:[0-9a-f]{64}" if app == "plex" else registry + r"/linuxserver/" + app + r"@sha256:[0-9a-f]{64}"
        if app == "netbootxyz":
            pattern = r"ghcr\.io/netbootxyz/netbootxyz@sha256:[0-9a-f]{64}"
        if not re.fullmatch(pattern, image["image"]):
            raise ValueError("Application image must have a pinned digest")
        guards[app + ".guard.sh"] = ('#!/bin/sh\nset -eu\ndeny() { exit 78; }\nexec \"$@\"\n'
                                      if app in ('tautulli', 'ombi', 'netbootxyz') else render_storage_guard(assertions, require_writable=app != 'plex'))
        services[app] = {
            "image": image["image"], "pull_policy": "never", "network_mode": "none", "restart": "no",
            "entrypoint": ["/bin/sh", "/installarr-storage-guard", image["entrypoint"]],
            "environment": {"PUID": str(config["service_user"]["uid"]), "PGID": str(config["service_user"]["gid"]),
                            "TZ": config["timezone"], "UMASK": "002"},
            "labels": {"org.installarr.managed": "isolated-compose-v1", "org.installarr.image-version": image["version"],
                       "org.installarr.bundle": bundle_identity(config)},
            "volumes": [bind(application_paths(config, app)["config_directory"], "/config"),
                        *([] if app in ('tautulli', 'ombi', 'netbootxyz') else copy.deepcopy(data_volumes)),
                        bind(directory / (app + ".guard.sh"), "/installarr-storage-guard", True)],
        }
    if 'netbootxyz' in services:
        from .netboot import MENU_VERSION
        service = services['netbootxyz']
        service['environment'] = {'PUID': '911', 'PGID': '1001', 'TZ': config['timezone'],
            'WEB_APP_PORT': '3001', 'NGINX_PORT': '80', 'MENU_VERSION': MENU_VERSION, 'IPXE_SB_VERSION': 'v2.0.0'}
        service['volumes'].append(bind(application_paths(config, 'netbootxyz')['assets_directory'], '/assets'))
        if 'netboot_assets' in config['storage']:
            check = expected.get('netboot_assets')
            if not check or not check.get('sentinel'):
                raise ValueError('Explicit netboot assets require mount assertions and a sentinel')
            asset_assertion = container_mount_assertion(config['storage']['netboot_assets'], '/assets', check)
            guards['netbootxyz.guard.sh'] = render_storage_guard([asset_assertion])
    if 'media_secondary' in config['storage'] and not config.get('secondary_media_read_only', True):
        secondary = container_mount_assertion(config['storage']['media_secondary'], '/media-secondary', expected['media_secondary'])
        for app in ('radarr', 'bazarr'):
            if app in services:
                services[app]['volumes'].append(bind(config['storage']['media_secondary'], '/media-secondary'))
                guards[app + '.guard.sh'] = render_storage_guard([*assertions, secondary])
    if 'plex' in services:
        service = services['plex']
        if 'media_secondary' in config['storage']:
            secondary = container_mount_assertion(config['storage']['media_secondary'], '/media-secondary', expected['media_secondary'])
            guards['plex.guard.sh'] = render_storage_guard([*assertions, secondary], require_writable=False)
            service['volumes'].append(bind(config['storage']['media_secondary'], '/media-secondary', True))
        if config.get('hostname'):
            service['hostname'] = config['hostname']
        service['environment'] = {'PLEX_UID': str(config['service_user']['uid']),
            'PLEX_GID': str(config['service_user']['gid']), 'TZ': config['timezone'],
            'CHANGE_CONFIG_DIR_OWNERSHIP': 'false', 'ALLOWED_NETWORKS': config['plex_allowed_networks'],
            'ADVERTISE_IP': 'http://{}:32400/'.format(config['bind_address'])}
        for volume in service['volumes']:
            if volume['target'] == '/data' or volume['target'].startswith('/data/'):
                volume['read_only'] = True
        service['volumes'].append(bind(Path(application_paths(config, 'plex')['config_directory']) / 'transcode', '/transcode'))
        if config.get('plex_claim_file'):
            service['environment']['PLEX_CLAIM_FILE'] = '/run/installarr-plex-claim'
            service['volumes'].append(bind(config['plex_claim_file'], '/run/installarr-plex-claim', True))
    if set(services) >= {'plex', 'tautulli'}:
        logs = Path(application_paths(config, 'plex')['config_directory']) / 'Library/Application Support/Plex Media Server/Logs'
        services['tautulli']['volumes'].append(bind(logs, '/plexlogs', True))
    if "jackett" in services:
        services["jackett"]["environment"]["AUTO_UPDATE"] = "false"
    if "sabnzbd" in services:
        for app in ("sonarr", "radarr"):
            if app in services:
                services[app]["network_mode"] = "service:sabnzbd"
                services[app]["depends_on"] = {"sabnzbd": {"condition": "service_started", "restart": True}}
    return {"compose": compose_literals({"services": services}), "guards": guards,
            "images": {app: IMAGES[app] for app in config["apps"]}}


def private_artifact(path, data, mode):
    if os.path.lexists(str(path)):
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1
                    or stat.S_IMODE(info.st_mode) != mode or handle.read(len(data) + 1) != data):
                raise ValueError("Existing bundle artifact differs; preserved")
        return
    fd, temporary = tempfile.mkstemp(prefix=".artifact-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        publish_noreplace(temporary, path)
        directory_fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_bundle(config):
    bundle = render_bundle(config)
    with Execution(config["project_directory"], {"operation": "isolated-compose-v1", "config": config,
                                                "images": bundle["images"]}) as execution:
        def artifacts():
            for filename, content in bundle["guards"].items():
                private_artifact(execution.directory / filename, content.encode(), 0o555)
            for filename, content in (("compose.json", bundle["compose"]), ("images.json", bundle["images"])):
                private_artifact(execution.directory / filename, (json.dumps(content, indent=2) + "\n").encode(), 0o600)
        execution.reconcile("artifacts", artifacts)
    return {"status": "generated", "project_directory": config["project_directory"], "apps": config["apps"],
            "note": "Isolated Compose only: no ports or networks. Storage directories and local database mounts must already be prepared and validated."}
