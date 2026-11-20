"""
Streaming travel pipeline behind POST /api/llm/ask.

                ┌─► destination ─┐
                ├─► flights ─────┤
    intake ─────┼─► hotels ──────┼─► compose ─► END
                ├─► attractions ─┤
                ├─► restaurants ─┤
                └─► weather ─────┘

Section nodes fan out in parallel (one LangGraph superstep), so total
latency is the slowest provider, not the sum of all of them.

intake   GPT-4o structured output: scope check + typed trip slots
         (destination, origin, dates, travelers, which sections are needed).
clarify  when required info is missing (origin, dates, ambiguous destination)
         the graph pauses with interrupt() and resumes with the user's answer.
section  each node calls one provider through the normalized tools and writes
         its own key in `sections`; nodes not needed for this question skip.
compose  streams the narrative, and builds the structured itinerary and
         follow-up suggestions in parallel.

Nodes report progress with custom callback events, so
`graph.astream_events(version="v2")` yields agent status, finished sections
and narrative tokens (on_chat_model_stream) as they happen.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.callbacks.manager import adispatch_custom_event
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from agents import fixtures
from tools.flight_search import _search_flights
from tools.google_places_api import perform_google_places_explore
from tools.google_places_common import google_api_key, normalize_place, place_details, text_search
from schemas.itinerary import Itinerary
from tools.google_restaurant_api import perform_google_restaurant_search
from tools.hotel_search import _search_hotels
from tools.weather_tool import weather_tool
from tools.car_search import search_cars

logger = logging.getLogger("travel_graph")

SECTIONS = ["flights", "hotels", "cars", "attractions", "restaurants", "weather"]
SECTION_TIMEOUT_S = 50
FIXTURE_LATENCY = {"flights": 1.6, "hotels": 1.2, "attractions": 0.6, "restaurants": 0.5, "weather": 0.4, "cars": 0.9}

AGENT_LABELS = {
    "intake": "Reading your request",
    "flights": "Flights",
    "hotels": "Hotels",
    "attractions": "Places to see",
    "restaurants": "Restaurants",
    "weather": "Weather",
    "cars": "Car rentals",
    "compose": "Writing your answer",
}


def use_fixtures() -> bool:
    return os.getenv("TRAVELBUDDY_FIXTURES", "").lower() in ("1", "true", "yes")


# ----------------------------------------------------------------- state
def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a or {})
    out.update(b or {})
    return out


from typing import Annotated  # noqa: E402  (kept next to the reducer it serves)


class TravelState(TypedDict, total=False):
    request_id: str
    user_input: str
    history: List[Dict[str, str]]
    today: str
    prefs: Dict[str, Any]
    trip: Dict[str, Any]
    sections: Annotated[Dict[str, Any], merge_dicts]
    destination: Dict[str, Any]
    answer: str
    itinerary: Dict[str, Any]
    suggestions: List[str]
    clarified: bool
    status: str


# ---------------------------------------------------------------- intake
class TripRequest(BaseModel):
    """Typed slots extracted from the user's message."""

    intent: Literal[
        "plan_trip", "flights", "hotels", "attractions", "restaurants",
        "weather", "packing", "general", "greeting",
    ] = Field(description="Main thing the user wants")
    destination: Optional[str] = Field(None, description="Destination city/region, as a searchable name, e.g. 'Lisbon, Portugal'")
    origin: Optional[str] = Field(None, description="Departure city name or IATA airport code (e.g. 'Boston' or 'BOS'), if given or clearly implied")
    start_date: Optional[str] = Field(None, description="Trip start / departure date as YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="Trip end / return date as YYYY-MM-DD")
    adults: Optional[int] = Field(None, description="Number of adult travelers")
    children: Optional[int] = Field(None, description="Number of child travelers")
    cabin_class: Optional[Literal["Economy", "PremiumEconomy", "Business", "First"]] = None
    cuisine: Optional[str] = Field(None, description="Cuisine preference for restaurants, if any")
    interests: List[str] = Field(default_factory=list, description="Interests such as museums, hiking, nightlife")
    sections: List[Literal["flights", "hotels", "cars", "attractions", "restaurants", "weather"]] = Field(
        default_factory=list,
        description="Which live searches answer this question. A full trip plan needs all that apply.",
    )
    in_scope: bool = Field(True, description="True for anything about travel, places, trips, food, culture, logistics")
    scope_reason: Optional[str] = Field(None, description="If not in scope: short, friendly reason")
    redirect_suggestions: List[str] = Field(default_factory=list, description="If not in scope: 2-3 travel questions they could ask instead")
    destination_ambiguous: bool = Field(False, description="True only if the destination could mean clearly different places (e.g. 'Portland', 'San Jose')")
    destination_options: List[str] = Field(default_factory=list, description="If ambiguous: the 2-4 likely places, as searchable names")


INTAKE_PROMPT = """You turn a traveler's message into structured search parameters for TravelBuddy.
Today is {today}. Resolve relative dates ("next Friday", "March 12-15") to YYYY-MM-DD in the future;
if no year is given use the next future occurrence. "for 3 days" from a start date sets end_date.
Use the conversation for context: a follow-up like "show cheaper hotels" keeps the earlier destination and dates.
Pick `sections` to cover the request:
- plan_trip: flights (only if an origin is known), hotels, attractions, restaurants, weather
- flights / hotels / attractions / restaurants / weather: that section (add weather when packing)
- cars: only when they mention renting a car, driving, a road trip, or ask for cars
- general questions about a place (neighborhoods, best time to visit, culture): attractions only if useful, else none
- greeting: none
Never invent an origin or dates the user did not give or clearly imply.
SCOPE: TravelBuddy answers anything a traveler might ask — destinations, neighborhoods ("best neighborhoods in
Lisbon" is in scope), where to stay or eat, culture, safety, visas, budgets, packing, weather, transport, events.
Mark in_scope=false only when the request has nothing to do with travel or places (coding help, math homework,
celebrity gossip, writing essays). Then give a kind scope_reason and 2-3 redirect_suggestions."""


def _history_text(history: List[Dict[str, str]], limit: int = 6) -> str:
    lines = []
    for m in (history or [])[-limit:]:
        role = "User" if m.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {str(m.get('content', ''))[:600]}")
    return "\n".join(lines)


_intake_llm = None
_compose_llm = None
_itinerary_llm = None


def itinerary_llm():
    global _itinerary_llm
    if _itinerary_llm is None:
        # response_format: {type: "json_schema", strict: true}
        _itinerary_llm = ChatOpenAI(model="gpt-4o", temperature=0.2).with_structured_output(Itinerary, method="json_schema", strict=True)
    return _itinerary_llm


def intake_llm():
    global _intake_llm
    if _intake_llm is None:
        _intake_llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(TripRequest, method="json_schema")
    return _intake_llm


def compose_llm():
    global _compose_llm
    if _compose_llm is None:
        _compose_llm = ChatOpenAI(model="gpt-4o", temperature=0.3, streaming=True)
    return _compose_llm


async def emit(payload: Dict[str, Any]) -> None:
    """Send a progress event (agent status / section / trip) to astream_events consumers."""
    try:
        await adispatch_custom_event("travelbuddy", payload)
    except Exception:  # no callback context (e.g. called outside a run) — nothing to send
        pass


async def intake_node(state: TravelState) -> Dict[str, Any]:
    await emit({"event": "agent", "agent": "intake", "state": "running"})
    if use_fixtures():
        req = fixtures.parse_request(state["user_input"], state["today"])
    else:
        messages = [SystemMessage(content=INTAKE_PROMPT.format(today=state["today"]))]
        hist = _history_text(state.get("history", []))
        if hist:
            messages.append(SystemMessage(content=f"Conversation so far:\n{hist}"))
        messages.append(HumanMessage(content=state["user_input"]))
        req: TripRequest = await intake_llm().ainvoke(messages)
    trip = req.model_dump()
    prefs = state.get("prefs") or {}
    if not trip.get("adults") and prefs.get("default_adults"):
        trip["adults"] = prefs["default_adults"]
    if not trip.get("origin") and prefs.get("home_airport") and (
        "flights" in trip.get("sections", []) or trip.get("intent") == "plan_trip"
    ):
        trip["origin"] = prefs["home_airport"]
        trip["origin_from_preferences"] = True
        if trip.get("intent") == "plan_trip" and "flights" not in trip["sections"]:
            trip["sections"] = ["flights", *trip["sections"]]
    await emit({"event": "agent", "agent": "intake", "state": "done"})
    if not trip.get("in_scope", True):
        return {"trip": trip, "status": "out_of_scope"}
    if missing_fields(trip, state) and not state.get("clarified"):
        return {"trip": trip}
    return {"trip": await announce_plan(trip)}


async def announce_plan(trip: Dict[str, Any]) -> Dict[str, Any]:
    if not trip.get("origin") and "flights" in trip["sections"]:
        trip["sections"] = [s for s in trip["sections"] if s != "flights"]
    planned = [s for s in SECTIONS if s in trip["sections"] and trip.get("destination")]
    trip["sections"] = planned
    await emit({"event": "plan", "sections": planned, "trip": trip})
    for s in planned:
        await emit({"event": "agent", "agent": s, "state": "queued"})
    return trip


# --------------------------------------------------------------- clarify
NEEDS_DESTINATION = {"plan_trip", "flights", "hotels", "attractions", "restaurants", "weather", "packing"}


def missing_fields(trip: Dict[str, Any], state: TravelState) -> List[str]:
    intent = trip.get("intent")
    missing: List[str] = []
    if intent in NEEDS_DESTINATION and (not trip.get("destination") or trip.get("destination_ambiguous")):
        missing.append("destination")
    if intent in ("plan_trip", "hotels", "flights") and not trip.get("start_date"):
        missing.append("dates")
    elif intent in ("plan_trip", "hotels") and not trip.get("end_date"):
        missing.append("dates")
    if intent == "flights" and not trip.get("origin"):
        missing.append("origin")
    if intent == "plan_trip" and not trip.get("origin") and not (state.get("prefs") or {}).get("home_airport"):
        missing.append("origin")
    return missing


def _date_options(today: str) -> List[Dict[str, str]]:
    t = datetime.strptime(today, "%Y-%m-%d").date()
    fri = t + timedelta(days=(4 - t.weekday()) % 7 or 7)
    in2 = fri + timedelta(days=7)
    month = (t.replace(day=1) + timedelta(days=32)).replace(day=1)
    month_fri = month + timedelta(days=(4 - month.weekday()) % 7)
    fmt = lambda d: d.strftime("%b %-d")
    return [
        {"label": f"Next weekend ({fmt(fri)}–{fmt(fri + timedelta(days=2))})", "start_date": fri.isoformat(), "end_date": (fri + timedelta(days=2)).isoformat()},
        {"label": f"In two weeks, 4 days ({fmt(in2)}–{fmt(in2 + timedelta(days=3))})", "start_date": in2.isoformat(), "end_date": (in2 + timedelta(days=3)).isoformat()},
        {"label": f"A week in {month.strftime('%B')} ({fmt(month_fri)}–{fmt(month_fri + timedelta(days=7))})", "start_date": month_fri.isoformat(), "end_date": (month_fri + timedelta(days=7)).isoformat()},
    ]


def clarification_payload(trip: Dict[str, Any], state: TravelState) -> Dict[str, Any]:
    missing = missing_fields(trip, state)
    fields: List[Dict[str, Any]] = []
    prefs = state.get("prefs") or {}
    if "destination" in missing:
        fields.append({
            "name": "destination", "type": "choice" if trip.get("destination_options") else "text",
            "label": "Which place do you mean?" if trip.get("destination_options") else "Where would you like to go?",
            "options": [{"label": o, "value": o} for o in trip.get("destination_options") or []],
            "optional": False,
        })
    if "dates" in missing:
        fields.append({
            "name": "dates", "type": "date_range", "label": "When are you travelling?",
            "options": _date_options(state["today"]), "optional": trip.get("intent") not in ("hotels", "flights"),
        })
    if "origin" in missing:
        opts = [{"label": prefs["home_airport"], "value": prefs["home_airport"]}] if prefs.get("home_airport") else []
        fields.append({
            "name": "origin", "type": "text", "label": "Where are you flying from?",
            "placeholder": "City or airport, e.g. Boston or BOS", "options": opts,
            "optional": trip.get("intent") != "flights", "skip_label": "Skip flights",
        })
    labels = {"destination": "where", "dates": "when", "origin": "where from"}
    question = "Quick check before I search: " + ", ".join(labels[m] for m in missing) + "?"
    return {"question": question, "missing": missing, "fields": fields, "trip": {k: trip.get(k) for k in ("intent", "destination", "origin", "start_date", "end_date", "adults")}}


async def clarify_node(state: TravelState) -> Dict[str, Any]:
    """Pause the graph for missing info; resume merges the answers into the trip."""
    trip = dict(state.get("trip") or {})
    answers = interrupt(clarification_payload(trip, state)) or {}
    skipped = set(answers.get("skip") or [])
    if answers.get("destination"):
        trip["destination"] = str(answers["destination"])[:120]
        trip["destination_ambiguous"] = False
    if answers.get("start_date"):
        trip["start_date"] = str(answers["start_date"])[:10]
    if answers.get("end_date"):
        trip["end_date"] = str(answers["end_date"])[:10]
    if answers.get("origin") and "origin" not in skipped:
        trip["origin"] = str(answers["origin"])[:80]
        if trip.get("intent") in ("plan_trip", "flights") and "flights" not in trip["sections"]:
            trip["sections"] = ["flights", *trip["sections"]]
    if answers.get("adults"):
        try:
            trip["adults"] = max(1, min(9, int(answers["adults"])))
        except (TypeError, ValueError):
            pass
    if "origin" in skipped:
        trip["origin"] = None
    return {"trip": await announce_plan(trip), "clarified": True}


SCOPE_PROMPT = """Decide if a message is in scope for TravelBuddy, a travel planning assistant.
In scope: anything about travel, destinations, neighborhoods, places, food and restaurants, culture, events,
safety, visas, money, packing, weather, transport, accommodation, itineraries, and greetings/small talk.
Out of scope: requests unrelated to travel or places (coding, homework, general trivia, writing unrelated text)."""


class ScopeDecision(BaseModel):
    in_scope: bool
    reason: Optional[str] = Field(description="If out of scope: short, friendly reason; else null")
    suggestions: List[str] = Field(description="If out of scope: 2-3 travel questions to ask instead; else empty")


_scope_llm = None


async def classify_scope(text: str) -> ScopeDecision:
    """Structured scope check (also used by the legacy endpoint before refusing)."""
    global _scope_llm
    if use_fixtures():
        return ScopeDecision(in_scope=not any(w in text.lower() for w in ("python", "homework", "joke")), reason="I plan trips, not code.", suggestions=["Plan 3 days in Lisbon"])
    if _scope_llm is None:
        _scope_llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(ScopeDecision, method="json_schema", strict=True)
    return await _scope_llm.ainvoke([SystemMessage(content=SCOPE_PROMPT), HumanMessage(content=text)])


async def scope_reply_node(state: TravelState) -> Dict[str, Any]:
    trip = state.get("trip") or {}
    reason = trip.get("scope_reason") or "That's outside what I can help with — I'm a travel planner."
    suggestions = trip.get("redirect_suggestions") or [
        "Plan a long weekend in Lisbon",
        "Best neighborhoods to stay in Tokyo",
        "What's the weather like in Rome next week?",
    ]
    return {"answer": reason, "suggestions": suggestions[:3], "status": "out_of_scope"}


# ------------------------------------------------------------ destination
_GEOCODE_CACHE: Dict[str, Dict[str, Any]] = {}
DEST_FIELDS = ["places.id", "places.displayName", "places.formattedAddress", "places.location", "places.viewport", "places.utcOffsetMinutes", "places.types"]


def geocode_destination(name: str) -> Optional[Dict[str, Any]]:
    """Destination geocode + suggested map bounds (Places Text Search viewport)."""
    key = name.lower().strip()
    if key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[key]
    api_key = google_api_key()
    if not api_key:
        return None
    try:
        results = text_search(name, api_key, fields=DEST_FIELDS, limit=1, timeout=8)
    except Exception as e:
        logger.warning(f"Destination geocode failed for {name}: {e}")
        return None
    if not results:
        return None
    place = normalize_place(results[0], "destination")
    dest = {
        "name": name,
        "formatted_name": place.name,
        "address": place.address,
        "place_id": place.place_id,
        "lat": place.location.lat if place.location else None,
        "lng": place.location.lng if place.location else None,
        "viewport": {k: v.model_dump() for k, v in place.viewport.items()} if place.viewport else None,
        "utc_offset_minutes": place.utc_offset_minutes,
    }
    if len(_GEOCODE_CACHE) < 1000:
        _GEOCODE_CACHE[key] = dest
    return dest


async def destination_node(state: TravelState) -> Dict[str, Any]:
    trip = state.get("trip") or {}
    name = trip.get("destination")
    if not name:
        return {}
    dest = fixtures.destination() if use_fixtures() else await asyncio.to_thread(geocode_destination, name)
    if not dest:
        return {}
    await emit({"event": "trip", "destination": dest, "start_date": trip.get("start_date"), "end_date": trip.get("end_date")})
    return {"destination": dest}


# --------------------------------------------------------------- sections
def _section(status: str, items: Optional[List[Dict[str, Any]]] = None, message: Optional[str] = None, **extra) -> Dict[str, Any]:
    items = items or []
    return {"status": status, "count": len(items), "items": items, "message": message, **extra}


async def _run_section(name: str, state: TravelState, fn) -> Dict[str, Any]:
    trip = state.get("trip") or {}
    if name not in trip.get("sections", []):
        return {}
    await emit({"event": "agent", "agent": name, "state": "running"})
    if use_fixtures():
        await asyncio.sleep(FIXTURE_LATENCY.get(name, 0.5))  # make progressive arrival visible locally
    try:
        result = await asyncio.wait_for(fn(trip, state.get("prefs") or {}), timeout=SECTION_TIMEOUT_S)
    except asyncio.TimeoutError:
        result = _section("failed", message=f"{AGENT_LABELS[name]} took too long to answer.", code=f"{name.upper()}_TIMEOUT", retryable=True)
    except Exception as e:  # provider/tool crash: keep the other sections going
        logger.exception(f"{name} section failed")
        result = _section("failed", message=f"{AGENT_LABELS[name]} search failed: {e}", code=f"{name.upper()}_FAILED", retryable=True)
    state_name = {"ok": "done", "estimate": "done", "empty": "empty", "failed": "failed", "skipped": "skipped"}[result["status"]]
    await emit({"event": "agent", "agent": name, "state": state_name, "count": result.get("count"), "message": result.get("message")})
    await emit({"event": "section", "type": name, "section": result})
    return {"sections": {name: result}}


def _tool_result(items_key: str, data: Dict[str, Any], empty_message: str) -> Dict[str, Any]:
    if data.get("error"):
        return _section("failed", message=str(data["error"])[:300], code=f"{items_key.upper()}_PROVIDER_ERROR", retryable=True)
    items = data.get(items_key) or []
    if not items:
        return _section("empty", message=data.get("message") or empty_message)
    return _section("ok", items)


def _shift(day: Optional[str], delta: int) -> Optional[str]:
    if not day:
        return None
    from datetime import datetime, timedelta

    try:
        return (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=delta)).date().isoformat()
    except ValueError:
        return None


