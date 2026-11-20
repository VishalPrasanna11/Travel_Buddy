"""Bookmarks: POST/GET/DELETE /api/saved-places (powers the "Saved" page)."""
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from middlewares.auth import Identity, require_identity
from middlewares.conn_database import get_db
from models.appModels import SavedPlace
from schemas.api import SCHEMA_VERSION

router = APIRouter()

KEEP = ("id", "name", "address", "location", "rating", "total_ratings", "price_level", "photos", "photo_url",
        "google_maps_uri", "website", "editorial_summary", "place_id", "star_rating", "guest_rating", "kind", "source", "fetched_at")


class SaveIn(BaseModel):
    entity: Dict[str, Any] = Field(..., description="The place/hotel entity as returned by /api/llm/ask")
    kind: Literal["place", "restaurant", "hotel"]
    conversation_id: Optional[str] = Field(None, max_length=64)


def out(row: SavedPlace) -> Dict[str, Any]:
    return {
        "id": row.id,
        "entity_id": row.entity_id,
        "kind": row.kind,
        "name": row.name,
        "entity": row.data,
        "conversation_id": row.conversation_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("", status_code=201)
async def save_place(body: SaveIn, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    entity_id = str(body.entity.get("id") or "")[:64]
    name = str(body.entity.get("name") or "")[:200]
    if not entity_id or not name:
        raise HTTPException(status_code=422, detail="The entity needs an id and a name.")
    snapshot = {k: body.entity[k] for k in KEEP if k in body.entity}
    row = db.query(SavedPlace).filter(SavedPlace.user_sub == ident.sub, SavedPlace.entity_id == entity_id).first()
    if row:
        row.data, row.name = snapshot, name
    else:
        row = SavedPlace(user_sub=ident.sub, entity_id=entity_id, kind=body.kind, name=name, data=snapshot, conversation_id=body.conversation_id)
        db.add(row)
    db.commit()
    db.refresh(row)
    return out(row)


@router.get("")
async def list_saved(
    kind: Optional[Literal["place", "restaurant", "hotel"]] = None,
    limit: int = Query(100, ge=1, le=500),
    ident: Identity = Depends(require_identity),
    db: Session = Depends(get_db),
):
    q = db.query(SavedPlace).filter(SavedPlace.user_sub == ident.sub)
    if kind:
        q = q.filter(SavedPlace.kind == kind)
    rows = q.order_by(SavedPlace.created_at.desc()).limit(limit).all()
    return {"items": [out(r) for r in rows], "schema_version": SCHEMA_VERSION}


@router.delete("/{saved_id}", status_code=204)
async def delete_saved(saved_id: str, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    """Accepts the saved id or the entity id."""
    row = (
        db.query(SavedPlace)
        .filter(SavedPlace.user_sub == ident.sub)
        .filter((SavedPlace.id == saved_id) | (SavedPlace.entity_id == saved_id))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Not in your saved places.")
    db.delete(row)
    db.commit()
