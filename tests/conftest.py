import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.database import DatabaseManager
from src.model import HousingModel
from src.rate_limit import RateLimiter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_housing.db")

    # Reset singleton instance
    DatabaseManager._instance = None

    db_manager = DatabaseManager(db_path)
    yield db_manager, db_path

    # Cleanup
    db_manager.close_connection()
    DatabaseManager._instance = None
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_token():
    """Generate a sample API token"""
    return "test_token_12345678901234567890123456789012"


@pytest.fixture
def db_manager_with_token(temp_db):
    """Create a database manager with a test token"""
    db_manager, db_path = temp_db
    token = "test_token_12345678901234567890123456789012"
    db_manager.create_api_token(token, None)
    return db_manager, db_path, token


@pytest.fixture
def mock_housing_model(monkeypatch):
    """Mock the HousingModel for testing"""
    from unittest.mock import MagicMock

    import pandas as pd

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
        # Return a simple prediction based on median_income
        return df["median_income"].values * 100000

    model.predict = mock_predict

    # Monkeypatch the model loading
    def mock_init(self, model_path="model.joblib"):
        self.model_path = model_path
        self.model = model
        self.expected_features = model.expected_features

    monkeypatch.setattr(HousingModel, "__init__", mock_init)

    return model


@pytest.fixture
def rate_limiter(temp_db):
    """Create a rate limiter instance for testing"""
    db_manager, _ = temp_db
    # Reset singleton instance
    RateLimiter._instance = None
    rate_limiter = RateLimiter(
        requests_per_minute=10, window_seconds=60, db_manager=db_manager
    )
    yield rate_limiter
    RateLimiter._instance = None


@pytest.fixture
def app_client(mock_housing_model, temp_db, monkeypatch):
    """Create a test client for the FastAPI app"""
    import main
    from main import app
    import src.config as config

    # Set up test fixtures
    db_manager, _ = temp_db
    # Update config module (used by endpoints) instead of main module
    config.housing_model = mock_housing_model
    config.db_manager = db_manager
    # Also update main module for compatibility
    main.housing_model = mock_housing_model
    main.db_manager = db_manager

    # Mock verify_admin_credentials to bypass authentication in tests
    def mock_verify_admin_credentials(username, password):
        return username
    
    monkeypatch.setattr("src.auth.verify_admin_credentials", mock_verify_admin_credentials)
    monkeypatch.setattr("src.endpoints.tokens.verify_admin_credentials", mock_verify_admin_credentials)

    # Initialize rate limiter with test db_manager
    from src.rate_limit import RateLimiter

    RateLimiter._instance = None
    RateLimiter(requests_per_minute=100, window_seconds=60, db_manager=db_manager)

    client = TestClient(app)
    return client


@pytest.fixture
def sample_housing_input():
    """Sample housing input data"""
    return {
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
