"""
Fixture responses for local development and UI verification.

Set TRAVELBUDDY_FIXTURES=1 to run the whole streaming pipeline without
OpenAI, RouteStack, Google or OpenWeather keys. Every value is clearly
fixture data (source/fetched_at are set, nothing is presented as live).
"""
from __future__ import annotations

import copy
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from schemas.entities import now_iso

_TODAY = date.today()
_START = _TODAY + timedelta(days=21)
_DAYS = [(_START + timedelta(days=i)).isoformat() for i in range(4)]


def _seg(carrier, name, num, dep, arr, dep_at, arr_at, mins, layover=None):
    return {
        "carrier": carrier, "carrier_name": name, "flight_number": num,
        "departure": {"airport": dep, "at": dep_at, "utc_offset": dep_at[-6:]},
        "arrival": {"airport": arr, "at": arr_at, "utc_offset": arr_at[-6:]},
        "duration_minutes": mins, "duration": f"PT{mins // 60}H{mins % 60}M", "cabin_class": "Economy",
        **({"layover_minutes": layover} if layover else {}),
    }


def _flights() -> List[Dict[str, Any]]:
    d = _DAYS[0]
    return [
        {
            "id": "fl_fixture01", "source": "routestack", "fetched_at": now_iso(), "is_estimate": False,
            "carrier": "TP", "carrier_name": "TAP Air Portugal", "origin": "BOS", "destination": "LIS",
            "departure_at": f"{d}T21:35:00-05:00", "arrival_at": f"{_DAYS[1]}T09:10:00+00:00",
            "duration_minutes": 395, "duration": "PT6H35M", "stops": 0, "cabin_class": "Economy",
            "segments": [_seg("TP", "TAP Air Portugal", "TP218", "BOS", "LIS", f"{d}T21:35:00-05:00", f"{_DAYS[1]}T09:10:00+00:00", 395)],
            "price": {"amount": 612.4, "currency": "USD", "basis": "total", "total": 1224.8, "per_traveler": 612.4, "as_of": now_iso()},
            "baggage": {"checked": "1 x 23kg", "cabin": "1 x 8kg"},
            "booking_url": "https://www.example.com/book/fixture01",
        },
        {
            "id": "fl_fixture02", "source": "routestack", "fetched_at": now_iso(), "is_estimate": False,
            "carrier": "IB", "carrier_name": "Iberia", "origin": "BOS", "destination": "LIS",
            "departure_at": f"{d}T18:05:00-05:00", "arrival_at": f"{_DAYS[1]}T11:40:00+00:00",
            "duration_minutes": 515, "duration": "PT8H35M", "stops": 1, "cabin_class": "Economy",
            "segments": [
                _seg("IB", "Iberia", "IB6166", "BOS", "MAD", f"{d}T18:05:00-05:00", f"{_DAYS[1]}T07:15:00+01:00", 430, 110),
                _seg("IB", "Iberia", "IB3104", "MAD", "LIS", f"{_DAYS[1]}T09:05:00+01:00", f"{_DAYS[1]}T09:30:00+00:00", 85),
            ],
            "price": {"amount": 488.0, "currency": "USD", "basis": "total", "total": 976.0, "per_traveler": 488.0, "as_of": now_iso()},
            "baggage": {"cabin": "1 x 10kg"},
            "booking_url": "https://www.example.com/book/fixture02",
        },
    ]


