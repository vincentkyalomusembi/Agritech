import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
import os

MODEL_PATH = "decision_tree.pkl"
DATA_PATH = "seed_data.csv"

def train_and_save():
    df = pd.read_csv("C:/Users/user/Desktop/Agritech/seed_data.csv")
    # Simple feature engineering
    df['soil_enc'] = LabelEncoder().fit_transform(df['soil_type'])
    df['farm_enc'] = LabelEncoder().fit_transform(df['farm_type'])
    X = df[['avg_rainfall','avg_temp','soil_enc','farm_enc']]
    y = df['recommendation']
    model = DecisionTreeClassifier(max_depth=5)
    model.fit(X, y)
    # save encoders + model; for simplicity, save model and reconstruct encoders at runtime using small maps
    joblib.dump(model, MODEL_PATH)
    print("Model trained and saved to", MODEL_PATH)
    return model

def load_model():
    if not os.path.exists(MODEL_PATH):
        return train_and_save()
    return joblib.load(MODEL_PATH)

if __name__ == "__main__":
    train_and_save()