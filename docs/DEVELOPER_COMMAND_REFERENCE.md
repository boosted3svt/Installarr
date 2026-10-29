# Advanced and historical command reference

The normal household entry point is `./installarr.sh`; see ../README.md.
The examples below include isolated physical-test infrastructure and are not a
sequence to run on a normal fresh installation. Current status is in CURRENT_PROGRESS.md.

# Installarr — start here

On a fresh Ubuntu computer with OpenSSH, the intended launch sequence is:

```sh
sudo apt-get update
sudo apt-get install -y git ca-certificates
git clone https://github.com/boosted3svt/Installarr.git
cd Installarr
./installarr.sh
```

The launcher installs its small Ubuntu runtime prerequisites if missing, then opens
the setup guide. This repository contains the guided installer; the remaining clean-host acceptance
work is documented below.

After package installation, run `installarr`. No flags or file paths are needed. The guide asks
which programs to install, where your media lives, and for the relevant account
details. It saves your choices and can continue an interrupted installation.


On each clean installation, enter the administrator login, provider credentials,
Plex authorization and optional family Discord account numbers when prompted.
No credential file needs to be kept or copied from the old computer. Mount defaults,
profiles and family roles are part of the installer; it generates Compose and
configures the programs through their APIs. The supplied development reference
Compose file is not needed on the new computer. Passwords and keys are kept private
on the installed server, outside Git and the ordinary settings file.

This project provisions a fresh Ubuntu media server. Combined fresh-host and
startup acceptance checks are still pending. The explicit commands below are for
advanced use and development, rather than the normal household setup flow.

# Installarr

Headless CLI for fresh Ubuntu media-stack provisioning. Reference apply has
version-pinned adapters and tested protected HTTP bootstrap for SABnzbd, Sonarr,
Radarr, Bazarr, Jackett, Plex, Tautulli, Ombi and netboot.xyz. Real Plex GUI playback
and Tautulli integration now pass. Ombi links, native Plex family routing and operator sign-in pass; full combined
family apply, clean-OS acceptance and reboot safety remain open. This is a working partial
installer, not a finished release.

The authoritative live services, operator decisions and resume commands are in
[current progress](docs/CURRENT_PROGRESS.md). The chronological evidence is in
[test results](docs/TEST_RESULTS.md), and remaining work is in the
[implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md).

The [fresh installation runbook](docs/INSTALLER_RUNBOOK.md) gives the current terminal
and unattended sequence, including preparation before a short-lived Plex claim.

The normal deployment path is `apply --reference`, using the approved standard
Docker web bridge and published HTTP ports after authentication checks. Older
isolated-daemon/relay examples below are historical development tooling; do not
run their masking/staging commands against the active standard engine.

## Run

For local agent setup and testing on the isolated physical Ubuntu machine, see
[Physical test host](docs/PHYSICAL_TEST_HOST.md) and [Agent handoff](AGENTS.md).

Python 3.8+ is required; host provisioning accepts Ubuntu 20.04 or newer,
including Ubuntu 22.04 and 24.04.
Read-only inventory can also run on older Ubuntu hosts. Timezone validation uses
the system timezone database (`tzdata`), without a Python `zoneinfo` dependency.
No third-party runtime dependencies are required. From this checkout:

```sh
python3 -m installarr menu
python3 -m installarr preflight
python3 -m installarr configure --config /tmp/installarr.json
python3 -m installarr plan --config /tmp/installarr.json
python3 -m installarr check-storage --config /tmp/installarr.json
python3 -m unittest discover -s tests -v
```

`configure` requires a terminal and refuses to overwrite existing files. Saved JSON
is mode 0600 and contains no credentials. For unattended planning, supply the same
JSON schema directly. `plan` exits 2 for identity conflicts, 1 for invalid input or
file errors, and 0 for a conflict-free preview; 0 does not imply deployment readiness.
Preflight reports command availability and exit codes without exposing command stderr.

## Read-only storage validation

Preflight now returns parsed mount records instead of escaped nested JSON. It only
lists mount metadata; it does not access remote files. `check-storage` explicitly
reads the configured directories as the invoking operator, without creating files.
It does not establish service-UID permissions or write access.

Add optional `storage_checks` to your existing JSON configuration. For example,
if `storage.media` is `/media/Media/TV`:

```json
"storage_checks": {
  "media": {
    "mountpoint": "/media/Media",
    "source": "192.168.1.103:/share/MD0_DATA/Public",
    "fstype": "nfs",
    "sentinel": "healthcheck.txt"
  }
}
```

