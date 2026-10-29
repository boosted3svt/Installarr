"""Terminal navigation over the same unattended commands; no implicit deployment."""
import json
import os
from pathlib import Path
import re
import sys


def run_menu(config_path, name, state_directory, execute):
    if not sys.stdin.isatty():
        raise ValueError('The menu requires a terminal; use explicit commands for unattended execution')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,25}', name):
        raise ValueError('Invalid reference deployment name')
    config_path = Path(config_path)
    state_directory = Path(state_directory or '/var/lib/installarr-' + name)
    choices = {
        '1': 'Choose programs and media folders',
        '2': 'Review your choices',
        '3': 'Save your administrator login',
        '4': 'Save download, subtitle and NAS account details',
        '6': 'Connect your Plex account',
        '7': 'Install the selected programs',
        '8': 'Check your programs',
        '9': 'Choose a saved settings file (advanced)',
        '5': 'Prepare the computer and download programs',
        '0': 'Exit',
    }
    while True:
        print('\nInstallarr — configuration: {}\nDeployment: {}\nPrivate state: {}'.format(config_path, name, state_directory))
        for key in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'):
            print('{}  {}'.format(key, choices[key]))
        try:
            choice = input('Select an action: ').strip()
        except EOFError:
            return 0
        if choice == '0':
            return 0
        if choice == '9':
            value = input('Configuration file path: ').strip()
            if value:
                config_path = Path(value).expanduser().absolute()
            continue
        if choice not in choices:
            print('Choose one of the numbered actions.')
            continue
        if choice in ('3', '4', '6', '7', '8', '5') and os.geteuid() != 0:
            print('Run the menu with sudo for private credentials and provisioning; configuration and planning work without root.')
            continue
        try:
            if choice == '1':
                command = ['configure', '--config', str(config_path)]
            elif choice == '2':
                command = ['plan', '--config', str(config_path)]
            elif choice == '3':
                from .cli import validate
                from .execution import Execution
                config = validate(json.loads(config_path.read_text()))
                # The nested secrets directory needs its private state parent.
                # Don't freeze a new config yet; existing state still must match.
                with Execution(state_directory, {'operation': 'reference-apply-v1', 'config': config, 'name': name}):
                    pass
                command = ['init-secrets', '--secrets-directory', str(state_directory / 'secrets'), '--config', str(config_path)]
            elif choice in ('4', '6'):
                from .cli import validate
                config = validate(json.loads(config_path.read_text()))
                if choice == '4':
                    from .providers import required_secrets
                    names = sorted(required_secrets(config))
                    commands = []
                    if names:
                        target = Path(config.get('provider_secrets_file', ''))
                        if not target.is_absolute():
                            print('Set an absolute provider credential file path before collecting credentials.')
                            continue
                        commands.append(['init-provider-secrets', '--secrets-directory', str(target.parent),
                                         '--filename', target.name, '--providers', ','.join(names)])
                    smb_paths = sorted({mount['credentials_file'] for mount in config.get('storage_mounts', {}).values()
                                        if mount.get('kind') == 'smb'})
                    for value in smb_paths:
                        target = Path(value)
                        commands.append(['init-smb-secrets', '--secrets-directory', str(target.parent), '--filename', target.name])
                    if not commands:
                        print('No selected providers or storage mounts require credentials.')
                    for command in commands:
                        code = execute(command)
                        if code:
                            print('Credential action returned status {}. Existing stores are preserved.'.format(code))
                            break
                    continue
                else:
                    target = Path(config.get('plex_claim_file', ''))
                    if 'plex' not in config['apps'] or not target.is_absolute():
                        print('Select Plex and an absolute private claim file path before collecting a claim.')
                        continue
                    command = ['init-plex-claim', '--secrets-directory', str(target.parent), '--filename', target.name, '--replace']
            elif choice in ('7', '5'):
                # Validate/preview first; a failed plan must never reach apply.
                if execute(['plan', '--config', str(config_path)]) != 0:
                    print('Resolve the plan errors before applying.')
                    continue
                command = ['apply', '--reference', '--config', str(config_path), '--name', name,
                           '--state-directory', str(state_directory)]
                if choice == '5':
                    command.append('--prepare-only')
            else:
                command = ['service-status', '--name', name]
            code = execute(command)
            if code:
                print('Action returned status {}. Saved configuration and checkpoints remain available.'.format(code))
        except (OSError, ValueError, TypeError):
            print('Action could not start: check the configuration file and private paths.')
