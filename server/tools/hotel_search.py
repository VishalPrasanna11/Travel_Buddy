from langchain_core.tools import tool
from typing import Dict, Any
import httpx
import os
import logging

logger = logging.getLogger("hotel_search")

GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"


def _search_hotels_google(params: Dict[str, str]) -> Dict[str, Any]:
    city = params.get("city", "")
    check_in = params.get("checkInDate", "")
    check_out = params.get("checkOutDate", "")
    adults = params.get("adults", "2")

    if not city:
        return {"error": "Missing required parameter: city"}

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_PLACE_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "Google API key not configured"}

    try:
        query = f"hotels in {city}"
        if check_in and check_out:
            query += f" available {check_in} to {check_out}"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.types,places.location,places.photos,places.priceLevel",
        }
        body = {
            "textQuery": query,
            "includedType": "hotel",
        }

        response = httpx.post(GOOGLE_PLACES_URL, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        results = response.json().get("places", [])[:10]

        hotels = []
        for place in results:
            name = place.get("displayName", {}).get("text", "")
            address = place.get("formattedAddress", "")
            rating = place.get("rating", 0.0)
            total_ratings = place.get("userRatingCount", 0)
            price_level = place.get("priceLevel", "PRICE_LEVEL_UNSPECIFIED")
            location_data = place.get("location", {})

            photo_url = None
            if photos := place.get("photos"):
                photo_name = photos[0].get("name", "")
                if photo_name:
                    photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx=400&key={api_key}"

            hotels.append({
                "name": name,
                "address": address,
                "rating": rating,
                "total_ratings": total_ratings,
                "price_level": price_level,
                "photo_url": photo_url,
                "location": {"lat": location_data.get("latitude"), "lng": location_data.get("longitude")},
            })

        return {
            "hotels": hotels,
            "count": len(hotels),
            "city": city,
            "checkInDate": check_in,
            "checkOutDate": check_out,
        }

    except Exception as e:
        logger.error(f"Hotel search error: {str(e)}")
        return {"error": f"Hotel search failed: {str(e)}"}


@tool
def hotel_search(input_str: str) -> Dict[str, Any]:
    """
    LangChain-compatible tool for hotel search using Google Places.

    Expected input_str:
    "city=Paris&checkInDate=2025-05-01&checkOutDate=2025-05-05&adults=2"
    """
    try:
        params = dict(p.split("=", 1) for p in input_str.split("&") if "=" in p)
        return _search_hotels_google(params)
    except Exception as e:
        return {"error": f"Failed to process hotel search: {str(e)}"}