The sentinel must already exist inside that storage directory. The command never
creates it. Source, filesystem and covering mountpoint must match exactly before
file reads occur. Configured storage directories containing symlinks are rejected
to avoid probing a different filesystem than the asserted mount.
A missing NAS that leaves an ordinary local directory therefore
fails before probing it. Each probe has a five-second subprocess timeout; kernel
uninterruptible filesystem I/O may delay process cleanup beyond that timeout.

Exit 0 means all configured storage purposes passed mount assertions and sentinel
reads. Exit 2 means at least one failed or lacks sufficient assertions; exit 1 means
invalid configuration or a command error. Individual results distinguish `verified`,
`failed`, and `incomplete`. These checks do not establish boot persistence, NAS write
access, or automatic protection for running containers. Existing configurations
remain valid, but their storage checks report incomplete until assertions are added.

## Storage wizard and host preparation plan

`configure` now asks for local, existing-mount, NFS or SMB storage independently
for each purpose. NFS/SMB inputs capture the exact source, mountpoint, filesystem
and optional existing sentinel; SMB captures only a credentials **file path**, never
a username/password. Do not put credentials in source URLs or paths.

These choices populate `storage_mounts` and automatically supply assertions to
`check-storage`. Multiple directories may share one identical mount. Conflicting
sources at a mountpoint, directories outside their declared mounts, conflicting
check assertions and nested mount layouts are rejected. Existing mounts are marked
for reuse without changing their persistence configuration. Local storage means an
existing filesystem directory, not disk formatting or partitioning.

`plan` now includes deduplicated mount proposals, required NFS/CIFS packages,
directory intentions, and outstanding validation gates. It does not execute them.
An example mount choice (alongside `storage.media: /media/Media/Movies`):

```json
"storage_mounts": {
  "media": {
    "kind": "nfs",
    "mountpoint": "/media/Media",
    "source": "192.168.1.103:/share/MD0_DATA/Public",
    "fstype": "nfs"
  }
}
```

Old JSON files remain accepted and report missing storage choices in the host
preparation blockers. Plans are declarative; the limited isolated `apply`
workflow below now executes the tested path. New wizard runs should use a new filename because overwrites remain
prohibited. No root access is needed for configuration and planning.

## Design requirements

- Fresh provisioning first; application-state migration/disaster recovery is a stretch goal.
- CLI only; browser authorization, if necessary, takes place on another device.
- Every app is optional: SABnzbd, Sonarr, Radarr, Bazarr, Jackett, Plex, Ombi,
  Tautulli and netbootxyz.
- Prefer documented image-specific non-root ownership. Never inherit production 0:0.
- Selected netbootxyz requires host user/group `nbxyz`, UID 911 and GID 1001.
  Its runtime permission mechanism must be verified against official image guidance.
  DHCP and client PXE reachability are operator-managed.
- Preserve the editable Plex allowed-network preset `192.168.0.0/23`.
- Generate Compose and application paths from one storage map. Existing host media
  is never renamed or recursively chowned by default.
- Validate mount identity, reachable sentinel files, application APIs, and service-UID
  access separately. Implement mount-loss protection beyond Docker health status.
- GUI administrator credentials are distinct from Linux users and generated API keys.
  Family Ombi users use Plex authorization, with optional reconciled family presets.
- Pin tested application images and TRaSH profile snapshots; dynamically resolve IDs.
- No production writes during development. Use isolated test paths and minimal
  disposable service pairs, never production download destinations.

## Remaining acceptance

See the maintained [implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md).
Connection tests do not prove request dispatch, real provider access, per-user
routing or clean-OS readiness. Reboot remains an explicit operator approval gate.
Work in the existing checkout; no worktree is required.

## Account preparation checkpoints

After reviewing `plan`, on an Ubuntu 20.04-or-newer provisioning target:

```sh
sudo python3 -m installarr prepare-accounts --config /path/to/installarr.json
```

This narrow command creates only missing groups/users, with no home directory and
a nologin shell for new users. It preserves existing matching accounts and refuses
collisions before changes. Selected netbootxyz reserves `nbxyz` UID 911/GID 1001.
It does not establish application runtime permissions or installation readiness.

Checkpoints default to `/var/lib/installarr-accounts` (0700), with 0600 files,
an exclusive process lock and atomic, fsynced updates. `--state-directory` can select
another private directory under trusted ancestors; use local storage, not NAS.
The parent must already exist. Reuse the same directory to resume the same account
plan. Changed identity plans are refused; investigate and reconcile previous
attempts before choosing a new state directory. Every rerun inspects real accounts,
even after a successful checkpoint. An interrupted account command may have taken
effect; subsequent runs inspect and reconcile it rather than trusting state.
State stores operation names/statuses and a plan digest, never credentials.

