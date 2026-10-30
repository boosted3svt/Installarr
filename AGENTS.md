# Installarr development handoff

Read README.md and docs/PHYSICAL_TEST_HOST.md before host experiments.
The user authorized continued implementation toward a fully usable headless
installer, including local tests on a dedicated physical Ubuntu machine.
Work in the existing checkout; no worktree is needed.

## Product requirements

- Fresh Ubuntu provisioning first; application-state migration/disaster recovery
  is a stretch goal. Provisioning accepts Ubuntu 20.04 or newer, including
  Ubuntu 22.04 and 24.04. Retain Python 3.8 compatibility for Ubuntu 20.04.
- CLI only, including menus, hidden credential input, unattended configuration
  and resumable execution. Browser-based Plex/Codex authorization can happen on
  another device. Do not store secrets in the nonsecret JSON configuration.
- Every app is optional: SABnzbd, Sonarr, Radarr, Bazarr, Jackett, Plex, Ombi,
  Tautulli, netbootxyz. Discover dependencies; do not pretend Jackett downloads torrents.
- Use current official image guidance and tested image versions. Standardize
  non-root application identities instead of copying production PUID/PGID 0:0.
  Image entrypoints may legitimately initialize as root then drop privileges.
- When netbootxyz is selected, host user/group nbxyz must use UID 911/GID 1001.
  Verify image runtime permissions. DHCP and PXE client reachability are out of scope.
- Plex ALLOWED_NETWORKS is desired behavior, default preset 192.168.0.0/23.
  Default timezone America/Chicago. Host IP/hostname are detected/editable.
- One storage map must populate Compose and every relevant application root,
  category, library and integration. Preserve existing host files and path case.
  Prefer local application databases. Do not recursively chown NAS libraries.
- Install nfs-common BEFORE any NFS mount attempt; cifs-utils for SMB. Use signed
  repositories. Preserve existing mounts/fstab; back up approved persistence edits.
- Mount health includes expected source/type and reachable files, plus separate
  service-UID write checks. An unhealthy Docker status does not stop containers.
  Prevent writes beneath absent mounts through reboot AND Docker auto-restarts.
- Prompt once for a shared GUI administrator username/password for supported apps.
  Do not confuse API keys with passwords. Plex uses its own authorization; Jackett
  username support must be verified. Do not expose bootstrap services unprotected.
- Ombi family users use individual Plex accounts, not local lookalikes. Optional
  family presets: lenora8 -> Lenora movie/TV roots and 1080-or-lower profiles;
  rebel739 -> Jeremy roots and 1080-or-lower profiles; beanie08 intentionally
  inherits global roots/profiles. AutoApproveMovie/AutoApproveTv for all three;
  Beanie also PowerUser. Resolve tags/profile/root/user IDs dynamically. Discord
  preferences remain disabled; collect optional IDs securely when needed.
- Pin full versioned TRaSH profiles, not just representative custom formats.
  API research from the earlier handoff is version-specific, not proof of working
  auth, Plex selective import, request dispatch, downloads or per-user routing.
  Validate schemas, read back writes and test restart persistence/reruns.

## Current implementation and next work

preflight/configure/plan/check-storage exist. A limited isolated `apply` now
orchestrates tested Sonarr/Radarr/SABnzbd selections on already-mounted storage.
It returns isolated_configured, not general installation readiness; authenticated host GUI
listeners now pass real host HTTP checks; outbound container networking remains
isolated and general installation readiness is not yet established.
Storage choice collection supports local/existing/NFS/SMB, with deduplicated plans
and read-only mount/sentinel checks. Config files are private and never overwritten.
`prepare-accounts` now provides a narrow Ubuntu-20.04-or-newer/root-gated account adapter
with locked private checkpoints and host reconciliation on reruns. Physical creation,
interrupted group creation recovery and completed reruns passed on Ubuntu 22.04;
see docs/TEST_RESULTS.md. Retained isolated identities: installarr-test 2000:2000
and nbxyz 911:1001; checkpoints: /var/lib/installarr-physical-test-accounts.
`init-secrets` stores shared GUI credentials privately, separately from config/state.
`check-storage-writes` provides opt-in mount-asserted service-UID write probes.
Physical NAS write/fsync/readback/cleanup passed for both identities after dropping
root and clearing supplementary groups. Wrong-source, simulated missing-mount and
root-only directory refusals passed. This is not boot/Docker mount-loss protection.
Run `python3 -m unittest discover -s tests -v` before committing changes.

