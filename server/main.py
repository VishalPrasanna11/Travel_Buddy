from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging
from dotenv import load_dotenv

from routes.userRoute import router as user_router
from routes.llmRoute import router as llm_router
from routes.llm_chat_historyRoute import router as llm_chat_history_router
from routes.geocodeRoute import router as geocode_router
from routes.chatRoute import router as chat_router
from routes.flightRoute import router as flight_router
from routes.placesRoute import router as places_router
from routes.bookingRoute import router as booking_router
from routes.conversationRoute import router as conversation_router
from routes.feedbackRoute import router as feedback_router
from middlewares.errors import RequestIdMiddleware, install_error_handlers

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
        # Create new app tables (conversations, feedback, …) if they don't exist yet.
        from middlewares.conn_database import engine
        from models.appModels import AppBase
        AppBase.metadata.create_all(bind=engine)
        logger.info("App tables ready")
    except Exception as e:
        logger.warning(f"Could not create app tables (DB unavailable?): {e}")
    try:
        from tools.routestack_auth import get_token
        get_token()
        logger.info("Successfully authenticated with RouteStack API")
    except Exception as e:
        logger.warning(f"RouteStack auth check failed (will retry on first request): {str(e)}")
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
    "http://localhost:5173",
    os.getenv("FRONTEND_URL", ""),
    "https://travelbuddyai-5b869d0b00e5.herokuapp.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After", "X-Schema-Version"],
)

app.add_middleware(RequestIdMiddleware)
install_error_handlers(app)

app.include_router(user_router, prefix="/api/users", tags=["users"])
app.include_router(llm_router, prefix="/api/llm", tags=["llm"])
app.include_router(llm_chat_history_router, prefix="/api/user", tags=["user"])
app.include_router(geocode_router, prefix="/api/maps", tags=["maps"])
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(flight_router, prefix="/api/flights", tags=["flights"])
app.include_router(places_router, prefix="/api/places", tags=["places"])
app.include_router(booking_router, prefix="/api/book", tags=["booking"])
app.include_router(conversation_router, prefix="/api/conversations", tags=["conversations"])
app.include_router(feedback_router, prefix="/api/feedback", tags=["feedback"])


@app.get("/api/health", tags=["root"])
async def health():
    return {
        "message": "Welcome to TravelBuddy API",
        "version": "1.0.0",
        "status": "online",
    }

# Serve React static build if the directory exists (Heroku production)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = os.path.join(_static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
