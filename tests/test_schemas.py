import pandas as pd
import pytest
from pydantic import ValidationError

from src.schemas import (CreateTokenRequest, CreateTokenResponse, HousingInput,
                         PredictionResponse, RevokeTokenRequest,
                         RevokeTokenResponse, TokensResponse,
                         prepare_input_data)


class TestHousingInput:
    """Tests for HousingInput schema"""

    def test_valid_housing_input(self):
        """Test creating a valid HousingInput"""
        data = {
            "longitude": -122.64,
            "latitude": 38.01,
            "housing_median_age": 36.0,
            "total_rooms": 1336.0,
            "total_bedrooms": 258.0,
            "population": 678.0,
            "households": 249.0,
            "median_income": 5.5789,
            "ocean_proximity": "NEAR OCEAN",
        }

        input_obj = HousingInput(**data)
        assert input_obj.longitude == -122.64
        assert input_obj.ocean_proximity == "NEAR OCEAN"

    def test_housing_input_missing_field(self):
        """Test that missing fields raise ValidationError"""
        data = {
            "longitude": -122.64,
            "latitude": 38.01,
            # Missing other required fields
        }

        with pytest.raises(ValidationError):
            HousingInput(**data)

    def test_housing_input_invalid_type(self):
        """Test that invalid types raise ValidationError"""
        data = {
            "longitude": "invalid",  # Should be float
            "latitude": 38.01,
            "housing_median_age": 36.0,
            "total_rooms": 1336.0,
            "total_bedrooms": 258.0,
            "population": 678.0,
            "households": 249.0,
            "median_income": 5.5789,
            "ocean_proximity": "NEAR OCEAN",
        }

        with pytest.raises(ValidationError):
            HousingInput(**data)


class TestPredictionResponse:
    """Tests for PredictionResponse schema"""

    def test_valid_prediction_response(self):
        """Test creating a valid PredictionResponse"""
        response = PredictionResponse(median_house_value=320201.58554044)
        assert response.median_house_value == 320201.58554044

    def test_prediction_response_model_dump(self):
        """Test model_dump method"""
        response = PredictionResponse(median_house_value=320201.58554044)
        data = response.model_dump()
        assert data == {"median_house_value": 320201.58554044}


class TestTokenSchemas:
    """Tests for token-related schemas"""

    def test_create_token_request_no_expiration(self):
        """Test CreateTokenRequest without expiration"""
        request = CreateTokenRequest()
        assert request.expires_at is None

    def test_create_token_request_with_expiration(self):
        """Test CreateTokenRequest with expiration"""
        expires_at = "2024-12-31T23:59:59"
        request = CreateTokenRequest(expires_at=expires_at)
        assert request.expires_at == expires_at

    def test_create_token_response(self):
        """Test CreateTokenResponse"""
        token = "test_token_12345"
        response = CreateTokenResponse(token=token, expires_at=None)
        assert response.token == token
        assert response.expires_at is None

    def test_revoke_token_request(self):
        """Test RevokeTokenRequest"""
        token = "test_token_12345"
        request = RevokeTokenRequest(token=token)
        assert request.token == token

    def test_revoke_token_response(self):
        """Test RevokeTokenResponse"""
        response = RevokeTokenResponse(message="Token revoked successfully")
        assert response.message == "Token revoked successfully"

    def test_tokens_response(self):
        """Test TokensResponse"""
        tokens = [
            {"token": "token1", "is_active": 1},
            {"token": "token2", "is_active": 1},
        ]
        response = TokensResponse(tokens=tokens)
        assert len(response.tokens) == 2
        assert response.tokens == tokens


class TestPrepareInputData:
    """Tests for prepare_input_data function"""

    def test_prepare_input_data_single(self):
        """Test preparing input data for a single record"""
        expected_features = [
            "longitude",
            "latitude",
            "housing_median_age",
            "total_rooms",
            "total_bedrooms",
            "population",
            "households",
            "median_income",
            "ocean_proximity_<1H OCEAN",
            "ocean_proximity_INLAND",
            "ocean_proximity_ISLAND",
            "ocean_proximity_NEAR BAY",
            "ocean_proximity_NEAR OCEAN",
        ]

        data_dicts = [
            {
                "longitude": -122.64,
                "latitude": 38.01,
                "housing_median_age": 36.0,
                "total_rooms": 1336.0,
                "total_bedrooms": 258.0,
                "population": 678.0,
                "households": 249.0,
                "median_income": 5.5789,
                "ocean_proximity": "NEAR OCEAN",
            }
        ]

        df = prepare_input_data(data_dicts, expected_features)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == expected_features
        assert df["ocean_proximity_NEAR OCEAN"].iloc[0] == 1
        assert df["ocean_proximity_<1H OCEAN"].iloc[0] == 0

    def test_prepare_input_data_batch(self):
        """Test preparing input data for multiple records"""
        expected_features = [
            "longitude",
            "latitude",
            "housing_median_age",
            "total_rooms",
            "total_bedrooms",
            "population",
            "households",
            "median_income",
            "ocean_proximity_<1H OCEAN",
            "ocean_proximity_INLAND",
            "ocean_proximity_ISLAND",
            "ocean_proximity_NEAR BAY",
            "ocean_proximity_NEAR OCEAN",
        ]

        data_dicts = [
            {
                "longitude": -122.64,
                "latitude": 38.01,
                "housing_median_age": 36.0,
                "total_rooms": 1336.0,
                "total_bedrooms": 258.0,
                "population": 678.0,
                "households": 249.0,
                "median_income": 5.5789,
                "ocean_proximity": "NEAR OCEAN",
            },
            {
                "longitude": -115.73,
                "latitude": 33.35,
                "housing_median_age": 23.0,
                "total_rooms": 1586.0,
                "total_bedrooms": 448.0,
                "population": 338.0,
                "households": 182.0,
                "median_income": 1.2132,
                "ocean_proximity": "INLAND",
            },
        ]

        df = prepare_input_data(data_dicts, expected_features)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == expected_features
        assert df["ocean_proximity_NEAR OCEAN"].iloc[0] == 1
        assert df["ocean_proximity_INLAND"].iloc[1] == 1

    def test_prepare_input_data_missing_features(self):
        """Test that missing features are filled with zeros"""
        expected_features = [
            "longitude",
            "latitude",
            "housing_median_age",
            "total_rooms",
            "total_bedrooms",
            "population",
            "households",
            "median_income",
            "ocean_proximity_<1H OCEAN",
            "ocean_proximity_INLAND",
            "ocean_proximity_ISLAND",
            "ocean_proximity_NEAR BAY",
            "ocean_proximity_NEAR OCEAN",
            "extra_feature",
        ]

        data_dicts = [
            {
                "longitude": -122.64,
                "latitude": 38.01,
                "housing_median_age": 36.0,
                "total_rooms": 1336.0,
                "total_bedrooms": 258.0,
                "population": 678.0,
                "households": 249.0,
                "median_income": 5.5789,
                "ocean_proximity": "NEAR OCEAN",
            }
        ]

        df = prepare_input_data(data_dicts, expected_features)

        # Extra feature should be added with zeros
        assert "extra_feature" in df.columns
        assert df["extra_feature"].iloc[0] == 0