DETAILS_TOP_N = 3
DETAIL_MERGE_FIELDS = ("reviews", "opening_hours", "editorial_summary", "website", "phone", "google_maps_uri", "price_level", "photos")


async def enrich_places(items: List[Dict[str, Any]], key: str, kind: str) -> List[Dict[str, Any]]:
    """Place Details (GET places/{id}) for the top results, merged into the Text Search entities."""
    top = [p for p in items[:DETAILS_TOP_N] if p.get("place_id")]
    details = await asyncio.gather(*[asyncio.to_thread(place_details, p["place_id"], key, kind) for p in top], return_exceptions=True)
    by_id = {p.place_id: p for p in details if p and not isinstance(p, Exception)}
    for item in items:
        d = by_id.get(item.get("place_id"))
        if not d:
            continue
        full = d.model_dump(mode="json", exclude_none=True)
        for f in DETAIL_MERGE_FIELDS:
            if full.get(f) and (not item.get(f) or (f in ("reviews", "photos") and len(full[f]) > len(item.get(f) or []))):
                item[f] = full[f]
        item["details_fetched_at"] = full.get("fetched_at")
    return items


HOTEL_GEO_TOP_N = 8


def _hotel_location(name: str, address: Optional[str], city: str, key: str) -> Optional[Dict[str, float]]:
    try:
        res = text_search(", ".join(x for x in (name, address or city) if x), key, fields=["places.location"], limit=1, timeout=8)
    except Exception:
        return None
    loc = (res[0].get("location") if res else None) or {}
    if loc.get("latitude") is None:
        return None
    return {"lat": loc["latitude"], "lng": loc["longitude"]}