This account-only command does not deploy applications. Reference apply separately
orchestrates mount reconciliation and authenticated application deployment. Test evidence and current host
limitations are recorded in [test results](docs/TEST_RESULTS.md).

## Shared GUI credentials

Collect the shared administrator username and hidden password once, separately
from the nonsecret configuration:

```sh
python3 -m installarr init-secrets --secrets-directory /private/local/installarr-secrets
```

The parent directory must exist under trusted ancestors. The secret directory is
0700 and `gui-admin.json` is 0600, owned by the invoking user. The file contains
plaintext credentials protected by filesystem permissions; it must stay on local
private storage. For unattended use, add `--credentials-file /private/input.json`.
That input must be a regular, single-link, nonsymlink 0600 file owned by the
invoking user, containing exactly `username` and `password`. Do not pass credential
values as command-line arguments or put them in the nonsecret configuration.

Reruns validate and retain existing credentials without prompting or overwriting.
Corrupt or unsafe files fail closed. Credentials are published atomically without
replacement and never printed or included in execution checkpoints. This command
does not yet configure application authentication; Plex authorization, Jackett
capabilities, API keys and credential rotation remain separate work.

## Explicit service-identity write checks

```sh
sudo python3 -m installarr check-storage-writes --config /path/to/installarr.json
```

This opt-in command writes temporary files, unlike `check-storage`. Every storage
purpose needs exact mountpoint/source/filesystem assertions, including local
directories. The child process switches to the configured service UID/GID with no
supplementary groups, verifies the mount again through an open directory descriptor,
creates a unique `.installarr-write-*` directory, writes/fsyncs/reopens a sentinel,
then removes only its own artifacts. No directories are provisioned or chowned.
Existing files are not inspected. Missing/wrong/read-only mounts refuse writes.

Unprivileged execution is permitted only when UID/GID already match and there are
no supplementary groups other than the primary group. An operator account with
extra groups cannot establish service permission readiness. Exit 0 means all write
checks passed, 2 means failed or incomplete checks, and 1 means invalid configuration
or a command error. Workers time out after ten seconds; blocked kernel NFS I/O can
delay termination and interruptions may leave temporary probe artifacts. Inspect
such artifacts within the authorized test subtree before cleaning them up.
These checks do not prove boot persistence, mount-loss protection or netbootxyz
runtime permissions; its reserved identity needs separate application checks.

## Docker package staging and isolated test daemon

```sh
sudo python3 -m installarr prepare-docker
sudo python3 -m installarr prepare-test-daemon
```

`prepare-docker` is a fresh-host adapter. It refuses conflicting container packages,
existing unmanaged Docker data/configuration and duplicate Docker repositories.
It never removes conflicting packages or replaces differing system files. It uses
Docker's HTTPS repository with a dedicated `Signed-By` keyring, verifies the primary
signing-key fingerprint, selects exact official package versions, records them in
private resume state, and verifies installed versions on every rerun. Reruns do
not silently upgrade or downgrade Docker. Current upstream repository guidance
supports Jammy/Noble/Resolute/Stonking; Ubuntu 20.04 remains accepted by Installarr,
but needs a separately validated Docker installation path.

Standard `docker.service`, `docker.socket` and `containerd.service` stay masked
through package installation and reboot. Package staging alone starts no daemon.
The separate `prepare-test-daemon` command starts `installarr-test-docker.service`
on `unix:///run/installarr-docker-test/docker.sock`, with private data at
`/var/lib/installarr-docker-test/data`. It disables bridge creation, iptables,
ip6tables, forwarding changes, masquerading and the userland proxy. It does not
enable the test unit at boot or alter default Docker daemon configuration.
Use `--network none` for disposable test containers; no ports are published.
This mode validates storage and container execution, not application connectivity.

Example test-daemon inspection:

```sh
sudo docker --host unix:///run/installarr-docker-test/docker.sock version
sudo docker --host unix:///run/installarr-docker-test/docker.sock ps -a
```

`installarr.startup` now generates a POSIX-shell container startup gate. It derives
source/subtree assertions from host storage mappings and checks the container's
actual mount source, root, filesystem, writable mount flag and readable sentinel
before executing the original entrypoint. It accepts only exact equivalent Linux
NFS/CIFS source/root representations. Sentinels must be nonsymlink basenames with
at least one newline-terminated line. Use `rprivate` bind propagation. The gate is
evaluated on every container restart, including Docker daemon auto-restarts;
existing containers retain their mounted filesystem if the host bind disappears.
No bind-source directory is created automatically by the long `--mount` syntax.

