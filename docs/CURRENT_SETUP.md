# Last selected setup — nonsecret reference, 2026-10-30

This records the operator's current choices for the next fresh Ubuntu24.04.5 test.
It is documentation, not a deployable config or a credential backup. The guide
generates new private settings, identities/checkpoints and application databases.
Never restore old /var/lib/installarr* state into the clean acceptance test.

## Selected apps and host

Plex, Radarr, Sonarr, SABnzbd, Bazarr, Ombi and Tautulli selected. Jackett and
netboot.xyz declined in the last run; every app remains optional in the guide.
Plex server name HomeNet-Test2; address10.70.0.99 (detect/confirm after reinstall);
timezone America/Chicago. Media service identity media2000:2000 is installer-managed.
The clean host must collect its shared administrator login locally; Plex uses its
own authorization. The original reference Compose is unnecessary.

## Exact selected storage

| Purpose | NFS source | Host mount/folder |
| --- | --- | --- |
| Primary | 192.168.1.103:/share/MD0_DATA/Public | /media/Media |
| Secondary movies | 192.168.1.102:/share/MD0_DATA/Public | Mount /media/Media-2; child media-movies-2 |

Both sources were verified mounted on the last host. No explicit NFS endpoint
overrides were selected. Do not substitute the isolated export or infer that any
mount survived reinstall. If the operator chooses an isolated test instead, use
the separate recipe in FRESH_HOST_CODEX_HANDOFF.md, with its exact transport values.
No extra exports, production sibling inspections, media moves or cleanup are implied.

| Role | Host folder | Container folder |
| --- | --- | --- |
| Movies | /media/Media/media-movies | /data/media-movies |
| Lenora movies | /media/Media/media-lenoramovies | /data/media-lenoramovies |
| Jeremy movies | /media/Media/media-jeremymovies | /data/media-jeremymovies |
| TV | /media/Media/media-tv | /data/media-tv |
| Lenora TV | /media/Media/media-lenoratv | /data/media-lenoratv |
| Jeremy TV | /media/Media/media-jeremytv | /data/media-jeremytv |
| Sports | /media/Media/media-Sports | /data/media-Sports |
| Standup | /media/Media/media-Standup | /data/media-Standup |
| Secondary movies | /media/Media-2/media-movies-2 | /data/media-movies-2 |
| Finished downloads | /media/Media/finished-downloads | /data/finished-downloads |
| Unfinished downloads | /media/Media/unfinished-downloads | /data/unfinished-downloads |

No separate download filesystem selected. SAB movies/tv completed-category children
are prepared and verified. Strict scoped binds may require copy imports instead
of hardlinks/instant moves. Plex media is read-only; Radarr/Bazarr can write their
configured movie locations including secondary; Sonarr can write TV locations.
Databases/configs remain local. Preserve existing files/case/ownership; no recursive
NAS chown or media migration. New standardized folders were intentionally empty.

## App defaults and family

- Plex Movies combines primary/Lenora/Jeremy/secondary movies; TV Shows combines
  all three TV folders; Sports and Standup use their matching roles. Music and
  removed/low-resolution libraries stay excluded without deleting their files.
- Radarr full pinned Remux + WEB1080p preferred, separate manual2160p option;
  Sonarr WEB1080p. Pinned quality sizes configured separately.
- Newshosting100connections, strictTLS563; NZBGeek direct Newznab.
- Bazarr OpenSubtitles.com only; standard English, not forced/hearing-impaired.
- Native Plex accounts lenora8/rebel739/beanie08; Lenora/Jeremy1080p roots/profiles,
  Beanie global inheritance/PowerUser; all autoapprove movie/TV. No local lookalikes.
- Optional private Discord IDs for rebel739/beanie08; lenora8 deliberately blank.
  Notification sending stays disabled. Numbers/credentials are not in this file;
  collect locally again on the clean machine, never in chat.

## Last host deployment and shutdown reference

Selected setup /var/lib/installarr-setup/installations/setup-c2c7141a879e;
live Compose project/compose.json, app configs apps/, state state/state.json.
Unit installarr-family-c2c7141a879e.service active/enabled, bootstrap stopped.
Both family-9ad2bb7ce113 and family-media retired/stopped. These names are historical
after the wipe; derive names from the new active-setup.json and installation.json.

If manually removing a surviving deployment, stop/disable its live and bootstrap
systemd supervisors BEFORE Compose down, otherwise supervision can recreate apps.
Use docker compose --project-name with the exact project's compose.json; JSON
Compose is intentional. Never global docker prune or umount -a for scoped cleanup.
Compose down preserves host bind-mounted app databases and NAS media. No shutdown
or cleanup is performed by this publication task.
