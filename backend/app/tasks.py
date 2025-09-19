# ==============================
# app/tasks.py
# ==============================
import asyncio
import os
import shutil
from typing import Dict, List, Callable, Any

from .sse import broker
from .config import AppConfig
from .qb_client import QBClient
from .pathmap import PathMapper
from .rsync import run_rsync


def _under(p: str, root: str) -> bool:
    p = (p or "").rstrip("/")
    r = (root or "").rstrip("/")
    return p == r or p.startswith(r + "/")


def _shell_join(parts: List[str]) -> str:
    out: List[str] = []
    for x in parts:
        if x is None:
            continue
        s = str(x)
        if not s:
            continue
        if any(ch.isspace() for ch in s):
            out.append(f'"{s}"')
        else:
            out.append(s)
    return " ".join(out)


def _normalize_flags(flags) -> List[str]:
    if flags is None:
        return []
    if isinstance(flags, (list, tuple, set)):
        seq = list(flags)
    else:
        seq = str(flags).split()
    return [f for f in seq if f]


async def _qb_call_with_timeout(
    fn: Callable[..., Any], *args, timeout: float = 5.0, **kwargs
):
    """
    Run a blocking qBittorrent client call off the event loop with a timeout,
    so a sluggish WebAPI can't block our SSE stream.
    """
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: fn(*args, **kwargs)), timeout=timeout
        )
    except asyncio.TimeoutError:
        raise TimeoutError(f"qB call timed out after {timeout}s")


