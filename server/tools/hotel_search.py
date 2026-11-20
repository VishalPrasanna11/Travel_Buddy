from langchain_core.tools import tool
from typing import Dict, Any
import logging
import re
import httpx
from tools.routestack_auth import headers, BASE_URL
from schemas.entities import Hotel, LatLng, Photo, Price, make_id, now_iso, to_float
from tools import offer_cache
from datetime import datetime
from typing import List, Optional, Tuple

logger = logging.getLogger("hotel_search")


_DEST_CACHE: Dict[str, Dict[str, Any]] = {}


def _search_destination(city: str) -> Dict[str, Any]:
    """Resolve a city to a RouteStack destination. The provider matches short
    names best ("Lisbon" finds far more hotels than "Lisbon, Portugal"), so we
    query the city part and use any country part to pick the right match."""
    parts = [p.strip() for p in city.split(",") if p.strip()]
    head = parts[0] if parts else city
    hint = parts[-1].lower() if len(parts) > 1 else ""
    key = city.lower()
    if key in _DEST_CACHE:
        return _DEST_CACHE[key]
    resp = httpx.post(
        f"{BASE_URL}/mcp/hotel/search-destinations",
        headers=headers(),
        json={"query": head},
        timeout=15,
    )
    resp.raise_for_status()
    destinations = [d for d in (resp.json().get("result") or []) if isinstance(d, dict)]
    if not destinations:
        return {}
    cities = [d for d in destinations if d.get("type") == "City"]
    pick = None
    if hint:
        pick = next((d for d in cities if hint in (d.get("fullName") or "").lower()), None)
    pick = pick or (cities[0] if cities else None)
    pick = pick or next((d for d in destinations if d.get("coordinates")), destinations[0])
    _DEST_CACHE[key] = pick
    return pick


AMENITY_CODES = [
    ("WIFI", ("wifi", "wi-fi", "internet")),
    ("POOL", ("pool",)),
    ("SPA", ("spa", "sauna", "massage")),
    ("GYM", ("fitness", "gym")),
    ("PARKING", ("parking",)),
    ("BREAKFAST", ("breakfast",)),
    ("RESTAURANT", ("restaurant",)),
    ("BAR", ("bar", "lounge")),
    ("AIR_CONDITIONING", ("air condition",)),
    ("AIRPORT_SHUTTLE", ("airport shuttle", "airport transfer")),
    ("PETS_ALLOWED", ("pet",)),
    ("ACCESSIBLE", ("wheelchair", "accessible")),
    ("LAUNDRY", ("laundry", "dry cleaning")),
    ("KITCHEN", ("kitchen",)),
    ("ROOM_SERVICE", ("room service",)),
    ("BUSINESS_CENTER", ("business center", "business centre", "meeting", "conference")),
    ("FRONT_DESK_24H", ("24-hour front desk", "24-hour reception")),
]


def amenity_codes(names: List[str]) -> List[str]:
    """Typed amenity codes from the provider's free-text facility names."""
    out: List[str] = []
    text = " | ".join(n.lower() for n in names)
    for code, needles in AMENITY_CODES:
        if any(re.search(rf"\b{re.escape(n)}(?:s|es)?\b", text) for n in needles):
            out.append(code)
    return out


def _nights(check_in: str, check_out: str) -> Optional[int]:
    try:
        d0 = datetime.strptime(check_in, "%Y-%m-%d").date()
        d1 = datetime.strptime(check_out, "%Y-%m-%d").date()
        return max((d1 - d0).days, 1)
    except (TypeError, ValueError):
        return None


def _address(h: Dict[str, Any]) -> Optional[str]:
    if isinstance(h.get("address"), str) and h["address"].strip():
        return h["address"].strip()
    a = ((h.get("contact") or {}).get("address")) or {}
    if not isinstance(a, dict):
        return None
    parts = [a.get("line1"), a.get("line2"), (a.get("city") or {}).get("name"), (a.get("country") or {}).get("name")]
    return ", ".join(p for p in parts if p) or None


def _coords(h: Dict[str, Any]) -> Optional[LatLng]:
    for key in ("geoCode", "geocode", "coordinates", "location"):
        c = h.get(key)
        if isinstance(c, dict):
            lat = c.get("lat") or c.get("latitude")
            lng = c.get("long") or c.get("lng") or c.get("lon") or c.get("longitude")
            if lat is not None and lng is not None:
                return LatLng(lat=float(lat), lng=float(lng))
    geo = ((h.get("contact") or {}).get("geoLocation")) or {}
    if geo.get("lat") is not None and (geo.get("long") or geo.get("lng")) is not None:
        return LatLng(lat=float(geo["lat"]), lng=float(geo.get("long") or geo.get("lng")))
    return None


def _cancellation(options: Dict[str, Any]) -> Tuple[Optional[str], Optional[bool]]:
    if not options:
        return None, None
    if options.get("freeCancellation"):
        return "Free cancellation (see the provider's terms for the deadline).", True
    if options.get("refundable") is True:
        return "Refundable rate; cancellation fees may apply.", True
    if options.get("refundable") is False:
        return "Non-refundable rate.", False
    return None, None


