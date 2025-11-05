import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from src.logging_config import get_logger

logger = get_logger(__name__)

TRAIN_DATA = "data/housing.csv"
MODEL_NAME = "model.joblib"
RANDOM_STATE = 100


def prepare_data(input_data_path):
    logger.info(f"Loading and preparing data from {input_data_path}")
    df = pd.read_csv(input_data_path)
    logger.debug(f"Loaded {len(df)} rows from CSV")
    df = df.dropna()
    logger.debug(f"After dropping NA: {len(df)} rows")

    # encode the categorical variables
    df = pd.get_dummies(df)
    logger.debug(f"After encoding: {len(df.columns)} columns")

    df_features = df.drop(["median_house_value"], axis=1)
    y = df["median_house_value"].values

    X_train, X_test, y_train, y_test = train_test_split(
        df_features, y, test_size=0.2, random_state=RANDOM_STATE
    )
    logger.info(f"Split data: Train={len(X_train)}, Test={len(X_test)}")

    return (X_train, X_test, y_train, y_test)


def train(X_train, y_train):
    logger.info(f"Training RandomForestRegressor on {len(X_train)} samples")
    # what columns are expected by the model
    logger.debug(
        f"Model expects {len(X_train.columns)} features: {list(X_train.columns)}"
    )

    regr = RandomForestRegressor(max_depth=12)
    regr.fit(X_train, y_train)
    logger.info("Model training completed")

    return regr


def predict(X, model):
    logger.debug(f"Making predictions for {len(X)} samples")
    Y = model.predict(X)
    logger.debug(f"Predictions completed: {len(Y)} results")
    return Y


def save_model(model, filename):
    logger.info(f"Saving model to {filename}")
    with open(filename, "wb"):
        joblib.dump(model, filename, compress=3)
    logger.info("Model saved successfully")


def load_model(filename):
    logger.info(f"Loading model from {filename}")
    model = joblib.load(filename)
    logger.info("Model loaded successfully")
    return model


class HousingModel:
    def __init__(self, model_path=MODEL_NAME):
        self.model_path = model_path
        logger.info(f"Initializing HousingModel with model: {model_path}")
        self.model = load_model(model_path)
        self._load_expected_features()
        logger.info(
            f"HousingModel initialized with {len(self.expected_features)} expected features"
        )

    def _load_expected_features(self):
        logger.debug(f"Loading expected features from {TRAIN_DATA}")
        df = pd.read_csv(TRAIN_DATA)
        df = df.dropna()
        df = pd.get_dummies(df)
        df_features = df.drop(["median_house_value"], axis=1)
        self.expected_features = df_features.columns.tolist()
        logger.debug(f"Loaded {len(self.expected_features)} expected features")

    def predict(self, X):
        logger.debug(f"Predicting with HousingModel for {len(X)} samples")
        return predict(X, self.model)

    def train(self, X_train, y_train):
        logger.info("Training HousingModel")
        self.model = train(X_train, y_train)
        return self.model

    def save(self, filename=None):
        save_path = filename or self.model_path
        logger.info(f"Saving HousingModel to {save_path}")
        save_model(self.model, save_path)
