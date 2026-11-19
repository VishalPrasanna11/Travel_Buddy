# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""LangGraph tool wrapper to Google Maps Places API (new)."""

import os
import requests
from typing import Dict, List, Any
from langchain_core.tools import tool


class PlacesService:
    """Wrapper to Places API (new)."""

    def _check_key(self):
        if not hasattr(self, "places_api_key") or not self.places_api_key:
            self.places_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    def find_place_from_text(self, query: str) -> Dict[str, str]:
        """Fetches place details using a text query via the new Places API."""
        self._check_key()

        if not self.places_api_key:
            print("WARNING: Google Places API key is not set!")
            return {"error": "Google Places API key is not set"}

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.places_api_key,
            "X-Goog-FieldMask": "places.id,places.formattedAddress,places.displayName,places.photos,places.location",
        }
        body = {"textQuery": query}

        try:
            print(f"Making Places API request with query: '{query}'")
            response = requests.post(url, headers=headers, json=body)
            status_code = response.status_code
            print(f"Places API response status: {status_code}")

            response.raise_for_status()
            place_data = response.json()

            if not place_data.get("places"):
                print(f"No places found for query: '{query}'")
                return {"error": "No places found."}

            place_details = place_data["places"][0]
            place_id = place_details.get("id", "")
            place_name = place_details.get("displayName", {}).get("text", "")
            place_address = place_details.get("formattedAddress", "")
            photos = self.get_photo_urls(place_details.get("photos", []), maxwidth=400)
            map_url = self.get_map_url(place_id)
            location = place_details.get("location", {})
            lat = str(location.get("latitude", ""))
            lng = str(location.get("longitude", ""))

            print(f"Found place: {place_name} at {place_address}")
            return {
                "place_id": place_id,
                "place_name": place_name,
                "place_address": place_address,
                "photos": photos,
                "map_url": map_url,
                "lat": lat,
                "lng": lng,
            }

        except requests.exceptions.RequestException as e:
            print(f"Request exception: {e}")
            return {"error": f"Error fetching place data: {e}"}

    def get_photo_urls(self, photos: List[Dict[str, Any]], maxwidth: int = 400) -> List[str]:
        """Extracts photo URLs from the new API photo resources."""
        photo_urls = []
        for photo in photos:
            photo_name = photo.get("name", "")
            if photo_name:
                photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx={maxwidth}&key={self.places_api_key}"
                photo_urls.append(photo_url)
        return photo_urls

    def get_map_url(self, place_id: str) -> str:
        """Generates the Google Maps URL for a given place ID."""
        return f"https://www.google.com/maps/place/?q=place_id:{place_id}"


places_service = PlacesService()


@tool
def map_tool(state: Dict[str, Any], key: str) -> Dict[str, Any]:
    """
    Enriches POIs in state[key]['places'] with Google Maps geolocation data.

    Args:
        state: The LangGraph state object.
        key: The state key under which POIs are stored.

    Returns:
        Updated state with populated place_id, lat, lng, and map_url.
    """
    if key not in state:
        state[key] = {}

    if "places" not in state[key]:
        state[key]["places"] = []

    pois = state[key]["places"]
    for poi in pois:
        location = poi["place_name"] + ", " + poi["address"]
        result = places_service.find_place_from_text(location)
        poi["place_id"] = result.get("place_id")
        poi["map_url"] = result.get("map_url")
        if "lat" in result and "lng" in result:
            poi["lat"] = result["lat"]
            poi["long"] = result["lng"]

    return {key: {"places": pois}}
