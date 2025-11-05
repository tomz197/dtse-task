from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field, field_validator


class HousingInput(BaseModel):
    longitude: float = Field(..., description="Longitude of the property location")
    latitude: float = Field(..., description="Latitude of the property location")
    housing_median_age: float = Field(..., ge=0, description="Median age of housing in the area")
    total_rooms: float = Field(..., ge=0, description="Total number of rooms")
    total_bedrooms: float = Field(..., ge=0, description="Total number of bedrooms")
    population: float = Field(..., ge=0, description="Population in the area")
    households: float = Field(..., ge=0, description="Number of households")
    median_income: float = Field(..., ge=0, description="Median income in the area")
    ocean_proximity: str = Field(..., description="Distance from the ocean")

    @field_validator('ocean_proximity')
    @classmethod
    def validate_ocean_proximity(cls, v: str) -> str:
        allowed_values = ['<1H OCEAN', 'INLAND', 'ISLAND', 'NEAR BAY', 'NEAR OCEAN']
        if v not in allowed_values:
            raise ValueError(f"ocean_proximity must be one of {allowed_values}, got '{v}'")
        return v


class PredictionResponse(BaseModel):
    median_house_value: float


class CreateTokenRequest(BaseModel):
    username: str
    password: str
    expires_at: Optional[str] = None


class CreateTokenResponse(BaseModel):
    token: str
    expires_at: Optional[str] = None


class RevokeTokenRequest(BaseModel):
    username: str
    password: str
    token: str


class RevokeTokenResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    token: str
    expires_at: Optional[str] = None


class GetTokensRequest(BaseModel):
    username: str
    password: str


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
