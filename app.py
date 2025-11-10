from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import json
import os
import requests
import pandas as pd

load_dotenv()

app = FastAPI()

# Load API keys
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Load seed data from CSV
def load_seed_data():
    df = pd.read_csv("seed_data.csv")
    # Group by county for easy lookup
    return df

seed_data = load_seed_data()

# Store user sessions
user_sessions = {}

def get_weather(region):
    """Fetch real-time weather data from OpenWeather API"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={region}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": round(data["main"]["temp"]),
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["main"].lower(),
                "rainfall": data.get("rain", {}).get("1h", 0)
            }
    except Exception as e:
        print(f"Weather API error: {e}")
    
    return None

def get_county_recommendations(county, farm_type="crop"):
    """Get recommendations from seed_data.csv for a county"""
    county_data = seed_data[seed_data["county"].str.lower() == county.lower()]
    
    if county_data.empty:
        return None
    
    # Filter by farm type
    farm_data = county_data[county_data["farm_type"] == farm_type]
    
    if farm_data.empty:
        farm_data = county_data.iloc[0]  # Default to first entry
    else:
        farm_data = farm_data.iloc[0]
    
    return {
        "soil_type": farm_data["soil_type"],
        "avg_rainfall": farm_data["avg_rainfall"],
        "avg_temp": farm_data["avg_temp"],
        "recommendation": farm_data["recommendation"]
    }

def get_ai_recommendation(county, weather_data, farm_type="crop"):
    """Generate AI recommendations based on county data and real-time weather"""
    
    county_data = get_county_recommendations(county, farm_type)
    
    if not county_data:
        return "No data available for this county."
    
    base_rec = county_data["recommendation"]
    soil = county_data["soil_type"]
    avg_temp = county_data["avg_temp"]
    
    # Enhance with weather-based logic
    if weather_data:
        temp = weather_data["temp"]
        humidity = weather_data["humidity"]
        description = weather_data["description"]
        
        if temp < 15:
            base_rec += "\n⚠️ Cold weather: Prioritize frost-resistant crops like potatoes."
        elif temp > 30:
            base_rec += "\n⚠️ Hot weather: Use drought-resistant crops. Ensure irrigation."
        
        if humidity > 80 and "rain" in description:
            base_rec += "\n💧 High rainfall detected: Watch for crop diseases. Ensure proper drainage."
        elif humidity < 40:
            base_rec += "\n🌱 Low humidity: Increase irrigation frequency."
    
    return base_rec

@app.post("/ussd", response_class=PlainTextResponse)
async def ussd_callback(request: Request):
    """Handle USSD requests from Africa's Talking"""

    # Parse incoming data
    form_data = await request.form()
    phone_number = form_data.get("phoneNumber", "")
    text = form_data.get("text", "")
    session_id = form_data.get("sessionId", "")

    # Initialize session if new user
    if phone_number not in user_sessions:
        user_sessions[phone_number] = {"state": "menu", "county": None, "farm_type": None}

    session = user_sessions[phone_number]
    response = ""

    # Main menu
    if text == "":
        response = "Welcome to Agritech AI\n"
        response += "1. Get Recommendation\n"
        response += "2. About Us"
        session["state"] = "menu"

    elif session["state"] == "menu":
        if text == "1":
            # Ask for county
            response = "Select your county:\n"
            counties = seed_data["county"].unique()
            for i, county in enumerate(counties, 1):
                response += f"{i}. {county}\n"
            session["state"] = "county_select"
        
        elif text == "2":
            response = "Agritech AI - AI-powered farm advice\n"
            response += "Real-time recommendations powered by OpenWeather\n"
            response += "1. Back to Menu"
            session["state"] = "menu"
        
        else:
            response = "Invalid option. Try again:\n"
            response += "1. Get Recommendation\n"
            response += "2. About Us"
    
    elif session["state"] == "county_select":
        counties = seed_data["county"].unique().tolist()
        try:
            county_index = int(text) - 1
            if 0 <= county_index < len(counties):
                selected_county = counties[county_index]
                session["county"] = selected_county
                
                # Ask for farm type
                response = "Select farm type:\n"
                response += "1. Crop\n"
                response += "2. Livestock"
                session["state"] = "farm_type_select"
            else:
                response = "Invalid county. Try again."
        except ValueError:
            response = "Invalid input. Select a county number."
    
    elif session["state"] == "farm_type_select":
        if text == "1":
            session["farm_type"] = "crop"
        elif text == "2":
            session["farm_type"] = "livestock"
        else:
            response = "Invalid option. Select 1 or 2."
            return response
        
        # Get real-time weather and recommendation
        weather_data = get_weather(session["county"])
        county_data = get_county_recommendations(session["county"], session["farm_type"])
        recommendation = get_ai_recommendation(session["county"], weather_data, session["farm_type"])
        
        response = f"📍 County: {session['county']}\n"
        response += f"🌾 Type: {session['farm_type']}\n"
        
        if county_data:
            response += f"🌱 Soil: {county_data['soil_type']}\n"
            response += f"🌧️ Avg Rainfall: {county_data['avg_rainfall']}mm\n"
        
        if weather_data:
            response += f"\n🌡️ Current Temp: {weather_data['temp']}°C\n"
            response += f"💧 Humidity: {weather_data['humidity']}%\n"
        
        response += f"\n📋 Recommendation:\n{recommendation}\n\n"
        response += "1. Back to Menu"
        session["state"] = "menu"
    
    return response

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "Agritech AI Backend Running", "version": "1.0"}

@app.get("/health")
async def health():
    """Health check for deployment"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)