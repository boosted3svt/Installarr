# Fresh headless installation runbook

## Standardized storage guide — latest implementation

Run `./installarr.sh` without flags. New setups explicitly choose local/NVMe,
NAS/NFS or existing mounted storage, each media/download folder and optional
separate download storage. The approved layout and exact production defaults are
in PROPOSED_PRODUCTION_STORAGE_CHANGELOG.md (now marked implemented). New Plex
libraries: Movies, TV Shows, Sports, Standup; Music excluded without deleting files.
SAB uses unfinished-downloads/finished-downloads and prepared movies/tv categories.
Strict per-app binds use common `/data/<role>` names and can require copy imports.

When the old saved setup is found, choose no to continuing it, then yes to a fresh
installation. Review and save the complete source/mount/folder/access map. Saving
alone does not stop services. On Start installation confirmation, the prior owned
deployment is stopped/disabled, its settings/DBs preserved, and only conflicting
managed mounts/fstab entries replaced. New setup selection is saved privately in
/var/lib/installarr-setup/active-setup.json; actual config/state are under its
selected /var/lib/installarr-setup/installations/setup-* directory. GUI/provider/
family inputs are reused privately. The new Plex database requires its own claim.

If a switch fails, resume the same saved setup. Do not delete checkpoints or force
mount over unrelated files. Before-switch fstab and verified prior unit/definition
backups are in the new private setup directory. Prior app databases stay at their
original paths; any retired local netboot assets child is preserved unchanged under
retired-local-assets. Restoring the prior setup requires stopping the new owned
deployment, checking current mounts, restoring reviewed persistence/asset paths and
starting only its prior unit; do not start both on the same ports. No automatic
database migration, media movement or reboot is performed.

The advanced/historical layout examples below describe saved legacy configs and
do not supersede these new guided defaults.

For the current physical test server, resume the exact configurations/state in
CURRENT_PROGRESS.md. This runbook describes a new approved Ubuntu target and a
new deployment name/state directory. The project remains a tested partial installer;
clean-host combined/systemd/boot acceptance is tracked in INTERACTIVE_TEST_QUEUE.md.

## Choose terminal navigation or unattended commands

From this checkout, run `./installarr.sh`. After package installation, run
`installarr`. Neither needs flags. Missing Python/certificate/timezone prerequisites
are bootstrapped before the guide. The guide handles settings paths and deployment
names, identifies mounted storage or offers the production NFS defaults, asks for
account details, prepares the host, then collects Plex authorization and installs.
All9reference apps are offered individually, with plain descriptions and editable
choices. The explicit commands below are advanced documentation.

The menu order is deliberate: configure → plan → shared GUI credentials → provider
credentials → prepare host/images → fresh Plex claim → apply. Preparation finishes
slow package/image work before the short-lived claim is collected. Every app is
optional; a missing downloader/indexer/request backend remains explicit in the
plan, without automatically adding apps.

## Nonsecret configuration

`python3 -m installarr configure --config /path/installarr.json` detects editable
host address/name and collects the shared data root, exact mounted source/type,
local application DB paths, optional apps, library grouping, pinned profiles and
provider choices. The file is private and never overwritten. Review with
`python3 -m installarr plan --config /path/installarr.json`.

For NFS the installer installs nfs-common before attempting the configured mount.
Use the exact approved export and preserve path case. Existing mounts/fstab are
reconciled, conflicts preserved and persistence edits backed up. Database paths
stay local; NAS libraries are not recursively chowned. Local/existing/NFS/SMB are
supported choices; SMB needs an existing root-private mount.cifs credential file
and cifs-utils. The current physical SMB fixture remains deferred; no Samba server
is installed by this project.

Default reference Plex libraries are Movies (Movies, Movies-2, jeremymovies,
lenoramovies), TV (TV, lenoratv, jeremytv), sports, StandUp and Music with matching
last-three folder names. Excluded/removed collections are documented in the checklist.
An optional storage.media_secondary supplies Movies-2 read-only from a separate
existing source/marker. Optional storage.netboot_assets uses911:1001 and its own
mount assertions; other app media uses the configured non-root identity.

Movie defaults are full pinned Remux + WEB1080p, with Remux + WEB2160p available
for manual upgrades; Sonarr WEB-1080p. Existing media assignments are preserved.
Optional family presets resolve genuine Plex identities/IDs dynamically; they do
not create local lookalikes or require other people's passwords.

## Private inputs and preparation

Collect shared GUI credentials once:

```sh
sudo install -d -m 0700 /var/lib/installarr-media-stack
sudo python3 -m installarr init-secrets --secrets-directory /var/lib/installarr-media-stack/secrets --config /path/installarr.json
```

The state parent `/var/lib` already exists; use an existing local parent for a
custom state path. For unattended GUI input, init-secrets accepts a separate
executor-owned0600 JSON credential file via --credentials-file. Selected Basic-auth
apps validate the username before publication. Providers support the same private
JSON import flag; --filename lets provider/Plex collectors honor a configured
private output name. Different collectors/files can share a private folder.

