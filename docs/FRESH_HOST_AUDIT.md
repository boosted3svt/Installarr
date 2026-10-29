# Fresh-host implementation audit — 2026-10-29

This records implementation/evidence boundaries, not release readiness. Operator
interaction gates and restoration recipes live in INTERACTIVE_TEST_QUEUE.md.

| Step | Current behavior / evidence | Remaining gate |
| --- | --- | --- |
| Bootstrap | Python3.8+, Ubuntu20.04+, tzdata; standard host account/systemd/util-linux tools required. No third-party Python packages. | Full clean OS/systemd target, I-04. |
| Accounts | Exact UID/GID collisions refused; locked checkpoints and interrupted group creation recovery; no existing identity changes. | Clean target acceptance. |
| Storage packages | Signed APT policy; NFS/CIFS clients before any managed mount; openssl for netboot authentication helper. | SMB physical fixture deferred I-06. |
| Repositories | Official Docker signing fingerprint pinned; deb822 Signed-By; explicit trusted/insecure source bypass refused before Docker staging too. | Changed upstream key/repository selection requires review, never bypass signatures. |
| Docker20.04 | Signed Focal archive installed/binary-tested in official20.04 userspace: Engine28.1.1/Compose2.35.1/Buildx0.23/containerd1.7.27, amd64 only. Package set pinned; changed archive refused. | Focal is outside current upstream support; full engine/systemd/boot acceptance is I-04/I-01. |
| Docker22.04/24.04 | Official signed repository; exact selected versions checkpointed. Stage with services masked, explicit owned-engine transition. Existing foreign engine/data/repositories preserved. | Full clean-host combined apply; no automatic Docker version migration. |
| Existing host | Matching owned active engine is not remasked/restarted. IP/DNS/manual routes/SSH/VLAN/disks preserved. Standard reference Docker NAT/bridge explicitly authorized. | Actual reimage/fresh host not authorized here. |
| Mount persistence | Exact source/type conflict checks, fstab backup/idempotence and private-namespace fresh NFS tests. No recursive media ownership changes. | Real NAS outage I-02 and reboot I-01. |
| Data directories | Validate anchors before writes; private local DBs, held-FD identity probes. Secondary Movies-2 is read-only/existing-only; netboot assets use911 independently. | Actual production secondary source details I-03. |
| Container publication | Unpublished bootstrap, real GUI auth, then matching authorization gate and HTTP ports. No optional HTTPS GUI mappings. | Combined physical permutations and final GUI I-08. |
| Storage protection | Exact pre-init mount/marker assertions; bounded per-UID supervisors stop only owned containers and recover. Docker restart is not mistaken for a health-check action. | Reboot/real outage acceptance; sentinel simulations are recorded separately. |
| App integrations | All nine adapters pinned/authenticated; real provider and generated output tests, native Plex users/routing, registered subtitle jobs. | Combined family apply I-07; Jackett choices I-05; unavailable public providers are external conditions. |
| Resumes | Private locked checkpoints, reread host/app state, reject conflicting artifacts; no secret values in nonsecret state. | Continue focused interruption/failure tests; don't infer readiness from inventory. |
| Runtime updates | Explicit stopped-unit refresh with private byte backups/journal, fingerprints, SIGKILL recovery and apply rerun tested. No silent saved-unit replacement. | Image/app schema/changed Compose migration remains separate; current release scope is fresh provisioning. |
| Boot | Test application and engine units remain boot-disabled. No reboot performed or approved. | I-01 requires explicit scheduling/permission and reconnect recipe. |

Docker upstream OS requirements: https://docs.docker.com/engine/install/ubuntu/
Official Focal archive: https://download.docker.com/linux/ubuntu/dists/focal/pool/stable/amd64/
Package evidence: /var/tmp/installarr-focal-docker-dipa_fld/result.json.
Python runtime evidence: /var/tmp/installarr-ubuntu-runtime-5aetmw0t.
All container userspace experiments had no host socket, NAS, credentials or privileged
host mounts; installing binaries in them does not establish host daemon readiness.


Latest fresh-rootfs adapter evidence:
/var/tmp/installarr-fresh-userspace-37klco9z/{20.04,24.04}/result.json,
acceptance.json and staging-acceptance.json. Real account/prerequisite/signed Docker
staging/directory adapters passed inside disposable userspaces; no host engine/socket,
NAS, credentials or system paths exposed. Actual native signed Compose2.35.1/5.6.1
parsed1022 configurations each, then refused absent binds on host engine29.9.2.
This strengthens userspace/client evidence; I-04 full systemd/engine/boot remains.
Bounded storage operation registry prevents retry accumulation of unreaped workers;
real outage acceptance is still I-02. See latest TEST_RESULTS.md entry.
