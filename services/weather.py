import os

import requests
from dotenv import load_dotenv


load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def get_mock_weather(county: str):
    county = (county or "").strip().title()
    base = sum(ord(char) for char in county) % 100 if county else 0
    temp = 18 + (base % 15)
    return {
        "temp": temp,
        "feels_like": temp + 1,
        "humidity": 45 + (base % 35),
        "pressure": 1000 + (base % 25),
        "wind_speed": round(1.5 + (base % 40) / 10.0, 1),
        "clouds": base % 100,
        "condition": "Sunny (Mocked)" if base % 2 == 0 else "Partly Cloudy (Mocked)",
        "source": "mock",
    }


def get_weather(county: str, timeout_secs: int = 2):
    """Fetch weather with short timeout for USSD performance. Falls back to mock on timeout."""
    if not OPENWEATHER_API_KEY:
        return get_mock_weather(county)

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather?q={county},KE"
            f"&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        response = requests.get(url, timeout=timeout_secs)
        if response.status_code == 200:
            data = response.json()
            main = data.get("main", {})
            wind = data.get("wind", {})
            clouds = data.get("clouds", {})
            weather = (data.get("weather") or [{}])[0]
            return {
                "temp": main.get("temp"),
                "feels_like": main.get("feels_like"),
                "humidity": main.get("humidity"),
                "pressure": main.get("pressure"),
                "wind_speed": wind.get("speed"),
                "clouds": clouds.get("all"),
                "condition": weather.get("description", "unknown"),
                "source": "openweather",
            }
    except (requests.Timeout, requests.ConnectionError, requests.ReadTimeout):
        # Timeout on weather API: use mock
        return get_mock_weather(county)
    except Exception:
        # Any error: fallback to mock
        return get_mock_weather(county)