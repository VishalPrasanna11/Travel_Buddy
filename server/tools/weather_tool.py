import json
import os
import re
import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from schemas.entities import WeatherAlert, WeatherDay, WeatherForecast, make_id, now_iso

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("weather_tool")

load_dotenv()

MAX_TRIP_DAYS = 14
_GEOCODE_CACHE: Dict[str, tuple] = {}


def _date_range(start: Optional[str], end: Optional[str]) -> List[str]:
    if not start:
        return []
    try:
        d0 = datetime.strptime(start, "%Y-%m-%d").date()
        d1 = datetime.strptime(end, "%Y-%m-%d").date() if end else d0
    except ValueError:
        return []
    if d1 < d0:
        d1 = d0
    out = []
    while d0 <= d1 and len(out) < MAX_TRIP_DAYS:
        out.append(d0.isoformat())
        d0 += timedelta(days=1)
    return out


class WeatherTool:
    def __init__(self, mcp_server_url=None):
        self.mcp_server_url = mcp_server_url or "http://weather-mcp:8080"
        self.fallback_url = "http://localhost:8080"

        if "OPENWEATHER_API_KEY" not in os.environ:
            logger.warning("OPENWEATHER_API_KEY not set – weather tool will use simulated data")

        logger.info(f"Initialized WeatherTool with API key: {os.environ.get('OPENWEATHER_API_KEY', '')[:5]}...")

    def _get_coordinates(self, location: str) -> tuple:
        cached = _GEOCODE_CACHE.get(location.lower())
        if cached:
            return cached
        api_key = os.getenv("OPENWEATHER_API_KEY")
        response = requests.get(
            "https://api.openweathermap.org/geo/1.0/direct",
            params={"q": location, "limit": 1, "appid": api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if data:
            coords = (data[0]["lat"], data[0]["lon"])
            _GEOCODE_CACHE[location.lower()] = coords
            return coords
        raise ValueError(f"Could not geocode location: {location}")

    # ------------------------------------------------------------ forecast
    @staticmethod
    def _local(ts: Optional[int], offset: int) -> Optional[datetime]:
        if ts is None:
            return None
        return datetime.fromtimestamp(ts + offset, tz=timezone.utc).replace(tzinfo=timezone(timedelta(seconds=offset)))

    def _parse_daily(self, data: Dict[str, Any], location: str, units: str, fetched_at: str) -> List[WeatherDay]:
        """Parse One Call 3.0 daily[] (8 days), which used to be ignored."""
        offset = int(data.get("timezone_offset") or 0)
        days: List[WeatherDay] = []
        for d in data.get("daily") or []:
            local = self._local(d.get("dt"), offset)
            if not local:
                continue
            temp = d.get("temp") or {}
            cond = (d.get("weather") or [{}])[0]
            sunrise = self._local(d.get("sunrise"), offset)
            sunset = self._local(d.get("sunset"), offset)
            date = local.date().isoformat()
            days.append(WeatherDay(
                id=make_id("wx", location, date),
                source="openweather",
                fetched_at=fetched_at,
                date=date,
                temp_min=temp.get("min"),
                temp_max=temp.get("max"),
                units=units,
                condition_id=cond.get("id"),
                condition=cond.get("description"),
                icon=cond.get("icon"),
                pop=d.get("pop"),
                precipitation_mm=(d.get("rain") or 0) + (d.get("snow") or 0) or None,
                humidity=d.get("humidity"),
                wind_speed=d.get("wind_speed"),
                uvi=d.get("uvi"),
                sunrise=sunrise.isoformat() if sunrise else None,
                sunset=sunset.isoformat() if sunset else None,
                summary=d.get("summary"),
                kind="forecast",
            ))
        return days

    def _day_summary(self, lat: float, lon: float, date: str, location: str, units: str, fetched_at: str) -> Optional[WeatherDay]:
        """Daily aggregation: forecast or history for one date, up to 1.5 years ahead."""
        try:
            resp = requests.get(
                "https://api.openweathermap.org/data/3.0/onecall/day_summary",
                params={"lat": lat, "lon": lon, "date": date, "units": units, "appid": os.getenv("OPENWEATHER_API_KEY")},
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning(f"day_summary returned {resp.status_code} for {location} {date}")
                return None
            s = resp.json()
        except Exception as e:
            logger.warning(f"day_summary failed for {location} {date}: {e}")
            return None
        temp = s.get("temperature") or {}
        precip = (s.get("precipitation") or {}).get("total")
        cloud = (s.get("cloud_cover") or {}).get("afternoon")
        # day_summary has no condition code; derive a coarse one from the aggregates.
        if precip is not None and precip >= 1:
            cid, desc = 500, "rain likely"
        elif cloud is not None and cloud >= 60:
            cid, desc = 803, "mostly cloudy"
        elif cloud is not None and cloud >= 25:
            cid, desc = 802, "partly cloudy"
        else:
            cid, desc = 800, "mostly clear"
        return WeatherDay(
            id=make_id("wx", location, date),
            source="openweather",
            fetched_at=fetched_at,
            date=date,
            temp_min=temp.get("min"),
            temp_max=temp.get("max"),
            units=units,
            condition_id=cid,
            condition=desc,
            precipitation_mm=precip,
            humidity=(s.get("humidity") or {}).get("afternoon"),
            wind_speed=((s.get("wind") or {}).get("max") or {}).get("speed"),
            kind="day_summary",
        )

    def get_forecast(
        self,
        location: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        units: str = "metric",
    ) -> WeatherForecast:
        """Typed forecast for a destination, keyed to the trip dates when given.

        Days inside One Call's 8-day window come from daily[]; later trip days
        come from day_summary. Without an API key (or on failure) this returns
        an honest, empty forecast with is_simulated=True — never invented numbers.
        """
        units = units if units in ("metric", "imperial") else "metric"
        fetched_at = now_iso()
        if not os.getenv("OPENWEATHER_API_KEY"):
            return self._simulated_forecast(location, units, "provider_not_configured")
        try:
            lat, lon = self._get_coordinates(location)
            resp = requests.get(
                "https://api.openweathermap.org/data/3.0/onecall",
                params={"lat": lat, "lon": lon, "appid": os.getenv("OPENWEATHER_API_KEY"), "units": units, "exclude": "minutely,hourly"},
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning(f"One Call API 3.0 returned {resp.status_code} for {location}")
                return self._simulated_forecast(location, units, "provider_unavailable")
            data = resp.json()
        except Exception as e:
            logger.error(f"Error calling OpenWeather API: {e}")
            return self._simulated_forecast(location, units, "provider_unavailable")

        days = self._parse_daily(data, location, units, fetched_at)
        wanted = _date_range(start_date, end_date)
        if wanted:
            by_date = {d.date: d for d in days}
            picked: List[WeatherDay] = []
            for date in wanted[:MAX_TRIP_DAYS]:
                if date in by_date:
                    picked.append(by_date[date])
                else:
                    summary = self._day_summary(lat, lon, date, location, units, fetched_at)
                    if summary:
                        picked.append(summary)
            days = picked or days

        alerts = [
            WeatherAlert(
                sender=a.get("sender_name"),
                event=a.get("event", "Weather alert"),
                start=datetime.fromtimestamp(a["start"], tz=timezone.utc).isoformat() if a.get("start") else None,
                end=datetime.fromtimestamp(a["end"], tz=timezone.utc).isoformat() if a.get("end") else None,
                description=a.get("description"),
            )
            for a in data.get("alerts") or []
        ]
        current = data.get("current") or {}
        deg = "°C" if units == "metric" else "°F"
        cond = (current.get("weather") or [{}])[0]
        report = (
            f"In {location}, it's currently {current.get('temp', 'N/A')}{deg} with "
            f"{cond.get('description', 'unknown conditions')}. Humidity {current.get('humidity', 'N/A')}%, "
            f"wind {current.get('wind_speed', 'N/A')} {'m/s' if units == 'metric' else 'mph'}."
        )
        if days:
            report += " Forecast: " + "; ".join(
                f"{d.date} {d.condition or ''} {round(d.temp_min) if d.temp_min is not None else '?'}–"
                f"{round(d.temp_max) if d.temp_max is not None else '?'}{deg}"
                + (f", {round((d.pop or 0) * 100)}% chance of rain" if d.pop is not None else "")
                for d in days
            )
        return WeatherForecast(
            id=make_id("wxf", location, start_date, end_date),
            source="openweather",
            fetched_at=fetched_at,
            location=location,
            lat=lat,
            lng=lon,
            timezone=data.get("timezone"),
            units=units,
            is_simulated=False,
            current={
                "temp": current.get("temp"),
                "feels_like": current.get("feels_like"),
                "condition_id": cond.get("id"),
                "condition": cond.get("description"),
                "icon": cond.get("icon"),
                "humidity": current.get("humidity"),
                "wind_speed": current.get("wind_speed"),
                "uvi": current.get("uvi"),
            },
            days=days,
            alerts=alerts,
            report=report,
        )

    def _simulated_forecast(self, location: str, units: str, reason: str) -> WeatherForecast:
        logger.info(f"Weather unavailable for {location} ({reason}); returning flagged estimate")
        return WeatherForecast(
            id=make_id("wxf", location, "simulated"),
            source="simulated",
            is_estimate=True,
            is_simulated=True,
            location=location,
            units=units,
            days=[],
            report=f"Live weather isn't available for {location} right now, so no forecast is included.",
            reason=reason,
        )

    def call_weather_api(self, location: str, start_date: Optional[str] = None, end_date: Optional[str] = None, units: str = "metric") -> Dict[str, Any]:
        """Legacy shape ({report, location, ...}) plus the typed forecast."""
        logger.info(f"Getting weather data for {location}")
        forecast = self.get_forecast(location, start_date, end_date, units)
        return {
            "report": forecast.report,
            "location": location,
            "is_simulated": forecast.is_simulated,
            "source": forecast.source,
            "forecast": forecast.model_dump(mode="json", exclude_none=True),
        }

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
        forecast = self._simulated_forecast(location, "metric", "provider_unavailable")
        return {"report": forecast.report, "location": location, "is_simulated": True, "source": "simulated",
                "forecast": forecast.model_dump(mode="json", exclude_none=True)}


weather_tool = WeatherTool()
