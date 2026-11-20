"""
Trips = conversations that have a structured itinerary.

GET /api/trips/{id}/export?format=ics|pdf   download the itinerary
GET /api/trips/{id}/share                   create (or reuse) a read-only public link
GET /api/shared/{token}                     public, read-only trip snapshot
"""
import hashlib
import io
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from controllers import conversationController as cc
from middlewares.auth import Identity, require_identity
from middlewares.conn_database import get_db
from models.appModels import TripShare
from schemas.api import SCHEMA_VERSION

router = APIRouter()
public_router = APIRouter()

SLOT_WINDOWS = {"morning": ("09:00", 180), "afternoon": ("13:00", 240), "evening": ("19:00", 120), "night": ("21:00", 120)}
SLOT_LABEL = {"morning": "Morning", "afternoon": "Afternoon", "evening": "Evening", "night": "Night"}


def _trip(db: Session, ident: Identity, trip_id: str):
    c = cc.get_owned(db, ident.sub, trip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Trip not found.")
    if not c.itinerary or not (c.itinerary.get("days")):
        raise HTTPException(status_code=409, detail="This conversation doesn't have a day-by-day plan yet.")
    return c


def _entities(c) -> Dict[str, Dict[str, Any]]:
    """All entities in the trip's answers, by id (latest wins)."""
    out: Dict[str, Dict[str, Any]] = {}
    for m in c.messages:
        for key in ("flights", "hotels", "attractions", "restaurants", "cars"):
            for e in ((m.data or {}).get(key) or []):
                if isinstance(e, dict) and e.get("id"):
                    out[e["id"]] = e
    return out


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "trip").split(",")[0].lower()).strip("-") or "trip"


# -------------------------------------------------------------------- ics
def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not parts else 74):
            parts.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    parts.append(cur.decode("utf-8"))
    return "\r\n ".join(parts)


def itinerary_ics(it: Dict[str, Any], entities: Dict[str, Dict[str, Any]], uid_seed: str) -> str:
    dest = (it.get("trip") or {}).get("destination") or {}
    tz = dest.get("timezone")
    where = dest.get("name") or ""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//TravelBuddy//Itinerary//EN", "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{_esc('Trip to ' + where)}"]
    if tz:
        lines.append(f"X-WR-TIMEZONE:{tz}")
    for di, day in enumerate(it.get("days") or []):
        for ii, item in enumerate(day.get("items") or []):
            start, length = SLOT_WINDOWS.get(item.get("slot"), SLOT_WINDOWS["morning"])
            if re.fullmatch(r"\d{2}:\d{2}", item.get("start_time") or ""):
                start = item["start_time"]
            length = item.get("duration_minutes") or length
            try:
                t0 = datetime.strptime(f"{day['date']} {start}", "%Y-%m-%d %H:%M")
            except (KeyError, ValueError):
                continue
            t1 = t0 + timedelta(minutes=length)
            tzp = f";TZID={tz}" if tz else ""
            ent = entities.get(item.get("ref") or "") or {}
            desc = "\n".join(x for x in (item.get("note"), ent.get("address")) if x)
            uid = hashlib.sha1(f"{uid_seed}-{di}-{ii}-{item.get('title')}".encode()).hexdigest()[:20]
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}@travelbuddy",
                f"DTSTAMP:{stamp}",
                f"DTSTART{tzp}:{t0.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND{tzp}:{t1.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{_esc(item.get('title') or 'Plan')}",
            ]
            if desc:
                lines.append(f"DESCRIPTION:{_esc(desc)}")
            loc = ent.get("address") or where
            if loc:
                lines.append(f"LOCATION:{_esc(loc)}")
            lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"


