# ==============================
# app/rsync.py
# ==============================
import asyncio
import os
import shlex
from typing import AsyncIterator, List, Optional

class RsyncProgress:
    def __init__(self, line: str):
        self.raw = line
        # --info=progress2 lines often look like:
        # "       1,234,567  10%    2.34MB/s    0:00:12 (xfr#1, to-chk=3/10)"
        # We'll forward raw; frontend can parse basic numbers. Keep lightweight here.

async def run_rsync(src: str, dst: str, flags: List[str], dry_run: bool = False) -> AsyncIterator[RsyncProgress]:
    os.makedirs(dst, exist_ok=True)
    cmd = ['rsync'] + flags + (["-n"] if dry_run else []) + [f"{src.rstrip('/')}/", f"{dst.rstrip('/')}/"]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    assert proc.stdout
    async for line in _aiter_lines(proc.stdout):
        yield RsyncProgress(line.decode(errors='ignore').rstrip())
    rc = await proc.wait()
    if rc != 0:
        raise RuntimeError(f"rsync failed rc={rc}")

async def _aiter_lines(stream: asyncio.StreamReader):
    while True:
        line = await stream.readline()
        if not line:
            break
        yield line