This gate is wired into generated Sonarr/Radarr Compose files and tested with
their real `/init` entrypoints. It requires `/bin/sh` and `/proc/self/mountinfo` in
the image. A blocked hard-NFS sentinel read can leave startup waiting without
executing the application. The managed service below adds ongoing reachability monitoring. Actual NAS-outage and an approved reboot test remain outstanding. See
[test results](docs/TEST_RESULTS.md) for exact versions and physical experiments.

## Guarded application Compose generation

```sh
python3 -m installarr render-compose --config /private/installarr.json
```

This writes a private bundle at `project_directory`: `compose.json`, per-app guard
scripts, image pins and locked resume state. It does not deploy containers or
create storage directories. Identical reruns retain files; changed plans or changed
existing artifacts are refused without replacement. Image descriptors exist for all
nine reference apps. Use reference apply for their tested authentication/bootstrap
workflow; plain rendering does not configure applications. No credentials are included in Compose, environment values or checkpoints.

The generated services use pinned LinuxServer image digests, their `/init`
entrypoints after the storage gate, and PUID/PGID from `service_user`. They use no published ports and `restart: no`. SAB stays networkless, while
selected Sonarr/Radarr join its namespace for loopback connections; without SAB,
each app uses `network_mode: none`. This is an isolated
bootstrap/testing bundle, not a complete connected deployment. Bind mounts use
long syntax with `create_host_path: false` and `rprivate` propagation. Dollar signs
are escaped for Compose so actual host paths remain literal.

`media`, `downloads` and `incomplete` map consistently beneath `/data` and all need
exact mount assertions plus existing newline-terminated health sentinels.
`configs` must be declared local; prepare and verify that actual filesystem before
deployment. Each app binds `storage.configs/<app>` at `/config`. The current fresh
layout derives Sonarr's `/data/media/TV` and Radarr's `/data/media/Movies` from
`storage.media`; it does not rename existing folders or infer existing library case.
Directories and service-UID permissions must already be prepared.

The internal `installarr.arr` adapter supports the standard and historical isolated
Docker sockets. It requires a tested runtime version before API writes, configures
Forms authentication with password confirmation, verifies real cookie login and
bad-password/anonymous rejection, and reconciles accessible root-folder IDs with
readback. API keys remain distinct from GUI credentials. Temporary curl config
travels on stdin and session cookies are private and removed after each check.
Reference apply orchestrates this adapter as an unattended bootstrap workflow.

Physical tests passed on Sonarr `4.0.20.3014-ls1` and Radarr `6.4.4.10685-ls324`:
actual app processes/database files used UID/GID 2000:2000; local databases,
authentication and roots persisted across restarts; fake media storage was refused
before `/init` without changing config files; recovery and literal-dollar NAS
paths passed. These results do not prove indexers, download clients, completed
imports, TRaSH profiles, Plex/Ombi integrations or general installation readiness.


## Storage client prerequisites

```sh
sudo python3 -m installarr prepare-prerequisites --config /private/installarr.json
```

Installs only missing `nfs-common`/`cifs-utils` required by the storage plan,
including reused network mounts, before any future mount operation. APT signature
checks remain enabled and explicit repository trust bypasses are refused. Private
checkpoints reconcile actual installed packages on reruns. This command does not
mount storage or edit fstab, directories, existing ownership or permissions. The
physical NFS prerequisite rerun passed with the already-installed package; missing
package installation and SMB remain unit-tested rather than physically validated.

## Managed isolated service lifecycle

```sh
sudo python3 -m installarr install-service --config /private/installarr.json --name test
sudo systemctl start installarr-test.service
sudo python3 -m installarr service-status --name test
sudo systemctl stop installarr-test.service
```

Install after preparing the asserted storage directories and rendering the bundle.
The command installs a disabled unit, private definition/checkpoints and an
immutable root-owned code snapshot. It uses the isolated Docker socket only. The
supervisor checks exact mounts, local configuration storage and service-UID
sentinel reads, stopping only its matching bundle containers when health fails.
Healthy storage permits recovery. Container policy changes or foreign containers
with colliding project labels are preserved and refused. A post-stop handler also
stops owned containers after a supervisor crash. Bounded health workers avoid
spawning more processes while a previous filesystem probe remains stuck.

Physical tests passed for marker loss/recovery, restart while unhealthy, supervisor
SIGKILL, unrelated-container preservation and enable/disable operations. Real NAS
outage and actual reboot execution remain untested. Units are disabled by default;
the retained test unit references cleaned disposable paths, not a usable deployment.

## SABnzbd download adapter

