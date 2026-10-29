"""Storage choices and declarative host preparation; never executes changes."""
from pathlib import PurePosixPath


def absolute_path(value):
    return isinstance(value, str) and value.startswith("/") and value != "/" and not any(
        part in ("..",) for part in PurePosixPath(value).parts
    ) and not any(c.isspace() for c in value) and "\x00" not in value


def validate_mounts(config):
    mounts = config.get("storage_mounts", {})
    if not isinstance(mounts, dict) or set(mounts) - set(config["storage"]):
        raise ValueError("Mounts must reference storage purposes")
    targets = {}
    for purpose, mount in mounts.items():
        if not isinstance(mount, dict) or mount.get("kind") not in ("local", "existing", "nfs", "smb"):
            raise ValueError("Choose local, existing, nfs or smb storage")
        kind = mount["kind"]
        allowed = {"kind"} if kind == "local" else {"kind", "mountpoint", "source", "fstype", "sentinel"}
        if kind == "smb":
            allowed.add("credentials_file")
        if set(mount) - allowed:
            raise ValueError("Unknown mount fields; credentials must not be embedded")
        if kind == "local":
            continue
        target, source, fstype = (mount.get(key) for key in ("mountpoint", "source", "fstype"))
        if not absolute_path(target) or not isinstance(source, str) or not source or any(c.isspace() for c in source):
            raise ValueError("Invalid mountpoint or source")
        path = PurePosixPath(config["storage"][purpose])
        if path != PurePosixPath(target) and PurePosixPath(target) not in path.parents:
            raise ValueError("Storage directory must be inside its mountpoint")
        authority = source[2:].split('/', 1)[0] if source.startswith('//') else source.split(':/', 1)[0]
        if fstype in ('nfs', 'nfs4', 'cifs') and '@' in authority:
            raise ValueError('Storage source must not contain inline account credentials')
        if kind == 'smb' and ',' in mount.get('credentials_file', ''):
            raise ValueError('SMB credential path cannot contain a mount-option separator')
        if kind == "nfs" and (fstype not in ("nfs", "nfs4") or ":/" not in source):
            raise ValueError("NFS requires server:/export and nfs/nfs4 filesystem")
        if kind == "smb" and (fstype != "cifs" or not source.startswith("//") or len(source[2:].split("/")) != 2 or not absolute_path(mount.get("credentials_file"))):
            raise ValueError("SMB requires //server/share, cifs and a protected credentials file path")
        if not isinstance(fstype, str) or not fstype:
            raise ValueError("Expected filesystem type is required")
        identity = (source, fstype, kind, mount.get("credentials_file"),
                    purpose_identity(config, purpose) if fstype == "cifs" else None)
        if target in targets and targets[target] != identity:
            raise ValueError("Conflicting sources or persistence policies for one mountpoint")
        targets[target] = identity
    points = sorted(targets)
    for index, target in enumerate(points):
        if any(PurePosixPath(target) in PurePosixPath(other).parents for other in points[index + 1:]):
            raise ValueError("Nested managed mountpoints require a separate reviewed layout")


def storage_assertions(config):
    checks = dict(config.get("storage_checks", {}))
    for purpose, mount in config.get("storage_mounts", {}).items():
        if mount["kind"] == "local":
            continue
        derived = {key: mount[key] for key in ("mountpoint", "source", "fstype", "sentinel") if key in mount}
        if purpose in checks and checks[purpose] != derived:
            raise ValueError("Storage mount and check assertions disagree")
        checks[purpose] = derived
    return checks


