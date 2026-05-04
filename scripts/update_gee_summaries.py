import json
from datetime import datetime, timezone
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.gee import COUNTY_GEOMETRIES, get_gee_insights


DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "gee_alerts_latest.json"


def build_county_summaries():
    counties = sorted(COUNTY_GEOMETRIES.keys())
    items = [get_gee_insights(county) for county in counties]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_county_summaries()
    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print(f"Saved GEE summaries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()