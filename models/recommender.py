"""
models/recommender.py
Loads seed_data.csv and produces crop/livestock recommendations.
Combines static county data with live weather adjustments.

Phase 1 note: county data will move from CSV → Supabase county_profiles table.
The function signatures stay the same so routes don't need to change.
"""

import pandas as pd
from functools import lru_cache
from core.config import settings


# ── Data loading ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_seed_data() -> pd.DataFrame:
    """
    Load seed_data.csv once and cache it for the process lifetime.
    lru_cache means the CSV is read once on first call, not on every request.
    """
    return pd.read_csv(settings.SEED_DATA_PATH)


def get_seed_data() -> pd.DataFrame:
    return _load_seed_data()


# ── County lookup ─────────────────────────────────────────────────────────────

def get_county_data(county: str, farm_type: str = "crop") -> dict | None:
    """
    Returns the best matching row for (county, farm_type) from seed data.
    Falls back to the first county row if no farm_type match found.
    Returns None if county not in seed data at all.
    """
    df = get_seed_data()
    county_rows = df[df["county"].str.lower() == county.lower()]

    if county_rows.empty:
        return None

    farm_rows = county_rows[county_rows["farm_type"] == farm_type]
    row = farm_rows.iloc[0] if not farm_rows.empty else county_rows.iloc[0]

    return {
        "county": row["county"],
        "soil_type": row["soil_type"],
        "avg_rainfall": row["avg_rainfall"],
        "avg_temp": row["avg_temp"],
        "farm_type": row["farm_type"],
        "recommendation": row["recommendation"],
    }


def list_counties() -> list[str]:
    """Returns all counties present in seed data."""
    return get_seed_data()["county"].unique().tolist()


# ── Recommendation logic ──────────────────────────────────────────────────────

def build_recommendation(county: str, farm_type: str, weather: dict | None) -> dict:
    """
    Combines static seed data with real-time weather to produce a recommendation.

    Returns:
        {
            "county": str,
            "farm_type": str,
            "soil_type": str,
            "avg_rainfall": int,
            "recommendation": str,
            "weather_notes": list[str],   ← weather-driven advice appended here
            "weather": dict | None,
        }
    Returns None if county is not in seed data.
    """
    county_data = get_county_data(county, farm_type)
    if not county_data:
        return None

    weather_notes = _weather_notes(weather)

    return {
        "county": county_data["county"],
        "farm_type": farm_type,
        "soil_type": county_data["soil_type"],
        "avg_rainfall": county_data["avg_rainfall"],
        "recommendation": county_data["recommendation"],
        "weather_notes": weather_notes,
        "weather": weather,
    }


def _weather_notes(weather: dict | None) -> list[str]:
    """Derive actionable weather advice from current conditions."""
    if not weather:
        return []

    notes = []
    temp = weather.get("temp")
    humidity = weather.get("humidity")
    condition = (weather.get("condition") or "").lower()

    if temp is not None:
        if temp < 15:
            notes.append("Cold weather: prioritise frost-resistant crops like potatoes.")
        elif temp > 30:
            notes.append("Hot weather: use drought-resistant varieties. Ensure irrigation.")

    if humidity is not None and condition:
        if humidity > 80 and "rain" in condition:
            notes.append("High rainfall: watch for fungal diseases. Ensure drainage.")
        elif humidity < 40:
            notes.append("Low humidity: increase irrigation frequency.")

    return notes