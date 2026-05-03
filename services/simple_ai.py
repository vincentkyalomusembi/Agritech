"""Legacy simple_ai moved into services for compatibility.

This is a copy of the original `simple_ai.py` preserved under `services/`.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print(f"Weather API Key: {'✓' if OPENWEATHER_API_KEY else '✗'}")
print(f"Gemini API Key: {'✓' if GEMINI_API_KEY else '✗'}")

# Load mock data (root fallback)
_ROOT = os.path.dirname(os.path.dirname(__file__))
mock_path = os.path.join(_ROOT, 'mock_data.json')
if not os.path.exists(mock_path):
    mock_path = os.path.join(_ROOT, 'data', 'mock_data.json')

with open(mock_path, 'r') as f:
    mock_data = json.load(f)

def get_weather(county):
    if not OPENWEATHER_API_KEY:
        print("Using mock weather data")
        return {"temp": 25, "condition": "Sunny (Mocked)"}
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={county},KE&appid={OPENWEATHER_API_KEY}&units=metric"
        print(f"Calling weather API for {county}...")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result = {
                "temp": data["main"]["temp"],
                "condition": data["weather"][0]["description"]
            }
            print(f"Weather API success: {result}")
            return result
        else:
            print(f"Weather API error: {response.status_code}")
            return {"temp": 25, "condition": "API Error"}
    except Exception as e:
        print(f"Weather API failed: {e}")
        return {"temp": 25, "condition": "Connection Failed"}

def get_recommendation(county, farm_type, soil_type=None):
    county = county.title()
    weather = get_weather(county)
    region_data = mock_data['regions'].get(county, {
        "soil": "loamy",
        "weather": "mild",
        "crop_recommendation": "maize",
        "livestock_recommendation": "chicken"
    })
    if farm_type.lower() in ["animal", "livestock"]:
        recommendation = region_data["livestock_recommendation"]
    else:
        recommendation = region_data["crop_recommendation"]
    advice = generate_ai_advice(county, soil_type or region_data["soil"], weather, recommendation)
    return {
        "county": county,
        "soil": soil_type or region_data["soil"],
        "farm_type": farm_type,
        "recommendation": recommendation,
        "advice": advice,
        "weather": weather
    }

def generate_ai_advice(county, soil, weather, crop):
    if not GEMINI_API_KEY:
        print("Using fallback advice")
        return f"Based on {county} with {soil} soil and {weather['condition']} weather ({weather['temp']}°C), {crop} is recommended."
    try:
        import urllib.request
        import urllib.parse
        prompt = f"In 2 sentences, explain why {crop} is suitable for farming in {county}, Kenya with {soil} soil and {weather['condition']} weather at {weather['temp']}°C."
        print(f"Would call Gemini API with: {prompt[:50]}...")
        return f"🌾 {crop.title()} thrives in {county}'s {soil} soil, especially with current {weather['condition']} conditions at {weather['temp']}°C. This combination provides optimal growing conditions for maximum yield."
    except Exception as e:
        print(f"Gemini API failed: {e}")
        return f"Based on {county} with {soil} soil, {crop} is recommended for current weather conditions."