`prepare-docker` now stages exact signed official packages with standard Docker/
containerd services masked. `prepare-test-daemon` runs a separate daemon without
bridge/firewall/forwarding changes; its unit is not enabled at boot. Current test
socket: unix:///run/installarr-docker-test/docker.sock. Do not unmask/start default
Docker services or create Docker bridge networks within the current test scope.
The container-side startup gate in installarr/startup.py passed a real isolated
daemon restart with an absent temporary bind; no local fallback writes occurred.
It is now integrated into isolated Sonarr/Radarr Compose bundles and their real
/init entrypoints. Managed ongoing supervision now passed marker-loss/recovery and supervisor-crash
tests; actual reboot and real NAS outage remain untested.

`render-compose` generates private, non-overwriting JSON Compose bundles from the
same storage map used by app adapters. Sonarr/Radarr/SABnzbd are implemented;
other selections fail explicitly. Bundles publish no ports. SAB owns a networkless
namespace; selected Sonarr/Radarr join it for loopback integration. Without SAB,
each app uses network_mode none. Bundles use
restart no, digest pins and long binds with create_host_path false/rprivate.
Physical pair tests passed on Sonarr 4.0.20.3014-ls1 and Radarr 6.4.4.10685-ls324:
runtime/database UID 2000:2000, local DBs, Forms GUI login/rejection, API/root
readback/reruns, restart persistence, wrong-FS refusal before /init and recovery.
API access still requires its separate key even with a valid GUI cookie. See the
latest docs/TEST_RESULTS.md section for failure evidence and exact image digests.

`install-service` installs disabled, root-snapshot systemd supervision for the
isolated daemon; `service-status` reads its private checkpoints. Matching bundle
containers stop on failed storage checks and recover on health restoration.
Supervisor SIGKILL fallback and preserving foreign containers passed. Retained
unit installarr-life-c2b4ff240f28.service is stopped/disabled and references removed
fixtures. Do not start that demo unit as a real deployment.
`prepare-prerequisites` reconciles required nfs-common/cifs-utils before mounts;
physical NFS installed-package reruns passed. `prepare-directories` now creates configured directories/health markers only on
verified existing storage, preserves existing metadata, probes service-UID writes,
and uses private local resume state. Wrong-source refusal before writes, unchanged
marker reruns, ownership-conflict refusal/recovery and the real CLI passed.
Visible retained NAS fixture: Installarr-Directory-Test-20261028-c0112b37; local
config/checkpoints: /var/tmp/installarr-directories-mjhtnqph. Do not confuse these
new empty test paths with the supplied original Movies/TV examples.
No fstab/mount adapter exists yet.
SABnzbd 5.1.3-ls278 passed real GUI authentication/rejection, storage category
readback/reruns, a generated NNTP download with exact NAS bytes/ownership, and
restart persistence. Initialize categories with get_cats before category writes:
get_config on a pristine missing section does not initialize SAB's lazy defaults.

`installarr.downloadclients.ensure_sabnzbd` now passed physical Sonarr/SAB and
Radarr/SAB connection tests: dynamic schema/ID, wrong-key rejection before save,
reruns without duplicates and recreation persistence. Generated bundles and supervision now support the tested shared SAB
loopback topology, with matching-owner and actual live namespace checks. Dispatch/import are not validated by connection tests.

