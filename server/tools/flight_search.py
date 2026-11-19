from langchain_core.tools import tool
from typing import Dict, Any
import logging
import httpx
from tools.routestack_auth import headers, BASE_URL

logger = logging.getLogger("flight_search")


def _lookup_location(term: str) -> list:
    resp = httpx.post(
        f"{BASE_URL}/mcp/flight/locations",
        headers=headers(),
        json={"term": term},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


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
        flights = []
        for itin in raw_itineraries[:10]:
            if itin is None:
                continue
            segments = itin.get("flights") or []
            seg_list = []
            for s in segments:
                seg_list.append({
                    "airline": s.get("airline", ""),
                    "flight_number": f"{s.get('flightCode', '')}{s.get('flightNumber', '')}",
                    "origin": s.get("departure", ""),
                    "destination": s.get("arrival", ""),
                    "departure_time": s.get("departureTime", ""),
                    "arrival_time": s.get("arrivalTime", ""),
                    "duration": f"{s.get('triptime', 0) // 60}h {s.get('triptime', 0) % 60}m",
                    "cabin_class": s.get("cabin", cabin_class),
                    "departure_airport": s.get("departairport", ""),
                    "arrival_airport": s.get("arrivalairport", ""),
                })

            price_val = itin.get("ourprice") or itin.get("totalFare") or itin.get("baseFare", "N/A")
            price_str = f"USD {price_val}"

            flights.append({
                "price": price_str,
                "segments": seg_list,
                "stops": itin.get("stops", max(len(seg_list) - 1, 0)),
                "fareSourceCode": itin.get("fareSourceCode", ""),
            })

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
