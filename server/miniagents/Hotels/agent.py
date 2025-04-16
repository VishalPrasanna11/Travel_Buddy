import os
import json
import httpx
import re
import logging
import traceback
import time
from typing import Dict, Any, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('hotel_agent')

# ------------------ City Code Cache ------------------ #
# Simple in-memory cache to reduce API calls
CITY_CODE_CACHE = {}

# ------------------ Rate Limiter ------------------ #
class RateLimiter:
    """Rate limiter to prevent hitting API limits"""
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

def get_city_code(city: str, token: str) -> str:
    """Get city code for a city with caching and rate limiting"""
    # Check cache first
    city_key = city.lower().strip()
    if city_key in CITY_CODE_CACHE:
        logger.info(f"🔍 City code for {city} found in cache: {CITY_CODE_CACHE[city_key]}")
        return CITY_CODE_CACHE[city_key]
    
    # Hardcoded common cities to reduce API calls
    common_cities = {
        "new york": "NYC",
        "los angeles": "LAX", 
        "chicago": "CHI",
        "london": "LON",
        "paris": "PAR",
        "tokyo": "TYO",
        "beijing": "BJS",
        "sydney": "SYD",
        "san francisco": "SFO",
        "washington": "WAS",
        "boston": "BOS",
        "miami": "MIA",
        "seattle": "SEA",
        "dallas": "DFW",
        "toronto": "YTO",
        "frankfurt": "FRA",
        "rome": "ROM",
        "madrid": "MAD",
        "berlin": "BER",
        "amsterdam": "AMS",
        "hong kong": "HKG",
        "bangkok": "BKK",
        "dubai": "DXB",
        "singapore": "SIN",
        "mumbai": "BOM",
        "delhi": "DEL",
        "shanghai": "SHA",
        "istanbul": "IST",
        "seoul": "SEL",
        "moscow": "MOW",
        "rio de janeiro": "RIO",
        "sao paulo": "SAO",
        "cairo": "CAI",
        "johannesburg": "JNB"
    }
    
    # Use hardcoded values if available
    if city_key in common_cities:
        city_code = common_cities[city_key]
        logger.info(f"🔍 Using hardcoded city code for {city}: {city_code}")
        # Cache the result
        CITY_CODE_CACHE[city_key] = city_code
        return city_code
    
    # Check if we need to wait due to rate limiting
    wait_seconds = rate_limiter.wait_time()
    if wait_seconds > 0:
        logger.info(f"⏳ Rate limiting - waiting {wait_seconds:.2f}s before city code request")
        time.sleep(wait_seconds)
    
    url = "https://test.api.amadeus.com/v1/reference-data/locations"
    params = {"keyword": city, "subType": "CITY"}
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        rate_limiter.record_call()
        res = httpx.get(url, headers=headers, params=params, timeout=30)
        
        if res.status_code == 429:
            rate_limiter.record_429()
            logger.warning(f"⚠️ Rate limited (429) on city code request for {city}")
            # Try to use a three-letter abbreviation as fallback
            fallback_code = city[:3].upper()
            logger.info(f"🔍 Using fallback city code for {city}: {fallback_code}")
            return fallback_code
        
        res.raise_for_status()
        data = res.json()
        city_code = data["data"][0]["iataCode"] if data.get("data") else city[:3].upper()
        
        # Cache the result
        CITY_CODE_CACHE[city_key] = city_code
        return city_code
    except Exception as e:
        logger.error(f"❌ Failed to get city code for {city}: {e}")
        # Use first three letters as fallback
        fallback_code = city[:3].upper()
        logger.info(f"🔍 Using fallback city code for {city} after error: {fallback_code}")
        return fallback_code

