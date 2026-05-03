def get_gee_insights(county: str):
    return {
        "status": "not_implemented",
        "county": (county or "").strip().title(),
        "message": "Google Earth Engine integration will be added later.",
    }