from langchain_core.tools import tool
from typing import Dict, Any
import snowflake.connector
import os
import logging

logger = logging.getLogger("flight_search")


def _search_flights_snowflake(params: Dict[str, str]) -> Dict[str, Any]:
    origin = params.get("origin", "").upper()
    destination = params.get("destination", "").upper()
    departure_date = params.get("departure_date", "")

    if not origin or not destination or not departure_date:
        return {"error": "Missing required parameters: origin, destination, departure_date"}

    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
        )

        cur = conn.cursor()
        query = """
            SELECT
                FLIGHT_ID, PRICE_RAW, PRICE_FORMATTED,
                ORIGIN_ID, DESTINATION_ID,
                DEPARTURE_TIME, ARRIVAL_TIME,
                AIRLINE_NAME, FLIGHT_NUMBER
            FROM FINAL_PROJECT.PUBLIC.DAILY_FLIGHTS
            WHERE UPPER(ORIGIN_ID) = %s
            AND UPPER(DESTINATION_ID) = %s
            AND DATE(DEPARTURE_TIME) = %s
            ORDER BY PRICE_RAW ASC
            LIMIT 10
        """
        cur.execute(query, (origin, destination, departure_date))
        rows = cur.fetchall()
        columns = [desc[0].lower() for desc in cur.description]

        flights = []
        for row in rows:
            flight = dict(zip(columns, row))
            departure = flight["departure_time"]
            arrival = flight["arrival_time"]
            delta = arrival - departure
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes = remainder // 60
            flight["duration"] = f"{hours}h {minutes}m"
            flight["departure_time"] = str(departure)
            flight["arrival_time"] = str(arrival)
            flights.append(flight)

        cur.close()
        conn.close()

        if not flights:
            return {
                "flights": [],
                "message": f"No flights found from {origin} to {destination} on {departure_date}",
            }

        return {
            "flights": flights,
            "count": len(flights),
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
        }

    except Exception as e:
        logger.error(f"Flight search error: {str(e)}")
        return {"error": f"Flight search failed: {str(e)}"}


@tool
def flight_search(input_str: str) -> Dict[str, Any]:
    """
    Finds flights based on user query using Snowflake flight data.
    Input should be a URL-style string, e.g., 'origin=NYC&destination=Paris&departure_date=2025-05-01'.
    """
    params = dict(param.split("=", 1) for param in input_str.split("&") if "=" in param)
    return _search_flights_snowflake(params)
