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
logger = logging.getLogger('restaurant_agent')

# ------------------ Cache ------------------ #
# Simple in-memory cache to reduce API calls
RESTAURANT_CACHE = {}

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

# ------------------ Restaurant Search ------------------ #
def search_restaurants(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core restaurant search function that takes parsed parameters
    and returns restaurant search results or error
    """
    try:
        # Required field guard
        required_keys = ["location", "cuisine"]
        missing = [k for k in required_keys if k not in params or not params[k]]
        if missing:
            return {"error": f"Missing required parameter(s): {', '.join(missing)}"}

        # Create a cache key
        cache_key = f"{params['location']}-{params['cuisine']}"
        if cache_key in RESTAURANT_CACHE:
            logger.info(f"🔍 Restaurant results for {cache_key} found in cache")
            return RESTAURANT_CACHE[cache_key]

        # Check if we need to wait due to rate limiting
        wait_seconds = rate_limiter.wait_time()
        if wait_seconds > 0:
            logger.info(f"⏳ Rate limiting - waiting {wait_seconds:.2f}s before restaurant search request")
            time.sleep(wait_seconds)

        # Try multiple query formats to increase chances of finding results
        queries = [
            f"best {params['cuisine']} restaurant in {params['location']}",
            f"{params['cuisine']} restaurant {params['location']}",
            f"{params['cuisine']} food in {params['location']}",
        ]
        
        result = None
        
        for query in queries:
            logger.info(f"🔍 Trying query: {query}")
            
            try:
                rate_limiter.record_call()
                # Use the places service to find restaurants
                search_result = places_service.find_place_from_text(query)
                
                if "error" not in search_result:
                    result = search_result
                    logger.info(f"✅ Found result with query: {query}")
                    break
                else:
                    logger.warning(f"⚠️ No results for query: {query}")
            except Exception as e:
                logger.error(f"❌ Error with query '{query}': {e}")
                continue
        
        if not result:
            return {"error": f"Could not find any {params['cuisine']} restaurants in {params['location']}"}
            
        logger.info(f"✅ Restaurant search success")
        
        # Create a response with additional metadata
        restaurants_data = {
            "restaurant": result,
            "query": {
                "location": params["location"],
                "cuisine": params["cuisine"]
            }
        }
        
        # Cache the result
        RESTAURANT_CACHE[cache_key] = {"restaurants": restaurants_data}
        
        return {"restaurants": restaurants_data}
            
    except Exception as e:
        logger.error(f"❌ Restaurant Search Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}
# ------------------ Restaurant Agent Main Function ------------------ #
def restaurant_search_agent(*, input_str: str) -> Dict[str, Any]:
    """
    Main restaurant search agent function that takes either natural language
    or structured input and returns restaurant search results
    """
    try:
        print("🔧 restaurant_search_agent CALLED with:", input_str)
        logger.info(f"🔍 Received input_str: {input_str}")

        # Parse the input string (either directly or preprocess with LLM in the other file)
        if re.search(r"location=.*&cuisine=", input_str):
            # Already in structured format
            params = dict(param.split("=", 1) for param in input_str.split("&") if "=" in param)
            logger.info(f"🔧 Params parsed: {params}")
            return search_restaurants(params)
        else:
            # For natural language input, we need to call the LLM parser
            # This will be handled in the parent file that imports this module
            return {"error": "Natural language parsing should be handled by the parent module"}

    except Exception as e:
        logger.error(f"❌ Restaurant Search Agent Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}

# ------------------ Formatting ------------------ #
def format_restaurant_results(restaurant_data: Dict[str, Any]) -> str:
    """Format restaurant search results into a readable string"""
    if "error" in restaurant_data:
        return f"❌ Restaurant search error: {restaurant_data['error']}"
    
    if "restaurants" not in restaurant_data:
        return "⚠️ No restaurant data received."
    
    restaurant = restaurant_data["restaurants"]["restaurant"]
    query = restaurant_data["restaurants"]["query"]
    
    msg = f"Here is a recommended {query['cuisine']} restaurant in {query['location']}:\n\n"
    
    # Build the restaurant info
    name = restaurant.get("place_name", "Unknown Restaurant")
    address = restaurant.get("place_address", "Unknown Location")
    
    msg += f"### {name} - Address: {address}"
    
    # Add map link if available
    map_url = restaurant.get("map_url")
    if map_url:
        msg += f" - [View on Google Maps]({map_url})"
    
    msg += "\n\nEnjoy your meal!"
    
    return msg