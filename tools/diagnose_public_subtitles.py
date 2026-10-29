"""Read-only public endpoint diagnosis using pinned provider code and TLS checks."""
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    work = Path(tempfile.mkdtemp(prefix='installarr-public-subtitle-diagnosis-', dir='/var/tmp'))
    script = r'''
import importlib,inspect,json,logging,sys,urllib.parse
from pathlib import Path
logging.disable(logging.CRITICAL)
base=Path('/app/bazarr/bin');sys.path[:0]=[str(base/'custom_libs'),str(base/'libs'),str(base/'bazarr')]
import requests
from subliminal.cache import region
from subliminal.video import Movie,Episode
from subzero.language import Language
region.configure('dogpile.cache.memory',expiration_time=600)
results=[]
for name in ('yifysubtitles','tvsubtitles'):
    module=importlib.import_module('subliminal_patch.providers.'+name)
    classes=[v for k,v in vars(module).items() if inspect.isclass(v) and v.__module__==module.__name__ and hasattr(v,'list_subtitles')]
    provider=classes[0]();provider.initialize()
    url=getattr(provider,'server_url',None)
    host=urllib.parse.urlsplit(url).hostname if isinstance(url,str) else None
    outcome={'provider':name,'base_host':host,'scheme':urllib.parse.urlsplit(url).scheme if isinstance(url,str) else None}
    try:
        video=Movie('generated.mkv',title='Framing Britney Spears',year=2021) if name=='yifysubtitles' else Episode('generated.mkv',series='11.22.63',season=1,episode=1,title='The Rabbit Hole',year=2016)
        if name=='yifysubtitles':video.imdb_id='tt12673718'
        subtitles=provider.list_subtitles(video,{Language('eng')})
        outcome.update(native_search='completed',english_results=len(subtitles))
    except Exception as error:
        outcome.update(native_search='failed',error_type=type(error).__name__)
        response=getattr(error,'response',None)
        if response is not None:outcome['http_status']=response.status_code
        if isinstance(error,requests.exceptions.SSLError):
            text=str(error).lower()
            outcome['tls_code']='unexpected_eof' if 'eof' in text else 'wrong_version' if 'wrong_version' in text else 'other'
            outcome['tls_reason']='certificate_expired' if 'expired' in text else 'untrusted_certificate' if 'certificate verify failed' in text else 'tls_handshake_failure'
        if response is not None and response.request is not None:
            outcome['request_host']=urllib.parse.urlsplit(response.request.url).hostname
    finally:
        provider.terminate()
    outcome['endpoint_probes']=[]
    for scheme in ('http','https'):
        endpoint=scheme+'://'+host+'/' if host else None
        if not endpoint:continue
        probe={'scheme':scheme}
        try:
            response=requests.get(endpoint,timeout=12,allow_redirects=True)
            probe.update(status=response.status_code,final_host=urllib.parse.urlsplit(response.url).hostname,
                         redirect_statuses=[r.status_code for r in response.history])
        except Exception as error:
            probe['error_type']=type(error).__name__
        outcome['endpoint_probes'].append(probe)
    results.append(outcome)
print(json.dumps(results))
'''
    image = 'ghcr.io/linuxserver/bazarr@sha256:9a625883f054e722795affe5e3ca71057e6ed817ecdf99f4a99624346fcc509c'
    print(json.dumps({'evidence': str(work)}), flush=True)
    result = subprocess.run(['docker', '--host', 'unix:///run/docker.sock', 'run', '--rm', '--network', 'bridge',
        '--user', '2000:2000', '--cap-drop', 'ALL', '--entrypoint', 'python3', image, '-B', '-c', script],
        capture_output=True, text=True, timeout=180)
    if result.returncode:
        (work / 'failure.txt').write_text('Pinned native public-provider diagnostic failed; no credentials/media used.\n')
        raise ValueError('Public provider diagnostic failed')
    data = json.loads(result.stdout)
    (work / 'result.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(data), flush=True)


if __name__ == '__main__':
    main()
