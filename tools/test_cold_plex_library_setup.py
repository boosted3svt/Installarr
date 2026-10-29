"""Cold empty Plex database, sequential reuse of the owned test identity; no browser input."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installarr.apply import wait_for
from installarr.credentials import read_private_json
from installarr.plex import IMAGE, PREFERENCES, PlexClient, PlexHTTP, configure_server
from installarr.lifecycle import command


def main():
    prepared = read_private_json('/var/tmp/installarr-prepared-fresh-test-v2.json')
    config = read_private_json(prepared['config'])
    unit = 'installarr-' + prepared['name'] + '.service'
    work = Path(tempfile.mkdtemp(prefix='installarr-cold-plex-', dir='/var/tmp'))
    source = Path(config['storage']['configs']) / 'plex' / PREFERENCES
    root = work / 'config'; root.mkdir(); os.chown(root, 2000, 2000)
    target = root / PREFERENCES; target.parent.mkdir(parents=True)
    for p in [root] + list(target.parents)[:3]:
        if p == work: break
        os.chown(p, 2000, 2000)
    shutil.copyfile(source, target); os.chown(target,2000,2000);target.chmod(0o600)
    name = 'installarr-cold-plex-' + work.name.rsplit('-',1)[1]
    docker = ['docker','--host','unix:///run/docker.sock']
    print(json.dumps({'evidence':str(work),'identity_policy':'source service stopped; never concurrent same identity'}),flush=True)
    subprocess.run(['systemctl','stop',unit],check=True,timeout=60)
    try:
        token=ET.parse(target).getroot().get('PlexOnlineToken','')
        cid=command(docker+['run','--detach','--name',name,'--restart','no','--network','installarr-'+prepared['name']+'_web',
            '--env','PLEX_UID=2000','--env','PLEX_GID=2000','--env','CHANGE_CONFIG_DIR_OWNERSHIP=false',
            '--mount','type=bind,source='+str(root)+',target=/config',
            '--mount','type=bind,source='+config['data_root']+',target=/data,readonly',
            '--mount','type=bind,source='+config['storage']['media_secondary']+',target=/media-secondary,readonly',IMAGE])
        client=PlexClient(PlexHTTP('unix:///run/docker.sock',cid,api_key=token))
        wait_for(client.status)
        wait_for(client.verify_authorization)
        original=client.transport.request
        responses=[]
        def observe(method,path,**kwargs):
            result=original(method,path,**kwargs)
            if method=='POST' and path=='/library/sections':
                query=dict(kwargs.get('query') or [])
                reason='invalid_language' if result[1].strip()=="'language' is invalid" else ('accepted' if result[0]in(200,201)else'other_validation_error')
                responses.append({'library':query.get('name'),'language':query.get('language'),'status':result[0],'reason':reason})
                if result[0] == 400:
                    hint = re.sub(r'[A-Za-z0-9_-]{16,}', '[REDACTED]', result[1])
                    hint = re.sub(r'[^\s<>]+@[^\s<>]+', '[EMAIL]', hint)
                    print('Validation detail: ' + hint[:400], flush=True)
                print(json.dumps(responses[-1]),flush=True)
            return result
        client.transport.request=observe
        result=configure_server(client,config)
        (work/'result.json').write_text(json.dumps({'status':'passed','libraries':result,'posts':responses,'empty_database':True},indent=2)+'\n')
        print('Cold library setup passed',flush=True)
    finally:
        subprocess.run(docker+['rm','--force',name],capture_output=True,timeout=30)
        subprocess.run(['systemctl','start',unit],check=True,timeout=60)


if __name__=='__main__':main()
