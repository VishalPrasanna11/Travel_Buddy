import logging
from typing import Dict, Any

from schemas.entities import dump, now_iso
from tools.google_places_common import normalize_place, text_search

logger = logging.getLogger("google_places_api")
logging.basicConfig(level=logging.INFO)


def perform_google_places_explore(location: str, api_key: str, query: str = None) -> Dict[str, Any]:
    """Top attractions for a location, normalized through schemas.Place."""
    try:
        logger.info(f"Searching Google Places (new API) for: {location}")
        fetched_at = now_iso()
        results = text_search(query or f"top tourist attractions in {location}", api_key)
        attractions = [normalize_place(p, "attraction", fetched_at) for p in results]
        return {"location": location, "attractions": dump(attractions), "fetched_at": fetched_at, "source": "google_places"}
    except Exception as e:
        logger.error(f"Failed to fetch places for {location}: {e}")
        return {"error": f"Failed to fetch attractions for {location}: {str(e)}"}
