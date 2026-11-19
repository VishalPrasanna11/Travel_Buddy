import os
import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("google_restaurant_api")
logging.basicConfig(level=logging.INFO)

GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"


def perform_google_restaurant_search(location: str, api_key: str) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.types,places.location,places.photos",
    }
    body = {
        "textQuery": f"best restaurants in {location}",
        "includedType": "restaurant",
    }

    try:
        logger.info(f"Searching restaurants in: {location}")
        response = httpx.post(GOOGLE_PLACES_URL, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        results = response.json().get("places", [])[:10]

        restaurants = []
        for place in results:
            name = place.get("displayName", {}).get("text", "")
            address = place.get("formattedAddress", "")
            rating = place.get("rating", 0.0)
            total_ratings = place.get("userRatingCount", 0)
            types = place.get("types", [])
            location_data = place.get("location", {})

            photo_url = None
            if photos := place.get("photos"):
                photo_name = photos[0].get("name", "")
                if photo_name:
                    photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx=400&key={api_key}"

            restaurants.append({
                "name": name,
                "address": address,
                "rating": rating,
                "total_ratings": total_ratings,
                "photo_url": photo_url,
                "location": {"lat": location_data.get("latitude"), "lng": location_data.get("longitude")},
                "types": types,
            })

        return {"location": location, "restaurants": restaurants}

    except Exception as e:
        logger.error(f"Failed to fetch restaurants for {location}: {e}")
        return {"error": f"Failed to fetch restaurants for {location}: {str(e)}"}
