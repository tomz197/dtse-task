import sys
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import joblib
import logging

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

TRAIN_DATA = 'data/housing.csv'
MODEL_NAME = 'model.joblib'
RANDOM_STATE=100

def prepare_data(input_data_path):
    df=pd.read_csv(input_data_path)
    df=df.dropna() 

    # encode the categorical variables
    df = pd.get_dummies(df)

    df_features=df.drop(['median_house_value'],axis=1)
    y=df['median_house_value'].values

    X_train, X_test, y_train, y_test = train_test_split(df_features, y, test_size=0.2, random_state=RANDOM_STATE)

    return (X_train, X_test, y_train, y_test)

def train(X_train, y_train):
    # what columns are expected by the model
    X_train.columns

    regr = RandomForestRegressor(max_depth=12)
    regr.fit(X_train,y_train)

    return regr

def predict(X, model):
    Y = model.predict(X)
    return Y

def save_model(model, filename):
    with open(filename, 'wb'):
        joblib.dump(model, filename, compress=3)

def load_model(filename):
    model = joblib.load(filename)
    return model

class HousingModel:
    def __init__(self, model_path=MODEL_NAME):
        self.model_path = model_path
        self.model = load_model(model_path)
        self._load_expected_features()

    def _load_expected_features(self):
        df = pd.read_csv(TRAIN_DATA)
        df = df.dropna()
        df = pd.get_dummies(df)
        df_features = df.drop(['median_house_value'], axis=1)
        self.expected_features = df_features.columns.tolist()

    def predict(self, X):
        return predict(X, self.model)

    def train(self, X_train, y_train):
        self.model = train(X_train, y_train)
        return self.model

    def save(self, filename=None):
        save_model(self.model, filename or self.model_path)
