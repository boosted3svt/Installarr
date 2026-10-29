# Current Installarr checkpoint

Authoritative latest checkpoint. Earlier live-service and pending-input descriptions
in chronological logs are superseded by this document.

## Product goal and normal launch

Fresh Ubuntu with OpenSSH only. Install Git, clone, launch one script:

```sh
sudo apt-get update
sudo apt-get install -y git ca-certificates
git clone https://github.com/boosted3svt/Installarr.git
cd Installarr
./installarr.sh
```

The script installs missing python3/ca-certificates/tzdata, then opens plain guided
setup with no flags. Installed console command `installarr` also defaults to the
guide. Normal prompts hide internal state paths, UID/GID and Compose details.
Explicit subcommands remain advanced tools. Published to the operator-owned boosted3svt/Installarr repository on main.
First implementation commit: bc9017a4eec41b8bd514901b0067accbdfffdd2c. Each clean installation prompts for credentials and optional
Discord IDs; no saved credential file or manual transfer is part of the flow.

Scope is fresh provisioning, shared logins, app API connections, full pinned TRaSH
profiles, storage and family roles/preferences. Do not add ordinary request/playback
user actions, disaster recovery or arbitrary reconfiguration as acceptance gates.
Every app remains optional; defaults reproduce all nine reference apps.

## Current live stack — supersedes the old three-service baseline

Operator approved the combined fresh-stack switch. All nine containers are now
running under **installarr-freshcheck-aaabe264-v2.service**, active/boot-disabled.

- Config: /var/tmp/installarr-fresh-acceptance-vhydzwl1/config-v2.json
- State: /var/tmp/installarr-fresh-acceptance-vhydzwl1/state-v2
- Result: /var/tmp/installarr-fresh-acceptance-vhydzwl1/result.json
- Exact app/container snapshot: sibling live-checkpoint.json
- Bootstrap unit freshcheck-aaabe264-v2-boot is stopped.
- Root runtime audit passes integrity and matches current source for both units.

HTTP at10.70.0.99: SAB8090, Sonarr8989, Radarr7878, Bazarr6767, Jackett9117,
Plex32400/web, Ombi3579, Tautulli8181, netboot3250.
Plex server name is **Installarr Fresh Acceptance**; five grouped libraries,
currently empty generated fixture folders. No original supplied media was copied.

The previous units are now STOPPED and boot-disabled; do not start them alongside
the new stack because they use the same ports:
installarr-poc-http-d29db77d, installarr-plex-standard-test,
installarr-ombi-family-2274744e. Their databases/configs are preserved.
Original claimed Plex DBs remain /var/tmp/installarr-plex-authorize-uo198y7v/configs.
Never start obsolete plex-auth-test/libraries-test/grouped-test units.
First-attempt freshcheck-aaabe264 units are also stopped/superseded.

Rollback: stop new freshcheck-aaabe264-v2 and its -boot unit, remove only their
owned containers if needed, then start exactly the previous three units. Approved
switch/retry helper tools/run_prepared_fresh_test.py implements failure rollback.
Do not rerun tools/prepare_fresh_acceptance.py blindly: an exact prepared fixture
already exists. Current root-private pointer: /var/tmp/installarr-prepared-fresh-test-v2.json.
No more browser claim is needed for the current claimed test server.

## Production defaults versus physical-test boundaries

| Source | Mount | Role |
| --- | --- | --- |
| 192.168.1.103:/share/MD0_DATA/Public | /media/Media | TV, family movie folders, primary media/downloads |
| 192.168.1.102:/share/MD0_DATA/Public | /media/NAS | Other movies at /media/NAS/Movies |

These operator-provided values are editable wizard defaults only. Production
exports were not accessed. The actual physical test source remains exclusively
192.168.1.102:/share/MD0_DATA/Public/installarr at /media/installarr.
One current owned NAS fixture: Installarr-Fresh-Acceptance-aaabe264, with Primary
and AdditionalMovies children. Application DBs and netboot assets are local under
the work directory. The installer does not create developer experiment folders on
a fresh system. Old NAS evidence fixtures have not been bulk-deleted.

