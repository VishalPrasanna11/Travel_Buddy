# from fastapi import APIRouter, Depends, HTTPException -testflight working
# import snowflake.connector
# import os
# from typing import List
# from pydantic import BaseModel
# from datetime import datetime

# router = APIRouter()

# # Pydantic model for flight response
# class FlightResponse(BaseModel):
#     flight_id: str
#     price_raw: float
#     price_formatted: str
#     origin_id: str
#     destination_id: str
#     departure_time: datetime
#     arrival_time: datetime
#     airline_name: str
#     flight_number: str
#     load_date: datetime

# # Dependency to get Snowflake connection
# def get_snowflake_conn():
#     conn = snowflake.connector.connect(
#         user=os.getenv("SNOWFLAKE_USER"),
#         password=os.getenv("SNOWFLAKE_PASSWORD"),
#         account=os.getenv("SNOWFLAKE_ACCOUNT"),
#         warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
#         database=os.getenv("SNOWFLAKE_DATABASE"),
#         schema=os.getenv("SNOWFLAKE_SCHEMA")
#     )
#     try:
#         yield conn
#     finally:
#         conn.close()

# # Test endpoint to fetch flights
# @router.get("/test", response_model=List[FlightResponse])
# async def test_fetch_flights(conn: snowflake.connector.SnowflakeConnection = Depends(get_snowflake_conn)):
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM FINAL_PROJECT.PUBLIC.DAILY_FLIGHTS LIMIT 10")
#         rows = cur.fetchall()
#         columns = [desc[0].lower() for desc in cur.description]
#         flights = [dict(zip(columns, row)) for row in rows]
#         return flights
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching flights: {str(e)}")
#     finally:
#         cur.close()


# from fastapi import APIRouter, Depends, HTTPException
# import snowflake.connector
# import os
# from typing import List
# from pydantic import BaseModel
# from datetime import datetime, date
# from fastapi import Query

# router = APIRouter()

# # Pydantic model for flight response
# class FlightResponse(BaseModel):
#     flight_id: str
#     price_raw: float
#     price_formatted: str
#     origin_id: str
#     destination_id: str
#     departure_time: datetime
#     arrival_time: datetime
#     airline_name: str
#     flight_number: str
#     load_date: datetime

# # Pydantic model for average price response
# class AvgPriceResponse(BaseModel):
#     date: date
#     avg_price: float

# # Dependency to get Snowflake connection
# def get_snowflake_conn():
#     conn = snowflake.connector.connect(
#         user=os.getenv("SNOWFLAKE_USER"),
#         password=os.getenv("SNOWFLAKE_PASSWORD"),
#         account=os.getenv("SNOWFLAKE_ACCOUNT"),
#         warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
#         database=os.getenv("SNOWFLAKE_DATABASE"),
#         schema=os.getenv("SNOWFLAKE_SCHEMA")
#     )
#     try:
#         yield conn
#     finally:
#         conn.close()

# # Test endpoint to fetch flights
# @router.get("/test", response_model=List[FlightResponse])
# async def test_fetch_flights(conn: snowflake.connector.SnowflakeConnection = Depends(get_snowflake_conn)):
#     try:
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM FINAL_PROJECT.PUBLIC.DAILY_FLIGHTS LIMIT 10")
#         rows = cur.fetchall()
#         columns = [desc[0].lower() for desc in cur.description]
#         flights = [dict(zip(columns, row)) for row in rows]
#         return flights
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching flights: {str(e)}")
#     finally:
#         cur.close()

# # Search flights by origin, destination, and date
# @router.get("/search", response_model=List[FlightResponse])
# async def search_flights(
#     origin_id: str = Query(..., description="Origin airport code (e.g., HYD)"),
#     destination_id: str = Query(..., description="Destination airport code (e.g., MIA)"),
#     departure_date: date = Query(..., description="Departure date (YYYY-MM-DD)"),
#     conn: snowflake.connector.SnowflakeConnection = Depends(get_snowflake_conn)
# ):
#     try:
#         cur = conn.cursor()
#         cur.execute("""
#             SELECT * FROM FINAL_PROJECT.PUBLIC.DAILY_FLIGHTS
#             WHERE origin_id = %s
#             AND destination_id = %s
#             AND DATE(departure_time) = %s
#         """, (origin_id.upper(), destination_id.upper(), departure_date))
#         rows = cur.fetchall()
#         if not rows:
#             raise HTTPException(status_code=404, detail="No flights found")
#         columns = [desc[0].lower() for desc in cur.description]
#         flights = [dict(zip(columns, row)) for row in rows]
#         return flights
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching flights: {str(e)}")
#     finally:
#         cur.close()