The internal `installarr.sab` adapter is pinned to SABnzbd `5.1.3-ls278`. It verifies
runtime versions before writes, configures shared Basic GUI authentication and
checks anonymous/bad-password rejection after restart. API keys remain separate.
The storage map sets `/data/incomplete`, `/data/downloads`, and relative `tv` and
`movies` category directories, with mandatory readback and safe repeated settings.
API credentials travel over Docker exec stdin; bootstrap publishes no ports.

A real isolated NNTP/yEnc transfer of generated test data passed: the completed
NAS file matched all 3,776 expected bytes and SHA256, owned by UID/GID 2000:2000.
Authentication, categories and history survived restart. This proves a downloader
transfer and destination mapping; provider access, Sonarr/Radarr dispatch/import,
and connected deployment remain separate unvalidated gates. Exact versions,
commands, failures and hashes are recorded in [test results](docs/TEST_RESULTS.md).


## Download-client connections

The internal `installarr.downloadclients.ensure_sabnzbd` adapter now reconciles
Sonarr/Radarr connections to SABnzbd using each running app's provider schema.
It resolves IDs dynamically, maps Sonarr to `tv` and Radarr to `movies` from the
application storage map, tests credentials before saving, reads back the entry,
and tests the saved connection. Repeated calls retain one entry and the same ID.
Existing conflicting implementations or changed endpoint/category/priority settings
are preserved and refused. API keys are passed separately from nonsecret config.

Physical tests used one application and SABnzbd at a time, with both GUI accounts
protected. A fixture-only Compose extension shared SAB's networkless container
namespace, providing loopback communication without host ports or a bridge. This
shared namespace topology is now supported by generated bundles and the supervisor,
including matching owner/inode checks. This is the historical isolated topology.
Normal reference apply uses the approved bridge with verified DNS/outbound HTTPS. See [test results](docs/TEST_RESULTS.md).


## Existing-library validation

The isolated physical tests now use the operator-supplied movie and TV episode
**in place**, mounted read-only in disposable app fixtures. Radarr and Sonarr
recognized the real files using official metadata, correct paths and sizes, and
retained file records across restart. Original names, sizes and modification times
were preserved; no media copies or deletions were performed.

Installer scope is correct storage, permissions and usable application integration.
Choosing or managing manual versus automatic import modes remains application
behavior. The fixture metadata relay and its temporary app proxy setting are test
infrastructure, not generated deployment settings. See [test results](docs/TEST_RESULTS.md).


## Prepare application directories

```sh
sudo python3 -m installarr prepare-prerequisites --config /private/installarr.json
sudo python3 -m installarr prepare-directories --config /private/installarr.json
```

Run after preparing service accounts and mounting the configured storage. The new
command checks every storage anchor before storage writes, requires exact network
mount assertions and local application databases, then creates configured storage
and selected app directories. Sonarr/Radarr roots preserve `TV`/`Movies` case.
Data directories need a basename health sentinel in their storage assertions.
Missing markers are created without overwriting existing files; existing markers
must be regular files containing a newline. Existing ownership and modes are
preserved; incompatible app-config ownership or service-user write access fails.
No mount, fstab, recursive chown or media-management operations are performed.

Network directory work runs as the configured service UID/GID with supplementary
groups cleared. Only newly created local directories receive the configured
ownership. App config subdirectories receive actual service-UID write/fsync checks;
their host parent can stay private because Docker binds each child separately.
Held directory handles and repeated exact-mount checks prevent fallback writes.
Private local checkpoints default to `/var/lib/installarr-directories`; use
`--state-directory` to select another existing local parent. Reruns inspect actual
storage rather than trusting completed steps.

The physical test retained a visible example at
`/media/installarr/Installarr-Directory-Test-20261028-c0112b37`, with health markers
under `media`, `downloads` and `incomplete`. Original supplied media is untouched.
Earlier disposable fixtures used hidden `.installarr-*` names and were cleaned,
so a plain `ls` would not have shown them while they ran.


## Resumable isolated apply

```sh
sudo python3 -m installarr apply --config /private/installarr.json --name test \
  --credentials-file /private/gui-admin.json
```

This first `apply` supports any nonempty selection of Sonarr, Radarr and SABnzbd
on already-mounted, asserted storage with local application databases. Other apps
are refused before host preparation. It reconciles accounts, signed prerequisites,
directories, staged Docker packages, the isolated daemon, pinned images, Compose,
a guarded systemd service, GUI credentials, app paths and SAB connections.

For unattended use, the credential input must be an executor-owned 0600 JSON file
with `username` and `password`, or supply an existing protected store using
`--secrets-directory`. Interactive use prompts once with hidden password input.
The shared credential store is separate from config and checkpoints and never
silently overwritten. Later resumes use the stored credentials without prompting.
Default private state: `/var/lib/installarr-apply/<name>`; `--state-directory` selects
another existing local parent. A changed deployment plan is refused.

