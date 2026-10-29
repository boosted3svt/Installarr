"""Real fresh-rootfs provisioning adapters; no host engine/NAS/secrets exposed.

This is foundation/package/mask/account/directory/render acceptance, not a full
OS/systemd/engine/boot or app startup test. Only a new owned local fixture is RW.
"""
import hashlib
import json
import shutil
from pathlib import Path
import subprocess
import tempfile


def main():
    source = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(prefix='installarr-fresh-userspace-', dir='/var/tmp'))
    snapshot = work / 'source'
    shutil.copytree(source / 'installarr', snapshot, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    docker = ['docker', '--host', 'unix:///run/docker.sock']
    identity_hashes = {str(path): hashlib.sha256(path.read_bytes()).digest() for path in (Path('/etc/passwd'), Path('/etc/group'))}
    print(json.dumps({'evidence': str(work)}), flush=True)
    for release in ('20.04', '24.04'):
        output = work / release
        output.mkdir(mode=0o700)
        image = json.loads(subprocess.check_output(docker + ['image', 'inspect', 'ubuntu:' + release], text=True))[0]['RepoDigests'][0]
        script = r'''set -eu
export DEBIAN_FRONTEND=noninteractive
printf '#!/bin/sh\nexit 101\n' >/usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
apt-get update -qq
apt-get install -y -qq --no-install-recommends python3 tzdata util-linux passwd systemd >/dev/null
mkdir -p /etc/systemd/system
for unit in rpcbind.service rpcbind.socket rpc-statd.service; do ln -s /dev/null /etc/systemd/system/$unit; done
mkdir -m 700 /tmp/installarr-state
cd /workspace
python3 -B - <<'INNER'
import copy,json,os,pwd,grp,subprocess
from pathlib import Path
from installarr.accounts import prepare_accounts
from installarr.cli import identity_conflicts,validate
from installarr.compose import IMAGES
from installarr.credentials import initialize_credentials
from installarr.directories import observed_mount,prepare_directories
from installarr.dockerhost import prepare_docker,PACKAGES,installed_version
from installarr.hostplan import preparation_plan
from installarr.lifecycle import health_spec
from installarr.plex import reference_libraries,store_claim
from installarr.profiles import recommended_profiles,Catalog
from installarr.prerequisites import prepare_prerequisites
from installarr.provider_secrets import initialize_provider_secrets
from installarr.reference import write_reference_bundle
from installarr.smb_secrets import initialize_smb_secrets
root=Path('/fixture');state=root/'state';state.mkdir(mode=0o700)
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
try: observed=observed_mount(fd)
finally: os.close(fd)
assert observed['fstype'] in ('ext4','xfs','btrfs'), 'Fixture must be a real local host bind, not overlay'
check={'mountpoint':observed['target'],'source':observed['source'],'fstype':observed['fstype'],'sentinel':'ready'}
config={'schema_version':1,'apps':list(IMAGES),'timezone':'America/Chicago','bind_address':'127.0.0.1',
'plex_allowed_networks':'192.168.0.0/23','hostname':'installarr-fresh-fixture','plex_server_name':'Fresh Foundation Fixture',
'service_user':{'name':'media','uid':2000,'gid':2000},'project_directory':str(root/'project'),
'data_root':str(root/'data'),'storage':{'media':str(root/'data'),'downloads':str(root/'data/downloads'),
'incomplete':str(root/'data/incomplete-downloads'),'configs':str(root/'configs'),'backups':str(root/'backups'),
'netboot_assets':str(root/'netboot-assets')},'quality_profiles':recommended_profiles(['radarr','sonarr']),
'plex_libraries':reference_libraries(),'ombi_family_presets':True}
config['storage_mounts']={purpose:{'kind':'local'} for purpose in config['storage']}
config['storage_checks']={purpose:dict(check) for purpose in ('media','downloads','incomplete','netboot_assets')}
validate(config)
# Actual account commands alter only the disposable container's account files.
accounts=prepare_accounts(config,state/'accounts',identity_conflicts)
again=prepare_accounts(config,state/'accounts',identity_conflicts)
assert pwd.getpwnam('media').pw_uid==2000 and pwd.getpwnam('media').pw_gid==2000
assert pwd.getpwnam('nbxyz').pw_uid==911 and grp.getgrnam('nbxyz').gr_gid==1001
# Select an asserted NFS map ONLY to install its client prerequisite; never mount.
prerequisite=copy.deepcopy(config);prerequisite.pop('data_root')
for purpose in ('media','downloads','incomplete'):
    prerequisite['storage_mounts'][purpose]={'kind':'existing','mountpoint':'/fixture/data','source':'fixture.invalid:/approved',
                                           'fstype':'nfs','sentinel':'ready'}
    prerequisite['storage_checks'].pop(purpose,None)
packages=prepare_prerequisites(prerequisite,state/'prerequisites')
assert installed_version('nfs-common') and installed_version('openssl')
# Run the real signed staging adapter, including genuine systemd masks and
# official package installation. PID1 is not systemd; no engine is started.
docker_first=prepare_docker(state/'docker')
docker_second=prepare_docker(state/'docker')
assert docker_first['package_versions']==docker_second['package_versions']
assert not Path('/run/docker.sock').exists()
for unit in ('docker.service','docker.socket','containerd.service'):
    assert os.readlink('/etc/systemd/system/'+unit)=='/dev/null'
versions={name:installed_version(name) for name in PACKAGES}
assert versions==docker_first['package_versions']
(root/'staging-acceptance.json').write_text(json.dumps({'accounts':'created/rerun','versions':versions,'masks':'preserved; no socket','prerequisites':packages},indent=2)+'\n')
directories=prepare_directories(config,state/'directories')
rerun=prepare_directories(config,state/'directories')
assert all(row.get('read_verified') or row.get('write_verified') or row.get('note') for row in directories['directories'])
assert all(row['created_components']==0 for row in rerun['directories'])
assert (root/'configs/netbootxyz').stat().st_uid==911
assert (root/'netboot-assets').stat().st_uid==911
assert (root/'configs/radarr').stat().st_uid==2000
secrets=state/'secrets'
initialize_credentials(secrets,lambda:{'username':'synthetic-admin','password':'synthetic-gui-pass'})
initialize_provider_secrets(secrets,['nzbgeek'],lambda name:{'api_key':'a'*32})
initialize_smb_secrets(secrets,lambda:{'username':'synthetic-smb','password':'synthetic-smb-pass'})
store_claim(secrets,lambda:'claim-abcdefghijklmnop')
bundle=write_reference_bundle(config,published=False)
assert set(bundle['compose']['services'])==set(IMAGES)
assert all('ports' not in service for service in bundle['compose']['services'].values())
assert len(Catalog().documents)==625
result={'accounts':'actual create/rerun; media2000 and nbxyz911:1001',
'prerequisites':packages,'docker_versions':versions,'docker_masks':'all preserved; no socket',
'directory_identity_writes':'actual UID2000/911 fsync/readback; rerun created0',
'local_fixture_filesystem':observed['fstype'],'credential_collectors':'all four share private folder; synthetic only',
'compose':'all nine selected services, unpublished, no apps started',
'scope':'fresh userspace foundation only; full engine/systemd/boot/app acceptance remains queued'}
(root/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
INNER
'''
        with (output / 'provision.log').open('w') as log:
            result = subprocess.run(docker + ['run', '--rm', '--network', 'bridge', '--cap-drop', 'NET_RAW',
                '--mount', 'type=bind,source=' + str(snapshot) + ',target=/workspace/installarr,readonly',
                '--mount', 'type=bind,source=' + str(output) + ',target=/fixture', image, '/bin/sh', '-c', script],
                stdout=log, stderr=subprocess.STDOUT, timeout=1500)
        metadata = {'release': release, 'image': image, 'status': result.returncode,
                    'scope': 'real fresh-rootfs adapters; no host engine/systemd/NAS/credentials exposed'}
        (output / 'result.json').write_text(json.dumps(metadata, indent=2) + '\n')
        print(json.dumps(metadata), flush=True)
        if result.returncode:
            raise SystemExit('Fresh userspace foundation failed; retained log has evidence')
    assert all(hashlib.sha256(Path(name).read_bytes()).digest()==value for name,value in identity_hashes.items())
    (work / 'host-account-files.json').write_text(json.dumps({'passwd_group':'unchanged','hashes':'not recorded'})+'\n')


if __name__ == '__main__':
    main()
