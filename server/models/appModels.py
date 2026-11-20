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


class Feedback(AppBase):
    __tablename__ = "message_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_sub = Column(String(128), nullable=False, index=True)
    message_id = Column(String(64), nullable=False, index=True)
    request_id = Column(String(64), nullable=True)
    rating = Column(String(8), nullable=False)  # "up" | "down"
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (Index("ux_feedback_user_message", "user_sub", "message_id", unique=True),)


class UserPreferences(AppBase):
    __tablename__ = "user_preferences"

    user_sub = Column(String(128), primary_key=True)
    locale = Column(String(16), nullable=True)  # BCP 47, e.g. en-US
    currency = Column(String(3), nullable=True)  # ISO 4217
    units = Column(String(8), nullable=True)  # metric | imperial
    home_airport = Column(String(80), nullable=True)
    default_adults = Column(Integer, nullable=True)
    default_children = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SavedPlace(AppBase):
    __tablename__ = "saved_places"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_sub = Column(String(128), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False)
    kind = Column(String(16), nullable=False)  # place | restaurant | hotel
    name = Column(String(200), nullable=False)
    data = Column(JSON, nullable=True)  # entity snapshot (address, rating, photo ref, location…)
    conversation_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ux_saved_user_entity", "user_sub", "entity_id", unique=True),)


class TripShare(AppBase):
    __tablename__ = "trip_shares"

    token = Column(String(32), primary_key=True)
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_sub = Column(String(128), nullable=False)
    snapshot = Column(JSON, nullable=False)  # read-only copy: answer, itinerary, entities
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