def preparation_plan(config):
    from .compose import IMAGES
    packages, mounts, directories = set(), {}, []
    for purpose, path in config["storage"].items():
        mount = config.get("storage_mounts", {}).get(purpose)
        directories.append({"purpose": purpose, "path": path, "action": "verify existing directory and marker read-only" if purpose == "media_secondary" and config.get("secondary_media_read_only", True) else "inspect; create only after storage validation and apply approval"})
        if not mount or mount["kind"] == "local":
            continue
        if mount["fstype"] in ("nfs", "nfs4"):
            packages.add("nfs-common")
        if mount["fstype"] == "cifs":
            packages.add("cifs-utils")
        prior = mounts.get(mount["mountpoint"])
        readonly = purpose == 'media_secondary' and config.get('secondary_media_read_only', True) and (prior is None or prior.get('read_only', False))
        mounts[mount["mountpoint"]] = {**mount, "read_only": readonly,
            "action": "reuse without editing persistence" if mount["kind"] == "existing" else "inspect existing mount/fstab; propose persistent mount after conflict and access checks"}
        if mount["kind"] == "smb":
            mounts[mount["mountpoint"]]["write_identity"] = purpose_identity(config, purpose)
    return {
        "required_storage_packages": sorted(packages),
        "required_application_packages": ["openssl"] if "netbootxyz" in config.get("apps", []) else [],
        "mounts": list(mounts.values()), "directories": directories,
        "blockers": (["Storage type has not been selected for every purpose"] if set(config.get("storage_mounts", {})) != set(config["storage"]) else []),
        "apply_available": False,  # General connected deployment remains unavailable.
        "reference_apply_available": bool(config.get("data_root")) and bool(config.get("apps", [])) and not (set(config.get("apps", [])) - set(IMAGES)),
        "isolated_apply_available": bool(config.get("apps", [])) and not (set(config.get("apps", [])) - {"sonarr", "radarr", "sabnzbd"}),
        "application_integrations": integration_plan(config),
        "requirements_before_apply": [
            "Supported Ubuntu, account collisions and Docker workload inspection",
            "Existing mount and persistence reconciliation; backup before approved edits",
            "NAS service-UID access and nonempty mountpoint checks",
            "Systemd and Docker restart protection for unavailable storage",
        ],
    }


def collect_storage(ask, purposes):
    paths, mounts = {}, {}
    for purpose in purposes:
        kind = ask("{} storage type: local/existing/nfs/smb".format(purpose), "local").lower()
        path = ask("Host directory for {}".format(purpose), "/srv/media-stack/{}".format(purpose))
        paths[purpose] = path
        mount = {"kind": kind}
        if kind in ("existing", "nfs", "smb"):
            mount["mountpoint"] = ask("Mountpoint containing this directory", path)
            mount["source"] = ask("Exact source (server:/export, //server/share or local device)", "")
            mount["fstype"] = ask("Filesystem type", "cifs" if kind == "smb" else "nfs" if kind == "nfs" else "ext4")
            if kind == "smb":
                mount["credentials_file"] = ask("Root-protected SMB credentials file path (never enter credentials here)", "/etc/installarr/smb.credentials")
            sentinel = ask("Existing sentinel file relative to this directory (blank skips)", "")
            if sentinel:
                mount["sentinel"] = sentinel
        mounts[purpose] = mount
    return paths, mounts


def collect_shared_storage(ask):
    """Collect one explicit data bind and its assertions without touching storage."""
    root = ask('Shared data root (contains media and download directories)', '/media/Media')
    kind = ask('Data storage type: local/existing/nfs/smb', 'existing').lower()
    point = ask('Exact data mountpoint', '/' if kind == 'local' else root)
    source = ask('Exact mounted source (device, server:/export or //server/share)', '')
    fstype = ask('Data filesystem type', 'ext4' if kind == 'local' else 'cifs' if kind == 'smb' else 'nfs')
    sentinel = ask('Health marker basename (created only after mount verification)', 'installarr-health')
    check = {'mountpoint': point, 'source': source, 'fstype': fstype, 'sentinel': sentinel}
    mount = {'kind': kind} if kind == 'local' else dict(check, kind=kind)
    if kind == 'smb':
        mount['credentials_file'] = ask('Root-protected SMB credentials file path', '/etc/installarr/smb.credentials')
    defaults = {'media': root, 'downloads': root + '/downloads', 'incomplete': root + '/incomplete-downloads',
                'configs': '/var/lib/installarr/apps', 'backups': '/var/lib/installarr/backups'}
    paths = {purpose: ask('Host directory for ' + purpose, default) for purpose, default in defaults.items()}
    mounts = {purpose: dict(mount) for purpose in ('media', 'downloads', 'incomplete')}
    mounts.update({purpose: {'kind': 'local'} for purpose in ('configs', 'backups')})
    checks = {purpose: dict(check) for purpose in ('media', 'downloads', 'incomplete')}
    return root, paths, mounts, checks


