# Supervised Plex media permissions

This optional policy repairs read access for the configured non-root media identity
inside Plex's selected library folders. It uses the existing Installarr host
supervisor; there is no new service/backend and Plex's media binds stay read-only.
It is storage-agnostic POSIX permission handling, not a NAS GUI/API/ACL integration.
The storage server must permit the host to make the requested metadata changes.

## Schedule

- First pass starts after the supervisor confirms healthy storage and running
  owned containers. It does not wait for a separate timer after startup.
- Next full pass is due60seconds AFTER the previous pass is collected as finished.
  The existing supervisor polls about every2seconds, plus bounded health-check time.
- A worker processes at most1000entries or5seconds of active traversal per batch.
  Large trees continue in later supervisor iterations, before the60second rest.
- A batch has a30second outer deadline for stalled filesystem operations. Timed-out
  workers are terminated/tracked; an unreaped worker prevents another repair worker.
  No overlapping repair passes are launched. Health supervision runs independently.
- A supervisor/container startup with healthy storage begins a new pass; resuming
  after supervisor restart starts traversal from the roots. Directory enumeration
  changing during a pass may defer a new entry until the following full pass.

This is eventual repair, not an instantaneous guarantee for a large/stalled library.
`complete` in status means traversal completed, not proof every item is accessible;
check denied/skipped/error counts too. Plex still needs a library scan to discover
media; the permission policy does not modify Plex's scan schedule or force scans.

## Scope and changes

Only host paths backing configured Plex library locations are included. Downloads,
application configs/databases, unrelated share folders and unselected sources are
excluded. An explicitly read-only secondary source remains excluded. The worker
checks exact source/type/mount and the existing health marker before traversal,
then rechecks held mount/root identity immediately before metadata changes.

Accessible items remain unchanged. For inaccessible directories/files:

- If the service UID owns the item, add owner read permission and directory search.
- Otherwise, assign the shared service GID if needed and add group read permission
  and directory search. This can replace an existing owning GROUP.
- The file-owner UID is preserved. File content and modification time are preserved;
  metadata change time necessarily changes. Existing write bits are not widened.
- The worker verifies access in a short-lived child with the service's real UID/GID
  and no supplementary groups (including Ubuntu20.04/Python3.8). Server refusals/access failures are counted, not treated as successful repair.

Symlinks, hard-linked regular files, special files, nested mounts and NAS `.@*`
metadata folders are skipped. Depth is bounded128frames. This avoids redirecting
repairs into unrelated/shared data. A missing/changed mount or unhealthy supervisor
storage check cancels repair rather than writing under a missing mount.

This explicitly approved option supersedes the old preserve-all-content-metadata
rule only within its configured scope. It is NOT recursive chown of an entire NAS
share, world-writable777 permissions, or running Plex as root. Restrictive copied
folders such as root:root750 can normally become root:media750, leaving the owner
UID intact. Read repair alone does not grant Arr/Bazarr write permission on copies.

## Enable, inspect or disable

New guided installs offer an explicit permission-repair question, default no.
The corresponding optional nonsecret setting is `media_permission_repair: true`.
New live reference supervisors then receive their own private opt-in policy.
Existing configs/Compose fingerprints are not silently rewritten.

For a deployment whose supervisor runtime already contains this feature:

```sh
sudo ./installarr.sh media-permissions --name family-media --enable
sudo ./installarr.sh media-permissions --name family-media
sudo ./installarr.sh service-status --name family-media
sudo ./installarr.sh media-permissions --name family-media --disable
```

Use the actual owned deployment name. Policy file:
`/var/lib/installarr-services/NAME/media-permissions.json` (root600).
Runtime health reports `media_permissions`: enabled/running/completion, counters,
last check time, interval and safe error labels; no file contents or secrets.
Progress cursors stay private/in-memory. Worker PID tracking is private/local.
Disabling is observed at the next supervisor iteration and cancels an active worker.

Old immutable supervisors require an explicit stopped-runtime refresh before this
policy can run. `runtime_supports_repair` distinguishes that case. The current
family-media installation was explicitly refreshed and restarted for this feature;
its private runtime backup is recorded in CURRENT_PROGRESS.md. Bootstrap stays off.
