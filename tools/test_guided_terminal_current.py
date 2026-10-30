"""Actual plain-language wizard/save-only PTY; never prepare/apply or write NAS."""
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
    work=Path(tempfile.mkdtemp(prefix='installarr-guided-preview-',dir='/var/tmp'))
    base=work/'setup'
    master,slave=pty.openpty()
    script='from pathlib import Path;from installarr.guided import run_setup;raise SystemExit(run_setup(Path('+repr(str(base))+')))'
    process=subprocess.Popen([sys.executable,'-u','-B','-c',script],stdin=slave,stdout=slave,stderr=slave)
    os.close(slave)
    answers=([''] + ['']*9
             + ['local', str(work/'media'), '', '', '', '']
             + ['']*8 + ['', '', '']
             + ['yes', 'local', str(work/'secondary'), '']
             + ['local', str(work/'netboot-assets'), '']
             + ['', '', '', '', '', '', 'no'])
    os.write(master, ('\n'.join(answers)+'\n').encode())
    output=bytearray();deadline=time.monotonic()+30
    try:
        while time.monotonic()<deadline:
            if select.select([master],[],[],0.1)[0]:
                try:data=os.read(master,65536)
                except OSError:break
                if not data:break
                output.extend(data)
            if process.poll()is not None:
                break
        status=process.wait(timeout=2)
    finally:
        if process.poll()is None:process.kill();process.wait(timeout=2)
        os.close(master)
    (work/'transcript.txt').write_bytes(output)
    assert status==0, 'Wizard preview failed; inspect transcript'
    config=json.loads((base/'settings.json').read_text())
    assert len(config['apps'])==9 and not(base/'state').exists() and not(base/'login').exists()
    assert config['providers']['bazarr']['enabled']==['opensubtitlescom']
    assert all(row['kind']=='local' for row in config['storage_mounts'].values())
    assert config['folder_map']['movies']==str(work/'media/media-movies')
    assert [r['name'] for r in config['plex_libraries']]==['Movies','TV Shows','Sports','Standup']
    text=output.decode(errors='replace')
    assert 'Your choices are saved.' in text and 'nonsecret' not in text and 'Compose project' not in text
    result={'status':'passed','all_nine_optional_apps':'selected via defaults','local_only_explicit_folder_map':True,'plain_guided_save_only':True,
            'no_provisioning_state_or_accounts_collected':True,'transcript':str(work/'transcript.txt')}
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