With SAB selected, Sonarr/Radarr join its otherwise networkless container namespace
and connect through container loopback. The supervisor verifies the matching SAB
container ID and actual live network-namespace inode. A stale namespace after a
SAB-only restart causes a scoped stop/recovery. App selections without SAB retain
individual `network_mode: none`. No bridge, host network configuration edits,
published ports or automatic boot enablement are added.

**This deployment still has isolated outbound networking. Authenticated host GUI
listeners are now provided at the configured address and app ports.**
The successful status is `isolated_configured`: real authentication/rejection,
storage readback and connection checks passed. The supervisor opens GUI listeners only after real authentication verification,
rechecks new backend namespaces and closes access on unhealthy storage or failure.
General outbound/provider connectivity remains unfinished.

Failure records the current step and stops only matching managed containers. A
rerun rechecks real state, including previously completed steps. Physical minimal
Sonarr/SAB and Radarr/SAB runs passed injected-failure stop, real CLI resume and
repeated application configuration without duplicated IDs. Exact commands and
retained test artifacts are recorded in [test results](docs/TEST_RESULTS.md).


Current completion checklist: [implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md).
`check-mounts --config ...` now reviews exact runtime mounts and fstab without
modification, detects conflicting/duplicate/read-only declarations, and does not
print operator credentials from mount options. Apply runs this review before
storage-directory writes. Missing persistence is reported, not treated as boot proof.

## Reference proof of concept

```sh
sudo python3 -m installarr apply --reference --config /private/installarr.json \
  --name example --state-directory /private/existing-parent/state \
  --credentials-file /private/gui-admin.json
```

Supports protected bootstrap for all nine reference apps and prepares the signed
standard Docker engine when needed. Declare an explicit `data_root` containing media, downloads
and incomplete directories, with exact common mount assertions. The installer
bootstraps without published ports, verifies authentication and integrations, then
publishes reference ports on `bind_address`. It does not enable boot automatically.
Repeat with the same config/name/state to reconcile without prompting for credentials.
`reference_poc_ready` means selected bootstrap/path/auth checks passed. Inspect
per-app evidence for pending integrations. It does not establish real provider
access, Ombi family/request routing, reboot or a full clean-OS installation.

Fresh-engine orchestration and the shared-data wizard are implemented. Full pinned
profiles, Plex claim/grouped libraries/playback and Tautulli connection are tested.
Ombi and netboot published bootstrap/reruns also pass; Ombi external integrations
and family routing remain pending. See the maintained checklist for current gates.

## Full quality profiles

The configuration wizard offers pinned full TRaSH profiles: Radarr **Remux + WEB
1080p** as the preferred movie profile, plus **Remux + WEB 2160p** as a separate
manual option; Sonarr **WEB-1080p**. The movie HD profile excludes 2160p and stops
quality upgrades at 1080p Remux. Existing movie/series assignments are preserved.
Switch an individual movie to the 2160p profile in Radarr when desired.

Unattended configuration can specify:

```json
"quality_profiles": {
  "radarr": {
    "default": "9ca12ea80aa55ef916e3751f4b874151",
    "available": ["9ca12ea80aa55ef916e3751f4b874151", "fd161a61e3ab826d3a22d53f935696dd"]
  },
  "sonarr": {
    "default": "72dae194fc92bf828f32cde7744e51a1",
    "available": ["72dae194fc92bf828f32cde7744e51a1"]
  }
}
```

Include only selected applications. Omission preserves previous behavior. `default`
is the installer's preferred profile metadata, returned as a dynamically resolved
API ID for future request routing; Radarr's manual Add Movie dialog retains its
own remembered selection. Apply creates/readbacks complete pinned definitions,
refuses conflicting operator definitions, and never bulk reassigns media.

## Plex authorization and grouped libraries

Use `init-plex-claim --secrets-directory /private/local/plex-claim` to collect a
short-lived claim with hidden input. Put only the resulting **file path** in
`plex_claim_file`; never put the claim/token in JSON or command-line arguments.
`--claim-file` accepts a private0600 raw input file for unattended use; `--replace`
explicitly refreshes an expired stored claim. Apply waits for account readiness
and refuses publication when authorization is missing. Existing claimed servers
reuse their private server token. Plex does not use the shared GUI password.

`plex_server_name` controls the friendly name; `hostname` is detected/editable by
the wizard. Libraries support multiple folders, relative to `storage.media`:

