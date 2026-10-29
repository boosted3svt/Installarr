# Physical test host and local Codex

This is a dedicated physical Ubuntu server, not a VM. It has OpenSSH and an isolated
VLAN allowing NAS and Internet access. The operator supplies isolated NAS storage.
No production test run is needed. Read AGENTS.md for implementation requirements.

## NFS prerequisite

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

## Bootstrap local Codex CLI

Install prerequisites as the normal administrator:

```sh
sudo apt update
sudo apt install -y ca-certificates curl git python3 tmux
curl -fsSL https://chatgpt.com/codex/install.sh -o /tmp/codex-install.sh
less /tmp/codex-install.sh
sh /tmp/codex-install.sh
```

Follow the installer's PATH instructions, reconnect SSH if needed, then:

```sh
codex --version
codex login --device-auth
```

Open the displayed authorization URL on another device and authenticate. Never
paste the login code, credential files or tokens into Git/chat. Device authorization
may need to be enabled in your account settings; follow the CLI's instructions.

Clone the repository, or pull main in the existing checkout. Private GitHub repository
authentication is separate from Codex login; use your normal GitHub access method.

```sh
git clone https://github.com/boosted3svt/Installarr.git
cd Installarr
tmux new -s installarr
codex
```

Start with normal permissions and give the agent this task:

> Read AGENTS.md and docs/PHYSICAL_TEST_HOST.md. Continue implementing the usable
> installer on this dedicated test machine. First inspect the host and confirm the
> isolated test mount. Run commands yourself, implement and test host preparation,
> then Docker and application adapters. Record results and blockers. Do not touch
> production or storage outside the test subtree. Do not format disks or change SSH,
> firewall, DHCP or networking. Ask before rebooting. Use sudo only within that scope.

Codex is a separate local session; it does not inherit the cloud chat. It can run
commands directly. Permission approvals and sudo may still require operator input.
For unattended host-level testing, after confirming the machine and storage scope,
an explicit opt-in is `codex --dangerously-bypass-approvals-and-sandbox`. This disables
Codex's sandbox and approval prompts; it does not grant Linux root privileges or
bypass sudo passwords. Do not use it on production. Choose a suitable administrative
access policy separately rather than casually granting passwordless sudo.

tmux keeps the terminal session alive if SSH disconnects, but not across reboot.
Reconnect using `tmux attach -t installarr`; after reboot use `codex resume` from
the checkout. Codex is not installed as a boot daemon by these instructions.

Official sources: https://github.com/openai/codex and
https://developers.openai.com/codex/cli/ . Commands were checked against the official
repository on 2026-10-27; use `codex --help` and `codex login --help` for installed-version details.

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
