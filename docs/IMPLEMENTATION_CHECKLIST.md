# Installarr implementation checklist

## Current acceptance target — 2026-10-30

- [x] Standardized seven-app operator run HomeNet-Test2 completed protected bootstrap,
      published GUI checks and automatic-startup selection; saved ready state observed.
- [x] Arr root requests have bounded60s deadlines and safe diagnostics;244host tests pass.
- [x] Current settings/host ownership and recent failure evidence recorded in
      CURRENT_SETUP.md and CURRENT_PROGRESS.md; old live-stack entries below are historical.
- [x] Publish current implementation and verify a fresh public clone (e1fed73;244tests).
- [ ] Operator-led Ubuntu24.04.5 reinstall, then complete no-flag fresh installation.
- [ ] Separately coordinated reboot/reconnect and absent-storage boot acceptance.

The operator backs up/restores Codex history only; no old app DBs or installer
state will be restored into this test. Publication does not authorize a wipe,
reboot, NAS cleanup or broader host changes.

## Latest standardized-storage implementation (2026-10-29)

- [x] Operator approved empty standardized media-* folders, no new Music library,
      and dedicated netboot export's assets child. Latest names supersede older
      sports/StandUp/TV conventions below for new guided installations.
- [x] Explicit local/NVMe/NAS/existing storage, editable per-role folders and mixed
      download storage, with exact checks and no absent-drive OS-disk fallback.
- [x] Strict per-app binds, shared canonical paths, four-library Plex policy,
      all relevant Arr roots and dynamic family routes.
- [x] SAB completed-category directories prepared and verified inside containers;
      scoped access/read-only checks and relevant Arr health gate.
- [x] Separate pinned movie/series quality-size adapter, conflict preservation,
      real API readback/restart/rerun on both Arr apps.
- [x] Real generated Radarr/SAB and Sonarr/SAB downloads/imports under narrow binds;
      hashes/ownership, stable reruns and forbidden paths checked.
- [x] Physical local-only SAB, absent-source pre-write refusal, Plex guarded bind
      and actual read-only write denial (no duplicate Plex server started).
- [x]1022native Compose configurations and242tests in host/root and installed-wheel
      Ubuntu20.04/24.04 userspaces. Plain real PTY local-only save/cancel passed.
- [x] Explicit fresh-setup selection preserves prior DBs/settings, reuses private
      inputs and supports bounded owned mount replacement with private backups.
      Root fixture tests cover fstab preservation/idempotence; actual live switch
      has not been performed by Codex. Fresh Plex DB needs new owner claim.
- [ ] Operator-run standardized production nine-app install and UI acceptance.
- [ ] Coordinated reboot/absent-storage boot acceptance; no reboot authorized.

Resumed2026-10-28 for autonomous work during operator absence; see AUTONOMOUS_WORK_PLAN.md and INTERACTIVE_TEST_QUEUE.md. Current resume commands and live service ownership are in
CURRENT_PROGRESS.md. TEST_RESULTS.md retains chronological evidence, including
failed experiments. A milestone is a progress update, not a reason to stop.

## Scope and operator decisions

- [x] Supplied reference Compose located and redacted baseline documented; source stays ignored.
- [x] Standard web bridge/Docker NAT authorized and tested; no new deployment backends.
- [x] HTTP GUI mappings only; outbound HTTPS to official services remains needed.
- [x] Final movie profiles: Remux + WEB1080p preferred, separate manual2160p option.
- [x] Plex uses multiple folder locations per Movies/TV library.
- [x] Final library/folder conventions: sports→sports, StandUp→StandUp, Music→Music.
- [x] Exclude low-res-TV/low-res-Movies and remove Disney, Only Heather,
      YouTube Videos and TubeSync Videos library entries in installer runs.
