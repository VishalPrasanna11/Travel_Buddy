from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv

from routes.userRoute import router as user_router
from routes.llmRoute import router as llm_router
from routes.llm_chat_historyRoute import router as llm_chat_history_router
from routes.geocodeRoute import router as geocode_router
from routes.chatRoute import router as chat_router
from routes.flightRoute import router as flight_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()


@asynccontextmanager
async def lifespan(app):
    logger.info("Starting up the application...")
    try:
        import snowflake.connector

        ctx = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
        )
        ctx.close()
        logger.info("Successfully connected to Snowflake")
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {str(e)}")
    yield


app = FastAPI(
    title="TravelBuddy API",
    description="AI-powered travel planning assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",
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

app.include_router(user_router, prefix="/api/users", tags=["users"])
app.include_router(llm_router, prefix="/api/llm", tags=["llm"])
app.include_router(llm_chat_history_router, prefix="/api/user", tags=["user"])
app.include_router(geocode_router, prefix="/api/maps", tags=["maps"])
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(flight_router, prefix="/api/flights", tags=["flights"])


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to TravelBuddy API",
        "version": "1.0.0",
        "status": "online",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
