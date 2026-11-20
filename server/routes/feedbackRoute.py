"""POST /api/feedback — thumbs up/down on an answer, with an optional reason."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from middlewares.auth import Identity, require_identity
from middlewares.conn_database import get_db
from models.appModels import Feedback

router = APIRouter()


class FeedbackIn(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=64)
    rating: Literal["up", "down"]
    reason: Optional[str] = Field(None, max_length=1000)
    request_id: Optional[str] = Field(None, max_length=64)


@router.post("", status_code=201)
async def give_feedback(body: FeedbackIn, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    """One rating per user per message; sending again updates it."""
    row = db.query(Feedback).filter(Feedback.user_sub == ident.sub, Feedback.message_id == body.message_id).first()
    if row:
        row.rating, row.reason = body.rating, body.reason
        row.request_id = body.request_id or row.request_id
    else:
        row = Feedback(user_sub=ident.sub, message_id=body.message_id, rating=body.rating, reason=body.reason, request_id=body.request_id)
        db.add(row)
    db.commit()
    return {"message_id": body.message_id, "rating": row.rating, "reason": row.reason}
