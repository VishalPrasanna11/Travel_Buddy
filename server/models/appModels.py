"""
Server-side app data keyed by the Auth0 `sub` claim (user_sub).
Tables are created on startup if missing (see main.lifespan).
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import declarative_base, relationship

AppBase = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


class Conversation(AppBase):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_sub = Column(String(128), nullable=False, index=True)
    title = Column(String(120), nullable=False, default="New trip")
    custom_title = Column(Integer, nullable=False, default=0)  # 1 once the user renamed it
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    # Latest structured itinerary (for exports / share links)
    itinerary = Column(JSON, nullable=True)

    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )

    __table_args__ = (Index("ix_conversations_user_updated", "user_sub", "updated_at"),)


class ConversationMessage(AppBase):
    __tablename__ = "conversation_messages"

    id = Column(String(64), primary_key=True, default=_uuid)
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False, default="")
    data = Column(JSON, nullable=True)  # structured sections, itinerary, suggestions…
    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