async def locate_hotels(hotels: List[Dict[str, Any]], city: str) -> List[Dict[str, Any]]:
    """RouteStack search results carry no coordinates; geocode the top hotels for map pins."""
    key = google_api_key()
    if not key:
        return hotels
    need = [h for h in hotels[:HOTEL_GEO_TOP_N] if not h.get("location")]
    found = await asyncio.gather(*[asyncio.to_thread(_hotel_location, h["name"], h.get("address"), city, key) for h in need], return_exceptions=True)
    for h, loc in zip(need, found):
        if isinstance(loc, dict):
            h["location"] = loc
            h["location_source"] = "google_places"
    return hotels


async def _flights(trip, prefs):
    if not trip.get("start_date"):
        return _section("skipped", message="Add travel dates to search flights.")
    if use_fixtures():
        return _tool_result("flights", fixtures.section("flights"), "No flights found.")
    params = {
        "origin": trip.get("origin") or "",
        "destination": trip["destination"],
        "departure_date": trip["start_date"],
        "return_date": trip.get("end_date") or "",
        "adults": str(trip.get("adults") or 1),
        "cabin_class": trip.get("cabin_class") or "Economy",
    }
    data = await asyncio.to_thread(_search_flights, params)
    out = _tool_result("flights", data, f"No flights {params['origin']}→{params['destination']} on {params['departure_date']}.")
    if out["status"] == "empty":
        out["alternatives"] = [d for d in (_shift(trip["start_date"], -1), _shift(trip["start_date"], 1)) if d]
    return out


