# Requirements and acceptance boundaries — 2026-10-29

Latest2026-10-30: CURRENT_PROGRESS.md and CURRENT_SETUP.md supersede historical
pending-input/live-unit statements in this matrix. Full standardized profiles/
quality sizes, native family notification preferences and a seven-app operator
ready/enabled run now pass. Current244host suites pass; publication and an
operator-led Ubuntu24.04.5 reinstall/full fresh guide/boot test are the next work.
Do not add repeated ordinary application-user actions as acceptance gates.

This matrix maps the operator handoff to actual evidence. “Passed” has the stated
scope; it never means all environments or a complete release. Current commands,
private fixture paths and running services are in CURRENT_PROGRESS.md. Exact pins,
failures and commands are chronological in TEST_RESULTS.md.

| Requirement | Implementation / evidence | Remaining interaction or scope |
| --- | --- | --- |
| Fresh Ubuntu first,20.04+ | Root/distro gate, signed host adapters, private state; physical22.04. Real20.04/24.04 fresh-rootfs account/prerequisite/Docker-mask/stage/directory/secret/render adapters passed; Python suites and wheel installs passed. | Full clean OS/systemd target I-04; Focal outside current upstream support. Migration/DR is a stretch goal. |
| Python3.8 | Actual20.04/Python3.8.10 suite, wheel/entrypoint/catalog and Linux atomic operation passed; grammar checks all Python. | Full current target/boot remains separate. |
| CLI menus, unattended, resume | Terminal navigation over same commands; real PTY plan/exit and hidden synthetic GUI collection. Nonsecret JSON/private secret files; immutable config/name/state; real interrupted account/import/runtime recovery and failed-apply resume. | Human workflow acceptance I-08. |
| Fresh Plex claim timing | Prepare-only stages host/images before claim, starts no apps, tolerates absent claim file. Rerun preserves live container IDs/start times/supervisor PID. | Fresh browser claim only when selected, I-07. |
| All nine apps optional | All511 render subsets and both signed Compose2.35.1/5.6.1 native parsers (bootstrap/published); individual/minimal physical pairs plus standalone Bazarr/Jackett and Tautulli/Ombi; no inferred apps. | Combined fresh-host/family acceptance I-04/I-07; not511 physical full stacks. |
| Dependencies discovered | Plan identifies missing downloader/indexer/Plex/request/subtitle setup; recognizes selected configured providers. Jackett explicitly not a downloader. | Optional Jackett indexer choices I-05; no torrent backend added. |
| Official tested images | Exact digest/version pins for all nine; real runtime/database UID/auth and API checks. Existing-image Nginx only for netboot protection. | Image/schema migration is outside the fresh provisioning acceptance; no auxiliary backend design added. |
| Standard non-root identities | Tested2000:2000 media apps; init may legitimately start as root. Account collisions/readback/recovery preserve existing identities. | Clean-target repeated acceptance I-04. |
| netboot911:1001 | Reserved nbxyz identities, actual local/NFS asset writes, auth/restart, separate bounded identity health workers. Node3001 unpublished. | DHCP/PXE client reachability explicitly out of scope. |
| Defaults editable | America/Chicago, detected/editable LAN IPv4/hostname, Plex allowed networks192.168.0.0/23; live Plex preference readback passed. | Final human wizard/GUI I-08. |
| One storage map / case preserved | Compose, Arr roots, SAB categories, Bazarr links, Plex grouped locations and family routes use map. Shared data_root passed real hardlinks; no media renames/copies in acceptance fixtures. | Actual secondary production source values I-03. |
| Separate secondary Movies-2 | Optional existing read-only source; existing marker/UID reads, no directory/marker creation or write probes; bind write refusal/source metadata preservation and sentinel stop/recovery passed. | Claimed Plex GUI I-07/I-08 and production values I-03. |
| Local app DBs / no recursive NAS chown | Local filesystem checks, actual database ownership. Existing metadata preserved. New fixture files only under approved export. | Full clean-target I-04; original supplied examples remain untouched. |
| NFS/SMB prerequisites before mounts | nfs-common/cifs-utils adapter precedes mount work; exact source/type checks, protected SMB file parser; signed sources with bypass rejection. Fresh NFS/persistence passed private namespace. | Hidden/private-file SMB collector/menu tested synthetically; physical share fixture I-06, no Samba server installed. |
| Preserve mounts/fstab | Conflict refusal, exact backups, duplicate-free resume; live host fstab preserved in experiments. | Real target persistence/reboot I-01/I-04. |
| Health vs UID write access | Separate mount/source/type/read/sentinel and UID write/fsync/readback probes; held descriptors prevent private ancestors masking leaf permissions. | Real NAS outage I-02; read-only secondary intentionally has no writes. |
| Reboot / Docker restart protection | Container pre-init assertions; ongoing scoped supervision stops/restarts only matching containers, bounded per-UID workers and supervisor-crash fallback. Docker restart=no plus guard on manual starts. | Actual reboot and real outage I-01/I-02; simulations do not establish them. |
| Shared GUI admin once | Private reusable GUI store, hidden password, Forms/Basic/native auth per app, actual valid/invalid/anonymous tests. API keys remain separate. Menu creates private state parent before collection. | Human GUI/menu I-08; Jackett password-only is verified. |
| Protected bootstrap / Plex own auth | No published bootstrap ports, native account claim and real Plex GUI playback; authenticated publication evidence/gates. Ombi host admin DB presence checked. | Fresh combined claim I-07; existing claimed DBs never copied into a concurrent server. |
| Native family identities | Selective genuine Plex import, dynamic profile/root/tag/user IDs; Lenora/Jeremy HD roots, Beanie inheritance, approvals/PowerUser and restart. Native boosted3svt ordinary-user requests passed without anyone else's credentials. | One full combined family apply I-07; browser sign-in already confirmed for operator. |
| Discord preferences | Per-user target POST/readback and private reusable collection implemented; notifications stay disabled independently of saved IDs. | Actual three IDs not found in retained Ombi/private fixtures; hidden local collection pending. See OMBI_FAMILY_PREFERENCES.md. |
| Full pinned TRaSH | Commit-pinned625-document catalog with checksum closure, default/required format groups, real schemas/ID/write/readback, HD/UHD coexistence/restart. HD preferred, UHD manual option; existing assignments preserved. | No unresolved profile-choice question. |
| Real providers | Newshosting100 strictTLS/auth, official100MB NNTP transfer, NZBGeek movie/TV links and stable IDs/reruns. English OpenSubtitles.com auth/search/download/defaults, registered Bazarr wanted jobs. | Yify TLS/410 and TVSubtitles search404 are external conditions; preserve requested providers/TLS. |
| Requests / downloads / imports | Native Ombi movie/TV dispatch and per-user roots/profiles; normal Radarr/Sonarr release→generated NNTP→completed import, exact hashes/ownership/history/restart. No import-mode manager. | Single combined fresh family/provider acceptance I-04/I-07; controlled fixture advertised size is synthetic and is documented. |
| Runtime updates | Read-only content audit, explicit stopped compatible-unit refresh with original-byte backups, durable journal, SIGKILL rollback and full apply rerun. Atomic no-replacement file publication survives crash/concurrency. | Existing three supervisors deliberately retain their original snapshots; image/app state migration is separate. |
| Failure ownership | Conflicting saved unit bytes/ownership/mode refused before host prep. Early normal-apply failure stops verified old supervisors; preparation-only errors preserve running apps. Physical same-config recovery passed. | New failures remain evidence; don't infer readiness from status/open ports. |
| Installable artifact | Wheel build/install/entrypoint/offline profiles and upstream license file passed official20.04/24.04 userspaces; updated build checks prepare-only CLI. | Artifact is local review evidence, no release/publish/commit/push requested. |
| Host scope | Only approved export/new fixtures; existing retained services preserved, standard bridge/NAT authorized. No hostIP/DNS/SSH/VLAN/disks/unrelated firewall edits. | Reboot, real NAS disruption, SMB scope and fresh target require explicit operator action. |

The interactive queue is a selection list for when the operator returns. Do not
stop autonomous work merely because one row is gated; continue independent work.


2026-10-29 evidence supplement: fresh20.04/24.04 userspace provisioning adapters
passed at /var/tmp/installarr-fresh-userspace-37klco9z. Both native signed Compose
clients passed1022 cases each and physical absent-bind refusal. CLI storage work now
uses bounded tracked workers and held-descriptor transfer; stopped-worker cross-CLI
retry refusal/recovery is tested. No change to interactive gates or readiness claims.
