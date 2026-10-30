# Remaining fresh-install acceptance — 2026-10-30

The operator requested publication, is backing up Codex history privately and plans
an Ubuntu24.04.5 reinstall. CURRENT_PROGRESS.md and CURRENT_SETUP.md supersede all
historical live stacks and earlier interaction queues. Do not invent application
user-action gates or request another person's account credentials.

## Current observed baseline, before wiping

HomeNet-Test2, seven apps, selected setup-c2c7141a879e, live unit
installarr-family-c2c7141a879e.service active/enabled, bootstrap inactive/disabled.
Saved reference_poc_ready, GUI/bootstrap checks and automatic_startup verified.
Both prior family-9ad2bb7ce113 and family-media stopped/disabled. Current source
map is .103 Public at/media/Media and .102 Public at/media/Media-2; both exact
mounts observed. These local resources become HISTORY after reinstall.

The old nine-app/three-unit experiments and their /var/tmp configs are not the
next target. Do not restart them or restore old Plex identities concurrently.

## Next operator actions

1. **Preserve conversation and publish source:** exit all Codex processes before
   making a private full ~/.codex backup to another computer/drive. Include session
   and SQLite state; history.jsonl alone is insufficient. Operator handles backup;
   Codex publishes reviewed source/tests/docs without credentials/reference Compose.
2. **Fresh Ubuntu:** operator performs installation with OpenSSH. Codex must not
   wipe/repartition the machine, alter SSH/VLAN/DNS/IP/manual routes or start a
   reboot. Install standalone Codex using FRESH_HOST_CODEX_HANDOFF.md; restore its
   history only if desired. Clone published source and report the host was wiped.
3. **Normal fresh guide:** run ./installarr.sh without flags. Do not preinstall
   Docker/NFS or copy old installer state/DBs. Each selected app optional; last run
   selected seven, declined Jackett/netboot. Use CURRENT_SETUP.md to review last
   nonsecret choices; isolated recipe is an alternative, not a silent substitution.
   Fresh shared login, providers, optional Discord targets and Plex claim use local
   hidden prompts. No passwords/API keys/Discord numbers in chat.
4. **Actual installer acceptance:** inspect the selected setup, actual mount source/
   type and service-UID access; read back app authentication, folder/category map,
   API links, full profiles/size limits, native family preferences, Plex libraries
   and local DB ownership. Record exact pins/config/result and any failure. No
   repeated requests/playback needed; these application features already have evidence.
5. **Boot/storage acceptance:** after completed installation and startup choice,
   coordinate operator-led reboot/reconnect and scoped absent-storage behavior.
   Do not shut down a NAS or affect unrelated mounts/services. Never use umount -a.
   Prior simulator/userspace tests and enabled-unit flags are not boot proof.

## Completed evidence and limits

All nine adapters previously passed combined fixtures; current seven-app operator
ready state and prior same-saved-setup recovery passed.244host tests pass; current
244test wheels pass20.04/24.04 userspaces. Standardized scoped paths, generated
Arr/SAB imports, local-NVMe paths, Plex read-only binds and pinned quality sizes
have physical evidence. Recent Sonarr timeout underlying cause was not captured;
its60s bounded folder deadline and safe transport errors are now included.

Full genuinely fresh Ubuntu/systemd provisioning and coordinated boot/mount
protection remain the goal. Do not label the installer release-ready based solely
on saved phase, open ports or unit tests. SMB physical fixtures, migration/disaster
recovery, new backends and arbitrary reconfiguration are outside this test scope.
