from pydantic import BaseModel
import pandas as pd

class HousingInput(BaseModel):
    longitude: float
    latitude: float
    housing_median_age: float
    total_rooms: float
    total_bedrooms: float
    population: float
    households: float
    median_income: float
    ocean_proximity: str

class PredictionResponse(BaseModel):
    median_house_value: float

def prepare_input_data(data_dicts, expected_features):
    df = pd.DataFrame(data_dicts)
    df = pd.get_dummies(df)
    
    for col in expected_features:
        if col not in df.columns:
            df[col] = 0
    
    df = df[expected_features]
    
    return df

