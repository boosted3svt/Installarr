# Current Installarr checkpoint

## Resume here — 2026-10-30

The operator requested publishing ALL current implementation/tests/documentation
before an operator-led Ubuntu24.04.5 reinstall and a full fresh-install test.
They will back up the Codex conversation separately, then restore it after the
reinstall. Publication is complete; the work now is preparation for that clean test;
no machine wipe, reboot, service shutdown or media cleanup is authorized for Codex.

Read this file, SAVED_CHECKPOINT.md, CURRENT_SETUP.md and FRESH_HOST_CODEX_HANDOFF.md
before acting. TEST_RESULTS.md preserves chronological evidence and failures.
Older AGENTS.md/live-stack statements are superseded by this checkpoint. Inspect
actual host state after reconnecting: conversation history does not restore a host.

## Published savepoint

Implementation commit e1fed73169336eb335475ae2af3937e99495d3ef is on public main.
The GitHub-uploaded tree exactly matched the reviewed staged tree. Fresh public
clone launcher/help/nonterminal safe exit and244tests passed; evidence:
/var/tmp/installarr-publication-clone-p_uxbhl4/result.json. This checkpoint follow-up
records that completed verification; no implementation changed after those tests.
Local checkout and public main are synchronized. Credentials, reference Compose
and Codex backups are excluded. Clone public main after reinstall.

## Last observed machine, before reinstall

Read-only inspection on2026-10-30 found a NEW successful operator-run installation:

- Plex name **HomeNet-Test2**; seven selected apps Plex, Radarr, Sonarr, SABnzbd,
  Bazarr, Ombi and Tautulli. Jackett/netboot.xyz were declined; still optional.
- Active setup pointer: /var/lib/installarr-setup/active-setup.json.
- Selected directory: /var/lib/installarr-setup/installations/setup-c2c7141a879e.
- Settings: settings.json; apply state: state/state.json; app databases: apps/;
  live Compose: project/compose.json; bootstrap Compose: state/bootstrap/compose.json.
- Owned live unit installarr-family-c2c7141a879e.service active/enabled, seven
  running containers, Plex healthy. Bootstrap unit inactive/disabled.
- Apply phase reference_poc_ready; bootstrap_auth_and_paths, published_gui and
  all preparation steps verified; automatic_startup verified. This is saved
  installer evidence plus current inventory, not a new independent API audit.
- Both earlier family-9ad2bb7ce113 and original family-media units are inactive/
  disabled. Never start obsolete units alongside the selected installation.
- Exact mount identity observed:192.168.1.103:/share/MD0_DATA/Public at/media/Media;
  192.168.1.102:/share/MD0_DATA/Public at/media/Media-2; both NFS.
- Nonsecret configuration map: CURRENT_SETUP.md. Private GUI/provider/family/claim
  inputs remain under the selected private setup; no values are published.

AFTER THE WIPE these paths, units, accounts, Docker state and claim are historical.
Do not recover app databases or old installer state into the clean acceptance test.
Restore only Codex conversation/config if desired, and clone the published source.
Fresh setup must collect required credentials/Discord IDs locally and obtain a
fresh Plex claim. Keep the separate family passwords out of the workflow.

## Current implementation being published

- Plain ./installarr.sh guide: optional apps, local/NVMe/NAS/existing storage,
  independent downloads, editable per-role folders, precise source/access summary.
- Canonical media-* paths, separate secondary movie source, prepared completed
  categories, strict per-app binds, Plex read-only media, local application DBs.
- Eight primary folders and four new Plex libraries: Movies, TV Shows, Sports,
  Standup; Music excluded with files preserved. No automatic media migration.
- Full pinned TRaSH profiles plus separate quality-size limits, readback,
  appropriate family roots/profiles/roles and private Discord preferences.
- NFS prerequisite/endpoint options, exact mount/source checks, protected fstab
  backups, startup guards, ongoing ownership-scoped supervision and mount ordering.
- Explicit fresh-install selection on a surviving host: preserve old DBs/settings,
  reuse private inputs, retire only owned previous units/mounts after confirmation.
- Safe Newshosting connection-limit diagnostic. Arr folder collection/registration
  gets60s HTTP/65s outer deadline; other requests remain10s. Transport diagnostics
  identify Sonarr/Radarr without leaking credentials, bodies or stderr. No blind
  mutating retry; resume reads existing app state before creating anything.

All nine adapters and511optional render subsets were previously tested. Current244-test installed wheels pass Ubuntu20.04/Python3.8 and24.04/Python3.12
userspaces (/var/tmp/installarr-distribution-pr9mfxnw).
Latest244-test host suites pass (htpc238/6skips, root242/2skips). These are not a
claim of full clean-OS/systemd/reboot acceptance. See TEST_RESULTS.md for exact
physical provider/import/library evidence, pins and publication verification.

## Two recent failures and their interpretation

1. AppArmor: boot initialized normally and loaded docker-default. Operator ran
   sudo umount -a, unmounting multiple system filesystems before setup. Missing
   securityfs then blocked Docker startup. Operator confirmed the command and
   rebooted; subsequent containers started. Never use blanket umount -a for NAS
   cleanup. Installer runtime prerequisite/error-reporting improvements remain
   useful, but no security bypass or AppArmor disabling was added.
2. Sonarr: initial TV-root request had no response before the ordinary10s limit;
   cleanup stopped owned apps. Original curl status/stderr were not retained;
   low-level cause unproven. Bounded standalone registration later took0.518s,
   root ID1/readback passed. Same saved seven-app apply then completed in104.44s,
   with actual published auth/integrations. No slow-NAS reproduction was claimed.
   The operator subsequently completed the newer HomeNet-Test2 guide recorded above.

## Next full test

1. DONE: publish implementation and verify a fresh public clone before erasing this checkout.
2. Operator exits Codex, backs up its full ~/.codex while stopped to another
   machine/drive, then performs the Ubuntu24.04.5 reinstall with OpenSSH.
3. Reinstall the standalone Codex CLI using the official curl installer; restore
   its private state if preserving this conversation. See FRESH_HOST_CODEX_HANDOFF.md.
4. Clone the published Installarr repo to /home/htpc/Installarr. Resume conversation
   01a1897b-0699-7b80-ae24-7badc34e2117 and explicitly report the host was wiped.
5. Run ./installarr.sh with no flags in a separate SSH terminal for hidden prompts.
   Do not manually preinstall Docker/NFS or restore /var/lib/installarr* databases.
   Let the launcher and guide perform dependency/storage/account/app preparation.
6. Confirm storage sources/access in the guide. CURRENT_SETUP.md records the last
   approved real layout; FRESH_HOST_CODEX_HANDOFF.md also offers an isolated export
   recipe. Do not silently substitute exports or broaden NAS access. Preserve
   existing media; never recursively chown libraries or delete prior media folders.
7. Verify actual shared GUI authentication, app API links, roots/categories,
   pinned profiles/sizes, native family preferences, four Plex libraries and local
   databases; record exact selected apps/version/result. Avoid repeated ordinary
   requests/playback as release gates. All nine apps remain optional.
8. Offer automatic startup only after successful setup. Coordinate reboot/reconnect
   and absent-storage boot acceptance with the operator separately. Do not run a
   reboot, shut down NAS or change SSH/IP/DNS/VLAN/disks/unrelated firewall rules.

A normal reboot preserves Codex history; a wipe requires an off-machine backup to
resume the same conversation. Signing in alone does not restore an erased chat.
The normal installer needs no Codex, saved credential transfer, tmux, reference
Compose file, disaster recovery tooling or new auxiliary backend.
