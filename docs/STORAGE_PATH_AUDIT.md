# Current storage path audit

Observed 2026-10-29T18:20:31.185366+00:00. Read-only service/container inspection and application API/settings reads. No configuration or service changes. Authentication credentials remained in memory and are excluded.

**Result:** all nine running containers have exactly the host sources, container destinations and read/write modes declared by the active Compose file. Queried Plex, Arr and Ombi root paths agree.

**Operator GUI follow-up:** matching paths are not sufficient acceptance. Radarr and
Sonarr report missing SAB completed-category folders; their absence is an installer
preparation defect even though all bind/path strings agree. See follow-up below.

Active unit: `installarr-family-media.service`. Compose: `/var/lib/installarr-setup/project/compose.json`, also confirmed by every container's Compose label. The bootstrap Compose file is not the running deployment.

## Ubuntu filesystems

| Ubuntu mount | Source | Type |
| --- | --- | --- |
| / | /dev/nvme0n1p2 | ext4 |
| /media/Media | 192.168.1.102:/share/MD0_DATA/Public/installarr | nfs |
| /media/NAS | 192.168.1.102:/share/MD0_DATA/Public/installarr | nfs |

Both NAS mounts are aliases of the same approved isolated export. They do not represent two independent NAS exports. Primary and additional movies use different subdirectories of that one export. Production exports were not inspected.

## Media folders: application readback versus Compose

The Compose bind is the parent `/data`, not a separate bind for each child. Below, `/data/<child>` resolves through the primary host folder. `/media-secondary` has its own bind. Plex media binds are read-only; Sonarr, Radarr, SABnzbd, Bazarr and Jackett primary media binds are read/write. Radarr/Bazarr secondary binds are read/write.

| Ubuntu folder | Compose destination → app path | Application reference | Finding |
| --- | --- | --- | --- |
| /media/Media/Installarr-Clean-Test/Primary/Movies | /data → /data/Movies | Plex Movies; radarr root; Bazarr inherits Radarr paths | Matches |
| /media/NAS/Installarr-Clean-Test/AdditionalMovies | /media-secondary | Plex Movies; radarr root; Bazarr inherits Radarr paths | Matches |
| /media/Media/Installarr-Clean-Test/Primary/jeremymovies | /data → /data/jeremymovies | Plex Movies; radarr root; Bazarr inherits Radarr paths | Matches |
| /media/Media/Installarr-Clean-Test/Primary/lenoramovies | /data → /data/lenoramovies | Plex Movies; radarr root; Bazarr inherits Radarr paths | Matches |
| /media/Media/Installarr-Clean-Test/Primary/StandUp | /data → /data/StandUp | Plex StandUp | Matches |
| /media/Media/Installarr-Clean-Test/Primary/TV | /data → /data/TV | Plex TV; sonarr root; Bazarr inherits Sonarr paths | Matches |
| /media/Media/Installarr-Clean-Test/Primary/lenoratv | /data → /data/lenoratv | Plex TV; sonarr root; Bazarr inherits Sonarr paths | Matches |
| /media/Media/Installarr-Clean-Test/Primary/jeremytv | /data → /data/jeremytv | Plex TV; sonarr root; Bazarr inherits Sonarr paths | Matches |
| /media/Media/Installarr-Clean-Test/Primary/Music | /data → /data/Music | Plex Music | Matches |
| /media/Media/Installarr-Clean-Test/Primary/sports | /data → /data/sports | Plex sports | Matches |
| /media/Media/Installarr-Clean-Test/Primary/incomplete-downloads | /data → /data/incomplete-downloads | SAB incomplete | Matches |
| /media/Media/Installarr-Clean-Test/Primary/downloads | /data → /data/downloads | SAB completed | Matches |
| /media/Media/Installarr-Clean-Test/Primary/downloads/movies | /data → /data/downloads/movies | SAB movies category; Radarr download client category | Matches; category subfolder not yet created |
| /media/Media/Installarr-Clean-Test/Primary/downloads/tv | /data → /data/downloads/tv | SAB tv category; Sonarr download client category | Matches; category subfolder not yet created |

SAB `movies` and `tv` category settings are relative to its completed-download folder. Both download clients use those exact categories. No remote-path mappings are configured in Sonarr/Radarr; shared `/data` paths make translation unnecessary. SAB's default/audio/software categories have blank overrides and therefore use the completed-download base.

## Ombi root selection

