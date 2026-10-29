# Saved checkpoint — published guided installer

**After a wipe:** this document's old local service/database paths are historical,
not resources to restore. Read [FRESH_HOST_CODEX_HANDOFF.md](FRESH_HOST_CODEX_HANDOFF.md)
for a new direct Codex session, credential prompts and isolated test settings.
The operator explicitly requires no tmux involvement. Continue fresh-install/boot
acceptance from the published notes; do not assume the old host state survived.

Authoritative resume: [CURRENT_PROGRESS.md](CURRENT_PROGRESS.md).

The operator-owned [boosted3svt/Installarr](https://github.com/boosted3svt/Installarr)
main now contains the guided implementation. Initial publication commit:
bc9017a4eec41b8bd514901b0067accbdfffdd2c. Fresh public clone, launcher and217tests
passed. Source/private-value review passed; reference Compose and private stores
were not published. Each clean installation prompts for needed credentials and
optional Discord IDs. No saved file, encrypted bundle or manual transfer is part
of the intended flow.

All9apps are running in installarr-freshcheck-aaabe264-v2.service (boot-disabled).
Config/state/result/live snapshot are under
/var/tmp/installarr-fresh-acceptance-vhydzwl1: config-v2.json, state-v2, result.json,
live-checkpoint.json. Bootstrap and the previous3test services are stopped; do not
start them alongside the new stack because of port conflicts. Current root runtime
integrity and source match. No fixture command remains running. No reboot performed.

Fresh Ubuntu/systemd and boot acceptance still need an approved clean target and
reboot coordination. Ordinary application actions and disaster recovery are outside
this fresh-installer goal. Production NFS defaults are in the guide, but current
physical writes remain restricted to the approved /media/installarr test export.
See INTERACTIVE_TEST_QUEUE.md for those remaining actions and TEST_RESULTS.md for
exact commands, evidence and failed attempts fixed during combined acceptance.
