# Proposed production storage change log

Status: APPROVED AND IMPLEMENTED IN CHECKOUT (2026-10-29). The operator requested
implementation and then chose empty standardized folders, no Music library, and
the netboot export's assets child. Production switching is performed by the guide
after its normal Start installation confirmation; it has not been executed by
Codex. The prior running test stack remains unchanged. No existing media moves.

Originally prepared 2026-10-29 from the operator's requested layout,
current saved configuration, Compose generator and storage/app adapters. No source
code, deployed configuration, service, mount, NAS directory or media changes made
for the original proposal. Production exports have not been mounted or inspected
by Codex for this implementation. See the implementation record at the end.

## 1. Current state and mount-list correction

Both `/media/Media` and `/media/NAS` currently mount
`192.168.1.102:/share/MD0_DATA/Public/installarr`, type nfs. Explicit path arguments
to `df -h /media/Media /media/NAS` show both. Plain `df`/`df -h` suppresses duplicate
filesystems; the operator's output includes `/media/NAS` and omits `/media/Media`.
`findmnt --mountpoint PATH` is the direct mount check. Listing historical test
folders is not evidence of local fallback writes: those fixtures exist on the
test export. This observation establishes current mounts, not every past state.

The running deployment deliberately uses empty test subfolders. The saved primary
root is `/media/Media/Installarr-Clean-Test/Primary`; secondary is
`/media/NAS/Installarr-Clean-Test/AdditionalMovies`. This explains empty libraries.
It is not the requested production configuration.

## 2. Proposed production mounts

| Purpose | Exact NFS source | Proposed Ubuntu mount |
| --- | --- | --- |
| Primary media and Usenet downloads | 192.168.1.103:/share/MD0_DATA/Public | /media/Media |
| Additional movies | 192.168.1.102:/share/MD0_DATA/Public | /media/Media-2 |
| netboot.xyz storage | 192.168.1.102:/share/MD0_DATA/netbootxyz | /media/netbootxyz |

`/media/Media-2` follows the latest detailed request and supersedes the earlier
`/media/NAS` secondary destination for the proposed configuration. Do not mount
production over a running test deployment. Review conflicting current mounts/fstab
first; preserve/back up entries, stop the owned deployment before switching, and
never silently overwrite unrelated mounts. The old test paths remain preserved.
Verified transport settings for the .102 test NAS are not assumed for .103; each
production source must pass its own exact identity/transport checks before writes.

## 3. One explicit folder map

Paths are proposed defaults shown and editable in the guide before saving. Each
row records its host source, container destination, storage assertion and app use.
No app independently constructs legacy `Movies`, `TV`, or family folder names.

| Purpose | Ubuntu host directory | Identical container path wherever used | App/library use |
| --- | --- | --- | --- |
| Unfinished downloads | /media/Media/unfinished-downloads | /data/unfinished-downloads | SAB incomplete directory |
| Finished downloads | /media/Media/finished-downloads | /data/finished-downloads | SAB completed base; Arr imports |
| Finished movie category | /media/Media/finished-downloads/movies | /data/finished-downloads/movies | SAB movies category; Radarr |
| Finished TV category | /media/Media/finished-downloads/tv | /data/finished-downloads/tv | SAB tv category; Sonarr |
| Global movies | /media/Media/media-movies | /data/media-movies | Radarr default; Plex Movies |
| Lenora movies | /media/Media/media-lenoramovies | /data/media-lenoramovies | Radarr root; Ombi Lenora; Plex Movies |
| Jeremy movies | /media/Media/media-jeremymovies | /data/media-jeremymovies | Radarr root; Ombi Jeremy; Plex Movies |
| Additional movies | /media/Media-2/media-movies-2 | /data/media-movies-2 | Radarr root; Plex Movies; Bazarr |
| Global TV | /media/Media/media-tv | /data/media-tv | Sonarr default; Plex TV Shows |
| Lenora TV | /media/Media/media-lenoratv | /data/media-lenoratv | Sonarr root; Ombi Lenora; Plex TV Shows |
| Jeremy TV | /media/Media/media-jeremytv | /data/media-jeremytv | Sonarr root; Ombi Jeremy; Plex TV Shows |
| Sports | /media/Media/media-Sports | /data/media-Sports | Plex Sports; Radarr access as requested |
| Standup | /media/Media/media-Standup | /data/media-Standup | Plex Standup; Radarr access as requested |
| netboot assets, proposed child | /media/netbootxyz/assets | /assets | netboot.xyz assets, UID911/GID1001 |

