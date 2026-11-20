"""
Conversations (server-side history, synced across devices).

GET    /api/conversations?limit=20&cursor=…   paginated, newest first
POST   /api/conversations                     {id?, title?}
GET    /api/conversations/{id}                with messages + structured data
PATCH  /api/conversations/{id}                {title}
DELETE /api/conversations/{id}
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from controllers import conversationController as cc
from middlewares.auth import Identity, require_identity
from middlewares.conn_database import SessionLocal, get_db

router = APIRouter()
logger = logging.getLogger("conversation_route")


class ConversationCreate(BaseModel):
    id: Optional[str] = Field(None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: Optional[str] = Field(None, max_length=120)


class ConversationPatch(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


def _owned_or_404(db: Session, ident: Identity, conversation_id: str):
    c = cc.get_owned(db, ident.sub, conversation_id)
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return c


@router.get("")
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None, max_length=16),
    ident: Identity = Depends(require_identity),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    items, next_cursor = cc.list_conversations(db, ident.sub, limit, cursor)
    return {"items": items, "next_cursor": next_cursor}


@router.post("", status_code=201)
async def create_conversation(body: ConversationCreate, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    try:
        c = cc.create_conversation(db, ident.sub, body.id, body.title)
    except PermissionError:
        raise HTTPException(status_code=409, detail="That conversation id is already in use.")
    return cc.conversation_dict(c)


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    return cc.conversation_dict(_owned_or_404(db, ident, conversation_id), with_messages=True)


@router.patch("/{conversation_id}")
async def patch_conversation(conversation_id: str, body: ConversationPatch, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    c = cc.rename(db, _owned_or_404(db, ident, conversation_id), body.title)
    return cc.conversation_dict(c)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    cc.delete(db, _owned_or_404(db, ident, conversation_id))


# ------------------------------------------------------------- from /ask
TITLE_PROMPT = "Write a 3-6 word title for this travel conversation (no quotes, no trailing period). Example: 'Lisbon long weekend in March'."


async def _generate_title(conversation_id: str, question: str, answer: str) -> None:
    from agents.travel_graph import use_fixtures

    if use_fixtures():
        return
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o", temperature=0.2, max_tokens=20)
        resp = await llm.ainvoke([SystemMessage(content=TITLE_PROMPT), HumanMessage(content=f"User: {question}\nAssistant: {answer[:600]}")])
        title = str(resp.content).strip().strip('"').strip("'").rstrip(".")[:80]
    except Exception as e:
        logger.info(f"title generation skipped: {e}")
        return

    def write():
        db = SessionLocal()
        try:
            cc.set_generated_title(db, conversation_id, title)
        finally:
            db.close()

    await asyncio.to_thread(write)


async def persist_turn(ident: Optional[Identity], conversation_id: Optional[str], question: str, final: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Save a finished /ask turn. Never fails the answer: DB problems are logged and skipped."""
    if not ident or not conversation_id:
        return {}
    data = {k: v for k, v in final.items() if k not in ("answer", "request_id", "schema_version", "model", "status", "conversation_id")}

    def write():
        db = SessionLocal()
        try:
            conv, um, am, first = cc.save_turn(db, ident.sub, conversation_id, question, final.get("answer") or "", data, request_id)
            # Read everything we need while the session is open.
            return {"conversation_id": conv.id, "message_id": am.id, "user_message_id": um.id, "title": conv.title}, first
        finally:
            db.close()

    try:
        saved, first = await asyncio.to_thread(write)
    except PermissionError:
        return {}
    except Exception as e:
        logger.warning(f"Could not save conversation turn: {e}")
        return {}
    if first:
        asyncio.create_task(_generate_title(saved["conversation_id"], question, final.get("answer") or ""))
    return saved