```json
"plex_libraries": [
  {"name": "Movies", "type": "movie", "relative_paths": ["Movies", "Movies-2", "jeremymovies", "lenoramovies"], "language": "en-US"},
  {"name": "TV", "type": "show", "relative_paths": ["TV", "lenoratv", "jeremytv"], "language": "en-US"},
  {"name": "sports", "type": "other", "relative_paths": ["sports"], "language": "en-US"},
  {"name": "StandUp", "type": "movie", "relative_paths": ["StandUp"], "language": "en-US"},
  {"name": "Music", "type": "artist", "relative_paths": ["Music"], "language": "en-US"}
]
```

These are the operator's final defaults. Library/folder spelling and case match
for sports and StandUp. Low-resolution folders are excluded. Disney, Only Heather,
YouTube Videos and TubeSync Videos are forbidden library entries; apply reconciles
existing matching sections out of the Plex database using library metadata APIs.
It never deletes their media directories or calls a media-file deletion API.

Existing parent library IDs and media assignments are preserved. Normal apply
allows additional locations but refuses removing/repointing existing locations;
the development fixture corrections were explicitly scoped to installer-created
test metadata. Plex's data bind and Tautulli's Plex-log bind are read-only.

The current test Movies-2 location is empty. A separate production secondary
mount outside the primary media root remains unimplemented; this JSON example
does not claim to configure that separate filesystem. See CURRENT_PROGRESS.md.

Ombi has tested protected administrator bootstrap, actual Sonarr/Radarr connections
and movie/TV request dispatch to the preferred profiles and roots. Plex library
lookup/restart passes; matched-media availability, native family import and administrator on-behalf
routing now pass. Operator-confirmed Plex sign-in and genuine ordinary-user requests now pass
using the operator’s own account. No other people’s credentials are needed. netboot.xyz protects its GUI/Socket.IO with Nginx already
present in the reference image; it adds no authentication service/backend. Its
Node backend port3001 is unpublished; reference frontend3250, assets7171 and TFTP69
mappings are retained. DHCP/PXE client testing is outside installer scope.

## Optional Plex family presets

Set `"ombi_family_presets": true` or enable the wizard choice to select the named
family presets. This requires Ombi, Plex and at least one Arr app with the full
recommended1080p profile available. Lenora uses lenoramovies/lenoratv; Jeremy uses
jeremymovies/jeremytv. Beanie inherits global roots/profiles. All three receive
movie/TV auto-approval; Beanie also receives PowerUser. No local family passwords
are created, and Discord preferences remain disabled. Native Plex import excludes
unrelated known friends and restores the original import settings. A private
recovery journal handles interrupted temporary settings on reruns.

Native imports/settings and administrator on-behalf movie/TV routing passed minimal
physical fixtures with restart persistence. Operator-confirmed Plex sign-in, native ordinary-user requests using the
operator’s own account, and physical interrupted-import recovery now pass. Full
combined family apply and real provider/download acceptance remain open. One rapid request sequence hit an upstream SQLite write lock; normal
sequential reruns passed. No database workaround or blanket retry was added.

The Plex wizard retains all reference groups by default. You can select whole
libraries and edit Movies/TV folder lists while keeping one library per group.
The plan also lists selected app integrations and missing provider/backend inputs
without silently adding applications.

## Optional providers and private credentials

Provider choices are optional and contain no credentials. Reference selections:

```json
"providers": {
  "newshosting": {"connections": 100},
  "nzbgeek": {},
  "bazarr": {"enabled": ["opensubtitlescom"]}
},
"provider_secrets_file": "/private/provider-secrets/providers.json"
```

Include only providers whose corresponding apps are selected. Newshosting uses
news.newshosting.com/TLS563 with strict certificate verification; set connections
to your subscription limit. NZBGeek is configured directly as Newznab in selected
Sonarr/Radarr. OpenSubtitles.com and .org use separate accounts; this pinned Bazarr
adapter supports the .com provider, as confirmed by its installed modules.

Collect credentials on the server, through hidden prompts:

```sh
sudo python3 -m installarr init-provider-secrets \
  --secrets-directory /private/provider-secrets \
  --providers newshosting,nzbgeek,opensubtitlescom
```

The resulting providers.json is private0600, separate from config/checkpoints;
existing files are preserved. Never put values in command arguments, chat or Git.
`check-providers --config ... --name ... --provider-secrets-file ...` tests current
owned reference SAB/Arr connections without saving settings or enabling indexers.
It does not yet authenticate/search OpenSubtitles in Bazarr. Real Newshosting/NZBGeek provider apply/reruns passed for minimal Radarr/SAB and
Sonarr/SAB pairs, including the official100MB NNTP download. Native OpenSubtitles.com
authentication/search/download and scheduled Bazarr library-search passed.
Only OpenSubtitles.com is offered by the installer. Settings acceptance alone is
not a successful provider test. See TEST_RESULTS.md for current physical evidence.