# -------------------------------------------------------------------- pdf
_PDF_REPLACE = {"→": "->", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...", "•": "-", "★": "*", "\u202f": " ", "\u2009": " "}


def _latin1(text: Any) -> str:
    s = str(text or "")
    for a, b in _PDF_REPLACE.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def itinerary_pdf(it: Dict[str, Any], entities: Dict[str, Dict[str, Any]], answer: Optional[str]) -> bytes:
    from fpdf import FPDF

    trip = it.get("trip") or {}
    dest = (trip.get("destination") or {}).get("name") or "Your trip"
    raspberry, ink, muted = (170, 68, 101), (55, 65, 81), (91, 100, 114)

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()
    pdf.set_title(_latin1(f"Trip to {dest}"))
    pdf.set_author("TravelBuddy")

    pdf.set_text_color(*raspberry)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 11, _latin1(f"Trip to {dest}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*muted)
    pdf.set_font("Helvetica", "", 11)
    travelers = trip.get("travelers") or {}
    meta = [f"{trip.get('start_date', '')} to {trip.get('end_date', '')}"]
    if trip.get("origin"):
        meta.append(f"from {trip['origin']}")
    if travelers.get("adults"):
        meta.append(f"{travelers['adults']} adult{'s' if travelers['adults'] > 1 else ''}")
    pdf.cell(0, 6, _latin1(" - ".join(meta)), new_x="LMARGIN", new_y="NEXT")
    if it.get("summary"):
        pdf.ln(2)
        pdf.set_text_color(*ink)
        pdf.multi_cell(0, 5.5, _latin1(it["summary"]))
    pdf.ln(4)

    for i, day in enumerate(it.get("days") or []):
        if pdf.get_y() > 250:
            pdf.add_page()
        pdf.set_draw_color(233, 233, 233)
        pdf.line(18, pdf.get_y(), 192, pdf.get_y())
        pdf.ln(3)
        pdf.set_text_color(*raspberry)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 7, _latin1(f"Day {i + 1} - {day.get('title', '')}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*muted)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.cell(0, 5, _latin1(day.get("date", "")), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        for item in day.get("items") or []:
            ent = entities.get(item.get("ref") or "") or {}
            pdf.set_text_color(*muted)
            pdf.set_font("Helvetica", "B", 8.5)
            label = SLOT_LABEL.get(item.get("slot"), "").upper()
            if item.get("start_time"):
                label += f"  {item['start_time']}"
            pdf.cell(32, 5.5, _latin1(label))
            pdf.set_text_color(*ink)
            pdf.set_font("Helvetica", "B", 10.5)
            title = item.get("title", "")
            if ent.get("rating"):
                title += f"  ({ent['rating']}/5)"
            pdf.multi_cell(0, 5.5, _latin1(title), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*muted)
            for extra in (item.get("note"), ent.get("address")):
                if extra:
                    pdf.set_x(50)
                    pdf.multi_cell(0, 4.8, _latin1(extra), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        pdf.ln(2)

    pdf.set_text_color(*muted)
    pdf.set_font("Helvetica", "I", 8)
    pdf.ln(4)
    pdf.multi_cell(0, 4, _latin1(f"Generated by TravelBuddy on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}. Prices, hours and availability change; check with the provider before you go."))
    return bytes(pdf.output())


@router.get("/{trip_id}/export")
async def export_trip(
    trip_id: str,
    format: str = Query("ics", pattern="^(ics|pdf)$"),
    ident: Identity = Depends(require_identity),
    db: Session = Depends(get_db),
):
    c = _trip(db, ident, trip_id)
    ents = _entities(c)
    name = f"travelbuddy-{_slug(((c.itinerary.get('trip') or {}).get('destination') or {}).get('name'))}-{(c.itinerary.get('trip') or {}).get('start_date', '')}"
    if format == "ics":
        body = itinerary_ics(c.itinerary, ents, c.id).encode("utf-8")
        return Response(body, media_type="text/calendar; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}.ics"'})
    answer = next((m.content for m in reversed(c.messages) if m.role == "assistant"), None)
    body = itinerary_pdf(c.itinerary, ents, answer)
    return Response(body, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'})


def _share_base(request: Request) -> str:
    if os.getenv("FRONTEND_URL"):
        return os.getenv("FRONTEND_URL").rstrip("/")
    # Behind Heroku's router the app sees http://; trust its forwarded headers for the public link.
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}".rstrip("/")


def _snapshot(c) -> Dict[str, Any]:
    last = next((m for m in reversed(c.messages) if m.role == "assistant" and (m.data or {}).get("itinerary")), None)
    data = dict((last.data if last else {}) or {})
    keep = {k: data.get(k) for k in ("trip", "itinerary", "flights", "hotels", "attractions", "restaurants", "weather", "cars", "sections") if data.get(k) is not None}
    keep["itinerary"] = c.itinerary
    return {
        "title": c.title,
        "answer": last.content if last else "",
        "data": keep,
        "shared_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{trip_id}/share")
async def share_trip(trip_id: str, request: Request, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
    """Create (or refresh) a read-only public link to this itinerary."""
    c = _trip(db, ident, trip_id)
    row = db.query(TripShare).filter(TripShare.conversation_id == c.id, TripShare.user_sub == ident.sub).first()
    if row:
        row.snapshot = _snapshot(c)
    else:
        row = TripShare(token=secrets.token_urlsafe(16)[:22], conversation_id=c.id, user_sub=ident.sub, snapshot=_snapshot(c))
        db.add(row)
    db.commit()
    return {"token": row.token, "url": f"{_share_base(request)}/share/{row.token}", "schema_version": SCHEMA_VERSION}


@public_router.get("/{token}")
async def get_shared(token: str):
    """Public read-only trip. No auth; exposes only the snapshot taken when sharing."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,40}", token):
        raise HTTPException(status_code=404, detail="This link isn't valid.")
    from middlewares.conn_database import SessionLocal

    db = SessionLocal()
    try:
        row = db.query(TripShare).filter(TripShare.token == token).first()
        if not row:
            raise HTTPException(status_code=404, detail="This trip link was removed or never existed.")
        return {**row.snapshot, "token": row.token, "schema_version": SCHEMA_VERSION}
    finally:
        db.close()
