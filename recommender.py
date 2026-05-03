from pathlib import Path
import json

from services.advisory import build_advice
from services.alerts import get_alerts
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


def get_recommendation(county, farm_type, soil_type=None):
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
    weather = get_weather(county)
    advice = build_advice(county, soil, weather, recommendation)

    return {
        "county": county,
        "soil": soil,
        "farm_type": farm_type_normalized,
        "recommendation": recommendation,
        "advice": advice,
        "weather": weather,
        "alerts": get_alerts(county),
        "market": get_market_prices(recommendation),
        "products": list_products(),
    }