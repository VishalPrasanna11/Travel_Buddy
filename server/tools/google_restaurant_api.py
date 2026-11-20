import logging
from typing import Dict, Any

from schemas.entities import dump, now_iso
from tools.google_places_common import normalize_place, text_search

logger = logging.getLogger("google_restaurant_api")
logging.basicConfig(level=logging.INFO)


def perform_google_restaurant_search(location: str, api_key: str, cuisine: str = None) -> Dict[str, Any]:
    """Top restaurants for a location, normalized through schemas.Place."""
    try:
        logger.info(f"Searching restaurants in: {location}")
        fetched_at = now_iso()
        query = f"best {cuisine + ' ' if cuisine else ''}restaurants in {location}"
        results = text_search(query, api_key, included_type="restaurant")
        restaurants = [normalize_place(p, "restaurant", fetched_at) for p in results]
        return {"location": location, "restaurants": dump(restaurants), "fetched_at": fetched_at, "source": "google_places"}
    except Exception as e:
        logger.error(f"Failed to fetch restaurants for {location}: {e}")
        return {"error": f"Failed to fetch restaurants for {location}: {str(e)}"}
