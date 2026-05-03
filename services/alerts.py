def get_alerts(county: str):
    county = (county or "").strip().title()
    if not county:
        return []
    return [f"No active alerts for {county}."]