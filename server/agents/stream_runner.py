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
# thread_id -> (owner sub, question, created) for paused (clarification) graphs
_threads: Dict[str, tuple] = {}
THREAD_TTL_S = 30 * 60


def remember_thread(thread_id: str, owner: Optional[str], question: str) -> None:
    import time

    now = time.time()
    for k in [k for k, v in _threads.items() if now - v[2] > THREAD_TTL_S]:
        _threads.pop(k, None)
    _threads[thread_id] = (owner, question, now)


def thread_owner(thread_id: Optional[str]):
    """Owner sub (or None for anonymous) of a known thread; False if unknown/expired."""
    entry = _threads.get(thread_id or "")
    return False if entry is None else entry[0]


def forget_thread(thread_id: Optional[str]) -> None:
    _threads.pop(thread_id or "", None)


def thread_question(thread_id: Optional[str]) -> Optional[str]:
    entry = _threads.get(thread_id or "")
    return entry[1] if entry else None

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