Existing supplied movie/TV files now passed real Radarr/Sonarr recognition and
restart persistence using direct read-only binds. Do not copy, rename or delete
these supplied examples. Operator clarified that manual versus automatic import
mode management is beyond installer scope; do not build an import manager or make
separate mode tests readiness gates. Fixture-only metadata relay uses container
loopback plus a private Unix socket and two official TLS hosts; no host listener
or network configuration changes. It is not a deployment setting.

`apply --config ... --name ...` now reconciles accounts/prerequisites/directories,
Docker staging/test daemon, pinned images, Compose, supervised startup and real
app authentication/root/category/SAB connection checks. Credentials stay in a
private separate store. Failure stops only its own containers; CLI resume/reruns
passed with stable app/container IDs. Existing unit/config conflicts are preserved.
Units remain disabled by default. User emphasized that GUIs must be accessible:
supervisor-managed host GUI listeners now expose authenticated apps at the
configured address. Physical tests used localhost; normal outbound connectivity
is still missing and this is not yet a usable general deployment.

Current continuous execution plan is docs/IMPLEMENTATION_CHECKLIST.md.
Next: finish mount/persistence reconciliation and outbound connectivity;
expand tested app adapters and the apply path. Real provider access, reboot, full pinned
TRaSH profiles and Plex/Ombi family behavior remain unvalidated. Use minimal disposable service pairs
for experiments, not a second complete stack. Record exact tested versions, commands,
results, failures and unresolved gates in docs/TEST_RESULTS.md without secrets.
Never mark install readiness based only on inventory, open ports or config acceptance.

## Test boundaries

Physical test host is isolated on a VLAN; it can reach the NAS and Internet only.
One isolated test NFS mount is intended for TV/movies. Confirm its actual source
and target before writing. The proposed test source was
192.168.1.102:/share/MD0_DATA/Public/installarr at /media/installarr; do not assume
it mounted successfully. Keep all NAS writes inside that confirmed test subtree.
Never inspect or modify production apps, sibling NAS folders, shares or host settings
outside the test scope. Do not repartition/format disks or change SSH/firewall/VLAN.
Preserve operator changes; propose reboot timing explicitly so SSH can reconnect.
Sudo access and Codex permissions are runtime prerequisites, not provided by this file.


## Latest operator scope correction (2026-10-28)

Reproduce the reference server. Approved changes standardize usernames/passwords,
quality profiles in download apps, and directory structure shared between apps.
Do not invent or add networking designs, auxiliary services or extra backends
without permission. SMB/Samba is optional and unnecessary for the current NFS
reference setup; its physical fixture is deferred. No Samba was installed/started.
The nsenter GUI relay is isolated test infrastructure, not an approved reference
networking replacement. Locate the actual reference Compose/app export before
making architecture/image/path/profile assumptions; the supplied reference is now at
/home/htpc/Installarr/reference_compose.yaml (service fragment; keep out of Git).
See docs/REFERENCE_BASELINE.md for the credential-redacted baseline. Network web
definition and profile selections are absent; network type was requested. Do not inspect production to get it.
Keep working on independently justified reference requirements while awaiting details.


## Approved reference networking (2026-10-28)

Operator confirmed web is a standard bridge and explicitly approved changes to
NAT/firewall/etc required by Docker. docs/REFERENCE_NETWORK_PLAN.md is approved:
stop the empty isolated daemon, start standard Docker/containerd, create the owned
reference bridge, then validate reference app ports after authentication. Preserve
existing host IP/DNS/manual routes, SSH, VLANs, disks and unrelated firewall rules.
Docker-created bridge/forwarding/NAT changes are now authorized. No reboot approval
has been given. This supersedes the earlier blanket no-Docker-network-change rule
only for this reference deployment/testing scope.

## Current reference proof of concept (supersedes historical isolated status)