Plex Movies combines Movies, Movies-2, jeremymovies,lenoramovies; TV combines
TV,lenoratv,jeremytv. sports→sports, StandUp→StandUp, Music→Music. Exclude low-res,
Disney, Only Heather, YouTube and TubeSync libraries; preserve their files.
Secondary writable mode shares /media-secondary with Radarr/Bazarr and registers
an extra Radarr API root; Plex retains a read-only bind. Legacy explicit read-only
mode is still supported. netboot assets use911:1001 independently of media2000.

## Accounts, providers and family preferences

Shared GUI username admin. Current private shared copy:
/var/tmp/installarr-fresh-acceptance-vhydzwl1/state-v2/secrets/gui-admin.json.
Never print it. Existing original GUI store and provider credentials are preserved.
Providers: /var/tmp/installarr-providers-secrets/providers.json.
Newshosting100 strictTLS563; NZBGeek; OpenSubtitles.com ONLY; English standard.
Do not reintroduce Yify/Supersubtitles/TVSubtitles. No torrent downloader was added.

Full pinned TRaSH snapshot d24f13ceea5e82ccc20d08b7814fca93840e4046 (625documents).
Movies prefer Remux+WEB1080p, separate manual2160p option; TV WEB1080p.
Resolve all app IDs dynamically. Native Plex family users lenora8/rebel739/beanie08
are prestaged with intended roots/profiles/approval roles; Beanie PowerUser/inherits
globals. No local lookalikes or family passwords. All verified on combined stack.

Private Discord targets: /var/lib/installarr-setup/family/family.json, root600.
rebel739 and beanie08 supplied locally, POSTed and verified; lenora8 deliberately
blank per operator. Notification sending remains disabled. IDs reused in the fresh
combined Ombi and read back without disclosure. Exact method/context:
OMBI_FAMILY_PREFERENCES.md. Do not ask for these IDs again or put values in Git.

## Latest evidence and real issues fixed

- All9 combined apply and repeat/readback passed; result.json above. Authenticated
  host publication, API integrations, profiles, family prefs and actual nine running
  containers verified. Standard Docker bridge; no extra backend or network design.
- Combined test exposed shared mutable volume objects: Plex readonly leaked to
  other apps. Fixed with separate volumes; all511 subsets now assert access modes.
- Cold empty Plex DB exposed HTTP400 "the server is still starting up. Please retry
  later" plus slow agent loading. Exact nonmutating startup refusal has a bounded
  retry; other validation failures are not retried. Plex HTTP deadline60s, bounded
  outer65s; read-only agent discovery retries known transient failures. Empty DB
  then created all five libraries without manual seeding:
  /var/tmp/installarr-cold-plex-10o5gfid/result.json.
- Writable secondary Radarr/Bazarr API roots/writes/reruns passed:
  /var/tmp/installarr-secondary-writable-z9p8s75c/result.json; generated NAS fixture
  removed after containers stopped.
- Minimal Ubuntu20.04/24.04 container userspaces without Python passed shell bootstrap:
  /var/tmp/installarr-bootstrap-9wwqkz11/{20.04,24.04}/result.json.
- Actual plain wizard PTY selected all9 and saved without provisioning/NAS writes:
  /var/tmp/installarr-guided-preview-pnenlp8s/result.json.
- Host217-test suites passed (root215/2skips, htpc212/5skips), logs
  /var/tmp/installarr-foundations-final-{root,htpc}.log.
- Final wheels passed217 tests (215passed/2skips) on both20.04 and24.04:
  /var/tmp/installarr-distribution-ukeybv4s/{20.04,24.04}/result.json.
  The installed source digests, all625profile documents/license, CLI and atomic
  runtime checks passed. No credentials/Discord IDs found in810reviewable files.

The guide now offers automatic startup after successful installation and verifies
only the owned deployment/Docker/containerd units. Unit tests cover readiness and
ownership gates. Physical test units remain disabled; no reboot approved/performed.
Publication completed through the existing authorized GitHub connector. A new
public clone of commit bc9017a4eec41b8bd514901b0067accbdfffdd2c passed the launcher and217-test
suite. Evidence: /var/tmp/installarr-public-clone-dd6cdxrk/result.json. Remaining
fresh-install acceptance is a genuinely clean Ubuntu/systemd target and its boot
behavior. Do not substitute more ordinary
application GUI actions for those remaining installer-level checks.