async def _hotels(trip, prefs):
    if not trip.get("start_date") or not trip.get("end_date"):
        return _section("skipped", message="Add check-in and check-out dates to see hotel prices.")
    if use_fixtures():
        return _tool_result("hotels", fixtures.section("hotels"), "No hotels found.")
    params = {
        "city": trip["destination"],
        "checkInDate": trip["start_date"],
        "checkOutDate": trip["end_date"],
        "adults": str(trip.get("adults") or 2),
    }
    if prefs.get("currency"):
        params["currency"] = prefs["currency"]
    data = await asyncio.to_thread(_search_hotels, params)
    if data.get("hotels"):
        data["hotels"] = await locate_hotels(data["hotels"], trip["destination"])
    return _tool_result("hotels", data, f"No hotels in {trip['destination']} for those dates.")


async def _attractions(trip, prefs):
    if use_fixtures():
        return _tool_result("attractions", fixtures.section("attractions"), "No places found.")
    key = google_api_key()
    if not key:
        return _section("failed", message="Places search isn't configured.", code="PLACES_NOT_CONFIGURED")
    interests = ", ".join(trip.get("interests") or [])
    query = f"top {interests + ' ' if interests else ''}attractions in {trip['destination']}"
    data = await asyncio.to_thread(perform_google_places_explore, trip["destination"], key, query)
    if data.get("attractions"):
        data["attractions"] = await enrich_places(data["attractions"], key, "attraction")
    return _tool_result("attractions", data, f"No places found in {trip['destination']}.")


