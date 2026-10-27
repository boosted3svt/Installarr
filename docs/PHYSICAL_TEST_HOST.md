# Physical test host and local Codex

This is a dedicated physical Ubuntu server, not a VM. It has OpenSSH and an isolated
VLAN allowing NAS and Internet access. The operator supplies isolated NAS storage.
No production test run is needed. Read AGENTS.md for implementation requirements.

## NFS prerequisite

On fresh Ubuntu, install the NFS client helper before mounting NFS:

```sh
sudo apt update
sudo apt install -y nfs-common
sudo mkdir -p /media/installarr
sudo mount -v /media/installarr
findmnt /media/installarr
```

The mount command assumes the operator has already added the test entry to fstab.
Never append duplicate entries. The current installer only lists required packages;
automatic installation is not implemented yet. Even reused NFS mounts require
nfs-common in the host plan. SMB uses cifs-utils instead.

## Bootstrap local Codex CLI

Install prerequisites as the normal administrator:

```sh
sudo apt update
sudo apt install -y ca-certificates curl git python3 tmux
curl -fsSL https://chatgpt.com/codex/install.sh -o /tmp/codex-install.sh
less /tmp/codex-install.sh
sh /tmp/codex-install.sh
```

Follow the installer's PATH instructions, reconnect SSH if needed, then:

```sh
codex --version
codex login --device-auth
```

Open the displayed authorization URL on another device and authenticate. Never
paste the login code, credential files or tokens into Git/chat. Device authorization
may need to be enabled in your account settings; follow the CLI's instructions.

Clone the repository, or pull main in the existing checkout. Private GitHub repository
authentication is separate from Codex login; use your normal GitHub access method.

```sh
git clone https://github.com/boosted3svt/Installarr.git
cd Installarr
tmux new -s installarr
codex
```

Start with normal permissions and give the agent this task:

> Read AGENTS.md and docs/PHYSICAL_TEST_HOST.md. Continue implementing the usable
> installer on this dedicated test machine. First inspect the host and confirm the
> isolated test mount. Run commands yourself, implement and test host preparation,
> then Docker and application adapters. Record results and blockers. Do not touch
> production or storage outside the test subtree. Do not format disks or change SSH,
> firewall, DHCP or networking. Ask before rebooting. Use sudo only within that scope.

Codex is a separate local session; it does not inherit the cloud chat. It can run
commands directly. Permission approvals and sudo may still require operator input.
For unattended host-level testing, after confirming the machine and storage scope,
an explicit opt-in is `codex --dangerously-bypass-approvals-and-sandbox`. This disables
Codex's sandbox and approval prompts; it does not grant Linux root privileges or
bypass sudo passwords. Do not use it on production. Choose a suitable administrative
access policy separately rather than casually granting passwordless sudo.

tmux keeps the terminal session alive if SSH disconnects, but not across reboot.
Reconnect using `tmux attach -t installarr`; after reboot use `codex resume` from
the checkout. Codex is not installed as a boot daemon by these instructions.

Official sources: https://github.com/openai/codex and
https://developers.openai.com/codex/cli/ . Commands were checked against the official
repository on 2026-10-27; use `codex --help` and `codex login --help` for installed-version details.
