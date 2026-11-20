"""
Streaming travel pipeline behind POST /api/llm/ask.

    intake ──► flights ─► hotels ─► attractions ─► restaurants ─► weather ─► compose ─► END

intake   GPT-4o structured output turns the question into typed trip slots
         (destination, origin, dates, travelers, which sections are needed).
section  each node calls one provider through the normalized tools and writes
         its own key in `sections`; nodes not needed for this question skip.
compose  writes the narrative answer from the structured results only.

Each node emits progress through LangGraph's stream writer, so
`graph.astream(stream_mode=["updates", "custom", "messages"])` yields agent
status, finished sections and narrative tokens as they happen.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from agents import fixtures
from tools.flight_search import _search_flights
from tools.google_places_api import perform_google_places_explore
from tools.google_places_common import google_api_key
from tools.google_restaurant_api import perform_google_restaurant_search
from tools.hotel_search import _search_hotels
from tools.weather_tool import weather_tool

logger = logging.getLogger("travel_graph")

SECTIONS = ["flights", "hotels", "attractions", "restaurants", "weather"]
SECTION_TIMEOUT_S = 50
FIXTURE_LATENCY = {"flights": 1.6, "hotels": 1.2, "attractions": 0.6, "restaurants": 0.5, "weather": 0.4, "cars": 0.9}

AGENT_LABELS = {
    "intake": "Reading your request",
    "flights": "Flights",
    "hotels": "Hotels",
    "attractions": "Places to see",
    "restaurants": "Restaurants",
    "weather": "Weather",
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
    answer: str
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
    sections: List[Literal["flights", "hotels", "attractions", "restaurants", "weather"]] = Field(
        default_factory=list,
        description="Which live searches answer this question. A full trip plan needs all that apply.",
    )


INTAKE_PROMPT = """You turn a traveler's message into structured search parameters for TravelBuddy.
Today is {today}. Resolve relative dates ("next Friday", "March 12-15") to YYYY-MM-DD in the future;
if no year is given use the next future occurrence. "for 3 days" from a start date sets end_date.
Use the conversation for context: a follow-up like "show cheaper hotels" keeps the earlier destination and dates.
Pick `sections` to cover the request:
- plan_trip: flights (only if an origin is known), hotels, attractions, restaurants, weather
- flights / hotels / attractions / restaurants / weather: that section (add weather when packing)
- general questions about a place (neighborhoods, best time to visit, culture): attractions only if useful, else none
- greeting: none
Never invent an origin or dates the user did not give or clearly imply."""


def _history_text(history: List[Dict[str, str]], limit: int = 6) -> str:
    lines = []
    for m in (history or [])[-limit:]:
        role = "User" if m.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {str(m.get('content', ''))[:600]}")
    return "\n".join(lines)


_intake_llm = None
_compose_llm = None


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


def emit(payload: Dict[str, Any]) -> None:
    """Send a custom stream event (agent status / section / trip)."""
    try:
        get_stream_writer()(payload)
    except Exception:  # not streaming (e.g. ainvoke) — nothing to send
        pass


async def intake_node(state: TravelState) -> Dict[str, Any]:
    emit({"event": "agent", "agent": "intake", "state": "running"})
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
    if not trip.get("origin") and prefs.get("home_airport") and "flights" in trip.get("sections", []):
        trip["origin"] = prefs["home_airport"]
    if not trip.get("origin") and "flights" in trip["sections"]:
        trip["sections"] = [s for s in trip["sections"] if s != "flights"]
    planned = [s for s in SECTIONS if s in trip["sections"] and trip.get("destination")]
    trip["sections"] = planned
    emit({"event": "agent", "agent": "intake", "state": "done"})
    emit({"event": "plan", "sections": planned, "trip": trip})
    for s in planned:
        emit({"event": "agent", "agent": s, "state": "queued"})
    return {"trip": trip}


# --------------------------------------------------------------- sections
def _section(status: str, items: Optional[List[Dict[str, Any]]] = None, message: Optional[str] = None, **extra) -> Dict[str, Any]:
    items = items or []
    return {"status": status, "count": len(items), "items": items, "message": message, **extra}


async def _run_section(name: str, state: TravelState, fn) -> Dict[str, Any]:
    trip = state.get("trip") or {}
    if name not in trip.get("sections", []):
        return {}
    emit({"event": "agent", "agent": name, "state": "running"})
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
    emit({"event": "agent", "agent": name, "state": state_name, "count": result.get("count"), "message": result.get("message")})
    emit({"event": "section", "type": name, "section": result})
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
    data = await asyncio.to_thread(_search_hotels, params)
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
    return _tool_result("attractions", data, f"No places found in {trip['destination']}.")


async def _restaurants(trip, prefs):
    if use_fixtures():
        return _tool_result("restaurants", fixtures.section("restaurants"), "No restaurants found.")
    key = google_api_key()
    if not key:
        return _section("failed", message="Places search isn't configured.", code="PLACES_NOT_CONFIGURED")
    data = await asyncio.to_thread(perform_google_restaurant_search, trip["destination"], key, trip.get("cuisine"))
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
        elif name in ("attractions", "restaurants"):
            entry["items"] = [
                {"id": p["id"], "name": p.get("name"), "rating": p.get("rating"), "reviews": p.get("total_ratings"),
                 "price_level": p.get("price_level"), "summary": p.get("editorial_summary")}
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


async def compose_node(state: TravelState) -> Dict[str, Any]:
    emit({"event": "agent", "agent": "compose", "state": "running"})
    trip = state.get("trip") or {}
    results = compact_results(state.get("sections") or {})
    if use_fixtures():
        answer = fixtures.answer(trip, results)
        # Stream the canned answer word by word like the model would.
        for word in answer.split(" "):
            emit({"event": "delta", "text": word + " "})
            await asyncio.sleep(0.01)
        emit({"event": "agent", "agent": "compose", "state": "done"})
        return {"answer": answer, "status": "success"}

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
    emit({"event": "agent", "agent": "compose", "state": "done"})
    return {"answer": answer, "status": "success"}


# ------------------------------------------------------------------ graph
def build_travel_graph():
    g = StateGraph(TravelState)
    g.add_node("intake", intake_node)
    g.add_node("flights", flights_node)
    g.add_node("hotels", hotels_node)
    g.add_node("attractions", attractions_node)
    g.add_node("restaurants", restaurants_node)
    g.add_node("weather", weather_node)
    g.add_node("compose", compose_node)
    g.set_entry_point("intake")
    g.add_edge("intake", "flights")
    g.add_edge("flights", "hotels")
    g.add_edge("hotels", "attractions")
    g.add_edge("attractions", "restaurants")
    g.add_edge("restaurants", "weather")
    g.add_edge("weather", "compose")
    g.add_edge("compose", END)
    return g.compile()


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
        "answer": "",
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
    for name in ("flights", "hotels", "attractions", "restaurants"):
        if name in sections:
            payload[name] = sections[name].get("items") or []
    if "weather" in sections:
        payload["weather"] = sections["weather"].get("forecast")
    return payload
