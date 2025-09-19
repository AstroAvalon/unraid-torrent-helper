# ==============================
# app/utils.py
# ==============================
from typing import List, Dict

# replace both helpers with these
def _under(path: str, root: str) -> bool:
    p = path.rstrip('/')
    r = root.rstrip('/')
    return p == r or p.startswith(r + '/')

def compute_misplaced(save_path: str) -> bool:
    return _under(save_path, '/data') and not _under(save_path, '/data/torrents')

def suggest_target(save_path: str) -> str:
    # if already under /data/torrents, keep as-is
    if _under(save_path, '/data/torrents'):
        return save_path
    # if under /data, rewrite the first '/data' to '/data/torrents'
    if _under(save_path, '/data'):
        # normalize without trailing slash to avoid double 'torrents'
        sp = save_path.rstrip('/')
        return sp.replace('/data', '/data/torrents', 1)
    return save_path
