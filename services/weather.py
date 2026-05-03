import os

import requests
from dotenv import load_dotenv


load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def get_mock_weather(county: str):
    county = (county or "").strip().title()
    base = sum(ord(char) for char in county) % 100 if county else 0
    return {
        "temp": 18 + (base % 15),
        "condition": "Sunny (Mocked)" if base % 2 == 0 else "Partly Cloudy (Mocked)",
    }


def get_weather(county: str):
    if not OPENWEATHER_API_KEY:
        return get_mock_weather(county)

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather?q={county},KE"
            f"&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": data["main"]["temp"],
                "condition": data["weather"][0]["description"],
            }
    except Exception:
        pass

    return get_mock_weather(county)