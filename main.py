from fastapi import FastAPI
from typing import List
from contextlib import asynccontextmanager
from src.model import HousingModel, MODEL_NAME
from src.schemas import HousingInput, PredictionResponse, prepare_input_data

housing_model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global housing_model
    housing_model = HousingModel(MODEL_NAME)
    yield
    housing_model = None

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Housing Price Prediction API"}

@app.post("/predict", response_model=PredictionResponse)
def predict_housing_price(input_data: HousingInput):
    df = prepare_input_data([input_data.dict()], housing_model.expected_features)
    prediction = housing_model.predict(df)
    
    return PredictionResponse(median_house_value=float(prediction[0]))

@app.post("/predict/batch", response_model=List[PredictionResponse])
def predict_housing_price_batch(input_data: List[HousingInput]):
    data_dicts = [item.dict() for item in input_data]
    df = prepare_input_data(data_dicts, housing_model.expected_features)
    predictions = housing_model.predict(df)
    
    return [PredictionResponse(median_house_value=float(pred)) for pred in predictions]

