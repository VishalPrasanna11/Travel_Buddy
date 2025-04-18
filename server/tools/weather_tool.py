import subprocess
import json
import os
import re
import sys
import time
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("weather_tool")

# Load environment variables from .env file
load_dotenv()

class WeatherTool:
    def __init__(self, mcp_server_path=None):
        # Path to the MCP server
        self.mcp_server_path = mcp_server_path or "/Users/lohith/Documents/VPProjects/fork-Travel_Buddy/Travel_Buddy/weekly-weather-mcp-master/simplified_mcp_server.py"
        self.process = None
        
    def start_server(self):
        """Start the MCP server if not already running"""
        if self.process is None or self.process.poll() is not None:
            # Add necessary environment variables
            env = os.environ.copy()
            
            # Check for OpenWeather API key
            if "OPENWEATHER_API_KEY" not in env:
                logger.error("OPENWEATHER_API_KEY environment variable not set")
                raise ValueError("OPENWEATHER_API_KEY environment variable not set")
            
            # Check for OpenAI API key (needed by the weather agent)
            if "OPENAI_API_KEY" not in env:
                logger.error("OPENAI_API_KEY environment variable not set")
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            # Log important information
            logger.info(f"Starting MCP server from path: {self.mcp_server_path}")
            logger.info(f"Using OpenWeather API key: {env['OPENWEATHER_API_KEY'][:5]}...")
            
            try:
                self.process = subprocess.Popen(
                    [sys.executable, self.mcp_server_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    env=env
                )
                
                # Give the server time to start
                time.sleep(2)
                logger.info("MCP server started successfully")
                
            except Exception as e:
                logger.error(f"Failed to start MCP server: {str(e)}")
                raise
    
    def stop_server(self):
        """Stop the MCP server"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                logger.info("MCP server terminated")
            except Exception as e:
                logger.error(f"Error terminating MCP server: {str(e)}")
            finally:
                self.process = None
    
    def call_mcp(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool with parameters"""
        try:
            self.start_server()
            
            # Create JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "method": "invoke",
                "params": {
                    "name": tool_name,
                    "parameters": parameters
                },
                "id": "1"
            }
            
            logger.info(f"Sending request to MCP server: {json.dumps(request)[:100]}...")
            
            # Send request to server
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            
            # Read response with timeout
            start_time = time.time()
            response_line = ""
            
            while time.time() - start_time < 30:  # 30 second timeout
                if self.process.stdout.readable():
                    response_line = self.process.stdout.readline().strip()
                    if response_line:
                        break
                time.sleep(0.1)
            
            if not response_line:
                logger.error("Timeout waiting for MCP server response")
                return {"error": "Timeout waiting for MCP server response"}
            
            logger.info(f"Received response from MCP server: {response_line[:100]}...")
            
            try:
                response = json.loads(response_line)
                
                if "error" in response:
                    logger.error(f"Error in MCP response: {response['error']}")
                    return {"error": response["error"]}
                
                return response.get("result", {})
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP response: {str(e)}")
                return {"error": f"Failed to parse MCP response: {str(e)}"}
                
        except Exception as e:
            logger.error(f"Error calling MCP: {str(e)}")
            return {"error": f"Error calling MCP: {str(e)}"}
    
    def get_weather(self, location: str, timezone_offset: float = 0) -> Dict[str, Any]:
        """Get comprehensive weather forecast for a location"""
        logger.info(f"Getting weather forecast for {location}")
        return self.call_mcp("get_weather", {
            "location": location,
            "api_key": os.getenv("OPENWEATHER_API_KEY", ""),
            "timezone_offset": timezone_offset
        })
    
    def get_current_weather(self, location: str, timezone_offset: float = 0) -> Dict[str, Any]:
        """Get current weather for a location"""
        logger.info(f"Getting current weather for {location}")
        return self.call_mcp("get_current_weather", {
            "location": location,
            "api_key": os.getenv("OPENWEATHER_API_KEY", ""),
            "timezone_offset": timezone_offset
        })
        
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location from user query"""
        logger.info(f"Extracting location from text: {text}")
        
        # If the input includes chat history, extract only the current query
        if "current query:" in text.lower():
            try:
                text = text.lower().split("current query:")[-1].strip()
                logger.info(f"Extracted current query for location extraction: {text}")
            except Exception as e:
                logger.error(f"Error extracting current query for location: {str(e)}")
        
        # Add more patterns to catch different phrasings
        patterns = [
            r"weather (?:in|at|for) ([A-Za-z\s]+)(?:,|\.|$)",
            r"weather (?:forecast|report|conditions) (?:in|at|for) ([A-Za-z\s]+)(?:,|\.|$)",
            r"(?:in|at) ([A-Za-z\s]+) (?:weather|forecast)",
            r"how is the weather (?:in|at) ([A-Za-z\s]+)(?:,|\.|$)",
            r"what's the weather (?:in|at|like in) ([A-Za-z\s]+)(?:,|\.|$)",
            r"what is the weather (?:in|at|like in) ([A-Za-z\s]+)(?:,|\.|$)",
            r"how's the weather (?:in|at) ([A-Za-z\s]+)(?:,|\.|$)",
            r"tell me (?:about )?(?:the )?weather (?:in|at|for) ([A-Za-z\s]+)(?:,|\.|$)",
            r"is it (?:raining|sunny|cold|hot|warm) in ([A-Za-z\s]+)(?:,|\.|$)",
            r"(?:plan|planning) (?:a )?(?:trip|vacation|visit) to ([A-Za-z\s]+)(?:,|\.|$)",
            r"traveling to ([A-Za-z\s]+)(?:,|\.|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                logger.info(f"Extracted location: {location}")
                return location
        
        # If none of the patterns match, check for city names
        common_cities = ["New York", "London", "Paris", "Tokyo", "Berlin", "Rome", "Madrid", "Beijing", "Sydney", "Cairo", 
                        "Boston", "Chicago", "Los Angeles", "San Francisco", "Seattle", "Miami", "Toronto", "Vancouver",
                        "Mumbai", "Delhi", "Bangkok", "Singapore", "Seoul", "Shanghai", "Mexico City", "Rio de Janeiro",
                        "Cape Town", "Dubai", "Istanbul", "Moscow", "Amsterdam", "Barcelona", "Vienna", "Prague"]
        
        for city in common_cities:
            if city.lower() in text.lower():
                logger.info(f"Found city name in text: {city}")
                return city
        
        logger.info("No location found in text")
        return None
        
    def extract_multiple_locations(self, text: str) -> List[str]:
        """Extract multiple locations from user query"""
        logger.info(f"Extracting multiple locations from text: {text}")
        
        # If the input includes chat history, extract only the current query
        if "current query:" in text.lower():
            try:
                text = text.lower().split("current query:")[-1].strip()
                logger.info(f"Extracted current query: {text}")
            except Exception as e:
                logger.error(f"Error extracting current query: {str(e)}")
        
        locations = []
        
        # Pattern for locations with connecting words ("and", "or", etc.)
        location_pattern = r"(?:in|at|for)\s+([A-Za-z\s]+?)(?:(?:,|\s+and|\s+&|\s+or|\s+as well as)|\s+and\s+([A-Za-z\s]+?)(?:$|,)|\s+or\s+([A-Za-z\s]+?)(?:$|,))"
        
        # Extract locations from patterns
        matches = list(re.finditer(location_pattern, text, re.IGNORECASE))
        for match in matches:
            # Get the first match group
            location = match.group(1).strip() if match.group(1) else None
            if location and location.lower() not in [loc.lower() for loc in locations]:
                locations.append(location)
            
            # Check for additional locations in other groups
            for i in range(2, 4):  # Check groups 2 and 3 if they exist
                if match.group(i):
                    location = match.group(i).strip()
                    if location and location.lower() not in [loc.lower() for loc in locations]:
                        locations.append(location)
        
        # Also try the single location extractor for the first location
        single_location = self.extract_location(text)
        if single_location and single_location.lower() not in [loc.lower() for loc in locations]:
            locations.append(single_location)
        
        # If we found multiple locations, great!
        if len(locations) > 1:
            logger.info(f"Multiple locations extracted: {locations}")
            return locations
        
        # If we only found one or no locations using the complex pattern,
        # try looking for common city names
        if len(locations) <= 1:
            common_cities = ["New York", "London", "Paris", "Tokyo", "Berlin", "Rome", "Madrid", "Beijing", "Sydney", 
                            "Boston", "Chicago", "Los Angeles", "San Francisco", "Seattle", "Miami", "Toronto", 
                            "Mumbai", "Delhi", "Bangkok", "Singapore", "Seoul", "Shanghai", "Mexico City"]
            
            # Simple pattern to match cities separated by connectors
            cities_pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(?:\s*(?:,|and|&|or)\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
            
            city_matches = re.finditer(cities_pattern, text)
            for match in city_matches:
                for i in range(1, 3):  # Check groups 1 and 2
                    if match.group(i):
                        potential_city = match.group(i).strip()
                        if potential_city in common_cities and potential_city.lower() not in [loc.lower() for loc in locations]:
                            locations.append(potential_city)
            
            # Direct city name extraction
            for city in common_cities:
                if city.lower() in text.lower() and city.lower() not in [loc.lower() for loc in locations]:
                    locations.append(city)
        
        logger.info(f"Final locations extracted: {locations}")
        return locations

    def get_weather_for_multiple_locations(self, locations: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get weather data for multiple locations"""
        weather_results = {}
        
        for location in locations:
            try:
                weather_data = self.get_current_weather(location)
                weather_results[location] = weather_data
            except Exception as e:
                logger.error(f"Error getting weather for {location}: {str(e)}")
                weather_results[location] = {
                    "error": str(e),
                    "location": location
                }
        
        return weather_results

    def format_weather_response(self, weather_results: Dict[str, Dict[str, Any]]) -> str:
        """Format weather data from multiple locations into a readable response"""
        if not weather_results:
            return "I couldn't find weather information for the locations you mentioned."
        
        # Single location case
        if len(weather_results) == 1:
            location = list(weather_results.keys())[0]
            data = weather_results[location]
            
            if "error" in data:
                return f"I tried to get weather information for {location}, but encountered an error: {data['error']}"
            
            return f"Here's the current weather for {location}: {data.get('report', 'No data available.')}"
        
        # Multiple locations
        response_parts = ["Here's the current weather information:"]
        
        for location, data in weather_results.items():
            if "error" in data:
                response_parts.append(f"• {location}: Sorry, I couldn't retrieve weather data for this location.")
            else:
                report = data.get("report", "No data available")
                response_parts.append(f"• {location}: {report}")
        
        return "\n\n".join(response_parts)

    def get_simulated_weather(self, location: str) -> Dict[str, Any]:
        """Provide simulated weather data when MCP server fails"""
        logger.info(f"Generating simulated weather for {location}")
        return {
            "report": f"In {location}, it's currently 22°C with clear skies. The humidity is around 65% with light winds. (This is simulated data as the weather service is unavailable.)"
        }

# Singleton instance
weather_tool = WeatherTool()

# For testing
if __name__ == "__main__":
    try:
        logger.info("Starting weather tool test")
        result = weather_tool.get_current_weather("London")
        logger.info(f"Test result: {result}")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
    finally:
        weather_tool.stop_server()
        logger.info("Test complete")
