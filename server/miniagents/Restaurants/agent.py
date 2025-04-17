import os
import json
import re
import logging
import traceback
from typing import Dict, Any, List, Optional

# Import the restaurant search tool
from tools.restaurant_search_tool import search_restaurants

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

# ------------------ Restaurant Agent Main Function ------------------ #
def restaurant_search_agent(*, input_str: str) -> Dict[str, Any]:
    """
    Main restaurant search agent function that takes either natural language
    or structured input and returns restaurant search results
    """
    try:
        logger.info(f"🔍 Received input_str: {input_str}")

        # Check if it's already in cache
        if input_str in RESTAURANT_CACHE:
            logger.info(f"🔍 Results for {input_str} found in cache")
            return RESTAURANT_CACHE[input_str]

        # Parse the input string to extract location
        if "location=" in input_str:
            # Already in structured format - use directly
            logger.info(f"🔧 Using structured input: {input_str}")
            result = search_restaurants(input_str)
        else:
            # For natural language input, try to extract the location
            location_match = re.search(r"(?:in|at|near|around)\s+([A-Za-z\s,]+)", input_str)
            if location_match:
                location = location_match.group(1).strip()
                logger.info(f"🔧 Extracted location: {location}")
                structured_input = f"location={location}"
                result = search_restaurants(structured_input)
            else:
                return {"error": "Could not determine location from input. Please specify a location."}
        
        # Cache the result
        RESTAURANT_CACHE[input_str] = result
        
        return result

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
    
    restaurants = restaurant_data["restaurants"]
    location = restaurants.get("location", "Unknown Location")
    restaurant_list = restaurants.get("restaurants", [])
    
    if not restaurant_list:
        return f"⚠️ No restaurants found in {location}."
    
    msg = f"Here are recommended restaurants in {location}:\n\n"
    
    for i, restaurant in enumerate(restaurant_list[:5], 1):
        name = restaurant.get("name", "Unknown Restaurant")
        address = restaurant.get("address", "Unknown Location")
        rating = restaurant.get("rating", "Not rated")
        total_ratings = restaurant.get("total_ratings", 0)
        
        msg += f"### {i}. {name}\n"
        msg += f"- Address: {address}\n"
        msg += f"- Rating: {rating}/5 ({total_ratings} reviews)\n"
        
        if "types" in restaurant and restaurant["types"]:
            msg += f"- Types: {', '.join(restaurant['types'][:3])}\n"
        
        msg += "\n"
    
    return msg