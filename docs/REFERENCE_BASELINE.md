# Reference-server container baseline

Source: `/home/htpc/Installarr/reference_compose.yaml`, supplied by the operator.
It is a service fragment rather than a complete Compose document. The source is
kept out of Git because it may contain credentials. Do not inspect the actual host
paths or production services named in it. Only reproduce/standardize the supplied
configuration within authorized test storage.

## Services and published ports

| Service | Reference image | Host → container ports | Config directory |
| --- | --- | --- | --- |
| SABnzbd | linuxserver/sabnzbd | 8090→8080; 9090→9090 | sabnzbd |
| Bazarr | ghcr.io/linuxserver/bazarr | 6767→6767 | bazarr |
| Plex | plexinc/pms-docker:${PMSTAG} | 32400,3005,8324,32469 TCP; 32410,32412,32413,32414 UDP | plex |
| Sonarr | linuxserver/sonarr | 8989→8989 | sonarr |
| Radarr | linuxserver/radarr | 7878→7878 | radarr |
| Jackett | linuxserver/jackett | 9117→9117 | jackett |
| plexpy / Tautulli | linuxserver/tautulli | 8181→8181 | plexpy |
| Ombi | linuxserver/ombi:latest | 3579→3579 | ombi |
| netbootxyz | ghcr.io/netbootxyz/netbootxyz | 3250→3000; 7171→80; 69→69 UDP | netbootxyz |

All reference services use network `web`; the operator confirmed a standard bridge
and approved Docker bridge/NAT/firewall changes.
Do not substitute shared-loopback, host networking, a custom GUI relay, or new
auxiliary services as the normal deployment design. Existing isolated experiments
remain tests only. The current reference proof of concept uses the confirmed bridge.

Reference restart policy is unless-stopped. Installer must preserve its requested
resumability while meeting the separately explicit fail-closed mount requirement;
Docker health status alone is insufficient and unguarded restart is not acceptable.

## Shared storage roles

Primary reference media parent is `/media/Media`. Its supplied child directories:

- TV, Movies, downloads, incomplete-downloads.
- lenoratv, lenoramovies, jeremytv, jeremymovies.
- Sports, StandUp, Music, Disney, Only_Heather.
- yt-videos, low-res-TV, low-res-Movies, tubesync_downloads/video.

A secondary movie source is `/media/NAS/Movies`. Netboot assets are separately at
`/media/netbootxyz/assets`. These are **reference path names only**, not authorized
storage locations for this test host. Actual experiments remain under the confirmed
`/media/installarr` export and private disposable local application directories.

The reference has inconsistent in-container aliases between apps (for example
/tv, /data/tvshows, /movies, /data/movies, /data/Movies-2, /movies-2), and family paths
vary in capitalization. Approved work is one shared directory map across apps while
preserving existing host filenames/case. Do not copy, rename or delete the supplied
TV/movie examples. Keep config databases local.

Jackett's /downloads maps to Torrents/Completed; this does not make Jackett a torrent
download client. No torrent client was included in the reference and none should be
added without permission. Tautulli reads Plex logs read-only and depends on Plex.

## Approved differences / unresolved choices

- Standardize non-root identities and shared GUI credentials where supported;
  Plex retains its own authorization and netboot requires nbxyz 911:1001.
- Pin tested image versions from the reference image families. Do not substitute
  another Plex/netboot provider. Registry aliases for the same LinuxServer images
  must be explained, not mistaken for additional services.
- Standardize quality profiles using full versioned TRaSH profiles, not invented
  representative subsets; the Compose fragment does not include existing profiles.
- Standardize shared container paths consistently from one storage map.
- Preserve Plex ALLOWED_NETWORKS preset, America/Chicago default and optional
  family behavior already specified in AGENTS.md.
- Do not assume all listed Plex libraries must be imported: selection remains an
  operator choice. Do not invent media organization/import-management features.

## Current gaps revealed by comparison

- All nine reference apps now have pinned/protected bootstrap adapters. Ombi integrations/family behavior and combined acceptance remain open.
- Radarr/SAB now run on the standard reference bridge with authenticated ports
  7878 and 8090. Remaining integration and clean-OS combined acceptance gates are unfinished.
- Legacy separate binds demonstrated EXDEV. Explicit shared data_root now passed
  real same-inode hardlinks and nested wrong-mount refusal; reference apply requires
  this map. Do not bind broader host ancestors.
- Secondary and family/library path roles are not fully modeled yet.
- Compose alone cannot supply quality profiles, Plex claims or family account IDs;
  resolve these through approved configuration/secure authorization, not production
  inspection or fabricated defaults.

Operator update: HTTP GUI ports only. Ignore optional HTTPS port mappings and
HTTPS application settings; outbound HTTPS to official APIs/registries remains needed.

Current implementation includes protected pinned bootstrap for all nine apps,
full profiles and real Plex/Tautulli integration/playback. Ombi links/family
behavior, separate secondary-source support, clean-OS combined acceptance and an
approved reboot remain open. See the final operator interpretation below.

## Final operator library/profile interpretation (supersedes folder guesses)

The Compose fragment describes mounts, not a one-to-one library list. Operator
clarified and GUI-tested the intended grouping; use these defaults:

| Library | Source-folder roles beneath the media map |
| --- | --- |
| Movies | Movies, Movies-2, jeremymovies, lenoramovies |
| TV | TV, lenoratv, jeremytv |
| sports | sports |
| StandUp | StandUp |
| Music | Music |

Names match for sports/StandUp; sport/comedy aliases were explicitly rejected.
Do not create low-resolution libraries or include either low-res folder. Disney,
Only Heather, YouTube Videos and TubeSync Videos are explicitly removed from all
installer runs. Their files are preserved; library metadata is removed separately.
The original fragment's path spellings above remain source evidence, not an
instruction to create every mount as a separate Plex library.

Current test source is solely the verified /media/installarr export. Movies-2 is
an empty test location; the production secondary movie filesystem is neither
supplied nor inspected, and separate-source provisioning remains open.

Movie profiles: full pinned Remux + WEB1080p preferred, Remux + WEB2160p available
for manual upgrades; TV WEB-1080p. Full profile reference apply/readback/restarts
passed. Plex/Tautulli claim, integration and GUI movie/episode playback passed.
Ombi and netboot now have tested protected published bootstrap adapters; Ombi
family/integrations and whole clean-OS deployment acceptance remain open. Exact
current units/configs and image pins are in CURRENT_PROGRESS.md/TEST_RESULTS.md.


## Confirmed production NFS defaults

Operator supplied the following via read-only findmnt output:

| NFS source | Local mount | Media role |
| --- | --- | --- |
| 192.168.1.103:/share/MD0_DATA/Public | /media/Media | TV, family movie folders, downloads, primary media |
| 192.168.1.102:/share/MD0_DATA/Public | /media/NAS | Additional movies at /media/NAS/Movies |

The guided fresh install offers these editable defaults and prepares both NFS
mounts before starting dependent programs. This is not authorization to mount or
inspect the production exports on the current test host. Physical experiments
continue only in 192.168.1.102:/share/MD0_DATA/Public/installarr at /media/installarr.
netboot assets default to /media/netbootxyz/assets on the local host unless the
operator selects an already connected different location.

The reference secondary movie path is shared with Radarr/Bazarr as writable and
Plex as read-only. The new secondary_media_read_only=false setting enables managed
writable preparation/markers, UID write probes, mount guards and the additional
Radarr API root. Default true retains earlier explicit read-only source behavior.
The normal fresh guide sets false, reproducing the reference app access pattern.
