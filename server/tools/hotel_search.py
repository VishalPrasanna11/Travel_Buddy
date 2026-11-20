from langchain_core.tools import tool
from typing import Dict, Any
import logging
import httpx
from tools.routestack_auth import headers, BASE_URL
from schemas.entities import Hotel, Photo, Price, make_id, now_iso, to_float

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


def normalize_hotel(h: Dict[str, Any], currency: str, check_in: str, check_out: str, fetched_at: str) -> Hotel:
    photos = []
    for p in (h.get("images") or h.get("photos") or [])[:8]:
        url = p if isinstance(p, str) else (p.get("url") if isinstance(p, dict) else None)
        if url:
            photos.append(Photo(url=url))
    facilities = h.get("facilities") or []
    names = [f.get("name", "") for f in facilities if isinstance(f, dict) and f.get("name")]
    return Hotel(
        id=make_id("ht", h.get("id"), h.get("name")),
        fetched_at=fetched_at,
        name=h.get("name", ""),
        address=h.get("address") or None,
        star_rating=to_float(h.get("starRating")),
        guest_rating=to_float(h.get("guestRating") or h.get("reviewScore")),
        price=Price.maybe(h.get("ourprice", h.get("baseprice")), currency, basis="total", as_of=fetched_at,
                          published=to_float(h.get("publishedRate")), saving=to_float(h.get("saving"))),
        check_in=check_in,
        check_out=check_out,
        amenity_names=names[:20],
        photos=photos,
        hotel_id=str(h.get("id", "")) or None,
        provider=h.get("providerName") or None,
    )


def _search_hotels(params: Dict[str, str]) -> Dict[str, Any]:
    city = params.get("city", "")
    check_in = params.get("checkInDate", "")
    check_out = params.get("checkOutDate", "")
    adults = int(params.get("adults", "2"))
    rooms = int(params.get("rooms", "1"))

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
        hotels = [
            normalize_hotel(h, currency, check_in, check_out, fetched_at).model_dump(mode="json", exclude_none=True)
            for h in raw_hotels[:10]
            if isinstance(h, dict)
        ]

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
