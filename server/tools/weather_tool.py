import json
import os
import re
import requests
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("weather_tool")

load_dotenv()


class WeatherTool:
    def __init__(self, mcp_server_url=None):
        self.mcp_server_url = mcp_server_url or "http://weather-mcp:8080"
        self.fallback_url = "http://localhost:8080"

        if "OPENWEATHER_API_KEY" not in os.environ:
            logger.warning("OPENWEATHER_API_KEY not set – weather tool will use simulated data")

        logger.info(f"Initialized WeatherTool with API key: {os.environ.get('OPENWEATHER_API_KEY', '')[:5]}...")

    def _get_coordinates(self, location: str) -> tuple:
        api_key = os.getenv("OPENWEATHER_API_KEY")
        geocode_url = f"https://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={api_key}"
        response = requests.get(geocode_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
        raise ValueError(f"Could not geocode location: {location}")

    def call_weather_api(self, location: str) -> Dict[str, Any]:
        logger.info(f"Getting weather data for {location}")

        try:
            api_key = os.getenv("OPENWEATHER_API_KEY")
            lat, lon = self._get_coordinates(location)
            url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={api_key}&units=metric&exclude=minutely,hourly,alerts"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                current = data.get("current", {})
                weather_report = (
                    f"In {location}, it's currently {current.get('temp', 'N/A')}°C "
                    f"({(current.get('temp', 0) * 9/5) + 32:.1f}°F) with "
                    f"{current.get('weather', [{}])[0].get('description', 'unknown conditions')}. "
                    f"The humidity is around {current.get('humidity', 'N/A')}% with "
                    f"winds at {current.get('wind_speed', 'N/A')} m/s."
                )
                return {
                    "report": weather_report,
                    "data": data,
                    "location": location,
                }
            else:
                logger.warning(f"One Call API 3.0 returned {response.status_code} for {location}")
                return self.get_simulated_weather(location)

        except Exception as e:
            logger.error(f"Error calling OpenWeather API: {str(e)}")
            return self.get_simulated_weather(location)

    def call_mcp(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            request = {
                "jsonrpc": "2.0",
                "method": "invoke",
                "params": {"name": tool_name, "parameters": parameters},
                "id": "1",
            }

            logger.info(f"Sending request to MCP server: {json.dumps(request)[:100]}...")

            try:
                response = self._send_request(self.mcp_server_url, request)
                return response
            except requests.RequestException as e:
                logger.warning(f"Failed to connect to primary MCP server URL: {str(e)}")

                logger.info(f"Trying fallback URL: {self.fallback_url}")
                try:
                    response = self._send_request(self.fallback_url, request)
                    self.mcp_server_url = self.fallback_url
                    return response
                except requests.RequestException as fallback_error:
                    logger.error(f"Failed to connect to fallback MCP server URL: {str(fallback_error)}")
                    if tool_name in ["get_weather", "get_current_weather"]:
                        location = parameters.get("location", "Unknown location")
                        return self.call_weather_api(location)
                    return {"error": f"Failed to connect to MCP server: {str(fallback_error)}"}

        except Exception as e:
            logger.error(f"Error calling MCP: {str(e)}")
            return {"error": f"Error calling MCP: {str(e)}"}

    def _send_request(self, url: str, request: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(request),
            timeout=30,
        )
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"Received response from MCP server: {json.dumps(response_data)[:100]}...")

        if "error" in response_data:
            logger.error(f"Error in MCP response: {response_data['error']}")
            return {"error": response_data["error"]}

        return response_data.get("result", {})

    def get_weather(self, location: str, timezone_offset: float = 0) -> Dict[str, Any]:
        logger.info(f"Getting weather forecast for {location}")
        return self.call_weather_api(location)

    def get_current_weather(self, location: str, timezone_offset: float = 0) -> Dict[str, Any]:
        logger.info(f"Getting current weather for {location}")
        return self.call_weather_api(location)

    def validate_location(self, location: str) -> bool:
        if not location or location.lower() in ["is the", "the", "a", "an", "is", "it"]:
            return False

        try:
            api_key = os.getenv("OPENWEATHER_API_KEY")
            geocode_url = f"https://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={api_key}"
            response = requests.get(geocode_url, timeout=5)
            data = response.json()
            return bool(data)
        except Exception:
            return False

    def extract_location(self, text: str) -> Optional[str]:
        logger.info(f"Extracting location from text: {text}")

        if "current query:" in text.lower():
            try:
                text = text.lower().split("current query:")[-1].strip()
                logger.info(f"Extracted current query for location extraction: {text}")
            except Exception as e:
                logger.error(f"Error extracting current query for location: {str(e)}")

        patterns = [
            r"weather (?:in|at|for) ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"weather (?:forecast|report|conditions) (?:in|at|for) ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"(?:in|at) ([A-Za-z][A-Za-z\s]+?) (?:weather|forecast)",
            r"how is the weather (?:in|at) ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"what'?s the weather (?:in|at|like in) ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"what is the weather (?:in|at|like in) ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"how'?s the weather (?:in|at) ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"tell me (?:about )?(?:the )?weather (?:in|at|for) ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"is it (?:raining|sunny|cold|hot|warm) in ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"(?:plan|planning) (?:a )?(?:trip|vacation|visit) to ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
            r"traveling to ([A-Za-z][A-Za-z\s]+?)(?:\?|\.|\s|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if location.lower() not in ["is the", "the", "a", "an", "is", "it"]:
                    if self.validate_location(location):
                        logger.info(f"Extracted and validated location: {location}")
                        return location
                    else:
                        logger.info(f"Location extraction candidate failed validation: {location}")

        city_match = re.search(r"([A-Za-z]+)\s+city\b", text, re.IGNORECASE)
        if city_match:
            city_name = f"{city_match.group(1)} City"
            if self.validate_location(city_name):
                return city_name
            city_without_suffix = city_match.group(1)
            if self.validate_location(city_without_suffix):
                return city_without_suffix

        at_city_match = re.search(r"weather at ([A-Za-z]+)\b", text, re.IGNORECASE)
        if at_city_match:
            city = at_city_match.group(1)
            if self.validate_location(city):
                return city

        direct_at_match = re.search(r"\bat ([A-Za-z]+)\b", text, re.IGNORECASE)
        if direct_at_match:
            location = direct_at_match.group(1)
            if self.validate_location(location):
                return location

        logger.info("No valid location found in text")
        return None

    def extract_multiple_locations(self, text: str) -> List[str]:
        logger.info(f"Extracting multiple locations from text: {text}")

        if "current query:" in text.lower():
            try:
                text = text.lower().split("current query:")[-1].strip()
                logger.info(f"Extracted current query: {text}")
            except Exception as e:
                logger.error(f"Error extracting current query: {str(e)}")

        primary_location = self.extract_location(text)
        locations = []
        if primary_location:
            locations.append(primary_location)

        multi_location_pattern = r"(?:in|at|for)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+and\s+|\s+&\s+|\s+or\s+|\s*,\s*)"
        matches = list(re.finditer(multi_location_pattern, text, re.IGNORECASE))
        for match in matches:
            location = match.group(1).strip()
            if (
                location.lower() not in ["is the", "the", "a", "an", "is", "it"]
                and location.lower() not in [loc.lower() for loc in locations]
            ):
                if self.validate_location(location):
                    locations.append(location)

        comma_pattern = r"([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*,\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)"
        comma_matches = re.findall(comma_pattern, text)
        for match in comma_matches:
            for potential_city in match:
                if (
                    potential_city
                    and potential_city.lower() not in ["is the", "the", "a", "an", "is", "it"]
                    and potential_city.lower() not in [loc.lower() for loc in locations]
                ):
                    if self.validate_location(potential_city):
                        locations.append(potential_city)

        if not locations:
            city_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
            city_matches = re.findall(city_pattern, text)
            for city in city_matches:
                if city not in ["What", "How", "Is", "Are", "The", "Weather", "A", "An", "In", "At"]:
                    if self.validate_location(city):
                        locations.append(city)

            direct_patterns = [
                r"\bat ([A-Za-z]+)\b",
                r"weather (?:in|at|for) ([A-Za-z]+)\b",
                r"weather at ([A-Za-z]+)\b",
            ]
            for pattern in direct_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if match and match.lower() not in ["is the", "the", "a", "an", "is", "it"]:
                        if self.validate_location(match):
                            if match not in locations:
                                locations.append(match)

        if not locations and "city" in text.lower():
            city_name_match = re.search(r"([A-Za-z]+)\s+city\b", text, re.IGNORECASE)
            if city_name_match:
                city_name = city_name_match.group(1)
                city_with_suffix = f"{city_name} City"
                if self.validate_location(city_with_suffix):
                    locations.append(city_with_suffix)
                elif self.validate_location(city_name):
                    locations.append(city_name)

        logger.info(f"Final validated locations extracted: {locations}")
        return locations

    def get_weather_for_multiple_locations(self, locations: List[str]) -> Dict[str, Dict[str, Any]]:
        weather_results = {}
        for location in locations:
            try:
                weather_data = self.call_weather_api(location)
                weather_results[location] = weather_data
            except Exception as e:
                logger.error(f"Error getting weather for {location}: {str(e)}")
                weather_results[location] = {"error": str(e), "location": location}
        return weather_results

    def format_weather_response(self, weather_results: Dict[str, Dict[str, Any]]) -> str:
        if not weather_results:
            return "I couldn't find weather information for the locations you mentioned."

        if len(weather_results) == 1:
            location = list(weather_results.keys())[0]
            data = weather_results[location]
            if "error" in data:
                return f"I tried to get weather information for {location}, but encountered an error: {data['error']}"
            return f"Here's the current weather for {location}: {data.get('report', 'No data available.')}"

        response_parts = ["Here's the current weather information:"]
        for location, data in weather_results.items():
            if "error" in data:
                response_parts.append(f"• {location}: Sorry, I couldn't retrieve weather data for this location.")
            else:
                report = data.get("report", "No data available")
                response_parts.append(f"• {location}: {report}")
        return "\n\n".join(response_parts)

    def get_simulated_weather(self, location: str) -> Dict[str, Any]:
        logger.info(f"Generating simulated weather for {location}")
        return {
            "report": f"In {location}, it's currently 22°C (72°F) with clear skies. The humidity is around 65% with light winds."
        }


weather_tool = WeatherTool()