async def _restaurants(trip, prefs):
    if use_fixtures():
        return _tool_result("restaurants", fixtures.section("restaurants"), "No restaurants found.")
    key = google_api_key()
    if not key:
        return _section("failed", message="Places search isn't configured.", code="PLACES_NOT_CONFIGURED")
    data = await asyncio.to_thread(perform_google_restaurant_search, trip["destination"], key, trip.get("cuisine"))
    if data.get("restaurants"):
        data["restaurants"] = await enrich_places(data["restaurants"], key, "restaurant")
    return _tool_result("restaurants", data, f"No restaurants found in {trip['destination']}.")


async def _weather(trip, prefs):
    if use_fixtures():
        forecast = fixtures.section("weather")
    else:
        fc = await asyncio.to_thread(
            weather_tool.get_forecast, trip["destination"], trip.get("start_date"), trip.get("end_date"), prefs.get("units") or "metric"
        )
        forecast = fc.model_dump(mode="json", exclude_none=True)
    if forecast.get("is_simulated"):
        return _section("estimate", [], forecast.get("report"), reason=forecast.get("reason", "provider_unavailable"), forecast=forecast)
    days = forecast.get("days") or []
    out = _section("ok" if days else "empty", days, None if days else "No forecast for those dates yet.")
    out["forecast"] = forecast
    return out


