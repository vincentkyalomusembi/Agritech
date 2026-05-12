import requests
from core.config import OPENWEATHER_API_KEY

def get_weather(region):
    """Fetch real-time weather data from OpenWeather API"""
    if not OPENWEATHER_API_KEY:
        return None
        
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
