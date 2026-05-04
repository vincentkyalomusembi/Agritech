import os
import warnings

from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def _gee_context_text(gee_insights: dict | None):
    if not gee_insights or gee_insights.get("status") != "ok":
        return ""

    metrics = gee_insights.get("metrics", {})
    ndvi = metrics.get("ndvi_mean")
    rainfall_anomaly = metrics.get("rainfall_anomaly_pct")
    alert_level = gee_insights.get("alert_level", "unknown")
    return (
        f" Satellite indicators show NDVI {ndvi} and rainfall anomaly {rainfall_anomaly}%."
        f" Current remote-sensing alert level is {alert_level}."
    )


def _weather_context_text(weather: dict):
    temp = weather.get("temp", "?")
    feels_like = weather.get("feels_like")
    humidity = weather.get("humidity")
    pressure = weather.get("pressure")
    wind_speed = weather.get("wind_speed")
    clouds = weather.get("clouds")
    condition = weather.get("condition", "unknown weather")
    source = weather.get("source", "unknown")

    parts = [f"weather={condition}", f"temp={temp}°C"]
    if feels_like is not None:
        parts.append(f"feels_like={feels_like}°C")
    if humidity is not None:
        parts.append(f"humidity={humidity}%")
    if pressure is not None:
        parts.append(f"pressure={pressure}hPa")
    if wind_speed is not None:
        parts.append(f"wind={wind_speed}m/s")
    if clouds is not None:
        parts.append(f"clouds={clouds}%")

    return f" OpenWeather({source}) says " + ", ".join(parts) + "."


def _parse_gee_risk(gee_insights: dict | None):
    if not gee_insights or gee_insights.get("status") != "ok":
        return "unknown"
    return gee_insights.get("alert_level", "unknown")


def build_advice(
    county: str,
    soil: str,
    weather: dict,
    recommendation: str,
    farm_type: str | None = None,
    gee_insights: dict | None = None,
    recommendation_options: list[str] | None = None,
    farm_size: str | None = None,
    budget: str | None = None,
    experience: str | None = None,
    skip_gemini: bool = False,
):
    county = (county or "").strip().title()
    soil = (soil or "loamy").strip().lower()
    weather_condition = weather.get("condition", "unknown weather")
    temp = weather.get("temp", "?")
    gee_context = _gee_context_text(gee_insights)
    weather_context = _weather_context_text(weather)
    gee_risk = _parse_gee_risk(gee_insights)
    farm_type = (farm_type or "crop").strip().lower()
    recommendation_options = [opt for opt in (recommendation_options or []) if opt]

    extra = ""
    if farm_size:
        extra += f" Farm size: {farm_size}."
    if budget:
        extra += f" Budget: KES {budget}."
    if experience:
        extra += f" Experience: {experience}."

    if not GEMINI_API_KEY or skip_gemini:
        options_text = ""
        if recommendation_options:
            options_text = " Best options: " + ", ".join(recommendation_options) + "."
        return (
            f"Based on {county} with {soil} soil and {weather_condition} weather "
            f"({temp}°C), {recommendation} is recommended.{options_text}{gee_context}{weather_context}{extra}"
        )

    try:
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        prompt = (
            f"You are an agronomy assistant. Use GEE as the primary signal for crop risk, "
            f"OpenWeather as the secondary environment signal, and user inputs to give a practical recommendation."
            f" County: {county}. Soil: {soil}. Farm type: {farm_type}. Suggested option: {recommendation}."
            f" GEE risk: {gee_risk}."
            f" Alternative options: {', '.join(recommendation_options) if recommendation_options else 'none'}."
            f" Explain in 2 short sentences why {recommendation} is suitable for farming in {county}, Kenya"
            f" with {soil} soil and {weather_condition} weather at {temp}°C."
            f" Include one actionable risk-management tip and mention whether the farmer should prioritize irrigation, drought tolerance, disease scouting, or heat-stress management."
            f"{gee_context}{weather_context}"
        )
        if farm_type == "livestock":
            prompt += (
                " If this is livestock, factor in heat stress, water availability, and disease pressure."
                " Prefer hardy livestock types in hot or dry conditions and mention shade, clean water, and feed planning."
            )
        if farm_size:
            prompt += f" The farmer has {farm_size} of land."
        if budget:
            prompt += f" Their budget is approximately KES {budget}."
        if experience:
            prompt += f" Experience level: {experience}."
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt, request_options={"timeout": 2})
        if getattr(response, "text", None):
            return response.text.strip()
    except Exception:
        pass

    return (
        f"Based on {county} with {soil} soil, {recommendation} is recommended for the current season."
        f"{' Best options: ' + ', '.join(recommendation_options) + '.' if recommendation_options else ''}"
        f"{gee_context}{weather_context}"
    )