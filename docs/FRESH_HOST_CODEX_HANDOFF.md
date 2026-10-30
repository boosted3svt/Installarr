# Codex after wiping the test machine

Run Codex directly in the SSH terminal. **Do not install or use tmux for this
workflow.** This is an operator test setup, not a prerequisite for using Installarr.

A clean OS installation that erases the home directory removes local Codex history
and authentication. Signing in alone does not recover erased history. The operator
now plans to back up the entire ~/.codex privately OFF this machine before wiping,
then restore it to /home/htpc/.codex, owned by htpc, with Codex/background server
stopped. That includes sessions and SQLite state, not just history.jsonl. It can
contain login credentials; never put the backup in Git. A live file copy of a
changing database is not a verified backup. Retain a separate off-machine copy.

After restoring, clone the published source to /home/htpc/Installarr and resume:

```sh
cd ~/Installarr
codex resume 01a1897b-0699-7b80-ae24-7badc34e2117
```

Tell Codex: "Ubuntu was reinstalled. Read CURRENT_PROGRESS.md, SAVED_CHECKPOINT.md
and CURRENT_SETUP.md; old host state is gone. Continue the fresh installer test."
Restoring conversation history does NOT restore the actual machine state. If no
usable history survives, start a new chat using the checkpoint prompt below.
The exact session ID avoids resuming an unrelated newer session with --last.

Current goal (2026-10-30): operator-led Ubuntu24.04.5/OpenSSH clean installation,
published source clone, no-flag installer launch and complete provisioning/API
acceptance. Last seven-app settings are documented in CURRENT_SETUP.md. App
databases, credentials, /var/lib/installarr* state and claimed Plex identity must
NOT be restored for this test. Fresh input/claim prompts are intentional. No wipe,
reboot, broad unmount, host networking redesign or media cleanup by Codex.

## 1. Install Codex as your normal Ubuntu administrator account

```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://chatgpt.com/codex/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
codex --version
codex login --device-auth
```

Complete the displayed device-code login in a browser on another computer or phone.
Device-code login may need enabling in your ChatGPT security/workspace settings.
Do not run Codex through sudo; grant the normal operator account sudo separately.

## 2. Optional operator-requested passwordless sudo

The operator explicitly requested unrestricted Codex execution and passwordless sudo
on the dedicated test machine. This grants that Ubuntu account passwordless root
commands; it does not expand the permitted production/NAS test scope. Run as the
normal Ubuntu user, not inside a root shell. Nothing here has been applied to the
old host merely by documenting these commands.

```sh
codex_sudoers_file=$(mktemp)
printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$(id -un)" > "$codex_sudoers_file"
sudo visudo -cf "$codex_sudoers_file" && sudo install -o root -g root -m 0440 "$codex_sudoers_file" /etc/sudoers.d/99-installarr-codex
rm "$codex_sudoers_file"
sudo -k
sudo -n whoami
```

The last command should print root without requesting a password. Codex's dangerous
flag disables its sandbox/approvals; the sudo rule provides the separate Linux root
access. To remove only this rule later, use
`sudo rm /etc/sudoers.d/99-installarr-codex`.

## 3. Clone the published project

```sh
cd ~
git clone https://github.com/boosted3svt/Installarr.git
```

If already cloned, use the existing checkout instead of cloning again.

## 4. Start Codex directly with fresh-machine context

```sh
codex --dangerously-bypass-approvals-and-sandbox -C "$HOME/Installarr" "Read AGENTS.md, README.md, docs/FRESH_HOST_CODEX_HANDOFF.md, docs/CURRENT_PROGRESS.md, docs/SAVED_CHECKPOINT.md and docs/INTERACTIVE_TEST_QUEUE.md. This machine has been wiped and Ubuntu freshly installed. Treat previous local files, credentials, containers and services as gone. Continue the fresh Installarr installation and boot acceptance test. Let Installarr perform provisioning instead of manually preinstalling Docker or NFS. Read CURRENT_SETUP.md for the last approved storage map and the separate isolated-export recipe here. Use only operator-selected sources and folders; do not silently substitute or inspect sibling shares. Prompt for credentials when needed. Ask before rebooting. Run directly in this terminal; do not use tmux."
```

Later, after a saved CLI session exists on this installation:

```sh
codex resume --last --dangerously-bypass-approvals-and-sandbox -C "$HOME/Installarr"
```

