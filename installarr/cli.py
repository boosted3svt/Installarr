"""Headless discovery, planning, private credentials and scoped host preparation."""
import argparse
import grp
import getpass
import ipaddress
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import subprocess
import sys
from .storage import check_storage, mount_inventory, validate_checks
from .hostplan import collect_shared_storage, collect_storage, preparation_plan, storage_assertions, validate_mounts
from .accounts import HostPrerequisiteError, prepare_accounts, supported_ubuntu
from .credentials import initialize_credentials, read_private_credentials
from .writecheck import check_service_writes
from .dockerhost import prepare_docker, prepare_test_daemon
from .compose import write_bundle
from .lifecycle import install_service, service_status
from .prerequisites import prepare_prerequisites
from .directories import prepare_directories
from .plex import PlexAuthorizationRequired
from .arr import AppAPIError

APPS = ("sabnzbd", "sonarr", "radarr", "bazarr", "jackett", "plex", "ombi", "tautulli", "netbootxyz")
PURPOSES = ("media", "downloads", "incomplete", "configs", "backups")


def validate_timezone(name):
    """Validate against Ubuntu's system tzdata without requiring Python 3.9."""
    if not isinstance(name, str) or not name or name.startswith("/") or any(
        part in ("", ".", "..") for part in name.split("/")
    ):
        raise ValueError("Invalid timezone name")
    try:
        with (Path("/usr/share/zoneinfo") / name).open("rb") as handle:
            if handle.read(4) != b"TZif":
                raise ValueError("Not a timezone data file")
    except OSError:
        raise ValueError("Unknown timezone or missing system tzdata") from None


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
        return {"available": True, "exit_code": result.returncode, "output": result.stdout.strip()}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "exit_code": None, "output": ""}


def preflight():
    release = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                release[key] = value.strip('"')
    except OSError:
        pass
    supported = supported_ubuntu(release)
    return {
        "os": release.get("PRETTY_NAME", platform.system()),
        "supported_target": supported,
        "target": "Ubuntu 20.04 or newer (full host provisioning not yet implemented)",
        "architecture": platform.machine(), "hostname": platform.node(),
        "running_as_root": os.geteuid() == 0,
        "systemd_running": Path("/run/systemd/system").is_dir(),
        "workspace_free_bytes": shutil.disk_usage(Path.cwd()).free,
        "docker": command(["docker", "version", "--format", "{{.Server.Version}}"]),
        "compose": command(["docker", "compose", "version", "--short"]),
        "mounts": mount_inventory(command),
        "note": "Read-only inventory; not a complete readiness or permission check.",
    }


