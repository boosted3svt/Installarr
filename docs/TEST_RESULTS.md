# Physical test results

## 2026-10-30: publication completed and fresh public clone verified

Published implementation e1fed73169336eb335475ae2af3937e99495d3ef to public main
through the existing GitHub connector with a lease on prior head c1aa297.40changed
files uploaded; resulting GitHub tree b1e95d7069637895ff2a67fd1112bbd8c721d5bd
exactly matches reviewed local index. Local HEAD/index/worktree synchronized.
Fresh unauthenticated clone /var/tmp/installarr-publication-clone-p_uxbhl4 verified
exact commit, executable launcher/help, no-argument nonterminal safe exit and
244tests (238passed/6skips). Result.json/tests.log retained there. This docs-only
follow-up records successful verification; no application changes since tests.

## 2026-10-30: publication and operator-led clean-test preparation

Operator explicitly authorized publication of all current reviewed implementation,
tests and handoff docs before reinstalling Ubuntu24.04.5. They will privately back
up/restore Codex conversation state; old installer/app databases are not restored
for acceptance. CURRENT_PROGRESS.md, SAVED_CHECKPOINT.md, CURRENT_SETUP.md and
FRESH_HOST_CODEX_HANDOFF.md now give a single current resume path and exact source/
folder/library/provider/family policy, with no private values.

Read-only current-host inspection discovered a NEW successful operator run:
selected setup-c2c7141a879e, Plex name HomeNet-Test2, seven apps, phase
reference_poc_ready, all bootstrap/published checks verified, automatic_startup
verified. Live unit installarr-family-c2c7141a879e.service active/enabled, bootstrap
inactive/disabled, seven containers running, Plex healthy. Prior family-media and
family-9ad2bb7ce113 units inactive/disabled. Exact .103 Public→/media/Media and
.102 Public→/media/Media-2 NFS identities verified. No API writes, service changes,
NAS/media reads or cleanup performed by publication inspection.

Final244-test host suites: htpc238passed/6skips and root242passed/2skips;
/tmp/installarr-publication-user.log and /tmp/installarr-publication-root.log.
Current244-test installed-wheel suites each242passed/2skips on official Ubuntu
20.04/Python3.8 and24.04/Python3.12 userspaces. Evidence directory:
/var/tmp/installarr-distribution-pr9mfxnw/{20.04,24.04}. Package entrypoints,
installed-source identity, pinned catalog/license and atomic runtime checks pass.
Wheel20.04:624215bytes, SHA256
23e037d8ddf731be5369b494650495746355979905bda1120e03c5061624207d;
wheel24.04:624213bytes, SHA256
db103ecdd099290b3a113bb50878c4edc14f4cf53051a9cca468e81eafb7109e.
These are userspace/package tests, not clean-OS/systemd/boot acceptance. Temporary
test containers have no host Docker socket, NAS or credentials mounted.

Python3.8grammar172files, shell syntax and git diff whitespace pass.823reviewable
files scanned against18actual private saved values and encoded variants: zero
matching files. GUI/provider passwords/APIkeys, Plex tokens/claims and family IDs
were never printed. reference_compose.yaml remains ignored/unpublished. Public
fresh-clone verification is recorded below with the publication savepoint.
Current live deployment left unchanged. No wipe/reboot/commit to private state.

## 2026-10-29: post-reboot Sonarr folder request and seven-app recovery

Operator reboot at21:15:16UTC restored securityfs. Continued setup ran all seven
bootstrap containers. SAB auth/storage/Newshosting checks passed; Sonarr configured
and verified shared GUI auth. Sonarr log shows GET rootfolder200, version200,
authenticated handler16:17:11.6CDT, no root POST response, then shutdown16:17:21.7.
Read-only SQLite showed0Sonarr roots/1user,0Radarr roots/users; no Arr integrations
or pinned profiles yet. Checkpoint bootstrap_auth_and_paths failed. This is
consistent with the10s HTTP deadline, but original curl stderr/status are not
retained, so low-level cause cannot be proved. Stop/exit137 during bounded cleanup
was not an OOM (Docker OOMKilled false). Plex had saved an account token privately.

Minimal owned Sonarr diagnostic started only its existing unpublished container,
waited for actual status, used60s request bound, and registered the existing
configured /data/media-tv: HTTP201 in0.518s. Actual root ID1/readback and repeat GET
passed; container stopped in finally. No data path/credentials changed, media
moved or duplicate root created. Slow cold request did not reproduce.

DockerHTTP now allows60s for Arr rootfolder GET/POST, retaining ordinary10s and
outer+5s deadlines. Root readback may scan NAS too. No blind POST retry introduced;
next resume checks collection before creation. Fixed AppAPIError(ValueError)
being swallowed by the broad transport exception handler; Arr timeout/transport
messages contain fixed app/operation labels and numeric statuses, never body,
stderr, inputs or credentials. Other adapters' existing diagnostic/retry contracts
remain compatible. Regression tests cover curl28/7, outer timeout, malformed
response, no retry, correct deadlines and synthetic secret exclusion.

Full current-source apply_reference with original selected config/name/state and
private GUI input completed in104.44s. Private result:
/var/lib/installarr-setup/installations/setup-9ad2bb7ce113/accepted-result.json.
Status reference_poc_ready; all7authenticated published app checks passed, existing
Plex claim reused, full pinned Arr profiles/sizes/provider links, six Radarr roots
(including secondary NAS), three Sonarr roots, SAB categories, Bazarr settings,
four Plex libraries, native Ombi family preferences and Tautulli link configured.
Active unit installarr-family-9ad2bb7ce113.service remains boot-disabled; seven
live containers, bootstrap stopped. Retired setup stayed stopped. No runtime
snapshot refresh, boot enablement, reboot, new NAS fixture/media move or commit.

244-test suite passed: htpc238/6skips, root242/2skips. Logs:
/tmp/installarr-post-reboot-tests.log and /tmp/installarr-post-reboot-root-tests.log.
First development suite exposed missing Plex subclass label handling in new error
context; corrected by scoping detailed diagnostics to Arr ports and preserving
other adapters' behavior before final suites/full physical apply. Changed files
parse as Python3.8; git diff whitespace passes. This is saved-install recovery,
not proof of first cold request reliability or full clean-OS/boot acceptance.

## 2026-10-29 21:04 UTC: operator guided startup blocked by AppArmor interface

Follow-up read-only current-boot journal investigation located the preceding event:
AppArmor initialized at20:57:02UTC; kernel audit confirms docker-default loaded
20:57:10UTC. `journalctl -b _COMM=sudo -o short-iso` records
`COMMAND=/usr/bin/umount -a` at20:58:08UTC, then setup elevation20:58:32UTC.
Concurrent systemd events show boot EFI, snap, kernel config/tracing/debug,
mqueue and hugepages mounts deactivated. No individual securityfs unmount event
was logged, but broad unmount after proven successful AppArmor startup explains
the later missing interface. It was not disabled at boot. Full system mount repair
remains outstanding; no reboot/mount/service changes made by this investigation.

Read-only follow-up inspected active-setup.json, selected installation metadata,
state/state.json and nested mount/directory/bootstrap checkpoints for
setup-9ad2bb7ce113. Configuration saved21:01:32UTC; bootstrap Compose
written21:02:00UTC; failed state saved21:04:05UTC. Accounts/prerequisites/mounts/
directories/Docker/images/Tautulli seed verified; bootstrap_auth_and_paths absent.
No API configuration was reached. Prior switch-state reports complete.

`docker inspect` restricted to owned containers' Name/State/Mounts showed all seven
bootstrap containers Created, PID0, never started, exit128, each reporting:

```text
Could not check if docker-default AppArmor profile was loaded: open /sys/kernel/security/apparmor/profiles: no such file or directory
```

Docker journal corroborates repeated failures until21:04:02UTC. Read-only
`findmnt -rn -t securityfs` found no mount; the profiles and lsm interface files
are absent, while /sys/module/apparmor/parameters/enabled contains Y. Docker info
reports AppArmor support; apparmor.service active/exited is insufficient runtime
proof. No sys-kernel-security.mount unit was found. Follow-up cause evidence is
above; no disabling or bypass of AppArmor was attempted.

Exact findmnt -M checks confirmed .103 Public at /media/Media and .102 Public at
/media/Media-2, both NFS, matching operator choices. No media contents inspected.
Bootstrap supervisor is now inactive/disabled after failure cleanup; previous
family-media also inactive/disabled; new published unit does not exist. Zero running
containers. New Plex Preferences.xml absent, so no new claim acceptance occurred.
Container records retain the failure even though supervisor post-stop checkpoint
now reports stopped. Readiness polling raises ApplyError on timeout; CLI's generic
ValueError handler suppresses its message, explaining the operator's unhelpful text.

Documentation/checkpoints updated; no code, mounts, packages, services, credentials,
NAS contents or boot settings changed by diagnosis. No tests run for this docs-only
record. Repair/normal Docker startup and same-saved-setup rerun remain outstanding.

## 2026-10-29: approved standardized storage, sizes and fresh-setup flow

Operator approved PROPOSED_PRODUCTION_STORAGE_CHANGELOG.md implementation and
resolved three choices: new standardized folders empty, no Music library in new
setup, netboot files in the dedicated export's assets child. No media relocation,
production outage or reboot was authorized. The implementation is in the existing
checkout, not committed/pushed; original nine-app family-media deployment remains
active/enabled on its original snapshots and isolated export.

Implemented explicit folder_map (new guide default; legacy configs compatible),
local/NVMe/NAS/existing choices, separately asserted download storage, editable role
folders and NFS endpoint prompts. Canonical container paths are /data/media-* plus
/data/unfinished-downloads and /data/finished-downloads. Secondary is
/data/media-movies-2. New library names Movies/TV Shows/Sports/Standup. Strict binds
remove unrelated media access from SAB/Arr/Jackett; Plex media stays RO and its local
config/transcode remains RW. Bazarr can write subtitles beside managed media.
Role-specific guarded binds, directory markers, supervisor checks and systemd
RequiresMountsFor supplement exact filesystem assertions. Missing selected drives
cannot silently become root-disk storage. Categories movies/tv are prepared before
startup; inside-container UID/access checks and relevant Arr missing-directory
health warnings gate success. All Arr/family roots derive from the same role map.

