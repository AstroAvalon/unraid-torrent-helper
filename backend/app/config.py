# ==============================
# app/config.py
# ==============================

from __future__ import annotations
import os
from pydantic import BaseModel, Field, AnyHttpUrl, validator
from typing import List, Optional

class PathMapping(BaseModel):
    container: str
    host: str

    @validator('container', 'host')
    def no_trailing_slash(cls, v: str) -> str:
        if v != '/' and v.endswith('/'):
            return v[:-1]
        return v

class AppConfig(BaseModel):
    # App
    secret_key: str = Field(default_factory=lambda: os.environ.get('APP_SECRET_KEY', 'change-me'))
    data_dir: str = Field(default_factory=lambda: os.environ.get('APP_DATA_DIR', '/config'))

    # Auth (local user bootstrap)
    init_admin_user: str = Field(default_factory=lambda: os.environ.get('INIT_ADMIN_USER', 'admin'))
    init_admin_pass: str = Field(default_factory=lambda: os.environ.get('INIT_ADMIN_PASS', 'admin'))

    # qBittorrent
    qb_url: AnyHttpUrl = Field(default_factory=lambda: os.environ.get('QB_URL', 'http://192.168.1.118:8080'))
    qb_username: str = Field(default_factory=lambda: os.environ.get('QB_USERNAME', 'admin'))
    qb_password: str = Field(default_factory=lambda: os.environ.get('QB_PASSWORD', 'adminadmin'))

    # Paths & mapping
    mappings: List[PathMapping] = Field(default_factory=lambda: [
        PathMapping(container='/data/torrents', host='/mnt/user/media/torrents'),
        PathMapping(container='/data/media',     host='/mnt/user/media'),
        PathMapping(container='/data',           host='/mnt/user/torrents'),
    ])

    # Migration
    rsync_flags: List[str] = Field(default_factory=lambda: ['-aHAX', '--info=progress2', '--partial', '--inplace', '--numeric-ids', '--preallocate'])
    max_concurrent_migrations: int = Field(default_factory=lambda: int(os.environ.get('MAX_CONCURRENT', '2')))

    # Metadata-fix
    stuck_minutes: int = Field(default_factory=lambda: int(os.environ.get('STUCK_MINUTES', '10')))
    backup_torrent_dir: str = Field(default_factory=lambda: os.environ.get('BACKUP_TORRENT_DIR', '/backup_torrents'))

    # Optional: turn off --inplace via env
    @property
    def rsync_flags_effective(self) -> List[str]:
        flags = list(self.rsync_flags)
        if os.environ.get('DISABLE_INPLACE', 'false').lower() in ('1','true','yes'):
            flags = [f for f in flags if f != '--inplace']
        return flags

    # replace the existing method in AppConfig
    def save_path_is_misplaced(self, save_path: str) -> bool:
        """
        Misplaced if path is under /data (== '/data' or '/data/...') but NOT under /data/torrents
        Handles both with/without trailing slash.
        """
        sp = save_path.rstrip('/')
        def under(p: str, root: str) -> bool:
            p = p.rstrip('/')
            root = root.rstrip('/')
            return p == root or p.startswith(root + '/')
        return under(sp, '/data') and not under(sp, '/data/torrents')