Standard Docker/containerd are active and boot-disabled; old isolated daemon stopped.
Operator-approved web bridge DNS and outbound HTTPS passed. Do not run the old
masking/staging adapter against the standard active engine. `apply --reference`
now provides protected unpublished bootstrap, shared data_root, standard bridge
ports, real GUI authentication and SAB connection readback. Current live Radarr/SAB
pair is installarr-poc-http-d29db77d.service at 10.70.0.99 ports 7878/8090; leave this
successful proof of concept available. Private config/state is under
/var/tmp/installarr-reference-poc-fz5b_65a; never print its credential files.
See docs/CURRENT_PROGRESS.md for current commands and remaining work.
Fresh NFS mount/fstab reconciliation and common-data hardlink tests now passed;
older text saying these are unimplemented is historical. Reboot remains unapproved.

Operator update: HTTP GUI ports only. Ignore optional HTTPS port mappings and
HTTPS application settings; outbound HTTPS to official APIs/registries remains needed.

Bazarr1.6.2-ls370 now passed minimal physical Radarr and Sonarr pairs: shared
GUI auth/rejection, actual remote-version lookup, restart/rerun persistence and
local database ownership2000:2000. Shared-data wizard and accurate plan paths
are implemented. Earlier POC unit poc-d29db77d is stopped; HTTP-only replacement
poc-http-d29db77d preserves the same databases, NAS data and GUI credentials.

Latest implementation: reference apply now orchestrates signed package staging and
standard-engine activation when needed; existing owned active engine reruns do not
remask/restart it. Shared-data CLI wizard is implemented. Bazarr and Jackett pins,
GUI auth/rejection and published HTTP acceptance passed. Jackett is password-only;
indexer selection/credentials remain external inputs. Clean-OS combined acceptance,
Plex/Ombi/Tautulli/netboot, full profiles and approved reboot remain outstanding.

## Current checkpoint and final operator corrections (2026-10-28)

This section supersedes earlier app/profile/library status above. The authoritative
resume document is docs/CURRENT_PROGRESS.md; keep it and the checklist current.
Do not stop at milestones. Operator explicitly reiterated continuous work until
needed input, actual GUI testing, permission or an explicit pause.

Live units: installarr-poc-http-d29db77d.service (Radarr7878/SAB8090) and
installarr-plex-standard-test.service (Plex32400/Tautulli8181), active/boot-disabled.
Plex name Installarr Test; operator confirmed movie and single-episode playback.
Current Plex config/state: /var/tmp/installarr-plex-standard-2bbujwqu/config.json
and state. Original claimed Plex DBs stay under
/var/tmp/installarr-plex-authorize-uo198y7v/configs. Never print claim/Preferences.xml.
Older plex-auth-test, plex-libraries-test and plex-grouped-test units are stopped;
never start them concurrently or rerun their superseded configs.

Final library policy: one Movies library with Movies, Movies-2, jeremymovies,
lenoramovies; one TV library with TV, lenoratv, jeremytv. Exclude both low-res
folders. Remaining libraries/folders match exactly: sports→sports,
StandUp→StandUp, Music→Music. The operator rejected differing names such as
sports→sport and StandUp→comedy. Remove Disney, Only Heather, YouTube Videos and
TubeSync Videos as libraries in all installer runs. Preserve their media/files.
The live test server now has5 libraries (IDs1,2,7,8,9), with stable Movies/TV IDs.
Movies-2 is only an empty test folder in the approved export; a separate production
secondary media-source adapter remains outstanding. Do not inspect production.

Full pinned TRaSH profiles now pass API schema/write/readback, coexistence,
restart/rerun and reference apply: Radarr Remux + WEB1080p preferred, separate
Remux + WEB2160p for manual changes; Sonarr WEB-1080p. Existing media profile
assignments are unchanged. Default preference is installer routing metadata.

Plex1.43.5.11079-b3b13e506 official baked/versioned image, private claim input,
read-only NAS startup guard, real account authorization, libraries and GUI playback
passed. Tautulli2.18.2-ls249 passed real Plex identity/version connection, read-only
logs and shared auth. PMS_IDENTIFIER is Plex's identity; PMS_UUID is Tautulli's
own identity and must be preserved. Stopped link updates retain private backups.

