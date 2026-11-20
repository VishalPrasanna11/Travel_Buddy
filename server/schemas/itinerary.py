"""
Structured itinerary returned by GPT-4o with response_format json_schema
(strict). Every field is required by the schema; "unknown" is null.
Item refs point at entity ids from the same response (fl_…, ht_…, pl_…).
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Slot = Literal["morning", "afternoon", "evening", "night"]
ItemKind = Literal["place", "restaurant", "hotel", "flight", "car", "transit", "free", "note"]


class ItineraryItem(BaseModel):
    slot: Slot
    kind: ItemKind
    ref: Optional[str] = Field(description="id of the entity from RESULTS this item uses (e.g. pl_ab12…), or null")
    title: str = Field(description="Short label, e.g. 'Belém Tower'")
    note: Optional[str] = Field(description="One practical tip, or null")
    start_time: Optional[str] = Field(description="Local start time HH:MM if it matters (flight, booking), else null")
    duration_minutes: Optional[int] = Field(description="Rough time to allow, or null")


class ItineraryDay(BaseModel):
    date: str = Field(description="YYYY-MM-DD")
    title: str = Field(description="Theme of the day, e.g. 'Alfama and the castle'")
    items: List[ItineraryItem]


class Travelers(BaseModel):
    adults: int
    children: int


class ItineraryDestination(BaseModel):
    name: str
    place_id: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    timezone: Optional[str] = Field(description="IANA time zone, e.g. Europe/Lisbon")


class ItineraryTrip(BaseModel):
    destination: ItineraryDestination
    origin: Optional[str]
    start_date: str
    end_date: str
    travelers: Travelers


class Itinerary(BaseModel):
    trip: ItineraryTrip
    days: List[ItineraryDay]
    summary: str = Field(description="One-sentence overview of the plan")