Set `"bazarr_language_profile": "english-standard"` to create/read back a standard
English subtitle profile and use it for new movies and TV shows. It excludes forced
and hearing-impaired subtitles, preserves existing media assignments and unrelated
language profiles, and refuses conflicting definitions/defaults. Physical restart/
rerun tests passed. Yify, Supersubtitles and TVSubtitles are excluded from installer
selections. Historical test evidence for them does not represent current defaults.

Optional `storage.netboot_assets` selects a separate netboot asset directory. Add
matching `storage_mounts.netboot_assets` and `storage_checks.netboot_assets` entries
for a network path; its health marker and exact mount are checked before startup
and during supervision. Assets use911:1001 independently of the media identity.
A shared SMB mount cannot simultaneously force both identities. Omitting this
option preserves the local `configs/netbootxyz/assets` default. No asset server or
DHCP/PXE configuration is added.

Saved supervisors use immutable runtime snapshots. Inspect them with
`sudo python3 -m installarr audit-runtime --name NAME`. For an explicit runtime-only
update, stop `installarr-NAME.service` and `installarr-NAME-boot.service`, then run
`sudo python3 -m installarr refresh-runtime --name NAME --state-directory ORIGINAL_STATE`.
The command requires a completed reference deployment and compatible unchanged
Compose artifacts, saves a private backup and recovers interrupted replacements
before a new attempt. It leaves both units stopped and boot settings unchanged.
Start only the live unit, then rerun the original reference apply for app checks.
Image/configuration migrations and reboot acceptance remain separate work.

Optional `storage.media_secondary` supplies the `Movies-2` location from a separate
existing source. Give it matching storage mount/assertion entries and an existing
readable basename health marker. The source must be distinct from other storage
purposes. Plex receives it at `/media-secondary` as a read-only bind within the
same Movies library; primary/family folders keep their existing paths. The installer
requires that source to exist, creates no folders or markers there, and checks
service-UID reads instead of writes. Production source values must be supplied;
the test export's empty Movies-2 folder is only the default single-source fixture.

Ubuntu20.04/amd64 has an archived compatibility path using the official signed
Focal packages: Engine/CLI28.1.1, Compose2.35.1, Buildx0.23.0 and containerd1.7.27.
These packages installed and executed in20.04 userspace; full engine/systemd/boot
acceptance remains outstanding. Focal is absent from Docker's current supported
Ubuntu list; this path does not imply ongoing upstream support. Ubuntu22.04/24.04
use the current official repository with exact selected versions checkpointed.
See [Docker's OS requirements](https://docs.docker.com/engine/install/ubuntu/)
and [the official Focal archive](https://download.docker.com/linux/ubuntu/dists/focal/pool/stable/amd64/).

`menu` provides terminal navigation for a new config, plan, private credential
collection, Plex claim, explicit reference apply and status. Use
`sudo python3 -m installarr menu --config /path/installarr.json --name media-stack`
for provisioning/private stores. It uses `/var/lib/installarr-media-stack` as the
state directory unless overridden; the state parent must already exist locally.
Configuration/planning work without root. Apply is always an explicit menu choice
and a failed plan blocks it. Existing config files are preserved; choose another
filename to start new choices. Human menu acceptance remains on the test checklist.

Use `apply --reference --prepare-only` (or the menu preparation action) before
collecting a fresh Plex claim. It completes host/image preparation without reading
the claim file or starting application containers, reusing the same config/name/state.
Then collect the claim and apply normally. A preparation rerun preserves existing
application services and boot settings; it is not application acceptance.

Private inputs also support unattended provider JSON import with
`init-provider-secrets --credentials-file /private/input.json`. Provider and Plex
collectors accept `--filename` for the configured output basename. The menu honors
those paths. `init-smb-secrets` creates a root-private mount.cifs file using hidden
input or private JSON, with optional domain; it performs no mount/server setup.
Collectors can share a0700 private folder using independent metadata/locks, and
legacy stores are reused unchanged. GUI `init-secrets --config ...` validates the
selected apps' username constraints before saving. Application failures now expose
fixed safe diagnostics/statuses while arbitrary exception/response text stays hidden.


Physical-test scripts under `tools/` are developer experiments, not installation
steps. Their `Installarr-*` NAS fixtures and generated media are not copied into a
fresh deployment. Normal installation creates configured storage/app directories
and health markers only. Historical test fixtures are preserved until explicitly
reviewed for cleanup; the installer never bulk-deletes existing media folders.
