from pathlib import Path
import json

from services.advisory import build_advice
from services.alerts import get_alerts
from services.gee import get_gee_insights
from services.market import get_market_prices
from services.products import list_products
from services.weather import get_weather
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ROOT_DATA_FILE = BASE_DIR / "mock_data.json"
PRIMARY_DATA_FILE = DATA_DIR / "mock_data.json"


def _load_mock_data():
    for path in (PRIMARY_DATA_FILE, ROOT_DATA_FILE):
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
    return {
        "regions": {
            "Makueni": {
                "soil": "sandy",
                "weather": "hot",
                "crop_recommendation": "sorghum",
                "livestock_recommendation": "goat",
            }
        }
    }


MOCK_DATA = _load_mock_data()


def _unique_keep_order(values):
    seen = set()
    ordered = []
    for value in values:
        item = (value or "").strip().lower()
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _crop_options(base_recommendation: str, weather: dict, gee_insights: dict | None):
    rainfall_anomaly = ((gee_insights or {}).get("metrics") or {}).get("rainfall_anomaly_pct")
    temp = weather.get("temp")
    humidity = weather.get("humidity")

    options = [base_recommendation, "sorghum", "millet", "cowpea", "cassava", "beans", "maize"]
    if isinstance(rainfall_anomaly, (int, float)) and rainfall_anomaly <= -30:
        options = ["sorghum", "millet", "cowpea", "cassava", base_recommendation, "beans", "maize"]
    elif isinstance(temp, (int, float)) and temp >= 30:
        options = ["sorghum", "millet", "cowpea", base_recommendation, "beans", "maize", "cassava"]
    elif isinstance(humidity, (int, float)) and humidity >= 75:
        options = ["maize", "beans", base_recommendation, "cowpea", "sorghum", "millet", "cassava"]

    return _unique_keep_order(options)[:4]


def _livestock_options(base_recommendation: str, weather: dict, gee_insights: dict | None):
    rainfall_anomaly = ((gee_insights or {}).get("metrics") or {}).get("rainfall_anomaly_pct")
    temp = weather.get("temp")
    humidity = weather.get("humidity")

    options = [base_recommendation, "goat", "chicken", "dairy cattle", "sheep"]
    if isinstance(rainfall_anomaly, (int, float)) and rainfall_anomaly <= -30:
        options = ["goat", "sheep", base_recommendation, "chicken", "dairy cattle"]
    elif isinstance(temp, (int, float)) and temp >= 30:
        options = ["goat", "sheep", "chicken", base_recommendation, "dairy cattle"]
    elif isinstance(humidity, (int, float)) and humidity >= 75:
        options = ["dairy cattle", "goat", "chicken", base_recommendation, "sheep"]

    return _unique_keep_order(options)[:4]


def _adjust_recommendation_by_context(base_recommendation: str, farm_type: str, weather: dict, gee_insights: dict | None):
    recommended = (base_recommendation or "").strip().lower()
    gee_alert = (gee_insights or {}).get("alert_level") if gee_insights else None
    rainfall_anomaly = ((gee_insights or {}).get("metrics") or {}).get("rainfall_anomaly_pct")
    temp = weather.get("temp")
    humidity = weather.get("humidity")

    if farm_type in {"animal", "livestock"}:
        if isinstance(temp, (int, float)) and temp >= 30:
            return "goat"
        if isinstance(rainfall_anomaly, (int, float)) and rainfall_anomaly <= -30:
            return "goat"
        if isinstance(humidity, (int, float)) and humidity >= 75:
            return "dairy cattle"
        if recommended in {"chicken", "goat", "dairy cattle"}:
            return recommended
        return "goat"

    if gee_alert == "high" or (isinstance(rainfall_anomaly, (int, float)) and rainfall_anomaly <= -30):
        if recommended not in {"sorghum", "millet", "cassava", "cowpea", "goat"}:
            return "sorghum"

    if isinstance(temp, (int, float)) and temp >= 30 and recommended == "maize":
        return "sorghum"

    if isinstance(humidity, (int, float)) and humidity >= 75 and recommended in {"maize", "beans"}:
        return recommended

    return recommended


def _select_options(base_recommendation: str, farm_type: str, weather: dict, gee_insights: dict | None):
    if farm_type in {"animal", "livestock"}:
        return _livestock_options(base_recommendation, weather, gee_insights)
    return _crop_options(base_recommendation, weather, gee_insights)


def get_recommendation(county, farm_type, soil_type=None, farm_size=None, budget=None, experience=None, ussd_mode=False):
    """Get recommendation with optional USSD-optimized fast path.
    
    Args:
        ussd_mode: If True, skip Gemini and expensive live GEE calls for speed.
                   Default False (use full pipeline).
    """
    county = (county or "").strip().title()
    farm_type = (farm_type or "crop").strip().lower()

    region_data = MOCK_DATA.get("regions", {}).get(
        county,
        {
            "soil": "loamy",
            "weather": "mild",
            "crop_recommendation": "maize",
            "livestock_recommendation": "chicken",
        },
    )

    if farm_type in {"animal", "livestock"}:
        recommendation = region_data["livestock_recommendation"]
        farm_type_normalized = "livestock"
    else:
        recommendation = region_data["crop_recommendation"]
        farm_type_normalized = "crop"

    soil = (soil_type or region_data.get("soil", "loamy")).strip().lower()
    weather = get_weather(county, timeout_secs=2 if ussd_mode else 5)

    # Load GEE: use cached only for USSD, avoid slow live calls during USSD session
    GEE_CACHE = BASE_DIR / "data" / "gee_alerts_latest.json"
    gee_insights = None
    try:
        if GEE_CACHE.exists():
            payload = json.loads(GEE_CACHE.read_text(encoding="utf-8"))
            for item in payload.get("items", []):
                if item.get("county") == county:
                    gee_insights = item
                    break
    except Exception:
        gee_insights = None

    # For non-USSD requests, try live GEE if cache missing
    if not gee_insights and not ussd_mode:
        try:
            gee_insights = get_gee_insights(county)
        except Exception:
            gee_insights = None

    recommendation = _adjust_recommendation_by_context(recommendation, farm_type_normalized, weather, gee_insights)
    recommendation_options = _select_options(recommendation, farm_type_normalized, weather, gee_insights)

    advice = build_advice(
        county,
        soil,
        weather,
        recommendation,
        farm_type=farm_type_normalized,
        gee_insights=gee_insights,
        recommendation_options=recommendation_options,
        farm_size=farm_size,
        budget=budget,
        experience=experience,
        skip_gemini=ussd_mode,  # Skip slow Gemini calls for USSD
    )

    # For USSD, skip expensive alert/market processing
    if ussd_mode:
        return {
            "county": county,
            "soil": soil,
            "farm_type": farm_type_normalized,
            "recommendation": recommendation,
            "recommendation_options": recommendation_options,
            "advice": advice,
            "weather": weather,
            "gee_insights": gee_insights,
        }

    # Full response for API/web requests
    return {
        "county": county,
        "soil": soil,
        "farm_type": farm_type_normalized,
        "recommendation": recommendation,
        "recommendation_options": recommendation_options,
        "advice": advice,
        "weather": weather,
        "gee_insights": gee_insights,
        "alerts": get_alerts(county),
        "market": get_market_prices(recommendation),
        "products": list_products(),
        "farm_size": farm_size,
        "budget": budget,
        "experience": experience,
    }