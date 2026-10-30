# Installarr

A guided installer for a fresh Ubuntu media server. Start with Ubuntu, OpenSSH
and an account that can use `sudo`; Installarr guides you through the rest.

**Status:** the earlier combined nine-app deployment passes. The standardized
storage layout passes physical Radarr/SAB and Sonarr/SAB download/import tests,
local-NVMe SAB tests and Plex read-only bind checks. Its full production run and
reboot acceptance remain pending.

## Start here

Connect to your Ubuntu server with SSH and paste these lines:

```sh
sudo apt-get update
sudo apt-get install -y git ca-certificates
git clone https://github.com/boosted3svt/Installarr.git
cd Installarr
./installarr.sh
```

The launcher installs its small Ubuntu prerequisites if needed, then opens the
setup guide. After package installation, the command `installarr` opens the same
guide. Neither entry point needs flags or variables.

The guide walks through:

1. Choosing programs, with a short explanation of each.
2. Choosing local disk/NVMe, NAS/NFS or already mounted storage, then each media/download folder.
3. Reviewing your choices and confirming installation.
4. Choosing one shared administrator login and entering provider account details.
5. Preparing Ubuntu, storage and Docker.
6. Authorizing Plex through its website on your phone or another computer.
7. Starting the containers and configuring their API connections, profiles and family settings.
8. Offering automatic startup when the computer turns on.

Press Enter to accept a suggested answer. Installation starts only after you
confirm it. Choices and private account details are saved on that installed
computer so the same guide can continue an interrupted setup.

For an existing saved test installation, answer **no** to continuing it, then
**yes** to creating a fresh installation to select the new folder layout. The
previous databases/settings remain preserved. On installation confirmation, only
the verified prior owned deployment is stopped; conflicting owned mounts/fstab
entries are replaced with private backups. Unrelated mounts/files are refused.
Private administrator/provider/family inputs are reused. The fresh Plex instance
uses a new database and needs its own private claim; the old claimed database is
preserved. No existing media is moved or renamed.

## Account details

Each **clean installation prompts for the credentials it needs**. There is no
saved file to keep or copy from an old server.

Have your administrator-login choice, Newshosting username/password, NZBGeek API
key and OpenSubtitles.com username/password available if you select those services.
Plex uses its own browser authorization. Optional family Discord account numbers
are entered privately when prompted; press Enter to leave one blank.

Passwords, API keys and Discord IDs are kept privately on the installed computer,
separately from ordinary settings and Git. A new, clean computer asks for them again.
The original reference Compose file is not needed: Installarr generates Compose
and connects the programs through their APIs.

## Programs and reference defaults

All nine programs are offered by default; each can be skipped:

- Plex — watch movies and TV shows.
- Sonarr and Radarr — manage TV and movies.
- SABnzbd — download using a Usenet subscription.
- Bazarr — subtitles through OpenSubtitles.com, with standard English defaults.
- Ombi — family requests and preferences.
- Tautulli — Plex activity.
- Jackett — additional indexers; no torrent downloader is installed.
- netboot.xyz — network-boot files and interface. DHCP/PXE network setup is separate.

The editable NFS defaults reproduce the supplied reference:

| NAS source | Connected folder |
| --- | --- |
| `192.168.1.103:/share/MD0_DATA/Public` | `/media/Media` |
| `192.168.1.102:/share/MD0_DATA/Public` | `/media/Media-2` |
| `192.168.1.102:/share/MD0_DATA/netbootxyz` | `/media/netbootxyz` |

Additional movies use `/media/Media-2/media-movies-2`. Network-boot assets default to
`/media/netbootxyz/assets`. Application databases stay on the local computer.
Local-only users choose their own existing filesystem and skip NFS provisioning.
NAS connection-port overrides are available when RPC discovery cannot reach a
server. An absent selected NAS or separate local drive never becomes OS-disk data
storage automatically.

The primary media root defaults to `/media/Media`, with editable children:
`media-movies`, `media-lenoramovies`, `media-jeremymovies`, `media-tv`,
`media-lenoratv`, `media-jeremytv`, `media-Sports` and `media-Standup`.
Downloads use `unfinished-downloads` and `finished-downloads`, including prepared
`finished-downloads/movies` and `finished-downloads/tv` categories. The same
`/data/<role-folder>` paths are used in every relevant container and app.

Movies prefer the full pinned TRaSH **Remux + WEB 1080p** profile, with a separate
**2160p** profile available for manual upgrades. TV uses **WEB-1080p**.

Plex groups the four movie folders into Movies, the three TV folders into TV Shows,
and adds Sports and Standup. Music is excluded from new setups, with files preserved.
The removed and low-resolution collections remain excluded.
The reference family option prestages genuine Plex users:

- `lenora8`: Lenora movie/TV folders and 1080p profiles.
- `rebel739`: Jeremy movie/TV folders and 1080p profiles.
- `beanie08`: global folders/profiles and PowerUser.

All three receive automatic movie/TV approval. Supplied Discord IDs go into their
Ombi notification preferences; notification sending remains disabled. Family Plex
passwords are never requested.

## Storage and verification

Installarr checks mount identity and application-account access before writes,
uses local application databases, and preserves existing media and path case.
Per-app binds restrict SAB to download folders, Radarr to finished downloads/movie/
Sports/Standup folders, and Sonarr to finished downloads/TV folders. Plex receives
only read-only media binds; Bazarr can write subtitles beside managed media.
Local Plex configuration/transcoding remains writable. Unavailable required
storage prevents startup and triggers owned-bundle shutdown. Narrow separate
binds can require copy-then-delete imports instead of instant moves/hardlinks.
The installer verifies actual category directories and access inside containers
before declaring success. TRaSH quality-size limits are configured separately
from the full pinned profiles and custom-format scores.

The dated or `Installarr-*` folders from development experiments are not created
by normal installation. The developer scripts under `tools/` are separate tests.

Current evidence includes a real nine-app deployment, authenticated HTTP checks,
API integrations, complete pinned profiles and family-preference readback. The
244-test suite passes on the host and from installed wheels in Ubuntu20.04 and
24.04 userspaces.
Those userspace tests do not replace the pending full clean-host/boot test.
Ubuntu20.04 compatibility uses a pinned archived amd64 Docker package set; details
and remaining acceptance limits are in the developer documentation.

## Development

For optional Codex assistance after wiping the test machine, use the
[post-wipe Codex handoff](docs/FRESH_HOST_CODEX_HANDOFF.md). Codex runs directly in
the SSH terminal; no tmux is part of the operator's workflow.

- [Current checkpoint](docs/CURRENT_PROGRESS.md)
- [Last selected nonsecret setup](docs/CURRENT_SETUP.md)
- [Installation details](docs/INSTALLER_RUNBOOK.md)
- [Test evidence](docs/TEST_RESULTS.md)
- [Remaining acceptance](docs/INTERACTIVE_TEST_QUEUE.md)
- [Advanced/historical commands](docs/DEVELOPER_COMMAND_REFERENCE.md)

Run the suite with `python3 -m unittest discover -s tests -v`.
The bundled TRaSH snapshot includes its upstream license and checksum manifest.
