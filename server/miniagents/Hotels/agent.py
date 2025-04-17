from langchain_core.tools import BaseTool
from typing import Dict, Any
import re
import logging
import traceback
from tools.hotel_search import hotel_search

logger = logging.getLogger('hotel_agent')

# ------------------ Hotel Agent Main Function with Tool ------------------ #
def hotel_search_agent(*, input_str: str) -> Dict[str, Any]:
    """
    Main hotel search agent function that takes either natural language
    or structured input and returns hotel search results using the hotel_search tool
    """
    try:
        logger.info(f"🔍 Received input_str: {input_str}")

        # Parse the input string (either directly or preprocess with LLM in the other file)
        if re.search(r"city=.*&checkInDate=.*&checkOutDate=.*&adults=", input_str):
            # Already in structured format, use the hotel_search tool directly
            logger.info(f"🔧 Using structured input with hotel_search tool: {input_str}")
            return hotel_search(input_str)
        else:
            # For natural language input, we need to call the LLM parser
            # This will be handled in the parent file that imports this module
            return {"error": "Natural language parsing should be handled by the parent module"}

    except Exception as e:
        logger.error(f"❌ Hotel Search Agent Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}
def format_hotel_results(hotels_data: Dict[str, Any]) -> str:
    """Format hotel search results into a readable string"""
    if "error" in hotels_data:
        return f"❌ Hotel search error: {hotels_data['error']}"
    
    if "attractions" not in hotels_data:
        return "⚠️ No hotel data received."
    
    hotels_list = hotels_data["attractions"]["attractions_list"]
    location = hotels_data["attractions"]["query"]["location"]
    
    if "error" in hotels_list:
        return f"❌ Error finding hotels: {hotels_list['error']}"
    
    if not hotels_list.get("attractions", []):
        return f"No hotels found for {location}."
    
    msg = f"Top hotels in {location}:\n\n"
    
    # Build the hotels list
    for i, hotel in enumerate(hotels_list.get("attractions", [])[:5], 1):
        name = hotel.get("name", "Unknown Hotel")
        address = hotel.get("address", "Unknown Location")
        rating = hotel.get("rating", "N/A")
        total_ratings = hotel.get("total_ratings", "N/A")
        
        msg += f"**{i}. {name}**\n"
        msg += f"📍 Address: {address}\n"
        msg += f"⭐ Rating: {rating}/5 ({total_ratings} reviews)\n"
        
        # Add photo if available
        if photo_url := hotel.get("photo_url"):
            msg += f"📸 [View Photo]({photo_url})\n"
        
        msg += "\n"
    
    return msg