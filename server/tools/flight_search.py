from langchain_core.tools import tool
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from zoneinfo import ZoneInfo
import logging
import re
import httpx
from tools import offer_cache
from tools.routestack_auth import headers, BASE_URL
from schemas.entities import Baggage, Flight, FlightEndpoint, FlightSegment, Price, make_id, now_iso, to_float

MAX_RESULTS = 10

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


_AIRPORTS = None


def _airport_tz(code: str) -> Optional[ZoneInfo]:
    """IANA zone for an IATA airport code (airportsdata), cached."""
    global _AIRPORTS
    if _AIRPORTS is None:
        try:
            import airportsdata
            _AIRPORTS = airportsdata.load("IATA")
        except Exception as e:  # dependency missing: times stay offset-less
            logger.warning(f"airportsdata unavailable: {e}")
            _AIRPORTS = {}
    tz = (_AIRPORTS.get((code or "").upper()) or {}).get("tz")
    try:
        return ZoneInfo(tz) if tz else None
    except Exception:
        return None


def _localize(at: Optional[str], airport: str) -> Tuple[Optional[str], Optional[str], Optional[datetime]]:
    """Provider times are airport-local without an offset. Attach the airport's
    UTC offset so clients can show correct local times and compute durations."""
    if not at:
        return None, None, None
    try:
        naive = datetime.fromisoformat(at.replace("Z", ""))
    except ValueError:
        return at, None, None
    tz = _airport_tz(airport)
    if naive.tzinfo is None and tz:
        aware = naive.replace(tzinfo=tz)
    elif naive.tzinfo is not None:
        aware = naive
    else:
        return naive.isoformat(), None, None
    iso = aware.isoformat()
    offset = iso[-6:] if iso[-6] in "+-" else "+00:00"
    return iso, offset, aware


def _iso_duration(mins: Optional[int]) -> Optional[str]:
    if not mins or mins <= 0:
        return None
    return f"PT{mins // 60}H{mins % 60}M" if mins % 60 else f"PT{mins // 60}H"


def _bag(value: Optional[str], kind: str) -> Optional[str]:
    """'0PC' -> 'No checked bag', '1PC' -> '1 checked bag', '23KG' -> '23 kg', '1 Piece' -> '1 piece'."""
    if not value:
        return None
    v = str(value).strip()
    m = re.fullmatch(r"(\d+)\s*(PC|P|PIECES?)", v, re.I)
    if m:
        n = int(m.group(1))
        if n == 0:
            return f"No {kind} bag"
        return f"{n} {kind} bag{'s' if n > 1 else ''}"
    m = re.fullmatch(r"(\d+)\s*(KG|K)", v, re.I)
    if m:
        return f"{m.group(1)} kg {kind}"
    return v[0].upper() + v[1:].lower() if v.isupper() else v


def _adult_allowance(items) -> Optional[str]:
    for it in items or []:
        if isinstance(it, dict) and str(it.get("type", "Adult")).lower().startswith("adult"):
            return it.get("value")
    first = (items or [None])[0]
    return first.get("value") if isinstance(first, dict) else None