Ombi4.53.10-ls274 passed shared local Admin authentication/rejection, local SQLite
ownership2000:2000, published HTTP3579, host admin-presence gate and apply rerun.
Its Plex/family imports, Sonarr/Radarr links and requests remain unconfigured and
untested. Never create local lookalikes for family Plex accounts.

netbootxyz0.7.6-nbxyz27/menus3.0.3 passed UID911/GID1001 permissions/write test,
shared Basic auth for GUI and Socket.IO, restart and published/reference apply
rerun. Protection uses Nginx already included in the same reference image; no
additional service/backend. Node3001 is unpublished, frontend3000 maps to3250.
Its config/assets fixture is local; DHCP/PXE clients remain out of scope. Health
checks now use separate bounded workers for each service identity, retaining the
no-new-probe rule while any old worker is unreaped. Do not relax911 permissions
to make a2000-based health check pass.

Latest suite134 tests,133 passed/1 skipped as both htpc and root. Python3.8 grammar
check passed; clean20.04/24.04 runtime tests are not established. No reboot is
approved; no commit/push made. Continue Ombi integrations/family behavior,
secondary media sources, menus, fresh-host/failure/runtime-update audit and final
acceptance. Detailed commands/failures/evidence are in docs/TEST_RESULTS.md.

## Operator-requested savepoint (2026-10-28, latest)

Work is paused at the operator's requested stopping point. Files and markdown are
saved; no Git commit/push. Final five-library Plex/Tautulli apply rerun passed
with stable IDs and no removed libraries recreated. Both live pairs remain active,
boot-disabled. No fixture/implementation command remains running. Resume from
docs/CURRENT_PROGRESS.md when asked; next work is Ombi integrations.

## Resumed continuation (2026-10-28; supersedes pause above)

Operator resumed. The retained Radarr/SAB and Plex/Tautulli pairs were already
running when inspected; obsolete units stayed stopped. Ombi actual Arr connectors,
remote key rejection, settings restart/reruns, movie/TV request dispatch to preferred
1080p roots/profiles, and published Ombi/Radarr apply/rerun now passed. Radarr global
root is a path in Ombi; Sonarr global root is an ID. Plex remote five-library link
and restart/rerun passed. Availability sync failed because supplied Plex items are
unmatched local:// entries; an operator GUI Match/Fix Match question is pending.
Do not claim full availability or family routing. All disposable fixtures removed;
original live pairs remain. Continue from CURRENT_PROGRESS.md. No commit/push/reboot.

## Matched-media/family continuation (2026-10-28; latest)

Operator matched both sample items. Ombi availability sync now passed movie/show/
episode with restart persistence. Native import of exactly the three family Plex
accounts, passwordless provider identities, approvals, Beanie PowerUser and disabled
Discord preferences passed. Administrator on-behalf movie/TV requests passed correct
Lenora/Jeremy1080p paths and Beanie global inheritance, including restart. Actual
family Plex browser login/requests remain unvalidated. One rapid request sequence
hit upstream SQLite Error5; sequential reruns passed. Preserve that failure evidence.

Additional retained GUI-only unit installarr-ombi-family-2274744e.service is active/
boot-disabled at10.70.0.99:3579. Config/state /var/tmp/installarr-ombi-family-gui-o799mzbk.
It has the three native family users but no request backends; operator was asked to
try Plex sign-in as one family user in a private browser, without submitting requests.
Original two service pairs remain active. No disposable experiment process remains.

Opt-in family preset config/apply and private interrupted-import journal are implemented;
full combined family apply and physical kill recovery still need acceptance. Grouped
library editing and accurate nine-adapter integration/input plans now exist. Host
suites149 tests/148 passed/1 skipped; earlier148-test suite passed actual Python3.8.10
on official Ubuntu20.04 and Python3.12.3 on24.04 userspace containers. This is not
clean-OS/systemd acceptance. No reboot/commit/push. CURRENT_PROGRESS.md is authoritative.

## Operator authentication correction (latest)

