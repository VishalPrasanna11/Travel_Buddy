import os
import json
import re
import logging
import traceback
from typing import Dict, Any

# Import the flight_search tool
from tools.flight_search import flight_search

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('flight_agent')

# ------------------ Flight Agent Main Function ------------------ #
def flight_search_agent(*, input_str: str) -> Dict[str, Any]:
    """
    Main flight search agent function that takes either natural language
    or structured input and returns flight search results by using the flight_search tool
    """
    try:
        print("🔧 flight_search_agent CALLED with:", input_str)
        logger.info(f"🔍 Received input_str: {input_str}")

        # Parse the input string (either directly or preprocess with LLM in the other file)
        if re.search(r"from=.*&to=.*&departureDate=", input_str):
            # Already in structured format - use the flight_search tool directly
            logger.info(f"🔧 Using flight_search tool with input: {input_str}")
            return flight_search(input_str)
        else:
            # For natural language input, we need to call the LLM parser
            # This will be handled in the parent file that imports this module
            return {"error": "Natural language parsing should be handled by the parent module"}

    except Exception as e:
        logger.error(f"❌ Flight Search Agent Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}

# ------------------ Formatting ------------------ #
def format_flight_results(flight_data: Dict[str, Any]) -> str:
    """Format flight search results into a readable string"""
    if "error" in flight_data:
        return f"❌ Flight search error: {flight_data['error']}"
    if "flight" not in flight_data:
        return "⚠️ No flight data received."
    offers = flight_data["flight"].get("data", [])
    if not offers:
        return "No flights found matching your criteria."

    msg = "Here are your flight options:\n\n"
    for i, offer in enumerate(offers[:5], 1):
        price = offer.get("price", {}).get("total", "N/A")
        currency = offer.get("price", {}).get("currency", "USD")
        msg += f"Option {i}: {price} {currency}\n"
        for j, itinerary in enumerate(offer.get("itineraries", [])):
            trip_type = "Outbound" if j == 0 else "Return"
            msg += f"  {trip_type} Journey:\n"
            for segment in itinerary.get("segments", []):
                dep = segment["departure"]["iataCode"]
                arr = segment["arrival"]["iataCode"]
                dep_time = segment["departure"]["at"].replace("T", " ").split("+")[0]
                arr_time = segment["arrival"]["at"].replace("T", " ").split("+")[0]
                flight_code = f"{segment.get('carrierCode', '')} {segment.get('number', '')}"
                msg += f"    {dep} → {arr} ({flight_code})\n    {dep_time} → {arr_time}\n"
        msg += "\n"
    return msg