| Selection | Resolved app path | Ubuntu folder | Stored reference |
| --- | --- | --- | --- |
| Global movies | /data/Movies | /media/Media/Installarr-Clean-Test/Primary/Movies | Path stored in Ombi |
| Global TV | /data/TV | /media/Media/Installarr-Clean-Test/Primary/TV | Ombi root ID 1 |
| beanie08 movies | /data/Movies | /media/Media/Installarr-Clean-Test/Primary/Movies | 0 = inherit global |
| beanie08 TV | /data/TV | /media/Media/Installarr-Clean-Test/Primary/TV | 0 = inherit global |
| lenora8 movies | /data/lenoramovies | /media/Media/Installarr-Clean-Test/Primary/lenoramovies | ID 3 |
| lenora8 TV | /data/lenoratv | /media/Media/Installarr-Clean-Test/Primary/lenoratv | ID 2 |
| rebel739 movies | /data/jeremymovies | /media/Media/Installarr-Clean-Test/Primary/jeremymovies | ID 4 |
| rebel739 TV | /data/jeremytv | /media/Media/Installarr-Clean-Test/Primary/jeremytv | ID 3 |

Ombi does not mount the media folders. Its paths/IDs refer to the remote Arr applications. All listed IDs resolve to existing roots.

## Local application and supporting paths

| App | Ubuntu folder | Container path | Live setting / purpose | Access |
| --- | --- | --- | --- | --- |
| bazarr | /var/lib/installarr-setup/apps/bazarr | /config | Application configuration/database | RW |
| jackett | /var/lib/installarr-setup/apps/jackett | /config | Application configuration/database | RW |
| netbootxyz | /var/lib/installarr-setup/apps/netbootxyz | /config | Application configuration/database | RW |
| ombi | /var/lib/installarr-setup/apps/ombi | /config | Application configuration/database | RW |
| plex | /var/lib/installarr-setup/apps/plex | /config | Application configuration/database | RW |
| radarr | /var/lib/installarr-setup/apps/radarr | /config | Application configuration/database | RW |
| sabnzbd | /var/lib/installarr-setup/apps/sabnzbd | /config | Application configuration/database | RW |
| sonarr | /var/lib/installarr-setup/apps/sonarr | /config | Application configuration/database | RW |
| tautulli | /var/lib/installarr-setup/apps/tautulli | /config | Application configuration/database | RW |
| Plex | /var/lib/installarr-setup/apps/plex/transcode | /transcode | Live TranscoderTempDirectory = /transcode | RW |
| Tautulli | /var/lib/installarr-setup/apps/plex/Library/Application Support/Plex Media Server/Logs | /plexlogs | pms_logs_folder = /plexlogs | RO |
| netboot.xyz | /media/netbootxyz/assets | /assets | Network boot assets | RW |
| SABnzbd | /var/lib/installarr-setup/apps/sabnzbd/admin | /config/admin | admin_dir = admin (relative config path; directory exists) | RW |
| SABnzbd | /var/lib/installarr-setup/apps/sabnzbd/logs | /config/logs | log_dir = logs (relative config path; directory exists) | RW |
| Tautulli | /var/lib/installarr-setup/apps/tautulli/backups | /config/backups | backup_dir | RW |
| Tautulli | /var/lib/installarr-setup/apps/tautulli/cache | /config/cache | cache_dir | RW |
| Tautulli | /var/lib/installarr-setup/apps/tautulli/exports | /config/exports | export_dir | RW |
| Tautulli | /var/lib/installarr-setup/apps/tautulli/logs | /config/logs | log_dir | RW |
| Tautulli | /var/lib/installarr-setup/apps/tautulli/newsletters | /config/newsletters | newsletter_dir | RW |

Bazarr has empty TV/movie path-mapping lists and uses the current media directory for subtitles (`subfolder=current`). Sonarr, Radarr and Bazarr currently contain no tracked series/movies, so there are no per-title paths to compare yet. Jackett's current ServerConfig has no explicit directory/path override. No NZB watched folder, NZB backup folder or scripts folder is configured in SAB.

The installer settings also reserve `/var/lib/installarr-setup/backups`; this is not a media bind or an application backup location. Tautulli's application backup folder is its own `/config/backups`, as listed above.

## Complete Compose bind inventory

Includes private control-file paths, but never their contents. Every row below matches the running Docker bind and access mode.