After a disconnect/reboot, inspect the actual host before repeating actions. After
another full wipe, restore backed-up history if available; otherwise start a new
chat with the checkpoint-reading command again.

## 5. Run the fresh installer

Use another SSH terminal when entering the installer's hidden credential prompts:

```sh
cd ~/Installarr
./installarr.sh
```

Codex can inspect state and fix installer code, but should let the installer perform
provisioning. The normal installer has no Codex dependency and needs no flags.
Credentials and optional family Discord IDs are prompted on each clean installation;
no credential exports, encrypted bundles, old app databases or files to transfer.

## Alternative isolated full-install test storage

CURRENT_SETUP.md records the last operator-selected real layout. If the operator
chooses an isolated test instead, override the wizard defaults with this recipe:

| Prompt | Test answer |
| --- | --- |
| Storage for primary media | nas |
| Folder for primary media | /media/Media/Installarr-Clean-Test/Primary |
| NAS address/shared folder for primary media | 192.168.1.102:/share/MD0_DATA/Public/installarr |
| Connect this NAS at this folder | /media/Media |
| Does this NAS need specific NFS connection ports? | yes; mount protocol udp, NFS2049, mount-service30000 |
| Finished/unfinished downloads folders | Accept proposed children under the test primary root |
| Use different storage for downloads? | no |
| Eight media folders | Accept standardized children under the test primary root |
| Also use additional movie storage? | yes |
| Storage for additional movies | nas |
| Folder for additional movies | /media/NAS/Installarr-Clean-Test/AdditionalMovies |
| NAS address/shared folder for additional movies | 192.168.1.102:/share/MD0_DATA/Public/installarr |
| Connect this NAS at this folder | /media/NAS |
| Does this NAS need specific NFS connection ports? | yes; udp,2049,30000 as above |
| Storage for network boot assets | local |
| Folder for network boot assets | /var/lib/installarr-test-assets |
| Is this folder on a separate mounted drive? | no (explicit OS-disk test assets) |

This uses the same approved isolated export at two local mounts with separate data
folders. The previous host used /media/installarr; that mount is not assumed to exist
on the new host. Verify actual source/target before writes. Production defaults
remain available for a separately authorized real deployment.

The current guide has explicit endpoint prompts; no manual JSON edit is required.
The 2026-10-29 fresh-host run confirmed that this NAS's RPC discovery port111
does not respond, although NFS2049 and mount-service30000 are reachable. Both
nfs-common and rpcbind were installed and local rpcbind was active. The isolated
export mounted immediately with explicit NFSv3 transport settings. A saved setup
can declare `nfs_transport` on each matching `kind: nfs` storage mount:
`{"port":2049,"mountport":30000,"mountproto":"udp","mountvers":3}`.
These are verified settings for this test NAS, not defaults to guess for other
servers. The installer retains TCP/hard NFS data semantics and persists these
endpoints. The guide uses ordinary RPC discovery unless explicit transport settings
are selected through those prompts or supplied in configuration. Preserve private input
stores and archive immutable operation checkpoints before changing an attempted
setup's storage map; never edit a checkpoint fingerprint to force reuse.

## Checkpoint interpretation after a wipe

- All nine apps, API links, shared authentication, full profiles and family roles
  passed combined acceptance on the old test installation; cold Plex library
  creation and217-test suites passed. These are historical evidence, not proof that
  the newly wiped host already has any prerequisites, mounts, users or services.
- Former /var/tmp, /var/lib and local Plex/Ombi database paths are gone. Do not try
  to start obsolete fixture units or recover their claimed identities.
- Remaining task: actual clean Ubuntu/systemd installation and coordinated boot
  acceptance. Do not replace this with more ordinary media-request/playback tests.
- Family usernames/roles and production NFS defaults ship in code. Personal Discord
  IDs and account credentials do not ship in Git; prompt for them again. The old
  operator left lenora8 blank and supplied rebel739/beanie08, but values are not
  available from this repository.
- Do not format disks or change SSH/VLAN/manual routes/unrelated firewall rules.
  Standard Docker bridge/NAT is authorized. Ask before rebooting.

Commands checked against installed Codex CLI0.165.0 and official documentation:
[Install](https://learn.chatgpt.com/docs/codex/cli),
[headless authentication](https://learn.chatgpt.com/docs/auth#login-on-headless-devices),
[CLI flags/resume](https://learn.chatgpt.com/docs/developer-commands?surface=cli),
[project context/history](https://learn.chatgpt.com/docs/projects).
