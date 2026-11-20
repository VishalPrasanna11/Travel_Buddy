from langchain_core.tools import tool
from typing import Dict, Any
import logging
import httpx
from tools.routestack_auth import headers, BASE_URL
from schemas.entities import Flight, FlightEndpoint, FlightSegment, Price, make_id, now_iso

logger = logging.getLogger("flight_search")


_LOCATION_CACHE: Dict[str, list] = {}


def _lookup_location(term: str) -> list:
    """Airport/city lookup. Tries the full term, then just the city part
    ("Boston, MA, USA" -> "Boston"), since the provider matches short names."""
    candidates = [term.strip()]
    head = term.split(",")[0].strip()
    if head and head not in candidates:
        candidates.append(head)
    for cand in candidates:
        key = cand.lower()
        if key in _LOCATION_CACHE:
            return _LOCATION_CACHE[key]
        resp = httpx.post(
            f"{BASE_URL}/mcp/flight/locations",
            headers=headers(),
            json={"term": cand},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json().get("result") or []
        if result:
            _LOCATION_CACHE[key] = result
            return result
    return []


def _minutes(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _segment(s: Dict[str, Any], cabin_class: str) -> FlightSegment:
    mins = _minutes(s.get("triptime"))
    return FlightSegment(
        carrier=s.get("flightCode", "") or s.get("airline", ""),
        carrier_name=s.get("airline") or None,
        flight_number=f"{s.get('flightCode', '')}{s.get('flightNumber', '')}",
        departure=FlightEndpoint(airport=s.get("departure", ""), airport_name=s.get("departairport") or None, at=s.get("departureTime") or None),
        arrival=FlightEndpoint(airport=s.get("arrival", ""), airport_name=s.get("arrivalairport") or None, at=s.get("arrivalTime") or None),
        duration_minutes=mins or None,
        duration=f"PT{mins // 60}H{mins % 60}M" if mins else None,
        cabin_class=s.get("cabin") or cabin_class,
    )


def normalize_flight(itin: Dict[str, Any], cabin_class: str, adults: int, fetched_at: str) -> Flight:
    segs = [_segment(s, cabin_class) for s in (itin.get("flights") or []) if s]
    currency = itin.get("currency") or "USD"
    total = itin.get("ourprice") or itin.get("totalFare") or itin.get("baseFare")
    price = Price.maybe(total, currency, basis="total", as_of=fetched_at)
    first, last = (segs[0], segs[-1]) if segs else (None, None)
    return Flight(
        id=make_id("fl", itin.get("fareSourceCode"), *[s.flight_number for s in segs]),
        fetched_at=fetched_at,
        carrier=first.carrier if first else "",
        carrier_name=first.carrier_name if first else None,
        origin=first.departure.airport if first else "",
        destination=last.arrival.airport if last else "",
        departure_at=first.departure.at if first else None,
        arrival_at=last.arrival.at if last else None,
        duration_minutes=sum(s.duration_minutes or 0 for s in segs) or None,
        stops=int(itin.get("stops", max(len(segs) - 1, 0)) or 0),
        cabin_class=cabin_class,
        segments=segs,
        price=price,
        fare_source_code=itin.get("fareSourceCode") or None,
    )


def _search_flights(params: Dict[str, str]) -> Dict[str, Any]:
    origin = params.get("origin", "").strip()
    destination = params.get("destination", "").strip()
    departure_date = params.get("departure_date", "")
    return_date = params.get("return_date", "")
    adults = int(params.get("adults", "1"))
    cabin_class = params.get("cabin_class", "Economy")

    if not origin or not destination or not departure_date:
        return {"error": "Missing required parameters: origin, destination, departure_date"}

    try:
        origin_locs = _lookup_location(origin)
        if not origin_locs:
            return {"error": f"Could not find airport/city for: {origin}"}
        dest_locs = _lookup_location(destination)
        if not dest_locs:
            return {"error": f"Could not find airport/city for: {destination}"}

        origin_code = origin_locs[0].get("code", origin)
        dest_code = dest_locs[0].get("code", destination)

        trip_type = "RoundTrip" if return_date else "OneWay"
        search_body = {
            "origin": origin_code,
            "destination": dest_code,
            "departureDate": departure_date,
            "adults": adults,
            "cabinClass": cabin_class,
            "type": trip_type,
        }
        if return_date:
            search_body["returnDate"] = return_date

        resp = httpx.post(
            f"{BASE_URL}/mcp/flight/search",
            headers=headers(),
            json=search_body,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_itineraries = data.get("result") or data.get("results") or []
        if raw_itineraries is None:
            raw_itineraries = []
        fetched_at = now_iso()
        flights = [
            normalize_flight(itin, cabin_class, adults, fetched_at)
            for itin in raw_itineraries[:10]
            if itin is not None
        ]
        flights = [f.model_dump(mode="json", exclude_none=True) for f in flights]

        if not flights:
            return {
                "flights": [],
                "message": f"No flights found from {origin} to {destination} on {departure_date}",
            }

        return {
            "flights": flights,
            "count": len(flights),
            "origin": origin_code,
            "destination": dest_code,
            "departure_date": departure_date,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"RouteStack API error: {e.response.status_code} {e.response.text}")
        return {"error": f"Flight search failed: {e.response.text}"}
    except Exception as e:
        logger.error(f"Flight search error: {str(e)}")
        return {"error": f"Flight search failed: {str(e)}"}


@tool
def flight_search(input_str: str) -> Dict[str, Any]:
    """
    Finds live flights using the RouteStack travel API.
    Input should be a URL-style string, e.g., 'origin=NYC&destination=Paris&departure_date=2025-05-01'.
    Optional params: return_date, adults, cabin_class (Economy/Business/First).
    """
    params = dict(param.split("=", 1) for param in input_str.split("&") if "=" in param)
    if "from" in params and "origin" not in params:
        params["origin"] = params.pop("from")
    if "to" in params and "destination" not in params:
        params["destination"] = params.pop("to")
    if "departureDate" in params and "departure_date" not in params:
        params["departure_date"] = params.pop("departureDate")
    if "returnDate" in params and "return_date" not in params:
        params["return_date"] = params.pop("returnDate")
    return _search_flights(params)
