"""
Fetches real time weather from Openweather API
Falls back to to deterministc mock data on timeout, missing  key or any error
"""

import requests
from core.config import settings

#mock fallback
def get_mock_weather(county: str) ->dict:
    """Returns realistic hardcoded weather for Kenyan counties."""
    
    county = (county or "").strip().title()
    base = sum(ord(c) for c in county) % 100 if county else 0
    temp = 18 + (base % 15)
    humidity = 45 + (base % 35)
    rainfall = 200 + (base % 700)
    condition = "Sunny" if base % 2==0 else "Partly cloudy"

    return {
        "temp": temp,
        "humidity": humidity,
        "rainfall" : rainfall,
        "condition": f"{condition} (mock)",
        "wind_speed": round(1.5 + (base % 40) / 10.0, 1),
        "source": "mock",
    }

#live data
def get_weather(county:str) -> dict:
    """Returns a dict with keys:
        temp (°C), humidity (%), rainfall (mm/hr), condition (str),
        wind_speed (m/s), source ('openweather' | 'mock')
    """
    if not settings.OPENWEATHER_API_KEY:
        return get_mock_weather(county)

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={county},KE"
            f"&appid={settings.OPENWEATHER_API_KEY}"
            f"&units=metric"
        )

        response = requests.get(url, timeout=settings.WEATHER_TIMEOUT_SECS)

        if response.status_code == 200:
            data = response.json()
            main = data.get("main", {})
            wind = data.get("wind", {})
            weather_desc = (data.get("weather") or [{}])[0]

            return {
                "temp": main.get("temp"),
                "humidity":main.get("humidity"),
                "rainfall":data.get("rain", {}).get("1h", 0),
                "condition": weather_desc.get("description", "unknown"),
                "wind_speed": wind.get("speed"),
                "source": "openweather",
            }
        
        #Non-200 (county not found)
        return get_mock_weather(county)

    except (requests.timeout, requests.ConnectionError, requests.ReadTimeout):
        return get_mock_weather(county)
    except Exception:
        return get_mock_weather(county)