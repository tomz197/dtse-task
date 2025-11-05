from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

from src.model import MODEL_NAME, HousingModel


class TestHousingModel:
    """Tests for HousingModel class"""

    @patch("src.model.joblib.load")
    @patch("src.model.pd.read_csv")
    def test_housing_model_initialization(self, mock_read_csv, mock_load):
        """Test HousingModel initialization"""
        # Mock the model
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        # Mock the CSV reading for expected features
        mock_df = pd.DataFrame(
            {
                "longitude": [-122.64],
                "latitude": [38.01],
                "housing_median_age": [36.0],
                "total_rooms": [1336.0],
                "total_bedrooms": [258.0],
                "population": [678.0],
                "households": [249.0],
                "median_income": [5.5789],
                "ocean_proximity": ["NEAR OCEAN"],
                "median_house_value": [320201.59],
            }
        )
        mock_read_csv.return_value = mock_df

        model = HousingModel(MODEL_NAME)

        assert model.model_path == MODEL_NAME
        assert model.model == mock_model
        assert len(model.expected_features) > 0

    @patch("src.model.joblib.load")
    @patch("src.model.pd.read_csv")
    def test_housing_model_predict(self, mock_read_csv, mock_load):
        """Test HousingModel predict method"""
        # Mock the model
        mock_model = MagicMock()
        mock_model.predict.return_value = [320201.59]
        mock_load.return_value = mock_model

        # Mock the CSV reading for expected features
        mock_df = pd.DataFrame(
            {
                "longitude": [-122.64],
                "latitude": [38.01],
                "housing_median_age": [36.0],
                "total_rooms": [1336.0],
                "total_bedrooms": [258.0],
                "population": [678.0],
                "households": [249.0],
                "median_income": [5.5789],
                "ocean_proximity": ["NEAR OCEAN"],
                "median_house_value": [320201.59],
            }
        )
        mock_read_csv.return_value = mock_df

        model = HousingModel(MODEL_NAME)

        # Create test input
        test_input = pd.DataFrame(
            {
                "longitude": [-122.64],
                "latitude": [38.01],
                "housing_median_age": [36.0],
                "total_rooms": [1336.0],
                "total_bedrooms": [258.0],
                "population": [678.0],
                "households": [249.0],
                "median_income": [5.5789],
                "ocean_proximity_<1H OCEAN": [0],
                "ocean_proximity_INLAND": [0],
                "ocean_proximity_ISLAND": [0],
                "ocean_proximity_NEAR BAY": [0],
                "ocean_proximity_NEAR OCEAN": [1],
            }
        )

        result = model.predict(test_input)

        assert len(result) == 1
        assert result[0] == pytest.approx(320201.59, abs=1)
        mock_model.predict.assert_called_once()

    @patch("src.model.joblib.load")
    @patch("src.model.pd.read_csv")
    def test_housing_model_load_expected_features(self, mock_read_csv, mock_load):
        """Test that expected features are loaded correctly"""
        # Mock the model
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        # Mock the CSV reading for expected features
        mock_df = pd.DataFrame(
            {
                "longitude": [-122.64],
                "latitude": [38.01],
                "housing_median_age": [36.0],
                "total_rooms": [1336.0],
                "total_bedrooms": [258.0],
                "population": [678.0],
                "households": [249.0],
                "median_income": [5.5789],
                "ocean_proximity": ["NEAR OCEAN"],
                "median_house_value": [320201.59],
            }
        )
        mock_read_csv.return_value = mock_df

        model = HousingModel(MODEL_NAME)

        # Verify expected features are set
        assert hasattr(model, "expected_features")
        assert isinstance(model.expected_features, list)
        assert len(model.expected_features) > 0
        assert "median_house_value" not in model.expected_features


class TestModelFunctions:
    """Tests for module-level functions"""

    @patch("src.model.pd.read_csv")
    def test_prepare_data(self, mock_read_csv):
        """Test prepare_data function"""
        from src.model import prepare_data

        # Create mock DataFrame
        mock_df = pd.DataFrame(
            {
                "longitude": [-122.64, -115.73],
                "latitude": [38.01, 33.35],
                "housing_median_age": [36.0, 23.0],
                "total_rooms": [1336.0, 1586.0],
                "total_bedrooms": [258.0, 448.0],
                "population": [678.0, 338.0],
                "households": [249.0, 182.0],
                "median_income": [5.5789, 1.2132],
                "ocean_proximity": ["NEAR OCEAN", "INLAND"],
                "median_house_value": [320201.59, 58815.45],
            }
        )
        mock_read_csv.return_value = mock_df

        X_train, X_test, y_train, y_test = prepare_data("dummy_path.csv")

        assert len(X_train) + len(X_test) == 2
        assert len(y_train) + len(y_test) == 2
        assert "median_house_value" not in X_train.columns
        assert "median_house_value" not in X_test.columns

    @patch("src.model.RandomForestRegressor")
    def test_train(self, mock_rf_class):
        """Test train function"""
        from src.model import train

        # Mock the regressor
        mock_regressor = MagicMock()
        mock_rf_class.return_value = mock_regressor

        # Create sample data
        X_train = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})
        y_train = [100, 200, 300]

        result = train(X_train, y_train)

        assert result == mock_regressor
        mock_regressor.fit.assert_called_once_with(X_train, y_train)

    def test_predict(self):
        """Test predict function"""
        from src.model import predict

        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = [100, 200, 300]

        # Create sample data
        X = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})

        result = predict(X, mock_model)

        assert len(result) == 3
        assert result[0] == pytest.approx(100, abs=1)
        mock_model.predict.assert_called_once_with(X)

    @patch("builtins.open", new_callable=mock_open)
    @patch("src.model.joblib.dump")
    def test_save_model(self, mock_dump, mock_file):
        """Test save_model function"""
        from src.model import save_model

        mock_model = MagicMock()
        save_model(mock_model, "test_model.joblib")

        mock_dump.assert_called_once()
        mock_file.assert_called_once_with("test_model.joblib", "wb")

    @patch("src.model.joblib.load")
    def test_load_model(self, mock_load):
        """Test load_model function"""
        from src.model import load_model

        mock_model = MagicMock()
        mock_load.return_value = mock_model

        result = load_model("test_model.joblib")

        assert result == mock_model
        mock_load.assert_called_once_with("test_model.joblib")