| Service | Ubuntu source | Container destination | Access |
| --- | --- | --- | --- |
| bazarr | /var/lib/installarr-setup/apps/bazarr | /config | RW |
| bazarr | /media/Media/Installarr-Clean-Test/Primary | /data | RW |
| bazarr | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| bazarr | /var/lib/installarr-setup/project/bazarr.guard.sh | /installarr-storage-guard | RO |
| bazarr | /media/NAS/Installarr-Clean-Test/AdditionalMovies | /media-secondary | RW |
| jackett | /var/lib/installarr-setup/apps/jackett | /config | RW |
| jackett | /media/Media/Installarr-Clean-Test/Primary | /data | RW |
| jackett | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| jackett | /var/lib/installarr-setup/project/jackett.guard.sh | /installarr-storage-guard | RO |
| netbootxyz | /media/netbootxyz/assets | /assets | RW |
| netbootxyz | /var/lib/installarr-setup/apps/netbootxyz | /config | RW |
| netbootxyz | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| netbootxyz | /var/lib/installarr-setup/project/netbootxyz.guard.sh | /installarr-storage-guard | RO |
| ombi | /var/lib/installarr-setup/apps/ombi | /config | RW |
| ombi | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| ombi | /var/lib/installarr-setup/project/ombi.guard.sh | /installarr-storage-guard | RO |
| plex | /var/lib/installarr-setup/apps/plex | /config | RW |
| plex | /media/Media/Installarr-Clean-Test/Primary | /data | RO |
| plex | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| plex | /var/lib/installarr-setup/project/plex.guard.sh | /installarr-storage-guard | RO |
| plex | /media/NAS/Installarr-Clean-Test/AdditionalMovies | /media-secondary | RO |
| plex | /var/lib/installarr-setup/plex/plex-claim.txt | /run/installarr-plex-claim | RO |
| plex | /var/lib/installarr-setup/apps/plex/transcode | /transcode | RW |
| radarr | /var/lib/installarr-setup/apps/radarr | /config | RW |
| radarr | /media/Media/Installarr-Clean-Test/Primary | /data | RW |
| radarr | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| radarr | /var/lib/installarr-setup/project/radarr.guard.sh | /installarr-storage-guard | RO |
| radarr | /media/NAS/Installarr-Clean-Test/AdditionalMovies | /media-secondary | RW |
| sabnzbd | /var/lib/installarr-setup/apps/sabnzbd | /config | RW |
| sabnzbd | /media/Media/Installarr-Clean-Test/Primary | /data | RW |
| sabnzbd | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| sabnzbd | /var/lib/installarr-setup/project/sabnzbd.guard.sh | /installarr-storage-guard | RO |
| sonarr | /var/lib/installarr-setup/apps/sonarr | /config | RW |
| sonarr | /media/Media/Installarr-Clean-Test/Primary | /data | RW |
| sonarr | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| sonarr | /var/lib/installarr-setup/project/sonarr.guard.sh | /installarr-storage-guard | RO |
| tautulli | /var/lib/installarr-setup/apps/tautulli | /config | RW |
| tautulli | /var/lib/installarr-setup/project/auth-ready.txt | /installarr-auth-verified | RO |
| tautulli | /var/lib/installarr-setup/project/tautulli.guard.sh | /installarr-storage-guard | RO |
| tautulli | /var/lib/installarr-setup/apps/plex/Library/Application Support/Plex Media Server/Logs | /plexlogs | RO |

## Discrepancies and interpretation

- No difference between declared Compose binds and running mounts across all nine services.
- No mismatched Plex library, Arr root, Ombi global/family route, or SAB category paths found.
- Primary/secondary names denote separate folders in the same isolated NAS export for this test. A production deployment would use its separately authorized exports.
- Completed-download category directories `movies`/`tv` do not exist yet; the configured paths agree, and SAB creates them when used. This is not an observed path mismatch.
- Empty app inventories limit this audit to configured roots and mappings; there are no existing title-level paths to verify.
- This audit does not perform downloads, imports, file writes, remounts or restart/boot tests.

## Operator GUI follow-up and read-only verification

- `/media-secondary` is an installer-defined alias introduced by the separate media
  source adapter (compose.py, plex.py, arr.py), not an original reference alias.
  Its intended production host source is `/media/NAS/Movies`; current test source
  is the AdditionalMovies directory shown above. Original reference aliases include
  `/data/Movies-2` and `/movies-2`. No rename or production mount change was made.
- Both Radarr profiles match pinned quality ordering/cutoffs/custom-format scores:
  Remux + WEB1080p ID7/55pinned CFs, Remux + WEB2160p ID8/56pinned CFs. Sonarr
  WEB1080p ID7/37pinned CFs also matches. Separately, neither app has installer-applied
  quality-size definitions: profiles.py never calls qualitydefinition. Live Radarr
  HDTV/WEB1080p sizes are0/95/100(min/preferred/max), while pinned movie guidance has
  different quality-specific limits. Sonarr's varying sliders are factory defaults,
  not evidence of applied pinned quality sizes. Implement and test separately.
- Storage preparation currently creates completed/incomplete base folders but omits
  SAB's movies/tv category directories. This explains both operator-reported Arr
  Docker warnings. Fix by preparing those exact category children through existing
  verified-storage/service-UID adapters; no remote path mapping is needed.
- Ombi Plex settings readback: enabled, one server plex:32400, saved token present,
  owner username/password fields empty. Read-only remote-library POST using the
  saved server returned successful and all five intended libraries. The installer
  already automates this with connect_plex; GUI account-credential controls are not
  necessary for the existing direct server link. No owner password is collected.
- This follow-up changed only documentation. No app settings, files on NAS, bind
  paths, image/runtime snapshots or services were modified. Production remains
  outside the currently selected isolated test-storage scope.
