from __future__ import annotations

from services.gee import get_gee_insights


def get_alerts(county: str):
    county = (county or "").strip().title()
    if not county:
        return []
    return [f"No active alerts for {county}."]


def _subscription_gate(subscribed: bool):
    if subscribed:
        return None
    return "This alert channel is available to subscribed users only. Please subscribe to receive live advisories."


def build_weather_alert(county: str, subscribed: bool = False):
    county = (county or "").strip().title()
    gate = _subscription_gate(subscribed)
    if gate:
        return gate

    gee = get_gee_insights(county)
    base_alerts = get_alerts(county)
    if gee.get("status") == "ok":
        metrics = gee.get("metrics", {})
        return (
            f"Weather alert for {county}:\n"
            f"• {base_alerts[0]}\n"
            f"• GEE risk level: {gee.get('alert_level', 'unknown').upper()}\n"
            f"• NDVI: {metrics.get('ndvi_mean', 'n/a')}\n"
            f"• Rainfall anomaly: {metrics.get('rainfall_anomaly_pct', 'n/a')}%"
        )

    return f"Weather alert for {county}: {base_alerts[0]}"


def build_disease_alert(county: str, subscribed: bool = False):
    county = (county or "").strip().title()
    gate = _subscription_gate(subscribed)
    if gate:
        return gate

    gee = get_gee_insights(county)
    if gee.get("status") == "ok":
        metrics = gee.get("metrics", {})
        rainfall_anomaly = metrics.get("rainfall_anomaly_pct", 0)
        ndvi = metrics.get("ndvi_mean", 0)
        if rainfall_anomaly > 20:
            risk_note = "wet conditions can increase fungal disease pressure"
        elif rainfall_anomaly < -20:
            risk_note = "dry stress may increase pest pressure and crop weakness"
        else:
            risk_note = "conditions are stable, but continue field scouting"

        return (
            f"Disease alert for {county}:\n"
            f"• GEE risk level: {gee.get('alert_level', 'unknown').upper()}\n"
            f"• NDVI: {ndvi}\n"
            f"• Rainfall anomaly: {rainfall_anomaly}%\n"
            f"• Advisory: {risk_note}"
        )

    return f"Disease alert for {county}: monitor crops closely and scout for pests and disease."