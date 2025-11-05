import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from src.database import DatabaseManager
from src.logging_config import get_logger, setup_logging
from src.model import MODEL_NAME, HousingModel
from src.rate_limit import RateLimiter
from src.schemas import (CreateTokenRequest, CreateTokenResponse, HousingInput,
                         PredictionResponse, RevokeTokenRequest,
                         RevokeTokenResponse, TokensResponse,
                         prepare_input_data)

log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE", "logs/app.log")
setup_logging(
    log_level=log_level,
    log_file=log_file,
    enable_file_logging=True,
    enable_console_logging=True,
)
logger = get_logger(__name__)

DB_PATH = os.getenv("DB_PATH", "data/housing.db") or os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "housing.db"
)

housing_model = None
db_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global housing_model, db_manager
    logger.info("Starting application lifespan")
    try:
        logger.info(f"Loading housing model from {MODEL_NAME}")
        housing_model = HousingModel(MODEL_NAME)
        logger.info("Model loaded successfully")

        logger.info(f"Initializing database manager with path: {DB_PATH}")
        db_manager = DatabaseManager(DB_PATH)
        logger.info("Database manager initialized")

        logger.info("Initializing rate limiter")
        RateLimiter(db_manager=db_manager)
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error during application startup: {e}", exc_info=True)
        raise

    yield

    logger.info("Shutting down application")
    housing_model = None
    del db_manager
    logger.info("Application shutdown complete")


app = FastAPI(lifespan=lifespan)


# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            }
        },
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"Response: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                }
            },
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} - Error: {str(e)} - Time: {process_time:.3f}s",
            exc_info=True,
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                }
            },
        )
        raise


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring and container health checks."""
    try:
        # Check if model and database are initialized
        if housing_model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not initialized",
            )
        if db_manager is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not initialized",
            )
        return {
            "status": "healthy",
            "service": "dtse-api",
            "model_loaded": True,
            "database_initialized": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service unhealthy"
        )


@app.post("/predict", response_model=PredictionResponse)
def predict_housing_price(
    input_data: HousingInput,
    token: str = Depends(RateLimiter().check_rate_limit_dependency),
):
    logger.info(f"Predicting housing price for single input (token: {token[:8]}...)")
    try:
        df = prepare_input_data(
            [input_data.model_dump()], housing_model.expected_features
        )
        prediction = housing_model.predict(df)
        result = float(prediction[0])
        logger.info(f"Prediction successful: {result:.2f}")
        return PredictionResponse(median_house_value=result)
    except Exception as e:
        logger.error(f"Error during prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed",
        )


@app.post("/predict/batch", response_model=List[PredictionResponse])
def predict_housing_price_batch(
    input_data: List[HousingInput],
    token: str = Depends(RateLimiter().check_rate_limit_dependency),
):
    logger.info(
        f"Predicting housing prices for batch of {len(input_data)} inputs (token: {token[:8]}...)"
    )
    try:
        if not input_data:
            logger.info("Empty batch request, returning empty list")
            return []

        data_dicts = [item.model_dump() for item in input_data]
        df = prepare_input_data(data_dicts, housing_model.expected_features)
        predictions = housing_model.predict(df)
        logger.info(
            f"Batch prediction successful: {len(predictions)} predictions generated"
        )
        return [
            PredictionResponse(median_house_value=float(pred)) for pred in predictions
        ]
    except Exception as e:
        logger.error(f"Error during batch prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch prediction failed",
        )


@app.post("/create-token", response_model=CreateTokenResponse)
def create_token(request: CreateTokenRequest):
    logger.info("Creating new API token")
    expires_at = None
    try:
        if request.expires_at:
            expires_at = datetime.fromisoformat(request.expires_at)
            logger.info(f"Token expiration set to: {expires_at}")
    except ValueError as e:
        logger.warning(f"Invalid expires_at format: {request.expires_at}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid expires_at format"
        )

    token = uuid.uuid4().hex
    try:
        db_manager.create_api_token(token, expires_at)
        logger.info(f"API token created successfully: {token[:8]}...")
        return CreateTokenResponse(token=token, expires_at=request.expires_at)
    except Exception as e:
        logger.error(f"Error creating API token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create token",
        )


@app.post("/revoke-token", response_model=RevokeTokenResponse)
def revoke_token(request: RevokeTokenRequest):
    logger.info(f"Revoking API token: {request.token[:8]}...")
    if not db_manager.deactivate_api_token(request.token):
        logger.warning(f"Token not found for revocation: {request.token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token not found"
        )
    logger.info(f"Token revoked successfully: {request.token[:8]}...")
    return RevokeTokenResponse(message="Token revoked successfully")


@app.post("/get-tokens")
def get_tokens():
    logger.info("Retrieving all active API tokens")
    try:
        tokens = db_manager.get_api_tokens()
        logger.info(f"Retrieved {len(tokens)} active tokens")
        return TokensResponse(tokens=tokens)
    except Exception as e:
        logger.error(f"Error retrieving tokens: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tokens",
        )
