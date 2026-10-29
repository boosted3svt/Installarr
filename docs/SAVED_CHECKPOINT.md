# Saved checkpoint — autonomous continuation 2026-10-29

**Active autonomous work during the operator's approximately five-hour absence.**
The earlier requested pause was superseded. Continue independent work; record
interaction gates in INTERACTIVE_TEST_QUEUE.md instead of asking or waiting.
All files saved in the existing checkout; no commit/push/reboot. A disposable
fixture may be active: inspect CURRENT_PROGRESS.md and the latest experiment log
before restarting anything. Preserve the three retained services below.

- Authoritative resume: [CURRENT_PROGRESS.md](CURRENT_PROGRESS.md).
- Open work: [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md).
- Exact commands/pins/failures/results: [TEST_RESULTS.md](TEST_RESULTS.md).
- Retain active/boot-disabled: installarr-poc-http-d29db77d.service,
  installarr-plex-standard-test.service, installarr-ombi-family-2274744e.service.
- Original supplied media preserved. Final five Plex libraries and exact matching
  sports/StandUp folders unchanged; movie/episode GUI playback confirmed.
- boosted3svt native Plex sign-in and ordinary-user request/routing tests passed.
  Original operator Admin settings restored. Never ask for other people's credentials.
- Private providers already collected at
  /var/tmp/installarr-providers-secrets/providers.json. Never print/recollect them.
- Newshosting100/TLS563 and NZBGeek actual Radarr/SAB and Sonarr/SAB apply/reruns
  passed. Official SAB100MB test completed through Newshosting to NAS,2000:2000.
- OpenSubtitles.com native login/search/download passed. Standard English future
  movie/TV defaults persisted, without forced/HI or reassignment of existing media.
- Yify TLS error, TVSubtitles HTTP error and Supersubtitles0 sample results remain
  limitations. No TLS bypass, new backend or silent provider removal.
- All disposable experiments removed; generated NAS outputs retained as evidence.
- Host suites158 tests,157 passed/1 appropriate skip as htpc/root. Python3.8 grammar
  and diff whitespace checks passed. Prior Ubuntu20.04/24.04 runtime suites148 tests.

Resume remaining scheduled Bazarr library-search, public-provider availability,
combined family apply, secondary sources, netboot asset storage, remaining menus,
fresh-host/runtime-update audit and clean-OS/explicitly approved boot acceptance.
Do not start older Plex units sharing the same databases. No reboot is approved.

Latest autonomous additions supersede the historical remaining-work paragraph:
registered scheduled Bazarr jobs passed; explicit local/NFS netboot assets passed
including marker-loss recovery; all511 optional render subsets passed; private
ancestor write probes use verified FDs. Explicit stopped-runtime refresh passed
SIGKILL rollback/retry and physical apply rerun. Separate read-only Movies-2 source
mapping passed unclaimed/unpublished Plex UID reads/write refusal and marker
supervision; production source details and claimed-library GUI remain queued.
Latest host suite before secondary additions:165 tests,164 passed/1 skipped;
repeat the complete suite after current source/CLI changes.

Autonomous continuation latest: native generated Radarr and Sonarr download/import,
standalone optional pairs, terminal menu and atomic no-replacement publication are
implemented/tested. Full175-test suites passed in20.04/24.04 userspace; host suite
refresh follows latest changes. See CURRENT_PROGRESS.md for current work/evidence;
this checkpoint is active, not a pause. No retained service stop/update or reboot.

## Latest autonomous continuation — 2026-10-29

Fresh Ubuntu20.04/24.04 userspace provisioning adapters passed (accounts, prerequisites,
signed Docker staging, local UID write probes, all-nine-app rendering). Native signed
Compose2.35.1/5.6.1 each passed1022 optional configurations and real absent-bind refusal
on host engine29.9.2. Full clean-OS/systemd/boot acceptance still needs I-04.

Bounded tracked storage workers now cover foreground anchor opens, directory work,
read/write probes and mount processes; unreaped groups block retries across CLI
invocations. Host198-test suites and153-file Python3.8 grammar passed; physical
read-only NAS-source rerun passed. Real NAS outage/reboot remain queued, not claimed.
Detailed evidence and limitations are in TEST_RESULTS.md.

Current exact baseline snapshot:
/var/tmp/installarr-interactive-state-il2ubn83/checkpoint.json (3active/boot-disabled
units,5containers). Latest wheel rebuild is underway at
/var/tmp/installarr-distribution-ngfrf9l0; inspect result.json before using it.
No interaction requested; retain all existing credentials and services.


Current wheel verification completed: /var/tmp/installarr-distribution-ngfrf9l0,
Ubuntu20.04/24.04 each198 tests passed with2appropriate skips; installed source hash,
profiles/data/license/CLI checks passed. Root/htpc current suites also passed198.
Physical writable NAS directory and read-only secondary reruns passed after worker
changes. Remaining clean-systemd/boot/outage and human gates remain in the queue.


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