# # Get average price for 10-day period
# @router.get("/avg-price", response_model=List[AvgPriceResponse])
# async def get_avg_price(
#     origin_id: str = Query(..., description="Origin airport code"),
#     destination_id: str = Query(..., description="Destination airport code"),
#     start_date: date = Query(..., description="Start date of 10-day period (YYYY-MM-DD)"),
#     conn: snowflake.connector.SnowflakeConnection = Depends(get_snowflake_conn)
# ):
#     try:
#         cur = conn.cursor()
#         cur.execute("""
#             SELECT DATE(departure_time) as date, AVG(price_raw) as avg_price
#             FROM FINAL_PROJECT.PUBLIC.DAILY_FLIGHTS
#             WHERE origin_id = %s
#             AND destination_id = %s
#             AND DATE(departure_time) BETWEEN %s AND DATEADD(day, 9, %s)
#             GROUP BY DATE(departure_time)
#             ORDER BY DATE(departure_time)
#         """, (origin_id.upper(), destination_id.upper(), start_date, start_date))
#         rows = cur.fetchall()
#         if not rows:
#             raise HTTPException(status_code=404, detail="No price data found")
#         columns = [desc[0].lower() for desc in cur.description]
#         avg_prices = [dict(zip(columns, row)) for row in rows]
#         return avg_prices
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching average prices: {str(e)}")
#     finally:
#         cur.close()




from fastapi import APIRouter, Depends, HTTPException
import snowflake.connector
import os
from typing import List
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from fastapi import Query

router = APIRouter()

# Pydantic model for flight response with duration
class FlightResponse(BaseModel):
    flight_id: str
    price_raw: float
    price_formatted: str
    origin_id: str
    destination_id: str
    departure_time: datetime
    arrival_time: datetime
    airline_name: str
    flight_number: str
    load_date: datetime
    duration: str  # e.g., "20h 40m"

# Pydantic model for analysis response
class FlightAnalysis(BaseModel):
    cheapest_flight: FlightResponse
    average_price: float
    fastest_flight: FlightResponse
    price_range: dict[str, float]
    airline_count: int

# Dependency to get Snowflake connection
def get_snowflake_conn():
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA")
    )
    try:
        yield conn
    finally:
        conn.close()

# Test endpoint to fetch flights
@router.get("/test", response_model=List[FlightResponse])
async def test_fetch_flights(conn: snowflake.connector.SnowflakeConnection = Depends(get_snowflake_conn)):
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM FINAL_PROJECT.PUBLIC.DAILY_FLIGHTS LIMIT 10")
        rows = cur.fetchall()
        columns = [desc[0].lower() for desc in cur.description]
        flights = [dict(zip(columns, row)) for row in rows]
        # Calculate duration
        for flight in flights:
            departure = flight['departure_time']
            arrival = flight['arrival_time']
            duration = arrival - departure
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes = remainder // 60
            flight['duration'] = f"{int(hours)}h {int(minutes)}m"
        return flights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching flights: {str(e)}")
    finally:
        cur.close()

# Search flights by origin, destination, and date
@router.get("/search", response_model=List[FlightResponse])
async def search_flights(
    origin_id: str = Query(..., description="Origin airport code (e.g., HYD)"),
    destination_id: str = Query(..., description="Destination airport code (e.g., MIA)"),
    departure_date: date = Query(..., description="Departure date (YYYY-MM-DD)"),
    conn: snowflake.connector.SnowflakeConnection = Depends(get_snowflake_conn)
):
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM FINAL_PROJECT.PUBLIC.DAILY_FLIGHTS
            WHERE origin_id = %s
            AND destination_id = %s
            AND DATE(departure_time) = %s
        """, (origin_id.upper(), destination_id.upper(), departure_date))
        rows = cur.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No flights found")
        columns = [desc[0].lower() for desc in cur.description]
        flights = [dict(zip(columns, row)) for row in rows]
        # Calculate duration
        for flight in flights:
            departure = flight['departure_time']
            arrival = flight['arrival_time']
            duration = arrival - departure
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes = remainder // 60
            flight['duration'] = f"{int(hours)}h {int(minutes)}m"
        return flights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching flights: {str(e)}")
    finally:
        cur.close()

# Analyze flights
@router.get("/analysis", response_model=FlightAnalysis)
async def analyze_flights(
    origin_id: str = Query(..., description="Origin airport code"),
    destination_id: str = Query(..., description="Destination airport code"),
    departure_date: date = Query(..., description="Departure date (YYYY-MM-DD)"),
    conn: snowflake.connector.SnowflakeConnection = Depends(get_snowflake_conn)
):
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM FINAL_PROJECT.PUBLIC.DAILY_FLIGHTS
            WHERE origin_id = %s
            AND destination_id = %s
            AND DATE(departure_time) = %s
        """, (origin_id.upper(), destination_id.upper(), departure_date))
        rows = cur.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No flights found")
        columns = [desc[0].lower() for desc in cur.description]
        flights = [dict(zip(columns, row)) for row in rows]

        # Calculate duration for each flight
        for flight in flights:
            departure = flight['departure_time']
            arrival = flight['arrival_time']
            duration = arrival - departure
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes = remainder // 60
            flight['duration'] = f"{int(hours)}h {int(minutes)}m"

        # Analysis
        cheapest_flight = min(flights, key=lambda x: x['price_raw'])
        fastest_flight = min(flights, key=lambda x: (x['arrival_time'] - x['departure_time']).total_seconds())
        average_price = sum(flight['price_raw'] for flight in flights) / len(flights)
        price_range = {
            "min": min(flight['price_raw'] for flight in flights),
            "max": max(flight['price_raw'] for flight in flights)
        }
        airline_count = len(set(flight['airline_name'] for flight in flights))

        return {
            "cheapest_flight": cheapest_flight,
            "average_price": average_price,
            "fastest_flight": fastest_flight,
            "price_range": price_range,
            "airline_count": airline_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing flights: {str(e)}")
    finally:
        cur.close()