Quality-size adapter uses manifest-verified pinned movie/series size documents,
runtime qualitydefinition/limits and dynamically resolved IDs; unlimited maxima
map to API null, preferred values stay explicit. Only tested factory defaults or
already-pinned values are accepted, so custom edits refuse before any size writes;
unrelated rows/titles/fields remain unchanged. Per-row interrupted writes resume.
These are separate from full pinned profiles/CF scores. Schema/default references:
[Radarr controller](https://raw.githubusercontent.com/Radarr/Radarr/v6.4.4.10685/src/Radarr.Api.V3/Qualities/QualityDefinitionController.cs),
[Radarr defaults](https://raw.githubusercontent.com/Radarr/Radarr/v6.4.4.10685/src/NzbDrone.Core/Qualities/Quality.cs),
[Sonarr defaults](https://raw.githubusercontent.com/Sonarr/Sonarr/v4.0.20.3014/src/NzbDrone.Core/Qualities/Quality.cs).

Fresh setup flow preserves previous settings/DBs, creates separate private state,
reuses private GUI/provider/family inputs, and stops/disables only verified prior
owned units/containers after Start installation confirmation. Only conflicting
managed mounts/fstab entries may be replaced; unrelated entries refuse before
retiring anything. Fstab backup is private/durable/checksum-tracked. Nonempty local
netboot mountpoint is not hidden: only the exact prior verified assets child can
be atomically archived unchanged; unrelated contents refuse. Old claimed Plex DB
is kept stopped, not copied into a concurrent server. Fresh Plex DB needs its own
private owner claim. Root fixture tests cover selective persistence/idempotence,
unrelated mount refusal, local asset preservation, save-only selection and unsafe
selection symlink refusal. Actual production switching is still operator-run
acceptance; these tests do not certify that unperformed live transition.

### Physical isolated tests on Ubuntu24.04.5

All NAS operations checked exact test source
192.168.1.102:/share/MD0_DATA/Public/installarr at /media/Media or /media/NAS;
no production exports were inspected/mounted. New folders are uniquely owned test
fixtures, not the original supplied examples. Apps ran unpublished, minimal pairs;
no second complete stack or external deployment backend was added.

1. `sudo python3 -u tools/test_physical_arr_download_import.py --app radarr --scoped`:
   first implementation /var/tmp/installarr-arr-import-wwgpm9u4 passed native
   release→synthetic loopback NNTP/SAB→normal import, exact bytes/hash/2000:2000 and
   restart. Enhanced final test /var/tmp/installarr-arr-import-r09mkng4 passed
  454484generated bytes, SHA256
   a403d5ab10e116e1b87aa6d344164c61f6264700aa5edcbadad81ef4f84ae984,
   grabbed/downloadFolderImported history, forbidden paths absent, category visible,
   all14movie size limits persisted, stable root/download-client IDs on rerun.
2. Same command with `--app sonarr --scoped`:
   /var/tmp/installarr-arr-import-nl0gzniw passed454501bytes, SHA256
  16cddac68ceaf240e7b77c11f528b604b7a6189e5da32ec8d3270c7c48cae3ff,
   normal import/history,2000:2000, restart, category/scopes and14series size limits.
   Fixture advertised release size4GiB is synthetic metadata; actual bytes above
   are the transferred/generated content, never a real-provider download claim.
3. Final paired reconfiguration/readback (final-roots.json in the latter two work
   directories) verified all scoped Arr roots even without Ombi selected, sizes,
   inside-container service-UID access, unchanged content and stable reruns.
4. Radarr/Bazarr minimal pair with secondary host
   /media/NAS/Installarr-Scoped-Secondary-14a628b2 mapped to
   /data/media-movies-2: actual root ID6, UID2000 RW access, Bazarr's own remote
   Radarr6.4.4.10685 lookup, restart and rerun passed. Evidence first final work
   directory's secondary-result.json. This is the isolated export at two mounts,
   not proof of independent production NAS export access.
5. Plex-image diagnostic with actual generated startup guard and RO media binds:
   all fixture media write attempts denied; download folders unmounted. No PMS or
   duplicate claimed identity started. Evidence plex-bind-result.json in the same
   work directory. New combined claimed library creation remains operator-run.
6. `sudo python3 -u tools/test_physical_scoped_local.py`:
   /var/tmp/installarr-scoped-local-zxdo3fsz/result.json passed unpublished local-only
   SAB, OS NVMe ext4 source /dev/nvme0n1p2, restart/rerun/categories/scopes and
   simulated absent drive refused before creating any data/config directories.
   Not acceptance of a separately mounted physical spare NVMe or its boot behavior.

Tested image versions/digests remain the manifest pins: Radarr6.4.4.10685-ls324
(084b3b2ab1d0ef930660727259546a241f2bdf67c9ed085d54bf1486a6887c9b),
Sonarr4.0.20.3014-ls1
(48e36b608b461273b9dae857725cd0561a127f2c694b687318f6d0c5ce63e5c9),
SAB5.1.3-ls278
(3ac1c9ea03bafa2588dd8acdcb809857bae305e71d2d90e11d689c78076a9c01),
Bazarr1.6.2-ls370
(9a625883f054e722795affe5e3ca71057e6ed817ecdf99f4a99624346fcc509c).
Plex diagnostic used unchanged official pinned1.43.5.11079-b3b13e506 image; no
new Plex server acceptance is implied by this shell/guard test.

### Regression, packaging, terminal and privacy checks

- Final `python3 -m unittest discover -s tests -v`:242tests,236passed/6skips in9.065s
  as htpc; root242tests,240passed/2skips in9.039s. Logs
  /tmp/installarr-standard-user-complete.log and
  /tmp/installarr-standard-root-complete.log. Initial expanded suite exposed three
  obsolete guide transcript/expectation tests; adapted to the new explicit storage
  questions and internal sudo continuation flag. No failing implementation test
  was suppressed. New tests exercise all511optional scoped-render subsets.
- Native Docker Compose5.6.1 parsed1022bootstrap/published combinations, all passed:
  /var/tmp/installarr-scoped-compose-tl78jgxe/result.json.
- Actual PTY `sudo python3 -u tools/test_guided_terminal_current.py`: all9apps,
  local-only explicit paths, four libraries, save-only/no provisioning/private-input
  collection passed; /var/tmp/installarr-guided-preview-i0ookiu8/result.json.
- Final `sudo python3 -u tools/test_distribution.py`: installed wheels passed242
  tests/240passed/2skips on both official Ubuntu20.04/Python3.8 and24.04/Python3.12.
  /var/tmp/installarr-distribution-id12iq8_/{20.04,24.04}/result.json/acceptance.json.
  Final wheel source digests equal checkout,625pinned documents/license intact,
  console scripts/imports/atomic runtime passed. Focal wheel623851bytes SHA256
  84a11f6128c9ea258f9775ed42c4a8a230fd84b6b52d324155ba67b764b02e47;
  Noble623849bytes SHA256
  d7123544e3ca088dc5e6f70dbc3cda07c7b41fcb9245395b860a222d396e4d9e.
  Earlier241-test wheel run at /var/tmp/installarr-distribution-m8nk4426 passed too;
  final repeat includes subsequent safety/validation changes. Userspace containers
  have no host socket/NAS/private inputs and do not replace real systemd/boot tests.
- Python3.8grammar172files, shell syntax and git diff whitespace passed.819
  reviewable files scanned against current GUI/provider passwords/keys, Plex
  token/claim and Discord IDs: zero matches. No secret values printed.
- All disposable app containers/networks stopped/removed. Generated NAS fixtures
  retained only at the exact test paths above; old supplied examples unchanged.
  Existing9-app family-media service remains available on original test config.
  No fixture command running, production mount switch, reboot, commit or push.

## 2026-10-29: fresh bootstrap Newshosting connection-limit refusal

Operator resumed guide and privately supplied Plex claim; bootstrap configuration
failed at Newshosting before server settings were saved. Checkpoint phase failed,
bootstrap_auth_and_paths failed; preparation steps remained verified. All9owned
bootstrap containers stopped by failure handling, with no published deployment.

Host strict TLS verification/greeting to news.newshosting.com:563 passed in0.18s,
greeting200. Saved credentials used privately: AUTHINFO USER381/PASS502. No raw
reply, credential, API key or claim printed. Reply classified using fixed booleans:
connection-limit wording present, incorrect-login/account-restriction wording absent.
This is an account-limit refusal, not evidence of invalid credentials.

Minimal diagnostic started only the owned unpublished SAB container. Initial
app_client wait was interrupted because its bundle audit requires all apps running;
finally stopped SAB. Audited direct SabHTTP transport then tested native API without
saving settings: accepted false,502present, TLS-error/timeout/invalid-login wording
absent. SAB stopped afterward; docker ps empty, no diagnostic process remains.
Operator confirmed another downloader is using subscription and chose to pause it
themselves before retrying. No production apps inspected/stopped and no credentials
changed. No full apply rerun by Codex while operator prepares the next GUI run.

Added fixed Newshosting connection-limit guidance for known502connection-limit
messages on initial/saved tests; arbitrary server messages remain unprinted. Tests
verify guidance, privacy and generic fallback for other refusals/malformed results.
Full224-test suite219passed/5skipped in5.936s; log
/tmp/installarr-provider-limit-regression.log. Changed files pass Python3.8grammar
and whitespace. No commit/push/reboot. Operator resumes `./installarr.sh` after
freeing connections; provider success/application startup still await that run.

## 2026-10-29: actual fresh-host NFS preparation and RPC discovery

After shared GUI/provider/family hidden prompts, operator's guide returned generic
ValueError during preparation. Root-private checkpoints identified accounts and
prerequisites verified, mount-0 failed before directories/Docker. Saved config had
production defaults and all9apps; no claim was collected. Operator explicitly
selected isolated test export for further work. No production export was retried.

Installed nfs-common1:2.6.4-3ubuntu5.1 and rpcbind1.2.6-7ubuntu2; rpcbind service and
socket active. TCP checks to test NAS192.168.1.102:111unreachable,2049/30000reachable.
Private-namespace approved-export mount with ordinary NFSv3 discovery exceeded
30sdeadline; UDP-discovery variant returned32/Connection timed out. Workers reaped,
no leaked mount. Explicit port2049,mountport30000,mountprotoUDP,mountvers3 mounted
immediately; exact kernel source/type/options read back, then unmounted with no NAS
writes. This matches the older exact-source transport evidence; installing another
Ubuntu package is not the missing step on this host.

Added optional validated nfs_transport to NFSv3 declarations: exact four supported
endpoint fields, integer port bounds, mount protocol and version checks. Shared
declarations must agree; explicit endpoints avoid discovery even with no existing
mount and carry into fstab, retaining hard/TCP data semantics. No arbitrary mount
options, weakened locking or global NAS-port defaults. Failed mount commands now
raise fixed HostPrerequisiteError guidance rather than opaque ValueError. Existing
automatic kernel transport reuse remains limited to the exact matching source.

Full suite `python3 -m unittest discover -s tests -v`:223tests/218passed/5skipped,
5.923s; /tmp/installarr-nfs-regression.log. New tests cover no-discovery endpoint
use, persistence, invalid options and contradictory shared mount declarations.
Changed Python files pass3.8grammar; whitespace check passes.

Saved settings switched to isolated source at /media/Media and /media/NAS, data
folders Installarr-Clean-Test/Primary and Installarr-Clean-Test/AdditionalMovies.
Original settings/private failed checkpoints preserved in /var/lib/installarr-setup
with before-isolated-20261029T175656Z suffix. Separate GUI/provider/family stores
retained unchanged. Installer apply_reference prepare_only now passed exact mounts,
fstab persistence, directory/service-UID write checks and signed Docker/standard
engine setup. Kernel confirms both mounts use only approved isolated export and
explicit verified endpoints. Application image downloads underway; app containers
not started. Docker/containerd boot-disabled. No claim, reboot, production access,
commit or push. Final continuation returned reference_prepared; every step verified,
all9exact pinned images present and zero containers confirmed. Preparation process
exited; operator can resume saved setup through `./installarr.sh` without overlap.

## 2026-10-29: fresh-host guided input failure after OpenSubtitles

Operator transcript reproduced against HEAD's original guided.py using in-memory
execution, mocked mount inventory/account discovery and the exact supplied answers.
Primary mount prompt accepted `yes`; media containment correction also accepted
`yes`. Final plan raised `Directories must be absolute, non-root paths without
parent traversal` immediately after the final provider-selection question. No
provider request or Discord collection was involved, and setup had not saved its
settings or started provisioning.

Fixed immediate folder/source validation in both NFS sections and repeated
containment correction for both media paths. Folder errors explain full paths,
Enter defaults and why yes/no is inappropriate. Regression replays the reported
eight-app selection, rejects both yes mount answers and reaches final validated
configuration with OpenSubtitles.com/family presets preserved. Additional coverage
checks repeated outside-mount answers, invalid NFS sources, invalid folder forms
and hidden optional Discord input with blank/retry/no-value-output behavior.

`python3 -m unittest discover -s tests -v`:221tests,216passed/5skipped in5.908s;
log /tmp/installarr-guided-regression.log. Changed Python files pass Python3.8
grammar parsing; `git diff --check` passes. Tests mock host discovery/provisioning;
this is not combined fresh-systemd or boot acceptance. No package/mount/service,
private credential or NAS changes, reboot, commit or push performed. Operator can
rerun `./installarr.sh` using isolated test storage settings in
FRESH_HOST_CODEX_HANDOFF.md; production defaults remain outside test authorization.

## Current coverage after review

This is a chronological experiment record. Historical blockers remain below as
evidence of what was true at each test; they are superseded by later results.
Acceptance of Ubuntu 20.04+ is a product policy, not proof of physical testing on
every release. Physical tests here used Ubuntu 22.04.5.

| Area | Current evidence | Still open |
| --- | --- | --- |
| Accounts/identities | Real creation/recovery, UID2000 and netboot911:1001 | Other clean OS releases |
| Storage | Exact-source/UID probes, directories, NFS mount/fstab private-namespace acceptance, shared-data hardlinks | Actual NAS outage/reboot, separate secondary media source |
| Docker | Signed recorded staging and approved standard bridge DNS/outbound HTTPS; active-engine reruns | Clean-OS combined acceptance |
| Lifecycle | Pre-init refusal, storage-loss stop/recovery/crash fallback, multiple bounded service-identity workers | Boot/outage, runtime-snapshot upgrade audit |
| App bootstrap | All nine pinned adapters; protected published HTTP and minimal apply/reruns | All optional combinations/dependencies |
| Profiles | Full commit-pinned HD/UHD/Sonarr profiles, runtime schemas, readback/restart/reference apply | Ombi per-user routing integration |
| Plex/Tautulli | Real claim, grouped library readback, operator movie/episode playback, real Tautulli link/read-only logs | Production secondary mount and final combined acceptance |
| Ombi | Local Admin/JWT auth, DB ownership/gate, published HTTP/apply rerun | Plex/family import, Arr connections, requests/routing |
| netboot | Existing-image Nginx GUI/Socket.IO auth,911:1001 writes, restart/published apply | Additional asset source choices; DHCP/PXE clients out of scope |
| Provider behavior | Generated NNTP bytes and prior Arr/SAB connections/file recognition | Real indexers/providers and app-initiated dispatch/downloads |

Current live units/configs are in CURRENT_PROGRESS.md. Later operator corrections
supersede earlier library and profile guesses. Historical paragraphs below retain
what happened at each experiment and must not be used as current resume commands.

Current OS policy (operator correction, 2026-10-27): Ubuntu 20.04 and newer are
accepted, including 22.04 and 24.04. Earlier references below to a 24.04-only gate
describe historical tests and have been superseded. Version acceptance does not
prove that all host adapters or app images have been tested on each release.

Current privilege status: operator enabled sudo; real account/resume tests and
service-UID NAS probes passed as recorded below. Earlier sudo and
service-UID blockers below are historical. A real reboot remains untested.

Current Docker status: signed Docker packages are staged, an isolated daemon-restart
storage gate passed, and generated Sonarr/Radarr Compose/entrypoints are now tested.
Ongoing storage-health supervision passed; real reboot remains untested. Earlier
Docker-unavailable and Compose-not-integrated statements below are historical.

## 2026-10-27 — account adapter and isolated NFS probe

Scope: existing checkout on the isolated physical machine. No production apps,
sibling NAS directories, disks, SSH, firewall, networking or fstab were modified.
No reboot was requested or performed. No containers were launched.

### Environment and mount verification

- `/etc/os-release`: Ubuntu 22.04.5 LTS; Python `3.10.12`, architecture x86_64.
  This differs from the supported fresh-provisioning target Ubuntu 24.04.
- `dpkg-query -W -f='${Package} ${Version}\n' nfs-common util-linux python3`:
  nfs-common `1:2.6.1-1ubuntu1.2`, util-linux `2.37.2-4ubuntu3.6`, python3
  package `3.10.6-1~22.04.1` (interpreter version above).
- `findmnt --json --target /media/installarr --output TARGET,SOURCE,FSTYPE,OPTIONS`
  executed outside the sandbox: target `/media/installarr`, source
  `192.168.1.102:/share/MD0_DATA/Public/installarr`, filesystem `nfs`, `rw`, NFSv3.
  The sandbox presents the same mount as read-only; it is not reliable evidence
  of actual host write permissions.
- `sudo -n true` outside the sandbox failed: a password is required. No privileged
  account creation, package installation or Docker installation was attempted.
- `python3 -m installarr preflight`: exit 0, `supported_target: false`;
  Docker/Compose unavailable in this session. Inventory is not readiness proof.

### NAS experiment

Command: `python3 tools/probe_test_mount.py`, outside the sandbox, exit 0.
The script opens the authorized directory and verifies its exact source/type/target
with `findmnt` via the inherited directory descriptor before writing. Descriptor
relative operations avoid falling through to an unmounted local directory.
It creates one randomly named `.installarr-probe-*` directory in the authorized
subtree, writes a new 0600 sentinel, flushes/fsyncs, reopens and compares its contents,
then deletes only its own sentinel and directory. It does not list or read existing
NAS files. Write, fsync, readback and cleanup passed as UID 1000/GID 1000.
This does **not** prove service-UID permissions, mount persistence, mount-loss
handling, Docker restart protection or application functionality.

### Implementation and checks

- Added `prepare-accounts`: rejects unsupported OS/non-root execution; prechecks
  all account collisions, creates missing groups and nologin users without home
  directories, and reads identities back after commands. Existing accounts are
  never changed. Reserved netbootxyz identity conflicts include the name as well
  as UID/GID overlap.
- Added private execution state: trusted ancestors, 0700 directory, 0600 files,
  no symlinks, regular single-link state files, process lock, plan fingerprint,
  atomic replacement and file/directory fsync. Failed/running/completed attempts
  all reconcile host facts on reruns. FIFOs are opened nonblocking and rejected.
  This is an account checkpoint foundation, not a general completed installer.
- Initial baseline: `python3 -m unittest discover -s tests -v`: 23 passed.
- First expanded run in sandbox: 28 passed, four checkpoint tests errored because
  root-owned ancestors appear as UID 65534. Security requirements were retained.
- Expanded suite outside the sandbox: 32 passed before the FIFO regression case
  was added. Final `python3 -m unittest discover -s tests -v` outside the sandbox:
  **33 passed**, exit 0 (0.157 seconds). `git diff --check` also passed.
- CLI gate exercised with a temporary private configuration and temporary state
  path: `main(['prepare-accounts', '--config', <temporary config>,
  '--state-directory', <temporary state>])` returned 1 on Ubuntu 22.04 and did not
  create a state directory. No account commands ran.
- Account creation/interruption tests use simulated account databases and commands;
  they are not evidence of real privileged account provisioning.

### Outstanding gates

Real account creation and rerun verification require a supported Ubuntu 24.04 host
and root access. Do not upgrade/reinstall this host implicitly. Still outstanding:
service-UID NAS tests, protected secrets, prerequisite and signed Docker install
adapters, mount/fstab reconciliation and backups, fail-closed boot/Docker restart
protection, Compose generation, pinned tested images, authenticated application
adapters and functional end-to-end tests. No installation-readiness claim is made.

## 2026-10-27 — protected GUI credentials and service-identity write checks

Implemented `init-secrets` with hidden terminal input and an unattended protected
JSON-file import. The store uses the existing private-directory/process-lock
checks, validates 0600 single-link regular files owned by the executor, rejects
symlinks/FIFOs, publishes complete credentials without replacement, and fsyncs file
and directory. Existing valid credentials are reused without collecting input.
Invalid existing files are retained and refused. No credentials enter checkpoints
or command output. This protects plaintext at rest through filesystem permissions;
it does not configure application authentication or implement rotation.

Implemented `check-storage-writes`. The worker requires a positive non-root UID/GID;
root execution clears supplementary groups and drops GID then UID before accessing
storage. Unprivileged execution refuses mismatched identities and extra groups.
Both parent and worker check exact mount assertions; the worker rechecks after
opening the directory and holds its descriptor for temporary writes and cleanup.
It checks write/fsync/reopen/readback in a unique directory without examining
existing files. Failed mount assertions and read-only mounts refuse writes.
The worker timeout is ten seconds; interruption or blocked NFS can leave probe
artifacts. Sentinel reads, persistence and mount-loss protection remain separate.

Commands/results:

- `python3 -m installarr --help`: exit 0; new commands registered.
- `python3 -m unittest discover -s tests -v`, outside the sandbox: **44 passed**,
  exit 0 (0.207 seconds). Credentials are synthetic and temporary. Coverage includes
  unattended import without credential output, reuse without prompting, corrupt
  stores, unsafe modes/hardlinks/symlinks/FIFOs, empty passwords, missing/wrong/ro
  mounts before writes, local temporary write/readback/cleanup and worker timeout.
  The local I/O unit test mocks the supplementary-group list; it is not a physical
  service-permission claim. No real privilege transition was executed.
- Physical worker exercised outside the sandbox using
  `probe_service_write('/media/installarr', {'mountpoint': '/media/installarr',
  'source': '192.168.1.102:/share/MD0_DATA/Public/installarr', 'fstype': 'nfs'},
  1000, 1000)`. Operator groups were `[4,24,27,30,46,100,110,1000]`; result was
  `failed`, as required because supplementary operator groups would otherwise mask
  permission failures. Worker refuses before opening the NAS or writing. Wrapper
  command exited 0 because it printed the returned diagnostic; the check failed.
- No NAS writes were made during this follow-up. No packages, accounts, mounts,
  host settings, containers or real application credentials were changed.

Next gates: test actual privilege dropping and service-UID NAS write success with
root access; implement signed prerequisite/Docker adapters, reconciled storage
preparation and fail-closed startup before Compose or application deployment.
The machine remains Ubuntu 22.04; provisioning mutations stay gated to Ubuntu 24.04.

## 2026-10-27 — corrected Ubuntu version policy

Operator clarified that the 24.04-only target was an obsolete assumption. Account
provisioning and preflight now share an Ubuntu 20.04-or-newer check; root remains
required for account changes. Updated current README/AGENTS instructions, retaining
historical test records above. Tests cover accepted 20.04/20.10/22.04/24.04/26.04,
rejected 18.04, missing/malformed versions and non-Ubuntu releases.

`python3 -m unittest discover -s tests -v` outside the sandbox: **45 passed**,
exit 0 (0.183 seconds). Local preflight now reports Ubuntu 22.04.5 LTS with
`supported_target: true`. No host changes or NAS writes were made.

## 2026-10-27 — sudo enabled; real account and service-UID NAS tests

Operator configured sudo access. `sudo -n id` outside the sandbox returned
`uid=0(root) gid=0(root) groups=0(root)`. Existing sandbox approvals remain in use.
Rechecked `findmnt --json --target /media/installarr --output
TARGET,SOURCE,FSTYPE,OPTIONS`: exact target `/media/installarr`, source
`192.168.1.102:/share/MD0_DATA/Public/installarr`, type `nfs`, `rw`, NFSv3.
Only that confirmed NAS subtree was written. No fstab/mount settings, disks, SSH,
firewall, networking, production applications or sibling NAS directories changed.
No packages or containers were installed and no reboot occurred.

### Real account creation, interruption and rerun

Specific name/ID lookups confirmed both proposed users/groups and numeric IDs were
absent, with no collisions: installarr-test 2000:2000 and nbxyz 911:1001.

Command: `sudo -n /usr/bin/python3 -B tools/test_physical_accounts.py`, exit 0.
The retained harness deliberately executed groupadd for installarr-test, raised an
interruption before useradd, and verified a failed checkpoint and absent user.
It then invoked the actual `prepare-accounts` CLI to resume the same account plan:
existing matching group reused, missing user created, and nbxyz group/user created.
A second CLI invocation returned verified and preserved account records exactly.
Readback confirmed requested UID/GID, home `/nonexistent`, shell
`/usr/sbin/nologin`, and only the intended primary group for both accounts.
`sudo -n passwd -S installarr-test` and `sudo -n passwd -S nbxyz` returned `L`
(password locked). No password hashes or credentials were printed.

Retained test resources, intentionally available for later isolated experiments:

- user/group `installarr-test`, UID/GID 2000:2000;
- user/group `nbxyz`, UID/GID 911:1001;
- root-owned private checkpoints `/var/lib/installarr-physical-test-accounts`.

The temporary CLI configuration under `/var/tmp/installarr-accounts-*` was removed
by the harness. No home directories, application databases or media directories
were provisioned. Later harness reruns preserve matching existing identities and
do not repeat the interruption once the user exists.

### Actual privilege-drop and NAS checks

First invoked `probe_service_write` as root for the exact confirmed mount with
2000:2000 and 911:1001: both returned verified with write/fsync/readback/cleanup true.
Then ran `sudo -n /usr/bin/python3 -B tools/test_physical_storage.py`, exit 0:

- Reverified exact mount identity and repeated both service-UID NAS probes: passed.
  The worker clears supplementary groups, drops GID then UID, and checks the
  mount via its held directory descriptor before creating its own temporary data.
- Deliberately wrong NFS source: failed as required before writes.
- Simulated missing NFS mount using a new service-owned local `/var/tmp` directory:
  failed as required; local directory remained empty. No actual mount was removed.
- Root-owned 0700 local fixture, correct local mount assertions, service UID 2000:
  access refused after privilege dropping; directory remained empty.
- All owned NAS sentinel/probe directories and local storage fixtures were removed.

This establishes scoped host-identity access for the tested NFS export. It does not
validate an image entrypoint's runtime identity, existing-library permissions,
NAS disappearance during running containers, boot persistence, Docker restart
protection, netbootxyz application permissions or DHCP/PXE client reachability.

Next: signed prerequisite/Docker adapters and fail-closed service startup, followed
by minimal disposable container tests. Full installer readiness remains unclaimed.

Post-experiment regression: `python3 -m unittest discover -s tests -v` outside the
sandbox: **45 passed**, exit 0 (0.210 seconds). `git diff --check` and
`python3 -m compileall -q installarr tools tests` passed.

## 2026-10-27 — signed Docker staging and container-side storage startup gate

### Initial inspection and approved scope

Read README.md and docs/PHYSICAL_TEST_HOST.md before host experiments. Specific
Docker/containerd binaries, packages, standard units, daemon config, Docker source
files/keyring and policy-rc.d were absent. ca-certificates, curl and gnupg were
already installed. No Docker workloads were present to preserve. Root-owned
`/var/lib/installarr-physical-network-baseline.json` records pre-install hashes of
link/address/route output, IPv4/IPv6 forwarding values and firewall rules, excluding
iptables-save comments/timestamps. No network configuration was changed.

Docker documentation notes that its normal daemon manages firewall/bridge state.
To remain within scope, the adapter masks `docker.service`, `docker.socket` and
`containerd.service` before installation and leaves them masked. A separate test
daemon disables bridge creation, iptables, ip6tables, IP forwarding changes,
masquerading and userland proxy. No Docker bridge networks or published ports were
created. No SSH/firewall/VLAN/DHCP/fstab/disk configuration was changed. No reboot
occurred; only the isolated Docker test daemon was restarted during the experiment.

### Signed, resumable Docker package staging

Implemented `prepare-docker` with root/Ubuntu gating, conflict refusal (no automatic
package removals), exact-content/no-replacement system file creation, a dedicated
Signed-By keyring, Docker HTTPS repository and primary-key fingerprint verification
against `9DC858229FC7DD38854AE2D88D81803C0EBFCD88`. Existing different repository
files/configuration are preserved and refused. Explicit APT options retain signature
checks and refuse package removals; needrestart runs in list-only mode. Version
selection is restricted to Docker's official repository. Private checkpoints keep
exact package versions and read them back on every rerun. No automatic upgrade or
downgrade occurs if the installed versions differ from the saved selection.

Command: `sudo -n /usr/bin/python3 -B -m installarr prepare-docker`, exit 0;
repeated after physical tests, exit 0 with unchanged versions:

| Package | Exact installed version |
| --- | --- |
| docker-ce | 5:29.9.2-1~ubuntu.22.04~jammy |
| docker-ce-cli | 5:29.9.2-1~ubuntu.22.04~jammy |
| containerd.io | 2.4.2-3~ubuntu.22.04~jammy |
| docker-buildx-plugin | 0.38.1-1~ubuntu.22.04~jammy |
| docker-compose-plugin | 5.6.1-1~ubuntu.22.04~jammy |

New repository/key files: `/etc/apt/sources.list.d/installarr-docker.sources` and
`/etc/apt/keyrings/installarr-docker.asc`. Private checkpoint directory:
`/var/lib/installarr-docker-install`. No existing persistence file was replaced,
so no replacement backup was necessary. No user was added to the docker group.

Upstream current Docker install guidance lists Jammy, Noble, Resolute and Stonking;
Installarr still accepts Ubuntu 20.04+, but Focal needs a separately validated
Docker path rather than claiming support for an untested modern package install.

### Isolated daemon

Command: `sudo -n /usr/bin/python3 -B -m installarr prepare-test-daemon`, exit 0;
rerun also returned 0 without changing configuration or package versions.
Engine `29.9.2`, Compose `5.6.1`, storage driver overlay2 with the classic image
store for this experiment. Test unit `/etc/systemd/system/installarr-test-docker.service`
is running but not enabled at boot. Socket is
`unix:///run/installarr-docker-test/docker.sock`; configuration/data/state are under
`/var/lib/installarr-docker-test`, with runtime state under `/run/installarr-docker-test`.
The standard services remain masked. `sudo -n systemd-analyze verify
/etc/systemd/system/installarr-test-docker.service` exited 0; it emitted an unrelated
warning about the preexisting snapd.service `RestartMode` key, which was not modified.

### Storage gate and exact test image

Implemented `installarr.startup.container_mount_assertion` and `render_storage_guard`.
The gate runs inside the container before the original entrypoint, checks exact
source/root/filesystem and writable mount/superblock flags from mountinfo, then
opens and reads a nonsymlink sentinel. It requires a newline-terminated sentinel
line. Target ambiguity, wrong subtree and missing/unreadable sentinel refuse the
entrypoint with exit 78. Host checks alone cannot protect daemon auto-restarts;
this container-side check runs again on every start. Private propagation retains
an existing mount view while a running container uses it.

Command: `sudo -n docker --host unix:///run/installarr-docker-test/docker.sock pull
busybox:1.37.0`, exit 0. The harness resolves and uses the immutable digest:
`busybox@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e`.
No application image was tested or declared ready.

Command: `sudo -n /usr/bin/python3 -B tools/test_physical_docker_storage.py`.
The harness verifies the actual NFS source via a held descriptor before writes,
creates one new `.installarr-docker-*` subtree as UID/GID 2000:2000, and uses only
its own local `/run/installarr-docker-guard-*` bind mount. The actual
`/media/installarr` mount is never removed. The container runs with network `none`,
UID/GID 2000:2000, all capabilities dropped, no-new-privileges, read-only rootfs,
private bind propagation and intentionally `restart=always` to exercise auto-restart.

Initial two runs timed out before the writer started and cleaned up their own
artifacts: the gate rejected a valid NFS subtree. The second diagnostic run showed
Linux's container mountinfo source as `server:/export/subtree` with mount-root `/`,
instead of `server:/export` with mount-root `/subtree`. Corrected the derived gate
to accept only those two exact equivalent identity pairs, preserving subtree path
case and rejecting unrelated roots. No permissive prefix match was introduced.

Corrected physical experiment passed, exit 0:

1. Healthy NAS: the guarded non-root loop appended only to its own NAS probe log.
2. Removed only the temporary host bind: running container retained the NFS view
   and kept writing there; writable local fallback directory remained untouched.
3. Put an identical readable sentinel in the local fallback and restarted only
   `installarr-test-docker.service`. Docker auto-restarted the `always` container,
   but the gate exited 78 before the writer because the bound filesystem identity
   was wrong. Restart attempts occurred; no local probe log was created.
4. Manually stopped restart attempts, restored the temporary NAS bind,
   and explicitly started it: writes recovered on the intended NAS fixture.
5. Removed the exact test container, its private bind, its known NAS sentinel/log
   and directory, and known local fixtures. No recursive NAS cleanup/chown occurred.

The first final-check repeat (after adding read-only-superblock checks) reached
the expected refusal/untouched-fallback result but failed at the harness's
`docker update --restart no` step while exit/restart activity was in flight.
The own-container diagnostic showed exit 78 and the intended local tmpfs fallback;
cleanup completed. Removed the unnecessary policy-change step: a manual stop
suppresses restart attempts before recovery, with the `always` policy retained.
The update failure's stderr was not retained, so its exact Engine error is unknown;
the harness now includes command stderr in isolated-test errors. This harness
failure did not permit local fallback writes. Final rerun with the revised manual
stop step: **passed**, exit 0, all four functional events completed and all own
container/bind/NAS/local fixtures removed. This rerun used the final startup gate,
including read-only-superblock refusal, and the same immutable BusyBox digest.

Post-experiment link, address, route, forwarding, iptables and ip6tables hashes all
matched the baseline exactly. The test daemon reported no remaining containers.
The BusyBox image cache, test daemon, unit, masks and private state are retained
for the next isolated experiments.

### Checks and remaining gates

- `python3 -m unittest discover -s tests -v` outside sandbox: 52 discovered,
  **51 passed, one root-only test skipped**, exit 0 (0.219 seconds).
- `sudo -n /usr/bin/python3 -B -m unittest discover -s tests -p test_dockerhost.py -v`:
  **all four passed**, including the skipped root-only file-preservation test.
- Final `git diff --check`, `python3 -m compileall -q installarr tools tests` and
  CLI `--help` passed. Read-only host verification found all three standard units
  inactive/masked, the test daemon active/static (not boot-enabled), zero test
  containers, and the original exact NFS source/type/target still mounted.
- Unit coverage includes signing-key changes, exact official version selection,
  root-owned file preservation, source/subtree mapping, missing/wrong mounts,
  missing and symlinked sentinels, and refusing entrypoint execution on failures.

This is a tested startup-protection building block, not completed app deployment.
Still needed: integrate the gate with generated Compose and each actual image's
entrypoint; host/service lifecycle and ongoing reachability supervision; general
prerequisite and mount/fstab reconciliation; bootstrap authentication and app API
adapters; approved real reboot test; functional application/download tests. A hard
NFS read can block startup without launching the application; bounded liveness
handling is not yet complete. No full-installation readiness claim is made.

Official guidance consulted on 2026-10-27:
[Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/),
[Docker daemon options](https://docs.docker.com/reference/cli/dockerd/),
[Docker restart policies](https://docs.docker.com/engine/containers/start-containers-automatically/),
[systemd service units](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).

## 2026-10-27 — review, generated Compose and authenticated Sonarr/Radarr pair

Reviewed the prior evidence against the implementation. Added the current-coverage
table above to distinguish completed experiments from historical blockers and
remaining acceptance gates. The prior results support account/NAS/Docker/startup
primitives; they did not prove application readiness. Outlined and executed this
next sequence: guarded Compose generation, one isolated real application pair,
authenticated API/root reconciliation, restart/refusal/recovery checks and updated
evidence. No reboot or host-network change was needed.

### Image discovery and pins

Commands, each against `unix:///run/installarr-docker-test/docker.sock`:

```sh
sudo -n docker --host unix:///run/installarr-docker-test/docker.sock pull lscr.io/linuxserver/sonarr:latest
sudo -n docker --host unix:///run/installarr-docker-test/docker.sock pull lscr.io/linuxserver/radarr:latest
```

Both exited 0. `latest` was used only to discover current builds. Inspected image
labels, RepoDigests, Entrypoint and Cmd before testing; generated Compose uses only
the immutable references below. Both image entrypoints were `/init` with no Cmd.

| App | Image version | Runtime API version | Immutable image |
| --- | --- | --- | --- |
| Sonarr | 4.0.20.3014-ls1 | 4.0.20.3014 | lscr.io/linuxserver/sonarr@sha256:48e36b608b461273b9dae857725cd0561a127f2c694b687318f6d0c5ce63e5c9 |
| Radarr | 6.4.4.10685-ls324 | 6.4.4.10685 | lscr.io/linuxserver/radarr@sha256:084b3b2ab1d0ef930660727259546a241f2bdf67c9ed085d54bf1486a6887c9b |

LinuxServer guidance documents PUID/PGID and local `/config` mappings. The generated
gate executes `/init` as PID 1 after checking storage; it does not force the image
to start as the non-root application UID, which would bypass initialization.
Actual application effective identities were checked separately below.

### Implementation

- `render-compose --config <file>` now generates `compose.json`, image metadata,
  per-app guards and private locked checkpoints at the selected project directory.
  JSON needs no third-party YAML package. Sonarr, Radarr or both can be selected;
  other apps fail explicitly until adapters exist.
- Bundle generation is non-overwriting and resumable for identical plans. Source
  paths come from the same storage map as default application root paths. Media,
  downloads and incomplete storage need exact mount assertions and existing
  sentinel files. App configs must be declared local. Generation does not create
  storage paths or infer existing library case.
- Long bind syntax sets `create_host_path: false` and `propagation: rprivate`.
  No ports are published, `network_mode` is `none`, `restart` is `no`, and image
  digests are pinned with `pull_policy: never`. Root-sensitive `/init` is retained;
  PUID/PGID specify the app identity. No credential values enter Compose or state.
- `installarr.arr` implements only the isolated test-socket transport. Before
  API writes, it checks the expected tested version against live system/status.
  It validates host/root schemas, resolves IDs from reads, performs configuration
  and rereads, and refuses inaccessible/duplicate root results.
- Host settings use Forms authentication, enabled for all addresses, with shared
  GUI username/password and password confirmation. GUI login is verified through
  actual cookies. API keys remain separate; authenticated API calls use X-Api-Key.
  Curl receives credentials/config on stdin, not in arguments. Temporary cookies
  are mode-private in the container and removed after each check. Response bodies
  and credential values are not printed on errors.

### Physical pair command and boundaries

Command: `sudo -n /usr/bin/python3 -B tools/test_physical_arr_pair.py`.
The retained harness first refuses nonempty test daemons, confirms the exact NFS
export through an open descriptor, and creates only a new `.installarr-arr-*`
subtree as UID/GID 2000:2000. Local private databases/configs are created under a
new `/var/tmp/installarr-arr-pair-*` directory on verified ext4. Neither existing
media nor production settings are read or copied. Shared test GUI credentials are
random synthetic values in a private secret store, not operator credentials.

The harness invokes the renderer CLI, verifies identical generation reruns, checks
the actual Compose model has no ports or networks, then deploys only the pair.
No download clients, indexers, movie/series records or requests are configured.

### Failures and corrections

1. First two runs rejected the host authentication update, with the second
   reporting HTTP 400. The initial adapter attempted Basic auth and omitted
   password confirmation. Current source explicitly rejects Basic and requires
   matching confirmation; changed to Forms, confirmation and the read-back host ID
   in the PUT route. Schema acceptance alone was not treated as success.
2. The Forms update/readback succeeded, but the first login verifier expected the
   GUI cookie to authorize the API as well. The tested apps deliberately require
   the separate API key. Corrected verification to require real GUI cookie access,
   anonymous API rejection and separate key-authenticated API success.
3. A subsequent run passed Sonarr auth/root reruns but the harness's `docker top`
   invocation failed. Its stderr was suppressed and the exact cause is unknown;
   host `ps --version` confirmed procps-ng 3.3.17 exists. Replaced that check with
   container-local `/proc/*/status` reads of effective UID/GID, restricted to the
   Sonarr/Radarr processes. No host process inventory was taken.
4. An added Compose regression initially expected the normalized `config --format
   json` output to contain single-dollar literals. Compose re-escapes them in its
   reusable serialized output. Corrected that assertion and tested a real NAS
   fixture containing a literal `$` end to end rather than relying on serialization.

Each failed physical attempt removed its own containers and NAS subtree. Four
private local failure fixtures were retained for diagnostics, each confirmed
root-owned mode 0700; their secret stores contain only synthetic credentials:
`/var/tmp/installarr-arr-pair-_q0l7388`, `/var/tmp/installarr-arr-pair-b_bql9z0`,
`/var/tmp/installarr-arr-pair-2t7mss7e`, `/var/tmp/installarr-arr-pair-swy3gvn3`.
No credentials/API keys/cookie values were printed or recorded here.

### Successful physical results

The corrected full pair run passed, and a subsequent run with runtime-version
write gating and sanitized HTTP reporting also passed. Final repeat used the
literal-dollar NAS fixture `.installarr-arr-$literal-<random id>`: exit 0,
all the following passed for both apps:

- Running API version matched the pinned image catalog. The application process
  had effective UID/GID 2000:2000. Primary SQLite files were on ext4, owned by
  2000:2000, outside NAS media storage.
- Shared Forms credentials worked, and incorrect passwords failed. Exact observed
  HTTP results for each app: anonymous GUI 302 to login, anonymous API 401; valid
  login POST 302 and cookie-authenticated GUI 200; the same GUI cookie's API access
  stayed 401. Incorrect login POST 302, GUI 302 and API 401. Separate API-key
  system/status and configuration calls returned successful JSON responses.
- Created accessible `/data/media/TV` for Sonarr and `/data/media/Movies` for
  Radarr from the common storage map, reading IDs dynamically. Repeated auth/root
  configuration retained root IDs and did not duplicate roots.
- `docker compose restart`: authentication, accessible roots and IDs persisted.
- Stopped the pair, saved config.xml hashes, then used an isolated Compose override
  to substitute a writable local media directory containing the same health marker.
  Both real images exited 78 before `/init`; config.xml hashes stayed unchanged
  and no files appeared in the local fallback besides the supplied marker.
- Restored the original generated Compose bindings: both apps recovered with the
  same credentials and root IDs. Literal-dollar path interpolation stayed correct
  in actual container mounts, source/subtree guards and application root access.
- Successful runs removed the exact pair/project containers, own NAS sentinels and
  empty TV/Movies fixture directories, and own local databases/configs/secrets.
  No recursive NAS chown or cleanup was used. Image caches remain for later tests.

Post-test hashes for links, addresses, routes, IPv4/IPv6 forwarding, iptables and
ip6tables matched the original baseline exactly. The isolated daemon had zero
remaining containers. The actual NFS export was never unmounted. No reboot,
firewall, SSH, VLAN, disk, fstab or default Docker-service changes occurred.

### Regression and remaining gates

- Final `python3 -m unittest discover -s tests -v`: **62 discovered, 61 passed,
  one root-only test skipped**, exit 0 (0.300 seconds).
- `sudo -n /usr/bin/python3 -B -m unittest discover -s tests -p test_dockerhost.py -v`:
  **four passed**, including that root-only test, exit 0 (0.002 seconds).
- Added coverage for optional app rendering, preserving case/literal paths, actual
  Compose interpolation, immutable/non-overwriting bundle reruns, unsafe selection
  refusal, stdin-only secrets, version mismatch before writes, dynamic root IDs,
  readback/access checks and distinguishing API keys from GUI cookies.
- Final `git diff --check`, `python3 -m compileall -q installarr tools tests` and
  CLI `--help` all passed; `render-compose` is registered.

Still open: a managed apply/lifecycle workflow, ongoing health supervision and hard
NFS liveness handling, general prerequisites and persistent mount reconciliation,
other application images/APIs, netbootxyz image permissions, downloader dispatch
and completed imports, full versioned TRaSH profiles, Plex authorization/selective
import, Ombi Plex family routing/presets, and an explicitly approved real reboot.
There is no general connected application deployment or end-to-end download
readiness claim from this isolated configuration/authentication experiment.

Official references consulted:
[LinuxServer Sonarr](https://docs.linuxserver.io/images/docker-sonarr/),
[LinuxServer Radarr](https://docs.linuxserver.io/images/docker-radarr/),
[Compose bind options](https://docs.docker.com/reference/compose-file/services/#long-syntax-5),
[Sonarr host configuration source](https://github.com/Sonarr/Sonarr/blob/develop/src/Sonarr.Api.V3/Config/HostConfigController.cs),
[Sonarr login source](https://github.com/Sonarr/Sonarr/blob/develop/src/Sonarr.Http/Authentication/AuthenticationController.cs),
[Radarr login source](https://github.com/Radarr/Radarr/blob/develop/src/Radarr.Http/Authentication/AuthenticationController.cs).
Those sources guided implementation; the runtime results above establish behavior
only for the exact pinned image versions, not arbitrary future releases.

## 2026-10-28 — managed lifecycle and ongoing storage supervision

Implemented `install-service` and `service-status` for the isolated daemon. A
root-owned content-addressed code snapshot under `/usr/local/lib/installarr-runtime`
runs independently of the writable checkout. Root-private definitions/checkpoints
live under `/var/lib/installarr-services/<name>`. Generated bundles now include a
configuration/image fingerprint ownership label. Existing different unit/bundle
artifacts are preserved and refused; unit installation is disabled by default.

The supervisor checks exact mount identities and writable flags through held
directory descriptors, then clears supplementary groups and drops to the service
UID/GID to read sentinels. Local application-config mounts must remain on their
registered local filesystem. Storage probes run in isolated processes with a
five-second deadline; timed-out workers are killed without blocking the supervisor
on kernel cleanup. No new probe is spawned until an earlier worker is reaped.
This bounds worker creation during stuck I/O; it does not make uninterruptible
kernel I/O itself cancellable. Regular successful checks repeat after two seconds.

Storage failures actively stop only matching project/bundle/image container IDs
and confirm stopped state. The controller audits image, entrypoint, bind paths,
private propagation, network/port settings and `restart: no` before starting.
Policy changes or foreign project collisions are refused without replacement.
Failed starts have retry backoff. systemd `ExecStopPost` stops owned containers even
if the main supervisor is SIGKILLed. Container-side gates still protect the race
between host checks and binding, and the unit does not claim application API
readiness merely because container processes are running.

Command: `sudo -n /usr/bin/python3 -B tools/test_physical_lifecycle.py`, exit 0.
Exact NAS source/type/target were reconfirmed before creating one new owned
`.installarr-lifecycle-*` subtree. Used one guarded Sonarr and one disposable
BusyBox witness on the existing networkless daemon. No actual NAS unmount,
Docker daemon restart, network changes or reboot occurred.

Physical results:

- Healthy storage started guarded Sonarr via a real root-snapshot systemd unit.
- Renaming only the own media sentinel stopped Sonarr in **6.34 seconds**; the
  unrelated BusyBox stayed running.
- Restarting the unit while unhealthy did not start Sonarr. Restoring the marker
  caused supervised recovery.
- SIGKILLing the main supervisor triggered the post-stop fallback. Sonarr stopped;
  the automatically restarted supervisor refused the now-missing marker. The
  witness was untouched, and marker restoration again recovered the app.
- A new witness with the same Compose project label but no matching bundle label
  caused the own app to stop while the foreign container remained running.
  Removing that collision recovered the managed app after backoff.
- Manual service stop stopped the app and persisted stopped status.
- Real systemd enable/is-enabled/disable calls passed, without rebooting. Unit
  verification and identical installation reruns passed. The test unit ended
  stopped/disabled; exact own containers, NAS markers/directories and successful
  local fixtures were removed.

Retained disabled test unit: `installarr-life-c2b4ff240f28.service`; root-private
definition/runtime evidence: `/var/lib/installarr-services/life-c2b4ff240f28`.
It references removed disposable fixture paths and must not be used as a real
deployment. The code snapshot is retained for inspection/reuse.

Regression command `python3 -m unittest discover -s tests -v`: **69 discovered,
68 passed and one root-only test skipped**, exit 0 (0.325 seconds). New tests cover
scoped stops, foreign-container preservation, policy refusal/backoff, exact check
definitions and refusing another worker while a modeled D-state worker is unreaped.
Real server outage, boot execution, application readiness monitoring and general
connected deployments remain unvalidated. Work continued into storage prerequisites
and downloader integration rather than ending at this milestone.


## 2026-10-28 — storage prerequisites and real isolated SABnzbd download

Implemented `prepare-prerequisites --config ...` with Ubuntu/root gating, locked
private resume checkpoints, deduplicated `nfs-common`/`cifs-utils` selection, signed
APT enforcement and installed-package readback on every rerun. Explicit repository
trust bypasses are refused. No mount, fstab, storage ownership or directory changes
are part of this adapter. Each SAB fixture exercised the NFS prerequisite twice:
installed `nfs-common` **1:2.6.1-1ubuntu1.2** was verified without package mutation.
Missing-client installation order and signature-bypass refusal passed unit tests;
this is not physical evidence for fresh installation or SMB.

Added digest-pinned SABnzbd Compose support and a version-gated API adapter. Image
metadata was discovered with the official `lscr.io/linuxserver/sabnzbd:latest` pull,
then all fixtures used this immutable pin:

- Image version **5.1.3-ls278**, runtime API version **5.1.3**.
- Image **lscr.io/linuxserver/sabnzbd@sha256:3ac1c9ea03bafa2588dd8acdcb809857bae305e71d2d90e11d689c78076a9c01**.
- `/init` initializes the image and drops the actual SAB application to
  **UID/GID 2000:2000**; its configuration/history database remains on local ext4.
- `network_mode: none`, `restart: no`, no published ports or Docker bridge.
  Python HTTP requests execute inside the container against its own loopback;
  keys/passwords are supplied via stdin, never command arguments or recorded output.

Command: `sudo -n /usr/bin/python3 -B tools/test_physical_sab.py`, **exit 0**.
The fixture first confirms `/media/installarr` is exactly NFS source
`192.168.1.102:/share/MD0_DATA/Public/installarr` via an inherited directory FD,
then creates only its own randomized `.installarr-sab-*` subtree as UID 2000.
No production files or sibling NAS folders are read or modified.

Passed physical behavior:

- A private shared GUI credential store with synthetic random test credentials;
  API logging disabled before credential changes. After restart, Basic GUI access
  at `/config/general/` returned **401 anonymous / 200 valid / 401 wrong password**.
  The API key is a separate credential, never treated as a GUI password.
- Storage map readback: incomplete `/data/incomplete`, completed `/data/downloads`,
  `tv` and `movies` category directories relative to the completed root. Repeating
  configuration preserved these settings; restart readback passed.
- An NNTP fixture bound only to **container loopback 127.0.0.1:21119** served one
  generated article, without providers, indexers, third-party content or credentials.
  SAB accepted a generated NZB, fetched **one BODY** and decoded the yEnc payload.
- Dynamic job ID reached completed history and a concrete completed storage path.
  The file was actually reopened through held NAS-directory descriptors after
  clearing supplementary groups and dropping to UID/GID 2000:2000.
- Completed file **3,776 bytes**, SHA256
  **eccc07b95ebb44ddabaaf90a09b42d24976d6d1589dd825e8ed0f81f75e3a584**,
  exact expected contents and **UID/GID 2000:2000**. SAB renamed the fixture binary
  to the NZB job name, which the test resolves from actual completed history.
- Authentication, category paths and completed job history survived a container
  restart. Own containers/NAS fixtures and successful local fixtures were cleaned.

Failures found and corrected during development:

- SAB returns some boolean settings as JSON booleans, not string `"0"`; numeric
  boolean comparison now handles that representation without weakening readback.
- Authentication middleware activates at process startup. Configuration acceptance
  is followed by restart and real rejection/login checks. Root URL redirects were
  not accepted as proof of GUI authentication; the real config page is checked.
- Setting categories before SAB's default category initialization returned the
  requested values but a later full getter replaced them with default empty dirs.
  Changing HTTP clients/methods did not fix this. Source inspection identified lazy
  default creation: `get_config` returns an empty result when the entire section is
  missing, while `get_cats` initializes it. The adapter now calls `get_cats` before
  category writes, version-gated because it can initialize persisted defaults.
  Mandatory collection readback, reruns and restart checks now pass.
- History can transiently say `Completed` before publishing its completed path;
  the test waits for both, and follows SAB's reported filename rather than assuming
  yEnc's original filename. It still verifies every completed byte and ownership.
- Failed test runs removed their own containers/NAS directories and retained only
  root-private local configuration evidence under `/var/tmp/installarr-sab-*`.
  These contain synthetic credentials and are intentionally not printed or committed.

Relevant primary sources consulted:
[SAB 5.1 API](https://sabnzbd.org/wiki/configuration/5.1/api),
[SAB 5.1.3 API source](https://github.com/sabnzbd/sabnzbd/blob/5.1.3/sabnzbd/api.py),
[SAB category initialization source](https://github.com/sabnzbd/sabnzbd/blob/5.1.3/sabnzbd/config.py),
[LinuxServer SAB image guidance](https://docs.linuxserver.io/images/docker-sabnzbd/).
Runtime results establish the behavior above only for the recorded image pin.

Regression verification:

- `python3 -m unittest discover -s tests -v` outside the filesystem sandbox:
  **76 discovered, 75 passed, one root-only skip**, exit 0 (0.344 seconds).
  The sandbox run failed trusted-ancestor and real-mount tests because it exposes
  different ownership/mount metadata; the unchanged suite passed on the real host.
- `sudo -n /usr/bin/python3 -B -m unittest discover -s tests -p test_dockerhost.py -v`:
  **4 passed**, including actual root ownership checks, exit 0.
- `sudo -n /usr/bin/python3 -B tools/test_physical_arr_pair.py`: **passed**, exit 0.
  Shared transport/catalog changes preserved both apps' real Forms login/rejection,
  distinct API-key behavior, accessible root reruns, restart persistence, effective
  UID/GID, local databases, wrong-filesystem refusal before `/init` and recovery.
- `sudo -n /usr/bin/python3 -B tools/check_physical_network.py`: **7/7 baseline
  fingerprints unchanged**, exit 0: links, addresses, all routing tables, IPv4/IPv6
  forwarding and iptables/ip6tables. The first audit used only the main routing
  table and mismatched the saved all-table hash; using the baseline's complete
  representation matched exactly. No network changes were made.

Real provider access, Sonarr/Radarr client connection/dispatch, media import, actual
NAS outage/reboot, full TRaSH profiles and Plex/Ombi behavior remain unvalidated.
No provider credentials or reboot approval are needed to keep implementing the
next isolated pair experiment and storage/apply adapters.

Final cleanup check: `sudo -n docker --host
unix:///run/installarr-docker-test/docker.sock ps --all --format
'{{.ID}} {{.Names}} {{.Status}}'` returned no containers, exit 0. A final repeat of
the 76-test suite passed (75 passed, one root-only skip; 0.345 seconds).
`python3 -m compileall -q installarr tools tests`, `git diff --check` and CLI help
all passed. No reboot occurred. Changes remain in the existing checkout, uncommitted.


## 2026-10-28 — real application/downloader connections

Implemented `installarr.downloadclients.ensure_sabnzbd` for the exact tested
Sonarr/Radarr API versions. It obtains the actual running provider schema, locates
fields by name and resolves the saved downloader ID dynamically. The storage map
now exposes each application's download category (`tv` / `movies`), reused by the
connection adapter. Credentials stay separate from nonsecret configuration.
The adapter performs the app's real downloader test before saving, reads back the
entry and tests the saved connection. Wrong runtime versions, unsupported schemas,
conflicting implementations, and operator-edited connection settings are refused.
Repeated matching configuration retains a single entry rather than duplicating it.

Commands, each **exit 0**:

- `sudo -n /usr/bin/python3 -B tools/test_physical_download_pair.py` (Radarr).
- `sudo -n /usr/bin/python3 -B tools/test_physical_download_pair.py --app sonarr`.

Exact image versions/digests were unchanged from the preceding experiments:
Radarr **6.4.4.10685-ls324**, Sonarr **4.0.20.3014-ls1**, SABnzbd **5.1.3-ls278**.
Each experiment used only one application/SAB pair, never a complete second stack.
Before fixture writes, the helper reconfirmed exact source/target/type of
`192.168.1.102:/share/MD0_DATA/Public/installarr` at `/media/installarr`, NFS.
Only new owned `.installarr-download-pair-*` subtrees were touched; application
state stayed in private new local ext4 directories.

Pair communication uses a **fixture-only** Compose extension: SAB retains
`network_mode: none`, and the app joins its namespace with
`network_mode: service:sabnzbd`. Docker inspect verified `container:<SAB-ID>`
for the dependent and `none` for SAB, with no published ports. No bridge, host
network/SSH/firewall changes or reboot occurred. Canonical generated bundles are
unchanged and remain individually networkless; the installed supervisor refuses
this experimental override. Both apps have real GUI authentication configured.

Passed for both application versions:

- Actual app-side SAB provider test succeeded with the separate SAB API key.
- `movies` (Radarr) and `tv` (Sonarr) categories read back correctly.
- A second call kept the same dynamic downloader ID and exactly one entry.
- Changing one API-key character failed the app's connection test **before save**;
  the original correct connection still passed afterward.
- Stopping and recreating both containers retained GUI authentication, SAB storage
  settings, downloader ID and a working saved connection. The namespace owner and
  dependent are recreated together so the dependent cannot retain stale loopback
  membership after a SAB-only restart.
- Own NAS/container/local successful fixtures were cleaned.

Unit tests also verify refusing an operator-edited host without connection tests or
writes, preserving a conflicting implementation, and refusing unknown versions
before even reading provider schemas.

Primary references used:
[Radarr API](https://radarr.video/docs/api/),
[Radarr pinned SAB settings](https://github.com/Radarr/Radarr/blob/v6.4.4.10685/src/NzbDrone.Core/Download/Clients/Sabnzbd/SabnzbdSettings.cs).
Source review also confirmed that adding a Radarr movie calls its metadata service;
release dispatch requires a separately controlled metadata/download fixture rather
than assuming a provider connection test exercises those paths.

These results establish authenticated provider connections and persistence, not
release dispatch, downloads initiated by an app, or completed media imports.
The previous generated SAB-only NNTP transfer remains the download-byte evidence.

Follow-up Radarr run:
`sudo -n /usr/bin/python3 -B tools/test_physical_download_pair.py --app radarr`,
exit 0, additionally changed only its own downloader priority to 2 through the app
API, verified reconciliation refused and preserved that edit, then restored its
own priority to 1 and repeated persistence checks. This physically verifies
operator-edit preservation in addition to the unit-tested host-edit case.

Final regression: `python3 -m unittest discover -s tests -v`, **80 discovered,
79 passed and one root-only skip**, exit 0 (0.370 seconds). Compilation and
`git diff --check` passed. The read-only network audit again matched all seven
saved baseline hashes; final isolated-daemon inventory was empty. No reboot.


## 2026-10-28 — supplied movie and TV library recognition

Operator clarified scope: use the provided test media directly; do not duplicate,
rename or delete it. Installer acceptance is correct paths, permissions and usable
application recognition. Managing manual versus automatic import modes is outside
installer scope. No import-management feature or media-copy workflow was added.

Re-read README, physical-host instructions and agent handoff. Reconfirmed with
`findmnt --json --target /media/installarr --output TARGET,SOURCE,FSTYPE,OPTIONS`:
exact target `/media/installarr`, NFS source
`192.168.1.102:/share/MD0_DATA/Public/installarr`, `rw`. Limited inventory to the
operator-supplied test subtree; found:

- `Movies/Framing Britney Spears (2021)/Framing Britney Spears (2021) WEBDL-720p.mkv`,
  **1,443,788,727 bytes**, and its `.en.hi.srt` subtitle, **126,361 bytes**.
- `TV/11.22.63/Season 1/11.22.63 - S01E01 - The Rabbit Hole Bluray-1080p Remux.mkv`,
  **12,029,218,594 bytes**.

New fixture command `tools/test_physical_library.py` uses the original movie/series
folder as a **read-only nested bind**, verified through Docker inspect. The app's
root is an empty, newly owned writable test directory because Radarr validates root
writability even for existing libraries. The original media is read directly: no
copy, hardlink, rename, deletion or recursive chown. New local application databases
and the empty NAS scaffolding are disposable and separate from the supplied data.

Each run used a minimal app/SAB pair with no bridge or published ports. SAB's tested
Python runtime hosted a temporary loopback metadata helper. A private 0600 Unix
socket in the disposable local config directory connected it to a host-side relay
that permits TLS only to `api.radarr.video:443` and `skyhook.sonarr.tv:443`. There is
no host TCP listener, DNS/route/firewall change, TLS interception or credential
logging. The fixture proxy setting affects only its own temporary app configuration.
This permits real official metadata lookup while preserving the isolated daemon's
network policy. The helper is test infrastructure, not installer configuration.

Commands and final successful results:

- `sudo -n /usr/bin/python3 -B tools/test_physical_library.py --app radarr`, exit 0:
  real title lookup, dynamic quality-profile/record IDs, supplied existing path,
  unmonitored movie with searches disabled. Radarr **6.4.4.10685-ls324** recognized
  exactly one unique file with the correct path/size and a mediaInfo object.
  Its file ID survived app restart. Metadata host observed: `api.radarr.video`.
- `sudo -n /usr/bin/python3 -B tools/test_physical_library.py --app sonarr`, exit 0:
  real series lookup and episode metadata, dynamic quality profile/record IDs,
  unmonitored series/seasons with missing-episode searches disabled. Sonarr
  **4.0.20.3014-ls1** recognized exactly one episode at the supplied Season 1 path,
  correct size and a mediaInfo object. Its file ID survived restart. Metadata host
  observed: `skyhook.sonarr.tv`.
- Original file inventories (relative names, sizes and modification timestamps),
  including the movie subtitle, matched before/after. Original mounts were read-only.
  Only own containers, local successful fixtures and empty own NAS scaffolding were
  removed. The supplied movie, subtitle and TV episode remain in place.

Development failures and corrections:

- Initial app images lacked Python; mounting the host Python executable alone
  also failed because the app images do not provide its glibc loader. No package or
  image changes were made. The final minimal pair reuses SAB's existing runtime.
- Registering the original read-only directory as the root failed app validation
  (HTTP 400). The final layout uses a writable empty own root plus the read-only
  original child directory, without weakening original-media protection.
- An early movie run started an explicit rescan while the app's initial refresh
  was active and observed two file rows for one path. The test now waits for the
  app's initial recognition/refresh and requires exactly one unique file. After a
  clean successful check, the unnecessary explicit-rescan step was removed to keep
  validation within the operator's installer scope; no manual-import UI was added.
- Failure runs cleaned own containers/NAS scaffolding and retained private local
  evidence under `/var/tmp/installarr-library-*`; supplied files stayed protected.

`ArrClient.json` now supports read query parameters for real lookup/file-list APIs;
write requests cannot use that query interface. Secrets still travel on stdin.
`python3 -m unittest discover -s tests -v`: **80 discovered, 79 passed, one root-only
skip**, exit 0 (0.350 seconds). Compilation and `git diff --check` passed. Read-only
network audit matched all seven baseline fingerprints. No reboot occurred.

Remaining installer work is storage reconciliation and resumable deployment/app
configuration. Different application import modes are not separate installer
readiness gates. These existing-library checks do not claim app-initiated downloads
or request dispatch, which remain distinct integration evidence.


## 2026-10-28 — configured directory preparation on existing storage

Scope remained installer preparation: verify configured storage, create needed
paths/health markers, preserve existing content and metadata, and verify actual
application-user write access. No media organization/import modes, mounts, fstab,
network, disk, SSH or recursive ownership edits were added.

Implemented CLI `prepare-directories --config ... [--state-directory ...]`.
All declared storage anchors are opened without symlink traversal and checked
before the first storage write. Remote paths require the exact configured mounted
source/type/target and rw flags; declared local paths require ext4/xfs/btrfs.
Required service identities and installed NFS/SMB prerequisites are checked first.
This adapter never attempts a mount or installs packages implicitly.

Workers retain directory descriptors and recheck mount identity before creation.
NAS work clears supplementary groups and drops to the configured UID/GID before
any creation. Local ownership is assigned only to newly created directories;
existing directory ownership/modes and marker contents are preserved. App config
ownership mismatches fail rather than being repaired. New health markers use
exclusive creation and fsync; existing markers must be nonsymlink regular files
with a newline. Actual UID write/fsync probes are removed immediately. Private
local Execution checkpoints reconcile each directory again on every rerun.
The host configs parent is preserved without requiring app-user access through
private host ancestors; each individually bound app-config child is verified.

Mount was reconfirmed rw at `/media/installarr`, source
`192.168.1.102:/share/MD0_DATA/Public/installarr`, filesystem nfs.
Command `sudo -n /usr/bin/python3 -B tools/test_physical_directories.py`, final
**exit 0**. No containers were started for this experiment.

Physical results:

- A wrong expected source failed before creating NAS directories, local app
  directories or checkpoints.
- Created own visible fixture
  **/media/installarr/Installarr-Directory-Test-20261028-c0112b37** as
  **installarr-test 2000:2000**. NAS directories: `media`, `downloads`, `incomplete`,
  `media/TV` and `media/Movies`; three **26-byte** `health` marker files contain
  `Installarr storage health` followed by newline. Each applicable directory passed
  actual UID/GID 2000:2000 write/fsync access.
- Local Sonarr/Radarr/SAB config children and backups were created under
  **/var/tmp/installarr-directories-mjhtnqph** and passed service-UID write checks.
- Repeated preparation created zero new components and preserved marker inodes,
  content, modes, UID/GID and modification timestamps.
- Changing only the own local Sonarr test config directory to root ownership
  caused refusal without correcting that ownership. Restoring its own test
  ownership and rerunning reconciled the checkpoint and passed.
- Real CLI command
  `sudo -n /usr/bin/python3 -B -m installarr prepare-directories --config /var/tmp/installarr-directories-mjhtnqph/config.json --state-directory /var/tmp/installarr-directories-mjhtnqph/state`
  returned `status: verified`, zero created components and successful write checks,
  exit 0. Config parent separately reports that its app children are checked.

First physical run failed at the private local backups directory: after dropping
UID, findmnt could not traverse its root-private ancestor. The worker now verifies
local mount identity before the drop and uses the same held descriptor for the
service-user probe; it does not require weakening host-parent permissions. Remote
workers still perform repeated exact mount checks as their service UID.
Partial fixture **Installarr-Directory-Test-20261028-ae3a5847** was removed only
after verifying its exact three owned child folders and expected marker contents,
through a mount-verified descriptor as UID 2000. Root-private failed local evidence
remains at `/var/tmp/installarr-directories-qygto798`.

Operator visibility correction: earlier experiments created hidden, short-lived
`.installarr-*` NAS subdirectories, then cleaned them. Plain `ls` hides these names.
This completed visible fixture and its local config/checkpoints are intentionally
**retained** for observation. No supplied Movies/TV folders or media files were
changed, copied, renamed or deleted.

Regression command `python3 -m unittest discover -s tests -v`: **83 discovered,
82 passed and one root-only skip**, exit 0 (0.379 seconds). Added tests cover marker
and directory metadata preservation, changed-mount refusal before mkdir, and
preserving invalid markers/symlinks. Compileall and diff whitespace checks passed.
Read-only network audit again matched all seven original hashes. No reboot.

Actual mount/fstab persistence reconciliation, an unattended apply command and
remaining app adapters are still open; this command claims directory preparation
only. SMB and the netbootxyz image runtime remain separately unvalidated.


## 2026-10-28 — first resumable isolated apply

Implemented `apply --config ... --name ...`, with optional protected credential
file/store and local state directory. Scope: nonempty subsets of the three tested
Sonarr/Radarr/SABnzbd images, already-mounted asserted data storage and local app
configuration. Unsupported apps and conflicting deployment definitions/units fail
before host preparation. This path does not edit mounts/fstab, enable boot, publish
ports, or change host networking. It is explicitly **isolated_configured**, not
normal installation readiness.

The orchestrator reuses account, signed prerequisite, directory, Docker staging,
isolated daemon, pinned image, Compose, root-snapshot supervisor and API adapters.
Credentials are collected once or read from a private 0600 input/store, then kept
separate from nonsecret config/checkpoints. Every rerun reconciles actual state.
Failure records failed status and stops only matching owned containers; an earlier
successful phase is cleared when a rerun starts and cannot survive a failed rerun.

Generated SAB pairs now share only SAB's container network namespace. No-SAB
bundles remain individually networkless. The bundle fingerprint includes the new
pair topology; old different artifacts are refused without replacement. Supervisor
audit requires the matching owned SAB container ID, expected port/restart/bind
policy, and matching live `/proc/<pid>/ns/net` inodes. This detects a dependent
retaining the old namespace after an owner restart and permits scoped recovery.

Physical commands, both exit 0:

- `sudo -n /usr/bin/python3 -B tools/test_physical_apply.py --app radarr`:
  retained local evidence `/var/tmp/installarr-apply-e9su0rc8`, unit
  `installarr-apply-9a85bc2429.service`, visible NAS fixture
  `/media/installarr/Installarr-Apply-Test-9a85bc2429`.
- `sudo -n /usr/bin/python3 -B tools/test_physical_apply.py --app sonarr`:
  retained local evidence `/var/tmp/installarr-apply-lrlggtrt`, unit
  `installarr-apply-695486fb1d.service`, visible NAS fixture
  `/media/installarr/Installarr-Apply-Test-695486fb1d`.

Each used exactly one app/SAB pair and confirmed the exact authorized writable NFS
source/target before writes. No original media or sibling NAS folders were touched.
The orchestrator created new paths and all application configuration itself. An
injected failure immediately before app configuration left two stopped owned
containers and a failed applications checkpoint. The real CLI then resumed using
its stored credentials, and a second CLI run preserved container IDs, root IDs,
and downloader IDs without duplicate entries. App versions/digest pins remained
Sonarr 4.0.20.3014-ls1, Radarr 6.4.4.10685-ls324 and SABnzbd 5.1.3-ls278.

Observed authentication: SAB anonymous/valid/wrong **401/200/401**; Sonarr/Radarr
Forms anonymous redirect, valid cookie GUI **200**, wrong-password GUI redirect,
unauthenticated API **401**. API keys remain distinct from GUI passwords. Correct
category and saved app-side SAB connection tests passed. Synthetic shared password
was absent from captured CLI output and every nested state.json checkpoint.
Units were disabled; tests ended by stopping units and removing only their owned
containers. Private local evidence and visible NAS fixture health markers remain.

GUI scope clarification from operator: every app still needs a reachable GUI.
Current test bundles do not provide one outside Docker exec. Shared loopback does
not prevent adding a normal access path, but authentication-verified exposure is a
required next implementation gate. Do not describe this first apply as fully usable
or substitute internal API success for browser access. Manual/automatic media
import mode management remains outside installer scope.


Extended final Radarr apply run:
`sudo -n /usr/bin/python3 -B tools/test_physical_apply.py --app radarr`, exit 0.
Retained local evidence `/var/tmp/installarr-apply-0aham5at`, visible NAS fixture
`/media/installarr/Installarr-Apply-Test-b3153725a0`, disabled/stopped unit
`installarr-apply-b3153725a0.service`.
In addition to initial interruption/resume and stable IDs, a direct restart of only
the owned SAB container recovered under real supervision with audited shared
namespace membership. A further injected failed apply after previous success
cleared the old success phase to `failed`, stopped owned containers and subsequently
resumed successfully through the CLI. These were container restarts, not a host
reboot or network configuration change.

Regression suite: `python3 -m unittest discover -s tests -v`: **87 discovered,
86 passed and one root-only skip**, exit 0 (0.341 seconds). New tests cover rejecting
unsupported apps before preparation, SAB authentication/restart ordering, generated
pair topology, and refusing a wrong owner or stale live namespace inode. Compilation
and `git diff --check` passed. No browser-accessibility claim follows from these
internal GUI-authentication tests.

Final network audit matched all seven baseline hashes; isolated Docker inventory
was empty after cleanup. A planner availability-field change initially broke four
storage-only unit fixtures without an apps key; using the existing optional-apps
contract fixed that regression. The final complete suite passed again. The planner
keeps general apply unavailable and reports isolated apply separately.


## 2026-10-28 — continuous-plan audit and authenticated host GUI access

Created docs/IMPLEMENTATION_CHECKLIST.md from actual requirements and accumulated
runtime evidence. Operator requested continuous execution until genuinely blocked;
completed milestones are updates, not stop points. Original media, host network
configuration and reboot boundaries remain unchanged.

Implemented supervisor-managed host TCP listeners for the configured bind address
and app ports. They use nsenter to enter only an audited backend network namespace
in a per-connection child, then clear supplementary groups/drop to the service
UID/GID and connect to its loopback app. A private socketpair carries bytes to the
host listener. No Docker port publishing, bridge, host route/firewall edits, helper
image or container Python dependency is needed. The standard host Python runtime
remains in the host mount namespace. Proxying preserves HTTP, cookies and binary
streams; bounded buffers/connection slots and half-close handling are included.

GUI exposure is authorized only after apply verifies actual app authentication.
A root-private bundle-bound gui-ready.json references the separate protected
credential store (no passwords/API keys in the marker). Before opening listeners on
a new backend namespace, the supervisor independently re-verifies real app login
and rejection. On API startup delays or auth failure it leaves access closed.
Apply revokes exposure before rerun configuration and removes authorization on
failure. Health failure/service stop closes listeners and active relay sessions.

Physical commands, both exit 0:

- `sudo -n /usr/bin/python3 -B tools/test_physical_apply.py --app radarr`:
  `/var/tmp/installarr-apply-alz4_nlp`, stopped/disabled unit
  `installarr-apply-3db3b97e52.service`, visible NAS own fixture
  `/media/installarr/Installarr-Apply-Test-3db3b97e52`.
- `sudo -n /usr/bin/python3 -B tools/test_physical_apply.py --app sonarr`:
  `/var/tmp/installarr-apply-7bfbmjdj`, stopped/disabled unit
  `installarr-apply-0cd7cd9262.service`, visible NAS own fixture
  `/media/installarr/Installarr-Apply-Test-0cd7cd9262`.

Real **host-side HTTP** (not Docker-exec-only) verified SAB GUI
**401 anonymous / 200 valid / 401 invalid**, and both Sonarr/Radarr Forms login,
valid GUI **200**, invalid/anonymous redirect, API without key **401**. Cookies stay
in memory. Generated test passwords remain absent from output/checkpoints. Tests
used **127.0.0.1**, ports 7878/8989/8080 as selected. Other-device LAN reachability
has not yet been physically checked. Host listeners use the configured address.

Extended Sonarr/SAB run also renamed only its own health marker after mount
verification and UID drop. It observed waiting_storage, both listener ports closed
and both owned containers stopped; marker restoration recovered healthy audited
apps and reverified/open GUI access. Direct SAB restart recovery, injected failed
rerun status clearing, CLI resume, stable IDs and no duplicates continued to pass.
Only test containers were removed; NAS health fixtures/local evidence were retained.

New focused tests verify binary payloads larger than relay buffers, request
half-close followed by a full response, no listener without authorization, and
keeping access closed on unverified authentication after restart. Existing
regressions still passed. The seven network baseline fingerprints remained exact.

Primary implementation reference: [nsenter manual](https://man7.org/linux/man-pages/man1/nsenter.1.html).
This implements GUI access for the isolated deployment, not general outbound app
networking. Metadata/provider/request-dispatch connectivity is still an open gate.
Work continued into read-only fstab/runtime reconciliation without a milestone stop.


## 2026-10-28 — mount/fstab reconciliation and fresh NFS in private namespace

Implemented read-only `check-mounts` and root `prepare-mounts`, integrated before
apply directory writes. Exact existing runtime mounts are reused; conflicting,
duplicate or read-only fstab declarations are refused and preserved. Inline
operator credentials are never included in review output. Fresh NFS/SMB paths
require client helpers first, empty local mountpoints and post-mount identity/rw
readback. No existing mounts are unmounted. Newly authorized persistence entries
append only after a private exact-content backup; root ownership/mode are preserved
and external changes are checked before replacement. Existing entries are not
rewritten. Only default live /etc/fstab updates trigger daemon-reload.

`nfs` assertions use explicit v3; `nfs4` assertions use v4, TCP and hard semantics.
New persistence has _netdev,nofail,x-systemd.mount-timeout=15s. SMB uses a protected
root-only credential file path, SMB3 and numeric service UID/GID; no raw secrets in
mount arguments or fstab. SMB physical validation is still pending at this point.

Physical checks:

- `sudo -n /usr/bin/python3 -B -m installarr check-mounts --config /var/tmp/installarr-directories-mjhtnqph/config.json`:
  exact runtime and matching existing fstab at /media/installarr, reuse, no conflicts,
  changed=false, exit 0.
- `prepare_mounts` against the same real existing config, with checkpoints at
  `/var/tmp/installarr-directories-mjhtnqph/mount-review-state`: verified, persistence
  changed=false, live /etc/fstab SHA256 unchanged, exit 0.
- `sudo -n /usr/bin/python3 -B tools/test_physical_mounts.py`: final exit 0,
  local evidence `/var/tmp/installarr-mounts-jrd19iwt`; own retained NAS subtree
  `/media/installarr/Installarr-Mount-Test-416d3c3a88`.
  A real new mount at `/var/tmp/installarr-mounts-jrd19iwt/mount` existed only inside
  `unshare --mount --propagation private`, from the exact authorized test export.
  All data writes stayed beneath the own named subtree. UID/GID 2000 directory and
  health-file writes passed. Fixture fstab backup was byte-exact and 0600; rerun
  kept the same persistence bytes without duplicates. The own private mount was
  unmounted before child exit. Parent verified no mount leaked into its namespace,
  live fstab hash unchanged and original /media/installarr source/type/target intact.

Failures corrected/recorded:

- A fresh private mount initially succeeded, but service-UID target-path lookup
  failed beneath a root-private local fixture ancestor. Directory mount checks now
  match /proc/self/fdinfo/<fd> mnt_id to explicit kernel findmnt ID records, avoiding
  path traversal after dropping UID without weakening directory permissions.
- Subsequent NAS subdirectory mount attempts hit an RPC portmap timeout. Exact
  diagnostic: mount.nfs portmap query failed: RPC: Timed out; Connection timed out.
  Existing NFS data access remained available. A mount deadline now terminates the
  entire helper process group; retry=0 avoids mount.nfs foreground retry delays.
- The adapter can reuse only kernel-reported transport for the **exact** already
  mounted source. This NAS reports mountport=30000,mountproto=udp,mountvers=3,
  with NFS port 2049. Reusing those working settings removed the RPC lookup
  dependency. No NAS service or host network configuration was changed. The final
  test mounts the authorized export root and writes only its own named directory.
- Earlier failed own fixture paths remain as private evidence/empty NAS test dirs:
  ff23be5a4b /var/tmp/installarr-mounts-6rl2ugof;
  c48fa4b9af /var/tmp/installarr-mounts-k9zy2qua;
  fd70b2d22c /var/tmp/installarr-mounts-hbaaddmp. No original media was touched.

Unit suite after these changes: **97 discovered, 96 passed, one root-only skip**,
exit 0 (0.351 seconds). Tests cover fstab escaping, optional fields, conflict and
credential redaction, persistence flags and limiting transport reuse to the exact
source. Live persistence modification and actual reboot remain untested.
Primary references: [fstab](https://man7.org/linux/man-pages/man5/fstab.5.html),
[NFS](https://man7.org/linux/man-pages/man5/nfs.5.html),
[fdinfo mount ID](https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html),
[findmnt](https://man7.org/linux/man-pages/man8/findmnt.8.html),
[kernel CIFS credentials](https://cdn.kernel.org/doc/html/latest/admin-guide/cifs/usage.html).
Work continued into SMB validation rather than stopping here.


## 2026-10-28 — reference-scope correction

Operator clarified that the installer must follow the reference server, permitting
standardization of accounts/shared credentials, quality profiles and shared paths,
with no invented additions without permission. Reclassified the checklist around
reference alignment. No actual reference Compose/app export was found in the
checkout; its location was requested without inspecting production.

SMB/Samba validation is deferred: the current reference uses NFS. An official Ubuntu
24.04 test image was pulled (digest
sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c),
but no Samba server/package or host SMB package was installed or started. The
custom GUI relay remains isolated test infrastructure; do not assume it is an
approved replacement for the reference networking architecture.

The existing account wizard now defaults to the already-tested non-root 2000:2000
identity rather than Ubuntu's usual human-admin 1000:1000. IDs remain editable and
existing collision checks apply; no host accounts were changed by this default edit.

## 2026-10-28 — usable reference Radarr/SAB bridge proof of concept

Operator confirmed standard web bridge and approved Docker NAT/firewall changes.
`sudo python3 tools/prepare_reference_network.py --operator-approved` passed:
standard Docker/containerd active and boot-disabled; isolated daemon stopped.
Host IP/DNS/manual routes, SSH, VLANs and disks were not modified. No reboot.
Bridge DNS and HTTPS proved using the pinned SAB image: Radarr resolved to
172.20.0.3 and https://lscr.io/v2/ returned expected HTTP401. No Samba installed.

Shared-data proof: `sudo python3 tools/test_physical_shared_data.py` passed real
same-inode hardlink and nested wrong-mount startup refusal. Retained evidence
/var/tmp/installarr-shared-data-u61q71rj; NAS Installarr-Shared-Data-edea79afca.
This fixes the earlier separate-bind EXDEV boundary using one explicit data_root.

`sudo python3 tools/create_reference_poc.py` completed reference_poc_ready.
Retained configuration/evidence: /var/tmp/installarr-reference-poc-fz5b_65a;
NAS fixture /media/installarr/Installarr-POC-d29db77d. Mount verified exactly:
192.168.1.102:/share/MD0_DATA/Public/installarr → /media/installarr, nfs,rw.
Original supplied movie/episode paths were not copied, renamed or deleted.
Unit installarr-poc-d29db77d.service is active and disabled at boot.
Radarr http://10.70.0.99:7878/; SAB http://10.70.0.99:8090/. SAB also preserves
reference mapping 9090→9090 (HTTPS service itself is not configured/tested).

Images retain tested pins: Radarr6.4.4.10685-ls324 sha256:
084b3b2ab1d0ef930660727259546a241f2bdf67c9ed085d54bf1486a6887c9b;
SAB5.1.3-ls278 sha256:
3ac1c9ea03bafa2588dd8acdcb809857bae305e71d2d90e11d689c78076a9c01.
Bootstrap uses the standard web bridge with no published ports. Only after real
authentication/path/connection verification does the live guarded bundle publish
ports. Both use one /data bind, UID/GID2000, and local config/database storage.

Real CLI rerun passed:
`sudo python3 -m installarr apply --reference --config /var/tmp/installarr-reference-poc-fz5b_65a/config.json --name poc-d29db77d --state-directory /var/tmp/installarr-reference-poc-fz5b_65a/state`.
No credential prompt; credentials remain only in the root-private secret store.
SAB host GUI anonymous401/valid200/invalid401. Radarr anonymousGUI302/API401,
valid GUI200, invalid GUI302; GUI cookie alone still API401. RootID1 and SAB
downloaderID1 persisted; connection test passed using DNS host sabnzbd, category movies.
Runtime container policy audit passed with exactly two owned containers.

Bridge-specific loss/recovery test: temporarily renamed only the generated fixture
health marker, after exact mount verification; supervisor entered waiting_storage,
both owned containers stopped and 7878/8090 refused connections. Marker restored
in finally; containers_running and live policy audit recovered. No NAS unmount/outage
or reboot was performed. Existing safety policy remains restart:no plus guarded
systemd supervision, not an unguarded Docker unless-stopped policy.

Added reference tests for unpublished bootstrap/reference port map, literal dollars
in auth-marker paths, and real shell refusal for missing/wrong marker, reset auth
and symlink config. Full suite:102 tests,101 passed,1 root-only skipped, exit0.
General fresh standard-engine activation, remaining apps, full profiles and reboot
are still unvalidated. Current readiness is reference_poc_ready, not full readiness.

## 2026-10-28 — HTTP-only POC and Bazarr physical integration

Operator requested no HTTPS listeners/settings. Reference SAB now publishes only
8090→8080; no9090. Replaced retained POC using a new private bundle/unit so original
immutable artifacts/checkpoints remain preserved. Current unit is
installarr-poc-http-d29db77d.service; config http-config.json, state http-state
under the same /var/tmp/installarr-reference-poc-fz5b_65a. Same app databases, NAS
data and protected credentials reused in place; root/downloader IDs remain1.
Old poc-d29db77d unit is stopped. Host GUI real authentication/rejection passed.

Official Bazarr guidance reviewed: https://docs.linuxserver.io/images/docker-bazarr/
and https://wiki.bazarr.media/Additional-Configuration/Settings/Application/.
Version-specific API/auth source reviewed at official release v1.6.2:
https://github.com/morpheus65535/bazarr/releases/tag/v1.6.2.
Pulled reference ghcr.io/linuxserver/bazarr image and pinned v1.6.2-ls370 digest
sha256:9a625883f054e722795affe5e3ca71057e6ed817ecdf99f4a99624346fcc509c.

First physical attempt failed strict radarr.base_url readback. Bazarr's own URL
builder normalizes / to empty in memory; accepting only that exact root equivalence
fixed it. No broad readback bypass. Failure fixtures/evidence retained at
/var/tmp/installarr-bazarr-test-7wr4a7pj and /var/tmp/installarr-bazarr-test-d5rjwtr7.

`sudo python3 -B tools/test_physical_bazarr.py --resume /var/tmp/installarr-bazarr-test-d5rjwtr7`
passed Radarr6.4.4.10685 connection from Bazarr, real Basic GUI401/200/401,
anonymous API401, restart/rerun, local bazarr.db ownership2000:2000 and container
policy audit. NAS Installarr-Bazarr-6dc87d16.
`sudo python3 -B tools/test_physical_bazarr.py --app sonarr` passed the same checks
with Sonarr4.0.20.3014. Evidence /var/tmp/installarr-bazarr-test-478idkci;
NAS Installarr-Bazarr-e6b2e578. Each fixture used only its minimal unpublished pair
and removed its own containers/bridge afterward; retained config/data are evidence.
No subtitle-provider credentials or subtitle download behavior were tested.

Added API version-before-write, real password rejection, readback-failure and
integration-conflict tests. Shared-data wizard now collects one explicit root,
mount assertion, health markers and consistent directory roles. Plan preview uses
the same derived data paths as Compose/app adapters. Full suite106 tests,105 passed,
one root-only skipped,exit0.

Bazarr final reference apply also passed protected bootstrap then real published
host GUI6767 authentication/rejection, plus Radarr7878, using retained fixture
/var/tmp/installarr-bazarr-test-d5rjwtr7/published-config.json and published-state.
Unit installarr-bazarr-pair-6dc87d16.service is now stopped/disabled. The live POC
was stopped briefly to avoid port conflicts and restored in finally; only HTTP7878
and8090 remain published. Root-only Docker file safety suite:4/4 passed.

## 2026-10-28 — standard-engine orchestration and Jackett auth groundwork

Reference apply now calls installarr.network.prepare_standard_docker: signed
package staging first on fresh hosts, recorded package-version reconciliation,
then standard bridge-capable engine startup. Current live owned-engine tool/CLI
reruns passed without remasking/restarting the running engine. Four new tests
cover fresh staging, interrupted-transition resume without remasking, active-engine
rerun and changed-package refusal before engine commands. Full clean-OS combined
provisioning remains unvalidated on this already-prepared host. Suite110 tests,
109 passed,1 root-only skipped; root-only Docker file suite separately4/4 passed.

Jackett official guidance/source reviewed: https://docs.linuxserver.io/images/docker-jackett/
and https://github.com/Jackett/Jackett/tree/v0.24.2949/src/Jackett.Server/Controllers.
Reference image pinned0.24.2949-ls19 digest
sha256:2c015f0978bb15d006937a0e6926d8a8c4ca955eed5f3372c6ec09a3a2de3ddd.
Official UI has password-only authentication (no administrator username).
Initial transport attempt rejected the versioned v2.0 path because dots were not
allowed; interrupted that waiting fixture safely, removed its container, allowed
dotted API versions while still rejecting parent traversal, and resumed same local
fixture. `sudo python3 -B tools/test_physical_jackett.py /var/tmp/installarr-jackett-test-hijk0c5b`
passed anonymous302/valid200/invalid302 before and after restart, actual runtime
v0.24.2949, ServerConfig owner2000:2000. No NAS binds or host ports in this first
fixture. Password/cookies/API keys stayed out of outputs and command arguments.
No indexer was invented, no torrent client added and no request/download claim made.

Jackett reference apply passed protected bootstrap then host HTTP9117 actual
anonymous302/valid200/invalid302. Retained published-config.json, published-state
and published-result.json under /var/tmp/installarr-jackett-test-hijk0c5b; unit
installarr-jackett-poc-212b038f.service stopped afterward. NAS fixture
/media/installarr/Installarr-Jackett-212b038f created only through exact mount-asserted
directory preparation. No existing media touched. Added version-before-write and
wrong-password acceptance refusal tests. Suite112 tests,111 passed,1 root-only skip.

## 2026-10-28 — resumed full pinned-profile physical acceptance

Confirmed exact /media/installarr NFS source
192.168.1.102:/share/MD0_DATA/Public/installarr before tests; retained HTTP POC
unit remained active. `python3 -m unittest discover -s tests -v`:115 tests,
114 passed, one root-only skip.

`sudo -n python3 -B tools/test_physical_profiles.py --app radarr` and
`sudo -n python3 -B tools/test_physical_profiles.py --app sonarr` both exited0.
Complete TRaSH snapshot d24f13ceea5e82ccc20d08b7814fca93840e4046:
Radarr HD Bluray + WEB,41 custom formats/3 default groups; Sonarr WEB-1080p,
37 custom formats/5 default groups. Runtime schema resolution, full write/readback,
restart and duplicate-free rerun passed, profile ID7 remained stable in both
disposable fixtures; container policy audits passed. Scripts removed their owned
containers/networks in finally. Local results: existing Bazarr fixture directories
/var/tmp/installarr-bazarr-test-d5rjwtr7/profile-result.json and
/var/tmp/installarr-bazarr-test-478idkci/profile-result.json. Original supplied
media and live POC profile assignments were not changed.

Operator delegated profile choice to the recommended approach. Selected starting
point: official HD Bluray + WEB for Radarr and WEB-1080p for Sonarr, using full
pinned definitions/default groups. This is an installer recommendation based on
TRaSH documented profiles, not an upstream universal recommendation. Integration
into configuration/apply and family ID routing remain outstanding.

## 2026-10-28 — operator HD cutoff and optional UHD profiles

Operator clarified: highest1080p movie cutoff, separately selectable2160p profile.
Full pinned Radarr Remux + WEB1080p (55 CFs/4 groups) and Remux + WEB2160p
(56 CFs/5 groups) passed `sudo -n python3 -B tools/test_physical_profiles.py
--app radarr`: complete API readback, restart, stable IDs8/9 and rerun. Both
profiles coexist; missing neutral-zero entries compare equivalently to API-added
zero scores when the other profile introduces formats. Nonzero scores and all
quality ordering/cutoffs still require exact readback. Disposable containers and
owned network removed; live POC untouched by this restart test.

Added optional quality_profiles config, strict pinned-ID/default validation, plan
preview, wizard choices and configure_apps reconciliation used by reference apply.
Preferred profile returns dynamic ID metadata for future request routing; no bulk
media assignment or assumed global Radarr default. Existing configurations omit
this field and preserve behavior. Full reference apply with this new field is not
yet physically exercised; shared app adapter is unit-tested.

Added the two profiles directly through the live POC Radarr adapter, with full
readback and immediate duplicate-free rerun: HD ID7/UHD ID8. No container restart,
config/state replacement or movie assignment writes. These options are now usable
in the retained GUI. Required suite117 tests,116 passed,1 root-only skip.

## 2026-10-28 — Tautulli protected bootstrap and published apply

Official guidance https://docs.linuxserver.io/images/docker-tautulli/ and upstream
v2.18.2 plexpy/config.py, webauth.py, webserve.py and lib/hashing_passwords.py
reviewed. Pinned LinuxServer2.18.2-ls249 digest
sha256:c6a48416d16b26f254b000133d2d844c1905ee58ed0f44aad9bda66598d39988.
Config-only unpublished fixture seeds upstream-compatible PBKDF2 SHA256/600000
password hash and independent random API key before first start. No plaintext
password in config or commands; existing config is verified/preserved.

Initial attempt refused anonymous303 because checks expected302/401. Added exact
CherryPy303 handling; did not weaken real login/password rejection. Evidence
/var/tmp/installarr-tautulli-test-6zl58cx9. Successful rerun fixture
/var/tmp/installarr-tautulli-test-83nybvu6: anonymous GUI303/API401, valid login200
and settings200, incorrect password401 and settings303, before/after restart.
Config.ini and tautulli.db owner2000:2000; existing-config seed rerun passed.

First full-apply attempt refused before provisioning because shared guard renderer
requires nonempty storage assertions; cleanup initially masked that error by trying
to stop absent unit. Fixed fixture cleanup and used a simple entrypoint wrapper
for this config-only app: no NAS/media/download bind exists. Existing storage
supervisor remains in place. Failed fixture /var/tmp/installarr-tautulli-apply-p3uwfa4i.
`sudo -n python3 -B tools/test_physical_tautulli_apply.py` then passed protected
bootstrap, published HTTP8181 authentication/rejection, reference apply rerun and
config verification in /var/tmp/installarr-tautulli-apply-qx2dovtf. Test unit
installarr-tautulli-auth-96165e00.service stopped; owned containers/networks removed.
Live Radarr/SAB pair remained active throughout.

Plex integration/authorization and optional Plex log bind remain pending; this is
authentication groundwork, not a validated connected Tautulli installation.

## 2026-10-28 — complete movie-profile reference apply

`sudo -n python3 -B tools/test_physical_profiles_apply.py` passed full protected
bootstrap, published loopback GUI authentication, HD/UHD profile readback, preferred
dynamic ID7, repeat apply and stable profile IDs7/8. Evidence
/var/tmp/installarr-profile-apply-rxav0qqy/result.json; stopped unit
installarr-profiles-5a218f19.service, removed owned containers/networks. Live
10.70.0.99 Radarr/SAB service stayed active; fixture used127.0.0.1 and its own DB.

## 2026-10-28 — official Plex image/permissions groundwork

Reviewed official https://github.com/plexinc/pms-docker README and entrypoint.
The public image digest1de9c641cddb30884794a98a5b476fc39e11d0d0703fe1b37c328f59f71590cc
contains no installed Plex package and fetches at startup; it was only inspected
with overridden entrypoint. Use full version1.43.5.11079-b3b13e506 instead, digest
sha256:6d778d41daae68f89115aa87a44ae14a96b23e71a2093da173b5a9aac4091336.
Confirmed package version matches version.txt; startup update script exits before
network lookup when these match.

`sudo -n python3 -B tools/test_physical_plex.py` passed no-network/no-published-port
first start/restart: API version1.43.5.11079-b3b13e506, stable machine identifier,
actual Plex process UID/GID2000:2000 and local library DB2000:2000, allowedNetworks
192.168.0.0/23 and customConnections readback. CHANGE_CONFIG_DIR_OWNERSHIP=false;
only local config/transcode binds. Evidence /var/tmp/installarr-plex-test-iy8xdz26.
Container removed. No account claim, NAS library selection or Plex integration
has been claimed as validated.

## 2026-10-28 — Plex claim, GUI and primary reference libraries/Tautulli

Operator securely supplied a claim through init-plex-claim and confirmed the GUI
was reachable and linked, initially displaying the container-ID server name and
empty libraries. The first apply checked authorization too soon after successful
claim exchange: token existed, but /identity had not yet reported claimed. Added
bounded account-readiness polling when a token is present; missing-token refusal
remains immediate. Retry succeeded with existing token, no second claim.
Evidence /var/tmp/installarr-plex-authorize-uo198y7v; initial unit
installarr-plex-auth-test.service is now stopped/disabled. Never print its claim
or Preferences.xml; those contain credentials. Host library API anonymous401,
valid token200, deliberately invalid token401 passed outside allowed-network preset.

Operator requested all reference libraries by default. Added explicit editable
Plex server name, media-relative library descriptors/plan paths, full schema/agent
language preflight and conflict refusal. New primary reference map uses the exact
verified /media/installarr NFS export and a read-only /data bind; local Plex DB
retained, not copied. Library scaffolding creates only missing directories and
preserves existing metadata. A separate secondary movie source is not supplied
and is not silently substituted. Ambiguous collections use personal-media type.

First library attempts returned400 for personal-media agent/modern scanner
incompatibility; inspected actual agent/language schema and response, switched
from legacy com.plexapp.agents.none to tv.plex.agents.none. Library creation then
passed. Tautulli link initially refused a mismatched pms_uuid: upstream generates
that as its own instance identity. Corrected to pms_identifier, retaining the
instance UUID. This distinction is verified from version-specific source.

`sudo -n python3 -B tools/test_physical_plex_libraries.py` passed all15 primary
libraries with IDs1-15 and exact paths, protected published Plex/Tautulli GUIs,
actual Tautulli lookup of Plex1.43.5.11079-b3b13e506, and unchanged size/mtime of
all3 supplied example files. Unit installarr-plex-libraries-test.service is active,
boot-disabled. Config/state/evidence /var/tmp/installarr-plex-libraries-m6m4j4kb;
original local config DBs remain under /var/tmp/installarr-plex-authorize-uo198y7v/configs.
NAS scaffolding is identified by exact private nonsecret config paths,
plus primary library directories and a unique root health marker.

Actual Plex reads: Movies ID1 contains Framing Britney Spears at its original
/data/Movies/...mkv; TV ID2 contains11.22.63 and one episode at original
/data/TV/11.22.63/Season1/...mkv. No copy/rename/delete or recursive NAS chown.
User playback confirmation requested asynchronously; playback not yet established.
Tautulli independent connected fixture /var/tmp/installarr-tautulli-test-fjspzit1
also passed auth/restart and actual Plex version lookup; removed only its container.
PMS link update is done stopped, with private backup and preserved unrelated fields;
API deliberately masks token, so reconciliation reads only private local config.

## 2026-10-28 — Ombi and netboot published bootstrap acceptance

Ombi official source v4.53.10 and LinuxServer guidance reviewed. Pinned4.53.10-ls274
image digest19d4f86713e7203d910b4aa431d7176e7a9a22f641beb1047da45aa989296509.
`sudo -n python3 -B tools/test_physical_ombi.py`: shared local administrator,
real JWT login/current Admin role, anonymous401, invalid password401, closed wizard,
stable user ID after restart and local Ombi/OmbiSettings DB owner2000:2000 passed.
Evidence /var/tmp/installarr-ombi-test-6ixb9f51. No family lookalikes created.
`sudo -n python3 -B tools/test_physical_ombi_apply.py` passed published HTTP3579
and full apply/rerun in /var/tmp/installarr-ombi-apply-96149_t6. Unit
ombi-auth-a782286e stopped, owned containers/network removed. Host supervisor uses
read-only SQLite to require a password-bearing local Admin before publication;
UserType1 is the tested local type (built-in type0 has no Admin password).
No Plex/family/Arr/request integration claim is made.

netboot official image0.7.6-nbxyz27 digest
109e60b2d0090a6b34a5ac67e7ccc623991f7291ab25c37040fd2e554a14d7fe;
menus3.0.3, iPXE Secure Bootv2.0.0. Native image already includes Nginx: added a
protected frontend configuration in that same container, not an auxiliary service.
Nginx3000 proxies Node3001, shared salted SHA512 Basic credentials are private;
Node3001 is not published. Both page and Socket.IO polling require valid login.
`sudo -n python3 -B tools/test_physical_netboot.py` passed401/200/401 for both,
restart, menu UID911/GID1001 and real911:1001 local assets write/read/cleanup.
Evidence /var/tmp/installarr-netboot-test-7f2l8vhy. No DHCP/PXE changes/tests.

First published apply waited on storage health: the supervisor incorrectly used
2000:2000 for911:1001 config. It refused access correctly; permissions were not
relaxed. Cleanup also tried removing an absent bridge; fixture now checks its own
network exists. Failed evidence /var/tmp/installarr-netboot-apply-aov1re9x.
Fixed health specs with per-app identities and separate bounded workers; any
unreaped worker blocks new probes. No forking of an easily-killed root parent.
`sudo -n python3 -B tools/test_physical_netboot_apply.py` then passed published
HTTP3250 GUI/Socket.IO authentication and full apply/rerun. Evidence
/var/tmp/installarr-netboot-apply-wp67sxas, unit netboot-auth-254f4021 stopped,
owned containers/networks removed. Config/assets stayed local; no NAS chown.
OpenSSL is an explicit signed application prerequisite for password hashing.

## 2026-10-28 — final operator library grouping/exclusions and playback

Operator confirmed movie and episode playback in the actual Plex GUI. Clarified
that TV and Movies aggregate multiple folders, rather than separate family
libraries. `sudo -n python3 -B tools/reconcile_plex_test_groups.py` verified parent
folder sets before removing only the six incorrectly created family/low-resolution
test sections. Existing Movies ID1/TV ID2 survived. Evidence
/var/tmp/installarr-plex-grouped-2qnbn8su; its unit is now stopped/superseded.

Operator then removed Disney, Only Heather, YouTube Videos and TubeSync Videos
from all installer runs, and finally required identical library/folder names:
sports→sports and StandUp→StandUp. Earlier sport/comedy aliases are superseded.
Defaults/validation enforce this; low-res folders are rejected. Multiple folder
locations use repeated location parameters; ordinary apply permits additions,
refuses silent repointing/removal and preserves unknown unrelated libraries.
Explicitly removed names are reconciled out using section-metadata DELETE only.
Plex media binds remain read-only; no media-file deletion API is called.

`sudo -n python3 -B tools/standardize_plex_test_libraries.py` passed current
reference apply with5 libraries: Movies1 (4 paths), TV2 (3 paths), sports7,
StandUp8, Music9. Four forbidden sections were removed/readback-verified. Evidence
/var/tmp/installarr-plex-standard-2bbujwqu/result.json. Active/boot-disabled unit
installarr-plex-standard-test.service supersedes all older Plex units sharing its
local DB. Radarr/SAB proof of concept stayed active throughout these transitions.
Read-only NAS and Plex-log binds plus current container policy audit passed.
Movies-2 is an empty isolated test folder; production secondary-source provisioning
is still a gap. Original supplied media were not moved, renamed or deleted.

Current verification: `python3 -m unittest discover -s tests -q` and
`sudo -n python3 -B -m unittest discover -s tests -q`:134 tests each,133 passed/1
appropriate identity-dependent skip. Root skips operator I/O test; htpc skips
root-only system-file test. All installer modules pass Python3.8 grammar parsing;
this is not a20.04 clean-install/runtime claim. No reboot, commit or push.

## 2026-10-28 — operator-requested saved checkpoint

Final `sudo -n python3 -B -m installarr apply --reference --config
/var/tmp/installarr-plex-standard-2bbujwqu/config.json --name plex-standard-test
--state-directory /var/tmp/installarr-plex-standard-2bbujwqu/state` exited0.
Exactly5 libraries retained IDs1/2/7/8/9 and grouped paths; no removed sections
recreated. Plex host authorization and Tautulli GUI auth/actual Plex connection
passed again. Both current service pairs active and boot-disabled; no running
implementation/fixture process at savepoint. Working-tree/docs saved, no Git
commit/push. Work paused at operator request, to resume with Ombi integrations.

## 2026-10-28 continuation: Ombi actual integrations and requests

Operator resumed after the savepoint, reporting stopped containers. Read-only
`systemctl is-active`, Docker inventory and `findmnt --mountpoint /media/installarr`
found Docker/containerd and the two retained pairs already active, with the exact
approved NFS source/type. No broad restart or superseded Plex unit was started.

Implemented authenticated, secret-free-evidence Ombi connectors for the pinned
4.53.10-ls274 runtime. Settings and remote lookups follow the versioned official
[Settings controller](https://github.com/Ombi-app/Ombi/blob/v4.53.10/src/Ombi/Controllers/V1/SettingsController.cs),
[Movie sender](https://github.com/Ombi-app/Ombi/blob/v4.53.10/src/Ombi.Core/Senders/MovieSender.cs)
and [TV sender](https://github.com/Ombi-app/Ombi/blob/v4.53.10/src/Ombi.Core/Senders/TvSender.cs).
Radarr's global default root is a path string; Sonarr's is a dynamic root ID.
An initial remote-lookup-only Radarr fixture used an ID for both; source review
caught this before request testing and the implementation was corrected. This
illustrates why accepted settings/connection tests do not prove dispatch.

Commands and retained private evidence (all disposable containers/networks removed):

- `sudo -n python3 -B tools/test_physical_ombi_arr.py --app radarr`:
  `/var/tmp/installarr-ombi-arr-test-k1zjxsl2`, initial remote lookup/restart/rerun.
- `sudo -n python3 -B tools/test_physical_ombi_arr.py --app sonarr`:
  `/var/tmp/installarr-ombi-arr-test-0uxpe_rj`; actual Ombi remote profile/root calls,
  bad remote key rejected before settings save, restart/rerun and DB UID/GID2000.
- `sudo -n python3 -B tools/test_physical_ombi_arr.py --app radarr --request`:
  `/var/tmp/installarr-ombi-arr-test-tf69z8db`; bad key rejected, actual Ombi movie
  request for TMDB10331 reached Radarr as ID1, profile7 (Remux + WEB1080p),
  `/data/Movies/Night of the Living Dead (1968)`, monitored true.
- `sudo -n python3 -B tools/test_physical_ombi_arr.py --app sonarr --request`:
  `/var/tmp/installarr-ombi-arr-test-1vwmytpe`; actual Ombi TV request for TVDB301824,
  season1/episode1, reached Sonarr ID1, profile7 (WEB-1080p), `/data/TV/11.22.63`,
  monitored true. Connection configuration survived restart/rerun.
- `sudo -n python3 -B tools/test_physical_ombi_arr_apply.py`:
  `/var/tmp/installarr-ombi-arr-apply-yhuynx34`, unit ombi-arr-41f6d0ed;
  full protected-bootstrap/published HTTP127.0.0.1 apply and rerun passed. Ombi
  saved remote profile/root calls were reverified after publication. Unit stopped,
  owned containers and fixture networks removed. Original retained pairs untouched.

These requests verify Ombi-to-Arr dispatch/default routing only. No indexer or
provider/downloader was configured in the fixtures; downloads, family identity
requests, post-request restart persistence and actual provider access are not claimed.
No supplied movie/episode was moved, renamed or deleted. Temporary NAS paths
were below the approved export in new Installarr-Ombi-Arr-* directories.

`sudo -n python3 -B tools/test_physical_ombi_plex.py` initially passed actual
Ombi POST Plex/Libraries against the retained claimed server, exact five-library
IDs1/2/7/8/9, saved settings and restart/rerun. Evidence:
`/var/tmp/installarr-ombi-plex-2tsk8m7r`. The fixture joins the existing approved
Plex test network; it starts only Ombi and never starts a second Plex database.
Private Plex token travels through stdin/private Ombi DB, never CLI/config/evidence.
The link preserves the Ombi install ID and uses explicit selected libraries.

A subsequent content-sync acceptance extension deliberately failed its deadline:
`/var/tmp/installarr-ombi-plex-cfandba7`. An explicit authenticated
`POST /api/v1/Job/plexcontentcacher` returned true; OmbiExternal.db contained one
TV show and one episode, but no movie. Read-only Plex API inspection established
`local://1` for Framing Britney Spears and `local://2` for the TV show (displayed
as `11 22 63`), with no matched external IDs. Playback does not prove metadata
matching. Operator was asked to use Match/Fix Match for the supplied movie (2021)
and show (2016) in the Plex GUI. Availability remains unvalidated; no fake IDs or
successful-sync claim added. The failed fixture container was stopped/removed.

Unit coverage adds dynamic root/profile selection, exact Plex library selection,
4K preservation, repeat-run no-op behavior, conflict refusal before save, wrong
remote roots and bearer cleanup on failures. Published Ombi connections use the
same adapters after bootstrap; family import/presets remain unconfigured.

Final continuation checks: `python3 -m unittest discover -s tests -q` and
`sudo -n python3 -B -m unittest discover -s tests -q` each ran138 tests,137 passed/1
appropriate skip. Python3.8 grammar parsing and `git diff --check` passed. This
is not clean20.04/24.04 runtime evidence. No commit/push or reboot. The pending GUI
matching question is the next availability acceptance dependency.

## 2026-10-28: matched Plex availability, native family identities and routing

Operator matched Framing Britney Spears (2021) and 11.22.63 (2016) in Plex.
Read-only Plex section queries now report plex://movie/601b12841c7caa002dcbd980
and plex://show/5d9c081008fddd001f291600 rather than local:// GUIDs.
`sudo -n python3 -B tools/test_physical_ombi_plex.py` passed:
`/var/tmp/installarr-ombi-plex-eiwyt_jp`. Ombi's own content database contains
exactly the supplied movie, show and episode; counts and connection settings
survived restart/rerun. No supplied media was modified.

Native family source/behavior uses Ombi4.53.10's
[Plex importer](https://github.com/Ombi-app/Ombi/blob/v4.53.10/src/Ombi.Schedule/Jobs/Plex/PlexUserImporter.cs),
[identity controller](https://github.com/Ombi-app/Ombi/blob/v4.53.10/src/Ombi/Controllers/V1/IdentityController.cs)
and [Plex identity lookup](https://github.com/Ombi-app/Ombi/blob/v4.53.10/src/Ombi.Core/Authentication/OmbiUserManager.cs).
Read-only friend discovery found all three specified accounts plus18 unrelated
friends; only the three named accounts were selected. No production app, share or
sibling media directory was inspected. Account discovery is via the already
operator-authorized Plex account, not a production application configuration.

`sudo -n python3 -B tools/test_physical_ombi_family.py`:
- discovery `/var/tmp/installarr-ombi-plex-qllqk324`;
- first import attempt `/var/tmp/installarr-ombi-plex-_efy88cr` failed readback because
  a pristine UserManagement settings record acquires its first database ID on save.
  Temporary settings restoration actually persisted false import flags; exact-ID
  comparison incorrectly reported restoration failure. Comparison now ignores only
  the settings database ID, preserving every user-facing field.
- `/var/tmp/installarr-ombi-plex-ijlmfvek` passed native selective import, all three
  UserType2 Plex identities, movie/TV approval roles, Beanie PowerUser, disabled
  Discord preferences, content sync and restart/rerun. No local passwords created.

Added opt-in `ombi_family_presets` configuration, CLI choice and planned paths.
Ombi/Plex plus at least one Arr and its pinned recommended1080p profile are required.
The shared storage map supplies lenoramovies/lenoratv and jeremymovies/jeremytv.
Beanie deliberately stores zero overrides to inherit globals. Family HD profile
selection is independent of a possible global UHD preference. Import uses Ombi's
native job with unrelated known friends excluded, no default elevated roles and
cleanup disabled. Original import settings are restored. A private locked journal
records original settings before temporary writes; reruns restore an interrupted
operation before checking existing users. Unexpected imported identities refuse
publication. Physical sudden-kill recovery/full combined family apply remain open;
unit coverage exercises durable recovery before the existing-user shortcut.

`sudo -n python3 -B tools/test_physical_ombi_family_arr.py --app radarr`:
- first `/var/tmp/installarr-ombi-arr-test-atd56ixx` dispatched Lenora's movie but
  a subsequent request returned500. Private log identifies upstream SQLite Error5,
  database locked, during MovieRequestEngine.ApproveMovie. Preserved as a failure;
  no blanket request retry or database-journal tweak was added to the installer.
- focused Jeremy request `--family-user rebel739` passed in
  `/var/tmp/installarr-ombi-arr-test-98s28bei`.
- full sequential rerun `/var/tmp/installarr-ombi-arr-test-ts1q6yh9` passed all three
  on-behalf requests, 1080p profile7, native root IDs and restart persistence:
  Lenora→/data/lenoramovies/Night of the Living Dead (1968),
  Jeremy→/data/jeremymovies/Plan 9 from Outer Space (1957),
  Beanie→/data/Movies/The General (1926). Fixture pauses2s between requests to let
  upstream background writes settle; rapid/concurrent SQLite behavior remains a limit.

`sudo -n python3 -B tools/test_physical_ombi_family_arr.py --app sonarr`:
`/var/tmp/installarr-ombi-arr-test-tw9tnbp6` passed all three on-behalf requests,
WEB-1080p profile7 and restart persistence:
Lenora→/data/lenoratv/11.22.63,
Jeremy→/data/jeremytv/Planet Earth,
Beanie→/data/TV/Firefly.
SQLite read-only checks confirmed exactly admin plus the three family users,
UserType2, genuine provider IDs and no family password hashes. Both pair fixtures
were removed. Their temporary secondary network attachment was only for initial
read-only Plex lookup/native import and was disconnected before controller audits
and restarts. Normal generated reference deployment remains one approved bridge;
network auditing was not relaxed. No providers/downloaders/indexers in these pairs.
These are administrator on-behalf routing tests, not actual family browser sign-in.

A protected Ombi-only GUI fixture is retained specifically for actual Plex sign-in:
`sudo -n python3 -B tools/prepare_ombi_family_gui.py`;
`/var/tmp/installarr-ombi-family-gui-o799mzbk/config.json` and state;
unit `installarr-ombi-family-2274744e.service`, active/boot-disabled,
http://10.70.0.99:3579. It copies only the stopped installer-owned local family-test
DBs, with private config and2000:2000 application files. Reference bootstrap,
published shared-admin auth/rejection and full apply/rerun passed. No request
backends selected; it is not the family-routing acceptance stack. Operator was
asked to test Plex sign-in with one imported family account in a private browser.
Never ask for their credentials/tokens. Original two retained pairs stay active.

CLI library menus now keep all reference groups by default, optionally select
whole groups and edit their folder lists without splitting Movies/TV. Exact
sports/StandUp naming policy stays enforced. Plans now recognize all nine tested
reference adapters and report selected integration links, missing provider/input
choices and absent request/download backends without adding applications. Jackett
is explicitly not a torrent downloader.

## 2026-10-28: supported Ubuntu Python userspace runtime checks

`sudo -n python3 -B tools/test_supported_python.py` passed the148-test suite in
both official Ubuntu userspace containers (147 passed/1 appropriate root skip):
- Ubuntu20.04, Python3.8.10,
  ubuntu@sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214.
- Ubuntu24.04, Python3.12.3,
  ubuntu@sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c.
Evidence/logs: `/var/tmp/installarr-ubuntu-runtime-vydoi_dc`.
Signed distro repositories supplied Python/openssl/tzdata/CA packages inside
containers only. Only installarr/tests source directories were bound read-only;
no host Docker socket, credentials, NAS, privileged mode or host network mounts.
Containers were removed automatically. This establishes actual Python runtime
compatibility, not clean-OS provisioning/systemd/boot acceptance.

Final host suites after the orchestration regression test:149 tests,148 passed/1
appropriate skip as both htpc and root. The added test proves that a global UHD
preference still gives family overrides the separately pinned HD profile, resolves
root IDs dynamically and passes the private recovery path to native import.
Python3.8 grammar and git diff whitespace checks pass. Ubuntu container runs above
used the immediately preceding148-test suite; no claim of149-container tests.

## 2026-10-28 operator-owned Plex sign-in identity

Operator rejected the request to test using other people’s family credentials and
authorized importing their own Plex account boosted3svt. This correction supersedes
the earlier GUI question; do not ask for shared family passwords.
`sudo -n python3 -B tools/import_ombi_operator_gui.py` passed in the existing retained
GUI fixture. The claimed server owner’s username was verified privately before
calling the native Plex owner importer. Only boosted3svt was added; import-users
and cleanup stayed disabled, temporary import-admin settings were restored through
a private recovery journal. Native owner import grants Admin. After systemd restart,
Plex UserType2, genuine provider ID, absent local password hash, native Admin role
and shared-local-admin auth/rejection all passed. Result:
/var/tmp/installarr-ombi-family-gui-o799mzbk/operator-import-result.json.
No credentials/tokens printed, no production state inspected, no application code
changed, no commit/push/reboot. Actual boosted3svt browser Plex sign-in is pending.

## 2026-10-28: operator-confirmed Plex sign-in and genuine ordinary-user requests

Operator confirmed browser Plex sign-in as boosted3svt. No family credentials
were requested or obtained after the correction. Tests below use only the already
operator-authorized Plex owner token, kept private; they do not mint fake JWTs,
change Plex permissions or use administrator on-behalf requests.

`sudo -n python3 -B tools/test_physical_ombi_operator_request.py` passed against
the retained Ombi/Radarr fixtures. The Ombi adapter now supports native
/api/v1/Token/plextoken authentication with bearer cleanup, and an explicitly
validated IPv4 backend address for this split-fixture test. Normal generated
reference links still default to service DNS names; no Docker network audit was
relaxed and no new network/backend/service was added.

Before requesting, Radarr indexer list was verified empty. Directory preparation
used exact mounted storage and service UID in a new subfolder under the retained
approved NAS POC subtree. Existing movie assignments were preserved. Native Plex
identity readback was boosted3svt, UserType2; request attribution matched that ID.
The General (1926), TMDB961, reached Radarr ID1, profile7, monitored true,
/data/Ombi-Operator-Test/Movies/The General (1926). Dedicated root ID2. Evidence:
/var/tmp/installarr-ombi-family-gui-o799mzbk/operator-request-result.json.
This updates the GUI fixture from sign-in-only to a connected Radarr request test;
it still has no Sonarr backend or real indexers/download proof.

`sudo -n python3 -B tools/test_physical_ombi_operator_routes.py` passed three
ordinary-user cases using boosted3svt's real native Plex authentication. A private
recovery journal saved the operator's original Ombi roles/profiles; temporary roles
excluded Admin. Each case authenticated afresh after role changes, verified
UserType2 and Admin false, submitted its own request without requestOnBehalf, and
checked requestedUserId against boosted3svt. Results (all profile7):
- Lenora-equivalent: /data/lenoramovies/Night of the Living Dead (1968).
- Jeremy-equivalent: /data/jeremymovies/Plan 9 from Outer Space (1957).
- Beanie-equivalent PowerUser/global inheritance:
  /data/Ombi-Operator-Test/Movies/His Girl Friday (1940).
Original operator Admin claims/profiles were restored in finally and read back;
private recovery journal cleared. Plex account permissions were never changed.
Evidence: /var/tmp/installarr-ombi-family-gui-o799mzbk/operator-routes-result.json.
No other people's credentials or local Plex-user passwords were used. This tests
permission/routing behavior with an authorized real Plex identity, rather than
requiring each family member to share credentials. Indexers stayed zero; no download
claim. Initial global-root request and all existing records were preserved.

## 2026-10-28: physical interrupted native family import recovery

`sudo -n python3 -B tools/test_physical_ombi_import_recovery.py` passed:
/var/tmp/installarr-ombi-import-recovery-50pnnry8/result.json. One unpublished Ombi
container only, local DB and existing Plex test-network connection; no second Plex.
Child CLI persisted original user-import settings in the locked journal, enabled
temporary selective import, read back the active flag, then received SIGKILL (-9).
Parent verified both the durable restore record and actual still-enabled app flag.
A normal import_family rerun restored original settings before reconciliation,
imported exactly lenora8/rebel739/beanie08 as native Plex users, restored all original
import settings, and cleared the journal. Total users=4 (local admin plus3 Plex).
Container restart and rerun retained identical IDs and false import flags. No
unrelated account import, user cleanup or publication. Fixture stopped/removed.

`sudo -n python3 -B tools/audit_runtime_snapshots.py` verified content hashes of
all three retained service snapshots against their saved directory identities.
All snapshots predate the current checkout; automatic code-refresh is absent.
Audit preserved all units/definitions and reported that limitation rather than
silently replacing running supervision. Runtime-refresh reconciliation remains open.

Added unit coverage for native Plex bearer cleanup on exceptions, explicit LAN
backend lookup and refusal of URLs/unspecified/multicast/non-string addresses.
Host suites now151 tests,150 passed/1 appropriate skip each as htpc and root.
Python3.8 grammar/whitespace checks passed. Earlier container runtime tests remain
148 tests, as documented. No reboot/commit/push. Next nonsecret input requested:
Usenet/indexer/subtitle provider names; credentials must be collected locally.

## 2026-10-28 provider selections, private input and adapter preparation

Operator specified Newshosting, NZBGeek and subtitle providers, and explicitly set
Newshosting maximum connections to100. Latest subtitle correction supersedes the
earlier .org answer: production Bazarr uses **OpenSubtitles.com, Yify Subtitles,
Supersubtitles and TVSubtitles**. No .org credential migration/signup was performed.

Newshosting's [official NNTP settings](https://support.newshosting.com/kb/article/104-newshosting-nntp-server-information/)
confirm news.newshosting.com, TLS563 and plan-dependent limits including100.
Configuration uses the operator's100 limit with certificate verification3 (strict).
NZBGeek uses its [official API endpoint](https://api.nzbgeek.info/), direct Newznab
connections in selected Sonarr/Radarr; no new indexer-manager/backend or torrent
client added. API-key/authentication/caps testing remains pending real credentials.

Inspected only the pinned Bazarr image with an unpublished networkless throwaway
container, overridden shell entrypoint, no host or NAS bind. Its installed provider
modules include opensubtitlescom/yifysubtitles/supersubtitles/tvsubtitles and no
OpenSubtitles.org provider. Tagged1.6.2 source agrees. Bazarr's
[official migration guidance](https://wiki.bazarr.media/Troubleshooting/OpenSubtitles-migration/)
confirms .org/.com accounts are separate. Latest operator list uses the available
.com provider, so no unsupported .org configuration is generated.

Implemented `init-provider-secrets`: all account usernames/passwords/API keys are
collected with hidden prompts, stored in executor-owned0600 providers.json under
locked0700 storage. Checkpoints contain only selected names/fingerprint, no values.
Reruns preserve existing credentials; wrong file mode/symlink/unknown records fail.
Nonsecret JSON accepts provider choices and a credential-file path only, never the
credential values. Wizard offers optional selections, editable connection count,
and four reference subtitle providers. Each app remains optional; dependencies
are checked rather than silently installed.

Reference apply preloads required private credentials before host changes; adapters
then configure selected services after protected bootstrap. Newshosting tests its
native TLS/auth connection before saving; server readback and saved connection
are checked. NZBGeek resolves schema/IDs/categories dynamically, tests before save,
reads back and retests saved entries. Conflicting definitions are preserved.
Bazarr reads back the exact four-provider selection and account settings without
claiming provider authentication or searches. Legacy isolated apply refuses provider
configuration before host mutations. Full provider apply/real credentials/restart
integration acceptance remain outstanding; mocked tests are not remote proof.

`check-providers` tests existing owned reference apps without saving settings:
Newshosting native test_server and Sonarr/Radarr Newznab test endpoints. It reports
OpenSubtitles credentials as awaiting actual Bazarr authentication/search, rather
than passing on file validation. Connection tests do not enable indexers or start
downloads. Provider secrets were not yet present when checked; operator has been
asked to collect them locally, never paste them into chat.

`sudo -n python3 -B tools/test_physical_bazarr_providers.py --app radarr` passed:
/var/tmp/installarr-bazarr-providers-f1zfacud. Disposable empty-library Bazarr/Radarr
pair; all four enabled-provider names and unused synthetic OpenSubtitles settings
survived restart/rerun, shared auth and database ownership2000:2000. No subtitle
search/download or real provider authentication. Correct repeated form encoding
(doseq) is now supported by Docker/host HTTP transports. Owned fixture removed.

Native SAB config/test_server schema confirmed against retained5.1.3 by submitting
an absent hostname, which was rejected before network access; response is under
value.result. Tagged ConfigServer/OptionBool source explains server ssl/enable
as integer0/1. The first networkless synthetic server-schema fixture
/var/tmp/installarr-sab-provider-schema-kfyu9_pn successfully saved via POST but
its assertion incorrectly required Python booleans; fixed to native0/1 and rerun.
Server credential updates now use POST form rather than query parameters, keeping
provider usernames/passwords out of request URLs. No real credentials were used.

Unit tests cover credential output/checkpoint separation, hidden CLI prompts,
existing-file reuse/permissions, embedded-secret rejection,100-connection bounds,
TLS metadata/readback, pre-save refusal, dynamic indexer IDs/categories, repeated
runs without duplicates, and connection-test-only operations without writes.

## 2026-10-28: real provider credentials, reference apply and Newshosting download

Operator reported successful local credential collection/checks. The actual private
store is **/var/tmp/installarr-providers-secrets/providers.json** (plural providers),
not the earlier suggested singular directory. Located by filename metadata only,
then validated with the strict private-file reader; no credential re-entry needed
and no values printed. Keep this path in future config/resume instructions.

First real check exposed SAB's pristine `get_config(section=servers)` response:
config exists but no servers key until a server is created. Adapter now treats that
as an empty collection; unit regression covers the native shape. No setting had
been saved by that failed check. Corrected command passed real Newshosting TLS/
authentication and NZBGeek Radarr Newznab test without saving or enabling anything.

The server POST-schema rerun also passed in
/var/tmp/installarr-sab-provider-schema-_3pf7tv3:100 connections, TLS563, strict
verification3, disabled synthetic host, native integer ssl/enable fields and restart
persistence. Network none, no real credentials/provider access in that fixture.

`sudo -n python3 -B tools/test_physical_real_providers.py --app radarr` passed:
/var/tmp/installarr-real-providers-9l_x5rmi, unit providers-80e22607;
NAS fixture /media/installarr/Installarr-Providers-80e22607. Minimal Radarr/SAB pair,
protected bootstrap and published loopback authentication, actual Newshosting100
connection settings, NZBGeek dynamic indexer ID1/category2000, full profiles and
reference apply/rerun all passed. Newshosting stored-password connection was tested
again via SAB's native server selector; repeated apply preserved the indexer ID.

Then SAB fetched the [official100MB random-data test](https://sabnzbd.org/tests/test_download_100MB.nzb)
through its normal URL fetcher, and downloaded through Newshosting. Host urllib
had received403 for the NZB URL; SAB's own normal client fetched it successfully.
No TLS verification disabled, alternate-IP/cookie workaround or bypass was used.
Native history status Completed, downloaded bytes114,967,316. All13 RAR/PAR files
were fs-read/hashed in the configured movies download category, owned2000:2000.
Full per-file sizes/SHA256 are in result.json; total payload includes repair data.
No original movie/TV/subtitle file was copied, renamed or overwritten. This proves
real NNTP transfer/storage, not movie/TV unpack/import or an Arr-selected release.
Owned units stopped, containers/networks removed; generated test files retained.
Original Radarr/SAB/Plex/Tautulli/Ombi fixtures remain unchanged/available.

`sudo -n python3 -B tools/test_physical_real_providers.py --app sonarr` passed:
/var/tmp/installarr-real-providers-80_97ydp, unit providers-95bd7c45. Actual Sonarr/
SAB pair, Newshosting100, NZBGeek dynamic ID1/category5000, protected bootstrap,
published auth and full reference apply/rerun passed.100MB transfer was not repeated
in that pair. Owned units/containers/networks stopped/removed.

## 2026-10-28: actual subtitle provider searches/download and English defaults

`sudo -n python3 -B tools/test_physical_bazarr_real_provider.py --app radarr`
used /var/tmp/installarr-bazarr-real-provider-_bzzjmn2 and its own empty NAS fixture.
Two harness errors preceded real probing: an inner app_client import incorrectly
shadowed the earlier call; then the sample Plex movie had TMDB/TVDB GUIDs but no
IMDb GUID. Fixed scoping and used the native OpenSubtitles title-search fallback,
without inventing an IMDb match or changing supplied media. Same fixture resumed.

The actual pinned image's OpenSubtitlesComProvider and its own bundled consumer
API key authenticated using the operator's private .com account, returned3 English
results for Framing Britney Spears, and downloaded one subtitle. Probe ran as
UID/GID2000, wrote only /data/installarr-provider-tests/opensubtitlescom.en.srt in
the new test subtree, fsynced/read back127,209 bytes, SHA256
`a32e97e12e04655e467dab93b528bcd2b310696b3218cc8f46789f9cea247513`.
Content was not emitted in chat/logs. Actual credentials, tokens and consumer key
travel only in private settings/stdin/in-memory; logging suppressed in the probe.
Settings/auth/database ownership/Arr link persisted across restart/rerun. This uses
the same bundled provider implementation, not a fake search response. It is not yet
a scheduled Bazarr library-search/download pipeline acceptance test.

Public native-provider probes used short-lived cap-dropped containers,2000:2000,
no credentials/media/host binds and no downloads. First evidence:
/var/tmp/installarr-public-subtitle-probes-wew5ghy_. Yify failed with SSLError;
Supersubtitles/TVSubtitles initially hit a harness TypeError because the bundled
Episode constructor takes singular episode, not episodes. Corrected only the probe.
Rerun evidence /var/tmp/installarr-public-subtitle-probes-1ss__yg2:
Supersubtitles native English search completed with0 results for11.22.63 S01E01;
TVSubtitles failed with HTTPError. Do not call these providers fully validated.
All four requested providers remain selected; no TLS weakening, added solver
backend, forked image or silent provider removal. OpenSubtitles.com is proven.

Operator explicitly selected **English, standard subtitles** for new movies/TV.
Added opt-in `bazarr_language_profile: english-standard`, wizard choice, plan and
apply wiring. Adapter uses actual enabled-language/profile APIs, allocates profile
IDs from the current collection, preserves unrelated profiles/languages, refuses
conflicting existing definitions/defaults before writes, and sets only future-media
defaults. English item is neither forced nor hearing-impaired. It does not bulk
reassign existing media. Repeated calls with matching state do not rewrite settings.

`sudo -n python3 -B tools/test_physical_bazarr_real_provider.py --app radarr`
with the language flag passed in /var/tmp/installarr-bazarr-english-jhs65sjw,
NAS /media/installarr/Installarr-Bazarr-8f371eef. Native English profile ID1,
movie/series default flags and profile IDs, all four providers, shared auth, Arr link
and2000:2000 DBs persisted across restart/rerun. A second native account/search/
subtitle download produced the same127,209-byte SHA256 under that separate fixture.
All owned containers/networks removed; the original supplied examples untouched.

New unit tests verify dynamic English ID42 in the presence of an unrelated ID41
profile, preserving that profile and its enabled French language, no duplicate/
write on rerun, and conflict refusal before mutation. Final host suites158 tests,
157 passed/1 appropriate skip each as htpc/root. Python3.8 grammar and whitespace
checks passed. Earlier Ubuntu20.04/24.04 runtime suites remain148 tests, not158.
No Git commit/push/reboot; user requested a pause after this English-default step.

## Autonomous continuation2026-10-28: classification and scheduled subtitle pipeline

Operator requested approximately5h continuous noninteractive work, queuing user
interaction instead of stopping. AUTONOMOUS_WORK_PLAN.md classifies every open
area; INTERACTIVE_TEST_QUEUE.md records baseline services and restoration needs.
No reboot/production access or extra backend was authorized. No questions asked.

`sudo -n python3 -B tools/test_physical_bazarr_scheduled.py` created only a new
Radarr/Bazarr pair and asserted NAS subtree:
/var/tmp/installarr-bazarr-scheduled-jrywgs8p,
/media/installarr/Installarr-Bazarr-Scheduled-fbafc148,
project installarr-bazarr-scheduled-fbafc148. Original examples were never bound,
copied or changed. No indexer/downloader selected. A real synthetic H264 video
(black frames sparse over90min) was created underUID2000. First Radarr scan refused
it because there was no audio track; this was correct app validation, not relaxed.
Regenerated only that owned fixture with silent AAC English audio. Native rescan
recognized it without an import-mode override/manager.

`sudo -n python3 -B tools/test_physical_bazarr_scheduled.py --resume /var/tmp/installarr-bazarr-scheduled-jrywgs8p --regenerate-video`
passed. Bazarr's normal update_movies scheduler job imported the generated movie
with the configured English profile; registered movies_full_scan_subtitles and
wanted_search_missing_subtitles_movies jobs were executed-now through native task
API (not a standalone provider call). It wrote a75,455-byte English subtitle next
to the generated video, UID/GID2000:2000, SHA256
940883a5f179b769db447b5125a4c39a7c212eb8adac9132cc8dbb46ae3806ba.
The generated video's hash stayed unchanged. Restart/rerun preserved movie/profile
state and subtitle. All four requested providers remained selected; normal pool
fallback succeeded despite known external-provider errors. This verifies the
registered scheduled search pipeline, not a claim that a multi-hour timer elapsed.
Owned containers/network removed; config/results/outputs retained.

## Autonomous continuation: explicit netboot assets and combination audit

Implemented optional storage.netboot_assets in the existing storage map, with its
own local/existing/NFS/SMB choice, exact assertions/marker, /assets bind and guarded
entrypoint. Required packages/mount reconciliation reuse existing adapters. Asset
directory creation and read/write probes use911:1001; ongoing supervisor health
checks include both default and explicit assets with the reserved identity. SMB
forceuid/gid derive911/1001 for dedicated assets; sharing a forced-UID SMB mount
with differently-owned media is rejected. No Samba service added/tested.

Local asset acceptance:
`sudo -n python3 -B tools/test_physical_netboot_assets.py --storage local` passed
in /var/tmp/installarr-netboot-assets-_t2ptnb5, unit netboot-assets-2a729d6e.
Protected reference apply/rerun, separate local asset bind, real911:1001 writes and
persistence across restart passed. Owned unit stopped/containers/network removed.

NFS first fixture /var/tmp/installarr-netboot-assets-bdyk4wye passed apply/rerun,
911:1001 writes and restart. Marker-loss supervision correctly stopped its container
and reported waiting_storage, but the harness mistakenly waited for nonexistent
storage_unhealthy, so timed out. Marker restored in finally, own unit/containers/
network removed. Corrected harness to the actual published lifecycle phase; no
supervisor/permission relaxation was made. Rerun evidence follows when complete.

Read-only render matrix now covers all511 nonempty subsets of9 optional apps in
legacy/bootstrap/reference modes. Tests verify exact selection/no auto-additions,
protected publication, correct ports/networks, no host-path fallback creation,
restart=no, conditional read-only Tautulli logs and unpublished netboot backend3001.
This is render/plan coverage, not physical511-stack acceptance.

Explicit asset paths exposed a host write-probe limitation: a root-private ancestor
prevented service traversal even though Docker can bind the service-owned leaf.
Probe now opens/asserts the source as root, drops all groups/UID/GID, then reopens
and writes through the verified leaf FD. This matches Docker bind access semantics;
actual leaf permissions still apply. Physical local probe evidence
/var/tmp/installarr-private-write-fd-cckn77al: private parent with911-owned leaf
passed write/fsync/readback/cleanup; root-only leaf refused before writes. No data
ownership was changed to hide a permission failure.

## Autonomous netboot NFS completion and optional-app matrix (2026-10-29)

Corrected NFS asset fixture completed: /var/tmp/installarr-netboot-assets-muufrje2/result.json,
unit installarr-netboot-assets-be56e9b2.service (now stopped, containers/network removed).
Explicit assets /media/installarr/Installarr-Netboot-Assets-muufrje2 on the exact
approved NFS export passed911:1001 write/fsync/readback/cleanup, protected GUI/socket,
apply/rerun and restart persistence. Removing only its own assets-ready marker
produced waiting_storage and stopped its container; restoration recovered it.
This is a sentinel simulation, not a real NAS outage or reboot. Original baseline
services stayed available. No DHCP/PXE acceptance claimed.

All511 nonempty app selections pass render assertions for app scope, bootstrap
publication protection, ports, create_host_path=false binds, reference bridge,
restart policy and conditional Tautulli/Plex log binding. This is not physical
acceptance of511 combinations. Full suite163 tests:162 passed/1 skipped as htpc
and root; logs /var/tmp/installarr-autonomous-suite-{htpc,root}.log.

## Explicit supervisor runtime refresh and interrupted-update recovery (2026-10-29)

New `audit-runtime --name NAME` reads immutable content hashes without rewriting.
New `refresh-runtime --name NAME --state-directory STATE` requires both reference
units inactive/failed and a completed original apply checkpoint. It verifies
existing owned definitions, unit evidence, checkpoint fingerprints and rendered
bundle compatibility; snapshots current Python/data, backs up original bytes
privately, journals updates before replacement, updates definition/health and
both service/supervisor/apply fingerprints. Units remain stopped; image, app data,
credential, configuration, Compose and enabled state are unchanged. Unknown edits
are preserved. Reboot and image upgrades are separate operations.

Physical disposable netboot fixture: /var/tmp/installarr-runtime-refresh-i7vx_qw6/result.json,
unit installarr-runtime-refresh-f5a96082.service. Started from a genuine prior
immutable runtime, running-update refusal preserved definition bytes. SIGKILL
injection after three replacements left a durable journal; next command restored
all original bytes and evidence. A subsequent refresh to the current snapshot,
explicit live start and full apply rerun passed protected GUI/socket and911 asset
write/restart persistence. Both fixture units stopped; containers/network removed.
Retained three deployments were never refreshed/stopped. Unit regression checks
rollback validates every artifact before any restore, preserves an unexpected
operator edit, and accepts only stopped unit states. No full fresh-OS upgrade or
image/schema migration readiness claimed.

## Separate read-only secondary movie source (2026-10-29)

Optional storage.media_secondary is the explicit source of Movies-2 in the Movies
library. Primary/family locations stay under the common data bind; only Plex gets
the extra /media-secondary read-only bind, create_host_path=false/rprivate. Exact
mount/marker checks feed the pre-init guard and UID2000 supervision. Directory
preparation requires an existing source and existing marker, creates nothing there,
preserves metadata and only tests reads. Explicit write checks skip this read-only
source. Wizard accepts local/existing/NFS/SMB maps without inventing a source.

Physical unpublished/unclaimed Plex fixture /var/tmp/installarr-secondary-tahx541o/result.json,
unit installarr-secondary-7e1cdf2a.service (stopped; container/network removed).
Only new paths below the approved export were used: Installarr-Secondary-Primary-secondary-7e1cdf2a
and Installarr-Secondary-Source-secondary-7e1cdf2a. Original fixture bytes, ownership
and mtimes were unchanged after directory checks and supervision. Actual2000:2000
container read succeeded; write was refused by the read-only bind. Marker removal
stopped its container and restoration recovered it. No host ports or claimed
identity were used. Library-path mapping/schema tests pass; claimed-library/GUI
acceptance and production source values remain deferred, not inferred from this test.

## Supported Python runtimes and Ubuntu20.04 Docker gap (2026-10-29)

Full167-test suite (166 pass/1 expected skip) ran in official Ubuntu20.04
Python3.8.10 and Ubuntu24.04 Python3.12.3 userspace. Evidence:
/var/tmp/installarr-ubuntu-runtime-5aetmw0t/{20.04,24.04}.{log,json}.
Images: ubuntu@sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214
and ubuntu@sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c.
No host socket/NAS/credentials passed. These are runtime regressions, not full
fresh OS/systemd/boot acceptance. Host suite after input-discovery changes168,
167 passed/1 skipped; previous root suite167 also passed.

Audit found Docker repository_text refused Focal despite the Ubuntu20.04 product
policy. Current upstream docs exclude20.04, but official signed Focal packages
remain. A separate official20.04 container installed using the pinned GPG primary
fingerprint and Signed-By APT repository, signature bypasses disabled, all service
starts denied/masked. Package install and binary execution passed:
Engine/CLI5:28.1.1-1~ubuntu.20.04~focal; Compose2.35.1-1~ubuntu.20.04~focal;
Buildx0.23.0-1~ubuntu.20.04~focal; containerd.io1.7.27-1.
Evidence /var/tmp/installarr-focal-docker-dipa_fld/result.json and install.log.
The adapter now allows only the tested amd64 Focal archived set and refuses an
unexpected archive selection; other architectures remain unvalidated. It also
checks existing source signature-bypass policy before Docker staging. No host
Docker packages/services/repositories changed. This compatibility path is explicitly
not ongoing upstream Focal support or daemon/systemd acceptance.
Primary sources: https://docs.docker.com/engine/install/ubuntu/ and
https://download.docker.com/linux/ubuntu/dists/focal/pool/stable/amd64/.

## Native generated Radarr download/import pipeline (2026-10-29)

/var/tmp/installarr-arr-import-4gd29mnj/result.json, project installarr-arr-import-2b3a21fb,
NAS Installarr-Arr-Import-2b3a21fb. Minimal unpublished Radarr/SAB pair, normal pinned
profiles/shared authentication/roots/categories/client connection. Generated black
1080p video with silent English audio,90min sparse-in-time,454630 bytes, SHA256
400e8236c1350a901bf7eac38219279491fd8622bd525083e21f61147745e208.
No supplied movie/episode copied or bound; no real indexer or credentials used.
A fixture-only HTTP NZB endpoint and loopback NNTP/yEnc process inside SAB served
only this generated video; no host ports/extra deployment backends. Native
release/push accepted the title, SAB fetched/decode-completed it, normal completed-
download handling imported to the movie root with exact bytes and2000:2000 ownership.
Native history has grabbed and downloadFolderImported; movieFileId1 persisted
through restart. Advertised4GiB release size was synthetic metadata, explicitly
not actual transferred bytes or a real indexer response. Real Newshosting/NZBGeek
acceptance remains separate evidence. No custom importer/import-mode manager added.

Initial harness readiness command returned nonzero before the fixture process
was ready and aborted safely; cleanup removed only owned containers/network.
Corrected bounded readiness polling plus the proper evidence key passed on rerun.
Primary API references used for experiment design, not version-proof:
https://github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Indexers/ReleasePushController.cs
and its official openapi.json; the pinned live response/download/import is the evidence.

## Native generated Sonarr download/import and menu (2026-10-29)

Sonarr counterpart /var/tmp/installarr-arr-import-g5o9de74/result.json, project
installarr-arr-import-27291daa, NAS Installarr-Arr-Import-27291daa. Same minimal
unpublished SAB pair and native release decision/completed-download handling;
11.22.63 S01E01 metadata with only generated black/silent video (not the supplied
episode),454751 bytes SHA25684c63c93e1e67fc200bd7c8af606845b1f4cb9f9e47a27b2bd4c355c055e2b1f,
2000:2000. Native grabbed/downloadFolderImported and episodeFileId1 persisted
through restart. Synthetic release size4GiB was metadata only. No real external
articles/indexers, no product import manager/mode changes. Containers/network removed.
Official Sonarr ReleasePushController source informed request shape; actual pinned
live result is version evidence, not the develop source alone.

Terminal menu command added without replacing unattended commands. It makes no
implicit deployment, refuses nonterminal use, blocks private/provisioning actions
without root and runs plan before selected apply; failed plan cannot reach apply.
Credentials reuse existing hidden-input/private-store commands. File selector never
overwrites a config. Unit tests cover no implicit execution/root and plan gates.
Real PTY navigation plan→exit passed, unchanged config/no host mutations:
/var/tmp/installarr-menu-terminal-4in37ccl/result.json. First PTY harness import
lacked checkout sys.path and failed before starting the menu; corrected harness passed.
Current171-test htpc suite passed170/1 skip; Python3.8 grammar passed all implementation,
test and fixture Python files. Human wizard/GUI usability remains queued, not claimed.

## Dependency-less optional combinations and atomic publication (2026-10-29)

Minimal standalone Tautulli/Ombi pair reference apply/rerun passed without Plex,
Radarr or Sonarr, exact selected app inventory and protected HTTP authentication:
/var/tmp/installarr-optional-pair-48lode31/result.json, unit optional-f238598b.
No native Plex/request backend was fabricated; plan explicitly lists missing
external integrations. Bazarr/Jackett standalone pair likewise passed with English
future defaults, no Arr app automatically added, explicit provider/indexer gaps:
/var/tmp/installarr-optional-pair-7xqbh_pc/result.json, unit optional-ed9f8939.
Both units stopped; owned containers/networks removed; retained services untouched.

Initial concurrent Bazarr/Jackett fixture failed safely during shared snapshot
creation: another deployment atomically created the identical target first.
A retry revealed link+unlink publication's transient two-link interval conflicted
with strict hardlink rejection. Final implementation uses Linux renameat2 with
RENAME_NOREPLACE for new runtime, bundle, GUI/provider/Plex secret and Tautulli seed
files. No destination entry is replaced. The winner remains a single-link file
even if killed immediately after publication; complete identical root-owned
runtime files can be securely reused by concurrent creators. Unexpected content,
mode, owner, symlink or hardlink still refuses. Root six-writer race, existing-entry
preservation (including dangling symlinks/directories), directory-FD publication,
NUL rejection and real SIGKILL/reuse regression tests passed. Directory fsync stays
at callers. No third-party Python dependency or unsafe fallback was introduced.
Primary syscall reference: https://man7.org/linux/man-pages/man2/rename.2.html.

Host suite172 tests passed170/2 expected skips as htpc,171/1 as root before the
three new atomic regression tests. Full175-test suites passed174/1 expected skip
in actual official Ubuntu20.04/Python3.8.10 and24.04/Python3.12.3 userspaces,
including the new libc operation and root concurrency test:
/var/tmp/installarr-ubuntu-runtime-b02psjy4/{20.04,24.04}.{log,json}.
These remain userspace tests; no systemd/engine/reboot readiness inferred.

Read-only public provider diagnostic /var/tmp/installarr-public-subtitle-diagnosis-f9exufw9/result.json:
pinned Yify uses HTTPS yifysubtitles.ch and native TLS handshake fails; TVSubtitles
uses HTTP www.tvsubtitles.net and returns404. No credentials/media binds/downloads,
TLS bypass, provider removal or bundled-code patch. More endpoint diagnosis is
recorded separately when finished; external availability does not block other work.

## Fresh claim timing, menu inputs and early failure ownership (2026-10-29)

apply --reference --prepare-only prepares identities/prerequisites/mounts/directories,
private GUI inputs, owned standard Docker and pinned images before a short-lived
Plex claim is needed. It does not read the claim file, create app units or start
app containers. Same config/name/state is then used for normal apply after claim.
Physical fresh claim-free preparation/rerun passed with unchanged container inventory:
/var/tmp/installarr-prepare-only-qmiv_7wb/result.json. No claim file was present.
The staged Plex-only timing fixture deliberately has no named libraries/family routes;
it is not full combined family acceptance. Menu order now places preparation before
claim, then apply. INSTALLER_RUNBOOK.md records the complete terminal/unattended flow.

Preparation on a ready disposable Tautulli/Ombi pair preserved container IDs,
StartedAt, supervisor PID and prior ready phase. Injected directory-preparation
failure in prepare-only mode also preserved running apps. The audit found early
normal-apply cleanup had not retained the old supervisor's unit name; it could
recreate stopped containers. Existing unit definition/hash/owner/mode evidence is
now validated before host prep, and verified names retained for failure cleanup.
The same injected error now stopped the old supervisor and containers persistently;
full same-config apply resumed to protected ready state. Evidence:
/var/tmp/installarr-prepare-preserves-q5v4_3_o/result.json (earlier success-only
probe /var/tmp/installarr-prepare-preserves-h0660m7k). Retained baseline untouched.

Real PTY hidden synthetic GUI collection created the private state parent and
kept password bytes out of the transcript, leaving configuration unfrozen until
apply: /var/tmp/installarr-menu-terminal-8c01egiq and latest1ppojb4w/result.json.
Initial menu path needed a state parent before nested secret collection; fixed.
The complete177-test suite passed175/2 skips as htpc,176/1 as root and176/1 in
actual20.04/Python3.8 and24.04/Python3.12 userspaces:
/var/tmp/installarr-ubuntu-runtime-gmt4ebic. Subsequent storage/secret tests are newer.

Current-at-build wheel validation /var/tmp/installarr-distribution-vydotohd passed
20.04/24.04 installation, entrypoint/preflight, prepare-only help,625 catalog hashes
and all recommended profiles/upstream license. Installed source hash both builds
28bc1dd83fdc68bb6cff98ade15f40dd807416485fdea0d44efab524adf37799.
Later storage/credential changes are newer than these wheels; rebuild before
presenting a current artifact. Build generators75.3.4 vs84.2.1 change only dist-info
metadata/WHEEL/RECORD, not installed package code/data. No release published.

## Read-only secondary host mounts and persistence policy (2026-10-29)

Mount planning/reconciliation now permits an existing RO mount when every purpose
on it is the read-only secondary source; new managed declarations use ro. A mount
shared with any writable purpose remains rw regardless of map iteration order.
Private-namespace bind/remount test /var/tmp/installarr-readonly-secondary-4t5eo1wi/result.json
passed UID2000 read, EROFS on write, existing-only directory/marker verification,
healthy bounded UID worker and unchanged fixture fstab. Live NAS/fstab and generated
source bytes/mtime/ownership remained unchanged. No app startup attempted inside
private namespace. Original source is only approved export; own fixture leaf
Installarr-Readonly-Secondary-388fad1d. Conflicting existing-vs-managed persistence
choices at one mountpoint now refuse before side effects, instead of last-write-wins.

Manual UHD preservation passed on the disposable generated movie:
/var/tmp/installarr-manual-uhd-a_c82gf_/result.json. Movie manually changed HD7→UHD8,
then restart and full app reconciliation retained8 while installer preferred HD7;
movieFileId1 and SHA256400e8236c1350a901bf7eac38219279491fd8622bd525083e21f61147745e208
were unchanged. No indexers/downloads; only this owned fixture's item was changed.

Public endpoint refinement /var/tmp/installarr-public-subtitle-diagnosis-zjyeuvld/result.json:
Yify HTTPS unexpected EOF/handshake failure, HTTP410; TVSubtitles native search404
while both HTTP/HTTPS homepage200. Homepage reachability is not successful search.
Selected providers/TLS/pinned code preserved. These are external availability limits.
Owned retained systemd unit syntax/dependency verification returned0; unrelated
snapd RestartMode warning preserved, no host setting changed. Evidence
/var/tmp/installarr-systemd-verify-result.json; not boot acceptance.

## Secure optional inputs and shared private credential directories (2026-10-29)

Provider init now accepts executor-owned0600 JSON via --credentials-file for
unattended use. Provider and Plex collectors honor optional --filename, so menus
use configured private paths rather than requiring implementation-specific names.
New init-smb-secrets collects hidden username/password/optional domain or imports
private JSON, writes root0600 mount.cifs format, validates with the actual mount
adapter parser and retains existing valid files. No SMB mount/server/install was
attempted. Line/control/Unicode separator injection, reserved/path filenames,
unsafe source modes, nonroot refusal, reuse and literal special characters tested.

The shared-folder audit found collector checkpoint names could collide even when
secret filenames differed. New collector metadata/locks are isolated by type and
filename under private .credential-state; actual secret paths do not move. Valid
legacy stores are reused without rewriting values or metadata. All four collectors
coexist in one private folder; original legacy-store bytes/modes/mtimes/entries
remain unchanged. Real authorized GUI/provider-store reuse proof (no recollection,
no values/hashes recorded): /var/tmp/installarr-legacy-secret-reuse-ebqeaclo/result.json.
A directory-creation race is now checked with lstat plus post-create resolution
before opening a lock; synthetic symlink redirection was refused without touching
the unrelated target. Full host suite189 tests is recorded in the latest namespace
logs; detailed exact totals below if further work changes them.

## 2026-10-29 — fresh userspaces, native Compose, bounded storage operations

Fresh-rootfs adapter acceptance passed on official Ubuntu20.04 and24.04 userspaces:
`/var/tmp/installarr-fresh-userspace-37klco9z/{20.04,24.04}/result.json`, acceptance.json,
staging-acceptance.json and provision.log. Actual account creation/rerun, prerequisite
installation, signed Docker package staging/rerun, service-UID local directory
write/fsync/readback and all-nine-app unpublished rendering passed. No host Docker
socket, accounts, NAS, system paths or credentials were mounted. Host passwd/group
remained unchanged. First fixture failed because its checkpoint parent was overlay;
the corrected fixture uses a verified local bind, retaining the filesystem policy.
This is userspace acceptance, not clean-systemd/engine/boot acceptance (I-04).

Official signed native Compose clients Focal2.35.1 and Noble5.6.1 each parsed1022
cases (all511 nonempty optional subsets, bootstrap and published). Evidence:
`/var/tmp/installarr-native-compose-p7w2c81e/{focal,noble}/result.json`.
Primary-key fingerprint, InRelease signature, package-index and .deb hashes were
verified before execution. No engine access during parsing. A separate real engine
29.9.2 probe showed both clients refuse an absent bind source without creating it:
`/var/tmp/installarr-compose-bind-6rm3pzc3/result.json`. No app data or ports.
The initial harness wrongly expected single-dollar serialization; corrected to
Compose's reusable escaped-dollar output, without changing product behavior.

CLI storage opens/inspection now run in a tracked, deadline-bound worker, passing
held directory descriptors back over a transient Unix socket. Directory preparation,
read/write probes and mount commands use durable PID/group records before filesystem
activity. Timeouts kill only the directly owned group and use bounded cleanup;
subsequent calls refuse new workers while a previous group remains, including a
separate CLI invocation. Recovered groups are never signalled automatically.
Synthetic stopped-worker tests exercise timeout/refusal/recovery without a NAS outage.
No daemon, listener or external backend was introduced. Existing supervisor health
workers retain their own bounded no-new-probe policy.

Host suite198 tests: htpc193 passed/5 skipped, root196 passed/2 skipped, logs
`/var/tmp/installarr-bounded-storage-{htpc,root}.log`. Python3.8 grammar153 files
passed. Physical read-only secondary rerun passed after worker integration:
`/var/tmp/installarr-readonly-secondary-wy_fpaxu/result.json`. UID2000 read-only
write refused EROFS, directory read and health passed, private fixture fstab and
live mount/fstab unchanged, source bytes/metadata unchanged. Real outage/reboot
remain untested and queued; a killed worker may leave its own probe artifact for
review after recovery. Do not infer full outage readiness from synthetic tests.

Current retained-service snapshot:
`/var/tmp/installarr-interactive-state-il2ubn83/checkpoint.json` — exactly3 active,
boot-disabled units and5 containers. No baseline app runtime/image/config changes.
No claims, provider credentials or family passwords were requested. No reboot,
commit or push. A nonroot distribution attempt failed Docker socket permission
before creating a container; rerun uses the existing authorized sudo access.


### Current distribution verification

/var/tmp/installarr-distribution-ngfrf9l0/{20.04,24.04}/result.json and acceptance.json:
both installed wheels passed198 tests (196passed/2appropriate skips), entrypoint,
prepare-only/provider/SMB help, package source-digest equality, all625 pinned catalog
documents and atomic runtime. The code snapshot includes bounded storage/mount work;
a later test-only extension additionally proves separate-CLI unreaped-worker refusal
in the current host suite. Wheels remain local evidence, not a published release.
20.04 wheel SHA25641472f5c10f59d877df881410864f106b32f03e28f55fefd7a9d69360e354f86,
604787bytes.24.04 SHA256e523f9b2a3dc2be7fe4b989b6cfb3047b7ba5af322310e86da26ad6edae48f08,
604785bytes. Different archive hashes reflect separate builds; installed code digests
were verified equal to the same source snapshot. No clean-engine/boot claim.

Physical NAS directory creation/write/rerun after bounded worker integration passed:
/var/tmp/installarr-directories-x3o28aoj, log /var/tmp/installarr-bounded-directories.log.
New owned NAS fixture Installarr-Directory-Test-20261028-11782add retained. Wrong
source caused no writes, markers unchanged on rerun, ownership conflict preserved
and recovered. Original supplied media untouched.


### Final autonomous verification checkpoint — 2026-10-29 05:05 UTC

Fresh current-code Bazarr/Jackett physical reference apply and rerun passed:
/var/tmp/installarr-optional-pair-o_e2ha8r/result.json. Both authenticated published
GUIs passed, no unselected backend was added, missing integrations/providers stayed
explicit. Disposable unit installarr-optional-6f29c20b.service stopped and containers/
owned network removed. This also exercises current bounded storage code through
full reference apply. No fixture command remains running.

Latest exact retained baseline snapshot:
/var/tmp/installarr-interactive-state-xfi7v389/checkpoint.json:3active/boot-disabled
units,5containers. It supersedes earlier snapshot pointers for recreation. Baseline
config, profiles, library grouping and credentials preserved. No reboot/commit/push.
Independent work reviewed/completed is recorded in AUTONOMOUS_WORK_PLAN.md and
IMPLEMENTATION_CHECKLIST.md; remaining interaction/permission/configuration gates
are I-01 through I-08 in INTERACTIVE_TEST_QUEUE.md. External public-provider failures
are separate conditions, not requests for user action. Installer readiness still
requires the explicitly deferred acceptance tests; no release-ready claim.


## Operator interactive acceptance resumed

Operator confirmed Plex integration/final five-library status. Radarr profile GUI
check pending credential retrieval locally (shared username admin, private existing
GUI store; no secret displayed by agent or changed). Only OpenSubtitles.com remains
supported/offered in Bazarr installer provider selections; removed Yify,
Supersubtitles and TVSubtitles. Historical immutable experiment configs/evidence are
not silently rewritten. Host suites199 tests passed: htpc194/5skips, root197/2skips.
Normal installer does not invoke tools/ experiment scripts or create their dated/
UUID NAS fixture directories; configured real directories and health markers remain.

Operator's unmount approach tested successfully using a separate owned bind of the
same approved NAS export, not the retained deployment mount:
/var/tmp/installarr-mount-detach-5mbfhq_2/result.json.
Ordinary unmount (no force/lazy) caused owned SAB container stop/waiting_storage,
underlying local directory stayed empty, remount recovered container. Disposable
service/containers/network stopped/removed; original3services remain active.
This is actual mount disappearance, not an unresponsive-but-present hard NFS mount.
The latter does not require shutting down the actual NAS; a separately scoped fault
experiment could be planned if desired. No reboot or shared NAS disruption occurred.
Actual approved mount here is /media/installarr; /media/NAS/installarr is absent.


Operator confirmed Radarr GUI has separate1080p/2160p profiles. Plex final library/
integration GUI status already confirmed. Next I-08 test is nonroot terminal wizard,
plan and exit using a fresh local config path; no apply or NAS writes requested.
Prepared local menu review directory: /var/tmp/installarr-operator-menu-2vdewuof (owned by htpc).
Command: python3 -m installarr menu --config /var/tmp/installarr-operator-menu-2vdewuof/config.json --name operator-menu
Actions1(createconfig),2(plan),0(exit); existing services untouched.


## Latest operator scope and family settings correction

Fresh installation of the reference stack is the goal. Do not add disaster recovery,
arbitrary reconfiguration or ordinary application user-action tests as release gates.
Acceptance focuses on shared administrator credentials, app-to-app API links, storage,
full pinned TRaSH profiles, genuine family identities/roles/root/profile preferences,
and family Discord IDs stored in Ombi notification preferences. Keep actual startup
and mount protection requirements; ordinary request/playback exercises already passed
and do not need repeated user involvement.

Old technical menu confirmed by operator, but wording/long flags rejected for normal
users. New no-argument `installarr` / checkout `./installarr.sh` opens plain guided
setup, automatic technical paths/identity, private accounts, host preparation before
Plex claim and saved-setup resume. Old explicit commands remain advanced. Unit tests
cover save-only/no host work, cancel, elevation, storage detection and stage ordering;
real PTY no-argument launch/cancel passed. Full real guided fresh installation remains
pending, not claimed by navigation tests.

Family Discord context and exact POST method are now documented in
OMBI_FAMILY_PREFERENCES.md. Live Ombi lenora8/rebel739/beanie08 all have empty Discord
targets and disabled notifications; relevant private stores had no reusable IDs.
Hidden local collection requested via `sudo ./installarr.sh family-accounts`.
No IDs requested in chat. New private store is /var/lib/installarr-setup/family/family.json;
fresh config carries only its path. Per-user POST stores target while disabled,
readback verifies it, omitted IDs preserve existing targets. Synthetic tests pass;
actual target POST/readback waits for locally supplied numbers.


## Fresh Ubuntu launch and private family targets

Operator's deployment contract: fresh Ubuntu with OpenSSH only; paste a few lines
to install Git, clone the repository and run ./installarr.sh with no flags. Guide
must install dependencies, mount storage and configure selected containers via APIs.
Current launcher bootstraps python3/ca-certificates/tzdata using Ubuntu APT when
missing, then opens guided setup. Official Ubuntu20.04 and24.04 minimal containers
with no Python initially both passed launcher/help/import and no-terminal safe-exit:
/var/tmp/installarr-bootstrap-9wwqkz11/{20.04,24.04}/result.json. No host socket,
NAS or credentials exposed. Full engine/systemd combined deployment remains pending.
Changes are local; no Git commit/push/publication has been performed.

Private family targets supplied: rebel739 and beanie08 saved and POSTed into their
native Ombi notification preferences, exact GET/repeat checks and real Ombi restart
persistence passed. Notifications disabled. Operator explicitly leaves lenora8 blank.
No numbers in logs, docs or ordinary configuration. Reusable private file:
/var/lib/installarr-setup/family/family.json. See OMBI_FAMILY_PREFERENCES.md.

Reference wizard defaults now offer all9optional reference apps, current Newshosting/
NZBGeek/OpenSubtitles.com choices, family rules and /media/Media; every app remains
optional. Internal paths/UIDs handled automatically. On fresh unmounted hosts the
wizard does not assume a NAS is already connected.

Operator reconfirmed production paths /media/Media (TV/family movies/downloads) and
/media/NAS/Movies (other movies). NFS server:/export and actual mount targets are not
yet supplied; read-only findmnt outputs requested from operator. Never substitute
the isolated test export or invent production sources. The supplied reference also
binds the secondary movie folder in Radarr/Bazarr; current read-only Plex-secondary
prototype still needs that reference writable/root integration reviewed before
claiming full production map equivalence. Netboot assets source is not established.
Retained baseline services available; current unit code/image/config snapshots stay
unchanged except explicit target-only Ombi preferences. No reboot or production access.


## Combined fresh-stack acceptance in progress

Operator provided exact production NFS defaults:
192.168.1.103:/share/MD0_DATA/Public -> /media/Media;
192.168.1.102:/share/MD0_DATA/Public -> /media/NAS, movies /media/NAS/Movies.
Wizard offers editable values; no production exports were accessed here. Reference
secondary path is now writable to Radarr/Bazarr, read-only to Plex, guarded by exact
mount/marker assertions. Native Radarr extra root and both2000-based app writes,
API rerun IDs passed /var/tmp/installarr-secondary-writable-z9p8s75c/result.json.
Its generated NAS fixture was removed after containers stopped. Earlier failed
attempts correctly refused a root outside /data; fixed by explicit exact-target
allowance only for a configured writable /media-secondary mapping, not arbitrary paths.

All9-app acceptance staged at /var/tmp/installarr-fresh-acceptance-vhydzwl1 using
only one owned test-export fixture Installarr-Fresh-Acceptance-aaabe264. No samples
copied/modified. Family private IDs are reused (Jeremy/Beanie; Lenora blank per operator).
Operator approved temporarily stopping the previous3test services to use their ports.
First attempt (freshcheck-aaabe264) found a real combined-render bug: shared mutable
volume objects caused Plex's read-only /data flag to affect SAB/Arr/Bazarr/Jackett.
Storage guards exited78, no applications wrote through an unintended writable mount.
Previous services automatically restored on failure. All first attempt units stopped,
containers removed. The bug is fixed using independent volume objects per service;
all511 subsets now assert writable data for other apps and readonly Plex.

Corrected retry reuses the same app databases/NAS fixture, but has new immutable
artifacts: config-v2.json, state-v2, project-v2, name freshcheck-aaabe264-v2.
Prepared manifest: /var/tmp/installarr-prepared-fresh-test-v2.json (root600).
No duplicate Plex identity runs concurrently. New Plex preferences have no account
token yet; initial claim expired during failed startup. New claim requested via
sudo ./tools/claim_fresh_test.py. After operator replies "claim saved", immediately
run sudo python3 tools/run_prepared_fresh_test.py; helper switches units, applies all9
and restores prior3on failure. Do not ask permission to switch again; approved already.
Do not start obsolete first-attempt units or silently rewrite their frozen bundles.


## Final combined reference acceptance and publication preparation

Current live unit is installarr-freshcheck-aaabe264-v2.service: all9containers active,
boot-disabled. Old3baseline services and obsolete bootstrap/first-attempt units are
stopped. Do not start old units alongside this stack (same ports). Exact current
config/state/result/live-checkpoint paths are in CURRENT_PROGRESS.md.

Combined apply and final rerun passed protected bootstrap, all9authenticated HTTP
endpoints, Arr/SAB/NZBGeek/Newshosting connections, Bazarr/OpenSubtitles.com/English
settings, full pinned profiles, Plex5libraries, Ombi genuine family identities/
roles/roots/profile preferences and supplied Discord targets, Tautulli identity,
netboot911permissions/auth. All9running inventory verified. Root runtime snapshot
integrity and checkout digests match. Latest full API evidence:
/var/tmp/installarr-fresh-acceptance-vhydzwl1/result.json and live-checkpoint.json.

Cold empty Plex database reproduced startup400refusal and slow agent discovery.
Fixed exact known nonmutating startup-refusal retries, bounded read-only discovery,
and a Plex-specific60sHTTP/65souterdeadline; other validation errors/auth failures
are not blindly retried. Empty DB created all5libraries with the fixed adapter:
/var/tmp/installarr-cold-plex-10o5gfid/result.json. Same claimed
identity was never run concurrently; source stack paused/restored around each
minimal cold diagnostic. No original media bound writable or copied.

Final host suites217tests: htpc212passed/5skips, root215passed/2skips.
Final installed-wheel suites on20.04/Python3.8 and24.04/Python3.12 each217tests,
215passed/2skips, at /var/tmp/installarr-distribution-ukeybv4s. Wheels respectively
SHA2567fc8adfc8f092998a305cee7f21382f48e21c666924e9f725a88c67702d37a66
(612831bytes),93072d9d38d7e19182560cfda90228e8004fe8160b990e2a2e2bbf68a4590e13
(612828bytes). Python3.8grammar165files and diff whitespace passed. Actual private
GUI/provider passwords/APIkeys, current Plex token and Discord targets were checked
against810reviewable Git files: no matches. reference_compose.yaml remains ignored.

Operator authorized publishing this implementation to their Installarr repo. GitHub
connector is already authenticated as boosted3svt with admin/push permission on
boosted3svt/Installarr (public); no new token/login required. Main local/remote both
6158c38c07655aea6bc8a817acea81c2c3865268 before publishing. No remote mutation yet
at this checkpoint. Publish only reviewed source/tests/docs/pinned profile data;
never private stores, reference Compose, claim files or personal Discord IDs.

Final credential portability decision: operator explicitly rejected carrying files
between installs. Do not implement encrypted saved-setup bundles, app-state restore
or credential exports. Each clean install prompts for needed credentials and optional
Discord IDs; nonsecret NFS defaults/profiles/family roles ship in code. Existing local
private files remain for operation/resume on that same installed computer. Reference
Compose is translated into code and is not a runtime prerequisite. No encryption
bundle code/dependency was added. Remaining real acceptance is clean Ubuntu/systemd
and boot behavior, not more ordinary app user-action tests. No reboot performed.


## Publication completed

Operator explicitly authorized publishing to their Installarr repository. Existing
GitHub connector authenticated as boosted3svt with admin/push permission; no new
login, token collection or machine Git credential setup was needed. Main advanced
by lease-checked fast-forward from6158c38c07655aea6bc8a817acea81c2c3865268 to
bc9017a4eec41b8bd514901b0067accbdfffdd2c. GitHub tree SHA exactly matched the reviewed
local staged tree91bbd85a61200ee24095d2c0f4a6cb2d13ecb074.809changed entries uploaded,
including full pinned625document catalog/license, source/tests/docs and executable
single-script launcher. Actual current private values were checked against the
staged payload: no GUI/provider secrets, Plex token or Discord IDs present. Supplied
reference_compose.yaml remains ignored/unpublished. Vendored whitespace is preserved
verbatim for its pinned checksums; ordinary code whitespace check passes.

A new unauthenticated public clone into /var/tmp/installarr-public-clone-dd6cdxrk
confirmed exact commit, executable launcher/help, no-argument nonterminal safe exit,
imports from the new clone and217tests passed (212passed/5appropriate skips).
Result: /var/tmp/installarr-public-clone-dd6cdxrk/result.json, tests.log. This is
fresh-clone validation, not a claim of full clean-Ubuntu/systemd or reboot acceptance.
Those remain the two actual operator acceptance tasks. No extra application-user
functionality tests, credential transfers or encrypted bundles are required.

Current all9-container freshcheck-aaabe264-v2 deployment remains active/boot-disabled;
previous3services and bootstrap are stopped. No reboot performed. Current source,
private paths, replica boundaries and rollback are in CURRENT_PROGRESS.md. Follow-up
publication metadata updates only documentation; installed code/tests remain the
same validated217-test version. Each clean install prompts for credentials/optional
Discord IDs. Future agents must not invent a file-import requirement.


## Latest operator correction: direct Codex after a wipe

The operator requests NO tmux involvement. Run Codex directly in the SSH terminal;
do not install tmux, create sessions, wrap commands or add a multiplexer dependency.
Authoritative commands and seed prompt: docs/FRESH_HOST_CODEX_HANDOFF.md. That guide
also records the explicitly requested dangerous Codex flag and validated optional
NOPASSWD sudo rule for the Ubuntu operator; these are test-operator opt-ins, not
requirements of Installarr or permission to touch production. Documentation only:
no new sudo policy has been installed on the current machine.

After wiping, old local Codex history/authentication, /var/tmp and /var/lib fixture
paths, containers, mounts and application DBs must be treated as gone. Start a new
Codex chat that reads the published checkpoints. Resume --last is only for a saved
session on the surviving new installation, not restoration of erased history.
Credentials and optional Discord IDs are collected through normal prompts again;
no file transfer/export/restore bundle. Do not preinstall Docker/NFS manually before
exercising the installer. Use only the approved isolated NAS export for testing;
production NFS defaults are not authorization to access production. Ask before reboot.

Current known acceptance: nine-app combined configuration, cold Plex initialization,
217-test host/installed-wheel/public-clone checks. Remaining: actual clean-host/systemd
and boot acceptance. Source/API logic unchanged by this documentation correction.
