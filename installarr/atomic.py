"""Linux atomic publication that never replaces an existing directory entry.

Ubuntu20.04+ provides renameat2/RENAME_NOREPLACE. Unlike link+unlink this does
not leave a two-link target when an updater dies between publication and cleanup.
Callers still fsync file contents first and the containing directory afterward.
"""
import ctypes
from functools import lru_cache
import os


@lru_cache(maxsize=1)
def _renameat2():
    try:
        function = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError:
        raise OSError('Atomic no-replacement publication requires Linux renameat2') from None
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    return function


def publish_noreplace(source, target, source_dir_fd=-100, target_dir_fd=-100):
    old, new = os.fsencode(source), os.fsencode(target)
    if not old or not new or b'\x00' in old or b'\x00' in new:
        raise ValueError('Invalid atomic publication path')
    if _renameat2()(source_dir_fd, old, target_dir_fd, new, 1):
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), os.fspath(target))
