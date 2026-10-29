# Installarr

A guided installer for a fresh Ubuntu media server. Start with Ubuntu, OpenSSH
and an account that can use `sudo`; Installarr guides you through the rest.

**Status:** the combined nine-app deployment and API configuration tests pass.
A full clean-Ubuntu/systemd installation and reboot acceptance test are still pending.

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
2. Connecting your NAS and choosing media folders.
3. Reviewing your choices and confirming installation.
4. Choosing one shared administrator login and entering provider account details.
5. Preparing Ubuntu, storage and Docker.
6. Authorizing Plex through its website on your phone or another computer.
7. Starting the containers and configuring their API connections, profiles and family settings.
8. Offering automatic startup when the computer turns on.

Press Enter to accept a suggested answer. Installation starts only after you
confirm it. Choices and private account details are saved on that installed
computer so the same guide can continue an interrupted setup.

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
| `192.168.1.102:/share/MD0_DATA/Public` | `/media/NAS` |

Additional movies use `/media/NAS/Movies`. Network-boot assets default to
`/media/netbootxyz/assets`. Application databases stay on the local computer.

Movies prefer the full pinned TRaSH **Remux + WEB 1080p** profile, with a separate
**2160p** profile available for manual upgrades. TV uses **WEB-1080p**.

Plex groups multiple folders into one Movies library and one TV library, alongside
sports, StandUp and Music. The removed and low-resolution collections are excluded.
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
Plex media access is read-only; Radarr/Bazarr share the writable additional movie
folder. Unavailable storage prevents dependent containers from starting normally.

The dated or `Installarr-*` folders from development experiments are not created
by normal installation. The developer scripts under `tools/` are separate tests.

Current evidence includes a real nine-app deployment, authenticated HTTP checks,
API integrations, complete pinned profiles and family-preference readback. The
217-test suite also passes from installed wheels in Ubuntu20.04 and24.04 userspaces.
Those userspace tests do not replace the pending full clean-host/boot test.
Ubuntu20.04 compatibility uses a pinned archived amd64 Docker package set; details
and remaining acceptance limits are in the developer documentation.

## Development

- [Current checkpoint](docs/CURRENT_PROGRESS.md)
- [Installation details](docs/INSTALLER_RUNBOOK.md)
- [Test evidence](docs/TEST_RESULTS.md)
- [Remaining acceptance](docs/INTERACTIVE_TEST_QUEUE.md)
- [Advanced/historical commands](docs/DEVELOPER_COMMAND_REFERENCE.md)

Run the suite with `python3 -m unittest discover -s tests -v`.
The bundled TRaSH snapshot includes its upstream license and checksum manifest.
