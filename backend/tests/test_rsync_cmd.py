# ==============================
# tests/test_rsync_cmd.py
# ==============================
import pytest
import asyncio
from app.rsync import run_rsync

@pytest.mark.asyncio
async def test_rsync_dryrun_builds(tmp_path):
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'
    src.mkdir(); (src / 'f').write_text('x')
    async for _ in run_rsync(str(src), str(dst), ['-a','--info=progress2'], dry_run=True):
        pass