def normalize_hotel(h: Dict[str, Any], currency: str, check_in: str, check_out: str, fetched_at: str) -> Hotel:
    photos: List[Photo] = []
    seen = set()
    candidates = [h.get("heroImage")] + list(h.get("images") or h.get("photos") or [])
    for p in candidates:
        url = p if isinstance(p, str) else (p.get("url") if isinstance(p, dict) else None)
        if url and url not in seen:
            seen.add(url)
            photos.append(Photo(url=url))
        if len(photos) >= 8:
            break
    facilities = h.get("facilities") or []
    names = [f.get("name", "") for f in facilities if isinstance(f, dict) and f.get("name")]
    names += [m for m in (h.get("mainamenity") or []) if isinstance(m, str)]
    options = h.get("options") or {}
    if options.get("freeBreakfast"):
        names.append("Free breakfast")
    nights = _nights(check_in, check_out)
    total = to_float(h.get("ourprice") or h.get("baseprice"))
    price = nightly = None
    if total:
        price = Price(amount=total, currency=currency, basis="total", total=total,
                      published=to_float(h.get("publishedRate")), saving=to_float(h.get("saving")), as_of=fetched_at)
        if nights:
            nightly = Price(amount=round(total / nights, 2), currency=currency, basis="per_night", total=total, as_of=fetched_at)
    cancel_text, refundable = _cancellation(options)
    reviews = h.get("reviews") or {}
    return Hotel(
        id=make_id("ht", h.get("id"), h.get("name")),
        fetched_at=fetched_at,
        name=h.get("name", ""),
        address=_address(h),
        location=_coords(h),
        star_rating=to_float(h.get("starRating")),
        guest_rating=to_float(h.get("guestRating") or h.get("reviewScore") or (reviews.get("rating") if isinstance(reviews, dict) else None)),
        review_count=(reviews.get("count") if isinstance(reviews, dict) else None),
        price=price,
        nightly_price=nightly,
        nights=nights,
        check_in=check_in,
        check_out=check_out,
        check_in_time=h.get("checkInTime") or None,
        check_out_time=h.get("checkOutTime") or None,
        amenities=amenity_codes(names),
        amenity_names=list(dict.fromkeys(n for n in names if n))[:24],
        photos=photos,
        cancellation_policy=cancel_text,
        refundable=refundable,
        pay_at_hotel=h.get("payAtHotel"),
        free_breakfast=options.get("freeBreakfast"),
        chain=h.get("chain") or None,
        distance_km=to_float(h.get("distancekm")),
        hotel_id=str(h.get("id", "")) or None,
        provider=h.get("providerName") or None,
        bookable=bool(h.get("id")),
    )


def _search_hotels(params: Dict[str, str]) -> Dict[str, Any]:
    city = params.get("city", "")
    check_in = params.get("checkInDate", "")
    check_out = params.get("checkOutDate", "")
    adults = int(params.get("adults", "2"))
    rooms = int(params.get("rooms", "1"))
    currency_pref = params.get("currency")

    if not city:
        return {"error": "Missing required parameter: city"}
    if not check_in or not check_out:
        return {"error": "Missing required parameters: checkInDate, checkOutDate"}

    try:
        dest = _search_destination(city)
        if not dest:
            return {"error": f"Could not find destination for: {city}"}

        dest_id = dest.get("id", "")
        coords = dest.get("coordinates") or {}
        lat = coords.get("lat", 0) if isinstance(coords, dict) else 0
        lng = (coords.get("long") or coords.get("lng") or coords.get("lon", 0)) if isinstance(coords, dict) else 0

        search_body = {
            "destinationId": dest_id,
            "checkIn": check_in,
            "checkOut": check_out,
            "roomCount": rooms,
            "rooms": [{"adults": adults} for _ in range(rooms)],
            "lat": lat,
            "long": lng,
        }
        if currency_pref:
            search_body["currency"] = currency_pref

        resp = httpx.post(
            f"{BASE_URL}/mcp/hotel/search-hotels",
            headers=headers(),
            json=search_body,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        result = data.get("result") or {}
        if not isinstance(result, dict):
            result = {}
        correlation_id = result.get("correlationId", "")
        token = result.get("token", "")
        currency = result.get("currency") or data.get("currency", "USD")

        raw_hotels = result.get("result") or []
        fetched_at = now_iso()
        hotels = []
        for h in raw_hotels[:10]:
            if not isinstance(h, dict):
                continue
            hotel = normalize_hotel(h, currency, check_in, check_out, fetched_at)
            offer_cache.put(hotel.id, "hotel", {
                "hotelId": str(h.get("id", "")),
                "hotelName": h.get("name", ""),
                "token": token,
                "correlationId": correlation_id,
                "checkIn": check_in,
                "checkOut": check_out,
                "rooms": [{"adults": adults, "children": 0, "childAges": []} for _ in range(rooms)],
                "roomCount": rooms,
                "destinationId": dest_id,
                "publishedRate": h.get("publishedRate"),
            })
            hotels.append(hotel.model_dump(mode="json", exclude_none=True))

        if not hotels:
            return {
                "hotels": [],
                "message": f"No hotels found in {city} for {check_in} to {check_out}",
            }

        return {
            "hotels": hotels,
            "count": len(hotels),
            "city": city,
            "checkInDate": check_in,
            "checkOutDate": check_out,
            "correlationId": correlation_id,
            "token": token,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"RouteStack API error: {e.response.status_code} {e.response.text}")
        return {"error": f"Hotel search failed: {e.response.text}"}
    except Exception as e:
        logger.error(f"Hotel search error: {str(e)}")
        return {"error": f"Hotel search failed: {str(e)}"}


@tool
def hotel_search(input_str: str) -> Dict[str, Any]:
    """
    Searches for hotels with live pricing using the RouteStack travel API.
    Input should be a URL-style string, e.g., 'city=Paris&checkInDate=2025-05-01&checkOutDate=2025-05-05&adults=2'.
    Optional params: rooms (default 1).
    """
    try:
        params = dict(p.split("=", 1) for p in input_str.split("&") if "=" in p)
        return _search_hotels(params)
    except Exception as e:
        return {"error": f"Failed to process hotel search: {str(e)}"}
