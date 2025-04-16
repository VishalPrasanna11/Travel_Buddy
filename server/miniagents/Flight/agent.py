import os
import json
import httpx
import re
import logging
import traceback
import time
from typing import Dict, Any
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('flight_agent')

# ------------------ IATA Code Cache ------------------ #
# Simple in-memory cache to reduce API calls
IATA_CODE_CACHE = {}

# ------------------ Rate Limiter ------------------ #
class RateLimiter:
    def __init__(self, max_calls=10, time_frame=1):  # 10 TPS for test environment
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

# ------------------ Amadeus API Helpers ------------------ #
def get_amadeus_access_token() -> str:
    """Get Amadeus API access token with rate limiting"""
    # Check if we can make a call
    wait_seconds = rate_limiter.wait_time()
    if wait_seconds > 0:
        logger.info(f"⏳ Rate limiting - waiting {wait_seconds:.2f}s before token request")
        time.sleep(wait_seconds)
    
    token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("AMADEUS_CLIENT_ID"),
        "client_secret": os.getenv("AMADEUS_CLIENT_SECRET")
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        rate_limiter.record_call()
        response = httpx.post(token_url, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 429:
            rate_limiter.record_429()
            logger.warning("⚠️ Rate limited (429) on token request")
            # Use a fallback token if we've stored one previously
            if hasattr(get_amadeus_access_token, "last_valid_token"):
                logger.info("🔑 Using cached token")
                return get_amadeus_access_token.last_valid_token
            raise Exception("Rate limited and no cached token available")
        
        response.raise_for_status()
        token = response.json()["access_token"]
        # Cache the token
        get_amadeus_access_token.last_valid_token = token
        return token
    except Exception as e:
        logger.error(f"❌ Failed to get Amadeus token: {e}")
        # Return last valid token if we have one
        if hasattr(get_amadeus_access_token, "last_valid_token"):
            logger.info("🔑 Using cached token after error")
            return get_amadeus_access_token.last_valid_token
        raise

def get_iata_code(city: str, token: str) -> str:
    """Get IATA code for a city with caching and rate limiting"""
    # Check cache first
    city_key = city.lower().strip()
    if city_key in IATA_CODE_CACHE:
        logger.info(f"🔍 IATA code for {city} found in cache: {IATA_CODE_CACHE[city_key]}")
        return IATA_CODE_CACHE[city_key]
    
    # Hardcoded common cities to reduce API calls
    common_cities = {
        "new york": "NYC", "los angeles": "LAX", "chicago": "CHI",
        "london": "LON", "paris": "PAR", "tokyo": "TYO",
        "beijing": "BJS", "sydney": "SYD", "san francisco": "SFO",
        "washington": "WAS", "boston": "BOS", "miami": "MIA",
        "seattle": "SEA", "dallas": "DFW", "toronto": "YTO",
        "frankfurt": "FRA", "rome": "ROM", "madrid": "MAD",
        "berlin": "BER", "amsterdam": "AMS", "hong kong": "HKG",
        "bangkok": "BKK", "dubai": "DXB", "singapore": "SIN",
        "mumbai": "BOM", "delhi": "DEL", "shanghai": "SHA",
        "istanbul": "IST", "seoul": "SEL", "moscow": "MOW",
        "rio de janeiro": "RIO", "sao paulo": "SAO", "cairo": "CAI",
        "johannesburg": "JNB"
    }
    
    # Use hardcoded values if available
    if city_key in common_cities:
        iata_code = common_cities[city_key]
        logger.info(f"🔍 Using hardcoded IATA code for {city}: {iata_code}")
        # Cache the result
        IATA_CODE_CACHE[city_key] = iata_code
        return iata_code
    
    # Check if we need to wait due to rate limiting
    wait_seconds = rate_limiter.wait_time()
    if wait_seconds > 0:
        logger.info(f"⏳ Rate limiting - waiting {wait_seconds:.2f}s before IATA code request")
        time.sleep(wait_seconds)
    
    url = "https://test.api.amadeus.com/v1/reference-data/locations"
    params = {"keyword": city, "subType": "CITY"}
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        rate_limiter.record_call()
        res = httpx.get(url, headers=headers, params=params, timeout=30)
        
        if res.status_code == 429:
            rate_limiter.record_429()
            logger.warning(f"⚠️ Rate limited (429) on IATA code request for {city}")
            # Try to use a three-letter abbreviation as fallback
            fallback_code = city[:3].upper()
            logger.info(f"🔍 Using fallback IATA code for {city}: {fallback_code}")
            # We don't cache fallbacks to allow proper resolution next time
            return fallback_code
        
        res.raise_for_status()
        data = res.json()
        iata_code = data["data"][0]["iataCode"] if data.get("data") else city[:3].upper()
        
        # Cache the result
        IATA_CODE_CACHE[city_key] = iata_code
        return iata_code
    except Exception as e:
        logger.error(f"❌ Failed to get IATA code for {city}: {e}")
        # Use first three letters as fallback
        fallback_code = city[:3].upper()
        logger.info(f"🔍 Using fallback IATA code for {city} after error: {fallback_code}")
        return fallback_code

# ------------------ Flight Search API ------------------ #
def search_flights(params: Dict[str, str]) -> Dict[str, Any]:
    """
    Core flight search function that takes parsed parameters
    and returns flight search results or error
    """
    try:
        # Required field guard
        required_keys = ["from", "to", "departureDate"]
        missing = [k for k in required_keys if k not in params or not params[k].strip()]
        if missing:
            return {"error": f"Missing required parameter(s): {', '.join(missing)}"}

        # Get the AMADEUS token
        try:
            token = get_amadeus_access_token()
        except Exception as e:
            logger.error(f"❌ Failed to get access token: {e}")
            return {"error": f"Unable to access flight API: {str(e)}"}

        # Resolve cities to IATA codes
        try:
            origin = get_iata_code(params["from"], token)
            destination = get_iata_code(params["to"], token)
            logger.info(f"🌍 Resolved origin: {origin}, destination: {destination}")
        except Exception as e:
            logger.error(f"❌ Failed to resolve city codes: {e}")
            return {"error": f"Unable to resolve city airport codes: {str(e)}"}

        if not origin or not destination:
            return {"error": f"Could not resolve IATA codes for: {params['from']} → {params['to']}"}

        # Prepare adults count
        adults = int(params.get("adults", "1") or 1)
        
        # Check if return date is specified
        is_one_way = "returnDate" not in params or not params["returnDate"].strip()
        
        # *** FIXED PAYLOAD STRUCTURE *** 
        # This follows the required format for the Amadeus Flight Offers Search API
        body = {
            "currencyCode": "USD",
            "originDestinations": [
                {
                    "id": "1",
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDateTimeRange": {
                        "date": params["departureDate"]
                    }
                }
            ],
            "travelers": [],
            "sources": ["GDS"],
            "searchCriteria": {
                "maxFlightOffers": 5,
                "flightFilters": {
                    "cabinRestrictions": [
                        {
                            "cabin": "ECONOMY",
                            "coverage": "MOST_SEGMENTS",
                            "originDestinationIds": ["1"]
                        }
                    ]
                }
            }
        }
        
        # Add return journey if needed
        if not is_one_way:
            body["originDestinations"].append({
                "id": "2",
                "originLocationCode": destination,
                "destinationLocationCode": origin,
                "departureDateTimeRange": {
                    "date": params["returnDate"]
                }
            })
            # Add return journey to cabin restrictions
            body["searchCriteria"]["flightFilters"]["cabinRestrictions"][0]["originDestinationIds"].append("2")
        
        # Add travelers
        for i in range(1, adults + 1):
            body["travelers"].append({
                "id": str(i),
                "travelerType": "ADULT"
            })

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Check if we need to wait due to rate limiting
        wait_seconds = rate_limiter.wait_time()
        if wait_seconds > 0:
            logger.info(f"⏳ Rate limiting - waiting {wait_seconds:.2f}s before flight search request")
            time.sleep(wait_seconds)

        # Make API request - INCREASED TIMEOUT to prevent errors
        logger.info(f"📡 Amadeus request body: {json.dumps(body)}")
        try:
            rate_limiter.record_call()
            response = httpx.post(
                "https://test.api.amadeus.com/v2/shopping/flight-offers", 
                headers=headers, 
                json=body,
                timeout=60  # Increased timeout to 60 seconds
            )
            
            if response.status_code == 429:
                rate_limiter.record_429()
                logger.warning("⚠️ Rate limited (429) on flight search request")
                return {
                    "error": "We're experiencing high demand. Please try again in a few minutes (rate limit exceeded)."
                }
            
            response.raise_for_status()
            logger.info(f"✅ Flight search success")
            return {"flight": response.json()}
        except httpx.TimeoutException:
            logger.error("❌ Request timed out while searching for flights")
            return {
                "error": "The search timed out. This route may take longer to search, please try again or search for a different route."
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Amadeus API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"Flight search failed: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            logger.error(f"❌ Flight search request error: {e}")
            return {"error": f"Error searching for flights: {str(e)}"}

    except Exception as e:
        logger.error(f"❌ Flight Search Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}

# ------------------ Flight Agent Main Function ------------------ #
def flight_search_agent(*, input_str: str) -> Dict[str, Any]:
    """
    Main flight search agent function that takes either natural language
    or structured input and returns flight search results
    """
    try:
        print("🔧 flight_search_agent CALLED with:", input_str)
        logger.info(f"🔍 Received input_str: {input_str}")

        # Parse the input string (either directly or preprocess with LLM in the other file)
        if re.search(r"from=.*&to=.*&departureDate=", input_str):
            # Already in structured format
            params = dict(param.split("=", 1) for param in input_str.split("&") if "=" in param)
            logger.info(f"🔧 Params parsed: {params}")
            return search_flights(params)
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