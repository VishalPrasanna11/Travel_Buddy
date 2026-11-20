"""Conversation storage: CRUD, pagination, turn persistence and titles."""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.appModels import Conversation, ConversationMessage

logger = logging.getLogger("conversations")

DEFAULT_TITLE = "New trip"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def message_dict(m: ConversationMessage) -> Dict[str, Any]:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "data": m.data,
        "request_id": m.request_id,
        "created_at": _iso(m.created_at),
    }


def conversation_dict(c: Conversation, with_messages: bool = False, turns: Optional[int] = None) -> Dict[str, Any]:
    out = {
        "id": c.id,
        "title": c.title,
        "custom_title": bool(c.custom_title),
        "created_at": _iso(c.created_at),
        "updated_at": _iso(c.updated_at),
    }
    if turns is not None:
        out["message_count"] = turns
    if with_messages:
        out["messages"] = [message_dict(m) for m in c.messages]
        out["itinerary"] = c.itinerary
    return out


def get_owned(db: Session, user_sub: str, conversation_id: str) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_sub == user_sub).first()


def list_conversations(db: Session, user_sub: str, limit: int, cursor: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Newest first. `cursor` is the offset of the next page (opaque to clients)."""
    offset = int(cursor) if cursor and cursor.isdigit() else 0
    counts = (
        db.query(ConversationMessage.conversation_id, func.count(ConversationMessage.id))
        .group_by(ConversationMessage.conversation_id)
        .subquery()
    )
    rows = (
        db.query(Conversation, counts.c[1])
        .outerjoin(counts, counts.c.conversation_id == Conversation.id)
        .filter(Conversation.user_sub == user_sub)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit + 1)
        .all()
    )
    items = [conversation_dict(c, turns=n or 0) for c, n in rows[:limit]]
    next_cursor = str(offset + limit) if len(rows) > limit else None
    return items, next_cursor


def create_conversation(db: Session, user_sub: str, conversation_id: Optional[str], title: Optional[str]) -> Conversation:
    if conversation_id:
        existing = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if existing:
            if existing.user_sub != user_sub:
                raise PermissionError("conversation belongs to another user")
            return existing
    c = Conversation(user_sub=user_sub, title=(title or DEFAULT_TITLE)[:120], custom_title=1 if title else 0)
    if conversation_id:
        c.id = conversation_id
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def rename(db: Session, c: Conversation, title: str) -> Conversation:
    c.title = title.strip()[:120] or c.title
    c.custom_title = 1
    db.commit()
    db.refresh(c)
    return c


def delete(db: Session, c: Conversation) -> None:
    db.delete(c)
    db.commit()


def heuristic_title(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip().rstrip("?.!")
    return (clean[:57] + "…") if len(clean) > 58 else (clean or DEFAULT_TITLE)


def save_turn(
    db: Session,
    user_sub: str,
    conversation_id: str,
    user_text: str,
    answer: str,
    data: Dict[str, Any],
    request_id: str,
    user_message_id: Optional[str] = None,
) -> Tuple[Conversation, ConversationMessage, ConversationMessage, bool]:
    """Persist one question + answer. Returns (conversation, user msg, assistant msg, is_first_turn)."""
    c = create_conversation(db, user_sub, conversation_id, None)
    first = db.query(ConversationMessage).filter(ConversationMessage.conversation_id == c.id).count() == 0
    um = ConversationMessage(conversation_id=c.id, role="user", content=user_text, request_id=request_id)
    if user_message_id:
        um.id = user_message_id
    am = ConversationMessage(conversation_id=c.id, role="assistant", content=answer, data=data, request_id=request_id)
    db.add_all([um, am])
    if data.get("itinerary"):
        c.itinerary = data["itinerary"]
    if first and not c.custom_title:
        c.title = heuristic_title(user_text)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(um)
    db.refresh(am)
    return c, um, am, first


def set_generated_title(db: Session, conversation_id: str, title: str) -> None:
    c = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if c and not c.custom_title and title:
        c.title = title[:120]
        db.commit()
