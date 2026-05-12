"""
models/recommender.py
Loads county data and produces crop/livestock recommendations.

Data source (two-layer, progressive)
--------------------------------------
  Layer 1 — Supabase county_profiles table (all 47 counties, live).
             Queried via db.county_profiles module.
  Layer 2 — CSV fallback (data/seed_data.csv, 8 counties).
             Used automatically if Supabase is unavailable or county is
             not in the remote table (dev / offline mode).

Recommendation strategy (two-layer)
--------------------------------------
  1. ML model (DecisionTreeClassifier) predicts based on rainfall, temp,
     soil type, and farm type — this is the primary signal.
  2. county_profiles supplies soil_type and avg_rainfall for the response
     payload and as fallback if the model isn't available.
  3. Weather notes layer applies real-time advice on top of the prediction.

Function signatures are unchanged from the CSV version — routes don't change.
"""

import pandas as pd
from functools import lru_cache

from core.config import settings
from models.ai_model import load_model, predict


# ── Model loading (once per process) ─────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_model_bundle() -> dict:
    """Load (or auto-train) the model bundle once per process lifetime."""
    return load_model()


# ── County data — Supabase + CSV fallback ─────────────────────────────────────

def _supabase_get_county(county: str, farm_type: str) -> dict | None:
    """
    Query county_profiles from Supabase.
    Returns None on any error (network, missing creds, missing row).
    """
    try:
        from supabase import create_client  # type: ignore

        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            return None

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        res = (
            client
            .table("county_profiles")
            .select("county,soil_type,avg_rainfall,avg_temp,farm_type,recommendation")
            .eq("county", county)
            .eq("farm_type", farm_type)
            .limit(1)
            .execute()
        )
        if res.data:
            r = res.data[0]
            return {
                "county":              r["county"],
                "soil_type":           r["soil_type"],
                "avg_rainfall":        int(r["avg_rainfall"]),
                "avg_temp":            float(r["avg_temp"]),
                "elevation_m":         int(r.get("elevation_m") or 1000),
                "irrigation":          int(r.get("irrigation") or 0),
                "market_price_index":  int(r.get("market_price_index") or 3),
                "farm_type":           r["farm_type"],
                "csv_recommendation":  r["recommendation"],
                "source":              "supabase",
            }
    except Exception as exc:
        print(f"[recommender] Supabase county lookup failed: {exc}")

    return None


def _supabase_list_counties() -> list[str] | None:
    """Returns distinct county names from Supabase, or None on failure."""
    try:
        from supabase import create_client  # type: ignore

        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            return None

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        res = (
            client
            .table("county_profiles")
            .select("county")
            .execute()
        )
        if res.data:
            seen = set()
            return [
                r["county"] for r in res.data
                if not (r["county"] in seen or seen.add(r["county"]))
            ]
    except Exception as exc:
        print(f"[recommender] Supabase list_counties failed: {exc}")

    return None


# ── CSV fallback ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_seed_data() -> pd.DataFrame:
    """Load seed_data.csv once and cache it."""
    return pd.read_csv(settings.SEED_DATA_PATH)


def _csv_get_county(county: str, farm_type: str) -> dict | None:
    df = _load_seed_data()
    county_rows = df[df["county"].str.lower() == county.lower()]
    if county_rows.empty:
        return None

    farm_rows = county_rows[county_rows["farm_type"] == farm_type]
    row = farm_rows.iloc[0] if not farm_rows.empty else county_rows.iloc[0]

    return {
        "county":              row["county"],
        "soil_type":           row["soil_type"],
        "avg_rainfall":        int(row["avg_rainfall"]),
        "avg_temp":            float(row["avg_temp"]),
        "elevation_m":         int(row["elevation_m"]) if "elevation_m" in row else 1000,
        "irrigation":          int(row["irrigation"]) if "irrigation" in row else 0,
        "market_price_index":  int(row["market_price_index"]) if "market_price_index" in row else 3,
        "farm_type":           row["farm_type"],
        "csv_recommendation":  row["recommendation"],
        "source":              "csv",
    }


def _csv_list_counties() -> list[str]:
    return _load_seed_data()["county"].unique().tolist()


# ── Public API ────────────────────────────────────────────────────────────────

# Keep get_seed_data() for backwards-compat (used by training scripts)
def get_seed_data() -> pd.DataFrame:
    return _load_seed_data()


def get_county_data(county: str, farm_type: str = "crop") -> dict | None:
    """
    Returns the best matching profile for (county, farm_type).
    Tries Supabase first, falls back to CSV.
    Returns None if the county is not found in either source.
    """
    data = _supabase_get_county(county, farm_type)
    if data:
        return data
    return _csv_get_county(county, farm_type)


def list_counties() -> list[str]:
    """Returns all county names. Supabase first (47), CSV fallback (8)."""
    counties = _supabase_list_counties()
    if counties:
        return counties
    return _csv_list_counties()


# ── Recommendation logic ──────────────────────────────────────────────────────

def build_recommendation(county: str, farm_type: str, weather: dict | None) -> dict | None:
    """
    Produces a recommendation combining ML prediction + county data + weather.

    Returns:
        {
            "county":            str,
            "farm_type":         str,
            "soil_type":         str,
            "avg_rainfall":      int,
            "recommendation":    str,
            "weather_notes":     list[str],
            "weather":           dict | None,
            "prediction_source": "model" | "csv",
            "data_source":       "supabase" | "csv",
        }
    Returns None if county is not found in any data source.
    """
    county_data = get_county_data(county, farm_type)
    if not county_data:
        return None

    # Live weather temp > county average
    temp = (
        weather.get("temp")
        if weather and weather.get("temp") is not None
        else county_data["avg_temp"]
    )
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
            elevation_m=county_data.get("elevation_m", 1000),
            irrigation=county_data.get("irrigation", 0),
            market_price_index=county_data.get("market_price_index", 3),
        )
        prediction_source = "model"
    except Exception as e:
        print(f"[recommender] ML prediction failed, using data fallback: {e}")

    return {
        "county":            county_data["county"],
        "farm_type":         farm_type,
        "soil_type":         county_data["soil_type"],
        "avg_rainfall":      county_data["avg_rainfall"],
        "recommendation":    recommendation,
        "weather_notes":     _weather_notes(weather),
        "weather":           weather,
        "prediction_source": prediction_source,
        "data_source":       county_data.get("source", "csv"),
    }


# ── Weather advisory notes ────────────────────────────────────────────────────

def _weather_notes(weather: dict | None) -> list[str]:
    """Derive actionable weather advice from current conditions."""
    if not weather:
        return []

    notes = []
    temp      = weather.get("temp")
    humidity  = weather.get("humidity")
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