from langchain_core.tools import tool
from typing import Dict, Any
import logging
import httpx
from tools.routestack_auth import headers, BASE_URL

logger = logging.getLogger("hotel_search")


def _search_destination(city: str) -> Dict[str, Any]:
    resp = httpx.post(
        f"{BASE_URL}/mcp/hotel/search-destinations",
        headers=headers(),
        json={"query": city},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    destinations = data.get("result") or []
    if not destinations:
        return {}
    # Prefer City-type destinations (they may lack coordinates but have a valid id)
    for d in destinations:
        if isinstance(d, dict) and d.get("type") == "City":
            return d
    # Fall back to first destination with coordinates
    for d in destinations:
        if isinstance(d, dict) and d.get("coordinates"):
            return d
    first = destinations[0]
    return first if isinstance(first, dict) else {}


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
        hotels = []
        for h in raw_hotels[:10]:
            photos = h.get("images") or h.get("photos") or []
            photo_url = photos[0] if photos and isinstance(photos[0], str) else None
            if not photo_url and photos and isinstance(photos[0], dict):
                photo_url = photos[0].get("url", "")

            facilities = h.get("facilities", [])
            facility_names = [f.get("name", "") for f in facilities if isinstance(f, dict)]

            hotels.append({
                "name": h.get("name", ""),
                "address": h.get("address", ""),
                "rating": h.get("starRating", 0),
                "review_score": h.get("guestRating") or h.get("reviewScore", ""),
                "price": f"{currency} {h.get('ourprice', h.get('baseprice', 'N/A'))}",
                "published_price": f"{currency} {h.get('publishedRate', '')}" if h.get("publishedRate") else None,
                "saving": f"{currency} {h.get('saving', '')}" if h.get("saving") else None,
                "photo_url": photo_url,
                "facilities": facility_names[:10],
                "hotelId": h.get("id", ""),
                "provider": h.get("providerName", ""),
            })

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
