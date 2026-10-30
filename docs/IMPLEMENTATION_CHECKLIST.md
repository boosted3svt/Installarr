# Installarr completion checklist — 2026-10-30

Authoritative status: CURRENT_PROGRESS.md. Current settings: CURRENT_SETUP.md.
Exact evidence/failures: TEST_RESULTS.md. Remaining operator gates:
INTERACTIVE_TEST_QUEUE.md. Old nine-app fixtures and pre-wipe hosts are history.

## Completion estimate

About90% complete for the AGREED fresh Ubuntu reference-installer scope. This is
an engineering estimate, not a measured test-coverage percentage or release-ready
claim. Core provisioning and the selected seven-app clean installation work;
the remaining effort is boot/failure acceptance and final hardening/documentation.
Every app remains optional; a nine-app physical install is not required when the
operator selects seven. Do not count migration, new backends, SMB servers, PXE
clients or repeated ordinary media requests/playback as mandatory remaining work.

## Implemented and tested

- [x] Ubuntu20.04+ policy, Python3.8 compatibility, signed prerequisites/Docker
      staging and standard bridge/NAT, no-flag shell bootstrap and guided CLI.
- [x] Shared private admin credentials, hidden provider/family/Plex inputs,
      unattended advanced config, private checkpoints and resumable execution.
- [x] All nine apps optional, pinned images and non-root identities; netboot911:1001.
- [x] Local/NVMe/existing/NFS/SMB selection, optional separate downloads/secondary
      media, canonical per-role paths, exact source/type/health and service-UID checks.
- [x] NFS helpers before mount, protected/idempotent fstab changes, local DBs,
      preservation of unrelated mounts/media, startup guards and scoped supervision.
- [x] SAB completed categories, narrow app binds and generated Radarr/Sonarr→SAB
      download/import evidence, real Newshosting/NZBGeek provider tests.
- [x] Full pinned TRaSH profiles and separate quality-size limits; readback/reruns.
- [x] Plex claim/grouped libraries/read-only media, Bazarr English/OpenSubtitles.com,
      Ombi native family identities/roles/routes/private notification preferences,
      Tautulli Plex link, Jackett password auth and netboot HTTP/auth permissions.
- [x] Genuine family/operator identity requests, native imports and recovery,
      supplied/generated media recognition and playback have earlier scoped evidence.
- [x] Authenticated protected bootstrap before HTTP publication; real valid/invalid
      GUI authentication/API readback; all511render subsets and native Compose parses.
- [x] Explicit owned fresh-setup switch, stopped runtime refresh, backups/journal
      recovery; existing unrelated files/units/configuration refused/preserved.
- [x] Operator completed genuinely fresh Ubuntu24.04.5 installation with seven
      selected apps at192.168.1.51, deliberately different from the old10.70.0.99
      network. Saved bootstrap/published/automatic-start checks and live inventory pass.
- [x] Opt-in supervised media permission repair after healthy startup and every60s
      after completion; bounded/no-overlap workers, no UID ownership changes,
      scope/marker/mount guards and exclusions. Real NAS + late-addition repair pass.
- [x] Operator confirms CODA, Astro Boy and6Underground now appear in Plex after
      permission repair, without any further container restart.
- [x] Guided permission-repair opt-in and local enable/disable/status controls;
      real PTY save-only choice, unit safety/scheduling/permission tests.

## Required completion work

- [x] Publish current permission policy and refreshed docs; verify an unauthenticated
      fresh clone includes the new module, guide option and tests. See Git history
      and CURRENT_PROGRESS.md for the resulting publication savepoint (f8f54cc).
- [ ] Coordinate an actual reboot/reconnect of THIS completed installation and
      verify NFS mount ordering, enabled units, protected startup and app availability.
      No reboot has been authorized or performed by Codex for this new installation.
- [ ] Coordinate a scoped missing/unresponsive-storage acceptance test including
      startup refusal, no local fallback writes, bounded workers, stop/recovery and
      repair cancellation. Never shut down the shared NAS or blanket umount -a.
- [ ] Finish permission-policy hardening against large/changing directory trees,
      interrupted workers and server-denied group/chmod operations. Existing unit/
      bounded-worker tests and small real fixtures are evidence, not proof of every
      filesystem/NAS behavior. Keep limits and skipped/denied status visible.
- [ ] Final release audit: current guide/defaults/help, clean-clone packaging,
      credential exclusion, failure diagnostics and all remaining evidence/limitations
      agree. Fix any issues uncovered by the above physical acceptance tests.

## Explicit optional/deferred scope

- Ubuntu20.04/24.04 userspace suites are not full clean20.04/22.04 systemd/boot tests;
  record supported-platform evidence honestly. Focal uses an amd64 signed archive
  and is outside current upstream Docker OS support.
- Physical SMB fixture when selected, Jackett indexer choices when selected,
  DHCP/PXE client reachability, extra secondary sources and image/schema upgrades
  are separate optional scope. No new torrent downloader, proxy or auxiliary backend.
- No app-state migration/disaster recovery, encryption/export bundle, arbitrary
  reconfiguration or more ordinary application-user actions as release gates.