- [x] Generic separate read-only Movies-2 source map, UID reads, write refusal and marker supervision.
- [ ] Actual production secondary source details and claimed Plex acceptance (interaction queue I-03/I-07).
- [x] Approved standardizations/normal deployment audit mapped in REQUIREMENTS_ACCEPTANCE_MATRIX.md and INSTALLER_RUNBOOK.md.

## Provisioning and storage foundation

- [x] CLI inventory, private nonsecret JSON, unattended configuration and resume checkpoints.
- [x] Ubuntu20.04+ policy/Python3.8-compatible grammar; physical testing on22.04.
- [x] Non-root accounts, collisions, interrupted creation, private credentials and hidden input.
- [x] nbxyz reserved UID911/GID1001; real image permissions/write test passed.
- [x] Signed NFS/CIFS prerequisite adapter; nfs-common before mount attempts.
- [x] Mount source/type/sentinel assertions and separate service-UID write/fsync probes.
- [x] Existing fstab/mount conflict reconciliation, backups and duplicate-free reruns.
- [x] Fresh NFS mount/persistence in private namespace; live fstab preserved.
- [x] Verified directory creation, preserved ownership/files/case; no recursive NAS-library chown.
- [x] Shared data_root and real same-inode hardlink/nested wrong-mount refusal.
- [x] Container pre-init gate, mount-loss supervision, crash fallback and scoped recovery.
- [x] Multiple service identities use separate bounded health workers without fork-orphan leaks.
- [x] Foreground storage anchors/probes/directory/mount workers have durable deadlines and cross-CLI unreaped-group refusal; real outage still gated.
- [x] Signed Docker staging and owned standard-engine activation; live reruns do not remask/restart it.
- [x] Actual Python unit runtime on official Ubuntu20.04/Python3.8 and24.04/Python3.12 userspace.
- [ ] Clean supported Ubuntu combined install/systemd acceptance.
- [ ] Real NAS outage and explicitly approved reboot/boot safety acceptance.
- [x] Optional SMB hidden/private-file credential collector and menu integration (synthetic tests only).
- [ ] Optional SMB physical fixture/share/credentials — I-06 deferred; no Samba server installed.

## Application acceptance

- [x] Sonarr/Radarr: pinned images, real Forms auth/API distinction, roots, local DBs,
      UID2000, restart/reruns and supplied file recognition.
- [x] SABnzbd: pinned image, real GUI auth, categories, restart and generated NNTP bytes/ownership.
- [x] Sonarr/SAB and Radarr/SAB connection tests, wrong-key refusal and persistence.
- [x] Full pinned TRaSH snapshots/default groups, dynamic schemas/IDs, readback,
      restart, HD/UHD coexistence and actual reference apply/rerun.
- [x] Bazarr: pinned image, shared GUI auth, actual Sonarr/Radarr version lookups,
      database ownership, published HTTP and apply/reruns.
- [x] Jackett: pinned image, verified password-only GUI, published HTTP and restart/reruns.
- [x] Private provider collector, reference choices/apply wiring, Newshosting TLS100 and NZBGeek test-before-save adapters.
- [x] Four Bazarr provider settings/readback/restart with empty test library.
- [x] Real Newshosting100 TLS/auth, NZBGeek in both Arr apps, full Radarr/SAB and Sonarr/SAB provider apply/reruns.
- [x] Actual official SAB100MB NNTP test transfer to NAS,2000:2000 files/hashes.
- [x] Native OpenSubtitles.com account/search/download to fixture NAS with fsync/readback.
- [x] English standard future movie/TV defaults, dynamic profile ID, restart/rerun and conflict preservation.
- [x] Registered Bazarr sync/index/wanted jobs downloaded beside generated media; profile/subtitle persisted and video unchanged.
- [x] Operator removed Yify/Supersubtitles/TVSubtitles; installer supports OpenSubtitles.com only.
- [ ] Jackett-specific indexers if selected; no torrent client provided.
- [x] Plex official baked/versioned image, UID2000/local DB, private claim file,
      account claim, host valid/invalid/anonymous token checks and allowed-network readback.
