"""GET/PATCH /api/users/preferences — locale, currency, units, home airport, traveler defaults."""
import re
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from middlewares.auth import Identity, require_identity
from middlewares.conn_database import SessionLocal, get_db
from models.appModels import UserPreferences
from schemas.api import SCHEMA_VERSION

router = APIRouter()

DEFAULTS: Dict[str, Any] = {
    "locale": None,  # None = follow the browser
    "currency": "USD",
    "units": "metric",
    "home_airport": None,
    "default_adults": 2,
    "default_children": 0,
}


class PreferencesPatch(BaseModel):
    locale: Optional[str] = Field(None, max_length=16)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    units: Optional[Literal["metric", "imperial"]] = None
    home_airport: Optional[str] = Field(None, max_length=80)
    default_adults: Optional[int] = Field(None, ge=1, le=9)
    default_children: Optional[int] = Field(None, ge=0, le=9)

    @field_validator("locale")
    @classmethod
    def _locale(cls, v):
        if v and not re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", v):
            raise ValueError("locale must be a BCP 47 tag like en-US")
        return v

    @field_validator("currency")
    @classmethod
    def _currency(cls, v):
        if v and not re.fullmatch(r"[A-Za-z]{3}", v):
            raise ValueError("currency must be a 3-letter ISO code")
        return v.upper() if v else v


def to_dict(row: Optional[UserPreferences]) -> Dict[str, Any]:
    out = dict(DEFAULTS)
    if row:
        for k in DEFAULTS:
            v = getattr(row, k)
            if v is not None:
                out[k] = v
    out["schema_version"] = SCHEMA_VERSION
    return out


def load_preferences(user_sub: Optional[str]) -> Dict[str, Any]:
    """Preferences for the pipeline (never raises; defaults when the DB is unavailable)."""
    if not user_sub:
        return {k: v for k, v in DEFAULTS.items() if v is not None and k != "currency"}
    db = SessionLocal()
    try:
        row = db.query(UserPreferences).filter(UserPreferences.user_sub == user_sub).first()
        prefs = to_dict(row)
        prefs.pop("schema_version", None)
        return prefs
    except Exception:
        return dict(DEFAULTS)
    finally:
        db.close()


@router.get("")
async def get_preferences(ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    return to_dict(db.query(UserPreferences).filter(UserPreferences.user_sub == ident.sub).first())


@router.patch("")
async def patch_preferences(body: PreferencesPatch, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    row = db.query(UserPreferences).filter(UserPreferences.user_sub == ident.sub).first()
    if not row:
        row = UserPreferences(user_sub=ident.sub)
        db.add(row)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, (v.strip() or None) if isinstance(v, str) else v)
    db.commit()
    db.refresh(row)
    return to_dict(row)
