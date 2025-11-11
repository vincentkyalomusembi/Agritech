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

# Load model or train quickly if missing
def train_model():
    data = pd.read_csv('seed_data.csv')
    X = data[['county', 'soil_type', 'farm_type']]
    y = data['recommendation']

    X_encoded = pd.get_dummies(X)
    model = DecisionTreeClassifier()
    model.fit(X_encoded, y)

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

# Function to get weather data (mock fallback)
def get_weather(county):
    print(f"DEBUG: OPENWEATHER_API_KEY exists: {bool(OPENWEATHER_API_KEY)}")
    if not OPENWEATHER_API_KEY:
        return {"temp": 25, "condition": "Sunny (Mocked)"}

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={county},KE&appid={OPENWEATHER_API_KEY}&units=metric"
        print(f"DEBUG: Making weather API call to: {url[:50]}...")
        response = requests.get(url, timeout=5)
        print(f"DEBUG: Weather API response status: {response.status_code}")
        data = response.json()
        result = {
            "temp": data["main"]["temp"],
            "condition": data["weather"][0]["description"]
        }
        print(f"DEBUG: Weather API success: {result}")
        return result
    except Exception as e:
        print(f"DEBUG: Weather API failed: {e}")
        return {"temp": 25, "condition": "Unavailable"}

# Predict using local ML model
def predict_crop(county, soil, farm_type='crop'):
    # Map farm_type to match training data
    farm_type_mapped = 'livestock' if farm_type in ['animal', 'livestock'] else 'crop'
    df = pd.DataFrame([[county, soil, farm_type_mapped]], columns=['county', 'soil_type', 'farm_type'])
    df = pd.get_dummies(df)
    df = df.reindex(columns=cols, fill_value=0)
    return model.predict(df)[0]

# Optional: Generate AI-like explanation using Gemini
def generate_ai_advice(county, soil, weather, crop):
    print(f"DEBUG: GEMINI_API_KEY exists: {bool(GEMINI_API_KEY)}")
    if not GEMINI_API_KEY:
        return f"Based on your region ({county}), {soil} soil, and weather ({weather['condition']}), {crop} is most suitable this season."
    try:
        import google.generativeai as genai
        print("DEBUG: Configuring Gemini API...")
        genai.configure(api_key=GEMINI_API_KEY)
        prompt = f"Explain in 2 lines why {crop} is suitable for {county} with {soil} soil and {weather['condition']} weather."
        print(f"DEBUG: Gemini prompt: {prompt}")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        result = response.text.strip()
        print(f"DEBUG: Gemini API success: {result[:50]}...")
        return result
    except Exception as e:
        print(f"DEBUG: Gemini API failed: {e}")
        return f"Based on {county} and {soil} soil, {crop} is recommended (AI offline)."