The secondary host folder has an explicit bind to `/data/media-movies-2`; this does
not merge NAS filesystems or require a union filesystem/backend. Remove the
installer-invented `/media-secondary` alias from newly generated setups. Main Plex
libraries become Movies, TV Shows, Sports and Standup with the exact case above.
Preserve existing Plex library IDs when editing the owned installation where
possible. Music is unresolved below; do not silently remove it.

## 4. Proposed application access

This table describes media access. Every app still needs its own writable LOCAL
`/config` and normal image temporary directories. Plex also needs writable LOCAL
transcode/cache/database/log directories; its media bind mounts remain read-only.

| App | Unfinished | Finished | Four movie folders | Three TV folders | Sports/Standup | Other |
| --- | --- | --- | --- | --- | --- | --- |
| SABnzbd | RW | RW | No bind | No bind | No bind | No media-library write access needed |
| Radarr | No bind | RW | RW | No bind | RW, requested | Import, rename, replace and remove completed source files |
| Sonarr | No bind | RW | No bind | RW | No bind | Import, rename, replace and remove completed source files |
| Plex | No bind | No bind | RO | RO | RO | Local transcode/config RW |
| Bazarr | No bind | No bind | RW | RW | Only if these items are managed through connected Arr apps | Subtitle creation/replacement beside media |
| Ombi | No bind | No bind | No bind | No bind | No bind | Remote Arr/Plex APIs; root IDs resolved dynamically |
| Tautulli | No bind | No bind | No bind | No bind | No bind | Plex logs RO; own local config RW |
| Jackett | No bind | No bind | No bind | No bind | No bind | API indexer links; no torrent client is installed |
| netboot.xyz | No bind | No bind | No bind | No bind | No bind | Separate netboot assets RW,911:1001 |

Radarr access does not make arbitrary sports/standup files identifiable movies.
Expose the folders as requested without automatically importing/renaming their
contents. Plex read-only access precludes saving subtitles/artwork beside media;
Bazarr supplies subtitles, while Plex metadata remains local.

All media apps currently share UID/GID2000:2000. That identity alone cannot enforce
different permissions per app. Proposed strict access uses only the allowed bind
subtrees, rather than giving all apps the existing writable `/data` parent. Do not
recursively chmod/chown existing NAS libraries or introduce unapproved NAS ACLs.
Check the NAS grants traverse/read/write/delete access for the service identity;
preserve existing ownership and refuse conflicts.

### Import performance choice for review

Narrow, separate container binds can prevent atomic renames/hardlinks even when
host folders are on the same filesystem. The strict-access proposal therefore
must support and test copy-then-delete imports, allow enough temporary free space,
and must not claim instant imports. Secondary-NAS imports necessarily cross
filesystems. Local-NVMe staging to NAS has the same copy requirement.