- [x] Plex name, exact multi-folder library readback, stable parent IDs and read-only NAS.
- [x] Operator confirmed actual movie and TV-episode GUI playback.
- [x] Tautulli pin/auth, actual Plex identity/version lookup, read-only Plex logs,
      local DB, stopped config backup and restart/apply persistence.
- [x] Ombi pin, shared local Admin/bootstrap closure, real bearer login/rejection,
      SQLite ownership, host publication gate and published HTTP/apply rerun.
- [x] Ombi actual Sonarr/Radarr remote links and movie/TV dispatch to preferred profiles/roots; restart/reruns.
- [x] Ombi Plex remote library link/readback/restart persistence.
- [x] Ombi movie/show/episode availability sync with matched Plex metadata; restart persistence.
- [x] Published Ombi/Radarr integration apply/rerun.
- [ ] Full combined family preset apply.
- [x] Operator-confirmed native Plex browser sign-in and genuine identity-attributed requests.
- [x] Native selective family Plex import, dynamic user/profile/root IDs, approvals,
      Beanie PowerUser and disabled Discord preferences.
- [x] Administrator on-behalf movie/TV per-user routing and restart persistence.
- [x] Genuine non-Admin Plex requests exercising family-equivalent presets with the operator’s own account.
- [x] Physical SIGKILL recovery of temporary native import settings, restart and stable IDs.
- [x] netboot.xyz pinned image/menus, existing-image Nginx shared auth for GUI and
      Socket.IO,911:1001 writes, restart and published HTTP/reference apply rerun.
- [x] Explicit netboot asset storage model, local physical apply/write/restart, reserved identity and mount guard.
- [x] NFS assets marker-loss/recovery and directory UID audit. DHCP/PXE reachability is out of scope.

## Installer completion

- [x] Reference apply protected bootstrap and published real HTTP checks for all nine app adapters.
- [x] Render all511 nonempty optional-app combinations with publication/ownership/bind scope assertions.
- [x] Additional dependency-less Bazarr/Jackett and Tautulli/Ombi physical apply/reruns; no inferred apps.
- [ ] Combined fresh-host acceptance remains I-04/I-07;511 physical full stacks are not required.
- [x] Grouped Plex library/location selection/editing and application integration/input discovery.
- [x] Terminal navigation plus secure GUI/provider/Plex inputs; real PTY plan/exit. Human usability remains I-08.
- [x] Explicit stopped-reference runtime refresh, original-byte backups, crash rollback and physical apply rerun.
- [x] Fresh-host/signature/runtime/failure/readiness audit; explicit updates preserve immutable saved artifacts.
- [ ] Clean OS/image migration acceptance remains separately scoped; fresh provisioning first.
- [x] Native requests/family routing and controlled generated Radarr/Sonarr grab→NNTP→normal import/restart evidence; real provider connectivity/transfer separately passed.
- [ ] Single combined family/provider deployment acceptance remains I-04/I-07.
- [x] Requirements-to-evidence matrix classifies every handoff requirement and deferred interaction.
- [x] Current-code wheel/userspace198-test checks, physical storage reruns and exact retained-service checkpoint refreshed; full clean-host gates remain above.

## Live service rule and input gates

Leave Radarr/SAB unit installarr-poc-http-d29db77d and Plex/Tautulli unit
installarr-plex-standard-test available. All older Plex units reuse the same DBs
and must stay stopped. See CURRENT_PROGRESS.md for their exact current paths.

No reboot is authorized. Production apps, sibling NAS shares, host IP/DNS/manual
routes, SSH, VLANs, partitions and unrelated firewall settings remain protected.
Use disposable single apps/pairs, not a second full stack. Continue independent
work when a provider/family credential is missing; never invent a tracker/backend
or create local lookalikes for Plex family users. Do not stop at milestones.
