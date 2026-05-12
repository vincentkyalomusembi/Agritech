from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from core.config import USER_SESSIONS, SEED_DATA
from services.weather import get_weather
from services.recommendation import get_county_recommendations, get_ai_recommendation

router = APIRouter()

@router.post("/ussd", response_class=PlainTextResponse)
async def ussd_callback(request: Request):
    """Handle USSD requests from Africa's Talking"""

    # Parse incoming data
    form_data = await request.form()
    phone_number = form_data.get("phoneNumber", "")
    text = form_data.get("text", "")

    # Initialize session if new user
    if phone_number not in USER_SESSIONS:
        USER_SESSIONS[phone_number] = {"state": "menu", "county": None, "farm_type": None}

    session = USER_SESSIONS[phone_number]
    response = ""

    # Main menu
    if text == "":
        response = "CON Welcome to Agritech AI\n"
        response += "1. Get Recommendation\n"
        response += "2. About Us"
        session["state"] = "menu"

    elif session["state"] == "menu":
        if text == "1":
            # Ask for county
            response = "CON Select your county:\n"
            counties = SEED_DATA["county"].unique() if not SEED_DATA.empty else []
            for i, county in enumerate(counties, 1):
                response += f"{i}. {county}\n"
            session["state"] = "county_select"
        
        elif text == "2":
            response = "CON Agritech AI - AI-powered farm advice\n"
            response += "Real-time recommendations powered by OpenWeather\n"
            response += "1. Back to Menu"
            session["state"] = "menu"
        
        else:
            response = "CON Invalid option. Try again:\n"
            response += "1. Get Recommendation\n"
            response += "2. About Us"
    
    elif session["state"] == "county_select":
        counties = SEED_DATA["county"].unique().tolist() if not SEED_DATA.empty else []
        try:
            # Extract the last part of the text for the current input
            current_input = text.split("*")[-1]
            county_index = int(current_input) - 1
            if 0 <= county_index < len(counties):
                selected_county = counties[county_index]
                session["county"] = selected_county
                
                # Ask for farm type
                response = "CON Select farm type:\n"
                response += "1. Crop\n"
                response += "2. Livestock"
                session["state"] = "farm_type_select"
            else:
                response = "CON Invalid county. Try again."
        except (ValueError, IndexError):
            response = "CON Invalid input. Select a county number."
    
    elif session["state"] == "farm_type_select":
        current_input = text.split("*")[-1]
        if current_input == "1":
            session["farm_type"] = "crop"
        elif current_input == "2":
            session["farm_type"] = "livestock"
        else:
            return "CON Invalid option. Select 1 or 2."
        
        # Get real-time weather and recommendation
        weather_data = get_weather(session["county"])
        county_data = get_county_recommendations(session["county"], session["farm_type"])
        recommendation = get_ai_recommendation(session["county"], weather_data, session["farm_type"])
        
        response = f"END 📍 County: {session['county']}\n"
        response += f"🌾 Type: {session['farm_type']}\n"
        
        if county_data:
            response += f"🌱 Soil: {county_data['soil_type']}\n"
            response += f"🌧️ Avg Rainfall: {county_data['avg_rainfall']}mm\n"
        
        if weather_data:
            response += f"\n🌡️ Current Temp: {weather_data['temp']}°C\n"
            response += f"💧 Humidity: {weather_data['humidity']}%\n"
        
        response += f"\n📋 Recommendation:\n{recommendation[:100]}..." # Keep it short for USSD
        session["state"] = "menu"
    
    return response
