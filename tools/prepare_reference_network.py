"""Explicit approved standard Docker transition; see docs/REFERENCE_NETWORK_PLAN.md."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.network import prepare_standard_docker

if __name__ == '__main__':
    if sys.argv[1:] != ['--operator-approved']:
        raise SystemExit('Requires explicit operator approval of docs/REFERENCE_NETWORK_PLAN.md')
    print(json.dumps(prepare_standard_docker(), indent=2))
