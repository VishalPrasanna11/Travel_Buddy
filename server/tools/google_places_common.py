"""
Shared Google Places (New) helpers: Text Search, response normalization
through schemas.Place, and photo references.
"""
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from schemas.entities import LatLng, OpeningHours, Photo, Place, Review, make_id, now_iso

logger = logging.getLogger("google_places")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

DETAIL_FIELDS = [
    "id",
    "displayName",
    "formattedAddress",
    "rating",
    "userRatingCount",
    "types",
    "primaryType",
    "location",
    "viewport",
    "utcOffsetMinutes",
    # photos includes photos.authorAttributions (required attribution)
    "photos",
    "regularOpeningHours",
    "priceLevel",
    "editorialSummary",
    "websiteUri",
    "googleMapsUri",
    "reviews",
    "internationalPhoneNumber",
]
SEARCH_FIELDS = [f"places.{f}" for f in DETAIL_FIELDS]
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

# photo ref -> author attributions, so the photo proxy can return them as a header
_PHOTO_ATTRIBUTIONS: Dict[str, List[Dict[str, Any]]] = {}
_MAX_ATTRIBUTIONS = 5000


def attributions_for(ref: str) -> List[Dict[str, Any]]:
    return _PHOTO_ATTRIBUTIONS.get(ref, [])

PRICE_LEVELS = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


def google_api_key() -> Optional[str]:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_PLACE_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")


def photo_url_for(ref: Optional[str], width: int = 640) -> Optional[str]:
    """Client-facing photo URL: our proxy, never a keyed Google URL."""
    if not ref:
        return None
    return f"/api/places/photo/{ref}?w={width}"


def _latlng(raw: Optional[Dict[str, Any]]) -> Optional[LatLng]:
    if not raw or raw.get("latitude") is None or raw.get("longitude") is None:
        return None
    return LatLng(lat=raw["latitude"], lng=raw["longitude"])


def normalize_place(raw: Dict[str, Any], kind: str = "attraction", fetched_at: Optional[str] = None) -> Place:
    fetched_at = fetched_at or now_iso()
    name = (raw.get("displayName") or {}).get("text", "") or raw.get("name", "")
    photos = []
    for p in raw.get("photos") or []:
        ref = p.get("name")
        if not ref:
            continue
        attrs = [
            {"name": a.get("displayName"), "uri": a.get("uri")}
            for a in p.get("authorAttributions") or []
        ]
        if attrs and len(_PHOTO_ATTRIBUTIONS) < _MAX_ATTRIBUTIONS:
            _PHOTO_ATTRIBUTIONS[ref] = attrs
        photos.append(Photo(ref=ref, width=p.get("widthPx"), height=p.get("heightPx"), attributions=attrs))
        if len(photos) >= 6:
            break
    hours = raw.get("regularOpeningHours") or raw.get("currentOpeningHours")
    opening = None
    if hours:
        opening = OpeningHours(
            open_now=hours.get("openNow"),
            weekday_descriptions=hours.get("weekdayDescriptions") or [],
            periods=hours.get("periods") or [],
        )
    viewport = raw.get("viewport")
    vp = None
    if viewport and _latlng(viewport.get("low")) and _latlng(viewport.get("high")):
        vp = {"low": _latlng(viewport["low"]), "high": _latlng(viewport["high"])}
    price_level = raw.get("priceLevel")
    reviews = [
        Review(
            author=(r.get("authorAttribution") or {}).get("displayName"),
            rating=r.get("rating"),
            text=(r.get("text") or r.get("originalText") or {}).get("text"),
            relative_time=r.get("relativePublishTimeDescription"),
        )
        for r in (raw.get("reviews") or [])[:3]
    ]
    place_id = raw.get("id")
    return Place(
        id=make_id("pl", place_id or name, raw.get("formattedAddress")),
        source="google_places",
        fetched_at=fetched_at,
        kind=kind,
        place_id=place_id,
        name=name,
        address=raw.get("formattedAddress"),
        location=_latlng(raw.get("location")),
        viewport=vp,
        rating=raw.get("rating"),
        total_ratings=raw.get("userRatingCount"),
        types=raw.get("types") or [],
        primary_type=raw.get("primaryType"),
        price_level=PRICE_LEVELS.get(price_level) if isinstance(price_level, str) else price_level,
        editorial_summary=(raw.get("editorialSummary") or {}).get("text"),
        opening_hours=opening,
        website=raw.get("websiteUri"),
        google_maps_uri=raw.get("googleMapsUri"),
        phone=raw.get("internationalPhoneNumber"),
        photos=photos,
        reviews=reviews,
        photo_url=photo_url_for(photos[0].ref if photos else None, 400),
        utc_offset_minutes=raw.get("utcOffsetMinutes"),
    )


_DETAILS_CACHE: Dict[str, Place] = {}


def place_details(place_id: str, api_key: str, kind: str = "attraction", timeout: float = 15) -> Optional[Place]:
    """GET places/{id}: hours, reviews, editorial summary, website, phone."""
    if place_id in _DETAILS_CACHE:
        return _DETAILS_CACHE[place_id]
    headers = {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": ",".join(DETAIL_FIELDS)}
    try:
        resp = httpx.get(DETAILS_URL.format(place_id=place_id), headers=headers, timeout=timeout)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Place details failed for {place_id}: {e}")
        return None
    place = normalize_place(resp.json(), kind)
    if len(_DETAILS_CACHE) < 2000:
        _DETAILS_CACHE[place_id] = place
    return place


def text_search(
    query: str,
    api_key: str,
    *,
    fields: List[str] = SEARCH_FIELDS,
    included_type: Optional[str] = None,
    limit: int = 10,
    timeout: float = 30,
) -> List[Dict[str, Any]]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": ",".join(fields),
    }
    body: Dict[str, Any] = {"textQuery": query}
    if included_type:
        body["includedType"] = included_type
    resp = httpx.post(TEXT_SEARCH_URL, headers=headers, json=body, timeout=timeout)
    resp.raise_for_status()
    return (resp.json().get("places") or [])[:limit]
