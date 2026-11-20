from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from controllers.llmController import LLMController, Message
from middlewares.conn_llm import get_openai_client
from middlewares.conn_database import get_db
from sqlalchemy.orm import Session
from openai import OpenAI
import asyncio
import json
import logging
import os
from middlewares.auth import Identity, optional_identity, resolve_email
from middlewares.errors import ask_limiter, error_response, request_id_of
from schemas.api import AskRequest
from agents.rootAgent import root_agent
from agents import stream_runner
from routes.conversationRoute import persist_turn

router = APIRouter()

class QuestionRequest(BaseModel):
    query: str
    chat_id: Optional[str] = None
    # Ignored: identity comes from the bearer token. Kept so old clients still validate.
    user_email: Optional[str] = None
    chat_history: Optional[List[Message]] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What are popular tourist destinations in Japan?",
                "chat_id": None,
                "chat_history": []
            }
        }
    }

@router.post("/ask-question")
async def ask_question(
    request: QuestionRequest,
    openai_client: OpenAI = Depends(get_openai_client),
    db: Session = Depends(get_db),
    ident: Optional[Identity] = Depends(optional_identity),
):
    """Legacy, non-streaming ask (keep-alive spaces, then one JSON document)."""
    controller = LLMController(openai_client)
    user_email = resolve_email(ident, db)

    async def generate():
        task = asyncio.create_task(controller.ask_question(
            query=request.query,
            chat_history=request.chat_history,
            chat_id=request.chat_id,
            user_email=user_email,
            db=db
        ))
        # Send a space every 10s to keep Heroku's connection alive (30s first-byte timeout)
        while not task.done():
            yield b" "
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=10)
                break
            except asyncio.TimeoutError:
                continue
        result = await task
        yield json.dumps(result).encode()

    return StreamingResponse(generate(), media_type="application/json")


# ---------------------------------------------------------------- streaming

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def anonymous_ask_allowed() -> bool:
    return os.getenv("ALLOW_ANONYMOUS_ASK", "").lower() in ("1", "true", "yes")


@router.post("/ask")
async def ask_stream(payload: AskRequest, request: Request, ident: Optional[Identity] = Depends(optional_identity)):
    """
    Streaming ask (Server-Sent Events). Event types:
      meta     {request_id, schema_version}                       first, immediately
      agent    {agent, state: queued|running|done|empty|failed|skipped, count?, message?}
      plan     {sections, trip}                                   which sections will run
      section  {type, section: {status, count, items, message}}   each as soon as it's ready
      delta    {text}                                             narrative tokens
      final    {request_id, answer, sections, flights, hotels, …}
      error    {code, message, retryable, section?, request_id}
    """
    request_id = request_id_of(request)
    if not ident and not anonymous_ask_allowed():
        return error_response(401, "Sign in to ask TravelBuddy.", request_id, code="UNAUTHORIZED", headers={"WWW-Authenticate": "Bearer"})
    client_key = ident.sub if ident else (request.client.host if request.client else "anon")
    wait = ask_limiter.check(client_key)
    if wait:
        return error_response(429, "Too many questions at once. Try again shortly.", request_id, retry_after=wait)
    resume = payload.resume or None
    thread_id = None
    if resume:
        thread_id = str(resume.get("request_id") or resume.get("thread_id") or "")
        owner = stream_runner.thread_owner(thread_id)
        if not thread_id or owner is False:
            return error_response(410, "That question expired. Ask again.", request_id, code="CLARIFICATION_EXPIRED")
        if owner and (not ident or ident.sub != owner):
            return error_response(403, "You can only answer your own questions.", request_id)
    elif not payload.query.strip():
        return error_response(400, "Ask a question first.", request_id, code="EMPTY_QUERY")

    history = [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in (payload.chat_history or [])[-10:]
        if m.get("content")
    ]
    answers = (resume or {}).get("answers") or {}
    events = root_agent.astream(
        {"input": payload.query, "history": history},
        request_id=request_id,
        resume=answers if resume else None,
        thread_id=thread_id,
    )

    # A resumed turn belongs to the question that was paused, not to the answer summary.
    question = (stream_runner.thread_question(thread_id) if resume else None) or payload.query or ""
    if not resume:
        stream_runner.remember_thread(request_id, ident.sub if ident else None, payload.query)

    async def on_final(ev):
        stream_runner.forget_thread(thread_id or request_id)
        saved = await persist_turn(ident, payload.conversation_id, question, ev, request_id)
        return {"conversation_id": payload.conversation_id, **saved}

    return StreamingResponse(
        stream_runner.stream_request(request_id, events, owner=ident.sub if ident else None, on_final=on_final),
        media_type="text/event-stream",
        headers={**SSE_HEADERS, "X-Request-ID": request_id},
    )


@router.delete("/ask/{request_id}")
async def cancel_ask(request_id: str, request: Request, ident: Optional[Identity] = Depends(optional_identity)):
    """Stop an answer in flight (cancels its asyncio task)."""
    rid = request_id_of(request)
    entry = stream_runner.running_task(request_id)
    if not entry:
        return error_response(404, "That request isn't running.", rid, code="NOT_RUNNING")
    owner = entry.get("owner")
    if owner and (not ident or ident.sub != owner):
        return error_response(403, "You can only stop your own requests.", rid)
    stream_runner.cancel(request_id)
    return {"request_id": request_id, "status": "cancelled"}
