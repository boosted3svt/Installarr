"""Full pinned-profile acceptance on one unpublished disposable app at a time."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import app_client, wait_for
from installarr.credentials import read_private_credentials
from installarr.directories import prepare_directories
from installarr.profiles import ensure_profile, recommended_profiles
from installarr.reference import reference_controller, remove_owned, write_reference_bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', choices=('radarr', 'sonarr'), required=True)
    args = parser.parse_args()
    work = Path('/var/tmp/installarr-bazarr-test-' + ('d5rjwtr7' if args.app == 'radarr' else '478idkci'))
    cfg = json.loads((work / 'config.json').read_text())
    cfg.update(apps=[args.app], project_directory=str(work / 'profile-project'))
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    identifiers = recommended_profiles([args.app])[args.app]['available']
    prepare_directories(cfg, work / 'profile-directories')
    write_reference_bundle(cfg, published=False)
    controller = reference_controller(cfg, 'installarr-profiles-' + args.app, published=False)
    print(json.dumps({'app': args.app, 'evidence': str(work), 'fixture_profile_ids': identifiers}), flush=True)
    try:
        controller.reconcile()
        client = wait_for(lambda: app_client(cfg, controller, args.app))
        client.verify_admin(credentials)
        first = [ensure_profile(client, args.app, identifier) for identifier in identifiers]
        controller.stop()
        controller.reconcile()
        client = wait_for(lambda: app_client(cfg, controller, args.app))
        second = [ensure_profile(client, args.app, identifier) for identifier in identifiers]
        assert first == second
        result = {'app': args.app, 'first': first, 'after_restart_and_rerun': second,
                  'container_audit': controller.audit(controller.inventory())}
        (work / 'profile-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    finally:
        remove_owned(controller)
        controller.run(controller.docker + ['network', 'rm', controller.project + '_web'])


if __name__ == '__main__':
    main()
