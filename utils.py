# utils.py
import random

# Simple mapping for soil default by county (demo)
REGION_SOIL = {
    "Makueni": "sandy",
    "Nyeri": "loamy",
    "Kitui": "sandy",
    "Kilifi": "sandy",
    "Nakuru": "loamy",
    "Embu": "clay",
    "Baringo": "sandy",
}

def get_default_soil(county: str):
    return REGION_SOIL.get(county.title(), "loamy")

# Mock weather function: returns a short text and basic numeric values.
def get_mock_weather(county: str):
    # For demo, generate simple plausible numbers by county name hash
    base = sum(ord(c) for c in county) % 100
    rainfall = 200 + (base % 700)   # 200 - 900 mm
    temp = 18 + (base % 15)         # 18 - 32 C
    conditions = "rain" if rainfall > 500 else "dry"
    return {"rainfall": rainfall, "temp": temp, "conditions": conditions}