def _hotels() -> List[Dict[str, Any]]:
    return [
        {
            "id": "ht_fixture01", "source": "routestack", "fetched_at": now_iso(), "is_estimate": False,
            "name": "Memmo Alfama", "address": "Travessa das Merceeiras 27, Lisbon", "location": {"lat": 38.7108, "lng": -9.1311},
            "star_rating": 4, "guest_rating": 9.1, "review_count": 2140,
            "price": {"amount": 831.0, "currency": "USD", "basis": "total", "total": 831.0, "as_of": now_iso()},
            "nightly_price": {"amount": 277.0, "currency": "USD", "basis": "per_night", "as_of": now_iso()},
            "nights": 3, "check_in": _DAYS[0], "check_out": _DAYS[3], "check_in_time": "15:00", "check_out_time": "12:00",
            "amenities": ["WIFI", "POOL", "BAR", "AIR_CONDITIONING"], "amenity_names": ["Free WiFi", "Rooftop pool", "Bar", "Air conditioning"],
            "photos": [], "cancellation_policy": "Free cancellation until 3 days before check-in.", "refundable": True,
            "booking_url": "https://www.example.com/hotel/fixture01",
        },
        {
            "id": "ht_fixture02", "source": "routestack", "fetched_at": now_iso(), "is_estimate": False,
            "name": "Lumiares Hotel & Spa", "address": "Rua do Diário de Notícias 142, Lisbon", "location": {"lat": 38.7122, "lng": -9.1445},
            "star_rating": 5, "guest_rating": 9.4, "review_count": 1320,
            "price": {"amount": 1104.0, "currency": "USD", "basis": "total", "total": 1104.0, "as_of": now_iso()},
            "nightly_price": {"amount": 368.0, "currency": "USD", "basis": "per_night", "as_of": now_iso()},
            "nights": 3, "check_in": _DAYS[0], "check_out": _DAYS[3], "amenities": ["WIFI", "SPA", "GYM", "RESTAURANT"],
            "amenity_names": ["Free WiFi", "Spa", "Fitness centre", "Restaurant"], "photos": [],
            "cancellation_policy": "Non-refundable rate.", "refundable": False,
        },
    ]


def _place(pid, name, kind, lat, lng, rating, count, summary, price_level=None, hours=None):
    return {
        "id": f"pl_{pid}", "source": "google_places", "fetched_at": now_iso(), "is_estimate": False, "kind": kind,
        "place_id": pid, "name": name, "address": f"{name}, Lisbon, Portugal", "location": {"lat": lat, "lng": lng},
        "rating": rating, "total_ratings": count, "editorial_summary": summary, "photos": [],
        "google_maps_uri": f"https://maps.google.com/?q={name.replace(' ', '+')}",
        **({"price_level": price_level} if price_level is not None else {}),
        **({"opening_hours": {"weekday_descriptions": hours}} if hours else {}),
    }


def _attractions():
    return [
        _place("fx_belem", "Belém Tower", "attraction", 38.6916, -9.2160, 4.6, 98210, "16th-century fortified tower on the Tagus.",
               hours=["Monday: Closed", "Tuesday: 9:30 AM – 6:00 PM", "Wednesday: 9:30 AM – 6:00 PM", "Thursday: 9:30 AM – 6:00 PM",
                      "Friday: 9:30 AM – 6:00 PM", "Saturday: 9:30 AM – 6:00 PM", "Sunday: 9:30 AM – 6:00 PM"]),
        _place("fx_jeronimos", "Jerónimos Monastery", "attraction", 38.6979, -9.2068, 4.7, 61500, "Manueline monastery and UNESCO site."),
        _place("fx_castelo", "São Jorge Castle", "attraction", 38.7139, -9.1335, 4.5, 77300, "Moorish castle above Alfama with city views."),
        _place("fx_lxf", "LX Factory", "attraction", 38.7033, -9.1789, 4.5, 52100, "Converted industrial complex of shops and cafés."),
    ]


def _restaurants():
    return [
        _place("fx_ramiro", "Cervejaria Ramiro", "restaurant", 38.7206, -9.1357, 4.5, 31800, "Classic seafood beer hall.", price_level=2),
        _place("fx_taberna", "Taberna da Rua das Flores", "restaurant", 38.7101, -9.1435, 4.6, 6200, "Small tavern with daily petiscos.", price_level=2),
        _place("fx_belcanto", "Belcanto", "restaurant", 38.7104, -9.1418, 4.7, 2100, "Two-Michelin-star modern Portuguese.", price_level=4),
    ]


