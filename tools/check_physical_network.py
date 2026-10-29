"""Read-only comparison with the pre-Docker physical-test network fingerprints."""
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    baseline = json.loads(Path('/var/lib/installarr-physical-network-baseline.json').read_text())
    commands = {
        'links': [['ip', '-j', 'link']],
        'addresses': [['ip', '-j', 'address']],
        'routes': [['ip', '-j', 'route', 'show', 'table', 'all']],
        'ipv4_forwarding': [['cat', '/proc/sys/net/ipv4/ip_forward']],
        'ipv6_forwarding': [['cat', '/proc/sys/net/ipv6/conf/all/forwarding']],
        'iptables': [['iptables-save']], 'ip6tables': [['ip6tables-save']],
    }
    result = {}
    for label, candidates in commands.items():
        match = None
        for args in candidates:
            completed = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
            content = completed.stdout.strip()
            if label in ('iptables', 'ip6tables'):
                content = '\n'.join(line for line in content.splitlines() if not line.startswith('#')).strip()
            digest = hashlib.sha256(content.encode()).hexdigest()
            if completed.returncode == baseline[label]['exit'] and digest == baseline[label]['sha256']:
                match = args
                break
        result[label] = {'unchanged': match is not None, 'matching_read_command': match}
    print(json.dumps(result, indent=2))
    if not all(item['unchanged'] for item in result.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
