"""RouteStack car rentals: /mcp/car/locations → /mcp/car/search, normalized through schemas.CarRental."""
import logging
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.tools import tool

from schemas.entities import CarRental, Price, make_id, now_iso, to_float
from tools import offer_cache
from tools.routestack_auth import BASE_URL, headers

logger = logging.getLogger("car_search")

MAX_RESULTS = 8
_LOC_CACHE: Dict[str, Dict[str, Any]] = {}


def _location(term: str) -> Optional[Dict[str, Any]]:
    """Prefer the destination's airport (most rental supply), then the city."""
    key = term.lower()
    if key in _LOC_CACHE:
        return _LOC_CACHE[key]
    head = term.split(",")[0].strip()
    for q in (f"{head} airport", head):
        resp = httpx.post(f"{BASE_URL}/mcp/car/locations", headers=headers(), json={"term": q}, timeout=15)
        resp.raise_for_status()
        results = [r for r in (resp.json().get("result") or []) if isinstance(r, dict)]
        if results:
            pick = next((r for r in results if r.get("type") == "airport"), None) or results[0]
            _LOC_CACHE[key] = pick
            return pick
    return None


def normalize_car(c: Dict[str, Any], fetched_at: str, pickup_at: str, dropoff_at: str) -> CarRental:
    pp = c.get("price_postpaid") or c.get("price_prepaid") or {}
    total = to_float(pp.get("total") or c.get("display_price"))
    currency = pp.get("currency") or "USD"
    days = pp.get("days")
    price = None
    if total is not None:
        price = Price(amount=total, currency=currency, basis="total", total=total, as_of=fetched_at,
                      per_traveler=None)
    pickup, dropoff = c.get("pickup") or {}, c.get("dropoff") or {}
    partner = c.get("partner") or {}
    features = [f.lower() for f in c.get("features") or []]
    fare_code = pp.get("fareCode") or c.get("fareCode")
    return CarRental(
        id=make_id("car", fare_code or c.get("vehicle_code"), partner.get("code"), total),
        fetched_at=fetched_at,
        vendor=partner.get("name"),
        vendor_logo=partner.get("logo"),
        name=c.get("name") or c.get("description") or "Rental car",
        category=c.get("type_name") or c.get("description"),
        transmission="Automatic" if c.get("hasAMT") or any("automatic" in f for f in features) else "Manual",
        seats=c.get("passengers"),
        bags=c.get("bags"),
        air_conditioning=c.get("hasAC"),
        image_url=c.get("heroImage") or next((i.get("url") for i in (c.get("images") or []) if isinstance(i, dict)), None),
        pickup_location=pickup.get("location"),
        dropoff_location=dropoff.get("location"),
        pickup_at=pickup_at,
        dropoff_at=dropoff_at,
        price=price,
        mileage="Unlimited mileage" if pp.get("mileage") else None,
        free_cancellation=pp.get("free_cancellation"),
        days=days,
        bookable=bool(fare_code),
    )


def search_cars(location: str, pickup_date: str, dropoff_date: str, pickup_time: str = "10:00", dropoff_time: str = "10:00") -> Dict[str, Any]:
    if not location or not pickup_date or not dropoff_date:
        return {"error": "Missing location or dates for car search"}
    try:
        loc = _location(location)
        if not loc:
            return {"cars": [], "message": f"No car rental locations found near {location}."}
        pickup = {"name": loc.get("name"), "code": loc.get("code"), "date": pickup_date, "time": pickup_time}
        dropoff = {"name": loc.get("name"), "code": loc.get("code"), "date": dropoff_date, "time": dropoff_time}
        resp = httpx.post(f"{BASE_URL}/mcp/car/search", headers=headers(), json={"pickup": pickup, "dropoff": dropoff}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result") or {}
        raw = result.get("cars") if isinstance(result, dict) else result
        fetched_at = now_iso()
        cars: List[Dict[str, Any]] = []
        for c in sorted([c for c in raw or [] if isinstance(c, dict)], key=lambda c: to_float((c.get("price_postpaid") or {}).get("total") or c.get("display_price")) or 1e12)[:MAX_RESULTS]:
            car = normalize_car(c, fetched_at, f"{pickup_date}T{pickup_time}:00", f"{dropoff_date}T{dropoff_time}:00")
            offer_cache.put(car.id, "car", {"car": c, "pickup": pickup, "dropoff": dropoff, "pickupDate": pickup_date,
                                            "dropoffDate": dropoff_date, "pickupTime": pickup_time, "dropoffTime": dropoff_time,
                                            "correlationId": data.get("correlationId")})
            cars.append(car.model_dump(mode="json", exclude_none=True))
        if not cars:
            return {"cars": [], "message": f"No rental cars available at {loc.get('name')} for those dates."}
        return {"cars": cars, "count": len(cars), "location": loc.get("name")}
    except httpx.HTTPStatusError as e:
        logger.error(f"RouteStack car API error: {e.response.status_code} {e.response.text[:300]}")
        return {"error": "Car search failed at the provider."}
    except Exception as e:
        logger.error(f"Car search error: {e}")
        return {"error": f"Car search failed: {e}"}


@tool
def car_search(input_str: str) -> Dict[str, Any]:
    """
    Finds rental cars with live prices using RouteStack.
    Input: 'location=Lisbon&pickup_date=2027-03-12&dropoff_date=2027-03-15' (optional pickup_time, dropoff_time HH:MM).
    """
    params = dict(p.split("=", 1) for p in input_str.split("&") if "=" in p)
    return search_cars(params.get("location", ""), params.get("pickup_date", ""), params.get("dropoff_date", ""),
                       params.get("pickup_time", "10:00"), params.get("dropoff_time", "10:00"))
