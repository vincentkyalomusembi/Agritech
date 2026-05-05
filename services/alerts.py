from __future__ import annotations

from services.gee import get_gee_insights
from services.weather import get_weather


def get_alerts(county: str):
    county = (county or "").strip().title()
    if not county:
        return []

    alerts = []

    gee = get_gee_insights(county)
    weather = get_weather(county)

    if gee.get("status") == "ok":
        metrics = gee.get("metrics", {})
        rainfall_anomaly = metrics.get("rainfall_anomaly_pct")
        ndvi = metrics.get("ndvi_mean")
        alert_level = (gee.get("alert_level") or "unknown").upper()

        alerts.append(f"GEE alert for {county}: {alert_level} risk.")
        alerts.append(f"NDVI: {ndvi}")
        alerts.append(f"Rainfall anomaly: {rainfall_anomaly}%")

        if isinstance(rainfall_anomaly, (int, float)) and rainfall_anomaly <= -40:
            alerts.append("Drought stress risk is high; conserve water and prioritize drought-tolerant crops.")
        elif isinstance(rainfall_anomaly, (int, float)) and rainfall_anomaly > 20:
            alerts.append("Excess rainfall risk; improve drainage and monitor fungal disease.")

    temp = weather.get("temp")
    humidity = weather.get("humidity")
    condition = str(weather.get("condition", "")).lower()

    if isinstance(temp, (int, float)) and temp >= 30:
        alerts.append(f"High heat warning: {temp}°C may stress crops and livestock.")
    if isinstance(humidity, (int, float)) and humidity >= 80:
        alerts.append(f"High humidity warning: {humidity}% may increase disease pressure.")
    if "rain" in condition:
        alerts.append(f"Weather note: {weather.get('condition')} in {county}; check drainage and spray timing.")

    if not alerts:
        alerts.append(f"No active alerts for {county}.")

    return alerts


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
    weather = get_weather(county)
    base_alerts = get_alerts(county)

    weather_lines = [
        f"• OpenWeather condition: {weather.get('condition', 'n/a')}",
        f"• Temperature: {weather.get('temp', 'n/a')}°C",
    ]
    if weather.get("feels_like") is not None:
        weather_lines.append(f"• Feels like: {weather.get('feels_like')}°C")
    if weather.get("humidity") is not None:
        weather_lines.append(f"• Humidity: {weather.get('humidity')}%")
    if weather.get("wind_speed") is not None:
        weather_lines.append(f"• Wind speed: {weather.get('wind_speed')} m/s")
    if weather.get("clouds") is not None:
        weather_lines.append(f"• Cloud cover: {weather.get('clouds')}%")

    if gee.get("status") == "ok":
        metrics = gee.get("metrics", {})
        return (
            f"Weather alert for {county}:\n"
            f"• {base_alerts[0]}\n"
            + "\n".join(weather_lines)
            + f"\n• GEE risk level: {gee.get('alert_level', 'unknown').upper()}\n"
            f"• NDVI: {metrics.get('ndvi_mean', 'n/a')}\n"
            f"• Rainfall anomaly: {metrics.get('rainfall_anomaly_pct', 'n/a')}%"
        )

    return (
        f"Weather alert for {county}:\n"
        f"• {base_alerts[0]}\n"
        + "\n".join(weather_lines)
    )


def build_disease_alert(county: str, subscribed: bool = False):
    county = (county or "").strip().title()
    gate = _subscription_gate(subscribed)
    if gate:
        return gate

    gee = get_gee_insights(county)
    weather = get_weather(county)
    if gee.get("status") == "ok":
        metrics = gee.get("metrics", {})
        rainfall_anomaly = metrics.get("rainfall_anomaly_pct", 0)
        ndvi = metrics.get("ndvi_mean", 0)
        humidity = weather.get("humidity")
        temp = weather.get("temp")
        if rainfall_anomaly > 20:
            risk_note = "wet conditions can increase fungal disease pressure"
        elif rainfall_anomaly < -20:
            risk_note = "dry stress may increase pest pressure and crop weakness"
        else:
            risk_note = "conditions are stable, but continue field scouting"

        if isinstance(humidity, (int, float)) and humidity >= 80:
            risk_note = f"high humidity ({humidity}%) can increase fungal disease pressure"
        elif isinstance(temp, (int, float)) and temp >= 30:
            risk_note = f"high heat ({temp}°C) may stress crops and invite secondary pests"

        return (
            f"Disease alert for {county}:\n"
            f"• GEE risk level: {gee.get('alert_level', 'unknown').upper()}\n"
            f"• NDVI: {ndvi}\n"
            f"• Rainfall anomaly: {rainfall_anomaly}%\n"
            f"• Weather humidity: {humidity if humidity is not None else 'n/a'}%\n"
            f"• Advisory: {risk_note}"
        )

    return f"Disease alert for {county}: monitor crops closely and scout for pests and disease."