Never ask the operator to sign in with someone else’s family credentials. They
explicitly rejected that request and authorized importing their own existing Plex
username boosted3svt as a fourth Plex identity in the Ombi sign-in fixture. Native
owner import now passed, without a local password; real provider ID, native Admin
role, original import-flag restoration and restart persistence verified. GUI remains
10.70.0.99:3579, unit ombi-family-2274744e. Next GUI question is boosted3svt’s own
Plex sign-in only; no requests in this backend-free GUI fixture.

## Operator-authenticated requests and recovery (latest)

Operator confirmed boosted3svt browser Plex sign-in. Native Plex-token requests now
passed attribution,1080p profile and dedicated Radarr root. The same real operator
identity also passed all three family-equivalent ordinary-user routing cases with
Admin disabled; original Ombi owner roles/profiles restored and verified afterward.
No Plex account permissions changed, no other people's credentials used. Earlier
family movie/TV on-behalf tests remain distinct evidence.

Ombi GUI is now connected to retained Radarr via its existing published LAN endpoint,
with dedicated global root /data/Ombi-Operator-Test/Movies; no Sonarr backend and
Radarr indexers remain zero. It is no longer sign-in-only, but actual downloads are
not established. Three retained units remain active/boot-disabled. Physical SIGKILL
import-journal recovery passed, selective native identities/stable restart verified,
disposable fixture removed. Host suites151 tests/150 passed/1 skip; earlier distro
container suites148 tests. Runtime snapshot integrity passed, but all retained
snapshots are older than checkout; automatic refresh remains open. No reboot/commit.

Next requested input: Usenet/indexer/subtitle provider names only; credentials must
be collected locally via hidden prompts/private stores, never chat. Continue other
independent work while awaiting answers. CURRENT_PROGRESS.md has current status.

## Provider selections and credential gate (latest)

Operator uses Newshosting with100 max connections and NZBGeek. Latest subtitle
correction: OpenSubtitles.com, Yify Subtitles, Supersubtitles and TVSubtitles; this
supersedes the earlier .org answer. All four modules exist in pinned Bazarr; provider
settings persisted in a disposable empty-library pair using unused synthetic creds.
No actual subtitle authentication/search/download is proven.

Provider private collector and reference wizard/apply adapters now exist. Defaults
Newshosting news.newshosting.com/TLS563/strict verify/100; direct NZBGeek Newznab
without new backends. `init-provider-secrets` prompts locally/hidden, writes private
providers.json; no values in nonsecret config/checkpoints. `check-providers` performs
non-saving native SAB/Arr tests, not real download proof. Operator has been asked to
run both from CURRENT_PROGRESS.md; provider credentials were absent at last check.
Never ask for them in chat. Full remote provider/apply/restart acceptance remains open.

## Saved pause after provider/English acceptance (latest; supersedes continuation)

Operator requested pause after the next step; English subtitle-default step is
complete and work is now paused. Resume only when asked. No commit/push/reboot.
All markdown/checkpoints saved, no implementation/fixture process running. Three
retained units remain active/boot-disabled; all disposable provider pairs removed.

Credentials already collected at /var/tmp/installarr-providers-secrets/providers.json
(plural providers). Do not print/recollect. Real Newshosting100 TLS/auth and NZBGeek
passed minimal Radarr/SAB and Sonarr/SAB full apply/reruns. Official100MB SAB test
downloaded114,967,316 bytes including repair files, owned2000:2000 on approved NAS.
Native OpenSubtitles.com auth/search3 results/download127,209 bytes, fsync/readback
and2000:2000 passed in generated fixture paths, without modifying supplied media.

Operator chose standard English subtitles, not forced/hearing-impaired, for new
movies/TV. bazarr_language_profile english-standard is implemented and physically
persisted across restart/rerun, preserving unrelated profiles/existing assignments.
Yify SSLError, TVSubtitles HTTPError and Supersubtitles0 English sample results are
limits, not successful provider acceptance. Do not weaken TLS/add solver backends
or silently remove providers. Scheduled Bazarr library-search acceptance remains.
Final host suites158 tests/157 passed/1 skip; Python3.8 grammar/whitespace passed.
Earlier supported-OS container suites148 tests; full fresh-OS/boot still pending.
CURRENT_PROGRESS.md and SAVED_CHECKPOINT.md are authoritative at resume.