def integration_plan(config):
    """Discover selected connections and missing inputs without selecting more apps."""
    apps = set(config.get('apps', []))
    links, inputs = [], []
    providers = config.get('providers', {})
    for app in ('radarr', 'sonarr'):
        if app in apps:
            if 'sabnzbd' in apps:
                links.append({'from': app, 'to': 'sabnzbd', 'purpose': 'Usenet downloads'})
            else:
                inputs.append(app + ': no selected downloader; download client setup remains external')
            if 'nzbgeek' not in providers:
                inputs.append(app + ': indexer selection and provider credentials remain external')
    if 'sabnzbd' in apps and 'newshosting' not in providers:
        inputs.append('sabnzbd: Usenet provider host and credentials required')
    if 'jackett' in apps:
        inputs.append('jackett: indexers required; Jackett is not a torrent downloader')
    if 'bazarr' in apps:
        targets = apps & {'radarr', 'sonarr'}
        links.extend({'from': 'bazarr', 'to': app, 'purpose': 'subtitles'} for app in sorted(targets))
        if not targets:
            inputs.append('bazarr: no selected Sonarr/Radarr integration')
        if not providers.get('bazarr', {}).get('enabled'):
            inputs.append('bazarr: subtitle providers required')
        if not config.get('bazarr_language_profile'):
            inputs.append('bazarr: subtitle language preference required')
    if 'ombi' in apps:
        targets = apps & {'radarr', 'sonarr', 'plex'}
        links.extend({'from': 'ombi', 'to': app, 'purpose': 'availability' if app == 'plex' else 'requests'}
                     for app in sorted(targets))
        if not targets & {'radarr', 'sonarr'}:
            inputs.append('ombi: no selected request backend')
        for app in sorted(targets & {'radarr', 'sonarr'}):
            if app not in config.get('quality_profiles', {}):
                inputs.append('ombi: preferred ' + app + ' quality profile selection required')
    if 'tautulli' in apps:
        if 'plex' in apps:
            links.append({'from': 'tautulli', 'to': 'plex', 'purpose': 'monitoring'})
        else:
            inputs.append('tautulli: external Plex authorization/connection remains unconfigured')
    if 'plex' in apps:
        inputs.append('plex: separate account authorization required on a fresh server')
    from .providers import required_secrets
    if required_secrets(config) and not config.get('provider_secrets_file'):
        inputs.append('providers: private credential file required; collect with init-provider-secrets')
    return {'selected_links': links, 'operator_inputs': inputs,
            'automatic_app_additions': [], 'torrent_downloader': 'not provided'}


def purpose_identity(config, purpose):
    return {'uid': 911, 'gid': 1001} if purpose == 'netboot_assets' else {
        key: config.get('service_user', {}).get(key) for key in ('uid', 'gid')}


def collect_asset_storage(ask):
    path = ask('Host netboot asset directory', '/var/lib/installarr/netboot-assets')
    kind = ask('Netboot asset storage type: local/existing/nfs/smb', 'local').lower()
    point = ask('Exact netboot asset mountpoint', '/' if kind == 'local' else path)
    source = ask('Exact asset mounted source (device, server:/export or //server/share)', '')
    fstype = ask('Asset filesystem type', 'ext4' if kind == 'local' else 'cifs' if kind == 'smb' else 'nfs')
    marker = ask('Asset health marker basename', 'installarr-health')
    check = {'mountpoint': point, 'source': source, 'fstype': fstype, 'sentinel': marker}
    mount = {'kind': kind} if kind == 'local' else dict(check, kind=kind)
    if kind == 'smb':
        mount['credentials_file'] = ask('Root-protected SMB credential file path', '/etc/installarr/netboot-smb.credentials')
    return path, mount, check


def collect_secondary_storage(ask):
    path = ask('Existing secondary Movies-2 directory (read-only app access)', '/srv/secondary/Movies')
    kind = ask('Secondary source storage type: local/existing/nfs/smb', 'existing').lower()
    point = ask('Exact secondary source mountpoint', '/')
    source = ask('Exact secondary mounted source (device, server:/export or //server/share)', '')
    fstype = ask('Secondary filesystem type', 'ext4' if kind == 'local' else 'cifs' if kind == 'smb' else 'nfs')
    marker = ask('Existing readable secondary health marker basename (not created by installer)', 'installarr-health')
    check = {'mountpoint': point, 'source': source, 'fstype': fstype, 'sentinel': marker}
    mount = {'kind': kind} if kind == 'local' else dict(check, kind=kind)
    if kind == 'smb':
        mount['credentials_file'] = ask('Root-protected SMB credential file path', '/etc/installarr/secondary-smb.credentials')
    return path, mount, check
