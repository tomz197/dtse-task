from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel


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


class CreateTokenRequest(BaseModel):
    expires_at: Optional[str] = None


class CreateTokenResponse(BaseModel):
    token: str
    expires_at: Optional[str] = None


class RevokeTokenRequest(BaseModel):
    token: str


class RevokeTokenResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    token: str
    expires_at: Optional[str] = None


class TokensResponse(BaseModel):
    tokens: List[Dict]


def prepare_input_data(data_dicts, expected_features):
    df = pd.DataFrame(data_dicts)
    df = pd.get_dummies(df)

    for col in expected_features:
        if col not in df.columns:
            df[col] = 0

    df = df[expected_features]

    return df
