from fastapi import APIRouter, Depends, HTTPException, Body
from app.controllers.flight_controller import FlightController
from app.models.schemas import FlightResponse
from app.config.settings import get_settings, Settings

router = APIRouter(prefix="/flights", tags=["flights"])

from pydantic import BaseModel

class FlightRequest(BaseModel):
    source: str
    destination: str
    date: str

@router.post("/", response_model=FlightResponse)
async def get_flight_data(
    request: FlightRequest = Body(...),  # Explicitly use Body parameter
    settings: Settings = Depends(get_settings)
):
    """Get flight data for a specific route and date"""
    import logging
    logging.info(f"Received request: {request}")
    try:
        # Initialize controller
        controller = FlightController(settings)
        
        # Process request - pass the request object directly
        response = await controller.process_flight_request(request)
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing flight data: {str(e)}")

@router.post("/test", response_model=dict)
async def test_endpoint(request: FlightRequest = Body(...)):
    """Test endpoint to verify request body parsing"""
    return {"received": {"source": request.source, 
                        "destination": request.destination, 
                        "date": request.date}}