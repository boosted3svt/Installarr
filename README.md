# Installarr

Headless CLI for fresh Ubuntu media-stack provisioning. This initial release
implements read-only discovery, interactive nonsecret configuration, and planning.
It does **not** install packages, create accounts, mount storage, deploy containers,
or provision application APIs yet. A successful inventory is not host readiness.

## Run

For local agent setup and testing on the isolated physical Ubuntu machine, see
[Physical test host](docs/PHYSICAL_TEST_HOST.md) and [Agent handoff](AGENTS.md).

Python 3.8+ is required; the initial host provisioning target is Ubuntu 24.04 LTS.
Read-only inventory can also run on older Ubuntu hosts. Timezone validation uses
the system timezone database (`tzdata`), without a Python `zoneinfo` dependency.
No third-party runtime dependencies are required. From this checkout:

```sh
python3 -m installarr preflight
python3 -m installarr configure --config /tmp/installarr.json
python3 -m installarr plan --config /tmp/installarr.json
python3 -m installarr check-storage --config /tmp/installarr.json
python3 -m unittest discover -s tests -v
```

`configure` requires a terminal and refuses to overwrite existing files. Saved JSON
is mode 0600 and contains no credentials. For unattended planning, supply the same
JSON schema directly. `plan` exits 2 for identity conflicts, 1 for invalid input or
file errors, and 0 for a conflict-free preview; 0 does not imply deployment readiness.
Preflight reports command availability and exit codes without exposing command stderr.

## Read-only storage validation

Preflight now returns parsed mount records instead of escaped nested JSON. It only
lists mount metadata; it does not access remote files. `check-storage` explicitly
reads the configured directories as the invoking operator, without creating files.
It does not establish service-UID permissions or write access.

Add optional `storage_checks` to your existing JSON configuration. For example,
if `storage.media` is `/media/Media/TV`:

```json
"storage_checks": {
  "media": {
    "mountpoint": "/media/Media",
    "source": "192.168.1.103:/share/MD0_DATA/Public",
    "fstype": "nfs",
    "sentinel": "healthcheck.txt"
  }
}
```

The sentinel must already exist inside that storage directory. The command never
creates it. Source, filesystem and covering mountpoint must match exactly before
file reads occur. Configured storage directories containing symlinks are rejected
to avoid probing a different filesystem than the asserted mount.
A missing NAS that leaves an ordinary local directory therefore
fails before probing it. Each probe has a five-second subprocess timeout; kernel
uninterruptible filesystem I/O may delay process cleanup beyond that timeout.

Exit 0 means all configured storage purposes passed mount assertions and sentinel
reads. Exit 2 means at least one failed or lacks sufficient assertions; exit 1 means
invalid configuration or a command error. Individual results distinguish `verified`,
`failed`, and `incomplete`. These checks do not establish boot persistence, NAS write
access, or automatic protection for running containers. Existing configurations
remain valid, but their storage checks report incomplete until assertions are added.

## Storage wizard and host preparation plan

`configure` now asks for local, existing-mount, NFS or SMB storage independently
for each purpose. NFS/SMB inputs capture the exact source, mountpoint, filesystem
and optional existing sentinel; SMB captures only a credentials **file path**, never
a username/password. Do not put credentials in source URLs or paths.

These choices populate `storage_mounts` and automatically supply assertions to
`check-storage`. Multiple directories may share one identical mount. Conflicting
sources at a mountpoint, directories outside their declared mounts, conflicting
check assertions and nested mount layouts are rejected. Existing mounts are marked
for reuse without changing their persistence configuration. Local storage means an
existing filesystem directory, not disk formatting or partitioning.

`plan` now includes deduplicated mount proposals, required NFS/CIFS packages,
directory intentions, and outstanding validation gates. It does not execute them.
An example mount choice (alongside `storage.media: /media/Media/Movies`):

```json
"storage_mounts": {
  "media": {
    "kind": "nfs",
    "mountpoint": "/media/Media",
    "source": "192.168.1.103:/share/MD0_DATA/Public",
    "fstype": "nfs"
  }
}
```

Old JSON files remain accepted and report missing storage choices in the host
preparation blockers. Plans are declarative, not runnable scripts; `apply` is not
implemented. New wizard runs should use a new filename because overwrites remain
prohibited. No root access is needed for configuration and planning.

## Design requirements

- Fresh provisioning first; application-state migration/disaster recovery is a stretch goal.
- CLI only; browser authorization, if necessary, takes place on another device.
- Every app is optional: SABnzbd, Sonarr, Radarr, Bazarr, Jackett, Plex, Ombi,
  Tautulli and netbootxyz.
- Prefer documented image-specific non-root ownership. Never inherit production 0:0.
- Selected netbootxyz requires host user/group `nbxyz`, UID 911 and GID 1001.
  Its runtime permission mechanism must be verified against official image guidance.
  DHCP and client PXE reachability are operator-managed.
- Preserve the editable Plex allowed-network preset `192.168.0.0/23`.
- Generate Compose and application paths from one storage map. Existing host media
  is never renamed or recursively chowned by default.
- Validate mount identity, reachable sentinel files, application APIs, and service-UID
  access separately. Implement mount-loss protection beyond Docker health status.
- GUI administrator credentials are distinct from Linux users and generated API keys.
  Family Ombi users use Plex authorization, with optional reconciled family presets.
- Pin tested application images and TRaSH profile snapshots; dynamically resolve IDs.
- No production writes during development. Use isolated test paths and minimal
  disposable service pairs, never production download destinations.

## Next implementation gates

1. Validate image documentation, choose versions, and expand storage configuration
   to model local/NFS/SMB sources and persistent mount requirements.
2. Build privileged host adapters with reviewed plans, backups and resume state.
3. Validate isolated physical Ubuntu account collisions, storage permissions, missing NAS, reboot,
   and Docker restart protection before claiming host provisioning readiness.
4. Generate Compose, bootstrap authentication, configure integrations, and read back
   settings through version-tested application adapters.
5. Exercise reruns, interrupted runs, restart persistence and approved functional tests.

Use the existing isolated checkout for development; do not create a worktree unless requested.
