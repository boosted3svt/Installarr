# Installarr

Headless CLI for fresh Ubuntu media-stack provisioning. This initial release
implements read-only discovery, interactive nonsecret configuration, and planning.
It does **not** install packages, create accounts, mount storage, deploy containers,
or provision application APIs yet. A successful inventory is not host readiness.

## Run

Python 3.8+ is required; the initial host provisioning target is Ubuntu 24.04 LTS.
Read-only inventory can also run on older Ubuntu hosts. Timezone validation uses
the system timezone database (`tzdata`), without a Python `zoneinfo` dependency.
No third-party runtime dependencies are required. From this checkout:

```sh
python3 -m installarr preflight
python3 -m installarr configure --config /tmp/installarr.json
python3 -m installarr plan --config /tmp/installarr.json
python3 -m unittest discover -s tests -v
```

`configure` requires a terminal and refuses to overwrite existing files. Saved JSON
is mode 0600 and contains no credentials. For unattended planning, supply the same
JSON schema directly. `plan` exits 2 for identity conflicts, 1 for invalid input or
file errors, and 0 for a conflict-free preview; 0 does not imply deployment readiness.
Preflight reports command availability and exit codes without exposing command stderr.

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
3. Validate Ubuntu VM account collisions, storage permissions, missing NAS, reboot,
   and Docker restart protection before claiming host provisioning readiness.
4. Generate Compose, bootstrap authentication, configure integrations, and read back
   settings through version-tested application adapters.
5. Exercise reruns, interrupted runs, restart persistence and approved functional tests.

Use the existing isolated checkout for development; do not create a worktree unless requested.
