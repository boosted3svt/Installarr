"""Apply the operator's final library exclusions and matching folder names."""
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from installarr.cli import save_config
from installarr.directories import prepare_directories
from installarr.lifecycle import command
from installarr.plex import PREFERENCES,PlexClient,PlexHostHTTP,reference_libraries
from installarr.reference import apply_reference


def main():
    previous=Path('/var/tmp/installarr-plex-grouped-2qnbn8su')
    work=Path(tempfile.mkdtemp(prefix='installarr-plex-standard-',dir='/var/tmp'))
    cfg=json.loads((previous/'config.json').read_text())
    cfg.update(plex_libraries=reference_libraries(),project_directory=str(work/'project'))
    save_config(work/'config.json',cfg)
    prepare_directories(cfg,work/'directories')
    prefs=ET.parse(str(Path(cfg['storage']['configs'])/'plex'/PREFERENCES)).getroot()
    client=PlexClient(PlexHostHTTP(cfg['bind_address'],32400,prefs.get('PlexOnlineToken')))
    client.verify_authorization()
    rows={row.get('title'):row for row in client.xml('/library/sections')}
    recorded=json.loads((previous/'result.json').read_text())['apply']['applications']['plex']['configuration']['libraries']
    saved={item['name']:item for item in recorded}
    for old,new,path in [('Sports','sports','/data/sports'),('StandUp','StandUp','/data/StandUp')]:
        row=rows[old]
        assert row.get('key')==saved[old]['id']
        assert [loc.get('path') for loc in row.findall('Location')]==saved[old]['paths']
        code,_=client.transport.request('PUT','/library/sections/'+row.get('key'),
            query={'name':new,'agent':row.get('agent'),'location':path})
        assert code in (200,201)
    print(json.dumps({'evidence':str(work),'libraries':len(cfg['plex_libraries'])}),flush=True)
    ready=False
    command(['systemctl','stop','installarr-plex-grouped-test.service'])
    try:
        result=apply_reference(cfg,'plex-standard-test',work/'state',credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        ready=True
        (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'unit':result['unit'],'configuration':result['applications']['plex']['configuration']},indent=2),flush=True)
    finally:
        if not ready:command(['systemctl','start','installarr-plex-grouped-test.service'])


if __name__=='__main__':main()