async def _cars(trip, prefs):
    if not trip.get("start_date") or not trip.get("end_date"):
        return _section("skipped", message="Add pick-up and drop-off dates to see rental cars.")
    if use_fixtures():
        return _tool_result("cars", fixtures.section("cars"), "No rental cars found.")
    data = await asyncio.to_thread(search_cars, trip["destination"], trip["start_date"], trip["end_date"])
    return _tool_result("cars", data, f"No rental cars in {trip['destination']} for those dates.")


async def cars_node(state):
    return await _run_section("cars", state, _cars)


async def flights_node(state):
    return await _run_section("flights", state, _flights)


async def hotels_node(state):
    return await _run_section("hotels", state, _hotels)


async def attractions_node(state):
    return await _run_section("attractions", state, _attractions)


async def restaurants_node(state):
    return await _run_section("restaurants", state, _restaurants)


async def weather_node(state):
    return await _run_section("weather", state, _weather)


# ---------------------------------------------------------------- compose
COMPOSE_PROMPT = """You are TravelBuddy, a warm, precise travel planner. Today is {today}.
Write the answer to the traveler in Markdown: short intro, then the substance, then one line inviting a follow-up.
DATA INTEGRITY — this is strict:
- Every price, rating, time, temperature or count you mention must appear in the RESULTS JSON below. Never estimate,
  simulate or invent numbers. If a section failed or is empty, say so plainly and suggest how to retry.
- Live result cards (flights, hotels, places, restaurants, weather) are shown under your answer, so summarize and
  recommend (best value, best rated, a sensible order to see things) instead of listing every field.
- For trip plans, give a day-by-day outline using the places in RESULTS (Morning / Afternoon / Evening).
- For general questions (neighborhoods, culture, best time to visit) answer from your knowledge, without numbers you can't support.
- If weather is marked as an estimate, do not describe conditions; tell them live weather wasn't available.
Keep it under 350 words."""


