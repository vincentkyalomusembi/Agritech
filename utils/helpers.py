"""
Helper utilities for the Agritech application.
"""

# Soil type mapping by county (defaults)
REGION_SOIL = {
    "Makueni": "sandy",
    "Nyeri": "loamy",
    "Kitui": "sandy",
    "Kilifi": "sandy",
    "Nakuru": "loamy",
    "Embu": "clay",
    "Baringo": "sandy",
}


def get_default_soil(county: str) -> str:
    """
    Get default soil type for a county.
    
    Args:
        county: County name
        
    Returns:
        Soil type string
    """
    return REGION_SOIL.get(county.title(), "loamy")


def get_mock_weather(county: str) -> dict:
    """
    Generate mock weather data based on county name hash.
    For demo purposes only.
    
    Args:
        county: County name
        
    Returns:
        Dictionary with rainfall, temp, and conditions
    """
    base = sum(ord(c) for c in county) % 100
    rainfall = 200 + (base % 700)   # 200 - 900 mm
    temp = 18 + (base % 15)         # 18 - 32 C
    conditions = "rain" if rainfall > 500 else "dry"
    
    return {
        "rainfall": rainfall,
        "temp": temp,
        "conditions": conditions
    }