class TaskRunner:
    def __init__(self, cfg: AppConfig, qb: QBClient, mapper: PathMapper):
        self.cfg = cfg
        self.qb = qb
        self.mapper = mapper
        self.sem = asyncio.Semaphore(cfg.max_concurrent_migrations)
        self.tasks: Dict[str, asyncio.Task] = {}

    def create_task(self, task_id: str, coro):
        t = asyncio.create_task(coro)
        self.tasks[task_id] = t
        return t

    async def migrate(self, task_id: str, hashes: List[str], dry_run: bool, delete_old: bool):
        async with self.sem:
            await broker.publish("state", {
                "taskId": task_id,
                "message": f"Starting migrate: {len(hashes)} torrents",
                "dryRun": dry_run
            })
            for h in hashes:
                await self._migrate_one(task_id, h, dry_run, delete_old)
            await broker.publish("done", {"taskId": task_id, "success": True})

    async def _migrate_one(self, task_id: str, h: str, dry_run: bool, delete_old: bool):
        # get torrent snapshot
        torrents = self.qb.list_torrents()
        tor = next((t for t in torrents if t.get("hash") == h), None)
        if not tor:
            await broker.publish("state", {"taskId": task_id, "hash": h, "message": "Not found", "level": "error"})
            return

        save_path = tor.get("save_path") or tor.get("download_path") or ""
        if not save_path:
            await broker.publish("state", {"taskId": task_id, "hash": h, "message": "Missing save_path", "level": "error"})
            return

        # container dst decision
        if _under(save_path, "/data/torrents"):
            dst_container = save_path.rstrip("/")
        elif _under(save_path, "/data"):
            dst_container = save_path.rstrip("/").replace("/data", "/data/torrents", 1)
        else:
            dst_container = save_path.rstrip("/")

        src_container = save_path.rstrip("/")

        # map to host
        src_host = self.mapper.container_to_host(src_container)
        dst_host = self.mapper.container_to_host(dst_container)
        if not src_host or not dst_host:
            await broker.publish("state", {
                "taskId": task_id, "hash": h,
                "message": f"Cannot map paths (src={src_container}, dst={dst_container})",
                "level": "error"
            })
            return

        # mapping info
        await broker.publish("state", {
            "taskId": task_id, "hash": h,
            "message": f"map: {src_container} -> {src_host} | {dst_container} -> {dst_host}"
        })

        # --- Build & publish command preview BEFORE any qB calls ---
        base_flags = _normalize_flags(getattr(self.cfg, "rsync_flags_effective", None))
        flags = base_flags.copy()
        if dry_run and "--dry-run" not in flags:
            flags = ["--dry-run", *flags]
        cmd_preview = ["rsync", *flags, f"{src_host}/", f"{dst_host}/"]
        cmd_str = _shell_join(cmd_preview)

        await broker.publish("state",   {"taskId": task_id, "hash": h, "message": cmd_str})
        await broker.publish("progress",{"taskId": task_id, "hash": h, "line":    cmd_str})
        await broker.publish("progress",{
            "taskId": task_id, "hash": h, "line": f"plan: {src_host} -> {dst_host}"
        })

        # --- Pause torrent (skip on dry-run to avoid blocking) ---
        if dry_run:
            await broker.publish("state", {"taskId": task_id, "hash": h, "message": "dry-run: skipping pause"})
        else:
            try:
                await broker.publish("state", {"taskId": task_id, "hash": h, "message": "Pause torrent"})
                await _qb_call_with_timeout(self.qb.pause, [h], timeout=5.0)
            except Exception as e:
                await broker.publish("state", {"taskId": task_id, "hash": h, "message": f"pause failed: {e}", "level": "warn"})

        # --- rsync availability ---
        rsync_path = shutil.which("rsync")
        if rsync_path is None:
            note = "rsync not found in PATH"
            if dry_run:
                await broker.publish("state", {"taskId": task_id, "hash": h, "message": f"{note} — dry-run preview only"})
                await broker.publish("state", {"taskId": task_id, "hash": h, "message": "dry-run complete"})
                return
            else:
                await broker.publish("state", {"taskId": task_id, "hash": h, "message": note, "level": "error"})
                # try to resume if we paused
                try:
                    await _qb_call_with_timeout(self.qb.resume, [h], timeout=5.0)
                except Exception:
                    pass
                return

        # --- Execute rsync ---
        try:
            async for prog in run_rsync(src_host, dst_host, base_flags, dry_run=dry_run):
                await broker.publish("progress", {"taskId": task_id, "hash": h, "line": prog.raw})
        except Exception as e:
            await broker.publish("state", {"taskId": task_id, "hash": h, "message": f"rsync error: {e}", "level": "error"})
            # try to resume if needed
            try:
                await _qb_call_with_timeout(self.qb.resume, [h], timeout=5.0)
            except Exception:
                pass
            return

        # --- Post actions ---
        if not dry_run:
            try:
                await broker.publish("state", {"taskId": task_id, "hash": h, "message": f"setLocation -> {dst_container}"})
                await _qb_call_with_timeout(self.qb.set_location, [h], dst_container, timeout=5.0)

                await broker.publish("state", {"taskId": task_id, "hash": h, "message": "recheck"})
                await _qb_call_with_timeout(self.qb.recheck, [h], timeout=5.0)

                await broker.publish("state", {"taskId": task_id, "hash": h, "message": "resume"})
                await _qb_call_with_timeout(self.qb.resume, [h], timeout=5.0)
            except Exception as e:
                await broker.publish("state", {"taskId": task_id, "hash": h, "message": f"post-action failed: {e}", "level": "warn"})
        else:
            await broker.publish("state", {"taskId": task_id, "hash": h, "message": "dry-run complete"})

        # Delete old tree (only on live, if requested)
        if not dry_run and delete_old:
            s = os.path.realpath(src_host)
            d = os.path.realpath(dst_host)
            if s.startswith(d + os.sep) or d.startswith(s + os.sep):
                await broker.publish("state", {
                    "taskId": task_id, "hash": h,
                    "message": f"Refusing to delete (overlap) src={s} dst={d}",
                    "level": "warn",
                })
            else:
                await broker.publish("state", {"taskId": task_id, "hash": h, "message": f"Deleting old {s}"})
                try:
                    await _rm_rf(s)
                except Exception as e:
                    await broker.publish("state", {"taskId": task_id, "hash": h, "message": f"Delete failed: {e}", "level": "error"})


async def _rm_rf(path: str):
    import shutil
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: shutil.rmtree(path, ignore_errors=True))