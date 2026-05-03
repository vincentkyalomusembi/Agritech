"""Legacy ML model module moved into services."""
import os
import requests
import pickle
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print(f"DEBUG: Loaded OPENWEATHER_API_KEY: {OPENWEATHER_API_KEY[:10] if OPENWEATHER_API_KEY else 'None'}...")
print(f"DEBUG: Loaded GEMINI_API_KEY: {GEMINI_API_KEY[:10] if GEMINI_API_KEY else 'None'}...")

def train_model():
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'seed_data.csv')
    data = pd.read_csv(data_path)
    X = data[['county', 'soil_type', 'farm_type']]
    y = data['recommendation']
    X_encoded = pd.get_dummies(X)
    model = DecisionTreeClassifier()
    model.fit(X_encoded, y)
    model_path = os.path.join(os.path.dirname(__file__), '..', 'model.pkl')
    pickle.dump((model, X_encoded.columns), open('model.pkl', 'wb'))
    return model, X_encoded.columns

def load_model():
    try:
        model, cols = pickle.load(open('model.pkl', 'rb'))
        return model
    except:
        model, cols = train_model()
        return model

try:
    model, cols = pickle.load(open('model.pkl', 'rb'))
except:
    model, cols = train_model()

def get_weather(county):
    if not OPENWEATHER_API_KEY:
        return {"temp": 25, "condition": "Sunny (Mocked)"}
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={county},KE&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=5)
        data = response.json()
        return {"temp": data["main"]["temp"], "condition": data["weather"][0]["description"]}
    except Exception as e:
        return {"temp": 25, "condition": "Unavailable"}

def predict_crop(county, soil, farm_type='crop'):
    farm_type_mapped = 'livestock' if farm_type in ['animal', 'livestock'] else 'crop'
    df = pd.DataFrame([[county, soil, farm_type_mapped]], columns=['county', 'soil_type', 'farm_type'])
    df = pd.get_dummies(df)
    df = df.reindex(columns=cols, fill_value=0)
    return model.predict(df)[0]

def generate_ai_advice(county, soil, weather, crop):
    if not GEMINI_API_KEY:
        return f"Based on your region ({county}), {soil} soil, and weather ({weather['condition']}), {crop} is most suitable this season."
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        prompt = f"Explain in 2 lines why {crop} is suitable for {county} with {soil} soil and {weather['condition']} weather."
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return f"Based on {county} and {soil} soil, {crop} is recommended (AI offline)."
