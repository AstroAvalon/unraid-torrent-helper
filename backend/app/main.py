# ==============================
# app/main.py
# ==============================
from __future__ import annotations
import asyncio
import os
import time
import uuid
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import AppConfig
from .db import DB
from .auth import router as auth_router, auth_guard
from .qb_client import QBClient
from .pathmap import PathMapper
from .tasks import TaskRunner
from .sse import router as sse_router
from .models import TorrentInfo, ListResponse, MigrateRequest, FixMetaRequest, TaskStatus
from .utils import compute_misplaced, suggest_target

app = FastAPI(title="Unraid Torrent Helper — Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
    allow_credentials=True,
)

app.include_router(auth_router)
app.include_router(sse_router)

@app.on_event('startup')
async def startup():
    cfg = AppConfig()
    db = DB(cfg)
    qb = QBClient(cfg)
    mapper = PathMapper(cfg.mappings)
    runner = TaskRunner(cfg, qb, mapper)
    app.state.cfg = cfg
    app.state.db = db
    app.state.qb = qb
    app.state.mapper = mapper
    app.state.runner = runner
    static_dir = os.path.join(cfg.data_dir, 'static')
    if os.path.isdir(static_dir):
        app.mount('/', StaticFiles(directory=static_dir, html=True), name='static')

@app.get('/api/healthz')
def healthz():
    return {"status": "ok"}

@app.get('/api/config', dependencies=[Depends(auth_guard)])
def get_config(req: Request):
    cfg: AppConfig = req.app.state.cfg
    # redact
    return {
        "qb_url": str(cfg.qb_url),
        "mappings": [m.dict() for m in cfg.mappings],
        "rsync_flags": cfg.rsync_flags_effective,
        "stuck_minutes": cfg.stuck_minutes,
        "backup_torrent_dir": cfg.backup_torrent_dir,
        "max_concurrent_migrations": cfg.max_concurrent_migrations,
    }

@app.get('/api/torrents', response_model=ListResponse, dependencies=[Depends(auth_guard)])
def list_torrents(req: Request):
    qb: QBClient = req.app.state.qb
    cfg: AppConfig = req.app.state.cfg
    items: List[TorrentInfo] = []
    for t in qb.list_torrents():
        misplaced = cfg.save_path_is_misplaced(t.get('save_path', ''))
        items.append(TorrentInfo(
            name=t.get('name',''),
            hash=t.get('hash',''),
            size=t.get('size',0),
            save_path=t.get('save_path',''),
            state=t.get('state',''),
            progress=t.get('progress',0.0),
            category=t.get('category'),
            tags=t.get('tags'),
            misplaced=misplaced,
            suggested_target=suggest_target(t.get('save_path','')) if misplaced else None,
        ))
    return ListResponse(items=items)

@app.post('/api/actions/migrate', dependencies=[Depends(auth_guard)])
async def migrate(body: MigrateRequest, req: Request):
    runner: TaskRunner = req.app.state.runner
    task_id = str(uuid.uuid4())
    coro = runner.migrate(task_id, body.hashes, body.dryRun, body.deleteOld)
    runner.create_task(task_id, coro)
    return {"taskId": task_id}

# (Phase 2) Fix-metadata orchestration — scaffold only; full strategy applied in Part 2b if needed
@app.post('/api/actions/fix-metadata', dependencies=[Depends(auth_guard)])
async def fix_metadata(body: FixMetaRequest, req: Request):
    qb: QBClient = req.app.state.qb
    # simple first step: reannounce; replacement flow will be expanded in next chunk if desired
    qb.reannounce(body.hashes)
    return {"ok": True, "message": "Reannounce sent"}