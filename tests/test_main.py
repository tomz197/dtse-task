from datetime import datetime, timedelta
from unittest.mock import MagicMock

from fastapi import status


def setup_mock_housing_model():
    """Helper function to create a mock housing model"""
    import src.config as config

    if config.housing_model is None:
        model = MagicMock()
        model.expected_features = [
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

        def mock_predict(df):
            return df["median_income"].values * 100000

        model.predict = mock_predict
        config.housing_model = model


def update_db_manager_and_rate_limiter(db_manager):
    """Helper function to update main.db_manager, config.db_manager and RateLimiter's db_manager"""
    import main
    import src.config as config
    from src.rate_limit import RateLimiter

    main.db_manager = db_manager
    config.db_manager = db_manager
    # Update RateLimiter's db_manager if it exists, or create new instance
    if RateLimiter._instance is not None:
        RateLimiter._instance._db_manager = db_manager
    else:
        # Create new instance with the db_manager
        RateLimiter(requests_per_minute=100, window_seconds=60, db_manager=db_manager)


class TestPredictEndpoints:
    """Tests for prediction endpoints"""

    def test_predict_single_without_token(self, app_client):
        """Test /predict endpoint without token"""
        sample_input = {
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

        response = app_client.post("/predict", json=sample_input)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
        error_data = response.json()
        assert error_data["status"] == "fail"

    def test_predict_single_with_token(self, app_client, db_manager_with_token):
        """Test /predict endpoint with valid token"""
        db_manager, _, token = db_manager_with_token
        update_db_manager_and_rate_limiter(db_manager)
        setup_mock_housing_model()

        sample_input = {
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

        response = app_client.post("/predict", json=sample_input, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "median_house_value" in data["data"]
        assert isinstance(data["data"]["median_house_value"], float)

    def test_predict_single_invalid_input(self, app_client, db_manager_with_token):
        """Test /predict endpoint with invalid input"""
        db_manager, _, token = db_manager_with_token
        update_db_manager_and_rate_limiter(db_manager)

        invalid_input = {
            "longitude": "invalid",  # Should be float
            "latitude": 38.01,
            # Missing other required fields
        }

        response = app_client.post("/predict", json=invalid_input, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert error_data["status"] == "fail"
        assert "data" in error_data

    def test_predict_batch_with_token(self, app_client, db_manager_with_token):
        """Test /predict/batch endpoint with valid token"""
        db_manager, _, token = db_manager_with_token
        update_db_manager_and_rate_limiter(db_manager)
        setup_mock_housing_model()

        sample_inputs = [
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

        response = app_client.post(
            "/predict/batch",
            json=sample_inputs,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "predictions" in data["data"]
        assert isinstance(data["data"]["predictions"], list)
        assert len(data["data"]["predictions"]) == 2
        assert all("median_house_value" in item for item in data["data"]["predictions"])

    def test_predict_batch_empty_list(self, app_client, db_manager_with_token):
        """Test /predict/batch endpoint with empty list"""
        db_manager, _, token = db_manager_with_token
        update_db_manager_and_rate_limiter(db_manager)
        setup_mock_housing_model()

        response = app_client.post("/predict/batch", json=[], headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "predictions" in data["data"]
        assert isinstance(data["data"]["predictions"], list)
        assert len(data["data"]["predictions"]) == 0


class TestTokenEndpoints:
    """Tests for token management endpoints"""

    def test_create_token_no_expiration(self, app_client, temp_db):
        """Test creating a token without expiration"""
        import main
        import src.config as config

        db_manager, _ = temp_db  # Update db_manager for this test
        main.db_manager = db_manager
        config.db_manager = db_manager

        response = app_client.post("/create-token", json={"username": "test", "password": "test"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "token" in data["data"]
        assert data["data"]["expires_at"] is None
        assert len(data["data"]["token"]) > 0

    def test_create_token_with_expiration(self, app_client, temp_db):
        """Test creating a token with expiration"""
        import main
        import src.config as config

        db_manager, _ = temp_db
        main.db_manager = db_manager
        config.db_manager = db_manager

        expires_at = (datetime.now() + timedelta(days=7)).isoformat()

        response = app_client.post(
            "/create-token",
            json={"username": "test", "password": "test", "expires_at": expires_at},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "token" in data["data"]
        assert data["data"]["expires_at"] == expires_at

    def test_create_token_invalid_expiration_format(self, app_client, temp_db):
        """Test creating a token with invalid expiration format"""
        import main
        import src.config as config

        db_manager, _ = temp_db
        main.db_manager = db_manager
        config.db_manager = db_manager

        response = app_client.post(
            "/create-token",
            json={"username": "test", "password": "test", "expires_at": "invalid-date"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_data = response.json()
        assert error_data["status"] == "fail"
        assert "data" in error_data

    def test_revoke_token(self, app_client, temp_db):
        """Test revoking a token"""
        import main
        import src.config as config

        db_manager, _ = temp_db
        main.db_manager = db_manager
        config.db_manager = db_manager

        # Create a token first
        create_response = app_client.post("/create-token", json={"username": "test", "password": "test"})
        token = create_response.json()["data"]["token"]

        # Revoke the token
        response = app_client.post(
            "/revoke-token",
            json={"username": "test", "password": "test", "token": token},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "message" in data["data"]
        assert "revoked" in data["data"]["message"].lower()

    def test_revoke_nonexistent_token(self, app_client, temp_db):
        """Test revoking a token that doesn't exist"""
        import main
        import src.config as config

        db_manager, _ = temp_db
        main.db_manager = db_manager
        config.db_manager = db_manager

        response = app_client.post(
            "/revoke-token",
            json={"username": "test", "password": "test", "token": "nonexistent_token"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_data = response.json()
        assert error_data["status"] == "fail"
        assert "data" in error_data

    def test_get_tokens(self, app_client, temp_db):
        """Test getting all active tokens"""
        import main
        import src.config as config

        db_manager, _ = temp_db
        main.db_manager = db_manager
        config.db_manager = db_manager

        # Create a few tokens
        tokens = []
        for _ in range(3):
            create_response = app_client.post("/create-token", json={"username": "test", "password": "test"})
            tokens.append(create_response.json()["data"]["token"])

        # Get all tokens
        response = app_client.post("/get-tokens", json={"username": "test", "password": "test"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "tokens" in data["data"]
        assert len(data["data"]["tokens"]) == 3

    def test_get_tokens_excludes_revoked(self, app_client, temp_db):
        """Test that revoked tokens are not returned"""
        import main
        import src.config as config

        db_manager, _ = temp_db
        main.db_manager = db_manager
        config.db_manager = db_manager

        # Create and revoke a token
        create_response = app_client.post("/create-token", json={"username": "test", "password": "test"})
        token = create_response.json()["data"]["token"]
        app_client.post(
            "/revoke-token",
            json={"username": "test", "password": "test", "token": token},
        )

        # Create another active token
        app_client.post("/create-token", json={"username": "test", "password": "test"})

        # Get all tokens - should only return active one
        response = app_client.post("/get-tokens", json={"username": "test", "password": "test"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert len(data["data"]["tokens"]) == 1


class TestRateLimiting:
    """Tests for rate limiting on endpoints"""

    def test_rate_limit_enforcement(self, app_client, db_manager_with_token):
        """Test that rate limiting is enforced"""
        from src.rate_limit import RateLimiter

        db_manager, _, token = db_manager_with_token
        update_db_manager_and_rate_limiter(db_manager)
        setup_mock_housing_model()

        # Reset rate limiter for testing with lower limit
        RateLimiter._instance = None
        RateLimiter(requests_per_minute=5, window_seconds=60, db_manager=db_manager)

        # Exhaust the rate limit
        sample_input = {
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

        # Make requests up to the limit
        for _ in range(5):
            response = app_client.post(
                "/predict",
                json=sample_input,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == status.HTTP_200_OK

        # Next request should be rate limited
        response = app_client.post("/predict", json=sample_input, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        error_data = response.json()
        assert error_data["status"] == "fail"
        assert "data" in error_data
        assert "Rate limit exceeded" in error_data["data"]["message"]

    def test_invalid_token(self, app_client, temp_db):
        """Test that invalid tokens are rejected"""
        db_manager, _ = temp_db
        update_db_manager_and_rate_limiter(db_manager)

        sample_input = {
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

        response = app_client.post(
            "/predict",
            json=sample_input,
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error_data = response.json()
        assert error_data["status"] == "fail"
        assert "data" in error_data

    def test_expired_token(self, app_client, temp_db):
        """Test that expired tokens are rejected"""
        from datetime import datetime, timedelta

        db_manager, _ = temp_db
        update_db_manager_and_rate_limiter(db_manager)

        # Create an expired token
        expires_at = datetime.now() - timedelta(days=1)
        db_manager.create_api_token("expired_token", expires_at)

        sample_input = {
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

        response = app_client.post(
            "/predict",
            json=sample_input,
            headers={"Authorization": "Bearer expired_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error_data = response.json()
        assert error_data["status"] == "fail"
        assert "data" in error_data


class TestRequestLogging:
    """Tests for request/response logging middleware"""

    def test_request_logging_middleware(self, app_client, db_manager_with_token):
        """Test that requests are logged"""
        db_manager, _, token = db_manager_with_token
        update_db_manager_and_rate_limiter(db_manager)
        setup_mock_housing_model()

        sample_input = {
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

        response = app_client.post("/predict", json=sample_input, headers={"Authorization": f"Bearer {token}"})

        # If we get here without errors, logging middleware is working
        assert response.status_code == status.HTTP_200_OK
