import os
import json
import httpx
import re
import logging
import traceback
import time
from typing import Dict, Any, List, Optional

# Import the places service
from tools.places import places_service

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('attractions_agent')

# ------------------ Cache ------------------ #
# Simple in-memory cache to reduce API calls
ATTRACTIONS_CACHE = {}

# ------------------ Rate Limiter ------------------ #
class RateLimiter:
    """Rate limiter to prevent hitting API limits"""
    def __init__(self, max_calls=10, time_frame=1):  # Default 10 TPS
        self.max_calls = max_calls
        self.time_frame = time_frame  # in seconds
        self.call_timestamps = []
        self.last_429_time = None
        self.backoff_time = 5  # Initial backoff in seconds
    
    def can_make_call(self):
        """Check if we can make a call based on our rate limit tracking"""
        now = time.time()
        
        # Remove timestamps older than our time frame
        self.call_timestamps = [t for t in self.call_timestamps if now - t <= self.time_frame]
        
        # If we've recently hit a 429, use exponential backoff
        if self.last_429_time and now - self.last_429_time < self.backoff_time:
            return False
        
        # Check if we're within rate limits
        return len(self.call_timestamps) < self.max_calls
    
    def record_call(self):
        """Record that we made a call"""
        self.call_timestamps.append(time.time())
    
    def record_429(self):
        """Record that we received a 429 error"""
        now = time.time()
        self.last_429_time = now
        # Increase backoff time exponentially (max 60 seconds)
        self.backoff_time = min(self.backoff_time * 2, 60)
        logger.warning(f"⚠️ Rate limited. New backoff time: {self.backoff_time}s")
    
    def wait_time(self):
        """Calculate how long to wait before next call"""
        now = time.time()
        
        # If we've hit a 429 recently, respect the backoff
        if self.last_429_time and now - self.last_429_time < self.backoff_time:
            return self.backoff_time - (now - self.last_429_time)
        
        # If we're at capacity, calculate wait time until oldest call expires
        if len(self.call_timestamps) >= self.max_calls and self.call_timestamps:
            return max(0, self.time_frame - (now - self.call_timestamps[0]))
        
        return 0  # No need to wait

# Initialize rate limiter
rate_limiter = RateLimiter()

# ------------------ Attractions Search ------------------ #
def search_attractions(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core attractions search function that takes parsed parameters
    and returns attractions search results or error
    """
    try:
        # Required field guard
        required_keys = ["location", "attraction_type"]
        missing = [k for k in required_keys if k not in params or not params[k]]
        if missing:
            return {"error": f"Missing required parameter(s): {', '.join(missing)}"}

        # Create a cache key
        cache_key = f"{params['location']}-{params['attraction_type']}"
        if cache_key in ATTRACTIONS_CACHE:
            logger.info(f"🔍 Attraction results for {cache_key} found in cache")
            return ATTRACTIONS_CACHE[cache_key]

        # Check if we need to wait due to rate limiting
        wait_seconds = rate_limiter.wait_time()
        if wait_seconds > 0:
            logger.info(f"⏳ Rate limiting - waiting {wait_seconds:.2f}s before attraction search request")
            time.sleep(wait_seconds)

        # Construct the search query
        query = f"{params['attraction_type']} in {params['location']}"
        
        try:
            rate_limiter.record_call()
            # Use the places service to find attractions
            result = places_service.find_place_from_text(query)
            
            if "error" in result:
                logger.error(f"❌ Attraction search error: {result['error']}")
                return {"error": result["error"]}
            
            logger.info(f"✅ Attraction search success")
            
            # Create a response with additional metadata
            attractions_data = {
                "attraction": result,
                "query": {
                    "location": params["location"],
                    "attraction_type": params["attraction_type"]
                }
            }
            
            # Cache the result
            ATTRACTIONS_CACHE[cache_key] = {"attractions": attractions_data}
            
            return {"attractions": attractions_data}
            
        except Exception as e:
            logger.error(f"❌ Attraction search request error: {e}")
            return {"error": f"Error searching for attractions: {str(e)}"}

    except Exception as e:
        logger.error(f"❌ Attraction Search Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}

# ------------------ Attractions Agent Main Function ------------------ #
def attractions_search_agent(*, input_str: str) -> Dict[str, Any]:
    """
    Main attractions search agent function that takes either natural language
    or structured input and returns attractions search results
    """
    try:
        print("🔧 attractions_search_agent CALLED with:", input_str)
        logger.info(f"🔍 Received input_str: {input_str}")

        # Parse the input string (either directly or preprocess with LLM in the other file)
        if re.search(r"location=.*&attraction_type=", input_str):
            # Already in structured format
            params = dict(param.split("=", 1) for param in input_str.split("&") if "=" in param)
            logger.info(f"🔧 Params parsed: {params}")
            return search_attractions(params)
        else:
            # For natural language input, we need to call the LLM parser
            # This will be handled in the parent file that imports this module
            return {"error": "Natural language parsing should be handled by the parent module"}

    except Exception as e:
        logger.error(f"❌ Attraction Search Agent Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}

# ------------------ Formatting ------------------ #
def format_attractions_results(attractions_data: Dict[str, Any]) -> str:
    """Format attractions search results into a readable string"""
    if "error" in attractions_data:
        return f"❌ Attraction search error: {attractions_data['error']}"
    
    if "attractions" not in attractions_data:
        return "⚠️ No attraction data received."
    
    attraction = attractions_data["attractions"]["attraction"]
    query = attractions_data["attractions"]["query"]
    
    msg = f"Here's a recommended {query['attraction_type']} in {query['location']}:\n\n"
    
    # Build the attraction info
    name = attraction.get("place_name", "Unknown Attraction")
    address = attraction.get("place_address", "Unknown Location")
    
    msg += f"**{name}**\n"
    msg += f"📍 Address: {address}\n"
    
    # Add map link if available
    map_url = attraction.get("map_url")
    if map_url:
        msg += f"🗺️ [View on Google Maps]({map_url})\n"
    
    # Add coordinates if available
    lat = attraction.get("lat")
    lng = attraction.get("lng")
    if lat and lng:
        msg += f"📌 Coordinates: {lat}, {lng}\n"
    
    # Add photos if available
    photos = attraction.get("photos", [])
    if photos:
        msg += "\n📸 Photos:\n"
        for i, photo in enumerate(photos[:3], 1):  # Limit to 3 photos
            msg += f"- [Photo {i}]({photo})\n"
    
    return msg