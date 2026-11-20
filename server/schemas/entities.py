"""
One schema per entity. Every tool output (RouteStack, Google Places,
OpenWeather) is normalized through these models before it reaches the
agents, the SSE stream or the client.

Every entity carries:
  id          stable id within a response ("fl_…", "ht_…", "pl_…", "wx_…")
  source      "routestack" | "google_places" | "openweather" | "simulated"
  fetched_at  ISO-8601 UTC timestamp of the upstream call
  is_estimate True when the values are not live provider data
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["routestack", "google_places", "openweather", "simulated"]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_id(prefix: str, *parts: Any) -> str:
    """Deterministic short id so the same upstream record keeps its id."""
    raw = "|".join(str(p) for p in parts if p is not None)
    return f"{prefix}_{hashlib.sha1(raw.encode()).hexdigest()[:10]}"


def to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


class EntityBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    source: Source
    fetched_at: str = Field(default_factory=now_iso)
    is_estimate: bool = False


class Price(BaseModel):
    """Prices are data, never only prose."""

    amount: float
    currency: str = "USD"
    basis: Literal["total", "per_night", "per_person", "per_day", "per_trip"] = "total"
    total: Optional[float] = None
    per_traveler: Optional[float] = None
    taxes_included: Optional[bool] = None
    published: Optional[float] = None
    saving: Optional[float] = None
    as_of: str = Field(default_factory=now_iso)

    @classmethod
    def maybe(cls, amount: Any, currency: str = "USD", **kw) -> Optional["Price"]:
        value = to_float(amount)
        if value is None:
            return None
        return cls(amount=value, currency=currency or "USD", **kw)


class LatLng(BaseModel):
    lat: float
    lng: float


class Photo(BaseModel):
    """`ref` is the Google photo resource name; clients load it through
    GET /api/places/photo/{ref}. `url` is used for non-Google photos."""

    ref: Optional[str] = None
    url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    attributions: List[Dict[str, Any]] = Field(default_factory=list)


# ------------------------------------------------------------------ flights
class FlightEndpoint(BaseModel):
    airport: str = ""
    airport_name: Optional[str] = None
    terminal: Optional[str] = None
    at: Optional[str] = None  # local time, ISO-8601 with UTC offset when known
    utc_offset: Optional[str] = None


class FlightSegment(BaseModel):
    carrier: str = ""
    carrier_name: Optional[str] = None
    flight_number: str = ""
    departure: FlightEndpoint
    arrival: FlightEndpoint
    duration_minutes: Optional[int] = None
    duration: Optional[str] = None  # ISO-8601 duration, e.g. PT7H5M
    cabin_class: Optional[str] = None
    layover_minutes: Optional[int] = None  # wait after this segment, before the next
    aircraft: Optional[str] = None
    fare_family: Optional[str] = None
    checked_baggage: Optional[str] = None
    cabin_baggage: Optional[str] = None
    seats_left: Optional[int] = None


class Baggage(BaseModel):
    checked: Optional[str] = None
    cabin: Optional[str] = None


class Flight(EntityBase):
    source: Source = "routestack"
    carrier: str = ""
    carrier_name: Optional[str] = None
    origin: str = ""
    destination: str = ""
    departure_at: Optional[str] = None
    arrival_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    duration: Optional[str] = None
    stops: int = 0
    return_stops: Optional[int] = None
    return_duration_minutes: Optional[int] = None
    cabin_class: Optional[str] = None
    fare_family: Optional[str] = None
    bookable: bool = False
    segments: List[FlightSegment] = Field(default_factory=list)
    return_segments: List[FlightSegment] = Field(default_factory=list)
    price: Optional[Price] = None
    baggage: Optional[Baggage] = None
    refundable: Optional[bool] = None
    booking_url: Optional[str] = None
    fare_source_code: Optional[str] = None


# ------------------------------------------------------------------- hotels
class Hotel(EntityBase):
    source: Source = "routestack"
    name: str
    address: Optional[str] = None
    location: Optional[LatLng] = None
    star_rating: Optional[float] = None
    guest_rating: Optional[float] = None
    review_count: Optional[int] = None
    price: Optional[Price] = None
    nightly_price: Optional[Price] = None
    nights: Optional[int] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    amenities: List[str] = Field(default_factory=list)  # typed codes, e.g. WIFI, POOL
    amenity_names: List[str] = Field(default_factory=list)
    photos: List[Photo] = Field(default_factory=list)
    cancellation_policy: Optional[str] = None
    refundable: Optional[bool] = None
    provider: Optional[str] = None
    hotel_id: Optional[str] = None
    pay_at_hotel: Optional[bool] = None
    free_breakfast: Optional[bool] = None
    chain: Optional[str] = None
    distance_km: Optional[float] = None
    bookable: bool = False
    booking_url: Optional[str] = None


# ------------------------------------------------------------------- places
class OpeningHours(BaseModel):
    open_now: Optional[bool] = None
    weekday_descriptions: List[str] = Field(default_factory=list)
    periods: List[Dict[str, Any]] = Field(default_factory=list)


class Review(BaseModel):
    author: Optional[str] = None
    rating: Optional[float] = None
    text: Optional[str] = None
    relative_time: Optional[str] = None


class Place(EntityBase):
    source: Source = "google_places"
    kind: Literal["attraction", "restaurant", "destination", "other"] = "attraction"
    place_id: Optional[str] = None
    name: str
    address: Optional[str] = None
    location: Optional[LatLng] = None
    viewport: Optional[Dict[str, LatLng]] = None  # {"low": LatLng, "high": LatLng}
    rating: Optional[float] = None
    total_ratings: Optional[int] = None
    types: List[str] = Field(default_factory=list)
    primary_type: Optional[str] = None
    price_level: Optional[int] = None  # 0 (free) … 4 (very expensive)
    editorial_summary: Optional[str] = None
    opening_hours: Optional[OpeningHours] = None
    website: Optional[str] = None
    google_maps_uri: Optional[str] = None
    phone: Optional[str] = None
    photos: List[Photo] = Field(default_factory=list)
    reviews: List[Review] = Field(default_factory=list)
    utc_offset_minutes: Optional[int] = None
    # Back-compat: older clients read photo_url. Always a proxy URL, never a keyed Google URL.
    photo_url: Optional[str] = None


# ------------------------------------------------------------------ weather
class WeatherDay(EntityBase):
    source: Source = "openweather"
    date: str  # YYYY-MM-DD, local to the destination
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    units: Literal["metric", "imperial"] = "metric"
    condition_id: Optional[int] = None  # OpenWeather condition code (800 = clear)
    condition: Optional[str] = None
    icon: Optional[str] = None
    pop: Optional[float] = None  # probability of precipitation, 0..1
    precipitation_mm: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    uvi: Optional[float] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    summary: Optional[str] = None
    kind: Literal["forecast", "day_summary", "simulated"] = "forecast"


class WeatherAlert(BaseModel):
    sender: Optional[str] = None
    event: str
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None


class WeatherForecast(EntityBase):
    source: Source = "openweather"
    location: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    timezone: Optional[str] = None
    units: Literal["metric", "imperial"] = "metric"
    is_simulated: bool = False
    current: Optional[Dict[str, Any]] = None
    days: List[WeatherDay] = Field(default_factory=list)
    alerts: List[WeatherAlert] = Field(default_factory=list)
    report: Optional[str] = None  # one-line prose kept for older clients


# ------------------------------------------------------------- car rentals
class CarRental(EntityBase):
    source: Source = "routestack"
    vendor: Optional[str] = None
    vendor_logo: Optional[str] = None
    name: str = ""
    category: Optional[str] = None  # e.g. Compact, SUV
    transmission: Optional[str] = None
    seats: Optional[int] = None
    bags: Optional[int] = None
    air_conditioning: Optional[bool] = None
    image_url: Optional[str] = None
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    pickup_at: Optional[str] = None
    dropoff_at: Optional[str] = None
    price: Optional[Price] = None
    mileage: Optional[str] = None
    free_cancellation: Optional[bool] = None
    days: Optional[int] = None
    bookable: bool = False
    booking_url: Optional[str] = None


def dump(items: List[BaseModel]) -> List[Dict[str, Any]]:
    return [i.model_dump(mode="json", exclude_none=True) for i in items]