def validate(config):
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("Expected a version 1 configuration object")
    allowed = {"schema_version", "apps", "timezone", "bind_address", "plex_allowed_networks", "service_user", "storage", "project_directory", "storage_checks", "storage_mounts", "data_root", "quality_profiles", "plex_claim_file", "plex_libraries", "plex_server_name", "hostname", "ombi_family_presets", "ombi_family_preferences_file", "providers", "provider_secrets_file", "bazarr_language_profile", "secondary_media_read_only", "folder_map"}
    if set(config) - allowed:
        raise ValueError("Unknown configuration fields; do not store credentials in this file")
    apps = config.get("apps")
    if not isinstance(apps, list) or not apps or any(a not in APPS for a in apps) or len(set(apps)) != len(apps):
        raise ValueError("Choose a nonempty, unique list of supported apps")
    from .profiles import validate_selections
    validate_selections(config)
    from .ombi_family import validate_family_config
    validate_family_config(config)
    from .providers import validate_providers
    validate_providers(config)
    if 'bazarr_language_profile' in config and ('bazarr' not in apps or config['bazarr_language_profile'] != 'english-standard'):
        raise ValueError('Supported subtitle default is English standard with selected Bazarr')
    try:
        ipaddress.IPv4Address(config["bind_address"])
        ipaddress.IPv4Network(config["plex_allowed_networks"], strict=False)
        validate_timezone(config["timezone"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("Valid IPv4 binding, Plex CIDR and timezone are required") from None
    if 'plex_claim_file' in config:
        value = config['plex_claim_file']
        if ('plex' not in apps or not isinstance(value, str) or not value.startswith('/')
                or value == '/' or '..' in Path(value).parts or any(ord(c) < 32 for c in value)):
            raise ValueError('Plex claim file requires an absolute private path and selected Plex')
    from .plex import validate_libraries
    if 'folder_map' not in config:
        validate_libraries(config)
    if 'hostname' in config and (not isinstance(config['hostname'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', config['hostname'])):
        raise ValueError('Invalid server hostname')
    if 'plex_server_name' in config:
        value = config['plex_server_name']
        if 'plex' not in apps or not isinstance(value, str) or not value.strip() or len(value) > 128 or any(ord(c) < 32 for c in value):
            raise ValueError('Invalid Plex server name')
    identity = config.get("service_user", {})
    if not isinstance(identity, dict) or set(identity) != {"name", "uid", "gid"} or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", str(identity.get("name", ""))):
        raise ValueError("Service user requires name, uid and gid")
    for field in ("uid", "gid"):
        value = identity[field]
        if type(value) is not int or not 1 <= value <= 2147483647:
            raise ValueError("Service UID/GID must be positive non-root integers")
    storage = config.get("storage", {})
    if (not isinstance(storage, dict) or not set(PURPOSES) <= set(storage)
            or set(storage) - (set(PURPOSES) | {'netboot_assets', 'media_secondary'})
            or ('netboot_assets' in storage and 'netbootxyz' not in apps)
            or ('media_secondary' in storage and 'plex' not in apps and (config.get('secondary_media_read_only', True) or not set(apps) & {'radarr', 'bazarr'}))):
        raise ValueError("Storage must specify media, downloads, incomplete, configs and backups")
    for value in [config.get("project_directory"), *storage.values()]:
        if not isinstance(value, str) or not value.startswith("/") or value == "/" or ".." in Path(value).parts or "\n" in value:
            raise ValueError("Directories must be absolute, non-root paths without parent traversal")
    if len(set(storage.values())) != len(storage):
        raise ValueError("Use distinct directories for each storage purpose")
    validate_checks(config.get("storage_checks", {}), storage)
    validate_mounts(config)
    validate_checks(storage_assertions(config), storage)
    if 'secondary_media_read_only' in config and (type(config['secondary_media_read_only']) is not bool or 'media_secondary' not in storage):
        raise ValueError('Secondary movie access choice requires a separate movie source')
    if 'media_secondary' in storage:
        check = storage_assertions(config).get('media_secondary')
        if not check or not check.get('sentinel') or '/' in check['sentinel']:
            raise ValueError('Secondary media requires exact mount assertions and an existing basename health marker')
        secondary = Path(storage['media_secondary'])
        if any(secondary == Path(path) or secondary in Path(path).parents or Path(path) in secondary.parents
               for purpose, path in storage.items() if purpose != 'media_secondary'):
            raise ValueError('Secondary media must not overlap other storage purposes')
    from .layout import validate_layout
    validate_layout(config)
    if 'folder_map' in config:
        validate_libraries(config)
    if 'data_root' in config and 'folder_map' not in config:
        root = Path(config['data_root']) if isinstance(config['data_root'], str) else None
        if root is None or not root.is_absolute() or str(root) == '/' or '..' in root.parts or any(ord(c) < 32 for c in str(root)):
            raise ValueError('Shared data root must be an absolute non-root directory')
        for purpose in ('media', 'downloads', 'incomplete'):
            path = Path(storage[purpose])
            if path != root and root not in path.parents:
                raise ValueError('All data purposes must be inside the shared data root')
        for purpose in ('configs', 'backups'):
            path = Path(storage[purpose])
            if path == root or root in path.parents:
                raise ValueError('Private configs/backups must stay outside the shared data bind')
        checks = storage_assertions(config)
        identities = []
        for purpose in ('media', 'downloads', 'incomplete'):
            check = checks.get(purpose)
            if not check or not check.get('sentinel'):
                raise ValueError('Shared data purposes require exact mount assertions and health markers')
            point = Path(check['mountpoint'])
            if root != point and point not in root.parents:
                raise ValueError('Shared data root must stay within the asserted data mount')
            identities.append(tuple(check[key] for key in ('mountpoint', 'source', 'fstype')))
        if len(set(identities)) != 1:
            raise ValueError('Shared data bind requires one common asserted filesystem')
    return config


def identity_conflicts(name, uid, gid):
    conflicts = []
    for lookup, key, label, expected in (
        (pwd.getpwnam, name, "named user's UID", uid),
        (pwd.getpwuid, uid, "UID owner's name", name),
        (grp.getgrnam, name, "named group's GID", gid),
        (grp.getgrgid, gid, "GID owner's name", name),
    ):
        try:
            record = lookup(key)
        except KeyError:
            continue
        actual = record.pw_uid if label == "named user's UID" else record.gr_gid if label == "named group's GID" else record[0]
        if actual != expected:
            conflicts.append(f"{name}: {label} is {actual}, expected {expected}")
    try:
        if pwd.getpwnam(name).pw_gid != gid:
            conflicts.append(f"{name}: existing primary group differs from requested GID {gid}")
    except KeyError:
        pass
    return conflicts


def plan(config):
    from .compose import data_targets
    from .plex import library_paths
    from .ombi_family import family_paths
    validate(config)
    user = config["service_user"]
    conflicts = identity_conflicts(user["name"], user["uid"], user["gid"])
    if "netbootxyz" in config["apps"]:
        conflicts += identity_conflicts("nbxyz", 911, 1001)
        if user != {"name": "nbxyz", "uid": 911, "gid": 1001} and (user["name"] == "nbxyz" or user["uid"] == 911 or user["gid"] == 1001):
            conflicts.append("Media identity overlaps reserved netbootxyz UID 911 / GID 1001")
    return {
        "mode": "preview only; no system changes",
        "apps": config["apps"], "service_user": user,
        "netbootxyz_identity": {"name": "nbxyz", "uid": 911, "gid": 1001} if "netbootxyz" in config["apps"] else None,
        "host_storage": config["storage"],
        "netboot_assets": {"host_path": config["storage"].get("netboot_assets", str(Path(config["storage"]["configs"]) / "netbootxyz/assets")), "container_path": "/assets", "uid": 911, "gid": 1001} if "netbootxyz" in config["apps"] else None,
        "host_preparation": preparation_plan(config),
        "proposed_container_paths": data_targets(config),
        "plex_allowed_networks": config["plex_allowed_networks"],
        "quality_profiles": config.get("quality_profiles", {}),
        "providers": config.get("providers", {}),
        "bazarr_language_profile": config.get("bazarr_language_profile"),
        "plex_libraries": library_paths(config),
        "ombi_family_paths": family_paths(config) if config.get("ombi_family_presets") else {},
        "conflicts": conflicts,
        "pending_checks": [
            "Official image permission mechanisms and pinned versions",
            "Storage source/protocol, persistent mounts, service-UID access and mount-loss protection",
            "Host binding ownership and port conflicts",
            "Application-specific roots, credentials and integration configuration",
        ],
        "scope": "Fresh provisioning; DHCP/PXE reachability is operator-managed. No migration.",
    }


def save_config(path, config):
    validate(config)
    # Refuse replacement, including symlinks; secrets are never collected here.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")



def detected_address():
    routes = command(['ip', '-j', '-4', 'route', 'show', 'default'])
    addresses = command(['ip', '-j', '-4', 'addr', 'show', 'scope', 'global'])
    try:
        route_rows = json.loads(routes['output']) if routes['exit_code'] == 0 else []
        preferred = route_rows[0].get('dev') if route_rows else None
        rows = json.loads(addresses['output']) if addresses['exit_code'] == 0 else []
        rows.sort(key=lambda row: row.get('ifname') != preferred)
        for row in rows:
            if row.get('ifname', '').startswith(('docker', 'br-', 'veth', 'lo')):
                continue
            for address in row.get('addr_info', []):
                value = ipaddress.IPv4Address(address['local'])
                if not value.is_loopback and not value.is_link_local:
                    return str(value)
    except (ValueError, KeyError, TypeError):
        pass
    return '127.0.0.1'

def configure(path):
    if not sys.stdin.isatty():
        raise ValueError("configure requires an interactive terminal; use a JSON file with plan for unattended review")
    def ask(label, default):
        return input(f"{label} [{default}]: ").strip() or default
    print("Collecting nonsecret choices only. No packages, accounts or mounts will be changed.")
    print("Available apps: " + ", ".join(APPS))
    config = {
        "schema_version": 1,
        "apps": ask("Apps (comma separated)", "sabnzbd,sonarr,radarr,bazarr,plex,ombi").replace(" ", "").split(","),
        "hostname": ask("Server hostname", platform.node()),
        "timezone": ask("Timezone", "America/Chicago"),
        "bind_address": ask("Server LAN IPv4 address", detected_address()),
        "plex_allowed_networks": ask("Plex allowed networks CIDR", "192.168.0.0/23"),
        "project_directory": ask("Compose project directory", "/opt/media-stack"),
        "service_user": {
            "name": ask("Media service account", "media"),
            "uid": int(ask("Media UID (availability checked by plan)", "2000")),
            "gid": int(ask("Media GID (availability checked by plan)", "2000")),
        },
    }
    if ask("Use one shared data root? yes/no", "yes").lower() == "yes":
        config['data_root'], config['storage'], config['storage_mounts'], config['storage_checks'] = collect_shared_storage(ask)
    else:
        config["storage"], config["storage_mounts"] = collect_storage(ask, PURPOSES)
    if 'netbootxyz' in config['apps'] and ask('Use default local netboot asset directory? yes/no', 'yes').lower() != 'yes':
        from .hostplan import collect_asset_storage
        asset_path, asset_mount, asset_check = collect_asset_storage(ask)
        config['storage']['netboot_assets'] = asset_path
        config['storage_mounts']['netboot_assets'] = asset_mount
        config.setdefault('storage_checks', {})['netboot_assets'] = asset_check
    if 'plex' in config['apps']:
        from .plex import collect_libraries
        config['plex_server_name'] = ask('Plex server name', config['hostname'])
        config['plex_libraries'] = collect_libraries(ask)
        if ask('Use a separate existing source for the Movies-2 folder? yes/no', 'no').lower() == 'yes':
            from .hostplan import collect_secondary_storage
            secondary_path, secondary_mount, secondary_check = collect_secondary_storage(ask)
            config['storage']['media_secondary'] = secondary_path
            config['storage_mounts']['media_secondary'] = secondary_mount
            config.setdefault('storage_checks', {})['media_secondary'] = secondary_check
        config['plex_claim_file'] = ask('Private Plex claim file path (collect with init-plex-claim)', '/var/lib/installarr-plex-claim/plex-claim.txt')
    from .profiles import recommended_profiles
    if set(config['apps']) & {'radarr', 'sonarr'}:
        print('Profiles: movies Remux + WEB 1080p, optional Remux + WEB 2160p; TV WEB-1080p.')
        if ask('Install these full pinned TRaSH profiles? yes/no', 'yes').lower() == 'yes':
            config['quality_profiles'] = recommended_profiles(config['apps'])
    if {'ombi', 'plex'} <= set(config['apps']) and set(config['apps']) & {'radarr', 'sonarr'}:
        config['ombi_family_presets'] = ask('Enable Plex family presets for lenora8, rebel739 and beanie08? yes/no', 'no').lower() == 'yes'
    providers = {}
    if 'sabnzbd' in config['apps'] and ask('Configure Newshosting? yes/no', 'no').lower() == 'yes':
        providers['newshosting'] = {'connections': int(ask('Newshosting maximum connections', '100'))}
    if set(config['apps']) & {'radarr', 'sonarr'} and ask('Configure NZBGeek? yes/no', 'no').lower() == 'yes':
        providers['nzbgeek'] = {}
    if 'bazarr' in config['apps'] and ask('Configure OpenSubtitles.com for subtitles? yes/no', 'no').lower() == 'yes':
        from .providers import SUBTITLES
        providers['bazarr'] = {'enabled': list(SUBTITLES)}
    if providers:
        config['providers'] = providers
        config['provider_secrets_file'] = ask('Private provider credential file (collect with init-provider-secrets)', '/var/lib/installarr-provider-secrets/providers.json')
    if 'bazarr' in config['apps'] and ask('Use standard English subtitles for new movies and TV shows? yes/no', 'yes').lower() == 'yes':
        config['bazarr_language_profile'] = 'english-standard'
    preview = plan(config)
    print(json.dumps(preview, indent=2))
    if ask("Save these choices? yes/no", "no").lower() == "yes":
        save_config(path, config)
        print(f"Saved nonsecret configuration to {path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("family-accounts", help="Save optional family Discord account numbers privately")
    setup = sub.add_parser("setup", help="Guided setup and resume (default when no command is supplied)")
    setup.add_argument('--continue-as-admin', action='store_true', help=argparse.SUPPRESS)
    sub.add_parser("preflight", help="Read-only host inventory")
    menu = sub.add_parser('menu', help='Interactive terminal navigation over configuration and deployment commands')
    menu.add_argument('--config', type=Path, default=Path('installarr.json'))
    menu.add_argument('--name', default='media-stack')
    menu.add_argument('--state-directory', type=Path)
    docker = sub.add_parser("prepare-docker", help="Stage signed Docker packages; keep standard services masked")
    docker.add_argument("--state-directory", type=Path, default=Path("/var/lib/installarr-docker-install"))
    sub.add_parser("prepare-test-daemon", help="Start isolated Docker test daemon without host networking changes")
    deploy = sub.add_parser("apply", help="Resume a supervised isolated deployment of tested apps")
    deploy.add_argument("--config", type=Path, required=True)
    deploy.add_argument("--name", required=True)
    deploy.add_argument("--state-directory", type=Path)
    deploy.add_argument("--secrets-directory", type=Path)
    deploy.add_argument("--credentials-file", type=Path)
    deploy.add_argument("--reference", action="store_true", help="Use the prepared standard engine and reference web bridge/ports")
    deploy.add_argument('--prepare-only', action='store_true', help='Reference mode: prepare host/images before a short-lived Plex claim; start no applications')
    service = sub.add_parser("install-service", help="Install a disabled storage-supervised systemd service")
    service.add_argument("--config", type=Path, required=True)
    service.add_argument("--name", required=True)
    status = sub.add_parser("service-status", help="Read private managed-service state")
    status.add_argument("--name", required=True)
    for runtime_action in ('audit-runtime', 'refresh-runtime'):
        runtime_parser = sub.add_parser(runtime_action, help='Inspect or explicitly refresh stopped reference supervisors')
        runtime_parser.add_argument('--name', required=True)
        if runtime_action == 'refresh-runtime':
            runtime_parser.add_argument('--state-directory', type=Path, required=True)
    claim = sub.add_parser('init-plex-claim', help='Store a Plex claim privately with hidden input')
    claim.add_argument('--secrets-directory', type=Path, required=True)
    claim.add_argument('--claim-file', type=Path, help='Private raw claim-token input file for unattended use')
    claim.add_argument('--replace', action='store_true', help='Explicitly replace an expired stored claim')
    claim.add_argument('--filename', default='plex-claim.txt', help='Private output basename within the secrets directory')
    check_providers = sub.add_parser('check-providers', help='Test existing app provider connections without saving settings')
    check_providers.add_argument('--config', type=Path, required=True)
    check_providers.add_argument('--name', required=True)
    check_providers.add_argument('--provider-secrets-file', type=Path, required=True)
    check_providers.add_argument('--newshosting-connections', type=int, default=100)
    provider_secrets = sub.add_parser('init-provider-secrets', help='Collect provider credentials with hidden input')
    provider_secrets.add_argument('--secrets-directory', type=Path, required=True)
    provider_secrets.add_argument('--providers', required=True, help='Comma-separated newshosting,nzbgeek,opensubtitlescom')
    provider_secrets.add_argument('--credentials-file', type=Path, help='Private 0600 provider JSON input for unattended collection')
    provider_secrets.add_argument('--filename', default='providers.json', help='Private output basename within the secrets directory')
    smb_secrets = sub.add_parser('init-smb-secrets', help='Store mount.cifs credentials privately; does not mount or install a server')
    smb_secrets.add_argument('--secrets-directory', type=Path, required=True)
    smb_secrets.add_argument('--filename', default='smb.credentials')
    smb_secrets.add_argument('--credentials-file', type=Path, help='Executor-owned 0600 JSON input for unattended use')
    secrets = sub.add_parser("init-secrets", help="Store shared GUI credentials privately")
    secrets.add_argument("--secrets-directory", type=Path, required=True)
    secrets.add_argument("--credentials-file", type=Path, help="Private 0600 JSON input for unattended use")
    secrets.add_argument("--config", type=Path, help="Validate shared GUI input against selected applications before saving")
    for name in ("configure", "plan", "check-storage", "check-storage-writes", "prepare-accounts", "render-compose", "prepare-prerequisites", "prepare-directories", "check-mounts", "prepare-mounts"):
        child = sub.add_parser(name)
        child.add_argument("--config", type=Path, default=Path("installarr.json"))
        if name == "prepare-mounts":
            child.add_argument("--state-directory", type=Path, default=Path("/var/lib/installarr-mounts"))
        if name == "prepare-directories":
            child.add_argument("--state-directory", type=Path, default=Path("/var/lib/installarr-directories"))
        if name == "prepare-accounts":
            child.add_argument("--state-directory", type=Path, default=Path("/var/lib/installarr-accounts"))
    args = parser.parse_args(argv)
    if args.action is None:
        args.action = "setup"
    try:
        if args.action == "family-accounts":
            if os.geteuid() != 0 or not sys.stdin.isatty():
                raise HostPrerequisiteError('Run sudo ./installarr.sh family-accounts in your terminal.')
            from .guided import collect_family
            from .execution import private_directory
            from .ombi_family import initialize_family_preferences
            base = private_directory(Path('/var/lib/installarr-setup'))
            result = initialize_family_preferences(base / 'family', collect_family)
            print('Family Discord account numbers ' + result['status'] + ' privately. Notifications remain disabled.')
            return 0
        if args.action == "setup":
            from .guided import run_setup
            return run_setup(continue_as_admin=True) if getattr(args, 'continue_as_admin', False) else run_setup()
        if args.action == 'menu':
            from .menu import run_menu
            return run_menu(args.config, args.name, args.state_directory, main)
        if args.action in ('audit-runtime', 'refresh-runtime'):
            from .runtime import audit_runtime, refresh_runtime
            result = audit_runtime(args.name) if args.action == 'audit-runtime' else refresh_runtime(args.name, args.state_directory)
            print(json.dumps(result, indent=2))
            return 2 if args.action == 'audit-runtime' and not all(row['integrity'] for row in result['services']) else 0
        if args.action == 'check-providers':
            from .providers import check_existing_providers
            print(json.dumps(check_existing_providers(validate(json.loads(args.config.read_text())), args.name,
                args.provider_secrets_file, args.newshosting_connections), indent=2))
            return 0
        if args.action == 'init-smb-secrets':
            from .smb_secrets import initialize_smb_secrets, read_smb_input
            if os.geteuid() != 0:
                raise HostPrerequisiteError('SMB credential collection requires root')
            values = read_smb_input(args.credentials_file) if args.credentials_file else None
            def collect_smb():
                if values is not None:
                    return values
                if not sys.stdin.isatty():
                    raise ValueError('SMB collection requires a terminal or private input file')
                result = {'username': getpass.getpass('SMB username (hidden): '),
                          'password': getpass.getpass('SMB password (hidden): ')}
                domain = getpass.getpass('SMB domain (optional, hidden): ')
                if domain:
                    result['domain'] = domain
                return result
            print(json.dumps(initialize_smb_secrets(args.secrets_directory, collect_smb, args.filename)))
            return 0
        if args.action == 'init-provider-secrets':
            from .provider_secrets import initialize_provider_secrets, read_provider_secrets
            names = args.providers.split(',')
            input_credentials = read_provider_secrets(args.credentials_file) if args.credentials_file else None
            if input_credentials is not None and not set(names) <= set(input_credentials):
                raise ValueError('Private provider input does not contain the selected providers')
            def collect_provider(name):
                if input_credentials is not None:
                    return input_credentials[name]
                if not sys.stdin.isatty():
                    raise ValueError('Provider credential collection requires a terminal')
                print('Enter credentials for ' + name + ' (hidden; stored privately).')
                if name == 'nzbgeek':
                    return {'api_key': getpass.getpass('NZBGeek API key: ')}
                return {'username': getpass.getpass(name + ' username: '),
                        'password': getpass.getpass(name + ' password: ')}
            print(json.dumps(initialize_provider_secrets(args.secrets_directory, names, collect_provider, args.filename)))
            return 0
        if args.action == "preflight":
            print(json.dumps(preflight(), indent=2))
        elif args.action == "prepare-docker":
            print(json.dumps(prepare_docker(args.state_directory), indent=2))
        elif args.action == "prepare-test-daemon":
            print(json.dumps(prepare_test_daemon(), indent=2))
        elif args.action == "apply":
            if args.reference:
                from .reference import apply_reference
                if args.state_directory is None:
                    raise ValueError("Reference proof of concept requires --state-directory with an existing local parent")
                print(json.dumps(apply_reference(validate(json.loads(args.config.read_text())), args.name, args.state_directory, args.credentials_file, prepare_only=args.prepare_only), indent=2))
                return 0
            if args.prepare_only:
                raise ValueError('--prepare-only requires reference mode')
            from .apply import apply
            print(json.dumps(apply(validate(json.loads(args.config.read_text())), args.name,
                args.state_directory, args.secrets_directory, args.credentials_file), indent=2))
        elif args.action == "install-service":
            print(json.dumps(install_service(validate(json.loads(args.config.read_text())), args.name), indent=2))
        elif args.action == "service-status":
            print(json.dumps(service_status(args.name), indent=2))
        elif args.action == "configure":
            configure(args.config)
        elif args.action == "render-compose":
            print(json.dumps(write_bundle(validate(json.loads(args.config.read_text()))), indent=2))
        elif args.action == "prepare-mounts":
            from .mounts import prepare_mounts
            print(json.dumps(prepare_mounts(validate(json.loads(args.config.read_text())), args.state_directory), indent=2))
        elif args.action == "check-mounts":
            from .mounts import check_mounts
            result = check_mounts(validate(json.loads(args.config.read_text())))
            print(json.dumps(result, indent=2))
            return 2 if result['status'] == 'conflict' else 0
        elif args.action == "prepare-directories":
            print(json.dumps(prepare_directories(validate(json.loads(args.config.read_text())), args.state_directory), indent=2))
        elif args.action == "prepare-prerequisites":
            print(json.dumps(prepare_prerequisites(validate(json.loads(args.config.read_text()))), indent=2))
        elif args.action == 'init-plex-claim':
            from .plex import store_claim, read_claim_file
            def collect_claim():
                if args.claim_file:
                    return read_claim_file(args.claim_file)
                if not sys.stdin.isatty():
                    raise ValueError('Use a private claim file for unattended use')
                print('Open https://www.plex.tv/claim on another device, then enter the short-lived claim below.')
                return getpass.getpass('Plex claim token (hidden): ')
            print(json.dumps(store_claim(args.secrets_directory, collect_claim, args.replace, args.filename), indent=2))
        elif args.action == "init-secrets":
            from .credentials import validate_selected_gui_credentials
            selected_config = validate(json.loads(args.config.read_text())) if args.config else None
            def collect():
                if args.credentials_file:
                    values = read_private_credentials(args.credentials_file)
                else:
                    if not sys.stdin.isatty():
                        raise ValueError("Use a protected credentials file for unattended use")
                    if selected_config and set(selected_config['apps']) & {'sabnzbd', 'bazarr', 'netbootxyz'}:
                        print('Selected Basic-auth apps require a username without a colon.')
                    values = {"username": input("Shared GUI administrator username: "),
                              "password": getpass.getpass("Shared GUI administrator password: ")}
                return validate_selected_gui_credentials(selected_config, values) if selected_config else values
            result = initialize_credentials(args.secrets_directory, collect)
            if selected_config:
                validate_selected_gui_credentials(selected_config, read_private_credentials(args.secrets_directory / 'gui-admin.json'))
            print(json.dumps(result, indent=2))
        elif args.action == "prepare-accounts":
            config = validate(json.loads(args.config.read_text()))
            result = prepare_accounts(config, args.state_directory, identity_conflicts)
            print(json.dumps(result, indent=2))
        elif args.action in ("check-storage", "check-storage-writes"):
            config = validate(json.loads(args.config.read_text()))
            checked_config = dict(config, storage_checks=storage_assertions(config))
            checker = check_storage if args.action == "check-storage" else check_service_writes
            result = checker(checked_config, mount_inventory(command))
            print(json.dumps(result, indent=2))
            return 0 if all(row["status"] in ("verified", "not_required") for row in result["checks"]) else 2
        else:
            result = plan(json.loads(args.config.read_text()))
            print(json.dumps(result, indent=2))
            return 2 if result["conflicts"] else 0
        return 0
    except PlexAuthorizationRequired:
        print('Plex account authorization is required. Store a fresh claim with init-plex-claim, set plex_claim_file to that private path, and rerun apply. Plex ports remain unpublished.', file=sys.stderr)
        return 2
    except HostPrerequisiteError as error:
        print(str(error), file=sys.stderr)
        return 1
    except AppAPIError as error:
        # This type's contract permits only fixed diagnostics and public HTTP
        # statuses, never server bodies, input credentials or arbitrary exceptions.
        print("Unable to complete {}: {}".format(args.action, error), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired, EOFError, KeyboardInterrupt) as error:
        # Do not echo arbitrary configuration contents or exception text.
        print(f"Unable to complete {args.action}: invalid input, inaccessible file, or interrupted operation ({type(error).__name__}).", file=sys.stderr)
        return 1