Alternatively, one common writable parent bind preserves same-filesystem move
opportunities but exposes additional siblings to Radarr/Sonarr/SAB. That is broader
than the proposed access table and should not be silently substituted. Review
choice: strict per-app bind access (proposed default) versus broader shared-tree
access for same-filesystem import performance. Both keep identical paths across
apps. See [Linux rename mount restrictions](https://man7.org/linux/man-pages/man2/rename.2.html)
and [TRaSH import filesystem guidance](https://trash-guides.info/File-and-Folder-Structure/Hardlinks-and-Instant-Moves/).

## 5. Guide changes, including local NVMe

Current guide can use local storage indirectly by choosing an already connected
drive whose covering filesystem is local. It lacks a clear first-class local/NAS
choice, hardcodes most media children and download names, and does not collect the
operator's full folder map. It also treats netboot assets as local unless already
on a detected network filesystem. These do not meet the requested experience.

Proposed guide sequence:

1. Choose apps; choose local disk/NVMe, NAS/NFS, or an already mounted filesystem.
2. For local storage, choose an existing mounted disk/folder. Detect exact source,
   type and mount; no partitioning/formatting or automatic disk selection.
3. For NAS, collect server/export and mount destination separately from media
   directories; keep the selected NAS intent even when the mount is absent.
4. Offer additional media/netboot storage independently. Collect any required NFS
   endpoint overrides without requiring manual JSON edits.
5. Present each folder role in section3. Accept defaults or choose existing folders
   individually; display case exactly. Local-only mode uses the same names under
   the chosen local root and does not request NAS credentials or mount packages.
6. Distinguish root/OS-disk storage from a separately mounted NVMe. An absent
   separately selected disk must fail its mount assertion rather than fall back
   to the root filesystem. Explicit mixed local/NAS assignments need per-role
   assertions and copy-import handling, not the current forced one-filesystem map.
7. Review full source → host folder → container path → app/library/access table,
   existing-versus-new directories, and proposed persistence edits before apply.
8. Resume the saved same setup or explicitly select new reviewed storage choices;
   never silently reuse the previous test map for a production attempt.

## 6. Mount-loss protection and correct completion criteria

Existing implementation already has mount/source/type checks, held-directory
descriptors, startup guards, `create_host_path:false`, private bind propagation,
restart:no and a supervisor that stops owned containers on failed storage checks.
Retain these; this review did not demonstrate local fallback writes. However,
detected local storage must never override an explicitly selected absent NAS.

Proposed changes and acceptance:

- Install NFS helpers before mounts; validate exact export, type, target and
  reachable health marker before any media/category directory or sentinel write.
  Creating the empty root-owned mountpoint is allowed; creating data beneath an
  absent network mount is forbidden.
- Check the filesystem held by each write descriptor immediately before operations.
  Protect every new media/download/netboot role, including category children.
  No broad recursive ownership change, symlink workaround or marker-only proof.
- Never adopt underlying ext4 as a replacement for configured NFS. Preserve/refuse
  nonempty underlying local mountpoint directories; report them for review instead
  of deleting them or mounting over them blindly.
- Add startup mount dependencies as a supplement to exact runtime identity guards;
  a systemd dependency or Docker health flag alone is not sufficient.
- Stop installation at any required mount failure. Do not publish/start dependent
  apps, enable automatic startup or report success with missing category paths.
- Ongoing failed/expired storage probes close owned GUI listeners and stop owned
  apps. Existing supervisor is bundle-wide: a required media mount loss currently
  stops the whole owned stack. Do not imply per-app selective recovery exists.
- Retain bounded worker tracking and fail-closed restart behavior through daemon
  restarts, supervisor crashes and reboot. Never launch replacement probes while an
  old worker is unreaped. Hard NFS outages can leave kernel-blocked tasks; do not
  promise instant termination or uninterrupted I/O. The requirement is no local
  fallback writes and no further installation progress on an unverified mount.
- Before declaring completion, check required paths from inside SAB/Arr/Plex and
  read back Arr health for the reported missing-download-directory warnings. Test
  copy/import behavior with generated small fixtures, never existing movies.
- Use isolated/private fixtures for failure tests. Any production outage/unmount
  test or reboot requires a separately coordinated action; none is approved here.

## 7. Other known fixes in the same proposed implementation

| Change | Expected outcome |
| --- | --- |
| Apply pinned quality-size definitions, separately from installed profiles/CFs | Radarr/Sonarr size sliders reflect tested movie/series guidance, with API/schema checks, readback and restart persistence |
| Prepare finished-downloads/movies and finished-downloads/tv | Arr downloader health checks no longer report nonexistent completed-category directories |
| Use explicit folder map in Plex, Arr, SAB, Bazarr and family adapters | No hardcoded legacy roots or divergent path aliases |
| Preserve Ombi's direct claimed-Plex token integration | Fetch/test selected libraries automatically; no owner Plex password or family passwords collected |
| Explain Plex library scan versus Arr registration | Existing files can appear in Plex after scan; an empty fresh Arr database does not automatically gain movie/series records merely because roots are added |
| Avoid duplicate welcome after sudo elevation | One welcome/Continue flow for normal launcher use |
| Preserve private existing input stores | No chat credentials or unnecessary recollection on the same installation |

The quality-size adapter must use the pinned snapshot's movie/series documents,
translate app-specific unlimited limits correctly and preserve unrelated/custom
settings instead of silently overwriting operator edits.

## 8. Decisions needed when reviewing this proposal

1. **Existing media — resolved:** operator chose new standardized folders empty.
   New `media-*` directories will initially be empty. Creating
   them does not relocate existing Movies/TV/family files. The guide should allow
   selecting the current populated folders as-is. Moving/renaming/copying existing
   production trees is a separate explicit decision; no bulk media migration is
   included in this proposal. Standard new names and immediate visibility of old
   files cannot both be assumed without settling their actual locations/handling.
2. **Music — resolved:** operator chose exclusion from the new setup. Existing
   Music files and the stopped previous Plex database remain preserved.
3. **netboot export layout — resolved:** operator confirmed the assets subfolder.
   Source is the supplied dedicated export,
   mounted at /media/netbootxyz, with host child /media/netbootxyz/assets. Confirm
   whether existing boot files are in that child or the export root. Keep app
   configuration local unless separately requested; verify911:1001 access.
4. **Permissions/performance:** implemented the approved proposal's strict-access
   default. Both real generated Radarr/SAB and Sonarr/SAB imports passed across
   these separate binds. Do not promise atomic rename/hardlink performance.

## 9. Implementation and production execution order, after review

1. Implement explicit source/folder/access model and guided selection; update CLI
   validation, Compose/app path adapters and directory/health planning together.
2. Add regression cases for local-only NVMe, NAS, mixed sources, exact new case,
   optional apps, family routes, category creation, quality sizes and mount loss.
   Keep Python3.8 compatibility; run full suite and targeted isolated physical tests.
3. Render a concrete new production plan privately and show its nonsecret mapping
   and persistence diffs. Reconcile verified actual production folder choices only
   within the approved sources; do not guess existing folder names from labels.
4. Schedule stopping only the owned test deployment. Preserve settings/checkpoints,
   stopped app databases and unit definitions; keep credentials/claimed identity.
   Never start duplicate Plex identity databases or overwrite immutable checkpoints.
5. Reconcile reviewed production mounts/fstab with backups. Create only approved
   new directories after exact mount/access verification. Do not remove the old
   test export folders or any production files.
6. Deploy the reviewed bundle and apply all app paths, library names/locations,
   categories, family roots and size settings. Preserve unrelated app state and
   library IDs; reject conflicting in-use roots rather than bulk reassign content.
7. Verify live readback, access matrix, service ownership, category visibility and
   Arr warnings. If a required check fails, stop the owned deployment and preserve
   evidence. An earlier test result or enabled unit does not establish boot safety.
8. Coordinate reboot testing later; no reboot, production switch, source change,
   directory creation or media move is performed by preparing this document.

## 10. Implementation record and next operator run

- `folder_map` is opt-in for saved/unattended configurations and the default for
  new guided configurations. Legacy saved configs remain unchanged/compatible.
- Local/NVMe, NAS and existing-mount selection, optional independent download
  storage, editable media roles, NAS endpoint overrides and full mapping review
  are implemented. Missing-drive intent cannot silently become OS-disk storage.
- Compose binds, role-specific startup guards, supervised checks, directories,
  Arr roots (including family/secondary), Plex library locations, SAB folders and
  Ombi family roots share the explicit layout. Jackett has no unnecessary media
  bind. All511optional app subsets pass rendering and1022native Compose parses.
- Category directories are prepared before startup, and actual container path
  access is tested as the service UID before completion. Relevant Arr missing-
  download-directory health warnings block successful setup.
- Pinned movie/series quality-size limits are applied/read back independently of
  full profiles/CFs, preserving unrelated qualities and refusing custom conflicts.
- The duplicate welcome after sudo elevation is removed.
- Saved-setup flow: answer no to continuing the old configuration, then yes to a
  fresh installation. New config/state/DBs are separate; private account inputs
  are reused after confirmation. Prior owned services are stopped/disabled and
  containers removed only after ownership verification. Conflicting managed mounts
  get normal bounded unmounts; unrelated mounts/fstab entries are refused.
- Before replacing fstab entries, a private durable checksum-tracked backup is
  saved. A nonempty local netboot mountpoint is not hidden: only its exact prior
  verified assets child may be atomically archived unchanged under the new setup's
  retired-local-assets directory; unrelated files cause refusal.
- Fresh-install distinction: the OLD claimed Plex database is preserved intact
  as stopped state. The NEW installation uses a new Plex database and needs a
  fresh owner claim; it does not silently rewrite old libraries or copy claimed
  identities. This implements a fresh production attempt, not a media/DB migration.
- Physical generated download/import, exact bytes/ownership, restart/rerun and
  scope checks passed on Radarr/SAB and Sonarr/SAB. Local-only SAB and actual Plex
  guard/read-only write-denial checks also passed. Detailed evidence/pins and
  supported-userspace results are in TEST_RESULTS.md and CURRENT_PROGRESS.md.
- Full production exports/UID access, new nine-app Plex claim/library creation,
  real owned-deployment switch and boot acceptance still need the operator-run
  installation. Existing nine-app deployment is left running on its old snapshots.
  No reboot, production outage, commit or push was performed.