# ------------------ Hotel Search API ------------------ #
def search_hotels(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core hotel search function that takes parsed parameters
    and returns hotel search results or error
    """
    try:
        # Required field guard
        required_keys = ["city", "checkInDate", "checkOutDate", "adults"]
        missing = [k for k in required_keys if k not in params or not params[k]]
        if missing:
            return {"error": f"Missing required parameter(s): {', '.join(missing)}"}

        # Fix date format and validate dates
        import datetime
        current_year = datetime.datetime.now().year
        
        # Function to fix and validate dates
        def fix_date(date_str, default_year=current_year):
            try:
                # Parse the date
                if "-" in date_str:
                    year, month, day = map(int, date_str.split("-"))
                else:
                    # Try other formats
                    try:
                        date_obj = datetime.datetime.strptime(date_str, "%m/%d/%Y")
                        return date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        try:
                            date_obj = datetime.datetime.strptime(date_str, "%m/%d/%y")
                            return date_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            # Default format handling
                            parts = re.split(r'[/.-]', date_str)
                            if len(parts) >= 3:
                                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                            else:
                                raise ValueError(f"Could not parse date: {date_str}")
                
                # Check if year is too old (probably a 2-digit year or wrong)
                if year < 100:  # 2-digit year
                    year += 2000
                
                # Ensure year is current or future
                if year < current_year:
                    logger.warning(f"⚠️ Date {date_str} appears to be in the past. Updating to {current_year}.")
                    year = current_year
                
                # Create a valid date string
                return f"{year:04d}-{month:02d}-{day:02d}"
            except Exception as e:
                logger.error(f"❌ Date parsing error for {date_str}: {e}")
                # Return today's date as fallback
                today = datetime.datetime.now()
                return today.strftime("%Y-%m-%d")
        
        # Fix check-in date
        params["checkInDate"] = fix_date(params["checkInDate"])
        logger.info(f"📅 Validated checkInDate: {params['checkInDate']}")
        
        # Fix check-out date
        params["checkOutDate"] = fix_date(params["checkOutDate"])
        logger.info(f"📅 Validated checkOutDate: {params['checkOutDate']}")
        
        # Ensure check-out is after check-in
        checkin_date = datetime.datetime.strptime(params["checkInDate"], "%Y-%m-%d")
        checkout_date = datetime.datetime.strptime(params["checkOutDate"], "%Y-%m-%d")
        
        if checkout_date <= checkin_date:
            logger.warning("⚠️ Check-out date is before or same as check-in date. Adding one day.")
            checkout_date = checkin_date + datetime.timedelta(days=1)
            params["checkOutDate"] = checkout_date.strftime("%Y-%m-%d")
            logger.info(f"📅 Adjusted checkOutDate: {params['checkOutDate']}")

        # Get the AMADEUS token
        try:
            token = get_amadeus_access_token()
        except Exception as e:
            logger.error(f"❌ Failed to get access token: {e}")
            return {"error": f"Unable to access hotel API: {str(e)}"}

        # Resolve city to city code
        try:
            city_code = get_city_code(params["city"], token)
            logger.info(f"🌍 Resolved city: {city_code}")
        except Exception as e:
            logger.error(f"❌ Failed to resolve city code: {e}")
            return {"error": f"Unable to resolve city code: {str(e)}"}

        if not city_code:
            return {"error": f"Could not resolve city code for: {params['city']}"}

        # Ensure adults is an integer
        try:
            if isinstance(params["adults"], str):
                params["adults"] = int(params["adults"])
        except ValueError:
            logger.warning(f"⚠️ Could not convert adults to integer: {params['adults']}. Using default.")
            params["adults"] = 1

        # Looking at the API documentation, lets try the Hotel List endpoint first
        # This is the first step to finding hotels - getting a list of available hotels in the city
        hotel_list_url = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"

        # Prepare API request parameters - keep it minimal to avoid format issues
        api_params = {
            "cityCode": city_code
        }

        # Check if we need to wait due to rate limiting
        wait_seconds = rate_limiter.wait_time()
        if wait_seconds > 0:
            logger.info(f"⏳ Rate limiting - waiting {wait_seconds:.2f}s before hotel search request")
            time.sleep(wait_seconds)

        # Send the request with minimal parameters
        logger.info(f"📡 Amadeus hotel list parameters: {api_params}")
        
        try:
            rate_limiter.record_call()
            response = httpx.get(
                hotel_list_url, 
                headers={"Authorization": f"Bearer {token}"},
                params=api_params,
                timeout=60  # 60 second timeout
            )
            
            if response.status_code == 429:
                rate_limiter.record_429()
                logger.warning("⚠️ Rate limited (429) on hotel list request")
                return {
                    "error": "We're experiencing high demand. Please try again in a few minutes (rate limit exceeded)."
                }
            
            response.raise_for_status()
            logger.info(f"✅ Hotel list search success")
            
            # Parse the actual API response
            hotel_data = response.json()
            
            # Add the check-in/check-out dates and adults to the response data
            # These aren't used in the API call but are useful for displaying to the user
            hotel_data["request"] = {
                "checkInDate": params["checkInDate"],
                "checkOutDate": params["checkOutDate"],
                "adults": params["adults"]
            }
            
            return {"hotels": hotel_data}
            
        except httpx.TimeoutException:
            logger.error("❌ Request timed out while searching for hotels")
            return {
                "error": "The search timed out. Please try again or search for a different location."
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Amadeus API error: {e.response.status_code} - {e.response.text}")
            
            # Provide more specific error info for common issues
            if e.response.status_code == 400:
                try:
                    error_json = e.response.json()
                    if "errors" in error_json:
                        error_details = error_json["errors"][0]
                        if error_details.get("code") == 367:  # INVALID FORMAT
                            # Try with a simpler request as a fallback - just the cityCode
                            logger.info("🔄 Trying simplified request with only cityCode parameter")
                            return {
                                "error": f"The Amadeus API reported an invalid format error. Please check the documentation for the correct format. Error details: {error_details.get('title', 'Unknown')}"
                            }
                except Exception:
                    pass
                
            return {"error": f"Hotel search failed: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            logger.error(f"❌ Hotel search request error: {e}")
            return {"error": f"Error searching for hotels: {str(e)}"}

    except Exception as e:
        logger.error(f"❌ Hotel Search Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}
# ------------------ Hotel Agent Main Function ------------------ #
def hotel_search_agent(*, input_str: str) -> Dict[str, Any]:
    """
    Main hotel search agent function that takes either natural language
    or structured input and returns hotel search results
    """
    try:
        print("🔧 hotel_search_agent CALLED with:", input_str)
        logger.info(f"🔍 Received input_str: {input_str}")

        # Parse the input string (either directly or preprocess with LLM in the other file)
        if re.search(r"city=.*&checkInDate=.*&checkOutDate=.*&adults=", input_str):
            # Already in structured format
            params = dict(param.split("=", 1) for param in input_str.split("&") if "=" in param)
            logger.info(f"🔧 Params parsed: {params}")
            return search_hotels(params)
        else:
            # For natural language input, we need to call the LLM parser
            # This will be handled in the parent file that imports this module
            return {"error": "Natural language parsing should be handled by the parent module"}

    except Exception as e:
        logger.error(f"❌ Hotel Search Agent Exception: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Internal error: {str(e)}"}

# ------------------ Formatting ------------------ #
def format_hotel_results(hotel_data: Dict[str, Any]) -> str:
    """Format hotel search results into a readable string"""
    if "error" in hotel_data:
        return f"❌ Hotel search error: {hotel_data['error']}"
    
    if "hotels" not in hotel_data:
        return "⚠️ No hotel data received."
    
    hotels = hotel_data["hotels"].get("data", [])
    if not hotels:
        return "No hotels found matching your criteria."

    msg = f"Here are some hotel options:\n\n"
    
    for i, hotel in enumerate(hotels[:10], 1):  # Show top 10 hotels
        name = hotel.get("name", "Unknown Hotel")
        hotel_id = hotel.get("hotelId", "Unknown ID")
        chain_code = hotel.get("chainCode", "")
        chain_name = get_chain_name(chain_code)
        
        address = "Unknown Location"
        if "address" in hotel:
            address_parts = []
            if hotel["address"].get("lines"):
                address_parts.extend(hotel["address"]["lines"])
            if hotel["address"].get("cityName"):
                address_parts.append(hotel["address"]["cityName"])
            if hotel["address"].get("postalCode"):
                address_parts.append(hotel["address"]["postalCode"])
            if hotel["address"].get("countryCode"):
                address_parts.append(hotel["address"]["countryCode"])
            address = ", ".join(address_parts)
        
        # Try to get rating
        rating = ""
        if "rating" in hotel:
            rating = f"{hotel['rating']} Stars"
        
        # Try to get amenities if available
        amenities = []
        if "amenities" in hotel:
            amenities = [amenity.replace("_", " ").title() for amenity in hotel["amenities"][:5]]
        
        # Build the hotel info
        msg += f"**{i}. {name}**"
        if chain_name:
            msg += f" - {chain_name}"
        msg += "\n"
        
        if rating:
            msg += f"⭐ Rating: {rating}\n"
        
        msg += f"📍 Address: {address}\n"
        
        if amenities:
            msg += f"🛎️ Amenities: {', '.join(amenities)}\n"
        
        msg += f"🆔 Hotel ID: {hotel_id}\n\n"
    
    return msg

def get_chain_name(chain_code: str) -> str:
    """Convert hotel chain code to chain name"""
    chain_codes = {
        "AC": "AccorHotels",
        "BW": "Best Western",
        "CH": "Choice Hotels",
        "HI": "Holiday Inn",
        "HY": "Hyatt",
        "IH": "InterContinental Hotels",
        "MC": "Marriott",
        "HL": "Hilton",
        "RD": "Radisson",
        "WY": "Wyndham",
        "SH": "Sheraton",
        "FO": "Four Seasons",
        "FS": "Fairmont",
        "RC": "Ritz-Carlton",
        "WI": "Westin",
        "SW": "Swissotel",
        "LQ": "La Quinta",
        "HH": "Holiday Inn Hotels"
    }
    return chain_codes.get(chain_code, "")