## Autonomous absence instruction (latest; supersedes pause)

Operator is away about5h and requests continuous noninteractive implementation.
Do not ask questions during this period. Classify every remaining step and record
interactive tests with exact configs/containers/staged settings/restoration recipes
in docs/INTERACTIVE_TEST_QUEUE.md, then work another independent task. See
docs/AUTONOMOUS_WORK_PLAN.md. No reboot, production access or new backends granted.
Keep three retained units active/boot-disabled; do not recollect existing secrets.


## Autonomous continuation checkpoint — 2026-10-29

The operator's five-hour absence instruction remains active: keep working and
queue interactive gates, do not stop at them. See docs/AUTONOMOUS_WORK_PLAN.md,
docs/INTERACTIVE_TEST_QUEUE.md and rewritten docs/CURRENT_PROGRESS.md. Scheduled
Bazarr search, explicit local/NFS netboot assets, read-only separate Movies-2 source
protection, explicit stopped-runtime refresh/SIGKILL recovery, generated Radarr
and Sonarr release→SAB NNTP→normal import/restart, terminal menu and dependency-less
optional pairs passed. Production secondary values, claimed combined family apply,
clean host, actual outage/reboot and human GUI/menu are still deferred gates.
Atomic new-file publication now uses Linux renameat2/RENAME_NOREPLACE; never relax
existing owner/mode/symlink/hardlink checks. The complete175-test suite passes in
actual20.04/24.04 userspaces including libc/concurrency/crash tests. Focal official
signed archive compatibility is amd64/pinned and outside current upstream support;
no host package change was made. Retained three units remain active/boot-disabled,
on original runtime snapshots. Distribution acceptance and remaining audits continue.


## Latest autonomous audit checkpoint (2026-10-29 05:05 UTC)

See docs/CURRENT_PROGRESS.md and docs/INTERACTIVE_TEST_QUEUE.md. During the operator's
absence independent implementation/validation continued; current198-test host and
Ubuntu20.04/24.04 installed-wheel suites passed. Fresh userspace provisioning and
native signed Compose clients were tested, bounded storage worker tracking added,
and physical NAS directories/RO secondary/current Bazarr-Jackett apply/reruns passed.
Latest exact baseline snapshot: /var/tmp/installarr-interactive-state-xfi7v389/checkpoint.json.
Only the3retained baseline services are active/boot-disabled;5containers. No fixture
command running, reboot, commit or push. Remaining gates need operator scope/input,
human GUI judgment, a fresh claim/clean systemd target or disruptive-test permission;
keep their recipes/checkpoints and never silently perform reboot/outage/production
access. No installer-release-readiness claim. Full details/limitations in TEST_RESULTS.md.


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


## Publication and upcoming clean test — 2026-10-30 (latest)

Operator explicitly requests publishing ALL reviewed current implementation/tests/
docs to boosted3svt/Installarr before their Ubuntu24.04.5 reinstall. They will
back up ~/.codex off-machine and restore it to resume this conversation. No wipe,
reboot, service teardown or media cleanup by Codex. Current authoritative context:
docs/CURRENT_PROGRESS.md, docs/SAVED_CHECKPOINT.md, docs/CURRENT_SETUP.md and
docs/FRESH_HOST_CODEX_HANDOFF.md; these supersede old live-service/pause statements.

