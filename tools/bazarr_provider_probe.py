"""Read-only native OpenSubtitles login/search probe run inside the pinned image.

Credentials arrive on stdin. Never emit HTTP bodies, tokens or exception messages.
"""
import ast
import json
import hashlib
import os
import re
import logging
from pathlib import Path
import sys

logging.disable(logging.CRITICAL)
spec = json.load(sys.stdin)
try:
    base = Path('/app/bazarr/bin')
    sys.path[:0] = [str(base / 'custom_libs'), str(base / 'libs'), str(base / 'bazarr')]
    from subliminal.cache import region
    from subliminal.video import Movie
    from subzero.language import Language
    from subliminal_patch.providers.opensubtitlescom import OpenSubtitlesComProvider
    tree = ast.parse((base / 'bazarr/app/get_providers.py').read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'get_providers_auth')
    key = None
    for node in ast.walk(function):
        if isinstance(node, ast.Dict):
            for name, value in zip(node.keys, node.values):
                if isinstance(name, ast.Constant) and name.value == 'opensubtitlescom' and isinstance(value, ast.Dict):
                    for field, setting in zip(value.keys, value.values):
                        if isinstance(field, ast.Constant) and field.value == 'api_key' and isinstance(setting, ast.Constant):
                            key = setting.value
    assert isinstance(key, str) and key
    region.configure('dogpile.cache.memory', expiration_time=600)
    provider = OpenSubtitlesComProvider(username=spec['credentials']['username'], password=spec['credentials']['password'],
                                        use_hash=False, api_key=key)
    provider.initialize()
    assert provider.token
    video = Movie('Installarr-read-only-subtitle-query.mkv', title=spec['title'], year=spec['year'])
    video.imdb_id = spec['imdb_id']
    results = provider.list_subtitles(video, {Language('eng')})
    result = {'provider': 'opensubtitlescom', 'authentication': 'verified', 'english_results': len(results),
              'subtitle_download': 'not attempted', 'original_media_files_written': False}
    if spec.get('download'):
        assert os.geteuid() == 2000 and results
        provider.download_subtitle(results[0])
        content = results[0].content
        assert isinstance(content, bytes) and len(content) > 100
        assert re.search(rb'\d{2}:\d{2}:\d{2}[,.]\d{3}', content)
        directory = Path('/data/installarr-provider-tests')
        directory.mkdir(mode=0o700, exist_ok=True)
        output = directory / 'opensubtitlescom.en.srt'
        fd = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        assert output.read_bytes() == content
        info = output.stat()
        result['subtitle_download'] = {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
                                       'uid': info.st_uid, 'gid': info.st_gid, 'fsync_readback': 'verified'}
    provider.terminate()
    print(json.dumps(result))
except Exception as error:
    print(json.dumps({'provider': 'opensubtitlescom', 'error_type': type(error).__name__,
                      'details': 'private native provider failure; no response/token/credential output'}))
    raise SystemExit(2)
