"""Native public-provider searches only; no media binds, credentials or downloads."""
import importlib
import inspect
import json
import logging
from pathlib import Path
import sys

logging.disable(logging.CRITICAL)
spec = json.load(sys.stdin)
name = spec['provider']
try:
    assert name in ('yifysubtitles', 'supersubtitles', 'tvsubtitles')
    base = Path('/app/bazarr/bin')
    sys.path[:0] = [str(base / 'custom_libs'), str(base / 'libs'), str(base / 'bazarr')]
    from subliminal.cache import region
    from subliminal.video import Movie, Episode
    from subzero.language import Language
    region.configure('dogpile.cache.memory', expiration_time=600)
    module = importlib.import_module('subliminal_patch.providers.' + name)
    classes = [value for key, value in vars(module).items() if inspect.isclass(value)
               and value.__module__ == module.__name__ and hasattr(value, 'list_subtitles')]
    assert len(classes) == 1
    provider = classes[0]()
    provider.initialize()
    if name == 'yifysubtitles':
        video = Movie('Installarr-read-only-query.mkv', title='Framing Britney Spears', year=2021)
        # Public IMDb entry verified independently; Plex movie lacks an IMDb GUID.
        video.imdb_id = 'tt12673718'
    else:
        video = Episode('Installarr-read-only-query.mkv', series='11.22.63', season=1, episode=1,
                        title='The Rabbit Hole', year=2016)
    subtitles = provider.list_subtitles(video, {Language('eng')})
    provider.terminate()
    print(json.dumps({'provider': name, 'native_search': 'completed', 'english_results': len(subtitles),
                      'downloads': 'not attempted', 'media_files_written': False}))
except Exception as error:
    print(json.dumps({'provider': name, 'native_search': 'failed', 'error_type': type(error).__name__,
                      'downloads': 'not attempted', 'media_files_written': False}))
