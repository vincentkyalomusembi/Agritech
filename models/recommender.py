"""
models/recommender.py
Loads seed_data.csv and produces crop/livestock recommendations.

Recommendation strategy (two-layer):
  1. ML model (DecisionTreeClassifier) predicts based on rainfall, temp,
     soil type, and farm type — this is the primary signal.
  2. CSV county data supplies soil_type and avg_rainfall for the response
     payload and as fallback if the model isn't available.
  3. Weather notes layer applies real-time advice on top of the prediction.

Phase 1 note: county data will move from CSV -> Supabase county_profiles table.
Function signatures stay the same so routes don't need to change.
"""

import pandas as pd
from functools import lru_cache
from core.config import settings
from models.ai_model import load_model, predict


# -- Model loading (once per process) -----------------------------------------

@lru_cache(maxsize=1)
def _get_model_bundle() -> dict:
    """
    Load (or auto-train) the model bundle once per process lifetime.
    lru_cache ensures we don't hit disk on every request.
    """
    return load_model()


# -- Data loading --------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_seed_data() -> pd.DataFrame:
    """
    Load seed_data.csv once and cache it for the process lifetime.
    """
    return pd.read_csv(settings.SEED_DATA_PATH)


def get_seed_data() -> pd.DataFrame:
    return _load_seed_data()


# -- County lookup -------------------------------------------------------------

def get_county_data(county: str, farm_type: str = "crop") -> dict | None:
    """
    Returns the best matching row for (county, farm_type) from seed data.
    Provides soil_type, avg_rainfall, avg_temp as ML model inputs.
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
        "avg_rainfall": int(row["avg_rainfall"]),
        "avg_temp": float(row["avg_temp"]),
        "farm_type": row["farm_type"],
        "csv_recommendation": row["recommendation"],
    }


def list_counties() -> list[str]:
    """Returns all counties present in seed data."""
    return get_seed_data()["county"].unique().tolist()


# -- Recommendation logic ------------------------------------------------------

def build_recommendation(county: str, farm_type: str, weather: dict | None) -> dict | None:
    """
    Produces a recommendation by combining ML prediction + county data + weather.

    Prediction priority:
      - Uses live weather temp when available
      - Falls back to county avg_temp / avg_rainfall from seed data
      - ML model predicts based on these features + soil + farm type
      - weather_notes adds real-time advisory on top

    Returns:
        {
            "county":            str,
            "farm_type":         str,
            "soil_type":         str,
            "avg_rainfall":      int,
            "recommendation":    str,   <- from ML model (or CSV fallback)
            "weather_notes":     list[str],
            "weather":           dict | None,
            "prediction_source": "model" | "csv",
        }
    Returns None if county is not in seed data.
    """
    county_data = get_county_data(county, farm_type)
    if not county_data:
        return None

    # Choose features: live weather temp > county averages
    temp = (
        weather.get("temp")
        if weather and weather.get("temp") is not None
        else county_data["avg_temp"]
    )
    # Use county avg_rainfall for the model (live hourly rainfall != annual avg)
    rainfall = county_data["avg_rainfall"]

    # ML prediction
    prediction_source = "csv"
    recommendation = county_data["csv_recommendation"]

    try:
        bundle = _get_model_bundle()
        recommendation = predict(
            bundle=bundle,
            avg_rainfall=rainfall,
            avg_temp=temp,
            soil_type=county_data["soil_type"],
            farm_type=farm_type,
        )
        prediction_source = "model"
    except Exception as e:
        print(f"[recommender] ML prediction failed, using CSV fallback: {e}")

    return {
        "county": county_data["county"],
        "farm_type": farm_type,
        "soil_type": county_data["soil_type"],
        "avg_rainfall": county_data["avg_rainfall"],
        "recommendation": recommendation,
        "weather_notes": _weather_notes(weather),
        "weather": weather,
        "prediction_source": prediction_source,
    }


# -- Weather advisory notes ----------------------------------------------------

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

    if humidity is not None:
        if humidity > 80 and "rain" in condition:
            notes.append("High rainfall: watch for fungal diseases. Ensure drainage.")
        elif humidity < 40:
            notes.append("Low humidity: increase irrigation frequency.")

    return notes