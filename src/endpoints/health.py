from fastapi import APIRouter, HTTPException, status

from src.jsend import success_response
from src.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
def health_check():
    import src.config as config

    try:
        if config.housing_model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not initialized",
            )
        if config.db_manager is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not initialized",
            )
        return success_response(
            {
                "status": "healthy",
                "service": "dtse-api",
                "model_loaded": True,
                "database_initialized": True,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service unhealthy")
