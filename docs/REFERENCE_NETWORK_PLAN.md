# Reference Docker network transition — operator approved 2026-10-28

The supplied reference uses a standard Docker bridge named `web` and published
application ports. The earlier test instructions prohibited host network/firewall
configuration changes, and the operator has now explicitly approved the Docker NAT/firewall/network
changes described below. Sudo access is already available.

Pre-transition verified state (historical):

- docker.service, docker.socket and containerd.service are masked/inactive.
- The isolated installarr-test-docker.service is active, with zero containers.
- Standard /run/docker.sock, /etc/docker/daemon.json and /var/lib/docker are absent.
- Original host link/address/route/forwarding/firewall fingerprints are recorded.

Approved transition executed on this dedicated physical test host:

1. Verify the isolated daemon still has no workloads and standard Docker still has
   no pre-existing socket/config/data. Preserve/refuse unexpected operator changes.
2. Stop the isolated test daemon; retain its images, local data and disabled test
   units. Do not migrate/delete data or start a second full application stack.
3. Unmask/start the already-installed official Docker/containerd services using
   standard defaults. Leave automatic boot enablement disabled pending reboot work.
4. Allow Docker to create its normal docker0 bridge, forwarding/NAT/firewall rules,
   and one owned standard bridge network for reference testing. This is the
   intentional change from the earlier no-network-change test policy.
5. Validate only that owned bridge using a disposable reference-app image with an
   overridden diagnostic command: Docker DNS and public registry HTTPS. No app GUI
   or application server is started for this network prerequisite test.
6. For later reference-app tests, publish only the reference ports at the configured
   host address after GUI authentication is configured and verified. Start only
   minimal disposable pairs until all adapters are validated.
7. Record the exact Docker-created changes. Never flush/replace unrelated firewall
   rules or edit host IPs, DNS, routes, SSH, VLAN or disks. Do not reboot.

If an unexpected existing workload/configuration is found, refuse and preserve it.
This proposal does not add a proxy, Samba server, tunnel or other auxiliary service.
The normal installer will follow the supplied reference container topology.

Current: standard Docker/containerd active, boot-disabled; isolated daemon stopped.
DNS and outbound registry HTTPS passed; authenticated Radarr/SAB reference pair
is live. See CURRENT_PROGRESS.md and TEST_RESULTS.md. Operator subsequently
requested HTTP GUI ports only; omit optional HTTPS listeners and app SSL setup.
