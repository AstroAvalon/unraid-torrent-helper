# ==============================
# tests/test_pathmap.py
# ==============================
from app.pathmap import PathMapper
from app.config import PathMapping

def test_longest_prefix_wins():
    pm = PathMapper([
        PathMapping(container='/data/torrents', host='/mnt/user/media/torrents'),
        PathMapping(container='/data', host='/mnt/user/torrents'),
    ])
    assert pm.container_to_host('/data/torrents/movies/x') == '/mnt/user/media/torrents/movies/x'
    assert pm.container_to_host('/data/foo') == '/mnt/user/torrents/foo'