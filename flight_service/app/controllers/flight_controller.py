from datetime import datetime
import logging
from app.models.schemas import FlightRequest, FlightResponse
from app.services.flight_service import FlightService
from app.services.s3_service import S3Service
from app.services.airflow_service import AirflowService
from app.config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class FlightController:
    """Controller for handling flight data requests"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.flight_service = FlightService(settings)
        self.s3_service = S3Service(settings)
        self.airflow_service = AirflowService(settings)
    
    async def process_flight_request(self, request: FlightRequest) -> FlightResponse:
        """
        Process a flight data request:
        1. Fetch daily and monthly flight data
        2. Store data in S3
        3. Trigger Airflow DAG
        """
        try:
            # Log request information
            logging.info(f"Processing flight request: {request.source} to {request.destination} on {request.date}")
            
            # Extract month from date
            flight_date = datetime.strptime(request.date, "%Y-%m-%d")
            month_year = flight_date.strftime("%Y-%m")
            
            # 1. Get daily flight data
            logging.info(f"Fetching daily flight data for {request.date}")
            daily_data = await self.flight_service.fetch_flight_data(
                request.source, 
                request.destination, 
                date=request.date
            )
            logging.info("Daily flight data fetched successfully")
            
            # 2. Get monthly flight data
            logging.info(f"Fetching monthly flight data for {month_year}")
            monthly_data = await self.flight_service.fetch_flight_data(
                request.source, 
                request.destination, 
                month=month_year
            )
            logging.info("Monthly flight data fetched successfully")
            
            # 3. Third API call placeholder (Amadeus - to be implemented)
            # logging.info("Fetching Amadeus data")
            # amadeus_data = await self.flight_service.fetch_amadeus_data(...)
            # logging.info("Amadeus data fetched successfully")
            
            # Upload data to S3
            daily_s3_key = f"Flightdata/{request.source}_to_{request.destination}_{request.date}_daily.json"
            logging.info(f"Uploading daily data to S3: {daily_s3_key}")
            daily_s3_info = await self.s3_service.upload_json(
                self.settings.S3_BUCKET_NAME,
                daily_s3_key,
                daily_data
            )
            
            monthly_s3_key = f"Flightdata/{request.source}_to_{request.destination}_{month_year}_monthly.json"
            logging.info(f"Uploading monthly data to S3: {monthly_s3_key}")
            monthly_s3_info = await self.s3_service.upload_json(
                self.settings.S3_BUCKET_NAME,
                monthly_s3_key,
                monthly_data
            )
            
            # Trigger Airflow DAG
            airflow_payload = {
                "conf": {
                    "daily_s3_bucket": self.settings.S3_BUCKET_NAME,
                    "daily_s3_key": daily_s3_key,
                    "monthly_s3_bucket": self.settings.S3_BUCKET_NAME,
                    "monthly_s3_key": monthly_s3_key
                }
            }
            
            logging.info("Triggering Airflow DAG")
            airflow_response = await self.airflow_service.trigger_dag(airflow_payload)
            logging.info(f"Airflow DAG triggered successfully: {airflow_response}")
            
            # Return response
            return FlightResponse(
                status="success",
                daily_data_url=daily_s3_info.url,
                monthly_data_url=monthly_s3_info.url,
                airflow_dag_run=airflow_response
            )
        except Exception as e:
            # Log errors at controller level
            logging.error(f"Error processing flight request: {str(e)}")
            raise e