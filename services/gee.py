from __future__ import annotations

import os
from datetime import date, timedelta
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


COUNTY_GEOMETRIES = {
    "Makueni": [[[37.3, -2.0], [37.8, -2.0], [37.8, -1.4], [37.3, -1.4], [37.3, -2.0]]],
    "Nakuru": [[[35.6, -0.6], [36.4, -0.6], [36.4, 0.3], [35.6, 0.3], [35.6, -0.6]]],
    "Nyeri": [[[36.6, -0.8], [37.2, -0.8], [37.2, -0.1], [36.6, -0.1], [36.6, -0.8]]],
    "Kakamega": [[[34.4, -0.2], [35.1, -0.2], [35.1, 0.5], [34.4, 0.5], [34.4, -0.2]]],
    "Machakos": [[[37.0, -1.8], [37.9, -1.8], [37.9, -1.1], [37.0, -1.1], [37.0, -1.8]]],
    "Kiambu": [[[36.5, -1.3], [37.0, -1.3], [37.0, -0.8], [36.5, -0.8], [36.5, -1.3]]],
    "Meru": [[[37.3, -0.4], [38.1, -0.4], [38.1, 0.4], [37.3, 0.4], [37.3, -0.4]]],
    "Uasin Gishu": [[[35.1, -0.4], [35.8, -0.4], [35.8, 0.4], [35.1, 0.4], [35.1, -0.4]]],
}

DEFAULT_GEOMETRY = [[[36.7, -1.4], [37.0, -1.4], [37.0, -1.1], [36.7, -1.1], [36.7, -1.4]]]


def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except Exception:
        return fallback


@lru_cache(maxsize=1)
def init_gee():
    try:
        import ee
    except Exception as exc:
        return {"available": False, "mode": "missing-package", "message": str(exc)}

    project = os.getenv("GEE_PROJECT_ID")
    service_account = os.getenv("GEE_SERVICE_ACCOUNT")
    key_path = os.getenv("GEE_KEY_PATH")

    try:
        if service_account and key_path:
            credentials = ee.ServiceAccountCredentials(service_account, key_path)
            ee.Initialize(credentials, project=project)
            return {"available": True, "mode": "service-account", "message": "initialized"}

        if project:
            ee.Initialize(project=project)
            return {"available": True, "mode": "oauth", "message": "initialized"}

        ee.Initialize()
        return {"available": True, "mode": "default", "message": "initialized"}
    except Exception as exc:
        return {"available": False, "mode": "auth-error", "message": str(exc)}


def _county_geometry(county: str):
    county_name = (county or "").strip().title()
    return COUNTY_GEOMETRIES.get(county_name, DEFAULT_GEOMETRY)


def _compute_ndvi_and_rainfall(county: str):
    import ee

    polygon = ee.Geometry.Polygon(_county_geometry(county))
    today = date.today()
    end_date = today.isoformat()

    recent_start = (today - timedelta(days=30)).isoformat()
    baseline_start = (today - timedelta(days=395)).isoformat()
    baseline_end = recent_start

    ndvi_collection = (
        ee.ImageCollection("MODIS/061/MOD13Q1")
        .select("NDVI")
        .filterBounds(polygon)
        .filterDate(recent_start, end_date)
    )
    ndvi_image = ndvi_collection.mean().multiply(0.0001)
    ndvi_value = ndvi_image.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=polygon, scale=250, maxPixels=1_000_000
    ).get("NDVI")

    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").select("precipitation")
    recent_total_img = chirps.filterBounds(polygon).filterDate(recent_start, end_date).sum()
    recent_total = recent_total_img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=polygon, scale=5500, maxPixels=1_000_000
    ).get("precipitation")

    baseline_daily_img = chirps.filterBounds(polygon).filterDate(baseline_start, baseline_end).mean()
    baseline_daily = baseline_daily_img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=polygon, scale=5500, maxPixels=1_000_000
    ).get("precipitation")

    ndvi_mean = _safe_float(ndvi_value.getInfo(), 0.0)
    rainfall_recent_mm = _safe_float(recent_total.getInfo(), 0.0)
    baseline_daily_mm = _safe_float(baseline_daily.getInfo(), 0.0)
    rainfall_expected_mm = baseline_daily_mm * 30.0

    if rainfall_expected_mm <= 0:
        anomaly_pct = 0.0
    else:
        anomaly_pct = ((rainfall_recent_mm - rainfall_expected_mm) / rainfall_expected_mm) * 100.0

    return {
        "ndvi_mean": round(ndvi_mean, 4),
        "rainfall_recent_30d_mm": round(rainfall_recent_mm, 2),
        "rainfall_expected_30d_mm": round(rainfall_expected_mm, 2),
        "rainfall_anomaly_pct": round(anomaly_pct, 2),
    }


def _derive_alert_level(ndvi_mean: float, rainfall_anomaly_pct: float):
    if ndvi_mean < 0.2 or rainfall_anomaly_pct < -40:
        return "high"
    if ndvi_mean < 0.3 or rainfall_anomaly_pct < -20:
        return "medium"
    return "low"


def get_gee_insights(county: str):
    county_name = (county or "").strip().title()
    init = init_gee()

    if not init.get("available"):
        return {
            "status": "unavailable",
            "county": county_name,
            "message": "Earth Engine is not initialized. Configure GEE credentials first.",
            "details": init,
        }

    try:
        metrics = _compute_ndvi_and_rainfall(county_name)
        alert_level = _derive_alert_level(metrics["ndvi_mean"], metrics["rainfall_anomaly_pct"])
        return {
            "status": "ok",
            "county": county_name,
            "alert_level": alert_level,
            "summary": (
                f"NDVI {metrics['ndvi_mean']}, rainfall anomaly {metrics['rainfall_anomaly_pct']}%."
            ),
            "metrics": metrics,
            "datasets": {
                "ndvi": "MODIS/061/MOD13Q1",
                "rainfall": "UCSB-CHG/CHIRPS/DAILY",
            },
            "gee_mode": init.get("mode"),
            "generated_on": date.today().isoformat(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "county": county_name,
            "message": "Failed to compute Earth Engine insights.",
            "details": str(exc),
        }