def compact_results(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Small, model-friendly view of the structured results."""
    out: Dict[str, Any] = {}
    for name, sec in (sections or {}).items():
        entry: Dict[str, Any] = {"status": sec.get("status"), "message": sec.get("message")}
        items = sec.get("items") or []
        if name == "flights":
            entry["items"] = [
                {"id": f["id"], "carrier": f.get("carrier_name") or f.get("carrier"), "from": f.get("origin"), "to": f.get("destination"),
                 "depart": f.get("departure_at"), "arrive": f.get("arrival_at"), "stops": f.get("stops"), "price": f.get("price")}
                for f in items[:5]
            ]
        elif name == "hotels":
            entry["items"] = [
                {"id": h["id"], "name": h.get("name"), "stars": h.get("star_rating"), "guest_rating": h.get("guest_rating"),
                 "price": h.get("price"), "nightly": h.get("nightly_price")}
                for h in items[:6]
            ]
        elif name == "cars":
            entry["items"] = [
                {"id": c["id"], "name": c.get("name"), "vendor": c.get("vendor"), "category": c.get("category"), "price": c.get("price")}
                for c in items[:5]
            ]
        elif name in ("attractions", "restaurants"):
            entry["items"] = [
                {"id": p["id"], "name": p.get("name"), "rating": p.get("rating"), "reviews": p.get("total_ratings"),
                 "price_level": p.get("price_level"), "summary": p.get("editorial_summary"),
                 "hours": ((p.get("opening_hours") or {}).get("weekday_descriptions") or None),
                 "location": p.get("location")}
                for p in items[:8]
            ]
        elif name == "weather":
            fc = sec.get("forecast") or {}
            entry["is_estimate"] = bool(fc.get("is_simulated"))
            entry["units"] = fc.get("units")
            entry["days"] = [
                {"date": d.get("date"), "min": d.get("temp_min"), "max": d.get("temp_max"), "condition": d.get("condition"), "pop": d.get("pop")}
                for d in items[:14]
            ]
        else:
            entry["items"] = items[:5]
        out[name] = entry
    return out


ITINERARY_PROMPT = """Build a structured day-by-day itinerary for this trip as JSON.
Rules:
- One entry in `days` per date from start_date to end_date inclusive.
- Each day has 2-5 items across morning / afternoon / evening (night only if it fits).
- Use places and restaurants from RESULTS and set `ref` to their exact `id`. Put the arrival flight
  (ref = flight id) on the first day and the hotel check-in (ref = hotel id) on arrival day when they exist.
- Group nearby places on the same day. Respect opening hours mentioned in RESULTS.
- Use null for ref when an item isn't one of the RESULTS (e.g. "Stroll the riverfront").
- Never include prices or numbers that aren't in RESULTS.
- destination.timezone is the IANA zone for the destination."""


def _known_ids(sections: Dict[str, Any]) -> Dict[str, str]:
    kinds = {"flights": "flight", "hotels": "hotel", "attractions": "place", "restaurants": "restaurant", "cars": "car"}
    out = {}
    for name, sec in (sections or {}).items():
        for item in sec.get("items") or []:
            if isinstance(item, dict) and item.get("id") and name in kinds:
                out[item["id"]] = kinds[name]
    return out


def clean_itinerary(it: Dict[str, Any], state: TravelState) -> Dict[str, Any]:
    """Ground the model's itinerary in real data: verified geocode, valid refs only."""
    known = _known_ids(state.get("sections") or {})
    dest = state.get("destination") or {}
    d = it.setdefault("trip", {}).setdefault("destination", {})
    for k in ("place_id", "lat", "lng"):
        if dest.get(k) is not None:
            d[k] = dest[k]
    if dest.get("viewport"):
        d["viewport"] = dest["viewport"]
    for day in it.get("days") or []:
        for item in day.get("items") or []:
            ref = item.get("ref")
            if ref and ref not in known:
                item["ref"] = None
            elif ref:
                item["kind"] = known[ref]
    return it


async def build_itinerary(state: TravelState, results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    trip = state.get("trip") or {}
    if trip.get("intent") != "plan_trip" or not trip.get("start_date") or not trip.get("destination"):
        return None
    if use_fixtures():
        return clean_itinerary(fixtures.itinerary(state), state)
    messages = [
        SystemMessage(content=ITINERARY_PROMPT),
        SystemMessage(content="TRIP: " + json.dumps({**trip, "destination_geocode": state.get("destination")}, default=str)),
        SystemMessage(content="RESULTS: " + json.dumps(results, default=str)),
        HumanMessage(content=state["user_input"]),
    ]
    try:
        it: Itinerary = await itinerary_llm().ainvoke(messages)
    except Exception as e:
        logger.warning(f"Structured itinerary failed: {e}")
        return None
    return clean_itinerary(it.model_dump(), state)


class FollowUps(BaseModel):
    suggestions: List[str] = Field(description="3 short follow-up requests the traveler might send next, each under 40 characters")


SUGGEST_PROMPT = """Suggest 3 next steps the traveler could tap to refine or extend this trip, phrased as their own request,
under 40 characters each, specific to the destination and results (e.g. "Add a Sintra day trip", "Show cheaper hotels",
"What's the weather like?"). If a section failed or was skipped, one suggestion should retry or fill it
(e.g. "Search flights from Boston"). Never suggest re-running a section whose status is "ok" — it already has
results. No numbers you can't see in RESULTS."""

_suggest_llm = None


async def build_suggestions(state: TravelState, results: Dict[str, Any]) -> List[str]:
    global _suggest_llm
    trip = state.get("trip") or {}
    if use_fixtures():
        return fixtures.suggestions(trip)
    if _suggest_llm is None:
        _suggest_llm = ChatOpenAI(model="gpt-4o", temperature=0.5).with_structured_output(FollowUps, method="json_schema", strict=True)
    try:
        out: FollowUps = await _suggest_llm.ainvoke([
            SystemMessage(content=SUGGEST_PROMPT),
            SystemMessage(content="TRIP: " + json.dumps({k: trip.get(k) for k in ("intent", "destination", "origin", "start_date", "end_date", "interests")}, default=str)),
            SystemMessage(content="RESULTS: " + json.dumps({k: {"status": v.get("status"), "message": v.get("message")} for k, v in results.items()}, default=str)),
            HumanMessage(content=state["user_input"]),
        ])
    except Exception as e:
        logger.info(f"suggestions skipped: {e}")
        return []
    return [x.strip()[:60] for x in out.suggestions if x.strip()][:4]


async def compose_node(state: TravelState) -> Dict[str, Any]:
    await emit({"event": "agent", "agent": "compose", "state": "running"})
    trip = state.get("trip") or {}
    results = compact_results(state.get("sections") or {})
    itinerary_task = asyncio.create_task(build_itinerary(state, results))
    suggestions_task = asyncio.create_task(build_suggestions(state, results))
    if use_fixtures():
        answer = fixtures.answer(trip, results)
        # Stream the canned answer word by word like the model would.
        for word in answer.split(" "):
            await emit({"event": "delta", "text": word + " "})
            await asyncio.sleep(0.01)
        itinerary, suggestions = await asyncio.gather(itinerary_task, suggestions_task)
        await emit({"event": "agent", "agent": "compose", "state": "done"})
        return {"answer": answer, "itinerary": itinerary or {}, "suggestions": suggestions, "status": "success"}

    messages = [
        SystemMessage(content=COMPOSE_PROMPT.format(today=state["today"])),
        SystemMessage(content="TRIP: " + json.dumps(trip, default=str)),
        SystemMessage(content="RESULTS: " + json.dumps(results, default=str)),
    ]
    hist = _history_text(state.get("history", []))
    if hist:
        messages.append(SystemMessage(content=f"Conversation so far:\n{hist}"))
    messages.append(HumanMessage(content=state["user_input"]))
    chunks: List[str] = []
    async for chunk in compose_llm().astream(messages, config={"tags": ["narrative"]}):
        text = chunk.content if isinstance(chunk.content, str) else ""
        if text:
            chunks.append(text)
    answer = "".join(chunks).strip()
    itinerary, suggestions = await asyncio.gather(itinerary_task, suggestions_task)
    await emit({"event": "agent", "agent": "compose", "state": "done"})
    return {"answer": answer, "itinerary": itinerary or {}, "suggestions": suggestions, "status": "success"}


# ------------------------------------------------------------------ graph
PARALLEL_NODES = ["destination", "flights", "hotels", "cars", "attractions", "restaurants", "weather"]


def route_after_intake(state: TravelState):
    if state.get("status") == "out_of_scope":
        return "scope_reply"
    if missing_fields(state.get("trip") or {}, state) and not state.get("clarified"):
        return "clarify"
    return PARALLEL_NODES


def build_travel_graph():
    g = StateGraph(TravelState)
    g.add_node("intake", intake_node)
    g.add_node("destination", destination_node)
    g.add_node("flights", flights_node)
    g.add_node("hotels", hotels_node)
    g.add_node("attractions", attractions_node)
    g.add_node("restaurants", restaurants_node)
    g.add_node("weather", weather_node)
    g.add_node("cars", cars_node)
    g.add_node("compose", compose_node)
    g.add_node("clarify", clarify_node)
    g.add_node("scope_reply", scope_reply_node)
    g.set_entry_point("intake")
    # Fan out: every section runs in the same superstep; compose waits for all of them.
    g.add_conditional_edges("intake", route_after_intake, ["scope_reply", "clarify", *PARALLEL_NODES])
    g.add_conditional_edges("clarify", lambda s: PARALLEL_NODES, PARALLEL_NODES)
    for node in PARALLEL_NODES:
        g.add_edge(node, "compose")
    g.add_edge("compose", END)
    g.add_edge("scope_reply", END)
    # Checkpointer: needed to pause for clarifying questions and resume later.
    return g.compile(checkpointer=InMemorySaver())


travel_graph = build_travel_graph()


def initial_state(request_id: str, query: str, history: List[Dict[str, str]], prefs: Optional[Dict[str, Any]] = None) -> TravelState:
    return {
        "request_id": request_id,
        "user_input": query,
        "history": history or [],
        "today": date.today().isoformat(),
        "prefs": prefs or {},
        "trip": {},
        "sections": {},
        "destination": {},
        "answer": "",
        "itinerary": {},
        "suggestions": [],
        "clarified": False,
        "status": "running",
    }


def final_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """The `final` event / JSON body: narrative + every structured section."""
    sections = state.get("sections") or {}
    payload: Dict[str, Any] = {
        "status": state.get("status") or "success",
        "answer": state.get("answer") or "",
        "model": "agent",
        "trip": state.get("trip") or {},
        "sections": {
            k: {kk: v.get(kk) for kk in ("status", "count", "message", "reason", "alternatives", "code") if v.get(kk) is not None}
            for k, v in sections.items()
        },
    }
    for name in ("flights", "hotels", "cars", "attractions", "restaurants"):
        if name in sections:
            payload[name] = sections[name].get("items") or []
    if "weather" in sections:
        payload["weather"] = sections["weather"].get("forecast")
    if state.get("destination"):
        payload["trip"] = {**payload["trip"], "destination": state["destination"]}
    if state.get("itinerary"):
        payload["itinerary"] = state["itinerary"]
    payload["suggestions"] = state.get("suggestions") or []
    if state.get("status") == "out_of_scope":
        payload["reason"] = state.get("answer")
    # Slots only the server needs.
    payload["trip"] = {k: v for k, v in payload["trip"].items() if k not in ("scope_reason", "redirect_suggestions", "destination_options", "destination_ambiguous", "in_scope")}
    return payload
