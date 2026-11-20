"""
Runs one /api/llm/ask request as an asyncio task and turns pipeline events
into Server-Sent Events. Tasks are registered by request_id so they can be
cancelled (DELETE /api/llm/ask/{request_id}) or outlive a dropped client.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Optional

from schemas.api import SCHEMA_VERSION

logger = logging.getLogger("stream_runner")

HEARTBEAT_S = 15

_running: Dict[str, Dict[str, Any]] = {}

# Section codes → retryable flag (mid-stream errors)
SECTION_EVENT_TYPES = ("agent", "plan", "trip", "section", "delta", "clarification", "final", "error")


def sse(event: str, data: Dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, default=str, separators=(',', ':'))}\n\n".encode()


def running_task(request_id: str) -> Optional[Dict[str, Any]]:
    return _running.get(request_id)


def cancel(request_id: str, owner: Optional[str] = None) -> bool:
    entry = _running.get(request_id)
    if not entry:
        return False
    if owner and entry.get("owner") and entry["owner"] != owner:
        return False
    entry["task"].cancel()
    return True


async def stream_request(
    request_id: str,
    events: AsyncIterator[Dict[str, Any]],
    owner: Optional[str] = None,
    on_final: Optional[Callable[[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]] = None,
) -> AsyncIterator[bytes]:
    queue: asyncio.Queue = asyncio.Queue()
    DONE = object()

    async def produce():
        try:
            async for ev in events:
                kind = ev.pop("event", None)
                if kind not in SECTION_EVENT_TYPES:
                    continue
                ev["request_id"] = request_id
                if kind == "section":
                    sec = ev.get("section") or {}
                    if sec.get("status") == "failed":
                        await queue.put(sse("error", {
                            "code": sec.get("code") or f"{str(ev.get('type')).upper()}_FAILED",
                            "message": sec.get("message") or "This section failed.",
                            "retryable": sec.get("retryable", True),
                            "section": ev.get("type"),
                            "request_id": request_id,
                        }))
                if kind == "final":
                    ev["schema_version"] = SCHEMA_VERSION
                    if on_final:
                        try:
                            extra = await on_final(ev)
                            if extra:
                                ev.update(extra)
                        except Exception:
                            logger.exception("on_final hook failed")
                await queue.put(sse(kind, ev))
        except asyncio.CancelledError:
            await queue.put(sse("error", {"code": "CANCELLED", "message": "Stopped.", "retryable": True, "request_id": request_id}))
            raise
        except Exception as e:
            logger.exception(f"ask {request_id} failed")
            await queue.put(sse("error", {
                "code": "AGENT_ERROR",
                "message": f"The planner hit an error: {str(e)[:200]}",
                "retryable": True,
                "request_id": request_id,
            }))
        finally:
            await queue.put(DONE)

    task = asyncio.create_task(produce())
    _running[request_id] = {"task": task, "owner": owner}
    try:
        yield sse("meta", {"request_id": request_id, "schema_version": SCHEMA_VERSION})
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_S)
            except asyncio.TimeoutError:
                yield b": ping\n\n"  # keeps Heroku's 55s idle timer from closing the stream
                continue
            if item is DONE:
                break
            yield item
    finally:
        if not task.done():
            # Client went away: stop spending tokens on an answer nobody reads.
            task.cancel()
        _running.pop(request_id, None)
