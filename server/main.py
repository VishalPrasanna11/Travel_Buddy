from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv

from routes.userRoute import router as user_router
from models.userModel import Base
from middlewares.conn_database import engine
from routes.geocodeRoute import router as geocode_router
from routes.chatRoute import router as chat_router



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create database tables automatically
logger.info("Creating database tables if they don't exist...")
Base.metadata.create_all(bind=engine)
logger.info("Database tables initialization complete")

# Create FastAPI application
app = FastAPI(
    title="User Authentication API",
    description="API for user authentication with Auth0 and PostgreSQL",
    version="1.0.0",
)

# Configure CORS
origins = [
    "http://localhost:3000",  # React frontend
    "http://localhost:8000",
    os.getenv("FRONTEND_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user_router, prefix="/api/users", tags=["users"])

app.include_router(geocode_router, prefix="/api/maps", tags=["maps"])

app.include_router(chat_router, prefix="/api", tags=["chat"])



@app.get("/", tags=["root"])
async def root():
    """Root endpoint to verify the API is running"""
    return {
        "message": "Welcome to User Authentication API",
        "version": "1.0.0",
        "status": "online"
    }

@app.on_event("startup")
async def startup_event():
    """Function that runs on application startup"""
    logger.info("Starting up the application...")
    # Check database connection
    try:
        # Create a connection to verify database is available
        with engine.connect() as connection:
            logger.info("Successfully connected to the database")
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")

if __name__ == "__main__":
    import uvicorn
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    # Run the application
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)