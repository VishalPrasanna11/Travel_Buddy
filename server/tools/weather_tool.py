import subprocess
import json
import os
import re
import sys
import time
import logging
from typing import Dict, Any, Optional
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


