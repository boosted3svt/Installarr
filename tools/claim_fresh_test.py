#!/usr/bin/env python3
"""Private browser authorization for the already prepared acceptance fixture."""
import getpass
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.credentials import read_private_json
from installarr.plex import store_claim

if os.geteuid() != 0 or not sys.stdin.isatty():
    raise SystemExit('Run sudo ./tools/claim_fresh_test.py from your terminal.')
try:
    prepared = read_private_json('/var/tmp/installarr-prepared-fresh-test-v2.json')
    print('Open https://www.plex.tv/claim and sign in with your own Plex account.')
    print('The code below authorizes the new Installarr Fresh Acceptance server.')
    store_claim(Path(prepared['claim_store']), lambda: getpass.getpass('Fresh Plex claim (hidden): '), replace=True)
    print('Claim saved privately. Reply "claim saved" to continue. Do not paste the code in chat.')
except (OSError, ValueError, EOFError, KeyboardInterrupt):
    raise SystemExit('The claim was not saved. Run this command again with a fresh code.')
