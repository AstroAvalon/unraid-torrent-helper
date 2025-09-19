# ==============================
# app/sse.py
# ==============================
import asyncio
import json
import time
from typing import AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .auth import auth_guard

router = APIRouter(prefix="/api/events", tags=["events"])

class SSEBroker:
    """
    Simple in-memory pub/sub for Server-Sent Events.
    """

    def __init__(self, heartbeat_sec: int = 10):
        self._subscribers: List[asyncio.Queue] = []
        self._heartbeat_sec = heartbeat_sec

    async def publish(self, event: str, data: Dict):
        payload = f"event: {event}\n" f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        # fan out (non-blocking)
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # drop slow subscriber
                try:
                    self._subscribers.remove(q)
                except ValueError:
                    pass

    async def _heartbeat(self, q: asyncio.Queue):
        """
        Periodic comment lines to keep proxies from closing idle connections.
        """
        while True:
            await asyncio.sleep(self._heartbeat_sec)
            try:
                q.put_nowait(f": heartbeat {int(time.time())}\n\n")
            except asyncio.QueueFull:
                break

    async def stream(self) -> AsyncIterator[str]:
        """
        Async generator per-subscriber.
        """
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self._subscribers.append(q)

        # Send an initial event so the client UI immediately shows "connected"
        await self.publish("state", {"message": "SSE connected"})

        hb_task = asyncio.create_task(self._heartbeat(q))

        try:
            while True:
                chunk = await q.get()
                yield chunk
        except asyncio.CancelledError:
            pass
        finally:
            hb_task.cancel()
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass


broker = SSEBroker()

@router.get("/stream")
async def stream(req: Request, user: str = Depends(auth_guard)):
    """
    Server-Sent Events endpoint.
    """
    async def gen():
        async for chunk in broker.stream():
            # If client disconnects, stop streaming
            if await req.is_disconnected():
                break
            yield chunk

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # for Nginx
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)