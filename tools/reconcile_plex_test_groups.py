"""Correct only installer-created test library metadata to operator-supplied groups.

No media file API is called. Plex's entire NAS bind stays read-only. Ordinary
apply never deletes libraries or removes existing folder locations.
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from installarr.cli import save_config
from installarr.directories import prepare_directories
from installarr.lifecycle import command
from installarr.plex import PREFERENCES, PlexClient, PlexHostHTTP, library_paths, reference_libraries
from installarr.reference import apply_reference
import xml.etree.ElementTree as ET


def main():
    previous=Path('/var/tmp/installarr-plex-libraries-m6m4j4kb')
    work=Path(tempfile.mkdtemp(prefix='installarr-plex-grouped-',dir='/var/tmp'))
    cfg=json.loads((previous/'config.json').read_text())
    cfg.update(plex_libraries=reference_libraries(),project_directory=str(work/'project'))
    save_config(work/'config.json',cfg)
    print(json.dumps({'evidence':str(work),'libraries':len(cfg['plex_libraries'])}),flush=True)
    prepare_directories(cfg,work/'directories')
    prefs=ET.parse(str(Path(cfg['storage']['configs'])/'plex'/PREFERENCES)).getroot()
    client=PlexClient(PlexHostHTTP(cfg['bind_address'],32400,prefs.get('PlexOnlineToken')))
    client.verify_authorization()
    old=json.loads((previous/'result.json').read_text())['applications']['plex']['configuration']['libraries']
    old_by_name={item['name']:item for item in old}
    current={row.get('title'):row for row in client.xml('/library/sections').findall('Directory')}
    desired=library_paths(cfg)
    # Refuse operator path/ID changes before modifying any known test metadata.
    for item in old:
        row=current.get(item['name'])
        expected=item.get('paths',[item.get('path')])
        if row is None or row.get('key')!=item['id'] or sorted(loc.get('path') for loc in row.findall('Location'))!=sorted(expected):
            raise ValueError('Test library changed outside recorded fixture; preserved')
    for item in desired:
        row=current[item['name']]
        locations=item['container_paths']
        if sorted(loc.get('path') for loc in row.findall('Location'))!=sorted(locations):
            code,_=client.transport.request('PUT','/library/sections/'+row.get('key'),query=
                [('agent',row.get('agent'))]+[('location',path) for path in locations])
            assert code in (200,201)
        saved=next(r for r in client.xml('/library/sections') if r.get('key')==row.get('key'))
        assert sorted(loc.get('path') for loc in saved.findall('Location'))==sorted(locations)
    # The parent library folder sets have read back successfully before removing
    # the six extra test sections introduced by the earlier incorrect mapping.
    keep={item['name'] for item in desired}
    removed=[]
    for name in ('Lenora Movies','Lenora TV','Jeremy Movies','Jeremy TV','Low Resolution TV','Low Resolution Movies'):
        assert name not in keep
        item=old_by_name[name]
        code,_=client.transport.request('DELETE','/library/sections/'+item['id'])
        assert code in (200,204)
        removed.append({'name':name,'id':item['id']})
    assert {row.get('title') for row in client.xml('/library/sections')}==keep
    ready=False
    command(['systemctl','stop','installarr-plex-libraries-test.service'])
    try:
        result=apply_reference(cfg,'plex-grouped-test',work/'state',credentials_file=Path('/var/tmp/installarr-reference-poc-fz5b_65a/http-state/secrets/gui-admin.json'))
        ready=True
        (work/'result.json').write_text(json.dumps({'apply':result,'removed_test_sections':removed},indent=2)+'\n')
        print(json.dumps({'unit':result['unit'],'configuration':result['applications']['plex']['configuration'],'removed_test_sections':removed},indent=2),flush=True)
    finally:
        if not ready:command(['systemctl','start','installarr-plex-libraries-test.service'])


if __name__=='__main__':main()