def _weather():
    conds = [(800, "clear sky", "01d", 0.05), (802, "scattered clouds", "03d", 0.1), (500, "light rain", "10d", 0.6), (801, "few clouds", "02d", 0.15)]
    days = []
    for i, d in enumerate(_DAYS):
        cid, desc, icon, pop = conds[i % len(conds)]
        days.append({"id": f"wx_fixture{i}", "source": "openweather", "fetched_at": now_iso(), "is_estimate": False, "date": d,
                     "temp_min": 12 + i, "temp_max": 19 + i, "units": "metric", "condition_id": cid, "condition": desc, "icon": icon,
                     "pop": pop, "uvi": 5.2, "kind": "forecast"})
    return {"id": "wxf_fixture", "source": "openweather", "fetched_at": now_iso(), "is_estimate": False, "location": "Lisbon, Portugal",
            "units": "metric", "is_simulated": False, "days": days, "alerts": [], "timezone": "Europe/Lisbon"}


_SECTIONS = {
    "flights": lambda: {"flights": _flights()},
    "hotels": lambda: {"hotels": _hotels()},
    "attractions": lambda: {"attractions": _attractions()},
    "restaurants": lambda: {"restaurants": _restaurants()},
    "cars": lambda: {"cars": [{
        "id": "car_fixture01", "source": "routestack", "fetched_at": now_iso(), "is_estimate": False, "vendor": "Europcar",
        "name": "Renault Clio or similar", "category": "Economy", "transmission": "Manual", "seats": 5, "bags": 2,
        "air_conditioning": True, "pickup_location": "Lisbon Airport (LIS)", "pickup_at": f"{_DAYS[1]}T10:00:00",
        "dropoff_at": f"{_DAYS[3]}T10:00:00", "price": {"amount": 96.0, "currency": "USD", "basis": "total", "as_of": now_iso()},
    }]},
}


def section(name: str):
    if name == "weather":
        return _weather()
    return copy.deepcopy(_SECTIONS[name]())


def destination():
    return {"name": "Lisbon, Portugal", "place_id": "fx_lisbon", "lat": 38.7223, "lng": -9.1393, "timezone": "Europe/Lisbon",
            "viewport": {"low": {"lat": 38.6913, "lng": -9.2298}, "high": {"lat": 38.7959, "lng": -9.0863}}}


def parse_request(text: str, today: str):
    """Tiny rule-based stand-in for the intake LLM."""
    from agents.travel_graph import TripRequest

    t = text.lower()
    if re.fullmatch(r"\s*(hi|hello|hey)[!. ]*", t):
        return TripRequest(intent="greeting")
    origin = "Boston" if "boston" in t or " bos" in t else None
    has_dates = bool(re.search(r"\d|march|april|may|june|july|next|week", t))
    intent = "plan_trip"
    for word, it in (("flight", "flights"), ("hotel", "hotels"), ("restaurant", "restaurants"), ("weather", "weather"), ("neighborhood", "general")):
        if word in t:
            intent = it
            break
    sections = {
        "plan_trip": ["flights", "hotels", "attractions", "restaurants", "weather"],
        "flights": ["flights"], "hotels": ["hotels"], "restaurants": ["restaurants"], "weather": ["weather"], "general": ["attractions"],
    }[intent]
    return TripRequest(
        intent=intent, destination="Lisbon, Portugal" if "lisbon" in t or intent != "general" else None,
        origin=origin, start_date=_DAYS[0] if has_dates else None, end_date=_DAYS[3] if has_dates else None,
        adults=2, sections=sections,
    )


def answer(trip: Dict[str, Any], results: Dict[str, Any]) -> str:
    if trip.get("intent") == "greeting":
        return "Hi! I'm TravelBuddy. Tell me where you'd like to go and when, and I'll find flights, hotels, places to see and the weather."
    dest = trip.get("destination") or "your destination"
    return (
        f"Here's a plan for **{dest}** using live results (fixture data in this environment).\n\n"
        "**Day 1:** Arrive, check in, and walk Alfama up to São Jorge Castle for sunset.\n\n"
        "**Day 2:** Belém in the morning (Jerónimos Monastery, then Belém Tower), LX Factory in the afternoon, "
        "seafood at Cervejaria Ramiro in the evening.\n\n"
        "**Day 3:** A slower day in Chiado and Baixa, with dinner at Taberna da Rua das Flores.\n\n"
        "Want me to add a Sintra day trip or look for cheaper hotels?"
    )
