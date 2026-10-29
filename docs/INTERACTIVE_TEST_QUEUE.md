# Remaining fresh-install acceptance

This replaces the earlier eight-item interaction list after the operator clarified
scope: fresh provisioning, account setup, storage, profiles and API integration.
Do not request ordinary app-user actions or additional family credentials.

## Completed operator input and combined acceptance

- Plex library status and supplied-media playback confirmed on earlier retained server.
- Separate Radarr1080p/2160p profiles confirmed in GUI.
- Initial terminal menu confirmed; operator required a simpler default flow. New
  no-flag guide is implemented and passed actual PTY save-only/no-provisioning test.
- Production sources supplied:192.168.1.103:/share/MD0_DATA/Public -> /media/Media;
  192.168.1.102:/share/MD0_DATA/Public -> /media/NAS. Additional movies /media/NAS/Movies.
- Family Discord targets supplied privately for rebel739/beanie08. lenora8 deliberately
  blank. All roles/roots/profile overrides and these notification targets passed
  combined fresh-stack API readback. Notifications remain disabled.
- Operator authorized replacing the previous3test services with the fresh9-app stack.
  Both new Plex claim prompts completed. Current claimed server needs no new claim.
- All9-app bootstrap, publication/auth, API links, profiles and family preferences
  passed; final rerun passed. Cold empty Plex library creation also passed after
  fixing explicit startup readiness and bounded Plex request deadlines.
- Ordinary unmount/remount of a separate test mount passed fail-closed stop/recovery
  without local fallback writes. No shared NAS shutdown required/performed.

## Current services and exact reproduction

Current: installarr-freshcheck-aaabe264-v2.service active, boot-disabled,9containers.
Config/state/result/live snapshot under /var/tmp/installarr-fresh-acceptance-vhydzwl1:
config-v2.json, state-v2, result.json, live-checkpoint.json.
Bootstrap unit is stopped. Older baseline3units must stay stopped while current
stack uses their ports. See CURRENT_PROGRESS.md for exact rollback and private-store
paths. Do not rerun superseded immutable configs or recreate an already-claimed
identity concurrently. No IDs, passwords, keys or claims belong in this document.

## Remaining actions requiring operator involvement

1. **Clean Ubuntu target:** provide a genuinely fresh Ubuntu/OpenSSH host or VM,
   or explicitly arrange an operator-led reinstall. Do not wipe/repartition this
   machine or alter SSH/VLAN to obtain one. Test the published clone-and-launch
   guide there, using approved test storage unless production deployment is expressly
   authorized. Production NFS values are defaults, not permission to inspect/mount
   production during current physical experiments.
2. **Boot acceptance:** after the new installation is configured and automatic startup
   selected, coordinate a reboot/reconnect test. No reboot is authorized/performed on
   the current test host. Its units remain disabled. Test absent-mount protection
   and recovery through boot without changing production NAS availability.

The tested implementation is published on boosted3svt/Installarr main at
bc9017a4eec41b8bd514901b0067accbdfffdd2c. The existing GitHub connection already
had permission; no new login/token was needed. A fresh public clone passed the
launcher and217-test suite. No files or credentials need to be transferred for the
normal fresh-install flow: enter the requested account details at its prompts.

## Explicitly outside the required flow

No credential exports, encrypted setup bundles, retained files to transfer between
installs, app-database migration/disaster recovery, new torrent backends, physical
SMB server, family-member passwords or repeated movie-request/playback tests.
Each clean install prompts for credentials and optional Discord IDs. Reference
paths/images/profiles/roles ship in code; original reference Compose stays out of Git
and is unnecessary at runtime. Optional future scopes do not block this fresh-NFS
installer acceptance.