Read-only observation now finds NEW successful operator-run HomeNet-Test2, seven
apps under /var/lib/installarr-setup/installations/setup-c2c7141a879e, unit
installarr-family-c2c7141a879e.service active/enabled; bootstrap inactive/disabled,
reference_poc_ready and automatic_startup verified. Previous family-9ad2bb7ce113
and family-media stopped/disabled. Current mounts .103 Public→/media/Media and
.102 Public→/media/Media-2 match selected sources. Keep this deployment unchanged.
After the wipe, all those host resources are historical: restore conversation
only if desired, clone published code and let ./installarr.sh provision fresh
accounts/packages/mounts/DBs. Fresh private credentials and Plex claim are intentional.

Publication includes scoped standardized folders, full pinned profile/quality sizes,
local/NVMe/NFS guide, fresh-setup switching and safe provider/Arr timeout diagnostics.
244host tests and current244test supported-distro wheels pass. Original Sonarr
10s stall cause not proved; no blind mutating retry. Never umount -a for NAS cleanup.
Next goal is full clean-OS/systemd install and coordinated boot/mount acceptance,
not repeated ordinary user actions. Every app remains optional; no new backends.

Publication complete: implementation e1fed73169336eb335475ae2af3937e99495d3ef
on public main, exact reviewed tree verified; fresh public clone launcher and
244tests pass. Docs-only follow-up records the completed savepoint. Clone main
after reinstall; no private files/reference Compose or app DBs published.


## Fresh host and approved permission supervision — 2026-10-30 (latest)

Operator reinstalled Ubuntu24.04.5 and completed fresh seven-app setup at
192.168.1.51/23, user plex, checkout /home/plex/Installarr, Plex HTPC-210. Live
installarr-family-media.service active/enabled; new settings/apps/state under
/var/lib/installarr-setup; bootstrap inactive/disabled. Current exact sources
.103 Public→/media/Media and .102 Public→/media/Media-2. Old /home/htpc/fixture
paths/units are historical after the wipe. No networking changes/reboot by Codex.

Operator confirmed copied movie subfolders root:root750 blocked UID2000 and
explicitly APPROVED a new opt-in recurring permission-repair policy in the existing
host supervisor. This supersedes preserve-all-content-metadata restrictions ONLY
inside configured Plex media roots. File-owner UIDs remain unchanged; grant shared
service GID/read/search when needed. No recursive whole-share chown,777,root Plex,
NAS API/ACL dependency or extra backend. Skip symlinks/hardlinks/nested mounts/
NAS metadata/explicit read-only secondary; check mount/marker before repair.

Feature is enabled locally after an explicit stopped-runtime refresh with private
backup; first pass after healthy/running containers, repeat60s AFTER completion,
2s supervisor polling overhead;1000entry/5s batches with30s worker deadline and
unreaped-worker refusal. Real NAS and asynchronous worker tests passed; first live
pass repaired7entries, no denials. Actual3movie reads as2000:2000 passed. A late
restricted fixture was repaired on the next pass62.41s after the previous completed
pass; fixture cleaned up. Later pass changed0. Read MEDIA_PERMISSIONS.md and
CURRENT_PROGRESS.md. Code/docs local, no commit/push yet for this new feature.


## Permission feature publication and completion scope — latest

Operator confirms CODA/Astro Boy/6Underground appeared in Plex after the repair
without any additional container restart, and explicitly requests publishing this
feature for fresh clones plus a completion estimate. Full254host and20.04/24.04
installed-wheel suites pass after fixing older-libc effective-ID checks with a
short-lived real-UID verifier.826reviewable files checked against current private
values: zero matches. No credentials/policy/DBs/Codex history in Git. Fresh guide
must explicitly opt in; default no. Later source portability fix is not silently
loaded into the already-running immutable supervisor; no additional restart.

Estimate about90% overall for agreed fresh-install scope, not measured coverage
or release-ready. Remaining work: publish/verify clone, coordinated actual reboot
and unavailable-storage acceptance, new-policy large/changing-tree/interruption
hardening and final release audit. Selected clean seven-app install is COMPLETE;
do not require another reinstall, all-nine selection or more ordinary app-user
actions. See rewritten IMPLEMENTATION_CHECKLIST.md and INTERACTIVE_TEST_QUEUE.md.
