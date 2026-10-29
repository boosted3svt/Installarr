# Codex after wiping the test machine

Run Codex directly in the SSH terminal. **Do not install or use tmux for this
workflow.** This is an operator test setup, not a prerequisite for using Installarr.

A clean OS installation removes local Codex history and authentication. Start a new
Codex chat using the published project checkpoints; this does not restore the full
erased transcript. `codex resume --last` is for later sessions on the same surviving
installation, not the first launch after a wipe.

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
codex --dangerously-bypass-approvals-and-sandbox -C "$HOME/Installarr" "Read AGENTS.md, README.md, docs/FRESH_HOST_CODEX_HANDOFF.md, docs/CURRENT_PROGRESS.md, docs/SAVED_CHECKPOINT.md and docs/INTERACTIVE_TEST_QUEUE.md. This machine has been wiped and Ubuntu freshly installed. Treat previous local files, credentials, containers and services as gone. Continue the fresh Installarr installation and boot acceptance test. Let Installarr perform provisioning instead of manually preinstalling Docker or NFS. Use only the isolated NAS test export 192.168.1.102:/share/MD0_DATA/Public/installarr; do not access production shares. Prompt for credentials when needed. Ask before rebooting. Run directly in this terminal; do not use tmux."
```

Later, after a saved CLI session exists on this installation:

```sh
codex resume --last --dangerously-bypass-approvals-and-sandbox -C "$HOME/Installarr"
```

After a disconnect/reboot, inspect the actual host before repeating actions. After
another full wipe, start a new chat with the checkpoint-reading command again.

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

## Isolated full-install test storage

The wizard offers production NFS defaults. Override them for this test:

| Prompt | Test answer |
| --- | --- |
| Folder for media and downloads | /media/Media/Installarr-Clean-Test/Primary |
| First NAS already connected? | no |
| First NAS address/shared folder | 192.168.1.102:/share/MD0_DATA/Public/installarr |
| First NAS mount folder | /media/Media |
| Use additional movie folder? | yes |
| Additional movie folder | /media/NAS/Installarr-Clean-Test/AdditionalMovies |
| Second NAS already connected? | no |
| Second NAS address/shared folder | 192.168.1.102:/share/MD0_DATA/Public/installarr |
| Second NAS mount folder | /media/NAS |

This uses the same approved isolated export at two local mounts with separate data
folders. The previous host used /media/installarr; that mount is not assumed to exist
on the new host. Verify actual source/target before writes. Production defaults
remain available for a separately authorized real deployment.

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
