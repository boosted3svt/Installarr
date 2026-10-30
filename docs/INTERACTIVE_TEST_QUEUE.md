# Remaining acceptance — 2026-10-30, after the fresh installation

The OS reinstall and fresh seven-app guide are COMPLETE. Current host is Ubuntu
24.04.5, user plex,192.168.1.51/23; selected deployment family-media, Plex HTPC-210,
state/settings/apps under /var/lib/installarr-setup. The installer completed real
bootstrap/published checks and enabled automatic startup. Prior host fixtures are
history. CURRENT_PROGRESS.md/CURRENT_SETUP.md are authoritative.

Operator approved scoped media permission repair, now active in the existing host
supervisor. Real NAS tests, actual three-movie UID2000reads, late-addition repair
and operator-confirmed Plex discovery pass. Full passes repeat60s after completion;
measured62.41s between passes including polling. See MEDIA_PERMISSIONS.md.

## Remaining operator-coordinated gates

1. **Reboot/reconnect:** schedule the reboot after reviewing this completed setup.
   Verify enabled Docker/containerd/owned service, expected NFS mounts and ordering,
   guarded startup, correct192.168.1.51bindings and actual app availability. Codex
   must not reboot without explicit timing approval. No more OS reinstall needed.
2. **Controlled unavailable storage:** agree on a disposable/scoped fault fixture
   to exercise absent or unresponsive mounts through startup and ongoing supervision,
   including repair cancellation and bounded workers. Verify no local fallback
   writes and safe recovery. Do not shut down a NAS, disrupt production shares,
   change SSH/VLAN/IP/DNS/routes or run umount -a.

## Independent work

Publish the feature and refreshed checkpoints; validate the fresh public clone.
Finish new-policy large-tree/concurrent-copy/worker-interruption/server-refusal
hardening and final release documentation/diagnostic audit. Do not reinterpret
ordinary Plex requests/playback, other people's passwords, an all-nine selection,
physical SMB or disaster recovery as additional required operator gates.

## Completed and remaining evidence boundaries

Earlier all-nine combined fixtures and provider/import/quality/family evidence
remain valid for their stated versions/scopes. The latest physical fresh24.04.5
run selected seven; that is a real clean-host result for those choices. Unit/wheel
suites and enabled-unit flags do not prove post-reboot or outage safety. Permission
repair cannot override a server that refuses metadata changes; skipped objects
and denials must remain visible. Fresh clones must explicitly opt in to repair.
