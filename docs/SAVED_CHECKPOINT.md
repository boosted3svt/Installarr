# Saved checkpoint — fresh install and media repair, 2026-10-30

Read CURRENT_PROGRESS.md, CURRENT_SETUP.md, MEDIA_PERMISSIONS.md and
IMPLEMENTATION_CHECKLIST.md. Chronological evidence/failures: TEST_RESULTS.md.

OS reinstall and seven-app fresh guide COMPLETE on Ubuntu24.04.5, user plex,
checkout /home/plex/Installarr, intentionally changed address192.168.1.51/23,
Plex HTPC-210. Current family-media live unit active/enabled; bootstrap inactive/
disabled; new settings/apps/state at /var/lib/installarr-setup. No old app DBs were
restored. Old /home/htpc fixtures/paths/units are history, never restart them.

Operator-approved opt-in permission repair is ACTIVE in the existing host supervisor.
First live pass repaired7entries; actual three-movie UID2000reads and a late-arriving
restricted fixture passed. Next pass completed62.41s later; following pass changed0.
Operator confirms CODA/Astro Boy/6Underground now visible in Plex without further
container restart. File-owner UIDs/content preserved; shared GID/read/search may
change only in selected media roots. Plex remains non-root/read-only. Skip unsafe/
shared-link/nested-mount/read-only objects, report denials; do not apply777/share-wide
chown or add NAS-specific backends. First pass after healthy startup, repeats60s
AFTER completion with bounded batches. MEDIA_PERMISSIONS.md has controls and limits.

Private opt-in /var/lib/installarr-services/family-media/media-permissions.json.
Runtime original-byte backup /var/lib/installarr-setup/state/runtime-backup-e2f0f365d78e27ff.json.
Current activated24.04snapshot remains validated; later source portability correction
for Python3.8 ships in fresh clones and needs explicit stopped-refresh on an
existing deployment. Do not silently replace immutable supervisor snapshots.

254tests pass as user/root and from20.04/24.04 installed wheels; initial Focal
permission-check failure was fixed before publication. Feature published as
f8f54cc0dad6d8786c0cd2454b9968de83f51846 on main; fresh public clone passed new
CLI/module checks and254tests. Docs-only follow-up records that verified savepoint. Fresh guide offers an
explicit YES opt-in; existing configs are not silently altered. No credentials,
private policy, reference Compose or Codex backup in Git.

Estimated90% complete for agreed fresh-install scope. Publication/clone verification complete; remaining: coordinated reboot/reconnect, controlled unavailable-storage/repair
cancellation/recovery acceptance, new-policy large/concurrent-tree/interruption
hardening and final release audit. No reboot/outage is approved; no need for
another reinstall, repeated ordinary app-user actions or extra backends.