def _segment(s: Dict[str, Any], cabin_class: str) -> Tuple[FlightSegment, Optional[datetime], Optional[datetime]]:
    mins = _minutes(s.get("triptime"))
    dep_iso, dep_off, dep_dt = _localize(s.get("departureTime"), s.get("departure", ""))
    arr_iso, arr_off, arr_dt = _localize(s.get("arrivalTime"), s.get("arrival", ""))
    if dep_dt and arr_dt and not mins:
        mins = int((arr_dt - dep_dt).total_seconds() // 60)
    seg = FlightSegment(
        carrier=s.get("flightCode", "") or "",
        carrier_name=s.get("airline") or None,
        flight_number=f"{s.get('flightCode', '')}{s.get('flightNumber', '')}",
        departure=FlightEndpoint(airport=s.get("departure", ""), airport_name=s.get("departairport") or None,
                                 at=dep_iso, utc_offset=dep_off),
        arrival=FlightEndpoint(airport=s.get("arrival", ""), airport_name=s.get("arrivalairport") or None,
                               at=arr_iso, utc_offset=arr_off),
        duration_minutes=mins or None,
        duration=_iso_duration(mins),
        cabin_class=s.get("cabin") or cabin_class,
        fare_family=s.get("fareFamily") or None,
        checked_baggage=_bag(_adult_allowance(s.get("checkInBaggage")), "checked"),
        cabin_baggage=_bag(_adult_allowance(s.get("cabinBaggage")), "cabin"),
        seats_left=s.get("remainingSeats"),
    )
    return seg, dep_dt, arr_dt


def _leg(raw_segments, cabin_class: str) -> Tuple[List[FlightSegment], Optional[int]]:
    """Segments with layovers, plus door-to-door minutes from real UTC times."""
    parsed = [_segment(s, cabin_class) for s in raw_segments]
    segs = [p[0] for p in parsed]
    for i in range(len(parsed) - 1):
        arr, nxt = parsed[i][2], parsed[i + 1][1]
        if arr and nxt:
            segs[i].layover_minutes = max(0, int((nxt - arr).total_seconds() // 60))
    total = None
    if parsed and parsed[0][1] and parsed[-1][2]:
        total = int((parsed[-1][2] - parsed[0][1]).total_seconds() // 60)
    elif segs:
        total = sum((s.duration_minutes or 0) + (s.layover_minutes or 0) for s in segs) or None
    return segs, total


def normalize_flight(itin: Dict[str, Any], cabin_class: str, adults: int, fetched_at: str, currency: str = "USD") -> Flight:
    raw = [s for s in (itin.get("flights") or []) if s]
    outbound_raw = [s for s in raw if str(s.get("legindicator", 0)) in ("0", "None")]
    return_raw = [s for s in raw if str(s.get("legindicator", 0)) == "1"]
    if not outbound_raw:
        outbound_raw, return_raw = raw, []
    segs, total_mins = _leg(outbound_raw, cabin_class)
    ret, ret_mins = _leg(return_raw, cabin_class) if return_raw else ([], None)

    pax = max(int(itin.get("quantity") or adults or 1), 1)
    total = to_float(itin.get("ourprice") or itin.get("totalFare") or itin.get("baseFare"))
    price = None
    if total is not None:
        price = Price(amount=total, currency=currency, basis="total", total=total,
                      per_traveler=round(total / pax, 2), taxes_included=True, as_of=fetched_at)
    first, last = (segs[0], segs[-1]) if segs else (None, None)
    checked = {s.checked_baggage for s in segs if s.checked_baggage}
    cabin = {s.cabin_baggage for s in segs if s.cabin_baggage}
    penalties = itin.get("penaltydetails") or []
    refundable = None
    if penalties and isinstance(penalties[0], dict) and "refundAllowed" in penalties[0]:
        refundable = bool(penalties[0].get("refundAllowed"))
    return Flight(
        id=make_id("fl", itin.get("fareSourceCode"), *[s.flight_number for s in segs + ret]),
        fetched_at=fetched_at,
        carrier=first.carrier if first else "",
        carrier_name=first.carrier_name if first else None,
        origin=first.departure.airport if first else "",
        destination=last.arrival.airport if last else "",
        departure_at=first.departure.at if first else None,
        arrival_at=last.arrival.at if last else None,
        duration_minutes=total_mins,
        duration=_iso_duration(total_mins),
        return_duration_minutes=ret_mins,
        stops=max(len(segs) - 1, 0),
        return_stops=max(len(ret) - 1, 0) if ret else None,
        cabin_class=(first.cabin_class if first else None) or cabin_class,
        fare_family=first.fare_family if first else None,
        segments=segs,
        return_segments=ret,
        price=price,
        baggage=Baggage(checked=" / ".join(sorted(checked)) or None, cabin=" / ".join(sorted(cabin)) or None) if (checked or cabin) else None,
        refundable=refundable,
        fare_source_code=itin.get("fareSourceCode") or None,
        bookable=bool(itin.get("fareSourceCode")),
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
        currency = data.get("currency") or "USD"
        flights = []
        for itin in raw_itineraries[:MAX_RESULTS]:
            if not itin:
                continue
            f = normalize_flight(itin, cabin_class, adults, fetched_at, currency)
            # Keep the raw offer server-side for the Book button (get-payment-url).
            offer_cache.put(f.id, "flight", {
                "flight": itin,
                "origin": origin_code,
                "destination": dest_code,
                "departureDate": departure_date,
                "returnDate": return_date or None,
                "adults": adults,
                "tripType": trip_type,
                "type": trip_type,
                "correlationId": data.get("correlationId"),
                "searchFilterObj": data.get("searchFilterObj"),
                "currency": currency,
            })
            flights.append(f.model_dump(mode="json", exclude_none=True))

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
