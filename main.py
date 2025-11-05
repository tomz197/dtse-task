from fastapi import FastAPI, HTTPException, status, Depends, Header
from typing import List, Optional
from contextlib import asynccontextmanager
from src.model import HousingModel, MODEL_NAME
from src.schemas import (
    HousingInput, 
    PredictionResponse, 
    prepare_input_data, 
    TokensResponse,
    CreateTokenRequest,
    CreateTokenResponse,
    RevokeTokenRequest,
    RevokeTokenResponse
)
from src.database import DatabaseManager, DB_PATH
from src.rate_limit import RateLimiter
import uuid
from datetime import datetime


housing_model = None
db_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global housing_model, db_manager
    housing_model = HousingModel(MODEL_NAME)
    db_manager = DatabaseManager(DB_PATH)
    RateLimiter(db_manager=db_manager)
    yield
    housing_model = None
    del db_manager


app = FastAPI(lifespan=lifespan)


@app.post("/predict", response_model=PredictionResponse)
def predict_housing_price(
    input_data: HousingInput,
    token: str = Depends(RateLimiter().check_rate_limit_dependency)
):
    df = prepare_input_data([input_data.model_dump()], housing_model.expected_features)
    prediction = housing_model.predict(df)
    
    return PredictionResponse(median_house_value=float(prediction[0]))


@app.post("/predict/batch", response_model=List[PredictionResponse])
def predict_housing_price_batch(
    input_data: List[HousingInput],
    token: str = Depends(RateLimiter().check_rate_limit_dependency)
):
    data_dicts = [item.model_dump() for item in input_data]
    df = prepare_input_data(data_dicts, housing_model.expected_features)
    predictions = housing_model.predict(df)
    
    return [PredictionResponse(median_house_value=float(pred)) for pred in predictions]


@app.post("/create-token", response_model=CreateTokenResponse)
def create_token(request: CreateTokenRequest):
    expires_at = None
    try:
        if request.expires_at:
            expires_at = datetime.fromisoformat(request.expires_at)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid expires_at format")

    token = uuid.uuid4().hex
    db_manager.create_api_token(token, expires_at)

    return CreateTokenResponse(
        token=token,
        expires_at=request.expires_at
    )


@app.post("/revoke-token", response_model=RevokeTokenResponse)
def revoke_token(request: RevokeTokenRequest):
    if not db_manager.deactivate_api_token(request.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token not found")
    return RevokeTokenResponse(message="Token revoked successfully")


@app.post("/get-tokens")
def get_tokens():
    tokens = db_manager.get_api_tokens()
    return TokensResponse(tokens=tokens)