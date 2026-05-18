"""
services/market.py
Kenyan agricultural commodity prices.

Data source: FAO regional reference prices (KES), cached 24 hours.
GEE risk adjustment: optional — if county provided and GEE is available,
drought/excess-rainfall risk shifts the price range up or down.

Price data is intentionally conservative — these are indicative ranges
aligned with FAO East Africa references, not live exchange data.
"""

import json
import time
from pathlib import Path

from core.config import settings

CACHE_TTL_SECONDS = 24 * 3600
CACHE_PATH = settings.DATA_DIR / "fao_prices_cache.json"

# ── FAO reference prices (KES) ────────────────────────────────────────────────
# Updated from FAO/KIPPRA regional averages for Kenya.
# Unit meanings: bag = 90kg maize bag; head = live animal; liter; kg.

BASE_PRICES: dict[str, dict] = {
    "maize":    {"min": 2600,  "max": 3500,  "unit": "Ksh/bag (90kg)"},
    "beans":    {"min": 6200,  "max": 8200,  "unit": "Ksh/bag (90kg)"},
    "sorghum":  {"min": 2400,  "max": 3300,  "unit": "Ksh/bag (90kg)"},
    "millet":   {"min": 2800,  "max": 3700,  "unit": "Ksh/bag (90kg)"},
    "cassava":  {"min": 750,   "max": 1500,  "unit": "Ksh/kg"},
    "wheat":    {"min": 3200,  "max": 4200,  "unit": "Ksh/bag (90kg)"},
    "rice":     {"min": 4500,  "max": 6000,  "unit": "Ksh/bag (50kg)"},
    "tea":      {"min": 35,    "max": 60,    "unit": "Ksh/kg (green leaf)"},
    "sugarcane": {"min": 4200, "max": 5500,  "unit": "Ksh/tonne"},
    "potato":   {"min": 1800,  "max": 3200,  "unit": "Ksh/bag (110kg)"},
    "goat":     {"min": 5000,  "max": 9000,  "unit": "Ksh/head"},
    "sheep":    {"min": 6200,  "max": 10500, "unit": "Ksh/head"},
    "chicken":  {"min": 1300,  "max": 2800,  "unit": "Ksh/bird"},
    "dairy_cow":{"min": 55000, "max": 90000, "unit": "Ksh/head"},
    "beef_cattle":{"min": 35000,"max": 65000,"unit": "Ksh/head"},
    "dairy":    {"min": 38,    "max": 50,    "unit": "Ksh/liter"},
    "fish_farming":{"min": 450,"max": 900,   "unit": "Ksh/kg"},
    "camel":    {"min": 40000, "max": 80000, "unit": "Ksh/head"},
    "green_grams":{"min": 7000,"max": 9500,  "unit": "Ksh/bag (90kg)"},
    "coconut":  {"min": 15,    "max": 35,    "unit": "Ksh/nut"},
    "vegetables":{"min": 20,   "max": 80,    "unit": "Ksh/kg"},
}

# GEE risk → price multiplier (scarcity = higher prices)
_GEE_MULTIPLIERS = {"high": 1.20, "medium": 1.08, "low": 0.95}


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> dict | None:
    try:
        if CACHE_PATH.exists():
            data = json.loads(CACHE_PATH.read_text())
            if time.time() - data.get("cached_at", 0) < CACHE_TTL_SECONDS:
                return data
    except Exception:
        pass
    return None


def _save_cache(prices: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        prices["cached_at"] = time.time()
        CACHE_PATH.write_text(json.dumps(prices, indent=2))
    except Exception as e:
        print(f"[market] Cache save error: {e}")


# ── Public API ────────────────────────────────────────────────────────────────

def get_all_prices() -> dict:
    """
    Returns price dict for all commodities.
    Reads from cache if fresh, otherwise returns BASE_PRICES and caches them.
    """
    cached = _load_cache()
    if cached:
        return cached

    prices = {k: dict(v) for k, v in BASE_PRICES.items()}
    prices["source"] = "fao_reference"
    _save_cache(prices)
    return prices


def get_market_prices(item: str, county: str | None = None) -> dict:
    """
    Returns price data for a single commodity.
    Applies GEE risk adjustment if county is provided and GEE is available.

    Returns:
        { min, max, unit, source, risk_adjusted (bool), risk_level (str) }
    """
    item = (item or "maize").strip().lower()
    prices = get_all_prices()

    # Normalise: dairy_cow → dairy for lookup
    base = prices.get(item) or BASE_PRICES.get(item)
    if not base:
        # Try partial match (e.g. "green gram" → "green_grams")
        normalised = item.replace(" ", "_").replace("-", "_")
        base = BASE_PRICES.get(normalised, BASE_PRICES["maize"])

    result = {
        "min":          base["min"],
        "max":          base["max"],
        "unit":         base["unit"],
        "source":       prices.get("source", "fao_reference"),
        "risk_adjusted": False,
        "risk_level":   "unknown",
    }

    # ── GEE adjustment ────────────────────────────────────────────────────────
    if county:
        try:
            from services.gee import get_gee_insights
            gee = get_gee_insights(county)
            if gee and gee.get("status") == "ok":
                level = gee.get("alert_level", "low")
                mult = _GEE_MULTIPLIERS.get(level, 1.0)
                result["min"]          = int(result["min"] * mult)
                result["max"]          = int(result["max"] * mult)
                result["risk_adjusted"] = True
                result["risk_level"]   = level
        except Exception:
            pass

    return result


def format_price_for_ussd(item: str, price_data: dict) -> str:
    """Formats price data into a compact USSD-friendly string."""
    adj = " (risk adj.)" if price_data.get("risk_adjusted") else ""
    return (
        f"{item.replace('_', ' ').title()}{adj}\n"
        f"Min: KES {price_data['min']:,}\n"
        f"Max: KES {price_data['max']:,}\n"
        f"Unit: {price_data['unit']}"
    )


# Commodities shown in the USSD market menu — ordered for farmers
USSD_COMMODITY_MAP: dict[str, str] = {
    "1":  "maize",
    "2":  "beans",
    "3":  "green_grams",
    "4":  "sorghum",
    "5":  "wheat",
    "6":  "potato",
    "7":  "goat",
    "8":  "chicken",
    "9":  "dairy",
    "10": "fish_farming",
}