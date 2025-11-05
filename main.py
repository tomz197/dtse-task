import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from src.database import DatabaseManager
from src.endpoints import health, predict, tokens
from src.logging_config import get_logger, setup_logging
from src.middleware import RequestLoggingMiddleware
from src.model import MODEL_NAME, HousingModel
from src.rate_limit import RateLimiter

load_dotenv()

log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE", "logs/app.log")
setup_logging(
    log_level=log_level,
    log_file=log_file,
    enable_file_logging=True,
    enable_console_logging=True,
)
logger = get_logger(__name__)

DB_PATH = os.getenv("DB_PATH", "data/housing.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import src.config as config
    logger.info("Starting application lifespan")
    try:
        logger.info(f"Loading housing model from {MODEL_NAME}")
        config.housing_model = HousingModel(MODEL_NAME)
        logger.info("Model loaded successfully")

        logger.info(f"Initializing database manager with path: {DB_PATH}")
        config.db_manager = DatabaseManager(DB_PATH)
        logger.info("Database manager initialized")

        logger.info("Initializing rate limiter")
        RateLimiter(db_manager=config.db_manager)
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error during application startup: {e}", exc_info=True)
        raise

    yield

    logger.info("Shutting down application")
    config.housing_model = None
    config.db_manager = None
    logger.info("Application shutdown complete")


app = FastAPI(
    title="DTSE Housing Price Prediction API",
    description="""
    REST API for housing price predictions using machine learning models.
    
    Features:
    * Token-based authentication
    * Rate limiting
    * Single and batch prediction endpoints
    * Token management endpoints
    
    The API uses a pre-trained machine learning model to predict median house values
    based on property characteristics such as location, age, rooms, and income.
    """,
    version="1.0.0",
    lifespan=lifespan,
    tags_metadata=[
        {
            "name": "health",
            "description": "Health check endpoints to verify service availability and status.",
        },
        {
            "name": "predictions",
            "description": "Housing price prediction endpoints. Requires authentication via Bearer token.",
        },
        {
            "name": "tokens",
            "description": "API token management endpoints. Requires admin credentials.",
        },
    ],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(health.router, tags=["health"])
app.include_router(predict.router, tags=["predictions"])
app.include_router(tokens.router, tags=["tokens"])
