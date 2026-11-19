from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
import logging

from tools.routestack_auth import headers, BASE_URL
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)


class FlightSegment(BaseModel):
    airline: str = ""
    flight_number: str = ""
    origin: str = ""
    destination: str = ""
    departure_time: str = ""
    arrival_time: str = ""
    duration: str = ""
    cabin_class: str = ""
    departure_airport: str = ""
    arrival_airport: str = ""


class FlightResult(BaseModel):
    price: str = ""
    segments: List[FlightSegment] = []
    stops: int = 0
    fareSourceCode: str = ""


@router.get("/search", response_model=List[FlightResult])
async def search_flights(
    origin_id: str = Query(..., description="Origin city or airport code"),
    destination_id: str = Query(..., description="Destination city or airport code"),
    departure_date: date = Query(..., description="Departure date (YYYY-MM-DD)"),
    return_date: Optional[date] = Query(None, description="Return date (YYYY-MM-DD)"),
    adults: int = Query(1, description="Number of adults"),
    cabin_class: str = Query("Economy", description="Cabin class"),
):
    try:
        hdrs = headers()

        origin_resp = httpx.post(
            f"{BASE_URL}/mcp/flight/locations",
            headers=hdrs,
            json={"term": origin_id},
            timeout=15,
        )
        origin_resp.raise_for_status()
        origin_locs = origin_resp.json().get("result", [])
        if not origin_locs:
            raise HTTPException(status_code=404, detail=f"Could not find airport for: {origin_id}")

        dest_resp = httpx.post(
            f"{BASE_URL}/mcp/flight/locations",
            headers=hdrs,
            json={"term": destination_id},
            timeout=15,
        )
        dest_resp.raise_for_status()
        dest_locs = dest_resp.json().get("result", [])
        if not dest_locs:
            raise HTTPException(status_code=404, detail=f"Could not find airport for: {destination_id}")

        origin_code = origin_locs[0].get("code", origin_id)
        dest_code = dest_locs[0].get("code", destination_id)

        trip_type = "RoundTrip" if return_date else "OneWay"
        search_body = {
            "origin": origin_code,
            "destination": dest_code,
            "departureDate": str(departure_date),
            "adults": adults,
            "cabinClass": cabin_class,
            "type": trip_type,
        }
        if return_date:
            search_body["returnDate"] = str(return_date)

        search_resp = httpx.post(
            f"{BASE_URL}/mcp/flight/search",
            headers=hdrs,
            json=search_body,
            timeout=60,
        )
        search_resp.raise_for_status()
        data = search_resp.json()

        raw = data.get("result", [])
        flights = []
        for itin in raw[:20]:
            segs = itin.get("flights", [])
            seg_list = []
            for s in segs:
                seg_list.append(FlightSegment(
                    airline=s.get("airline", ""),
                    flight_number=f"{s.get('flightCode', '')}{s.get('flightNumber', '')}",
                    origin=s.get("departure", ""),
                    destination=s.get("arrival", ""),
                    departure_time=str(s.get("departureTime", "")),
                    arrival_time=str(s.get("arrivalTime", "")),
                    duration=f"{s.get('triptime', 0) // 60}h {s.get('triptime', 0) % 60}m",
                    cabin_class=s.get("cabin", cabin_class),
                    departure_airport=s.get("departairport", ""),
                    arrival_airport=s.get("arrivalairport", ""),
                ))

            price_val = itin.get("ourprice") or itin.get("totalFare") or itin.get("baseFare", "N/A")
            price_str = f"USD {price_val}"

            flights.append(FlightResult(
                price=price_str,
                segments=seg_list,
                stops=itin.get("stops", max(len(seg_list) - 1, 0)),
                fareSourceCode=itin.get("fareSourceCode", ""),
            ))

        return flights

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flight search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Flight search failed: {str(e)}")
