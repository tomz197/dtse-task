from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from src.jsend import success_response
from src.logging_config import get_logger
from src.rate_limit import RateLimiter
from src.schemas import HousingInput, prepare_input_data

logger = get_logger(__name__)

router = APIRouter()


@router.post("/predict")
def predict_housing_price(
    input_data: HousingInput,
    token: str = Depends(RateLimiter().check_rate_limit_dependency),
):
    logger.info(f"Predicting housing price for single input (token: {token[:8]}...)")

    import src.config as config

    if config.housing_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not initialized",
        )

    try:
        df = prepare_input_data([input_data.model_dump()], config.housing_model.expected_features)
        prediction = config.housing_model.predict(df)
        result = float(prediction[0])
        logger.info(f"Prediction successful: {result:.2f}")
        return success_response({"median_house_value": result})
    except Exception as e:
        logger.error(f"Error during prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed",
        )


@router.post("/predict/batch")
def predict_housing_price_batch(
    input_data: List[HousingInput],
    token: str = Depends(RateLimiter().check_rate_limit_dependency),
):
    logger.info(f"Predicting housing prices for batch of {len(input_data)} inputs (token: {token[:8]}...)")

    import src.config as config

    if config.housing_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not initialized",
        )

    try:
        if not input_data:
            logger.info("Empty batch request, returning empty list")
            return success_response({"predictions": []})

        data_dicts = [item.model_dump() for item in input_data]
        df = prepare_input_data(data_dicts, config.housing_model.expected_features)
        predictions = config.housing_model.predict(df)
        logger.info(f"Batch prediction successful: {len(predictions)} predictions generated")
        predictions_list = [{"median_house_value": float(pred)} for pred in predictions]
        return success_response({"predictions": predictions_list})
    except Exception as e:
        logger.error(f"Error during batch prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch prediction failed",
        )
