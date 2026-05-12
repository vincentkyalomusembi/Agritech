from core.config import SEED_DATA

def get_county_recommendations(county, farm_type="crop"):
    """Get recommendations from seed_data for a county"""
    if SEED_DATA.empty:
        return None
        
    county_data = SEED_DATA[SEED_DATA["county"].str.lower() == county.lower()]
    
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
