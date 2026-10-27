# Installarr development handoff

Read README.md and docs/PHYSICAL_TEST_HOST.md before host experiments.
The user authorized continued implementation toward a fully usable headless
installer, including local tests on a dedicated physical Ubuntu machine.
Work in the existing checkout; no worktree is needed.

## Product requirements

- Fresh Ubuntu provisioning first; application-state migration/disaster recovery
  is a stretch goal. Initial provisioning target: Ubuntu 24.04 LTS. Read-only
  discovery supports Python 3.8 / production Ubuntu 20.04.
- CLI only, including menus, hidden credential input, unattended configuration
  and resumable execution. Browser-based Plex/Codex authorization can happen on
  another device. Do not store secrets in the nonsecret JSON configuration.
- Every app is optional: SABnzbd, Sonarr, Radarr, Bazarr, Jackett, Plex, Ombi,
  Tautulli, netbootxyz. Discover dependencies; do not pretend Jackett downloads torrents.
- Use current official image guidance and tested image versions. Standardize
  non-root application identities instead of copying production PUID/PGID 0:0.
  Image entrypoints may legitimately initialize as root then drop privileges.
- When netbootxyz is selected, host user/group nbxyz must use UID 911/GID 1001.
  Verify image runtime permissions. DHCP and PXE client reachability are out of scope.
- Plex ALLOWED_NETWORKS is desired behavior, default preset 192.168.0.0/23.
  Default timezone America/Chicago. Host IP/hostname are detected/editable.
- One storage map must populate Compose and every relevant application root,
  category, library and integration. Preserve existing host files and path case.
  Prefer local application databases. Do not recursively chown NAS libraries.
- Install nfs-common BEFORE any NFS mount attempt; cifs-utils for SMB. Use signed
  repositories. Preserve existing mounts/fstab; back up approved persistence edits.
- Mount health includes expected source/type and reachable files, plus separate
  service-UID write checks. An unhealthy Docker status does not stop containers.
  Prevent writes beneath absent mounts through reboot AND Docker auto-restarts.
- Prompt once for a shared GUI administrator username/password for supported apps.
  Do not confuse API keys with passwords. Plex uses its own authorization; Jackett
  username support must be verified. Do not expose bootstrap services unprotected.
- Ombi family users use individual Plex accounts, not local lookalikes. Optional
  family presets: lenora8 -> Lenora movie/TV roots and 1080-or-lower profiles;
  rebel739 -> Jeremy roots and 1080-or-lower profiles; beanie08 intentionally
  inherits global roots/profiles. AutoApproveMovie/AutoApproveTv for all three;
  Beanie also PowerUser. Resolve tags/profile/root/user IDs dynamically. Discord
  preferences remain disabled; collect optional IDs securely when needed.
- Pin full versioned TRaSH profiles, not just representative custom formats.
  API research from the earlier handoff is version-specific, not proof of working
  auth, Plex selective import, request dispatch, downloads or per-user routing.
  Validate schemas, read back writes and test restart persistence/reruns.

## Current implementation and next work

preflight/configure/plan/check-storage exist; there is NO apply command yet.
Storage choice collection supports local/existing/NFS/SMB, with deduplicated plans
and read-only mount/sentinel checks. Config files are private and never overwritten.
Run `python3 -m unittest discover -s tests -v` before committing changes.

Next: implement host adapters (accounts, prerequisites, Docker, storage), persistent
execution state, protected secrets and fail-closed service startup; then Compose
generation and version-tested app API adapters. Use minimal disposable service pairs
for experiments, not a second complete stack. Record exact tested versions, commands,
results, failures and unresolved gates in docs/TEST_RESULTS.md without secrets.
Never mark install readiness based only on inventory, open ports or config acceptance.

## Test boundaries

Physical test host is isolated on a VLAN; it can reach the NAS and Internet only.
One isolated test NFS mount is intended for TV/movies. Confirm its actual source
and target before writing. The proposed test source was
192.168.1.102:/share/MD0_DATA/Public/installarr at /media/installarr; do not assume
it mounted successfully. Keep all NAS writes inside that confirmed test subtree.
Never inspect or modify production apps, sibling NAS folders, shares or host settings
outside the test scope. Do not repartition/format disks or change SSH/firewall/VLAN.
Preserve operator changes; propose reboot timing explicitly so SSH can reconnect.
Sudo access and Codex permissions are runtime prerequisites, not provided by this file.
