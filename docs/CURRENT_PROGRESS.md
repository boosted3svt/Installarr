# Current Installarr checkpoint — 2026-10-30

## Current host, after the completed reinstall

Operator reinstalled Ubuntu24.04.5, restored this Codex conversation and completed
./installarr.sh from published source with seven apps. Host/user/checkout are now
192.168.1.51/23, plex, /home/plex/Installarr; hostname plex; Plex name HTPC-210.
The address was deliberately changed from the old10.70.0.99 network to test fresh
address handling. Saved config, Docker bindings and completed published checks
use192.168.1.51. No IP/DNS/routes/VLAN/SSH changes made by Codex.

- Current owned unit installarr-family-media.service active/enabled; seven apps
  Plex/Radarr/Sonarr/SABnzbd/Bazarr/Ombi/Tautulli running. Bootstrap inactive/disabled.
- New settings /var/lib/installarr-setup/settings.json; app DBs apps/; state
  state/state.json; live Compose project/compose.json; bootstrap state/bootstrap/compose.json.
- First setup uses the base directory, no active-setup pointer required. Saved
  reference_poc_ready, all preparation/bootstrap/published checks and automatic_startup
  verified. Docker/containerd enabled. These flags do not prove actual reboot behavior.
- Actual mounts .103:/share/MD0_DATA/Public at/media/Media and .102 Public at
  /media/Media-2, both NFS, matched exact operator selections. CURRENT_SETUP.md maps
  roles and paths. App DBs local, service identity media2000:2000, Plex binds read-only.
- Old /home/htpc, HomeNet-Test2, setup-c2c7141a879e/family-9ad2bb7ce113 and other
  fixtures belonged to the erased OS. Do not restore or start those resources.

## New approved media-permission policy

Operator copied test movies through the NAS GUI; nested directories were root:root
750, inaccessible as2000:2000 despite accessible library roots. This explained empty
Movies while directly placed TV and permissive Sports content appeared. Root-shell
listings did not prove service-account access. Operator explicitly approved a new
opt-in recurring host-supervisor repair policy, superseding preservation ONLY
within configured Plex library roots. No NAS API/ACL dependency or new backend.

Implemented installarr/media_permissions.py, existing-supervisor integration, new
media-permissions enable/disable/status CLI, and guided explicit opt-in (default no,
nonsecret media_permission_repair boolean). Existing deployment opt-in is a private
sidecar, preserving immutable config/Compose fingerprints. File-owner UIDs and
content/mtime are preserved; inaccessible objects may get shared-group ownership
and group read/search or owner read/search. Existing write bits not widened.
Skip symlinks, hardlinks, nested mounts, special files, NAS metadata and explicitly
read-only secondary sources. Exact source/marker/held-mount checks precede repair;
server denials/skips/errors visible. MEDIA_PERMISSIONS.md gives the complete policy.

Schedule: first pass after healthy storage/running containers; next full pass60s
AFTER completion. Existing supervisor polls roughly2s plus health-check time.
1000entry/5s active batches,30s worker deadline, no overlapping repair walks and
persistent unreaped-worker refusal. Large trees continue in following supervisor
iterations. Repair does not set Plex scan preferences or automatically force scans.

Physical evidence:
- Direct NAS repair/read/rerun: /var/tmp/installarr-media-repair-hnhflpd9/result.json.
- Actual asynchronous tracked worker: /var/tmp/installarr-media-worker-rjk1uw6z/result.json.
- First actual live pass checked22, changed7, denied0, skipped14. Actual3movie
  reads succeeded as2000:2000. Late restricted fixture repaired on next pass,
 62.41s between completions: /var/tmp/installarr-media-repeat-lidace8y/result.json.
  Disposable fixtures removed exactly; later pass changed0.
- Operator then confirmed CODA, Astro Boy and6Underground appeared in Plex WITHOUT
  any additional container restart. No repeated request/playback task is needed.

Current policy ENABLED at /var/lib/installarr-services/family-media/media-permissions.json.
Explicit stopped runtime refresh preserved original bytes in
/var/lib/installarr-setup/state/runtime-backup-e2f0f365d78e27ff.json, then restarted
only this owned live stack; bootstrap remains off and automatic startup unchanged.
Activated snapshot6e089fbf65ed0b2f5ca3b1ea02ea4b7a9c0c28472b6fdc6e3afed87560c06f20
has verified integrity and works on current24.04. No further container restart
was made after the operator observed movie discovery. Checkout subsequently fixes
older-libc effective-ID access emulation using a short-lived real-UID verifier;
that portability correction ships in fresh clones. Loading later source into an
already-installed supervisor still requires the explicit stopped-refresh workflow.

## Validation and publication

Current254-test suites pass as normal user/root, plus installed-wheel suites on
Ubuntu20.04/Python3.8 and24.04/Python3.12 at
/var/tmp/installarr-distribution-98jjoqcm. New tests cover actual root-owned750
repair/UID reads, idempotence, bytes/mtime/UID preservation, wrong/missing mounts,
symlinks/hardlinks/nested mounts, server denials, batching/cursor escape, scheduling,
no-overlap, disable/cancellation and unhealthy-storage cancellation. Existing tests
cover durable worker timeouts/unreaped groups and supervisor crash fallback.
Python3.8 grammar174files, shell syntax and whitespace checks pass. Real all-nine
PTY save-only guide includes explicit repair opt-in without host provisioning.

Initial Focal wheel exposed libc/Python effective-ID permission-check differences;
fixed with permanently dropped real IDs in a short-lived verifier. Final wheels
pass; the first failure and initially absent Ubuntu test image are recorded in
TEST_RESULTS.md, not hidden or counted as successful acceptance.

Operator now explicitly requests publishing this feature and remaining-work outline.
Public main before this change:4694b0d856d99bf123a9f7259691de380ff52886. No private
policy, credentials, reference Compose, file contents or Codex history go into Git.
Fresh clones must answer YES to the new permission-repair question to enable it.

## Remaining work and completion estimate

About90% complete for the agreed fresh Ubuntu reference installer, an engineering
estimate, not measured test coverage or a release-ready claim. The core installer
and this selected clean seven-app run work. Every app remains optional; earlier
all-nine fixture tests remain scoped evidence and do not force selecting nine now.

1. Publish/verify fresh clone of this feature and refreshed documentation.
2. Coordinate actual reboot/reconnect to verify enabled units, NFS ordering,
   guarded startup and real app availability on the new address. No reboot approved.
3. Coordinate controlled missing/unresponsive storage acceptance including startup
   refusal, no local fallback writes, bounded workers, repair cancellation and safe
   recovery. Do not shut down shared NAS, disrupt production or run umount -a.
4. Finish new-policy large/changing-tree, interrupted-worker and denied-server
   hardening and final failure-diagnostic/documentation/release audit; fix findings.

No new OS reinstall, ordinary media-request/playback tests, other people's
credentials, new backends, SMB server, PXE clients or migration/disaster recovery
are required gates. See IMPLEMENTATION_CHECKLIST.md and INTERACTIVE_TEST_QUEUE.md.
