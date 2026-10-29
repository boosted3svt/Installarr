"""Actual pseudo-terminal menu navigation, with no provisioning or credentials."""
import argparse
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials', action='store_true', help='Use only synthetic hidden inputs; requires root')
    args = parser.parse_args()
    if args.credentials and os.geteuid() != 0:
        raise ValueError('Synthetic private menu acceptance requires root')
    source = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(source))
    sys.path.insert(0, str(source / 'tests'))
    from test_compose import compose_configuration
    work = Path(tempfile.mkdtemp(prefix='installarr-menu-terminal-', dir='/var/tmp'))
    config = compose_configuration()
    config['apps'] = ['sabnzbd']
    path = work / 'config.json'
    path.write_text(json.dumps(config, indent=2) + '\n'); path.chmod(0o600)
    before = path.read_bytes()
    master, slave = pty.openpty()
    process = subprocess.Popen([sys.executable, '-B', '-m', 'installarr', 'menu', '--config', str(path), '--name', 'menu-preview', '--state-directory', str(work / 'state')],
                               stdin=slave, stdout=slave, stderr=slave, cwd=str(source), close_fds=True)
    os.close(slave)
    output = bytearray()
    sent = False
    phase = 0
    synthetic_password = b'Synthetic-only-menu-pass-734'
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                output.extend(chunk)
                if not args.credentials and not sent and b'Select an action:' in output:
                    os.write(master, b'2\n0\n'); sent = True
                elif args.credentials:
                    if phase == 0 and b'Select an action:' in chunk:
                        os.write(master, b'3\n'); phase = 1; sent = True
                    elif phase == 1 and b'Shared GUI administrator username:' in chunk:
                        os.write(master, b'menu-synthetic-admin\n'); phase = 2
                    elif phase == 2 and b'Shared GUI administrator password:' in chunk:
                        os.write(master, synthetic_password + b'\n'); phase = 3
                    elif phase == 3 and b'Select an action:' in chunk:
                        os.write(master, b'0\n'); phase = 4
            if process.poll() is not None:
                break
        process.wait(timeout=3)
    finally:
        if process.poll() is None:
            process.kill(); process.wait()
        os.close(master)
    text = output.decode(errors='replace')
    (work / 'transcript.txt').write_text(text)
    assert process.returncode == 0 and sent
    if args.credentials:
        from installarr.credentials import read_private_credentials
        assert phase == 4 and synthetic_password not in output
        target = work / 'state/secrets/gui-admin.json'
        assert read_private_credentials(target)['password'].encode() == synthetic_password
        assert (work / 'state').stat().st_mode & 0o777 == 0o700
        assert not (work / 'state/state.json').exists(), 'Credential collection froze a new deployment config'
    else:
        assert 'preview only; no system changes' in text
    assert text.count('Select an action:') >= 2
    assert path.read_bytes() == before
    result = {'status': 'passed', 'terminal': 'real PTY', 'actions': ['synthetic hidden GUI collection', 'exit'] if args.credentials else ['plan', 'exit'],
              'configuration': 'unchanged', 'host_mutations': 'private fixture files only' if args.credentials else 'none', 'evidence': str(work)}
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
