# ==============================
# app/models.py
# ==============================
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict

class TorrentInfo(BaseModel):
    name: str
    hash: str
    size: int
    save_path: str
    state: str
    progress: float
    category: Optional[str] = None
    tags: Optional[str] = None
    misplaced: bool = False
    suggested_target: Optional[str] = None

class ListResponse(BaseModel):
    items: List[TorrentInfo]

class MigrateRequest(BaseModel):
    hashes: List[str]
    dryRun: bool = False
    deleteOld: bool = False

class FixMetaRequest(BaseModel):
    hashes: List[str]
    strategy: Optional[List[Literal['reannounce','dht-nudge','replace']]] = None
    dryRun: bool = False

class TaskStatus(BaseModel):
    taskId: str
    status: Literal['queued','running','done','error','canceled']
    message: Optional[str] = None
    results: Optional[Dict] = None

class LoginRequest(BaseModel):
    username: str
    password: str


# ==============================
# app/db.py
# ==============================
import os
import sqlite3
from typing import Optional, Tuple
from .config import AppConfig

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta_seen (
  hash TEXT PRIMARY KEY,
  first_seen_ts INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  payload TEXT,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL
);
"""

class DB:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        os.makedirs(cfg.data_dir, exist_ok=True)
        self.path = os.path.join(cfg.data_dir, 'app.db')
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def get_conn(self):
        return self.conn