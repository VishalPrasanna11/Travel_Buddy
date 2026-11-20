"""
API contract shared by every endpoint: schema version, request ids,
the typed error body and the SSE event payloads for POST /api/llm/ask.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "2026-11-20"

SectionName = Literal["flights", "hotels", "attractions", "restaurants", "weather", "cars", "destination"]
AgentState = Literal["queued", "running", "done", "empty", "failed", "skipped"]


def new_request_id() -> str:
    return f"r_{uuid.uuid4().hex[:16]}"


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False
    section: Optional[str] = None
    request_id: Optional[str] = None
    retry_after: Optional[int] = None


class ErrorResponse(BaseModel):
    error: ErrorBody
    detail: Optional[str] = None  # kept for clients that read FastAPI's `detail`
    schema_version: str = SCHEMA_VERSION


class SectionStatus(BaseModel):
    status: Literal["ok", "empty", "failed", "skipped", "estimate"]
    count: int = 0
    message: Optional[str] = None
    reason: Optional[str] = None
    alternatives: List[str] = Field(default_factory=list)


# ------------------------------------------------------------ SSE payloads
class AgentEvent(BaseModel):
    agent: str
    state: AgentState
    count: Optional[int] = None
    message: Optional[str] = None


class SectionEvent(BaseModel):
    type: SectionName
    status: SectionStatus
    items: List[Dict[str, Any]] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class DeltaEvent(BaseModel):
    text: str


class AskRequest(BaseModel):
    query: str = ""
    conversation_id: Optional[str] = None
    chat_history: List[Dict[str, str]] = Field(default_factory=list)
    # Answer a clarification: resume the paused graph for this request.
    resume: Optional[Dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Plan 3 days in Lisbon from Boston, March 12-15, 2 adults",
                "conversation_id": None,
                "chat_history": [],
            }
        }
    }
