# Physical test host and local Codex

This is a dedicated physical Ubuntu server, not a VM. It has OpenSSH and an isolated
VLAN allowing NAS and Internet access. The operator supplies isolated NAS storage.
No production test run is needed. Read AGENTS.md for implementation requirements.

## Historical manual NFS prerequisite test

This section records earlier manual storage experiments. Do not run these commands
before the fresh-install acceptance test: let Installarr install NFS helpers and
prepare mounts itself. Use FRESH_HOST_CODEX_HANDOFF.md for the current test flow.

On fresh Ubuntu, install the NFS client helper before mounting NFS:

```sh
sudo apt update
sudo apt install -y nfs-common
sudo mkdir -p /media/installarr
sudo mount -v /media/installarr
findmnt /media/installarr
```

The mount command assumes the operator has already added the test entry to fstab.
Never append duplicate entries. The installer now provides `prepare-prerequisites --config /path/to/config.json`
for signed, resumable installation of the required client packages. `check-mounts` and `prepare-mounts` now reconcile exact mounts/fstab, preserve
existing entries and back up approved persistence edits. Fresh NFS mount tests
passed in a private mount namespace; live host fstab stayed unchanged. Even reused NFS mounts require
nfs-common in the host plan. SMB uses cifs-utils instead.

## Codex on a fresh or wiped host

Follow [FRESH_HOST_CODEX_HANDOFF.md](FRESH_HOST_CODEX_HANDOFF.md) for the current
installation, device login, operator-requested passwordless sudo and direct Codex
launch commands. **No tmux involvement:** do not install it or wrap Codex with it.
Run Codex directly in the SSH terminal. The guide includes the exact initial
checkpoint prompt and later resume command.

A wiped installation has no surviving local chat history or old test services.
Start a new chat from GitHub checkpoints rather than trying to resume an erased
thread. Let Installarr perform Docker/NFS provisioning for the clean-install test.
The normal installer itself needs no Codex installation or permission bypass.

## Current physical checkpoint (2026-10-29)

The operator approved standard Docker web-bridge/NAT changes. Standard Docker and
containerd are active and boot-disabled; the historical isolated daemon is stopped.
Do not run the earlier masking/staging workflow against the active engine. Host
IP/DNS/manual routes, SSH, VLANs, disks and unrelated firewall rules stay protected.
No reboot has been approved.

Exact test mount:192.168.1.102:/share/MD0_DATA/Public/installarr at/media/installarr,
NFS. Verify it with findmnt before every experiment that writes. Only this test
export is authorized; preserve the supplied movie, subtitle and episode files.

Leave these active, disabled-at-boot service pairs available:

- installarr-poc-http-d29db77d.service: Radarr7878/SAB8090.
- installarr-plex-standard-test.service: Plex32400/Tautulli8181.
- installarr-ombi-family-2274744e.service: Ombi3579, own native Plex sign-in confirmed.

Operator confirmed real Plex GUI movie/episode playback. Plex is already claimed,
uses a read-only NAS bind, and is named Installarr Test. Current config/state:
/var/tmp/installarr-plex-standard-2bbujwqu/config.json and state. Older Plex test
units share its original local databases and must remain stopped.

Final Plex libraries: Movies (four folders), TV (three), sports→sports,
StandUp→StandUp and Music→Music. No low-res folders, Disney, Only Heather,
YouTube Videos or TubeSync Videos libraries. Movies-2 is an empty test placeholder;
the production secondary mount is not validated. No media directories were deleted.

Ombi native family/Arr/Plex links, availability/routing and import crash recovery
passed; full fresh combined family apply still needs a claim/coordinated scope.
netboot explicit local/NFS assets,911:1001 permissions and marker recovery passed.
Generic read-only secondary Movies-2 source protection passed; production source
values/claimed GUI remain outstanding. Scheduled subtitles, controlled generated
Radarr/Sonarr download/import, optional standalone pairs and terminal menu passed.
Immutable runtime updates are explicit/stopped-only with backups/journal recovery;
retained three units stay on their original snapshots. No clean-host/systemd,
real NAS outage or reboot readiness is claimed.

Operator asked for continuous progress while away for roughly five hours. Queue
interactive state/recipes in INTERACTIVE_TEST_QUEUE.md and continue independent
work. Do not ask/wait at those gates during the absence. This supersedes the prior
saved pause. Read AUTONOMOUS_WORK_PLAN.md for the full classification.

Read CURRENT_PROGRESS.md for precise current commands, private-file boundaries,
latest test totals and next work; IMPLEMENTATION_CHECKLIST.md tracks remaining
requirements and TEST_RESULTS.md records exact pins, failures and physical evidence.
Continue independent work; do not stop solely because a milestone passed.
