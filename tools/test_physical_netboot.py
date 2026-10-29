"""Unpublished official netboot frontend auth/runtime fixture; no DHCP/PXE changes."""
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.credentials import read_private_credentials
from installarr.lifecycle import command
from installarr.netboot import IMAGE, MENU_VERSION, VERSION, NetbootClient, NetbootHTTP, seed_admin


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-netboot-test-', dir='/var/tmp'))
    for name in ('config','assets'):
        (work/name).mkdir(mode=0o700)
        os.chown(work/name,911,1001)
    credentials = read_private_credentials('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json')
    seed_admin(work/'config',credentials)
    docker=['docker','--host','unix:///run/docker.sock']
    name='installarr-netboot-'+uuid.uuid4().hex[:8]
    network=name+'_web'
    command(docker+['network','create','--driver','bridge',network])
    print(json.dumps({'evidence':str(work),'container':name}),flush=True)
    container=None
    try:
        args=['run','--detach','--name',name,'--network',network,'--restart','no','--env','PUID=911','--env','PGID=1001',
              '--env','WEB_APP_PORT=3001','--env','NGINX_PORT=80','--env','MENU_VERSION='+MENU_VERSION,'--env','IPXE_SB_VERSION=v2.0.0']
        for role in ('config','assets'):
            args+=['--mount','type=bind,source='+str(work/role)+',target=/'+role+',bind-propagation=rprivate']
        container=command(docker+args+[IMAGE])
        client=NetbootClient(NetbootHTTP('unix:///run/docker.sock',container))
        first=wait_for(lambda:client.verify_admin(credentials),seconds=120)
        menu=work/'config/menus/menu.ipxe'
        assert menu.read_text().startswith('#!ipxe')
        assert [menu.stat().st_uid,menu.stat().st_gid]==[911,1001]
        # A real write/read/cleanup as the service identity, only in local fixture assets.
        command(docker+['exec','--user','911:1001',container,'/bin/sh','-c',
            'set -eu; f=/assets/.installarr-write-test; test ! -e "$f"; printf "installarr\\n" > "$f"; test "$(cat "$f")" = installarr; rm -- "$f"'])
        command(docker+['restart',container])
        second=wait_for(lambda:client.verify_admin(credentials),seconds=120)
        seed_admin(work/'config',credentials)
        result={'version':VERSION,'image':IMAGE,'menu_version':MENU_VERSION,'first':first,'after_restart':second,
                'menu_owner':[menu.stat().st_uid,menu.stat().st_gid],'service_uid_write':'passed','published_ports':0,
                'dhcp_pxe_client_tests':'out of scope'}
        (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2),flush=True)
    finally:
        if container:
            command(docker+['stop','--time','5',container]);command(docker+['rm',container])
        command(docker+['network','rm',network])


if __name__=='__main__':main()