If the reference providers are selected, collect privately at the directory named
by provider_secrets_file in the nonsecret config:

```sh
sudo python3 -m installarr init-provider-secrets --secrets-directory /var/lib/installarr-provider-secrets --providers newshosting,nzbgeek,opensubtitlescom
sudo python3 -m installarr apply --reference --prepare-only --config /path/installarr.json --name media-stack --state-directory /var/lib/installarr-media-stack
```

Preparation reconciles identities, prerequisites, mounts/directories, signed
Docker staging/owned standard-engine activation and pinned image availability.
It starts no application containers, leaves existing application services as they
were and keeps boot settings unchanged. Matching private GUI credentials are reused.
If no provider credentials are selected, skip that collection command. Public
subtitle providers without credentials need no secret record.

For fresh Plex only, open https://www.plex.tv/claim on another device **after**
preparation. Collect the new claim privately and immediately apply:

```sh
sudo python3 -m installarr init-plex-claim --secrets-directory /var/lib/installarr-plex-claim --replace
sudo python3 -m installarr apply --reference --config /path/installarr.json --name media-stack --state-directory /var/lib/installarr-media-stack
```

Set plex_claim_file to that directory's plex-claim.txt in the original config
before preparation. A new claim is unnecessary for an already authorized matching
Plex deployment. Optional unattended claim input uses a separate private raw claim
file via init-plex-claim --claim-file. Never place tokens/passwords/API keys in the
nonsecret JSON, shell arguments, Git or chat.

## Optional SMB private input

For a selected SMB mount, the menu's provider/storage input action can create the
configured root-private mount.cifs credential file. The equivalent command is:

```sh
sudo python3 -m installarr init-smb-secrets --secrets-directory /etc/installarr --filename smb.credentials
```

It collects hidden username/password/optional domain and stores0600 credentials;
it does not mount anything or install a Samba server. Unattended --credentials-file
accepts a separate root-owned0600 JSON object with username/password and optional
domain. Existing valid files are retained. The configured path must match the
output file; each private directory is0700. Physical SMB share acceptance remains
deferred. Other provider imports likewise use --credentials-file; actual secret
values never appear in the nonsecret config, output or metadata checkpoints.

## Apply, resume and acceptance

Apply uses unpublished bootstrap, real app authentication/configuration checks,
then reference HTTP port publication guarded by matching authorization evidence.
It prints selected GUI URLs and private credential-file location. Its
reference_poc_ready result does not certify every external provider, full combined
family behavior, clean OS or reboot. Use TEST_RESULTS.md for exact evidence.

Resume with the same config, name and state directory. Conflicting files/units,
identities or host settings are preserved; do not reuse another deployment's name
or point new configs at existing immutable state. A failed attempt stops only its
own selected services. Review `service-status --name media-stack` and saved private
checkpoints when diagnosing. Separate GUI administrator credentials and API keys
remain distinct; Plex uses its own authorization and Jackett is password-only.

Saved supervisors run immutable Python snapshots. `audit-runtime --name NAME`
verifies them. `refresh-runtime --name NAME --state-directory ORIGINAL_STATE`
requires both live/bootstrap units stopped, creates private original-byte backups,
recovers interruptions and leaves them stopped. Start the live unit explicitly
and rerun apply for app checks. It does not migrate images/configuration/databases.

Application and Docker boot enablement remain explicit. Do not infer reboot
readiness from successful live apply; complete the scheduled boot/storage outage
acceptance on an approved target first. Current physical test units stay disabled.


## Confirmed production NFS defaults

Operator supplied the following via read-only findmnt output:

| NFS source | Local mount | Media role |
| --- | --- | --- |
| 192.168.1.103:/share/MD0_DATA/Public | /media/Media | TV, family movie folders, downloads, primary media |
| 192.168.1.102:/share/MD0_DATA/Public | /media/NAS | Additional movies at /media/NAS/Movies |

The guided fresh install offers these editable defaults and prepares both NFS
mounts before starting dependent programs. This is not authorization to mount or
inspect the production exports on the current test host. Physical experiments
continue only in 192.168.1.102:/share/MD0_DATA/Public/installarr at /media/installarr.
netboot assets default to /media/netbootxyz/assets on the local host unless the
operator selects an already connected different location.

The reference secondary movie path is shared with Radarr/Bazarr as writable and
Plex as read-only. The new secondary_media_read_only=false setting enables managed
writable preparation/markers, UID write probes, mount guards and the additional
Radarr API root. Default true retains earlier explicit read-only source behavior.
The normal fresh guide sets false, reproducing the reference app access pattern.


After successful guided installation, an ordinary yes/no prompt offers automatic
startup (suggested yes). Only the verified owned service and Docker/containerd are
enabled, after complete ready-state/identity checks. The current physical test
remains boot-disabled and has not been rebooted. Full clean-host/boot acceptance
is still pending. Normal setup does not require manual API-key copying between apps.
